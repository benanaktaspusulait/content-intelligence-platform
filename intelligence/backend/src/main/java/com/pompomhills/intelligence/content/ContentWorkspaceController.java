package com.pompomhills.intelligence.content;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.*;

/** Minimal local content/prompt workspace over the existing canonical tables. */
@RestController
@RequestMapping("/api/v1/intelligence/contents")
public class ContentWorkspaceController {
  private final JdbcClient jdbc;

  public ContentWorkspaceController(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @GetMapping
  public List<ContentSummary> list() {
    return jdbc.sql("""
        SELECT c.id,c.title,c.description,c.type,c.status,c.created_at,c.updated_at,
               pv.id latest_prompt_version_id,pv.version_number latest_prompt_version_number
        FROM contents c
        LEFT JOIN LATERAL (
          SELECT id,version_number FROM prompt_versions WHERE content_id=c.id
          ORDER BY version_number DESC LIMIT 1
        ) pv ON true ORDER BY c.updated_at DESC, c.id DESC
        """).query((rs, ignored) -> new ContentSummary(
        rs.getLong("id"), rs.getString("title"), rs.getString("description"),
        rs.getString("type"), rs.getString("status"),
        rs.getObject("created_at", java.sql.Timestamp.class).toInstant(),
        rs.getObject("updated_at", java.sql.Timestamp.class).toInstant(),
        nullableLong(rs, "latest_prompt_version_id"), nullableInt(rs, "latest_prompt_version_number"))).list();
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public ContentSummary create(@RequestBody CreateContentRequest request) {
    if (request.title() == null || request.title().isBlank()) throw new IllegalArgumentException("title is required");
    String type = request.type() == null ? "SHORT" : request.type().toUpperCase();
    if (!List.of("EPISODE", "SHORT", "REEL").contains(type)) throw new IllegalArgumentException("type must be EPISODE, SHORT, or REEL");
    Long id = jdbc.sql("""
        INSERT INTO contents(title,description,type,status,created_at,updated_at)
        VALUES (:title,:description,CAST(:type AS content_type),'DRAFT',now(),now()) RETURNING id
        """).param("title", request.title().trim()).param("description", request.description()).param("type", type).query(Long.class).single();
    return get(id);
  }

  @GetMapping("/{contentId}")
  public ContentSummary get(@PathVariable Long contentId) {
    return jdbc.sql("""
        SELECT c.id,c.title,c.description,c.type,c.status,c.created_at,c.updated_at,
               pv.id latest_prompt_version_id,pv.version_number latest_prompt_version_number
        FROM contents c LEFT JOIN LATERAL (
          SELECT id,version_number FROM prompt_versions WHERE content_id=c.id
          ORDER BY version_number DESC LIMIT 1
        ) pv ON true WHERE c.id=:id
        """).param("id", contentId).query((rs, ignored) -> new ContentSummary(
        rs.getLong("id"), rs.getString("title"), rs.getString("description"), rs.getString("type"), rs.getString("status"),
        rs.getObject("created_at", java.sql.Timestamp.class).toInstant(), rs.getObject("updated_at", java.sql.Timestamp.class).toInstant(),
        nullableLong(rs, "latest_prompt_version_id"), nullableInt(rs, "latest_prompt_version_number"))).optional().orElseThrow(() -> new IllegalArgumentException("content not found: " + contentId));
  }

  @GetMapping("/{contentId}/prompt-versions")
  public List<PromptVersionSummary> prompts(@PathVariable Long contentId) {
    return jdbc.sql("SELECT id,content_id,version_number,raw_text,parsed_ir,created_at FROM prompt_versions WHERE content_id=:id ORDER BY version_number DESC")
        .param("id", contentId).query((rs, ignored) -> new PromptVersionSummary(rs.getLong("id"), rs.getLong("content_id"), rs.getInt("version_number"), rs.getString("raw_text"), rs.getString("parsed_ir"), rs.getObject("created_at", java.sql.Timestamp.class).toInstant())).list();
  }

  @PostMapping("/{contentId}/prompt-versions")
  @ResponseStatus(HttpStatus.CREATED)
  public PromptVersionSummary createPrompt(@PathVariable Long contentId, @RequestBody CreatePromptRequest request) {
    if (request.rawText() == null || request.rawText().isBlank()) throw new IllegalArgumentException("rawText is required");
    jdbc.sql("SELECT id FROM contents WHERE id=:id").param("id", contentId).query(Long.class).optional().orElseThrow(() -> new IllegalArgumentException("content not found: " + contentId));
    Integer version = jdbc.sql("SELECT COALESCE(MAX(version_number),0)+1 FROM prompt_versions WHERE content_id=:id").param("id", contentId).query(Integer.class).single();
    Long id = jdbc.sql("INSERT INTO prompt_versions(content_id,version_number,raw_text,parsed_ir,created_at) VALUES (:content,:version,:text,CAST(:parsed AS jsonb),now()) RETURNING id")
        .param("content", contentId).param("version", version).param("text", request.rawText()).param("parsed", request.parsedIr() == null ? "{}" : request.parsedIr()).query(Long.class).single();
    return prompts(contentId).stream().filter(item -> item.id().equals(id)).findFirst().orElseThrow();
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException { long value = rs.getLong(column); return rs.wasNull() ? null : value; }
  private Integer nullableInt(java.sql.ResultSet rs, String column) throws java.sql.SQLException { int value = rs.getInt(column); return rs.wasNull() ? null : value; }

  public record CreateContentRequest(String title, String description, String type) {}
  public record CreatePromptRequest(String rawText, String parsedIr) {}
  public record ContentSummary(Long id, String title, String description, String type, String status, java.time.Instant createdAt, java.time.Instant updatedAt, Long latestPromptVersionId, Integer latestPromptVersionNumber) {}
  public record PromptVersionSummary(Long id, Long contentId, Integer versionNumber, String rawText, String parsedIr, java.time.Instant createdAt) {}
}
