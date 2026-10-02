package com.pompom.creative.intelligence;

public class IntelligenceContentTimeoutException extends IntelligenceContentClientException {
  public IntelligenceContentTimeoutException(
      long contentId, long promptVersionId, Throwable cause) {
    super(
        "Timed out loading prompt version %d for content %d".formatted(promptVersionId, contentId),
        cause);
  }
}
