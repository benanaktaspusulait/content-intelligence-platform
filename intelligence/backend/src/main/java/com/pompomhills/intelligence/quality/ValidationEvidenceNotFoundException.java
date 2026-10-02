package com.pompomhills.intelligence.quality;

/**
 * Thrown when no validation record exists for the requested ID. Stable code: {@code
 * VALIDATION_EVIDENCE_NOT_FOUND}.
 */
public class ValidationEvidenceNotFoundException extends RuntimeException {
  public static final String ERROR_CODE = "VALIDATION_EVIDENCE_NOT_FOUND";

  private final long validationRecordId;

  public ValidationEvidenceNotFoundException(long validationRecordId) {
    super("No validation record exists with id %d".formatted(validationRecordId));
    this.validationRecordId = validationRecordId;
  }

  public long getValidationRecordId() {
    return validationRecordId;
  }
}
