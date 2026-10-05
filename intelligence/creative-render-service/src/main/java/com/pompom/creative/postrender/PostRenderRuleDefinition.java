package com.pompom.creative.postrender;

import java.util.Map;

public record PostRenderRuleDefinition(
    String id,
    String version,
    String family,
    PostRenderSeverity severity,
    String source,
    String operator,
    Object expected,
    String missingEvidence,
    String resultWhenMatched,
    String policyEffect,
    String description) {

  public Map<String, Object> expectedCondition() {
    return Map.of("operator", operator, "expected", expected);
  }
}
