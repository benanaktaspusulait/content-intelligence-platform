package com.pompomhills.intelligence.video.workbench;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class VideoAnalysisWorkbenchDtos {
  private VideoAnalysisWorkbenchDtos() {}

  public record PageResponse(
      List<Row> content, int page, int size, long totalElements, int totalPages, Summary summary) {}

  public record Summary(long total, long current, long stale, long missing, long running,
      long failed, long ready, long review, long regenerate, long editPlan, long incomplete) {}

  public record Row(
      UUID id,
      String title,
      String relativePath,
      long durationMs,
      int width,
      int height,
      String videoStatus,
      Instant ingestedAt,
      String analysisStatus,
      String analysisVersion,
      String classification,
      Double confidence,
      String reason,
      String triage,
      String publicationState,
      Long observedViews,
      Integer observationCount,
      List<CharacterAssociation> characters) {}

  public record CharacterAssociation(UUID id, String name, String participation, String role,
      String source, Double confidence, String evidenceReference) {}

  public record BulkRequest(List<UUID> videoIds, boolean allMatching, String analysisStatus,
      String triage, String publicationState, UUID characterId, String characterRole,
      String query, boolean reanalyzeSelected) {}

  public record BulkResponse(int requested, int accepted, int skipped, int alreadyRunning,
      int failed, List<UUID> jobIds) {}
}
