package com.pompomhills.intelligence.content;

import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.api.VideoDtos.PromptFile;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

/** Minimal local content/prompt workspace over the existing canonical tables. */
@RestController
@RequestMapping("/api/v1/intelligence/contents")
public class ContentWorkspaceController {
  private final JdbcClient jdbc;
  private final VideoService videos;
  private final MediaContentService media;
  @org.springframework.beans.factory.annotation.Autowired
  private com.pompomhills.intelligence.workflow.WorkflowService optimizationWorkflow;

  public ContentWorkspaceController(
      JdbcClient jdbc, VideoService videos, MediaContentService media) {
    this.jdbc = jdbc;
    this.videos = videos;
    this.media = media;
  }

  @GetMapping
  public List<ContentSummary> list() {
    return jdbc.sql(
            """
            SELECT c.id,c.title,c.description,c.type,c.status,c.created_at,c.updated_at,
                   pv.id latest_prompt_version_id,pv.version_number latest_prompt_version_number
            FROM contents c
            LEFT JOIN LATERAL (
              SELECT id,version_number FROM prompt_versions WHERE content_id=c.id
              ORDER BY version_number DESC LIMIT 1
            ) pv ON true ORDER BY c.updated_at DESC, c.id DESC
            """)
        .query(
            (rs, ignored) ->
                new ContentSummary(
                    rs.getLong("id"),
                    rs.getString("title"),
                    rs.getString("description"),
                    rs.getString("type"),
                    rs.getString("status"),
                    rs.getObject("created_at", java.sql.Timestamp.class).toInstant(),
                    rs.getObject("updated_at", java.sql.Timestamp.class).toInstant(),
                    nullableLong(rs, "latest_prompt_version_id"),
                    nullableInt(rs, "latest_prompt_version_number")))
        .list();
  }

  @GetMapping("/quality-summary")
  public List<PromptQualityRecord> qualitySummary() {
    return jdbc.sql(
            """
            SELECT c.id content_id,c.title,c.source_path,pv.id prompt_version_id,pv.version_number,
                   q.id validation_record_id,q.created_at analyzed_at,q.ruleset_version,q.overall_score,q.status,
                   q.report_json::jsonb->'preRenderAssessment'->>'creative_grade' creative_grade,
                   COALESCE(q.report_json::jsonb->'preRenderAssessment'->>'prompt_stage',q.report_json::jsonb->'preRenderAssessment'->>'readiness') readiness,
                   q.report_json::jsonb->'preRenderAssessment'->>'verdict' summary
            FROM contents c
            LEFT JOIN LATERAL (SELECT id,version_number,raw_text FROM prompt_versions WHERE content_id=c.id ORDER BY version_number DESC LIMIT 1) pv ON true
            LEFT JOIN LATERAL (
              SELECT id,created_at,ruleset_version,overall_score,status,report_json FROM quality_validations
              WHERE ((content_id=c.id AND prompt_version_id=pv.id) OR prompt_text=pv.raw_text)
              ORDER BY id DESC LIMIT 1
            ) q ON true
            ORDER BY c.updated_at DESC,c.id DESC
            """)
        .query(
            (rs, ignored) ->
                new PromptQualityRecord(
                    rs.getLong("content_id"),
                    rs.getString("title"),
                    rs.getString("source_path"),
                    nullableLong(rs, "prompt_version_id"),
                    nullableInt(rs, "version_number"),
                    nullableQualitySummary(rs)))
        .list();
  }

  private PromptQualitySummary nullableQualitySummary(java.sql.ResultSet rs)
      throws java.sql.SQLException {
    Long validationId = nullableLong(rs, "validation_record_id");
    if (validationId == null) return null;
    java.sql.Timestamp timestamp = rs.getTimestamp("analyzed_at");
    java.math.BigDecimal score = rs.getBigDecimal("overall_score");
    return new PromptQualitySummary(
        validationId,
        timestamp == null ? null : timestamp.toInstant(),
        rs.getString("ruleset_version"),
        score == null ? null : score.doubleValue(),
        rs.getString("status"),
        rs.getString("creative_grade"),
        rs.getString("readiness"),
        rs.getString("summary"));
  }

