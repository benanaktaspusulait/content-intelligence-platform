package com.pompom.creative.evidence;

/** The intelligence backend is unreachable or returned a server error. */
public class ValidationEvidenceServiceException extends ValidationEvidenceClientException {
  public ValidationEvidenceServiceException(String message) {
    super(message);
  }

  public ValidationEvidenceServiceException(String message, Throwable cause) {
    super(message, cause);
  }
}
