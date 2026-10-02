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
        screen_time_ratio=excluded.screen_time_ratio,action_share=excluded.action_share,speaking_share=excluded.speaking_share
        """)
        .param("video", videoId)
        .param("character", characterId)
        .param("participation", participation)
        .param("role", role)
        .param("screen", screenTimeRatio)
        .param("action", actionShare)
        .param("speaking", speakingShare)
        .update();
  }

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
