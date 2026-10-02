package com.pompom.creative.evidence;

/**
 * The intelligence backend reports the validation record exists but is not complete evidence (422,
 * {@code VALIDATION_EVIDENCE_INCOMPLETE}). Distinct from {@link
 * ValidationEvidenceNotFoundException}: the record exists but can never authorize render.
 */
public class ValidationEvidenceIncompleteRemoteException extends ValidationEvidenceClientException {
  private final long validationRecordId;

  public ValidationEvidenceIncompleteRemoteException(long validationRecordId) {
    super("Validation record %d is not complete evidence".formatted(validationRecordId));
    this.validationRecordId = validationRecordId;
  }

  public long getValidationRecordId() {
    return validationRecordId;
  }
}
