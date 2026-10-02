package com.pompom.creative.evidence;

public abstract class ValidationEvidenceClientException extends RuntimeException {
  protected ValidationEvidenceClientException(String message) {
    super(message);
  }

  protected ValidationEvidenceClientException(String message, Throwable cause) {
    super(message, cause);
  }
}
