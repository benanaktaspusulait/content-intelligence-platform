package com.pompomhills.intelligence.experiment.api;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@RestController
@RequestMapping("/api/v1/experiments")
public class ExperimentController {
  private static final List<String> TYPES =
      List.of("EXPLOIT", "ADJACENT", "EXPLORE", "CHARACTER_CONTROL_TEST");
  private final JdbcClient jdbc;
  private final ObjectMapper json;

  public ExperimentController(JdbcClient jdbc, ObjectMapper json) {
    this.jdbc = jdbc;
    this.json = json;
  }

  @PostMapping
  ExperimentView create(@Valid @RequestBody CreateExperiment request) {
    String type = request.experimentType().toUpperCase();
    if (!TYPES.contains(type)) throw new IllegalArgumentException("Unsupported experiment type");
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO experiments
              (id,video_id,variant_id,platform,hypothesis,experiment_type,planned_publish_time,
               test_variables,notes,status)
            VALUES (:id,:video,:variant,:platform,:hypothesis,:type,:planned,
                    CAST(:variables AS jsonb),:notes,'PLANNED')
            """)
        .param("id", id)
        .param("video", request.videoId())
        .param("variant", request.variantId(), java.sql.Types.OTHER)
        .param("platform", request.platform().toLowerCase())
        .param("hypothesis", request.hypothesis())
        .param("type", type)
        .param("planned", request.plannedPublishTime(), java.sql.Types.TIMESTAMP_WITH_TIMEZONE)
        .param("variables", writeJson(request.testVariables()))
        .param("notes", request.notes(), java.sql.Types.VARCHAR)
        .update();
    return get(id);
  }

  @GetMapping
  List<ExperimentView> list() {
    return jdbc.sql(
            """
            SELECT id,video_id,platform,hypothesis,experiment_type,planned_publish_time,status
            FROM experiments ORDER BY created_at DESC
            """)
        .query((rs, ignored) -> view(rs))
        .list();
  }

  private ExperimentView get(UUID id) {
    return jdbc.sql(
            """
            SELECT id,video_id,platform,hypothesis,experiment_type,planned_publish_time,status
            FROM experiments WHERE id=:id
            """)
        .param("id", id)
        .query((rs, ignored) -> view(rs))
        .single();
  }

  private ExperimentView view(java.sql.ResultSet rs) throws java.sql.SQLException {
    var planned = rs.getObject("planned_publish_time", java.time.OffsetDateTime.class);
    return new ExperimentView(
        rs.getObject("id", UUID.class),
        rs.getObject("video_id", UUID.class),
        rs.getString("platform"),
        rs.getString("hypothesis"),
        rs.getString("experiment_type"),
        planned == null ? null : planned.toInstant(),
        rs.getString("status"));
  }

  private String writeJson(Object value) {
    try {
      return json.writeValueAsString(value == null ? Map.of() : value);
    } catch (JacksonException error) {
      throw new IllegalArgumentException("Invalid test variables", error);
    }
  }

  public record CreateExperiment(
      @NotNull UUID videoId,
      UUID variantId,
      @NotBlank String platform,
      @NotBlank String hypothesis,
      @NotBlank String experimentType,
      Instant plannedPublishTime,
      Map<String, Object> testVariables,
      String notes) {}

  public record ExperimentView(
      UUID id,
      UUID videoId,
      String platform,
      String hypothesis,
      String experimentType,
      Instant plannedPublishTime,
      String status) {}
}
