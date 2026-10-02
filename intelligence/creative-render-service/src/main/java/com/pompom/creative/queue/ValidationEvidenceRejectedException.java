package com.pompom.creative.queue;

/**
 * Thrown by {@link ValidationEvidencePolicy} when a queue request fails any approved
 * render-authorization predicate. Carries a stable {@code errorCode} so callers (and the HTTP
 * problem response) can distinguish rejection reasons without parsing free text.
 */
public class ValidationEvidenceRejectedException extends RuntimeException {
  private final String errorCode;

  public ValidationEvidenceRejectedException(String errorCode, String message) {
    super(message);
    this.errorCode = errorCode;
  }

  public String getErrorCode() {
    return errorCode;
  }
}