  @PostMapping
  public ContentSummary create(@RequestBody CreateContentRequest request) {
    if (request.title() == null || request.title().isBlank())
      throw new IllegalArgumentException("title is required");
    String type = request.type() == null ? "SHORT" : request.type().toUpperCase();
    if (!List.of("EPISODE", "SHORT", "REEL").contains(type))
      throw new IllegalArgumentException("type must be EPISODE, SHORT, or REEL");
    Long id =
        jdbc.sql(
                """
                INSERT INTO contents(title,description,type,status,created_at,updated_at)
                VALUES (:title,:description,CAST(:type AS content_type),'DRAFT',now(),now()) RETURNING id
                """)
            .param("title", request.title().trim())
            .param("description", request.description())
            .param("type", type)
            .query(Long.class)
            .single();
    return get(id);
  }

  @GetMapping("/{contentId}")
  public ContentSummary get(@PathVariable Long contentId) {
    return jdbc.sql(
            """
            SELECT c.id,c.title,c.description,c.type,c.status,c.created_at,c.updated_at,
                   pv.id latest_prompt_version_id,pv.version_number latest_prompt_version_number
            FROM contents c LEFT JOIN LATERAL (
              SELECT id,version_number FROM prompt_versions WHERE content_id=c.id
              ORDER BY version_number DESC LIMIT 1
            ) pv ON true WHERE c.id=:id
            """)
        .param("id", contentId)
        .query(
            (rs, ignored) ->
                new ContentSummary(
                    rs.getLong("id"),
                    rs.getString("title"),
                    rs.getString("description"),
                    rs.getString("type"),
                    rs.getString("status"),
                    rs.getObject("created_at", java.sql.Timestamp.class).toInstant(),
                    rs.getObject("updated_at", java.sql.Timestamp.class).toInstant(),
                    nullableLong(rs, "latest_prompt_version_id"),
                    nullableInt(rs, "latest_prompt_version_number")))
        .optional()
        .orElseThrow(() -> new IllegalArgumentException("content not found: " + contentId));
  }

  @GetMapping("/{contentId}/prompt-versions")
  public List<PromptVersionSummary> prompts(@PathVariable Long contentId) {
    return jdbc.sql(
            "SELECT"
                + " id,content_id,version_number,raw_text,parsed_ir,source_path,source_sha256,created_at"
                + " FROM prompt_versions WHERE content_id=:id ORDER BY version_number DESC")
        .param("id", contentId)
        .query(
            (rs, ignored) ->
                new PromptVersionSummary(
                    rs.getLong("id"),
                    rs.getLong("content_id"),
                    rs.getInt("version_number"),
                    rs.getString("raw_text"),
                    rs.getString("parsed_ir"),
                    rs.getString("source_path"),
                    rs.getString("source_sha256"),
                    rs.getObject("created_at", java.sql.Timestamp.class).toInstant()))
        .list();
  }

  @GetMapping("/prompt-library")
  public List<PromptLibraryItem> promptLibrary(@RequestParam String sourceDirectory) {
    return jdbc.sql(
            """
            SELECT c.id content_id,c.title,pv.id prompt_version_id,pv.version_number,pv.raw_text,pv.source_path
            FROM contents c JOIN prompt_versions pv ON pv.content_id=c.id
            WHERE c.source_path LIKE :prefix || '/%'
              AND pv.version_number=(SELECT MAX(latest.version_number) FROM prompt_versions latest WHERE latest.content_id=c.id)
            ORDER BY c.source_path
            """)
        .param("prefix", sourceDirectory.replaceAll("/+$", ""))
        .query(
            (rs, ignored) ->
                new PromptLibraryItem(
                    rs.getLong("content_id"),
                    rs.getString("title"),
                    rs.getLong("prompt_version_id"),
                    rs.getInt("version_number"),
                    rs.getString("raw_text"),
                    rs.getString("source_path")))
        .list();
  }

