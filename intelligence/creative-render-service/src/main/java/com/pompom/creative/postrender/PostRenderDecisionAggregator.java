package com.pompom.creative.postrender;

import java.util.List;

public class PostRenderDecisionAggregator {
  public PostRenderDecision aggregate(List<PostRenderRuleResult> results) {
    if (results.stream()
        .anyMatch(
            result ->
                result.outcome() == PostRenderOutcome.SERVICE_ERROR
                    && result.severity() == PostRenderSeverity.BLOCKER))
      return PostRenderDecision.SYSTEM_ERROR;
    if (results.stream()
        .anyMatch(
            result ->
                result.outcome() == PostRenderOutcome.FAIL
                    && result.severity() == PostRenderSeverity.BLOCKER))
      return PostRenderDecision.FAIL;
    if (results.stream()
        .anyMatch(
            result ->
                result.reviewRequired()
                    || (result.outcome() == PostRenderOutcome.FAIL
                        && result.severity() != PostRenderSeverity.INFO))) {
      return PostRenderDecision.HUMAN_REVIEW;
    }
    return PostRenderDecision.PASS;
  }
}
