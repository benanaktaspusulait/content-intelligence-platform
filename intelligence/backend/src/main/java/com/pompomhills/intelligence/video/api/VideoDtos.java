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
      UUID variantId) {}

  public record MetadataFile(String relativePath, String content) {}

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
      String analysisVersion) {}
}
