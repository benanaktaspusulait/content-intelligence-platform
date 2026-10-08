package com.pompomhills.intelligence.modelregistry;

import java.util.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.ObjectMapper;

/** Training consumes verified mature observations and immutable pre-publication feature snapshots. */
@Service
public class StatisticalTrainingService {
  private final JdbcClient jdbc;
  private final RestClient ml;
  private final ObjectMapper json;

  public StatisticalTrainingService(JdbcClient jdbc, RestClient mlRestClient, ObjectMapper json) {
    this.jdbc = jdbc;
    this.ml = mlRestClient;
    this.json = json;
  }

  public Map<String, Object> train(String platform, String reason) {
    if (!List.of("instagram", "facebook", "tiktok").contains(platform)
        || reason == null
        || reason.isBlank())
      throw new IllegalArgumentException(
          "Supported platform and explicit training reason required");
    var rows =
        jdbc.sql(
                """
                SELECT po.id,po.video_id,po.views,po.publication_timestamp,po.measurement_timestamp,po.metric_semantics,
                  snap.knowledge_cutoff,snap.features::text
                FROM effective_performance_observations po
                JOIN LATERAL (SELECT knowledge_cutoff,features FROM prediction_feature_snapshots fs
                  WHERE fs.video_id=po.video_id AND fs.variant_id IS NOT DISTINCT FROM po.variant_id
                    AND lower(fs.platform)=lower(po.platform) AND fs.knowledge_cutoff<po.publication_timestamp
                    AND fs.created_at<po.publication_timestamp AND fs.source_analysis_version='sampled-visual-motion-v5' ORDER BY fs.created_at DESC LIMIT 1) snap ON true
                WHERE lower(po.platform)=:platform AND po.paid=false AND po.views IS NOT NULL
                  AND po.metric_semantics IN ('CUMULATIVE','SNAPSHOT')
                  AND upper(COALESCE(po.raw_payload_json->>'horizon',''))='72H'
                  AND po.measurement_timestamp BETWEEN po.publication_timestamp+interval '72 hours' AND po.publication_timestamp+interval '73 hours'
                  AND po.measurement_timestamp<=now()
                  AND EXISTS(SELECT 1 FROM video_publications vp WHERE vp.video_id=po.video_id
                    AND vp.variant_id IS NOT DISTINCT FROM po.variant_id AND lower(vp.platform)=lower(po.platform)
                    AND vp.platform_content_id=po.platform_content_id AND vp.published_at=po.publication_timestamp)
                ORDER BY po.publication_timestamp,po.id
                """)
            .param("platform", platform)
            .query(
                (rs, ignored) -> {
                  var value = new LinkedHashMap<String, Object>();
                  value.put("observationId", rs.getString("id"));
                  value.put("videoId", rs.getString("video_id"));
                  value.put("features", json.readValue(rs.getString("features"), Map.class));
                  value.put(
                      "featureCutoff",
                      rs.getObject("knowledge_cutoff", java.time.OffsetDateTime.class).toString());
                  value.put(
                      "publishedAt",
                      rs.getObject("publication_timestamp", java.time.OffsetDateTime.class)
                          .toString());
                  value.put(
                      "measuredAt",
                      rs.getObject("measurement_timestamp", java.time.OffsetDateTime.class)
                          .toString());
                  value.put("views", rs.getLong("views"));
                  value.put("metricSemantics", rs.getString("metric_semantics"));
                  value.put("horizon", "72H");
                  value.put("verified", true);
                  value.put("paid", false);
                  return value;
                })
            .list();
    for (var row : rows)
      row.put("parentVideoId", root(UUID.fromString(String.valueOf(row.get("videoId")))));
    if (rows.stream().map(r -> r.get("parentVideoId")).distinct().count() < 30)
      throw new org.springframework.web.server.ResponseStatusException(
          org.springframework.http.HttpStatus.CONFLICT,
          "At least 30 verified mature independent parent videos with pre-publish features"
              + " required; no artifact created");
    var result =
        ml.post()
            .uri("/v1/training/train")
            .body(
                Map.of(
                    "contractVersion",
                    "v1",
                    "platform",
                    platform,
                    "datasetVersion",
                    "verified-72h-" + UUID.randomUUID(),
                    "rows",
                    rows))
            .retrieve()
            .body(Map.class);
    if (result == null || !Boolean.TRUE.equals(result.get("artifactCreated")))
      throw new IllegalStateException("ML did not return a trained artifact");
    return result;
  }

  private String root(UUID video) {
    var seen = new HashSet<UUID>();
    UUID current = video;
    while (seen.add(current) && seen.size() <= 32) {
      var parents =
          jdbc.sql(
                  """
                  SELECT DISTINCT parent FROM (
                    SELECT rj.openart_params->>'parentVideoId' parent FROM videos v JOIN render_assets ra ON ra.relative_path=v.relative_path JOIN render_jobs rj ON rj.id=ra.render_job_id WHERE v.id=:video AND ra.asset_type='VIDEO'
                    UNION SELECT payload->>'videoId' FROM post_family_workflow_events WHERE kind='EDIT_HANDOFF' AND payload->>'artifactVideoId'=:text
                  ) links WHERE parent IS NOT NULL
                  """)
              .param("video", current)
              .param("text", current.toString())
              .query(String.class)
              .list();
      if (parents.isEmpty()) return current.toString();
      if (parents.size() != 1)
        throw new IllegalStateException("Ambiguous sibling lineage is not training eligible");
      current = UUID.fromString(parents.getFirst());
    }
    throw new IllegalStateException("Cyclic or oversized parent lineage is not training eligible");
  }

  public Map<String, Object> verify(String platform, String path, Map<?, ?> metrics) {
    if (!"grouped-ridge-72h-v1".equals(metrics.get("pipelineVersion"))
        || !(metrics.get("artifactSha256") instanceof String hash)
        || !hash.matches("[a-f0-9]{64}"))
      throw new org.springframework.web.server.ResponseStatusException(
          org.springframework.http.HttpStatus.NOT_IMPLEMENTED,
          "Legacy model has no verified statistical artifact; registry unchanged");
    var verified =
        ml.post()
            .uri("/v1/training/verify-artifact")
            .body(Map.of("platform", platform, "artifactPath", path, "artifactSha256", hash))
            .retrieve()
            .body(Map.class);
    if (verified == null || !Boolean.TRUE.equals(verified.get("verified")))
      throw new IllegalStateException("Artifact verification failed");
    return verified;
  }
}
