package com.pompomhills.intelligence.video.ml;

import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class MlVideoClient {
  private final RestClient restClient;

  public MlVideoClient(RestClient mlRestClient) {
    this.restClient = mlRestClient;
  }

  public MlAnalysisResponse analyse(String relativePath) {
    return restClient
        .post()
        .uri("/v1/analysis/video")
        .body(new MlAnalysisRequest("v1", relativePath))
        .retrieve()
        .body(MlAnalysisResponse.class);
  }

  public record MlAnalysisRequest(String contractVersion, String relativePath) {}

  public record Metadata(
      long durationMs,
      int width,
      int height,
      double fps,
      double aspectRatio,
      String codec,
      boolean audioPresent,
      String sha256) {}

  public record MlAnalysisResponse(
      String contractVersion,
      Metadata metadata,
      String analysisVersion,
      String analysisType,
      String primaryEngine,
      List<String> secondaryEngines,
      String classification,
      Double motionHeuristicScore,
      Double measurementConfidence,
      Map<String, Object> measurementQuality,
      String reason,
      String storyboardPath,
      List<Map<String, Object>> timeline,
      Map<String, Object> features,
      Map<String, Object> evidence,
      Map<String, Object> sampling,
      Map<String, Object> motion,
      Map<String, Object> visualSimilarity,
      List<Map<String, Object>> darkFrameCandidates) {
    public MlAnalysisResponse(
        String contractVersion,
        Metadata metadata,
        String analysisVersion,
        String primaryEngine,
        List<String> secondaryEngines,
        String classification,
        double actionDnaScore,
        double confidence,
        String reason,
        String storyboardPath,
        List<Map<String, Object>> timeline,
        Map<String, Object> features,
        Map<String, Object> evidence) {
      this(
          contractVersion,
          metadata,
          analysisVersion,
          "LEGACY",
          primaryEngine,
          secondaryEngines,
          classification,
          actionDnaScore,
          confidence,
          Map.of(),
          reason,
          storyboardPath,
          timeline,
          features,
          evidence,
          Map.of(),
          Map.of(),
          Map.of(),
          List.of());
    }

    public double actionDnaScore() {
      return motionHeuristicScore == null ? 0.0 : motionHeuristicScore;
    }

    public double confidence() {
      return measurementConfidence == null ? 0.0 : measurementConfidence;
    }
  }
}
