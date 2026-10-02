package com.pompomhills.intelligence.performance;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DiscoveryProfileService {
  public static final String ALGORITHM_VERSION = "new-audience-quality-v1";

  private final JdbcClient jdbc;
  private final DiscoveryScoreProperties properties;

  public DiscoveryProfileService(JdbcClient jdbc, DiscoveryScoreProperties properties) {
    this.jdbc = jdbc;
    this.properties = properties;
  }

  @Transactional(readOnly = true)
  public DiscoveryProfile profile(UUID videoId, String platform, Instant cutoff) {
    String normalizedPlatform = platform.toLowerCase();
    OffsetDateTime cutoffTime = OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC);
    AudienceSnapshot audience =
        jdbc.sql(
                """
                SELECT id,measurement_timestamp,views,follows,followers_percentage,
                       nonfollowers_percentage,recommendation_percentage
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform
                  AND COALESCE(measurement_timestamp,created_at)<=:cutoff
                ORDER BY COALESCE(measurement_timestamp,created_at) DESC,created_at DESC
                LIMIT 1
                """)
            .param("video", videoId)
            .param("platform", normalizedPlatform)
            .param("cutoff", cutoffTime)
            .query(
                (rs, ignored) ->
                    new AudienceSnapshot(
                        rs.getObject("id", UUID.class),
                        instant(rs.getObject("measurement_timestamp", OffsetDateTime.class)),
                        nullableLong(rs, "views"),
                        nullableLong(rs, "follows"),
                        nullableDouble(rs, "followers_percentage"),
                        nullableDouble(rs, "nonfollowers_percentage"),
                        nullableDouble(rs, "recommendation_percentage")))
            .optional()
            .orElse(null);
    CountrySnapshot us =
        jdbc.sql(
                """
                SELECT co.percentage,co.estimated_absolute_count,
                       COALESCE(co.observed_at,po.measurement_timestamp,po.created_at) observed_at,
                       co.data_quality_status
                FROM country_observations co
                JOIN performance_observations po ON po.id=co.performance_observation_id
                WHERE po.video_id=:video AND po.platform=:platform AND co.country_code='US'
                  AND COALESCE(co.observed_at,po.measurement_timestamp,po.created_at)<=:cutoff
                ORDER BY COALESCE(co.observed_at,po.measurement_timestamp,po.created_at) DESC
                LIMIT 1
                """)
            .param("video", videoId)
            .param("platform", normalizedPlatform)
            .param("cutoff", cutoffTime)
            .query(
                (rs, ignored) ->
                    new CountrySnapshot(
                        rs.getDouble("percentage"),
                        nullableLong(rs, "estimated_absolute_count"),
                        instant(rs.getObject("observed_at", OffsetDateTime.class)),
                        rs.getString("data_quality_status")))
            .optional()
            .orElse(null);
    Double nonFollower = audience == null ? null : audience.nonFollowerShare();
    Double usShare = us == null ? null : us.percentage();
    Double qualityScore = score(nonFollower, usShare);
    Long views = audience == null ? null : audience.views();
    Long follows = audience == null ? null : audience.follows();
    Double followsPerThousand =
        views == null || views <= 0 || follows == null ? null : follows * 1000.0 / views;
    Map<String, Object> components = new LinkedHashMap<>();
    components.put("nonFollowerShare", nonFollower);
    components.put("usAudienceShare", usShare);
    components.put("nonFollowerWeight", properties.nonFollowerWeight());
    components.put("usAudienceWeight", properties.usAudienceWeight());
    components.put("usAudienceTargetPercentage", properties.usAudienceTargetPercentage());
    return new DiscoveryProfile(
        videoId,
        normalizedPlatform,
        cutoff,
        audience == null ? null : audience.observedAt(),
        us == null ? null : us.observedAt(),
        audience == null ? null : audience.followerShare(),
        nonFollower,
        usShare,
        us == null ? null : us.estimatedAbsoluteCount(),
        audience == null ? null : audience.recommendationShare(),
        followsPerThousand,
        qualityScore,
        ALGORITHM_VERSION,
        qualityScore == null ? "UNAVAILABLE" : "DERIVED_FROM_REPORTED_SHARES",
        components);
  }

  public Double score(Double nonFollowerShare, Double usAudienceShare) {
    if (nonFollowerShare == null || usAudienceShare == null) return null;
    double target = Math.max(properties.usAudienceTargetPercentage(), 0.0001);
    double normalizedUs = Math.min(100.0, usAudienceShare / target * 100.0);
    double score =
        properties.nonFollowerWeight() * nonFollowerShare
            + properties.usAudienceWeight() * normalizedUs;
    return Math.round(Math.max(0, Math.min(100, score)) * 100.0) / 100.0;
  }

  private Instant instant(OffsetDateTime value) {
    return value == null ? null : value.toInstant();
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  private Double nullableDouble(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    double value = rs.getDouble(column);
    return rs.wasNull() ? null : value;
  }

  private record AudienceSnapshot(
      UUID id,
      Instant observedAt,
      Long views,
      Long follows,
      Double followerShare,
      Double nonFollowerShare,
      Double recommendationShare) {}

  private record CountrySnapshot(
      Double percentage,
      Long estimatedAbsoluteCount,
      Instant observedAt,
      String dataQualityStatus) {}

  public record DiscoveryProfile(
      UUID videoId,
      String platform,
      Instant cutoff,
      Instant audienceObservedAt,
      Instant countryObservedAt,
      Double followerShare,
      Double nonFollowerShare,
      Double usAudienceShare,
      Long estimatedUsAudience,
      Double recommendationShare,
      Double followsPerThousandViews,
      Double newAudienceQualityScore,
      String algorithmVersion,
      String dataQualityStatus,
      Map<String, Object> components) {}
}
