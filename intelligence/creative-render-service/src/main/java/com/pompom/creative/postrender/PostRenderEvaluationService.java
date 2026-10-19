package com.pompom.creative.postrender;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.qa.QaAnalysisResult;
import java.time.Instant;
import java.util.List;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Runs and persists one immutable post-render evidence/policy evaluation. */
@Service
@RequiredArgsConstructor
public class PostRenderEvaluationService {
  private final PostRenderEvidenceExtractor evidenceExtractor;
  private final PostRenderRuleEngine ruleEngine;
  private final PostRenderEvaluationRepository evaluationRepository;
  private final PostRenderRuleResultRepository ruleResultRepository;
  private final PostRenderAssessmentRepository assessmentRepository;
  private final PostRenderAssessmentAggregator assessmentAggregator;
  private final ObjectMapper objectMapper;
  private final StoryVideoQcClient storyVideoQcClient;

  @Transactional
  public EvaluationResult evaluate(
      RenderAsset asset, UUID renderAttemptId, QaAnalysisResult qa, String qaStatus) {
    Instant started = Instant.now();
    RenderEvidenceIR evidence = evidenceExtractor.extract(asset, renderAttemptId, qa, qaStatus);
    List<PostRenderRuleResult> results = new ArrayList<>(ruleEngine.evaluate(evidence));
    if (asset.getAssetType() == RenderAsset.AssetType.VIDEO) {
      Map<String, Object> qc = storyVideoQcClient.inspect(asset);
      Map<String, Object> enriched = new LinkedHashMap<>(evidence.evidence());
      enriched.put("videoQc", qc);
      evidence = new RenderEvidenceIR(evidence.assetId(), evidence.renderJobId(), evidence.renderAttemptId(),
          evidence.videoId(), evidence.variantId(), evidence.evidenceVersion(), evidence.capturedAt(),
          evidence.analyzerVersions(), Map.copyOf(enriched));
      String status = String.valueOf(qc.get("status"));
      results.replaceAll(PostRenderEvaluationService::audiencePolicy);
      results.add(new PostRenderRuleResult("CREATIVE_REVIEW_ADVICE", "3", ruleEngine.rulesetVersion(),
          "POST_RENDER", "CREATIVE_VIEWER_EXPERIENCE", PostRenderSeverity.INFO, PostRenderOutcome.NOT_APPLICABLE,
          qc.getOrDefault("creativeRecommendation", "NOT_EVALUATED") + ": creative review is decision support; owner chooses publication", qc,
          Map.of("role", "OWNER_DECISION_SUPPORT"), Map.of("source", "videoQc"), "audience-first-simple-v1", true, Instant.now()));
    }
    PostRenderDecision decision = new PostRenderDecisionAggregator().aggregate(results);
    PostRenderAssessment assessment = assessmentAggregator.aggregate(evidence, results);
    boolean reviewRequired =
        decision == PostRenderDecision.HUMAN_REVIEW
            || results.stream().anyMatch(PostRenderRuleResult::reviewRequired);

    PostRenderEvaluation evaluation =
        evaluationRepository.save(
            PostRenderEvaluation.builder()
                .renderAsset(asset)
                .renderAttemptId(renderAttemptId)
                .evidenceVersion(evidence.evidenceVersion())
                .postRenderRulesetVersion(ruleEngine.rulesetVersion())
                .analyzerVersions(write(evidence.analyzerVersions()))
                .evidenceSnapshot(write(evidence.evidence()))
                .overallDecision(decision)
                .humanReviewRequired(reviewRequired)
                .startedAt(started)
                .completedAt(Instant.now())
                .build());

    ruleResultRepository.saveAll(
        results.stream()
            .map(
                result ->
                    PostRenderRuleResultEntity.builder()
                        .evaluation(evaluation)
                        .ruleId(result.ruleId())
                        .ruleVersion(result.ruleVersion())
                        .rulesetVersion(result.rulesetVersion())
                        .stage(result.stage())
                        .family(result.family())
                        .severity(result.severity())
                        .outcome(result.outcome())
                        .message(result.message())
                        .actualValue(write(result.actualValue()))
                        .expectedCondition(write(result.expectedCondition()))
                        .evidenceReferences(write(result.evidenceReferences()))
                        .evaluator(result.evaluator())
                        .reviewRequired(result.reviewRequired())
                        .evaluatedAt(result.evaluatedAt())
                        .build())
            .toList());

    assessmentRepository.save(
        PostRenderAssessmentEntity.builder()
            .evaluation(evaluation)
            .grade(assessment.grade())
            .label(assessment.label())
            .verdict(assessment.verdict())
            .evidenceCoveragePercent(assessment.evidenceCoveragePercent())
            .assessmentVersion(assessment.assessmentVersion())
            .snapshot(write(assessment))
            .build());

    return new EvaluationResult(evaluation, evidence, results);
  }

  static PostRenderRuleResult audiencePolicy(PostRenderRuleResult r) {
    // Keep heuristic/plan findings visible, without imposing a loop or planned payoff.
    if (java.util.Set.of("TECHNICAL_INTEGRITY", "MEDIA_VALIDITY").contains(r.family())
        && !"TECH_QA_EVIDENCE_SERVICE".equals(r.ruleId())) return r;
    return new PostRenderRuleResult(r.ruleId(), r.ruleVersion(), r.rulesetVersion(), r.stage(), r.family(),
        PostRenderSeverity.INFO, PostRenderOutcome.NOT_APPLICABLE,
        "Diagnostic only (" + r.outcome() + "): " + r.message(), r.actualValue(), r.expectedCondition(),
        r.evidenceReferences(), r.evaluator(), false, r.evaluatedAt());
  }

  private String write(Object value) {
    try {
      return value == null ? null : objectMapper.writeValueAsString(value);
    } catch (JsonProcessingException error) {
      throw new IllegalStateException("Could not persist post-render evidence", error);
    }
  }

  public record EvaluationResult(
      PostRenderEvaluation evaluation,
      RenderEvidenceIR evidence,
      List<PostRenderRuleResult> results) {}
}
