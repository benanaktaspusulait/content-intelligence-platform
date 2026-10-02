package com.pompomhills.intelligence.quality;

/** Exception thrown when validation request is invalid. */
class QualityValidationException extends RuntimeException {
  private final String errorCode;

  public QualityValidationException(String message, String errorCode) {
    super(message);
    this.errorCode = errorCode;
  }

  public String getErrorCode() {
    return errorCode;
  }
}

/** Exception thrown when ML service is unavailable or returns error. */
class MlServiceException extends RuntimeException {
  public MlServiceException(String message) {
    super(message);
  }

  public MlServiceException(String message, Throwable cause) {
    super(message, cause);
  }
}
