package com.pompomhills.intelligence.performance;

import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Descriptive health signals for distribution and retention; never a render authorization gate. */
@Service
public class OperationalGuardService {
  public static final String DISTRIBUTION = "DISTRIBUTION";
  public static final String RETENTION = "RETENTION";
  private final JdbcClient jdbc;
  private final OperationalGuardProperties properties;
  private final Clock clock;
  private final ObjectMapper objectMapper;

  public OperationalGuardService(
      JdbcClient jdbc, OperationalGuardProperties properties, Clock clock, ObjectMapper objectMapper) {
    this.jdbc = jdbc;
    this.properties = properties;
    this.clock = clock;
    this.objectMapper = objectMapper;
  }

  @Transactional
  public GuardSnapshot evaluate(String platform) {
    String normalized = normalize(platform);
    if (!properties.enabled()) {
      return new GuardSnapshot(normalized, false, List.of(), properties.policyVersion());
    }
    List<GuardDecision> decisions =
        List.of(evaluateDistribution(normalized), evaluateRetention(normalized));
    return new GuardSnapshot(normalized, true, decisions, properties.policyVersion());
  }

  @Transactional(readOnly = true)
  public GuardSnapshot latest(String platform) {
    String normalized = normalize(platform);
    List<GuardDecision> decisions =
        jdbc.sql(
                """
                SELECT id,guard_type,platform,scope_type,state,policy_version,evidence_count,
                       metric_value,evaluated_at,evidence
                FROM operational_guard_decisions
                WHERE platform=:platform
                ORDER BY evaluated_at DESC
                """)
            .param("platform", normalized)
            .query(
                (rs, ignored) ->
                    new GuardDecision(
                        rs.getObject("id", UUID.class),
                        rs.getString("guard_type"),
                        rs.getString("platform"),
                        rs.getString("scope_type"),
                        rs.getString("state"),
                        rs.getString("policy_version"),
                        rs.getInt("evidence_count"),
                        nullableDouble(rs, "metric_value"),
                        rs.getObject("evaluated_at", OffsetDateTime.class).toInstant(),
                        rs.getString("evidence")))
            .list();
    return new GuardSnapshot(normalized, true, latestPerType(decisions), properties.policyVersion());
  }

  private GuardDecision evaluateDistribution(String platform) {
    Aggregate aggregate = aggregate(platform, "recommendation_percentage");
    String state =
        aggregate.evidenceCount() < properties.minimumMatureObservations()
            || aggregate.metricValue() == null
            ? "INSUFFICIENT_EVIDENCE"
            : aggregate.metricValue() < properties.recommendationPercentageFloor()
                ? "PUBLICATION_REVIEW_REQUIRED"
                : "HEALTHY";
    return persist(
        DISTRIBUTION,
        platform,
        state,
        aggregate,
        Map.of(
            "metric", "recommendation_percentage",
            "floor", properties.recommendationPercentageFloor(),
            "maturityHours", properties.maturityHours(),
            "interpretation", "descriptive_distribution_signal_only"));
  }

  private GuardDecision evaluateRetention(String platform) {
    RetentionAggregate aggregate = retentionAggregate(platform);
    boolean insufficient =
        aggregate.evidenceCount() < properties.minimumMatureObservations()
            || aggregate.completionRate() == null
            || aggregate.averageWatchSeconds() == null;
    String state =
        insufficient
            ? "INSUFFICIENT_EVIDENCE"
            : aggregate.completionRate() < properties.completionRateFloor()
                    || aggregate.averageWatchSeconds() < properties.averageWatchSecondsFloor()
                ? "WEAK_RETENTION"
                : "HEALTHY";
    Map<String, Object> evidence = new java.util.LinkedHashMap<>();
    evidence.put("metrics", List.of("completion_rate", "average_watch_seconds"));
    evidence.put("completionRate", aggregate.completionRate());
    evidence.put("completionRateFloor", properties.completionRateFloor());
    evidence.put("averageWatchSeconds", aggregate.averageWatchSeconds());
    evidence.put("averageWatchSecondsFloor", properties.averageWatchSecondsFloor());
    evidence.put("maturityHours", properties.maturityHours());
    evidence.put("interpretation", "descriptive_retention_signal_only");
    return persist(
        RETENTION,
        platform,
        state,
        new Aggregate(aggregate.evidenceCount(), aggregate.completionRate()),
        evidence);
  }

