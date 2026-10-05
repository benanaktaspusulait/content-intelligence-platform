package com.pompomhills.intelligence.video.prompt;

import java.util.List;

public record PromptSourceResolution(
    Status status,
    String videoPath,
    String promptPath,
    String promptText,
    String matchingMethod,
    String confidence,
    int candidateCount,
    List<String> candidates,
    String errorMessage) {
  public enum Status {
    MATCHED_EXACT,
    MATCHED_SIDECAR,
    MATCHED_SINGLE_FOLDER_PROMPT,
    AMBIGUOUS,
    NOT_FOUND,
    ERROR
  }

  public boolean matched() {
    return promptText != null && promptPath != null
        && (status == Status.MATCHED_EXACT || status == Status.MATCHED_SIDECAR
            || status == Status.MATCHED_SINGLE_FOLDER_PROMPT);
  }
}