  @PostMapping("/{contentId}/prompt-versions")
  @ResponseStatus(HttpStatus.CREATED)
  @Transactional
  public PromptVersionSummary createPrompt(
      @PathVariable Long contentId, @RequestBody CreatePromptRequest request) {
    if (request.rawText() == null || request.rawText().isBlank())
      throw new IllegalArgumentException("rawText is required");
    jdbc.sql("SELECT id FROM contents WHERE id=:id FOR UPDATE")
        .param("id", contentId)
        .query(Long.class)
        .optional()
        .orElseThrow(() -> new IllegalArgumentException("content not found: " + contentId));
    String sourcePath = null;
    String parentPromptText = null;
    if (request.parentPromptVersionId() != null) {
      var parent =
          jdbc.sql(
                  "SELECT source_path,raw_text FROM prompt_versions WHERE id=:parent AND"
                      + " content_id=:content")
              .param("parent", request.parentPromptVersionId())
              .param("content", contentId)
              .query((rs, ignored) -> new PromptParent(rs.getString("source_path"), rs.getString("raw_text")))
              .optional()
              .orElseThrow(
                  () -> new IllegalArgumentException("Parent version does not belong to content"));
      sourcePath = parent.sourcePath();
      parentPromptText = parent.rawText();
    }
    java.util.UUID roleId =
        request.creativeRoleRecordId() == null
            ? null
            : java.util.UUID.fromString(request.creativeRoleRecordId());
    boolean optimizationApproval = request.candidateId() != null;
    if (optimizationApproval) {
      if (roleId == null || request.optimizationComparisonId() == null
          || !Boolean.TRUE.equals(request.operatorApproved())
          || request.parentPromptVersionId() == null || parentPromptText == null)
        throw new IllegalArgumentException("Explicit candidate approval and source provenance are required");
      var comparisonSource =
          jdbc.sql(
                  "SELECT payload->>'sourceAnalysisId' FROM post_family_workflow_events"
                      + " WHERE id=CAST(:comparison AS uuid) AND kind='CREATIVE_OPTIMIZATION'"
                      + " AND payload->>'roleRecordId'=:role")
              .param("comparison", request.optimizationComparisonId())
              .param("role", roleId.toString())
              .query(String.class)
              .optional()
              .orElseThrow(() -> new IllegalArgumentException("Optimization comparison provenance is unavailable"));
      var approvedCandidate =
          jdbc.sql(
                  "SELECT c->>'prompt' FROM post_family_workflow_events role_event"
                      + " CROSS JOIN LATERAL jsonb_array_elements(role_event.payload->'result'->'candidates') c"
                      + " WHERE role_event.id=:role AND role_event.kind='CREATIVE_ROLE'"
                      + " AND role_event.payload->>'role'='PROMPT_OPTIMIZATION'"
                      + " AND c->>'candidateId'=:candidate"
                      + " AND role_event.payload->'sourceRequest'->'context'->>'analysisRunId'=:analysis"
                      + " AND role_event.payload->'sourceRequest'->'context'->>'contentId'=:content"
                      + " AND role_event.payload->'sourceRequest'->'context'->>'promptVersionId'=:parent")
              .param("role", roleId)
              .param("candidate", request.candidateId())
              .param("analysis", comparisonSource)
              .param("content", contentId.toString())
              .param("parent", request.parentPromptVersionId().toString())
              .query(String.class)
              .optional()
              .orElseThrow(() -> new IllegalArgumentException("Candidate does not match its saved optimization source"));
      if (!request.rawText().equals(approvedCandidate))
        throw new IllegalArgumentException("Approved prompt text must match the exact selected candidate");

      var comparison =
          jdbc.sql(
                  "SELECT EXISTS(SELECT 1 FROM post_family_workflow_events e"
                      + " CROSS JOIN LATERAL jsonb_array_elements(e.payload->'candidates') c"
                      + " WHERE e.id=CAST(:comparison AS uuid) AND e.kind='CREATIVE_OPTIMIZATION'"
                      + " AND e.payload->>'roleRecordId'=:role"
                      + " AND e.payload->>'sourcePromptVersionId'=:parent"
                      + " AND e.payload->>'sourceAnalysisId'=:analysis"
                      + " AND e.payload->>'sourcePromptSha256'=:sourceHash"
                      + " AND c->>'candidateId'=:candidate AND c->>'prompt'=:text"
                      + " AND c->'fidelity'->>'essentialEventsPreserved'='true'"
                      + " AND c->'review'->'canonicalRuleEvaluation'->>'rulesetVersion'=e.payload->>'rulesetVersion')")
              .param("comparison", request.optimizationComparisonId())
              .param("role", roleId.toString())
              .param("analysis", comparisonSource)
              .param("parent", request.parentPromptVersionId().toString())
              .param("sourceHash", sha256(parentPromptText))
              .param("candidate", request.candidateId())
              .param("text", request.rawText())
              .query(Boolean.class)
              .single();
      if (!comparison)
        throw new IllegalArgumentException("Candidate comparison is stale or its validation is incomplete");
      var latestAnalysis =
          jdbc.sql(
                  "SELECT id::text FROM post_family_workflow_events WHERE kind='REVIEW'"
                      + " AND payload->>'contentId'=:content ORDER BY created_at DESC,id DESC LIMIT 1")
              .param("content", contentId.toString())
              .query(String.class)
              .optional()
              .orElse("");
      if (!latestAnalysis.equals(comparisonSource))
        throw new IllegalStateException("Candidate analysis is stale; revalidate before approval");
      if (optimizationWorkflow == null) throw new IllegalStateException("Current candidate approval validation is unavailable");
      optimizationWorkflow.requireCurrentOptimizationApproval(
          java.util.UUID.fromString(request.optimizationComparisonId()), request.candidateId(), request.rawText());

      var existingVersion =
          jdbc.sql(
                  "SELECT id FROM prompt_versions WHERE content_id=:content"
                      + " AND parsed_ir->'creativeOptimizationProvenance'->>'comparisonId'=:comparison"
                      + " AND parsed_ir->'creativeOptimizationProvenance'->>'candidateId'=:candidate")
              .param("content", contentId)
              .param("comparison", request.optimizationComparisonId())
              .param("candidate", request.candidateId())
              .query(Long.class)
              .optional();
      if (existingVersion.isPresent()) {
        var existing = prompts(contentId).stream()
            .filter(item -> item.id().equals(existingVersion.get()))
            .findFirst()
            .orElseThrow();
        if (!request.rawText().equals(existing.rawText()))
          throw new IllegalArgumentException("This approved candidate already has a different immutable version");
        return existing;
      }
    } else if (request.optimizationComparisonId() != null || Boolean.TRUE.equals(request.operatorApproved())) {
      throw new IllegalArgumentException("Candidate approval metadata is incomplete");
    }
    if (roleId == null && request.parentPromptVersionId() != null)
      roleId =
          jdbc.sql(
                  "SELECT creative_role_record_id FROM prompt_creative_provenance WHERE"
                      + " prompt_version_id=:parent")
              .param("parent", request.parentPromptVersionId())
              .query(java.util.UUID.class)
              .optional()
              .orElse(null);
    CreativePromptSource roleSource = null;
    if (roleId != null && optimizationApproval)
      roleSource = new CreativePromptSource(request.rawText(), false);
    else if (roleId != null)
      roleSource =
          jdbc.sql(
                  "SELECT payload->'result'->>'prompt' prompt, "
                      + "COALESCE(payload->'result'->'productionPlan'->>'promptTextEdited','false')='true' edited "
                      + "FROM post_family_workflow_events WHERE id=:id AND kind='CREATIVE_ROLE' AND payload->>'role'='BUILD_PROMPT'")
              .param("id", roleId)
              .query((rs, ignored) -> new CreativePromptSource(rs.getString("prompt"), rs.getBoolean("edited")))
              .optional()
              .filter(value -> value.rawText() != null && !value.rawText().isBlank())
              .orElseThrow(() -> new IllegalArgumentException("Draft provenance requires a saved BUILD_PROMPT record"));
    String optimizationProvenance = "{}";
    if (optimizationApproval) {
      try {
        optimizationProvenance =
            new com.fasterxml.jackson.databind.ObjectMapper()
                .writeValueAsString(java.util.Map.of(
                    "creativeOptimizationProvenance",
                    java.util.Map.of(
                        "comparisonId", request.optimizationComparisonId(),
                        "candidateId", request.candidateId(),
                        "roleRecordId", roleId.toString(),
                        "sourceAnalysisId",
                            jdbc.sql(
                                    "SELECT payload->>'sourceAnalysisId' FROM post_family_workflow_events"
                                        + " WHERE id=CAST(:comparison AS uuid) AND kind='CREATIVE_OPTIMIZATION'")
                                .param("comparison", request.optimizationComparisonId())
                                .query(String.class)
                                .single(),
                        "operatorApproved", true)));
      } catch (com.fasterxml.jackson.core.JsonProcessingException error) {
        throw new IllegalStateException("Cannot preserve optimization approval provenance", error);
      }
    }
    Integer version =
        jdbc.sql(
                "SELECT COALESCE(MAX(version_number),0)+1 FROM prompt_versions WHERE"
                    + " content_id=:id")
            .param("id", contentId)
            .query(Integer.class)
            .single();
    Long id =
        jdbc.sql(
                "INSERT INTO"
                    + " prompt_versions(content_id,version_number,raw_text,parsed_ir,source_path,parent_prompt_version_id,created_at)"
                    + " VALUES (:content,:version,:text,CAST(:parsed AS jsonb) ||"
                    + " CASE WHEN :optimization THEN CAST(:provenance AS jsonb) ||"
                    + " jsonb_build_object('creativeOptimizationProvenance',"
                    + " (CAST(:provenance AS jsonb)->'creativeOptimizationProvenance') ||"
                    + " jsonb_build_object('approvedAt',now())) ELSE '{}'::jsonb END,"
                    + " :source,:parent,now()) RETURNING id")
            .param("content", contentId)
            .param("version", version)
            .param("text", request.rawText())
            .param("optimization", optimizationApproval)
            .param("provenance", optimizationProvenance)
            .param("source", sourcePath, java.sql.Types.VARCHAR)
            .param("parent", request.parentPromptVersionId(), java.sql.Types.BIGINT)
            .param("parsed", request.parsedIr() == null ? "{}" : request.parsedIr())
            .query(Long.class)
            .single();
    if (roleId != null)
      jdbc.sql(
              "INSERT INTO"
                  + " prompt_creative_provenance(prompt_version_id,creative_role_record_id,operator_edited)"
                  + " VALUES (:version,:role,:edited)")
          .param("version", id)
          .param("role", roleId)
          .param("edited", roleSource.operatorEdited() || !request.rawText().equals(roleSource.rawText()))
          .update();
    return prompts(contentId).stream()
        .filter(item -> item.id().equals(id))
        .findFirst()
        .orElseThrow();
  }

