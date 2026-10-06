package com.pompomhills.intelligence.video;

import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Shared availability predicate for persisted semantic evidence and local dependents. */
final class SemanticEvidenceAvailability {
  private static final Set<String> AVAILABLE = Set.of("COMPLETED", "PARTIAL", "CACHE_HIT");

  private SemanticEvidenceAvailability() {}

  static boolean isAvailable(Map<String, Object> evidence) {
    if (evidence == null || evidence.isEmpty()) return false;
    String status = String.valueOf(evidence.getOrDefault("status", "UNKNOWN"))
        .toUpperCase(Locale.ROOT);
    return AVAILABLE.contains(status) && evidence.get("provenance") instanceof Map<?, ?>;
  }
}
