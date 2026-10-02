package com.pompom.creative.evidence;

/** The intelligence backend has no validation record with the requested ID. */
public class ValidationEvidenceNotFoundException extends ValidationEvidenceClientException {
  private final long validationRecordId;

  public ValidationEvidenceNotFoundException(long validationRecordId) {
    super("No validation evidence exists with id %d".formatted(validationRecordId));
    this.validationRecordId = validationRecordId;
  }

  public long getValidationRecordId() {
    return validationRecordId;
  }
}
