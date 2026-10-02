package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Read-only analytics for a single Instagram Reel: the current live metric read plus the
 * append-only history of previously captured snapshots. Unavailable metrics are null, never zero.
 */
public record MetaReelAnalyticsResponse(
    String mediaId,
    String mediaType,
    String mediaProductType,
    String caption,
    String permalink,
    Instant publishedAt,
    String thumbnailUrl,
    MetaReelsResponse.LocalMatch localMatch,
    MetricAvailability availability,
    String unavailableReason,
    Metrics live,
    List<Snapshot> history,
    String apiVersion) {

  public enum MetricAvailability {
    NOT_REQUESTED,
    AVAILABLE,
    PARTIAL,
    UNAVAILABLE
  }

  /** Metric values are nullable; a null means the platform did not report that metric. */
  public record Metrics(Long views, Long reach, Long shares, Long saved, Long totalInteractions) {}

  public record Snapshot(
      UUID observationId,
      UUID collectionRunId,
      Instant measuredAt,
      MetricAvailability availability,
      String unavailableReason,
      Metrics metrics) {}
}