  @GetMapping("/{contentId}/prompt-versions/{promptVersionId}/videos")
  public List<java.util.Map<String, Object>> linkedVideos(
      @PathVariable Long contentId, @PathVariable Long promptVersionId) {
    if (jdbc.sql("SELECT count(*) FROM prompt_versions WHERE id=:prompt AND content_id=:content")
            .param("prompt", promptVersionId)
            .param("content", contentId)
            .query(Long.class)
            .single()
        == 0) throw new IllegalArgumentException("Prompt version does not belong to content");
    return jdbc.sql(
            """
            SELECT DISTINCT v.id,v.relative_path FROM videos v WHERE
              EXISTS(SELECT 1 FROM render_assets ra JOIN render_jobs rj ON rj.id=ra.render_job_id WHERE ra.relative_path=v.relative_path AND ra.asset_type='VIDEO' AND rj.prompt_version_id=:prompt AND rj.content_id=:content)
              OR EXISTS(SELECT 1 FROM video_prompt_links l WHERE l.id=(SELECT max(id) FROM video_prompt_links WHERE video_id=v.id) AND l.origin='ORIGINAL' AND l.video_hash=v.content_hash AND l.prompt_version_id=:prompt)
            ORDER BY v.relative_path
            """)
        .param("prompt", promptVersionId)
        .param("content", contentId)
        .query(
            (rs, ignored) ->
                java.util.Map.<String, Object>of(
                    "videoId",
                    rs.getString("id"),
                    "relativePath",
                    rs.getString("relative_path"),
                    "promptVersionId",
                    promptVersionId))
        .list();
  }

