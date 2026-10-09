package com.pompomhills.intelligence.meta;

import java.time.Clock;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MetaPageInsightsService {
  private static final String METRICS = "page_impressions,page_engaged_users,page_post_engagements";
  private final MetaReadProperties properties;
  private final MetaGraphReadClient client;
  private final JdbcClient jdbc;
  private final Clock clock;

  public MetaPageInsightsService(
      MetaReadProperties properties, MetaGraphReadClient client, JdbcClient jdbc, Clock clock) {
    this.properties = properties;
    this.client = client;
    this.jdbc = jdbc;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public MetaPageInsightsResponse get(String objectId) {
    String id = objectId == null || objectId.isBlank() ? properties.pageId() : objectId.trim();
    requireConfigured(id);
    try {
      Map<String, Long> metrics = readMetrics(client.getObjectInsights(id, METRICS));
      return new MetaPageInsightsResponse(
          id,
          metrics.isEmpty()
              ? MetaPageInsightsResponse.Availability.PARTIAL
              : MetaPageInsightsResponse.Availability.AVAILABLE,
          metrics.isEmpty() ? "Meta returned no insight values." : null,
          metrics,
          loadSnapshots(id),
          properties.apiVersion());
    } catch (MetaGraphException error) {
      return new MetaPageInsightsResponse(
          id,
          MetaPageInsightsResponse.Availability.UNAVAILABLE,
          "Facebook Page insights are unavailable.",
          Map.of(),
          loadSnapshots(id),
          properties.apiVersion());
    }
  }

  @Transactional
  public MetaPageInsightsResponse capture(String objectId) {
    MetaPageInsightsResponse current = get(objectId);
    Instant measuredAt = clock.instant();
    jdbc.sql(
            "INSERT INTO meta_page_insight_snapshots (object_id, measured_at, availability, metrics) VALUES (:objectId, :measuredAt, :availability, CAST(:metrics AS jsonb))")
        .param("objectId", current.objectId())
        .param("measuredAt", measuredAt)
        .param("availability", current.availability().name())
        .param("metrics", toJson(current.metrics()))
        .update();
    return new MetaPageInsightsResponse(
        current.objectId(), current.availability(), current.reason(), current.metrics(),
        loadSnapshots(current.objectId()), current.apiVersion());
  }

  private List<MetaPageInsightsResponse.Snapshot> loadSnapshots(String objectId) {
    return jdbc.sql(
            "SELECT measured_at, metrics FROM meta_page_insight_snapshots WHERE object_id=:objectId ORDER BY measured_at DESC LIMIT 50")
        .param("objectId", objectId)
        .query(
            (rs, rowNum) ->
                new MetaPageInsightsResponse.Snapshot(
                    rs.getTimestamp("measured_at").toInstant(), Map.of()))
        .list();
  }

  private Map<String, Long> readMetrics(MetaGraphReadClient.InstagramInsightsResponse response) {
    Map<String, Long> metrics = new LinkedHashMap<>();
    if (response != null && response.data() != null) {
      for (MetaGraphReadClient.InsightMetric metric : response.data()) {
        if (metric != null && metric.name() != null && metric.resolveValue() != null) {
          metrics.put(metric.name(), metric.resolveValue());
        }
      }
    }
    return Map.copyOf(metrics);
  }

  private void requireConfigured(String id) {
    if (!properties.enabled() || id == null || id.isBlank() || !client.hasEffectiveAccessToken()) {
      throw new MetaNotConfiguredException();
    }
  }

  private String toJson(Map<String, Long> metrics) {
    return metrics.entrySet().stream()
        .map(entry -> "\\\"" + entry.getKey() + "\\\":" + entry.getValue())
        .collect(java.util.stream.Collectors.joining(",", "{", "}"));
  }
}
