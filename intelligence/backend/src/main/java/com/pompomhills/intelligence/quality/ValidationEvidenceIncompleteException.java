package com.pompomhills.intelligence.quality;

/**
 * Thrown when a validation record exists but is missing or has invalid required evidence fields
 * (legacy pre-evidence rows, negative counts, malformed prompt hash). Stable code: {@code
 * VALIDATION_EVIDENCE_INCOMPLETE}.
 */
public class ValidationEvidenceIncompleteException extends RuntimeException {
  public static final String ERROR_CODE = "VALIDATION_EVIDENCE_INCOMPLETE";

  private final long validationRecordId;

  public ValidationEvidenceIncompleteException(long validationRecordId, String reason) {
    super(
        "Validation record %d is missing required evidence: %s"
            .formatted(validationRecordId, reason));
    this.validationRecordId = validationRecordId;
  }

  public long getValidationRecordId() {
    return validationRecordId;
  }
}
