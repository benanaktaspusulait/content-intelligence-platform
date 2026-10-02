package com.pompom.creative.intelligence;

public class IntelligenceContentNotFoundException extends IntelligenceContentClientException {
  public IntelligenceContentNotFoundException(long contentId, long promptVersionId) {
    super("No prompt version %d belongs to content %d".formatted(promptVersionId, contentId));
  }
}
