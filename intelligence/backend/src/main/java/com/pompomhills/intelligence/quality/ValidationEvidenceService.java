package com.pompomhills.intelligence.quality;

import java.time.Clock;
import java.time.Instant;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Reads immutable validation evidence for the internal evidence endpoint consumed by
 * creative-render-service's render queue gate.
 *
 * <p>{@link #getEvidence(long)} never trusts the stored {@code status} column verbatim: it
 * recomputes the decision status from the record's actual field completeness on every read, so a
 * record can report {@link ValidationDecisionStatus#RENDER_READY} only when every deterministic,
 * semantic, producibility, and independent-revalidation field is present and internally consistent.
 * This closes two gaps at once: legacy rows created before this evidence model existed, and rows
 * created today whose semantic/producibility/independent-revalidation identity the ML service
 * cannot yet populate (that pipeline lands in a later slice) - both must resolve to a non-ready
 * status rather than a fabricated render authorization.
 */
@Service
public class ValidationEvidenceService {

  private static final Pattern SHA256_PATTERN = Pattern.compile("^[0-9a-f]{64}$");

  private final QualityValidationRepository repository;
  private final Clock clock;

  @Autowired
  public ValidationEvidenceService(QualityValidationRepository repository) {
    this(repository, Clock.systemUTC());
  }

  ValidationEvidenceService(QualityValidationRepository repository, Clock clock) {
    this.repository = repository;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public ValidationEvidenceResponse getEvidence(long validationRecordId) {
    QualityValidationEntity entity =
        repository
            .findById(validationRecordId)
            .orElseThrow(() -> new ValidationEvidenceNotFoundException(validationRecordId));

    requireCompleteBaseEvidence(entity);

    ValidationDecisionStatus status = resolveStatus(entity);

    return new ValidationEvidenceResponse(
        entity.getId(),
        entity.getContentId(),
        entity.getPromptVersionId(),
        entity.getPromptSha256(),
        status,
        entity.getBlockerCount(),
        entity.getCriticalCount(),
        entity.getWarningCount(),
        entity.getDeterministicRulesetVersion(),
        entity.getSemanticProvider(),
        entity.getSemanticModelVersion(),
        entity.getProducibilityValidatorVersion(),
        entity.getIndependentRevalidationId(),
        entity.getIndependentlyRevalidatedAt(),
        entity.getValidatedAt(),
        entity.getExpiresAt());
  }

  /**
   * Fields that must always be present for a record to be usable evidence at all, regardless of
   * what the final decision status turns out to be. A record failing this check is not merely
   * NEEDS_REVISION - it is not evidence; the caller must treat it as if it never existed.
   */
  private void requireCompleteBaseEvidence(QualityValidationEntity entity) {
    long id = entity.getId();
    if (entity.getContentId() == null) {
      throw new ValidationEvidenceIncompleteException(id, "contentId is missing");
    }
    if (entity.getPromptVersionId() == null) {
      throw new ValidationEvidenceIncompleteException(id, "promptVersionId is missing");
    }
    if (entity.getPromptSha256() == null
        || !SHA256_PATTERN.matcher(entity.getPromptSha256()).matches()) {
      throw new ValidationEvidenceIncompleteException(id, "promptSha256 is missing or malformed");
    }
    if (entity.getBlockerCount() == null || entity.getBlockerCount() < 0) {
      throw new ValidationEvidenceIncompleteException(id, "blockerCount is missing or negative");
    }
    if (entity.getCriticalCount() == null || entity.getCriticalCount() < 0) {
      throw new ValidationEvidenceIncompleteException(id, "criticalCount is missing or negative");
    }
    if (entity.getWarningCount() == null || entity.getWarningCount() < 0) {
      throw new ValidationEvidenceIncompleteException(id, "warningCount is missing or negative");
    }
    if (entity.getDeterministicRulesetVersion() == null) {
      throw new ValidationEvidenceIncompleteException(id, "deterministicRulesetVersion is missing");
    }
    if (entity.getValidatedAt() == null) {
      throw new ValidationEvidenceIncompleteException(id, "validatedAt is missing");
    }
  }

  /**
   * Recomputes the authoritative decision status. RENDER_READY requires zero blockers/criticals and
   * every semantic, producibility, and independent-revalidation field present; any gap downgrades
   * to NEEDS_REVISION even if the stored status column says RENDER_READY.
   */
  private ValidationDecisionStatus resolveStatus(QualityValidationEntity entity) {
    ValidationDecisionStatus storedStatus = parseStatus(entity.getStatus());
    if (storedStatus != ValidationDecisionStatus.RENDER_READY) {
      return storedStatus;
    }
    if (entity.getBlockerCount() > 0 || entity.getCriticalCount() > 0) {
      return ValidationDecisionStatus.NEEDS_REVISION;
    }
    if (entity.getSemanticProvider() == null
        || entity.getSemanticModelVersion() == null
        || entity.getProducibilityValidatorVersion() == null) {
      return ValidationDecisionStatus.NEEDS_REVISION;
    }
    if (entity.getIndependentRevalidationId() == null
        || entity.getIndependentlyRevalidatedAt() == null) {
      return ValidationDecisionStatus.NEEDS_REVISION;
    }
    // Absence of expiresAt is never treated as "never expires" - no freshness policy means the
    // evidence has no proven freshness, so it must not authorize render.
    Instant expiresAt = entity.getExpiresAt();
    if (expiresAt == null || !expiresAt.isAfter(clock.instant())) {
      return ValidationDecisionStatus.NEEDS_REVISION;
    }
    return ValidationDecisionStatus.RENDER_READY;
  }

  private ValidationDecisionStatus parseStatus(String status) {
    try {
      return ValidationDecisionStatus.valueOf(status);
    } catch (IllegalArgumentException | NullPointerException ex) {
      return ValidationDecisionStatus.SERVICE_ERROR;
    }
  }
}