  @PostMapping("/{contentId}/source-alias")
  @Transactional
  public java.util.Map<String, Object> reconcileSourcePath(
      @PathVariable Long contentId, @RequestBody SourceAliasRequest request) {
    if (request.relativePath() == null
        || request.reason() == null
        || request.reason().isBlank()
        || request.promptVersionId() == null)
      throw new IllegalArgumentException(
          "Exact saved prompt, new relative path and reason required");
    var content =
        jdbc.sql("SELECT source_path FROM contents WHERE id=:id FOR UPDATE")
            .param("id", contentId)
            .query((rs, ignored) -> new PromptParent(rs.getString("source_path"), null))
            .optional()
            .orElseThrow(() -> new IllegalArgumentException("Content not found"));
    var source =
        jdbc.sql("SELECT raw_text FROM prompt_versions WHERE id=:id AND content_id=:content")
            .param("id", request.promptVersionId())
            .param("content", contentId)
            .query(String.class)
            .optional()
            .orElseThrow(() -> new IllegalArgumentException("Prompt does not belong to content"));
    if (java.nio.file.Path.of(request.relativePath()).isAbsolute())
      throw new IllegalArgumentException("Source path must be relative");
    String path = java.nio.file.Path.of(request.relativePath()).normalize().toString();
    String hash = sha256(media.readMetadata(path));
    if (!hash.equals(sha256(source)))
      throw new IllegalArgumentException(
          "New path bytes do not match the selected immutable prompt snapshot");
    var owner =
        jdbc.sql(
                "SELECT id FROM contents WHERE source_path=:path UNION SELECT content_id FROM"
                    + " content_source_path_aliases WHERE source_path=:path")
            .param("path", path)
            .query(Long.class)
            .list();
    if (owner.stream().anyMatch(id -> !id.equals(contentId)))
      throw new IllegalArgumentException("Path already belongs to another content");
    for (String alias :
        java.util.stream.Stream.of(content.sourcePath(), path)
            .filter(java.util.Objects::nonNull)
            .distinct()
            .toList()) {
      jdbc.sql(
              "INSERT INTO content_source_path_aliases(source_path,content_id,source_sha256,reason)"
                  + " VALUES (:path,:content,:hash,:reason) ON CONFLICT(source_path) DO NOTHING")
          .param("path", alias)
          .param("content", contentId)
          .param("hash", hash)
          .param("reason", request.reason())
          .update();
    }
    jdbc.sql("UPDATE contents SET source_path=:path,updated_at=now() WHERE id=:id")
        .param("id", contentId)
        .param("path", path)
        .update();
    return java.util.Map.of(
        "contentId",
        contentId,
        "promptVersionId",
        request.promptVersionId(),
        "sourcePath",
        path,
        "sourceSha256",
        hash,
        "historicalVersionsPreserved",
        true);
  }

