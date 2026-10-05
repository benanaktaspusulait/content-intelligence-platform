package com.pompomhills.intelligence.prediction;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

/** Read-only, leakage-safe readiness projection over imported observations. */
@Service
public class PredictionDataReadinessService {
  private static final int MINIMUM_ELIGIBLE_ROWS = 3;
  private static final int EXPERIMENTAL_READY_ROWS = 30;
  private final JdbcClient jdbc;

  public PredictionDataReadinessService(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  public List<Readiness> all() {
    return List.of("FACEBOOK_REELS", "INSTAGRAM_REELS", "TIKTOK", "YOUTUBE_SHORTS")
        .stream().map(this::forPlatform).toList();
  }

  private Readiness forPlatform(String platform) {
    String storedPlatform = switch (platform) {
      case "FACEBOOK_REELS" -> "FACEBOOK";
      case "INSTAGRAM_REELS" -> "INSTAGRAM";
      case "YOUTUBE_SHORTS" -> "YOUTUBE";
      default -> platform;
    };
    Map<String, Object> counts = jdbc.sql("""
        SELECT
          COUNT(*) FILTER (WHERE po.video_id IS NOT NULL AND po.publication_timestamp IS NOT NULL
            AND po.measurement_timestamp IS NOT NULL AND po.paid=false AND po.views IS NOT NULL) AS eligible,
          COUNT(*) FILTER (WHERE po.paid=false) AS organic,
          COUNT(*) FILTER (WHERE po.paid=true) AS paid,
          COUNT(*) FILTER (WHERE po.video_id IS NULL OR po.publication_timestamp IS NULL
            OR po.measurement_timestamp IS NULL) AS incomplete
        FROM performance_observations po
        WHERE UPPER(po.platform)=:platform
        """).param("platform", storedPlatform).query((rs, ignored) -> {
          Map<String, Object> values = new java.util.LinkedHashMap<>();
          values.put("eligible", rs.getLong("eligible"));
          values.put("organic", rs.getLong("organic"));
          values.put("paid", rs.getLong("paid"));
          values.put("incomplete", rs.getLong("incomplete"));
          return values;
        }).single();
    int eligible = ((Number) counts.get("eligible")).intValue();
    String status = eligible == 0 ? "NO_DATA"
        : eligible < MINIMUM_ELIGIBLE_ROWS ? "INSUFFICIENT_DATA"
        : eligible < EXPERIMENTAL_READY_ROWS ? "EXPERIMENTAL_READY" : "TRAINING_READY";
    String note = eligible < MINIMUM_ELIGIBLE_ROWS
        ? "Need at least 3 eligible organic observations; no numeric forecast is available."
        : eligible < EXPERIMENTAL_READY_ROWS
            ? "Evidence is available for experiments, but the production model gate is not met."
            : "Training eligibility is met; chronological validation is still required before activation.";
    return new Readiness(platform, eligible, ((Number) counts.get("organic")).intValue(),
        ((Number) counts.get("paid")).intValue(), ((Number) counts.get("incomplete")).intValue(),
        status, note, MINIMUM_ELIGIBLE_ROWS, EXPERIMENTAL_READY_ROWS);
  }

  public record Readiness(String platform, int eligibleObservations, int organicObservations,
      int paidObservations, int incompleteObservations, String status, String note,
      int minimumEligibleRows, int experimentalReadyRows) {}
}
