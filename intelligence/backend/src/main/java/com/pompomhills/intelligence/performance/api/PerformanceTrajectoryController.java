package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.InterventionService;
import com.pompomhills.intelligence.performance.ObservationSeries;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/performance")
public class PerformanceTrajectoryController {
  private final JdbcClient jdbc;
  private final InterventionService interventions;

  public PerformanceTrajectoryController(JdbcClient jdbc, InterventionService interventions) {
    this.jdbc = jdbc;
    this.interventions = interventions;
  }

  @GetMapping("/video/{videoId}/trajectory")
  TrajectoryView trajectory(
      @PathVariable UUID videoId, @RequestParam(defaultValue = "instagram") String platform) {
    List<ObservationSeries.RawObservation> raw =
        jdbc.sql(
                """
                SELECT measurement_timestamp,views,metric_semantics,source
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform AND measurement_timestamp IS NOT NULL
                ORDER BY measurement_timestamp
                """)
            .param("video", videoId)
            .param("platform", platform.toLowerCase())
            .query(
                (rs, ignored) ->
                    new ObservationSeries.RawObservation(
                        rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant(),
                        nullableLong(rs, "views"),
                        rs.getString("metric_semantics"),
                        rs.getString("source")))
            .list();

    List<String> sourcesPresent =
        raw.stream().map(ObservationSeries.RawObservation::source).distinct().sorted().toList();
    boolean reconciliationApplied = sourcesPresent.size() > 1;

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);
    List<ObservationSeries.NormalizedPoint> selected =
        reconciliationApplied ? dominantSource(normalized) : normalized;

    var interventionEvents = interventions.list(videoId, platform);
    Instant firstIntervention =
        interventionEvents.isEmpty() ? null : interventionEvents.getFirst().eventTime();
    var points = new ArrayList<TrajectoryPoint>();
    for (int index = 0; index < selected.size(); index++) {
      ObservationSeries.NormalizedPoint current = selected.get(index);
      ObservationSeries.NormalizedPoint previous = index == 0 ? null : selected.get(index - 1);
      Long delta = previous == null ? null : current.cumulativeViews() - previous.cumulativeViews();
      Double velocity = null;
      if (previous != null && delta != null) {
        double hours =
            Duration.between(previous.measuredAt(), current.measuredAt()).toMillis() / 3_600_000.0;
        if (hours > 0) velocity = delta / hours;
      }
      points.add(
          new TrajectoryPoint(
              current.measuredAt(),
              current.cumulativeViews(),
              null,
              null,
              null,
              null,
              null,
              delta,
              velocity,
              firstIntervention != null && !current.measuredAt().isBefore(firstIntervention)));
    }
    return new TrajectoryView(
        videoId,
        platform.toLowerCase(),
        label(points),
        firstIntervention == null,
        interventionEvents,
        points,
        sourcesPresent,
        reconciliationApplied);
  }

  /**
   * When more than one source contributed observations, this trajectory uses only the source
   * with the most normalized points - an explicit, visible reconciliation rule rather than
   * silently interleaving two independently-collected series. Callers can see which sources were
   * present via {@link TrajectoryView#sourcesPresent()} and that reconciliation happened via
   * {@link TrajectoryView#sourceReconciliationApplied()}.
   */
  private List<ObservationSeries.NormalizedPoint> dominantSource(
      List<ObservationSeries.NormalizedPoint> normalized) {
    Map<String, List<ObservationSeries.NormalizedPoint>> bySource = new LinkedHashMap<>();
    for (var point : normalized) {
      bySource.computeIfAbsent(point.source(), key -> new ArrayList<>()).add(point);
    }
    return bySource.values().stream()
        .max((a, b) -> Integer.compare(a.size(), b.size()))
        .orElse(List.of());
  }

  private String label(List<TrajectoryPoint> points) {
    if (points.size() < 3) return "INSUFFICIENT_DATA";
    Double previous = points.get(points.size() - 2).viewsPerHour();
    Double latest = points.getLast().viewsPerHour();
    if (previous == null || latest == null) return "INSUFFICIENT_DATA";
    if (latest > Math.max(50, previous * 1.75)) return "SECOND_WAVE";
    if (latest < 10) return "EARLY_STALL";
    if (latest > previous * 1.1) return "PERSISTENT_GROWTH";
    return "SLOW_GROWTH";
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  public record TrajectoryPoint(
      Instant measuredAt,
      Long views,
      Long reach,
      Long likes,
      Long comments,
      Long shares,
      Long follows,
      Long deltaViews,
      Double viewsPerHour,
      boolean intervened) {}

  public record TrajectoryView(
      UUID videoId,
      String platform,
      String label,
      boolean cleanOrganic,
      List<InterventionService.InterventionView> interventions,
      List<TrajectoryPoint> points,
      List<String> sourcesPresent,
      boolean sourceReconciliationApplied) {}
}
