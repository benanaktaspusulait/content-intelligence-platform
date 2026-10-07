package com.pompom.publishercontract;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

/** Normalized lifecycle status for an internal publisher operation. */
public enum PublishStatus {
  ACCEPTED("accepted"),
  COMPLETED("completed"),
  FAILED("failed"),
  RECONCILIATION_REQUIRED("reconciliation_required");

  private final String wireValue;

  PublishStatus(String wireValue) {
    this.wireValue = wireValue;
  }

  @JsonValue
  public String wireValue() {
    return wireValue;
  }

  @JsonCreator
  public static PublishStatus fromWireValue(String wireValue) {
    return Arrays.stream(values())
        .filter(status -> status.wireValue.equals(wireValue))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Unknown publish status: " + wireValue));
  }
}
