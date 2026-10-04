package com.pompomhills.intelligence.performance.api;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Internal append-only bridge from creative-render collection to the canonical evidence ledger. */
@RestController
@RequestMapping("/api/v1/performance/observations")
public class PerformanceObservationIntakeController {

  private final JdbcClient jdbc;
  private final String bridgeToken;

  public PerformanceObservationIntakeController(
      JdbcClient jdbc,
      @Value("${pompom.internal.observation-bridge-token:}") String bridgeToken) {
    this.jdbc = jdbc;
    this.bridgeToken = bridgeToken;
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public ObservationResponse ingest(
      @RequestHeader(value = "X-Internal-Observation-Token", required = false) String token,
      @RequestBody ObservationRequest request) {
    if (bridgeToken.isBlank() || token == null || !sameToken(token, bridgeToken)) {
      throw new org.springframework.web.server.ResponseStatusException(
          HttpStatus.UNAUTHORIZED, "Internal observation bridge authentication failed");
    }
    if (request.videoId() == null
        || request.platform() == null
        || request.sourceObservationKey() == null) {
      throw new IllegalArgumentException(
          "videoId, platform and sourceObservationKey are required");
    }

    UUID existing =
        jdbc.sql(
                "SELECT id FROM performance_observations "
                    + "WHERE platform=:platform AND source='API' AND source_observation_key=:key")
            .param("platform", request.platform())
            .param("key", request.sourceObservationKey())
            .query(UUID.class)
            .optional()
            .orElse(null);
    if (existing != null) {
      return new ObservationResponse(existing, true);
    }

    UUID id =
        jdbc.sql(
                """
                INSERT INTO performance_observations
                  (import_row_id,video_id,variant_id,platform,platform_content_id,
                   publication_timestamp,measurement_timestamp,metric_semantics,views,reach,
                   unique_viewers,likes,comments,shares,saves,follows,paid,source,source_version,
                   source_observation_key,raw_payload_json,data_quality_status)
                VALUES (NULL,:video,:variant,:platform,:contentId,:published,:measured,'SNAPSHOT',
                        :views,:reach,:uniqueViewers,:likes,:comments,:shares,:saves,:follows,
                        false,'API','creative-render-v1',:sourceKey,CAST(:payload AS jsonb),'API_REPORTED')
                RETURNING id
                """)
            .param("video", request.videoId())
            .param("variant", request.variantId())
            .param("platform", request.platform())
            .param("contentId", request.platformContentId())
            .param("published", request.publicationTimestamp())
            .param("measured", request.measurementTimestamp())
            .param("views", request.views())
            .param("reach", request.reach())
            .param("uniqueViewers", request.uniqueViewers())
            .param("likes", request.likes())
            .param("comments", request.comments())
            .param("shares", request.shares())
            .param("saves", request.saves())
            .param("follows", request.follows())
            .param("sourceKey", request.sourceObservationKey())
            .param("payload", request.rawPayload() == null ? "{}" : request.rawPayload())
            .query(UUID.class)
            .single();
    return new ObservationResponse(id, false);
  }

  private boolean sameToken(String provided, String expected) {
    return MessageDigest.isEqual(
        provided.getBytes(StandardCharsets.UTF_8), expected.getBytes(StandardCharsets.UTF_8));
  }

  public record ObservationRequest(
      UUID videoId,
      UUID variantId,
      String platform,
      String platformContentId,
      Instant publicationTimestamp,
      Instant measurementTimestamp,
      Long views,
      Long reach,
      Long uniqueViewers,
      Long likes,
      Long comments,
      Long shares,
      Long saves,
      Long follows,
      String sourceObservationKey,
      String rawPayload) {}

  public record ObservationResponse(UUID id, boolean duplicate) {}
}
