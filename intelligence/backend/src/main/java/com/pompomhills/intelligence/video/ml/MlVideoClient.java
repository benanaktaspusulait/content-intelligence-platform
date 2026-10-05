package com.pompomhills.intelligence.video.ml;

import com.pompomhills.intelligence.video.VideoService;
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
    return analyse(relativePath, VideoService.CURRENT_ANALYSIS_VERSION);
  }

  public MlAnalysisResponse analyse(String relativePath, String analysisVersion) {
    return analyse(relativePath, analysisVersion, Map.of(), false);
  }

  public MlAnalysisResponse analyse(
      String relativePath, String analysisVersion, Map<String, Object> cachedSemanticVideoEvidence) {
    return analyse(relativePath, analysisVersion, cachedSemanticVideoEvidence, true);
  }

  public MlAnalysisResponse analyse(
      String relativePath,
      String analysisVersion,
      Map<String, Object> cachedSemanticVideoEvidence,
      boolean semanticRequested) {
    return restClient
        .post()
        .uri("/v1/analysis/video")
        .body(new MlAnalysisRequest("v1", relativePath, analysisVersion, cachedSemanticVideoEvidence, semanticRequested))
        .retrieve()
        .body(MlAnalysisResponse.class);
  }

  @SuppressWarnings("unchecked")
  public Map<String, Object> fuseSemanticEvidence(
      Map<String, Object> temporalProfile, Map<String, Object> semanticVideoEvidence) {
    return restClient
        .post()
        .uri("/v1/analysis/semantic-fusion")
        .body(Map.of("temporal_profile", temporalProfile, "semantic_video_evidence", semanticVideoEvidence))
        .retrieve()
        .body(Map.class);
  }

  public record MlAnalysisRequest(
      String contractVersion,
      String relativePath,
      String analysisVersion,
      Map<String, Object> cachedSemanticVideoEvidence,
      boolean semanticRequested) {}

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
      List<Map<String, Object>> darkFrameCandidates,
      Map<String, Object> semanticVideoEvidence) {
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
          List.of(),
          Map.of());
    }

    public double actionDnaScore() {
      return motionHeuristicScore == null ? 0.0 : motionHeuristicScore;
    }

    public double confidence() {
      return measurementConfidence == null ? 0.0 : measurementConfidence;
    }
  }
}
