package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PostRenderAssessmentAggregatorTest {
  private final PostRenderAssessmentAggregator aggregator = new PostRenderAssessmentAggregator();

  @Test
  void blockerServiceFailureIsIncompleteRatherThanAFalseCreativeGrade() {
    PostRenderRuleResult result =
        result(PostRenderSeverity.BLOCKER, PostRenderOutcome.SERVICE_ERROR, false);
    PostRenderAssessment assessment = aggregator.aggregate(evidence(), List.of(result));

    assertThat(assessment.grade()).isEqualTo("INCOMPLETE");
    assertThat(assessment.evidenceCoveragePercent()).isZero();
  }

  @Test
  void cleanEvaluatedEvidenceIsGradeA() {
    PostRenderRuleResult result = result(PostRenderSeverity.INFO, PostRenderOutcome.PASS, false);
    PostRenderAssessment assessment = aggregator.aggregate(evidence(), List.of(result));

    assertThat(assessment.grade()).isEqualTo("A");
    assertThat(assessment.evidenceCoveragePercent()).isEqualTo(100);
  }

  private PostRenderRuleResult result(
      PostRenderSeverity severity, PostRenderOutcome outcome, boolean review) {
    return new PostRenderRuleResult(
        "TEST",
        "1.0",
        "TEST",
        "POST_RENDER",
        "TEST",
        severity,
        outcome,
        "test message",
        null,
        Map.of(),
        Map.of(),
        "test",
        review,
        Instant.now());
  }

  private RenderEvidenceIR evidence() {
    return new RenderEvidenceIR(
        UUID.randomUUID(),
        UUID.randomUUID(),
        UUID.randomUUID(),
        null,
        null,
        "render-evidence-v2",
        Instant.now(),
        Map.of(),
        Map.of(
            "payoff", Map.of("status", "NOT_AVAILABLE"),
            "motion", Map.of("motionHeuristicScore", 80),
            "visualSimilarity", Map.of("firstLastSimilarity", 0.8)));
  }
}