  public record SourceAliasRequest(Long promptVersionId, String relativePath, String reason) {}

  @PostMapping("/import-folder")
  @Transactional
  public PromptImportResponse importFolder(@RequestBody ImportFolderRequest request) {
    if (request.relativeDirectory() == null || request.relativeDirectory().isBlank()) {
      throw new IllegalArgumentException("relativeDirectory is required");
    }
    List<PromptFile> files = videos.promptFiles(request.relativeDirectory());
    int imported = 0;
    int unchanged = 0;
    for (PromptFile file : files) {
      String rawText = media.readMetadata(file.relativePath());
      String hash = sha256(rawText);
      Long contentId =
          jdbc.sql("SELECT id FROM contents WHERE source_path=:source")
              .param("source", file.relativePath())
              .query(Long.class)
              .optional()
              .orElse(null);
      if (contentId == null)
        contentId =
            jdbc.sql("SELECT content_id FROM content_source_path_aliases WHERE source_path=:path")
                .param("path", file.relativePath())
                .query(Long.class)
                .optional()
                .orElse(null);
      if (contentId == null) {
        contentId =
            jdbc.sql(
                    """
                    INSERT INTO contents(title,description,type,status,source_path,created_at,updated_at)
                    VALUES (:title,:description,CAST(:type AS content_type),'DRAFT',:source,now(),now()) RETURNING id
                    """)
                .param("title", titleFromFolder(file.folder()))
                .param("description", "Imported from mounted library: " + file.relativePath())
                .param("type", contentType(file.relativePath()))
                .param("source", file.relativePath())
                .query(Long.class)
                .single();
      }
      Integer already =
          jdbc.sql(
                  "SELECT COUNT(*) FROM prompt_versions WHERE content_id=:content AND"
                      + " source_path=:source AND source_sha256=:hash")
              .param("content", contentId)
              .param("source", file.relativePath())
              .param("hash", hash)
              .query(Integer.class)
              .single();
      if (already > 0) {
        unchanged++;
        continue;
      }
      Integer version =
          jdbc.sql(
                  "SELECT COALESCE(MAX(version_number),0)+1 FROM prompt_versions WHERE"
                      + " content_id=:id")
              .param("id", contentId)
              .query(Integer.class)
              .single();
      jdbc.sql(
              """
              INSERT INTO prompt_versions(content_id,version_number,raw_text,parsed_ir,source_path,source_sha256,created_at)
              VALUES (:content,:version,:text,CAST('{}' AS jsonb),:source,:hash,now())
              """)
          .param("content", contentId)
          .param("version", version)
          .param("text", rawText)
          .param("source", file.relativePath())
          .param("hash", hash)
          .update();
      jdbc.sql("UPDATE contents SET updated_at=now() WHERE id=:id").param("id", contentId).update();
      imported++;
    }
    return new PromptImportResponse(request.relativeDirectory(), files.size(), imported, unchanged);
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  private Integer nullableInt(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    int value = rs.getInt(column);
    return rs.wasNull() ? null : value;
  }

  public record CreateContentRequest(String title, String description, String type) {}

  private record PromptParent(String sourcePath, String rawText) {}

  @GetMapping("/{contentId}/prompt-versions/{promptVersionId}/creative-provenance")
  public java.util.Map<String, Object> creativeProvenance(
      @PathVariable Long contentId, @PathVariable Long promptVersionId) {
    jdbc.sql("SELECT id FROM prompt_versions WHERE id=:prompt AND content_id=:content")
        .param("prompt", promptVersionId)
        .param("content", contentId)
        .query(Long.class)
        .optional()
        .orElseThrow(
            () -> new IllegalArgumentException("Prompt version does not belong to content"));
    return jdbc.sql(
            """
            SELECT e.id,e.payload->>'role' role,e.payload->>'provider' provider,e.payload->>'model' model,
                   e.payload->>'sourceStoryRecordId' story,p.operator_edited,
                   e.payload->'sourceRequest'->>'text' approved_story,
                   e.payload->'sourceRequest'->'context'->>'storyRevisionId' story_revision,
                   e.payload->'sourceRequest'->'context'->>'candidateId' candidate,
                   e.payload->'sourceRequest'->'context'->>'approvalRecordId' approval,
                   COALESCE(e.payload->'result'->'productionPlan'->>'promptTextEdited','false')='true' plan_edited,
                   (pv.parsed_ir->'creativeOptimizationProvenance')::text optimization_provenance
            FROM prompt_creative_provenance p JOIN prompt_versions pv ON pv.id=p.prompt_version_id
            JOIN post_family_workflow_events e ON e.id=p.creative_role_record_id
            WHERE pv.content_id=:content AND pv.id=:prompt
            """)
        .param("content", contentId)
        .param("prompt", promptVersionId)
        .query(
            (rs, index) -> {
              java.util.Map<String, Object> value = new java.util.LinkedHashMap<>();
              boolean optimization = "PROMPT_OPTIMIZATION".equals(rs.getString("role"));
              value.put("origin", optimization ? "PROMPT_OPTIMIZATION" : "BUILD_PROMPT");
              value.put("creativeRoleRecordId", rs.getObject("id").toString());
              value.put("provider", rs.getString("provider"));
              value.put("model", rs.getString("model"));
              boolean edited = rs.getBoolean("operator_edited");
              value.put("operatorEdited", edited);
              if (optimization) {
                value.put(
                    "creativeOptimizationProvenance",
                    parseOptimizationProvenance(rs.getString("optimization_provenance")));
              } else {
                value.put("sourceStoryRecordId", rs.getString("story"));
                value.put("approvedStoryText", rs.getString("approved_story"));
                value.put("storyRevisionId", rs.getString("story_revision"));
                value.put("candidateId", rs.getString("candidate"));
                value.put("approvalRecordId", rs.getString("approval"));
                value.put("promptTextEdited", rs.getBoolean("plan_edited") || edited);
                value.put(
                    "productionSpecificationStatus",
                    edited || rs.getBoolean("plan_edited") ? "STALE" : "NOT_VALIDATED");
              }
              value.put("validationStatus", "NOT_VALIDATED");
              return value;
            })
        .optional()
        .orElseGet(() -> java.util.Map.of("origin", "MANUAL_OR_LEGACY"));
  }

  private static Map<String, Object> parseOptimizationProvenance(String json) {
    if (json == null || json.isBlank()) return Map.of();
    try {
      return new com.fasterxml.jackson.databind.ObjectMapper()
          .readValue(
              json,
              new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
    } catch (com.fasterxml.jackson.core.JsonProcessingException error) {
      throw new IllegalStateException("Saved creative optimization provenance is invalid", error);
    }
  }

  private record CreativePromptSource(String rawText, boolean operatorEdited) {}

  public record CreatePromptRequest(
      String rawText,
      String parsedIr,
      Long parentPromptVersionId,
      String creativeRoleRecordId,
      String candidateId,
      String optimizationComparisonId,
      Boolean operatorApproved) {
    public CreatePromptRequest(String rawText, String parsedIr, Long parentPromptVersionId) {
      this(rawText, parsedIr, parentPromptVersionId, null, null, null, null);
    }

    public CreatePromptRequest(
        String rawText, String parsedIr, Long parentPromptVersionId, String creativeRoleRecordId) {
      this(rawText, parsedIr, parentPromptVersionId, creativeRoleRecordId, null, null, null);
    }
  }

  public record ImportFolderRequest(String relativeDirectory) {}

  public record PromptImportResponse(
      String relativeDirectory, int discovered, int imported, int unchanged) {}

  public record ContentSummary(
      Long id,
      String title,
      String description,
      String type,
      String status,
      java.time.Instant createdAt,
      java.time.Instant updatedAt,
      Long latestPromptVersionId,
      Integer latestPromptVersionNumber) {}

  public record PromptVersionSummary(
      Long id,
      Long contentId,
      Integer versionNumber,
      String rawText,
      String parsedIr,
      String sourcePath,
      String sourceSha256,
      java.time.Instant createdAt) {}

  public record PromptLibraryItem(
      Long contentId,
      String title,
      Long promptVersionId,
      Integer versionNumber,
      String rawText,
      String sourcePath) {}

  public record PromptQualityRecord(
      Long contentId,
      String title,
      String sourcePath,
      Long promptVersionId,
      Integer versionNumber,
      PromptQualitySummary latestQuality) {}

  public record PromptQualitySummary(
      Long validationRecordId,
      java.time.Instant analyzedAt,
      String rulesetVersion,
      Double overallScore,
      String status,
      String creativeGrade,
      String readiness,
      String summary) {}

  private String titleFromFolder(String folder) {
    String name =
        folder.substring(folder.lastIndexOf('/') + 1).replace('_', ' ').replace('-', ' ').trim();
    return name.isBlank() ? "Imported Pompom Prompt" : name;
  }

  private String contentType(String path) {
    String upper = path.toUpperCase(java.util.Locale.ROOT);
    return upper.contains("SOCIAL_REELS")
        ? "REEL"
        : upper.contains("EPISODE_PACKAGES") ? "EPISODE" : "SHORT";
  }

  private String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("SHA-256 is unavailable", error);
    }
  }
}
