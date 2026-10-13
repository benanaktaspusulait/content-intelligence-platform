package com.pompomhills.intelligence.quality;

import java.util.LinkedHashMap;
import java.util.Map;

/** Structured failure returned by an ML workflow endpoint. */
public final class MlWorkflowException extends RuntimeException {
  private final int statusCode;
  private final Map<String, Object> diagnostics;

  public MlWorkflowException(int statusCode, Map<String, Object> diagnostics) {
    super(String.valueOf(diagnostics.getOrDefault("detail", "ML workflow request failed")));
    this.statusCode = statusCode;
    this.diagnostics = java.util.Collections.unmodifiableMap(new LinkedHashMap<>(diagnostics));
  }

  public int statusCode() {
    return statusCode;
  }

  public Map<String, Object> diagnostics() {
    return diagnostics;
  }
}
