package com.pompom.creative.evidence;

/** The intelligence backend did not respond within the configured timeout. */
public class ValidationEvidenceTimeoutException extends ValidationEvidenceClientException {
  public ValidationEvidenceTimeoutException(long validationRecordId, Throwable cause) {
    super(
        "Timed out fetching validation evidence for record %d".formatted(validationRecordId),
        cause);
  }
}
