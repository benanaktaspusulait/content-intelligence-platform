package com.pompomhills.intelligence.character;

import jakarta.persistence.EntityNotFoundException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CharacterService {
  private final CharacterRepository characters;
  private final JdbcClient jdbc;

  public CharacterService(CharacterRepository characters, JdbcClient jdbc) {
    this.characters = characters;
    this.jdbc = jdbc;
  }

  @Transactional
  public CharacterView create(String name, CharacterStatus status, String notes) {
    if (characters.existsByNameIgnoreCase(name))
      throw new IllegalArgumentException("Character name already exists");
    return map(characters.save(new CharacterEntity(UUID.randomUUID(), name, status, notes)));
  }

  @Transactional
  public void assign(
      UUID videoId,
      UUID characterId,
      String participation,
      String role,
      Double screenTimeRatio,
      Double actionShare,
      Double speakingShare) {
    if (!characters.existsById(characterId))
      throw new EntityNotFoundException("Character not found: " + characterId);
    Integer videoCount =
        jdbc.sql("select count(*) from videos where id=:id")
            .param("id", videoId)
            .query(Integer.class)
            .single();
    if (videoCount == 0) throw new EntityNotFoundException("Video not found: " + videoId);
    jdbc.sql(
            """
        insert into video_characters(video_id,character_id,participation,role,screen_time_ratio,action_share,speaking_share)
        values(:video,:character,:participation,:role,:screen,:action,:speaking)
        on conflict(video_id,character_id) do update set participation=excluded.participation,role=excluded.role,
        screen_time_ratio=excluded.screen_time_ratio,action_share=excluded.action_share,speaking_share=excluded.speaking_share,
        association_source='MANUAL',confidence='HIGH',manually_confirmed=true,updated_at=now()
        """)
        .param("video", videoId)
        .param("character", characterId)
        .param("participation", participation)
        .param("role", role)
        .param("screen", screenTimeRatio)
        .param("action", actionShare)
        .param("speaking", speakingShare)
        .update();
    jdbc.sql("UPDATE video_characters SET association_source='MANUAL',confidence='HIGH',manually_confirmed=true,updated_at=now() WHERE video_id=:video AND character_id=:character")
        .param("video", videoId).param("character", characterId).update();
  }

  private static final java.util.Set<String> PARTICIPATIONS = java.util.Set.of("PRIMARY", "SECONDARY");
  private static final java.util.Set<String> ROLES =
      java.util.Set.of("PROTAGONIST", "HELPER", "RIVAL", "OBSERVER", "COMEDIC_TARGET", "TEACHER", "UNKNOWN");

  /**
   * Replaces the complete character set of a video in one transaction. At most one PRIMARY is
   * allowed; existing participation ratios are preserved for retained characters. Every stored row
   * is marked as a manual, confirmed association.
   */
  @Transactional
  public void replaceForVideo(UUID videoId, List<VideoCharacterInput> items) {
    Integer videoCount =
        jdbc.sql("select count(*) from videos where id=:id").param("id", videoId).query(Integer.class).single();
    if (videoCount == 0) throw new EntityNotFoundException("Video not found: " + videoId);
    java.util.Set<UUID> seen = new java.util.HashSet<>();
    UUID primary = null;
    for (VideoCharacterInput item : items) {
      if (item.characterId() == null) throw new IllegalArgumentException("characterId is required");
      if (!PARTICIPATIONS.contains(item.participation()))
        throw new IllegalArgumentException("Invalid participation: " + item.participation());
      if (!ROLES.contains(item.role())) throw new IllegalArgumentException("Invalid role: " + item.role());
      if (!seen.add(item.characterId()))
        throw new IllegalArgumentException("Duplicate character: " + item.characterId());
      if (!characters.existsById(item.characterId()))
        throw new EntityNotFoundException("Character not found: " + item.characterId());
      if ("PRIMARY".equals(item.participation())) {
        if (primary != null) throw new IllegalArgumentException("A video can have only one primary character");
        primary = item.characterId();
      }
    }
    if (seen.isEmpty()) {
      jdbc.sql("delete from video_characters where video_id=:video").param("video", videoId).update();
      return;
    }
    jdbc.sql("delete from video_characters where video_id=:video and character_id not in (:ids)")
        .param("video", videoId).param("ids", seen).update();
    // Demote first so the single-primary unique index is never violated mid-transaction.
    jdbc.sql("update video_characters set participation='SECONDARY' where video_id=:video and participation='PRIMARY'")
        .param("video", videoId).update();
    for (VideoCharacterInput item : items) {
      jdbc.sql(
              """
          insert into video_characters(video_id,character_id,participation,role,association_source,confidence,manually_confirmed,updated_at)
          values(:video,:character,:participation,:role,'MANUAL','HIGH',true,now())
          on conflict(video_id,character_id) do update set participation=excluded.participation,role=excluded.role,
          association_source='MANUAL',confidence='HIGH',manually_confirmed=true,updated_at=now()
          """)
          .param("video", videoId)
          .param("character", item.characterId())
          .param("participation", "SECONDARY")
          .param("role", item.role())
          .update();
    }
    if (primary != null) {
      jdbc.sql("update video_characters set participation='PRIMARY' where video_id=:video and character_id=:character")
          .param("video", videoId).param("character", primary).update();
    }
  }

  public record VideoCharacterInput(UUID characterId, String participation, String role) {}

  @Transactional(readOnly = true)
  public List<CharacterView> list() {
    return characters.findAll().stream().map(this::map).toList();
  }

  @Transactional(readOnly = true)
  public List<CharacterCoverageView> coverage() {
    List<CharacterView> canonical = list();
    Map<UUID, Map<String, Long>> byCharacter = new LinkedHashMap<>();
    jdbc.sql(
            """
            SELECT vc.character_id,
              COALESCE(ca.primary_engine,'UNCLASSIFIED') AS format,
              count(DISTINCT po.id) AS observations
            FROM video_characters vc
            JOIN performance_observations po ON po.video_id=vc.video_id
            LEFT JOIN LATERAL (
              SELECT primary_engine FROM creative_analyses
              WHERE video_id=vc.video_id ORDER BY created_at DESC LIMIT 1
            ) ca ON true
            GROUP BY vc.character_id,COALESCE(ca.primary_engine,'UNCLASSIFIED')
            """)
        .query(
            (rs, ignored) -> {
              UUID characterId = rs.getObject("character_id", UUID.class);
              byCharacter
                  .computeIfAbsent(characterId, unused -> new LinkedHashMap<>())
                  .put(normalizeFormat(rs.getString("format")), rs.getLong("observations"));
              return characterId;
            })
        .list();
    return canonical.stream()
        .map(
            character -> {
              Map<String, Long> formats = byCharacter.getOrDefault(character.id(), Map.of());
              long total = formats.values().stream().mapToLong(Long::longValue).sum();
              return new CharacterCoverageView(
                  character.id(),
                  character.name(),
                  character.status(),
                  total,
                  formats,
                  confidence(total));
            })
        .toList();
  }

  private String normalizeFormat(String value) {
    return value.trim().toUpperCase().replace(' ', '_').replace('-', '_');
  }

  private String confidence(long observations) {
    if (observations == 0) return "NO_DATA";
    if (observations < 10) return "LOW";
    if (observations < 30) return "MEDIUM";
    return "HIGH";
  }

  private CharacterView map(CharacterEntity item) {
    return new CharacterView(
        item.getId(), item.getName(), item.getStatus(), item.getNotes(), item.isActive());
  }

  public record CharacterView(
      UUID id, String name, CharacterStatus status, String notes, boolean active) {}

  public record CharacterCoverageView(
      UUID id,
      String name,
      CharacterStatus status,
      long observations,
      Map<String, Long> formatObservations,
      String confidence) {}
}
