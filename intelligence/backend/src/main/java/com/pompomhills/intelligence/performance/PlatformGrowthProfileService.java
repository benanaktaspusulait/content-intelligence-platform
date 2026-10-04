package com.pompomhills.intelligence.performance;

import java.time.Duration;
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
  /**
   * How close an observation must be to a target horizon to count as satisfying that horizon's
   * label. A "24h" checkpoint built from a 1-hour-old observation is misleading - per the
   * audit's P1-07 finding, this must be visible rather than silently accepted.
   */
  private static final Duration CHECKPOINT_TOLERANCE = Duration.ofHours(2);

  private final JdbcClient jdbc;

  public PlatformGrowthProfileService(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Transactional(readOnly = true)
  public GrowthProfile profile(UUID videoId, String platform, Instant cutoff, UUID variantId) {
    String normalized = platform.toLowerCase(Locale.ROOT);
    List<ObservationSeries.RawObservation> raw =
        jdbc.sql(
                """
                SELECT measurement_timestamp,views,metric_semantics,source
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform
                  AND publication_timestamp IS NOT NULL
                  AND measurement_timestamp IS NOT NULL
                  AND measurement_timestamp<=:cutoff
                  AND variant_id IS NOT DISTINCT FROM :variant
                ORDER BY measurement_timestamp
                """)
            .param("video", videoId)
            .param("platform", normalized)
            .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
            .param("variant", variantId, java.sql.Types.OTHER)
            .query(
                (rs, ignored) ->
                    new ObservationSeries.RawObservation(
                        rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant(),
                        nullableLong(rs, "views"),
                        rs.getString("metric_semantics"),
                        rs.getString("source")))
            .list();
    Instant publishedAt = earliestPublication(videoId, normalized, cutoff, variantId);
    if (publishedAt == null) return empty(videoId, normalized);

    List<ObservationSeries.NormalizedPoint> points = ObservationSeries.normalize(raw);
    if (points.isEmpty()) return empty(videoId, normalized);

    MetricCheckpoint at6h = checkpoint(points, publishedAt.plusSeconds(6 * 3600L));
    MetricCheckpoint at24h = checkpoint(points, publishedAt.plusSeconds(24 * 3600L));
    MetricCheckpoint at48h = checkpoint(points, publishedAt.plusSeconds(48 * 3600L));
    MetricCheckpoint at7d = checkpoint(points, publishedAt.plusSeconds(7 * 24 * 3600L));
    ObservationSeries.NormalizedPoint latest = points.getLast();

    Double instagramBurstRatio =
        at6h == null || at24h == null || at24h.views() == 0
            ? null
            : at6h.views() / (double) at24h.views();
    Long viewsAfter24h =
        at24h == null || !latest.measuredAt().isAfter(publishedAt.plusSeconds(24 * 3600L))
            ? null
            : Math.max(0, latest.cumulativeViews() - at24h.views());
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
        new MetricCheckpoint(latest.measuredAt(), latest.cumulativeViews(), true),
        instagramBurstRatio,
        viewsAfter24h,
        facebookTailRatio,
        signal,
        "Ratios are descriptive and use metric-semantics-normalized cumulative checkpoints "
            + "without interpolation; a checkpoint outside its tolerance window is flagged, not "
            + "hidden.");
  }

  private Instant earliestPublication(UUID videoId, String platform, Instant cutoff, UUID variantId) {
    return jdbc.sql(
            """
            SELECT min(publication_timestamp) FROM performance_observations
            WHERE video_id=:video AND platform=:platform AND publication_timestamp IS NOT NULL
              AND measurement_timestamp<=:cutoff AND variant_id IS NOT DISTINCT FROM :variant
            """)
        .param("video", videoId)
        .param("platform", platform)
        .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
        .param("variant", variantId, java.sql.Types.OTHER)
        .query(OffsetDateTime.class)
        .optional()
        .map(OffsetDateTime::toInstant)
        .orElse(null);
  }

  private MetricCheckpoint checkpoint(List<ObservationSeries.NormalizedPoint> points, Instant horizon) {
    ObservationSeries.NormalizedPoint candidate = null;
    for (var point : points) {
      if (point.measuredAt().isAfter(horizon)) break;
      candidate = point;
    }
    if (candidate == null) return null;
    boolean withinTolerance =
        Duration.between(candidate.measuredAt(), horizon).abs().compareTo(CHECKPOINT_TOLERANCE) <= 0;
    return new MetricCheckpoint(candidate.measuredAt(), candidate.cumulativeViews(), withinTolerance);
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
        "Ratios are descriptive and use metric-semantics-normalized cumulative checkpoints "
            + "without interpolation; a checkpoint outside its tolerance window is flagged, not "
            + "hidden.");
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  public record MetricCheckpoint(Instant measuredAt, long views, boolean withinTolerance) {}

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