  private Aggregate aggregate(String platform, String metric) {
    return jdbc.sql(
            """
            SELECT count(*) evidence_count, avg(metric_value) metric_value
            FROM (
              SELECT DISTINCT ON (video_id,variant_id)
                recommendation_percentage AS metric_value
              FROM effective_performance_observations
              WHERE platform=:platform AND publication_timestamp IS NOT NULL
                AND COALESCE(measurement_timestamp,created_at) >=
                    publication_timestamp + (:maturityHours * interval '1 hour')
                AND recommendation_percentage IS NOT NULL
                AND data_quality_status <> 'UNAVAILABLE'
              ORDER BY video_id,variant_id,
                       COALESCE(measurement_timestamp,created_at) DESC,created_at DESC
            ) mature
            """)
        .param("platform", platform)
        .param("maturityHours", properties.maturityHours())
        .query(
            (rs, ignored) -> new Aggregate(rs.getInt("evidence_count"), nullableDouble(rs, "metric_value")))
        .single();
  }

  private RetentionAggregate retentionAggregate(String platform) {
    return jdbc.sql(
            """
            SELECT count(*) evidence_count, avg(completion_rate) completion_rate,
                   avg(average_watch_seconds) average_watch_seconds
            FROM (
              SELECT DISTINCT ON (video_id,variant_id)
                completion_rate,average_watch_seconds
              FROM effective_performance_observations
              WHERE platform=:platform AND publication_timestamp IS NOT NULL
                AND COALESCE(measurement_timestamp,created_at) >=
                    publication_timestamp + (:maturityHours * interval '1 hour')
                AND completion_rate IS NOT NULL AND average_watch_seconds IS NOT NULL
                AND data_quality_status <> 'UNAVAILABLE'
              ORDER BY video_id,variant_id,
                       COALESCE(measurement_timestamp,created_at) DESC,created_at DESC
            ) mature
            """)
        .param("platform", platform)
        .param("maturityHours", properties.maturityHours())
        .query(
            (rs, ignored) ->
                new RetentionAggregate(
                    rs.getInt("evidence_count"),
                    nullableDouble(rs, "completion_rate"),
                    nullableDouble(rs, "average_watch_seconds")))
        .single();
  }

  private GuardDecision persist(
      String type, String platform, String state, Aggregate aggregate, Map<String, Object> evidence) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO operational_guard_decisions
              (id,guard_type,platform,scope_type,state,policy_version,evidence_count,metric_value,evaluated_at,evidence)
            VALUES (:id,:type,:platform,'PLATFORM',:state,:version,:count,:metric,:evaluated,CAST(:evidence AS jsonb))
            """)
        .param("id", id)
        .param("type", type)
        .param("platform", platform)
        .param("state", state)
        .param("version", properties.policyVersion())
        .param("count", aggregate.evidenceCount())
        .param("metric", aggregate.metricValue())
        .param("evaluated", OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC))
        .param("evidence", toJson(evidence))
        .update();
    return new GuardDecision(id, type, platform, "PLATFORM", state, properties.policyVersion(),
        aggregate.evidenceCount(), aggregate.metricValue(), clock.instant(), toJson(evidence));
  }

  private List<GuardDecision> latestPerType(List<GuardDecision> decisions) {
    List<GuardDecision> latest = new ArrayList<>();
    for (GuardDecision decision : decisions) {
      if (latest.stream().noneMatch(item -> item.guardType().equals(decision.guardType()))) {
        latest.add(decision);
      }
    }
    return latest;
  }

  private String normalize(String platform) {
    if (platform == null || platform.isBlank()) throw new IllegalArgumentException("platform is required");
    return platform.toLowerCase(Locale.ROOT);
  }

  private Double nullableDouble(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    double value = rs.getDouble(column);
    return rs.wasNull() ? null : value;
  }

  private String toJson(Map<String, Object> value) {
    try {
      return objectMapper.writeValueAsString(value);
    } catch (JsonProcessingException exception) {
      throw new IllegalStateException("Cannot serialize operational guard evidence", exception);
    }
  }

  private record Aggregate(int evidenceCount, Double metricValue) {}
  private record RetentionAggregate(int evidenceCount, Double completionRate, Double averageWatchSeconds) {}

  public record GuardSnapshot(String platform, boolean enabled, List<GuardDecision> decisions, String policyVersion) {}

  public record GuardDecision(
      UUID id, String guardType, String platform, String scopeType, String state,
      String policyVersion, int evidenceCount, Double metricValue, Instant evaluatedAt, String evidence) {}
}
