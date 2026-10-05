package com.pompomhills.intelligence.video.api;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class VideoDtos {
  private VideoDtos() {}

  public record IngestRequest(@NotBlank String relativePath, UUID seriesId) {}

  public record DirectoryIngestRequest(
      @NotBlank String relativeDirectory, UUID seriesId, boolean recursive) {}

  public record DirectoryIngestResponse(
      String relativeDirectory,
      int discovered,
      List<VideoResponse> ingested,
      List<IngestError> errors) {}

  public record IngestError(String relativePath, String message) {}

  public record MediaDirectory(String name, String relativePath, long videoCount) {}

  public record MediaFile(
      String name,
      String relativePath,
      Long sizeBytes,
      Instant modifiedAt,
      boolean ingested,
      UUID videoId,
      String status,
      UUID variantId,
      String thumbnailPath,
      List<MediaCharacter> characters) {}

  public record MediaCharacter(UUID id, String name, String participation, String role,
      String source, String confidence) {}

  public record MetadataFile(String relativePath, String content) {}

  public record PromptFile(String name, String relativePath, String folder, Long sizeBytes, Instant modifiedAt) {}

  public record PromptDirectory(String name, String relativePath, long promptCount) {}

  public record MetadataUpdateRequest(
      @jakarta.validation.constraints.NotBlank String relativePath, String content) {}

  public record VideoResponse(
      UUID id,
      String originalFilename,
      String relativePath,
      long durationMs,
      int width,
      int height,
      double fps,
      double aspectRatio,
      String codec,
      boolean audioPresent,
      String status,
      UUID seriesId,
      Instant ingestedAt) {}

  public record AnalysisResponse(
      UUID analysisId,
      UUID videoId,
      String primaryEngine,
      java.util.List<String> secondaryEngines,
      String classification,
      double creativeStructureMatch,
      double confidence,
      Map<String, Object> features,
      String storyboardPath) {}

  public record AnalysisStatusResponse(
      UUID videoId,
      boolean hasCompletedAnalysis,
      String jobId,
      String jobState,
      Integer attempts,
      Integer maxAttempts,
      String errorMessage,
      UUID analysisId,
      String classification,
      Double actionDnaScore,
      Double confidence,
      String reason,
      String storyboardPath,
      String analysisVersion,
      String analysisType,
      Double motionHeuristicScore,
      Double measurementConfidence,
      Map<String, Object> measurementQuality,
      Map<String, Object> sampling,
      Map<String, Object> motion,
      Map<String, Object> visualSimilarity,
      List<Map<String, Object>> darkFrameCandidates,
      List<Map<String, Object>> timeline,
      Map<String, Object> temporalProfile,
      Map<String, Object> presentation,
      Map<String, Object> semanticVideoEvidence) {
    public AnalysisStatusResponse(
        UUID videoId,
        boolean hasCompletedAnalysis,
        String jobId,
        String jobState,
        Integer attempts,
        Integer maxAttempts,
        String errorMessage,
        UUID analysisId,
        String classification,
        Double actionDnaScore,
        Double confidence,
        String reason,
        String storyboardPath,
        String analysisVersion) {
      this(videoId, hasCompletedAnalysis, jobId, jobState, attempts, maxAttempts, errorMessage,
          analysisId, classification, actionDnaScore, confidence, reason, storyboardPath,
          analysisVersion, "LEGACY", actionDnaScore, confidence, Map.of(), Map.of(), Map.of(), Map.of(), List.of(), List.of(), Map.of(), Map.of(), Map.of());
    }
  }
}
