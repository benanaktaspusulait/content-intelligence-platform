package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.UUID;

/** Result of capturing a single append-only read-only analytics snapshot. */
public record MetaSnapshotResponse(
    String mediaId,
    UUID observationId,
    UUID collectionRunId,
    Instant measuredAt,
    boolean persisted,
    MetaReelsResponse.LocalMatch localMatch,
    MetaReelAnalyticsResponse.MetricAvailability availability,
    String unavailableReason,
    MetaReelAnalyticsResponse.Metrics metrics) {}
