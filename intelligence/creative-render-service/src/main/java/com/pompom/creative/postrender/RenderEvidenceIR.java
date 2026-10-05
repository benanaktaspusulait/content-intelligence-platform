package com.pompom.creative.postrender;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/** Immutable measured evidence snapshot consumed by the post-render policy. */
public record RenderEvidenceIR(
    UUID assetId,
    UUID renderJobId,
    UUID renderAttemptId,
    UUID videoId,
    UUID variantId,
    String evidenceVersion,
    Instant capturedAt,
    Map<String, String> analyzerVersions,
    Map<String, Object> evidence) {

  public Object valueAt(String source) {
    Object current = evidence;
    for (String segment : source.split("\\.")) {
      if (!(current instanceof Map<?, ?> map) || !map.containsKey(segment)) return null;
      current = map.get(segment);
    }
    return current;
  }

  public EvidenceStatus statusAt(String source) {
    String[] segments = source.split("\\.");
    if (segments.length == 0) return EvidenceStatus.UNKNOWN;
    StringBuilder statusPath = new StringBuilder();
    for (int i = 0; i < segments.length - 1; i++) {
      if (i > 0) statusPath.append('.');
      statusPath.append(segments[i]);
    }
    if (statusPath.length() > 0) statusPath.append('.');
    statusPath.append(segments[segments.length - 1]).append("Status");
    Object status = valueAt(statusPath.toString());
    if (status instanceof EvidenceStatus evidenceStatus) return evidenceStatus;
    if (status instanceof String value) {
      try {
        return EvidenceStatus.valueOf(value);
      } catch (IllegalArgumentException ignored) {
        return EvidenceStatus.UNKNOWN;
      }
    }
    return valueAt(source) == null ? EvidenceStatus.UNKNOWN : EvidenceStatus.AVAILABLE;
  }
}
