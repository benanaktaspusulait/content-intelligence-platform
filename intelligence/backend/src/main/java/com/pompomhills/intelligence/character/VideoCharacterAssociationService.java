package com.pompomhills.intelligence.character;

import com.pompomhills.intelligence.video.VideoEntity;
import com.pompomhills.intelligence.video.VideoRepository;
import com.pompomhills.intelligence.video.prompt.PromptSourceResolution;
import com.pompomhills.intelligence.video.prompt.VideoPromptSourceResolver;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VideoCharacterAssociationService {
  public static final String BACKFILL_VERSION = "legacy-backfill-v1";
  private final VideoRepository videos;
  private final JdbcClient jdbc;
  private final VideoPromptSourceResolver promptResolver;
  private final PromptCharacterResolver characterResolver;

  public VideoCharacterAssociationService(VideoRepository videos, JdbcClient jdbc,
      VideoPromptSourceResolver promptResolver, PromptCharacterResolver characterResolver) {
    this.videos = videos; this.jdbc = jdbc; this.promptResolver = promptResolver; this.characterResolver = characterResolver;
  }

  @Transactional
  public AssociationResult associate(UUID videoId, Mode mode) {
    VideoEntity video = videos.findById(videoId).orElseThrow(() -> new IllegalArgumentException("Video not found: " + videoId));
    boolean hasStrong = jdbc.sql("SELECT EXISTS(SELECT 1 FROM video_characters WHERE video_id=:id AND (manually_confirmed=true OR association_source IN ('MANUAL','PRODUCTION_CONTRACT','VIDEO_PLAN','EXPLICIT_EXISTING_RELATION')))")
        .param("id", videoId).query(Boolean.class).single();
    if (hasStrong && mode != Mode.RECOMPUTE_INFERRED) return new AssociationResult(videoId, "PRESERVED_STRONG_ASSOCIATION", null, List.of(), 0, 0);
    PromptSourceResolution resolution = promptResolver.resolve(video);
    persistResolution(videoId, resolution);
    if (!resolution.matched()) return new AssociationResult(videoId, resolution.status().name(), resolution.promptPath(), List.of(), 0, resolution.candidateCount());
    List<PromptCharacterResolver.DetectedCharacter> found = characterResolver.resolve(resolution.promptText());
    if (found.isEmpty()) return new AssociationResult(videoId, "CHARACTER_NOT_FOUND_IN_PROMPT", resolution.promptPath(), List.of(), 0, found.size());
    if (mode == Mode.RECOMPUTE_INFERRED) jdbc.sql("DELETE FROM video_characters WHERE video_id=:id AND manually_confirmed=false AND association_source NOT IN ('PRODUCTION_CONTRACT','VIDEO_PLAN','MANUAL','EXPLICIT_EXISTING_RELATION')").param("id", videoId).update();
    boolean single = found.size() == 1;
    List<String> names = new ArrayList<>();
    for (PromptCharacterResolver.DetectedCharacter item : found) {
      String participation = single ? "PRIMARY" : "SECONDARY";
      String source = resolution.status() == PromptSourceResolution.Status.MATCHED_EXACT ? "PROMPT_ENTITY" : "PROMPT_FILE_INFERRED";
      jdbc.sql("""
          INSERT INTO video_characters(video_id,character_id,participation,role,association_source,confidence,source_prompt_path,resolver_version,evidence_reference,manually_confirmed,updated_at)
          VALUES(:video,:character,:participation,'UNKNOWN',:source,:confidence,:prompt,:version,:evidence,false,now())
          ON CONFLICT(video_id,character_id) DO UPDATE SET
            participation=CASE WHEN video_characters.manually_confirmed THEN video_characters.participation ELSE excluded.participation END,
            role=CASE WHEN video_characters.manually_confirmed THEN video_characters.role ELSE excluded.role END,
            association_source=CASE WHEN video_characters.manually_confirmed THEN video_characters.association_source ELSE excluded.association_source END,
            confidence=CASE WHEN video_characters.manually_confirmed THEN video_characters.confidence ELSE excluded.confidence END,
            source_prompt_path=CASE WHEN video_characters.manually_confirmed THEN video_characters.source_prompt_path ELSE excluded.source_prompt_path END,
            resolver_version=CASE WHEN video_characters.manually_confirmed THEN video_characters.resolver_version ELSE excluded.resolver_version END,
            evidence_reference=CASE WHEN video_characters.manually_confirmed THEN video_characters.evidence_reference ELSE excluded.evidence_reference END,
            updated_at=now()
          """).param("video", videoId).param("character", item.characterId()).param("participation", participation)
          .param("source", source).param("confidence", single ? "HIGH" : "MEDIUM")
          .param("prompt", resolution.promptPath()).param("version", PromptCharacterResolver.VERSION)
          .param("evidence", "matched=" + item.matchedAlias() + ";mentions=" + item.mentionCount()).update();
      names.add(item.canonicalName());
    }
    return new AssociationResult(videoId, "ASSOCIATED", resolution.promptPath(), names, found.size(), 0);
  }

  @Transactional
  public BackfillReport backfill(Mode mode, boolean dryRun) {
    List<UUID> ids = jdbc.sql("SELECT v.id FROM videos v WHERE :mode='RECOMPUTE_INFERRED' OR :mode='RETRY_UNRESOLVED' OR NOT EXISTS(SELECT 1 FROM video_characters vc WHERE vc.video_id=v.id)").param("mode", mode.name()).query(UUID.class).list();
    int scanned=0, associated=0, matched=0, missing=0, ambiguous=0, unresolved=0, errors=0, preserved=0;
    for (UUID id : ids) {
      scanned++;
      try {
        if (dryRun) {
          VideoEntity video = videos.findById(id).orElseThrow(); PromptSourceResolution result = promptResolver.resolve(video);
          if (result.matched()) matched++; else if (result.status()==PromptSourceResolution.Status.AMBIGUOUS) ambiguous++; else missing++;
        } else {
          AssociationResult result = associate(id, mode);
          if ("ASSOCIATED".equals(result.status())) { associated++; matched++; }
          else if ("PRESERVED_STRONG_ASSOCIATION".equals(result.status())) preserved++;
          else if ("AMBIGUOUS".equals(result.status())) ambiguous++;
          else if ("CHARACTER_NOT_FOUND_IN_PROMPT".equals(result.status())) unresolved++;
          else if (result.status().equals("ERROR")) errors++; else missing++;
        }
      } catch (RuntimeException error) { errors++; }
    }
    return new BackfillReport(scanned, associated, matched, missing, ambiguous, unresolved, errors, preserved, dryRun, mode.name());
  }

  private void persistResolution(UUID videoId, PromptSourceResolution r) {
    jdbc.sql("""
      INSERT INTO video_prompt_resolutions(video_id,status,prompt_path,matching_method,confidence,candidate_count,error_message,resolver_version,resolved_at)
      VALUES(:video,:status,:path,:method,:confidence,:count,:error,:version,now())
      ON CONFLICT(video_id) DO UPDATE SET status=excluded.status,prompt_path=excluded.prompt_path,matching_method=excluded.matching_method,confidence=excluded.confidence,candidate_count=excluded.candidate_count,error_message=excluded.error_message,resolver_version=excluded.resolver_version,resolved_at=now()
      """).param("video",videoId).param("status",r.status().name()).param("path",r.promptPath()).param("method",r.matchingMethod()).param("confidence",r.confidence()).param("count",r.candidateCount()).param("error",r.errorMessage()).param("version",VideoPromptSourceResolver.VERSION).update();
  }

  public enum Mode { MISSING_ONLY, RETRY_UNRESOLVED, RECOMPUTE_INFERRED }
  public record AssociationResult(UUID videoId, String status, String promptPath, List<String> characters, int associationCount, int candidateCount) {}
  public record BackfillReport(int videosScanned,int associationsCreated,int promptMatched,int promptMissing,int promptAmbiguous,int characterUnresolved,int errors,int preserved,boolean dryRun,String mode) {}
}
