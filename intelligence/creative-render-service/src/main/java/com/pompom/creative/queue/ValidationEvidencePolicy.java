package com.pompom.creative.queue;

import com.pompom.creative.evidence.ValidationEvidenceDto;
import java.time.Instant;
import org.springframework.stereotype.Component;

/**
 * Enforces every hard precondition from the design doc (Slice B item 5, "Enforce immutable
 * validation evidence") before a render job may be queued. {@link #validate} returns normally only
 * when every predicate passes; otherwise it throws {@link ValidationEvidenceRejectedException} with
 * a stable {@code errorCode}. The caller ({@code RenderJobQueueService}) must create zero rows when
 * this method throws.
 *
 * <p>Order matters only for which single error code is reported first when multiple predicates
 * fail; every predicate is still independently enforced and tested.
 */
@Component
public class ValidationEvidencePolicy {

  public void validate(QueueRenderJobRequest request, ValidationEvidenceDto evidence, Instant now) {
    if (!"RENDER_READY".equals(evidence.status())) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_NOT_RENDER_READY",
          "Validation record %d has status %s, not RENDER_READY"
              .formatted(evidence.validationRecordId(), evidence.status()));
    }
    if (evidence.blockerCount() > 0) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_HAS_BLOCKERS",
          "Validation record %d has %d blocker(s)"
              .formatted(evidence.validationRecordId(), evidence.blockerCount()));
    }
    if (evidence.criticalCount() > 0) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_HAS_CRITICALS",
          "Validation record %d has %d critical(s)"
              .formatted(evidence.validationRecordId(), evidence.criticalCount()));
    }
    if (evidence.independentRevalidationId() == null
        || evidence.independentlyRevalidatedAt() == null) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_NOT_INDEPENDENTLY_REVALIDATED",
          "Validation record %d has no independent revalidation"
              .formatted(evidence.validationRecordId()));
    }
    if (evidence.contentId() != request.contentId()
        || evidence.promptVersionId() != request.promptVersionId()) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_IDENTITY_MISMATCH",
          "Validation record %d is linked to content %d/prompt version %d, not the requested %d/%d"
              .formatted(
                  evidence.validationRecordId(),
                  evidence.contentId(),
                  evidence.promptVersionId(),
                  request.contentId(),
                  request.promptVersionId()));
    }
    if (evidence.promptSha256() == null || !evidence.promptSha256().matches("^[0-9a-f]{64}$")) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_PROMPT_HASH_INVALID",
          "Validation record %d has a missing or malformed prompt hash"
              .formatted(evidence.validationRecordId()));
    }
    if (request.requestPromptSha256() != null
        && !request.requestPromptSha256().equals(evidence.promptSha256())) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_PROMPT_HASH_MISMATCH",
          "Validation record %d's prompt hash does not match the request's expected hash"
              .formatted(evidence.validationRecordId()));
    }
    if (evidence.deterministicRulesetVersion() == null
        || evidence.semanticProvider() == null
        || evidence.semanticModelVersion() == null
        || evidence.producibilityValidatorVersion() == null) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_VERSIONS_INCOMPLETE",
          "Validation record %d is missing a required ruleset/semantic/producibility version identity"
              .formatted(evidence.validationRecordId()));
    }
    if (evidence.expiresAt() == null || !evidence.expiresAt().isAfter(now)) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_EXPIRED",
          "Validation record %d evidence has no expiry or has expired"
              .formatted(evidence.validationRecordId()));
    }
  }
}
