package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public record MetaPageInsightsResponse(
    String objectId,
    Availability availability,
    String reason,
    Map<String, Long> metrics,
    List<Snapshot> snapshots,
    String apiVersion) {
  public enum Availability {
    AVAILABLE,
    PARTIAL,
    UNAVAILABLE
  }

  public record Snapshot(Instant measuredAt, Map<String, Long> metrics) {}
}
