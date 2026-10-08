package com.pompomhills.intelligence.modelregistry.api;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@RestController
@RequestMapping("/api/v1/models")
public class ModelRegistryController {
  private final JdbcClient jdbc;
  private final ObjectMapper json;

  public ModelRegistryController(JdbcClient jdbc, ObjectMapper json) {
    this.jdbc = jdbc;
    this.json = json;
  }

  @GetMapping
  List<ModelView> list() {
    return jdbc.sql(
            """
            SELECT id,version,model_type,platform,training_dataset_version,feature_version,
                   knowledge_cutoff,metrics::text,artifact_path,status,trained_at
            FROM model_versions ORDER BY trained_at DESC
            """)
        .query((rs, ignored) -> map(rs))
        .list();
  }

  @PostMapping
  ModelView register(@Valid @RequestBody RegisterModel request) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO model_versions
              (id,version,model_type,platform,training_dataset_version,feature_version,
               knowledge_cutoff,metrics,artifact_path,status,trained_at)
            VALUES (:id,:version,:type,:platform,:dataset,:feature,:cutoff,
                    CAST(:metrics AS jsonb),:artifact,'CHALLENGER',:trained)
            """)
        .param("id", id)
        .param("version", request.version())
        .param("type", request.modelType())
        .param("platform", request.platform().toLowerCase())
        .param("dataset", request.trainingDatasetVersion())
        .param("feature", request.featureVersion())
        .param("cutoff", request.knowledgeCutoff())
        .param("metrics", writeJson(request.metrics()))
        .param("artifact", request.artifactPath(), java.sql.Types.VARCHAR)
        .param("trained", request.trainedAt())
        .update();
    return get(id);
  }

  @PostMapping("/{id}/promote")
  @Transactional
  ModelView promote(@PathVariable UUID id, @RequestBody(required = false) Promotion request) {
    ModelView challenger = get(id);
    if (!"CHALLENGER".equals(challenger.status())) {
      throw new IllegalStateException("Only a challenger can be promoted");
    }
    throw new org.springframework.web.server.ResponseStatusException(
        org.springframework.http.HttpStatus.NOT_IMPLEMENTED,
        "Promotion unavailable: artifact verification and registry-controlled inference are not connected; cold-start prediction remains active");
  }

  private ModelView get(UUID id) {
    return jdbc.sql(
            """
            SELECT id,version,model_type,platform,training_dataset_version,feature_version,
                   knowledge_cutoff,metrics::text,artifact_path,status,trained_at
            FROM model_versions WHERE id=:id
            """)
        .param("id", id)
        .query((rs, ignored) -> map(rs))
        .optional()
        .orElseThrow(() -> new IllegalArgumentException("Model version not found: " + id));
  }

  private ModelView map(java.sql.ResultSet rs) throws java.sql.SQLException {
    try {
      return new ModelView(
          rs.getObject("id", UUID.class),
          rs.getString("version"),
          rs.getString("model_type"),
          rs.getString("platform"),
          rs.getString("training_dataset_version"),
          rs.getString("feature_version"),
          rs.getObject("knowledge_cutoff", OffsetDateTime.class).toInstant(),
          json.readValue(rs.getString("metrics"), Map.class),
          rs.getString("artifact_path"),
          rs.getString("status"),
          rs.getObject("trained_at", OffsetDateTime.class).toInstant());
    } catch (JacksonException error) {
      throw new IllegalStateException("Stored model metrics are invalid", error);
    }
  }

  private String writeJson(Object value) {
    try {
      return json.writeValueAsString(value == null ? Map.of() : value);
    } catch (JacksonException error) {
      throw new IllegalArgumentException("Invalid metrics", error);
    }
  }

  public record RegisterModel(
      @NotBlank String version,
      @NotBlank String modelType,
      @NotBlank String platform,
      @NotBlank String trainingDatasetVersion,
      @NotBlank String featureVersion,
      @NotNull Instant knowledgeCutoff,
      Map<String, Object> metrics,
      String artifactPath,
      @NotNull Instant trainedAt) {}

  public record Promotion(String reason) {}

  public record ModelView(
      UUID id,
      String version,
      String modelType,
      String platform,
      String trainingDatasetVersion,
      String featureVersion,
      Instant knowledgeCutoff,
      Map<?, ?> metrics,
      String artifactPath,
      String status,
      Instant trainedAt) {}
}
