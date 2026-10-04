package com.pompom.creative.metrics;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.PublicationJob;
import java.time.Instant;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

/** Sends observed metrics to the backend-owned append-only evidence ledger. */
@Service
@Slf4j
public class PerformanceObservationPublisher {

  private final RestClient client;
  private final ObjectMapper objectMapper;
  private final String bridgeToken;

  public PerformanceObservationPublisher(
      RestClient.Builder builder,
      ObjectMapper objectMapper,
      @Value("${pompom.intelligence-base-url:http://localhost:8080}") String baseUrl,
      @Value("${pompom.observation-bridge-token:}") String bridgeToken) {
    this.client = builder.baseUrl(baseUrl).build();
    this.objectMapper = objectMapper;
    this.bridgeToken = bridgeToken;
  }

  public void publish(PublicationJob job, MetricsCollectionJob collectionJob, VideoMetrics metrics) {
    if (bridgeToken.isBlank()) {
      throw new IllegalStateException("Observation bridge token is not configured");
    }
    try {
      client
          .post()
          .uri("/api/v1/performance/observations")
          .header("X-Internal-Observation-Token", bridgeToken)
          .body(
              new Request(
                  job.getVideoId(),
                  job.getVariantId(),
                  job.getPlatform().name(),
                  job.getPlatformVideoId(),
                  job.getCompletedAt(),
                  metrics.getCollectedAt() == null ? Instant.now() : metrics.getCollectedAt(),
                  metrics.getViews(),
                  metrics.getReach(),
                  null,
                  metrics.getLikes(),
                  metrics.getComments(),
                  metrics.getShares(),
                  metrics.getSaves(),
                  null,
                  "creative-render:" + job.getId() + ":" + collectionJob.getCollectionPoint(),
                  objectMapper.writeValueAsString(metrics)))
          .retrieve()
          .toBodilessEntity();
    } catch (Exception error) {
      throw new IllegalStateException("Canonical performance observation bridge failed", error);
    }
  }

  private record Request(
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
}
