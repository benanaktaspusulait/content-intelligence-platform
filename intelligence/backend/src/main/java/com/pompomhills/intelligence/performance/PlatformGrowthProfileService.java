package com.pompomhills.intelligence.performance;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PlatformGrowthProfileService {
  private final JdbcClient jdbc;

  public PlatformGrowthProfileService(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Transactional(readOnly = true)
  public GrowthProfile profile(UUID videoId, String platform, Instant cutoff) {
    String normalized = platform.toLowerCase(Locale.ROOT);
    List<Point> points =
        jdbc.sql(
                """
                SELECT publication_timestamp,measurement_timestamp,views
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform
                  AND publication_timestamp IS NOT NULL
                  AND measurement_timestamp IS NOT NULL
                  AND measurement_timestamp<=:cutoff AND views IS NOT NULL
                ORDER BY measurement_timestamp
                """)
            .param("video", videoId)
            .param("platform", normalized)
            .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
            .query(
                (rs, ignored) ->
                    new Point(
                        rs.getObject("publication_timestamp", OffsetDateTime.class).toInstant(),
                        rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant(),
                        rs.getLong("views")))
            .list();
    if (points.isEmpty()) return empty(videoId, normalized);

    Instant publishedAt = points.getFirst().publishedAt();
    MetricCheckpoint at6h = checkpoint(points, publishedAt.plusSeconds(6 * 3600L));
    MetricCheckpoint at24h = checkpoint(points, publishedAt.plusSeconds(24 * 3600L));
    MetricCheckpoint at48h = checkpoint(points, publishedAt.plusSeconds(48 * 3600L));
    MetricCheckpoint at7d = checkpoint(points, publishedAt.plusSeconds(7 * 24 * 3600L));
    Point latest = points.getLast();

    Double instagramBurstRatio =
        at6h == null || at24h == null || at24h.views() == 0
            ? null
            : at6h.views() / (double) at24h.views();
    Long viewsAfter24h =
        at24h == null || !latest.measuredAt().isAfter(publishedAt.plusSeconds(24 * 3600L))
            ? null
            : Math.max(0, latest.views() - at24h.views());
    Double facebookTailRatio =
        viewsAfter24h == null || at24h.views() == 0 ? null : viewsAfter24h / (double) at24h.views();

    String signal =
        switch (normalized) {
          case "instagram" -> instagramBurstRatio == null ? "INSUFFICIENT_DATA" : "EARLY_BURST";
          case "facebook" -> facebookTailRatio == null ? "INSUFFICIENT_DATA" : "LONG_TAIL";
          default -> "GENERAL_TRAJECTORY";
        };
    return new GrowthProfile(
        videoId,
        normalized,
        publishedAt,
        at6h,
        at24h,
        at48h,
        at7d,
        new MetricCheckpoint(latest.measuredAt(), latest.views()),
        instagramBurstRatio,
        viewsAfter24h,
        facebookTailRatio,
        signal,
        "Ratios are descriptive and use observed cumulative checkpoints without interpolation.");
  }

  private MetricCheckpoint checkpoint(List<Point> points, Instant horizon) {
    Point candidate = null;
    for (Point point : points) {
      if (point.measuredAt().isAfter(horizon)) break;
      candidate = point;
    }
    return candidate == null
        ? null
        : new MetricCheckpoint(candidate.measuredAt(), candidate.views());
  }

  private GrowthProfile empty(UUID videoId, String platform) {
    return new GrowthProfile(
        videoId,
        platform,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        "INSUFFICIENT_DATA",
        "Ratios are descriptive and use observed cumulative checkpoints without interpolation.");
  }

  private record Point(Instant publishedAt, Instant measuredAt, long views) {}

  public record MetricCheckpoint(Instant measuredAt, long views) {}

  public record GrowthProfile(
      UUID videoId,
      String platform,
      Instant publishedAt,
      MetricCheckpoint views6h,
      MetricCheckpoint views24h,
      MetricCheckpoint views48h,
      MetricCheckpoint views7d,
      MetricCheckpoint latest,
      Double instagramBurstRatio,
      Long viewsAfter24h,
      Double facebookTailRatio,
      String primarySignal,
      String disclaimer) {}
}
