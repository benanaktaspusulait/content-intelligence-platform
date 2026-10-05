package com.pompom.creative.api.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.postrender.PostRenderEvaluation;
import com.pompom.creative.postrender.PostRenderEvaluationRepository;
import com.pompom.creative.postrender.PostRenderAssessmentEntity;
import com.pompom.creative.postrender.PostRenderAssessmentRepository;
import com.pompom.creative.postrender.PostRenderRuleResultEntity;
import com.pompom.creative.postrender.PostRenderRuleResultRepository;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/post-render/evaluations")
@RequiredArgsConstructor
public class PostRenderEvaluationController {
  private final PostRenderEvaluationRepository evaluations;
  private final PostRenderRuleResultRepository results;
  private final PostRenderAssessmentRepository assessments;
  private final ObjectMapper objectMapper;

  @GetMapping("/{id}")
  public ResponseEntity<EvaluationView> get(@PathVariable UUID id) {
    return evaluations.findById(id)
        .map(evaluation -> ResponseEntity.ok(new EvaluationView(
            evaluation.getId(), evaluation.getRenderAsset().getId(), evaluation.getRenderAttemptId(),
            evaluation.getEvidenceVersion(), evaluation.getPostRenderRulesetVersion(),
            evaluation.getAnalyzerVersions(), evaluation.getEvidenceSnapshot(),
            evaluation.getOverallDecision().name(), evaluation.isHumanReviewRequired(),
            evaluation.getHumanDecision(), evaluation.getStartedAt(), evaluation.getCompletedAt(),
            assessments.findByEvaluationId(id).map(this::assessment).orElse(null),
            results.findByEvaluationIdOrderByRuleId(id).stream().map(this::rule).toList())))
        .orElseGet(() -> ResponseEntity.notFound().build());
  }

  private RuleView rule(PostRenderRuleResultEntity value) {
    return new RuleView(value.getRuleId(), value.getRuleVersion(), value.getRulesetVersion(),
        value.getStage(), value.getFamily(), value.getSeverity().name(), value.getOutcome().name(),
        value.getMessage(), parse(value.getActualValue()), parse(value.getExpectedCondition()),
        parse(value.getEvidenceReferences()), value.getEvaluator(), value.isReviewRequired(),
        value.getEvaluatedAt());
  }

  private AssessmentView assessment(PostRenderAssessmentEntity value) {
    PostRenderAssessmentSnapshot snapshot = snapshot(value);
    return new AssessmentView(value.getGrade(), snapshot.decision(), snapshot.risk(), snapshot.recommendedAction(), value.getLabel(), value.getVerdict(),
        value.getEvidenceCoveragePercent(), value.getAssessmentVersion(), parse(value.getSnapshot()));
  }

  private PostRenderAssessmentSnapshot snapshot(PostRenderAssessmentEntity value) {
    Object parsed = parse(value.getSnapshot());
    if (parsed instanceof Map<?, ?> map) {
      return new PostRenderAssessmentSnapshot(stringValue(map, "decision", "REVIEW"),
          stringValue(map, "risk", "UNKNOWN"), stringValue(map, "recommendedAction", "HUMAN_REVIEW"));
    }
    return new PostRenderAssessmentSnapshot("REVIEW", "UNKNOWN", "HUMAN_REVIEW");
  }

  private String stringValue(Map<?, ?> map, String key, String fallback) {
    Object value = map.get(key);
    return value == null ? fallback : String.valueOf(value);
  }

  private Object parse(String value) {
    try { return value == null ? null : objectMapper.readValue(value, Object.class); }
    catch (Exception ignored) { return value; }
  }

  public record EvaluationView(UUID id, UUID assetId, UUID renderAttemptId, String evidenceVersion,
      String rulesetVersion, String analyzerVersions, String evidenceSnapshot, String decision,
      boolean humanReviewRequired, String humanDecision, Instant startedAt, Instant completedAt,
      AssessmentView assessment,
      List<RuleView> ruleResults) {}

  public record AssessmentView(String grade, String decision, String risk, String recommendedAction, String label, String verdict, int evidenceCoveragePercent,
      String assessmentVersion, Object snapshot) {}

  private record PostRenderAssessmentSnapshot(String decision, String risk, String recommendedAction) {}

  public record RuleView(String ruleId, String ruleVersion, String rulesetVersion, String stage,
      String family, String severity, String outcome, String message, Object actualValue,
      Object expectedCondition, Object evidenceReferences, String evaluator, boolean reviewRequired,
      Instant evaluatedAt) {}
}
