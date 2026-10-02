package com.pompom.creative.intelligence;

public class IntelligenceContentConflictException extends IntelligenceContentClientException {
  public IntelligenceContentConflictException(long contentId, long promptVersionId) {
    super("Content %d and prompt version %d are in conflict".formatted(contentId, promptVersionId));
  }
}
