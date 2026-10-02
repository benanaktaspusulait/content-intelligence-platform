package com.pompom.creative.intelligence;

public abstract class IntelligenceContentClientException extends RuntimeException {
  protected IntelligenceContentClientException(String message) {
    super(message);
  }

  protected IntelligenceContentClientException(String message, Throwable cause) {
    super(message, cause);
  }
}
