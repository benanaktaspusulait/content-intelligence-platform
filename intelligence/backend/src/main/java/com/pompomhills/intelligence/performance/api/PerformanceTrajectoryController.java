package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.InterventionService;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
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
    List<RawPoint> source =
        jdbc.sql(
                """
                SELECT measurement_timestamp,views,reach,likes,comments,shares,follows
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform AND measurement_timestamp IS NOT NULL
                ORDER BY measurement_timestamp
                """)
            .param("video", videoId)
            .param("platform", platform.toLowerCase())
            .query(
                (rs, ignored) ->
                    new RawPoint(
                        rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant(),
                        nullableLong(rs, "views"),
                        nullableLong(rs, "reach"),
                        nullableLong(rs, "likes"),
                        nullableLong(rs, "comments"),
                        nullableLong(rs, "shares"),
                        nullableLong(rs, "follows")))
            .list();
    var interventionEvents = interventions.list(videoId, platform);
    Instant firstIntervention =
        interventionEvents.isEmpty() ? null : interventionEvents.getFirst().eventTime();
    var points = new ArrayList<TrajectoryPoint>();
    for (int index = 0; index < source.size(); index++) {
      RawPoint current = source.get(index);
      RawPoint previous = index == 0 ? null : source.get(index - 1);
      Long delta =
          previous == null || current.views() == null || previous.views() == null
              ? null
              : current.views() - previous.views();
      Double velocity = null;
      if (previous != null && delta != null) {
        double hours = Duration.between(previous.at(), current.at()).toMillis() / 3_600_000.0;
        if (hours > 0) velocity = delta / hours;
      }
      points.add(
          new TrajectoryPoint(
              current.at(),
              current.views(),
              current.reach(),
              current.likes(),
              current.comments(),
              current.shares(),
              current.follows(),
              delta,
              velocity,
              firstIntervention != null && !current.at().isBefore(firstIntervention)));
    }
    return new TrajectoryView(
        videoId,
        platform.toLowerCase(),
        label(points),
        firstIntervention == null,
        interventionEvents,
        points);
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

  private record RawPoint(
      Instant at, Long views, Long reach, Long likes, Long comments, Long shares, Long follows) {}

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
      List<TrajectoryPoint> points) {}
}
