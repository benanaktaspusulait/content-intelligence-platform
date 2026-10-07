package com.pompom.publishercontract;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

/** Provider-neutral error categories returned in {@link PublishResult#errorClass()}. */
public enum PublishErrorClass {
  VALIDATION("validation"),
  AUTHENTICATION("authentication"),
  AUTHORIZATION("authorization"),
  RATE_LIMITED("rate_limited"),
  TRANSIENT("transient"),
  PROVIDER_REJECTED("provider_rejected"),
  UNSUPPORTED("unsupported"),
  DUPLICATE("duplicate"),
  RECONCILIATION_REQUIRED("reconciliation_required"),
  UNKNOWN("unknown");

  private final String wireValue;

  PublishErrorClass(String wireValue) {
    this.wireValue = wireValue;
  }

  @JsonValue
  public String wireValue() {
    return wireValue;
  }

  @JsonCreator
  public static PublishErrorClass fromWireValue(String wireValue) {
    return Arrays.stream(values())
        .filter(errorClass -> errorClass.wireValue.equals(wireValue))
        .findFirst()
        .orElseThrow(
            () -> new IllegalArgumentException("Unknown publish error class: " + wireValue));
  }
}
