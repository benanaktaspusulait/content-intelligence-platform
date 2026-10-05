package com.pompom.creative.postrender;

import java.time.Instant;
import java.util.Map;

public record PostRenderRuleResult(
    String ruleId,
    String ruleVersion,
    String rulesetVersion,
    String stage,
    String family,
    PostRenderSeverity severity,
    PostRenderOutcome outcome,
    String message,
    Object actualValue,
    Map<String, Object> expectedCondition,
    Map<String, Object> evidenceReferences,
    String evaluator,
    boolean reviewRequired,
    Instant evaluatedAt) {}
