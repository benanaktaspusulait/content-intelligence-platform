package com.pompomhills.intelligence.content;

public class ContentPromptNotFoundException extends RuntimeException {
  private final long contentId;
  private final long promptVersionId;

  public ContentPromptNotFoundException(long contentId, long promptVersionId) {
    super("No prompt version %d belongs to content %d".formatted(promptVersionId, contentId));
    this.contentId = contentId;
    this.promptVersionId = promptVersionId;
  }

  public long getContentId() {
    return contentId;
  }

  public long getPromptVersionId() {
    return promptVersionId;
  }
}
