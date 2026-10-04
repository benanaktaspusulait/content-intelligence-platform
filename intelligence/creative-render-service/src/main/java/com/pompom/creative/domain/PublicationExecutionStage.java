package com.pompom.creative.domain;

public enum PublicationExecutionStage {
  QUEUED,
  SUBMITTING,
  COMPLETE,
  FAILED,
  AMBIGUOUS,
  CANCELLED;

  public boolean isTerminal() {
    return this == COMPLETE || this == FAILED || this == AMBIGUOUS || this == CANCELLED;
  }
}
