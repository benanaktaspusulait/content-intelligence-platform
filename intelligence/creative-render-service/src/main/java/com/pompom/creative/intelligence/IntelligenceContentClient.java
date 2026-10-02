package com.pompom.creative.intelligence;

public interface IntelligenceContentClient {
  ContentPromptSnapshot fetch(long contentId, long promptVersionId);
}
