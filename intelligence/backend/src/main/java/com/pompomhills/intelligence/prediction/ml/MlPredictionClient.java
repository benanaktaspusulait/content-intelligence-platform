package com.pompomhills.intelligence.prediction.ml;

import java.time.Instant;
import java.util.Map;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class MlPredictionClient {
  private final RestClient rest;

  public MlPredictionClient(RestClient mlRestClient) {
    this.rest = mlRestClient;
  }

  public PredictionResponse prepublish(
      String platform, Map<String, Object> fingerprint, Instant cutoff) {
    return rest.post()
        .uri("/v1/prediction/prepublish")
        .body(new PredictionRequest("v1", platform, fingerprint, cutoff))
        .retrieve()
        .body(PredictionResponse.class);
  }

  public PredictionResponse live(
      String platform,
      Map<String, Object> fingerprint,
      Map<String, Object> liveFeatures,
      Instant cutoff) {
    return rest.post()
        .uri("/v1/prediction/live")
        .body(new LivePredictionRequest("v1", platform, fingerprint, cutoff, liveFeatures))
        .retrieve()
        .body(PredictionResponse.class);
  }

  public record PredictionRequest(
      String contractVersion,
      String platform,
      Map<String, Object> fingerprint,
      Instant knowledgeCutoff) {}

  public record LivePredictionRequest(
      String contractVersion,
      String platform,
      Map<String, Object> fingerprint,
      Instant knowledgeCutoff,
      Map<String, Object> liveFeatures) {}

  public record PredictionResponse(
      String contractVersion,
      String modelVersion,
      String datasetVersion,
      String featureVersion,
      String confidence,
      int comparableSampleSize,
      Map<String, Object> payload) {}
}
