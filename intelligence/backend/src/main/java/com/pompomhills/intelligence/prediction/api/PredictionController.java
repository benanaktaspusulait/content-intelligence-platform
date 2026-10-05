package com.pompomhills.intelligence.prediction.api;

import com.pompomhills.intelligence.prediction.PredictionService;
import com.pompomhills.intelligence.prediction.PredictionDataReadinessService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/predictions")
public class PredictionController {
  private final PredictionService service;
  private final PredictionDataReadinessService readiness;
  private final JdbcClient jdbc;

  public PredictionController(PredictionService service, PredictionDataReadinessService readiness, JdbcClient jdbc) {
    this.service = service;
    this.readiness = readiness;
    this.jdbc = jdbc;
  }

  @GetMapping("/readiness")
  public List<PredictionDataReadinessService.Readiness> readiness() {
    return readiness.all();
  }

  @PostMapping
  public PredictionService.PredictionView generate(@Valid @RequestBody GeneratePrediction request) {
    return service.generate(request.videoId(), request.platform().toLowerCase());
  }

  @PostMapping("/live")
  public PredictionService.PredictionView generateLive(
      @Valid @RequestBody GenerateLivePrediction request) {
    return service.generateLive(
        request.videoId(), request.platform().toLowerCase(), request.knowledgeCutoff());
  }

  @PostMapping("/{id}/lock")
  public PredictionService.PredictionView lock(
      @PathVariable UUID id, @RequestBody(required = false) LockPrediction request) {
    return service.lock(id, request == null ? "confirmed for publication" : request.reason());
  }

  @GetMapping
  public List<PredictionService.PredictionView> list() {
    return service.list();
  }

  @PostMapping("/{id}/evaluate")
  public PredictionService.PredictionView evaluate(
      @PathVariable UUID id, @Valid @RequestBody EvaluatePrediction request) {
    return service.evaluate(id, request.horizonMinutes(), request.actualValue());
  }

  @GetMapping("/video/{videoId}")
  public List<PredictionService.PredictionView> history(@PathVariable UUID videoId) {
    return service.history(videoId);
  }

  /** Read-only projection of persisted prediction audit evidence for the reliability workspace. */
  @GetMapping("/reliability")
  public List<ReliabilityView> reliability() {
    return jdbc.sql(
            """
            SELECT pa.id, pa.prediction_id, p.model_version, p.platform, pa.horizon_minutes,
                   pa.actual_value, pa.absolute_error, pa.log_error, pa.interval_50_covered,
                   pa.interval_80_covered, pa.brier_score, pa.created_at
            FROM prediction_audits pa
            JOIN predictions p ON p.id=pa.prediction_id
            ORDER BY pa.created_at DESC
            """)
        .query((rs, ignored) -> new ReliabilityView(
            rs.getObject("id", UUID.class),
            rs.getObject("prediction_id", UUID.class),
            rs.getString("model_version"),
            rs.getString("platform"),
            rs.getInt("horizon_minutes"),
            nullableDouble(rs, "actual_value"),
            nullableDouble(rs, "absolute_error"),
            nullableDouble(rs, "log_error"),
            nullableBoolean(rs, "interval_50_covered"),
            nullableBoolean(rs, "interval_80_covered"),
            nullableDouble(rs, "brier_score"),
            rs.getObject("created_at", java.time.OffsetDateTime.class).toInstant()))
        .list();
  }

  private Double nullableDouble(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    double value = rs.getDouble(column);
    return rs.wasNull() ? null : value;
  }

  private Boolean nullableBoolean(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    boolean value = rs.getBoolean(column);
    return rs.wasNull() ? null : value;
  }

  public record ReliabilityView(
      UUID id,
      UUID predictionId,
      String modelVersion,
      String platform,
      int horizonMinutes,
      Double actualValue,
      Double absoluteError,
      Double logError,
      Boolean interval50Covered,
      Boolean interval80Covered,
      Double brierScore,
      java.time.Instant evaluatedAt) {}

  public record GeneratePrediction(UUID videoId, @NotBlank String platform) {}

  public record GenerateLivePrediction(
      UUID videoId, @NotBlank String platform, java.time.Instant knowledgeCutoff) {}

  public record LockPrediction(String reason) {}

  public record EvaluatePrediction(int horizonMinutes, double actualValue) {}
}
