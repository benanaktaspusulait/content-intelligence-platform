package com.pompomhills.intelligence.quality;

/**
 * Immutable render-authorization decision for a validation record.
 *
 * <p>Only {@link #RENDER_READY} evidence may authorize a render job. A record can report this
 * status only when every required deterministic, semantic, producibility, and independent
 * revalidation field is present and consistent - see {@link ValidationEvidenceService}.
 */
public enum ValidationDecisionStatus {
  RENDER_READY,
  NEEDS_REVISION,
  BLOCKED,
  SERVICE_ERROR
}
