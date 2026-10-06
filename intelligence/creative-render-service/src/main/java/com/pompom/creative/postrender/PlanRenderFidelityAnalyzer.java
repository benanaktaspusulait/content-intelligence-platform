package com.pompom.creative.postrender;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Compares explicit planned payoff intent with observed payoff evidence conservatively. */
@Component
public class PlanRenderFidelityAnalyzer {
  public Map<String, Object> compare(Map<String, Object> contract, Map<String, Object> observed) {
    Map<String, Object> result = new LinkedHashMap<>();
    if (contract == null || contract.isEmpty()) {
      result.put("status", "CONTRACT_NOT_AVAILABLE_LEGACY");
      result.put("payoff", dimension("UNKNOWN", "UNKNOWN", "UNKNOWN", "HUMAN_REVIEW"));
      return result;
    }
    Map<String, Object> intent = map(contract.get("intent"));
    Map<String, Object> payoff = map(intent.get("payoffIntent"));
    String planned = first(payoff, "emphasisStrategy", "emphasis", "motionStrategy");
    String direction = String.valueOf(observed.getOrDefault("contrastDirection", "UNKNOWN"));
    if (planned == null || planned.isBlank()) {
      result.put("status", "AVAILABLE");
      result.put("payoff", dimension("NOT_EVALUATED", "NOT_EVALUATED", "UNKNOWN", "EDIT_PLAN"));
      return result;
    }
    String normalized = planned.toUpperCase();
    String fidelity;
    String rootCause = "UNKNOWN";
    String action = "HUMAN_REVIEW";
    if (direction.equals("UNKNOWN")) {
      fidelity = "UNKNOWN";
    } else if (normalized.contains("REDUCTION")) {
      fidelity = direction.equals("REDUCTION") ? "MATCH" : "MISMATCH";
      rootCause = fidelity.equals("MISMATCH") ? "RENDER_FIDELITY_ISSUE" : "UNKNOWN";
      action = fidelity.equals("MISMATCH") ? "REGENERATE" : "NO_ACTION";
    } else if (normalized.contains("SPIKE")) {
      fidelity = direction.equals("INCREASE") ? "MATCH" : "MISMATCH";
      rootCause = fidelity.equals("MISMATCH") ? "RENDER_FIDELITY_ISSUE" : "UNKNOWN";
      action = fidelity.equals("MISMATCH") ? "REGENERATE" : "NO_ACTION";
    } else {
      fidelity = "NOT_EVALUATED";
      action = "HUMAN_REVIEW";
    }
    result.put("status", "AVAILABLE");
    result.put("payoff", dimension(fidelity, planned, direction, action));
    result.put("rootCause", rootCause);
    result.put("recommendedActionType", action);
    return result;
  }

  private Map<String, Object> dimension(
      String fidelity, String planned, String observed, String action) {
    return Map.of(
        "fidelity",
        fidelity,
        "planned",
        planned,
        "observed",
        observed,
        "recommendedActionType",
        action);
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> map(Object value) {
    return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
  }

  private String first(Map<String, Object> map, String... keys) {
    for (String key : keys) if (map.get(key) != null) return String.valueOf(map.get(key));
    return null;
  }
}
