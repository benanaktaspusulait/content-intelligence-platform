package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.Map;

/**
 * Quality validation report from ML service.
 *
 * @param overallScore 0-100 quality score
 * @param status RENDER_READY, NEEDS_REVISION, BLOCKED, or SERVICE_ERROR
 * @param rulesetVersion Ruleset version used
 * @param blockerCount Number of blocker-level failures
 * @param criticalCount Number of critical-level failures
 * @param warningCount Number of warning-level issues
 * @param familyScores Per-family scores (Concept Strength, Hook Strength, etc.)
 * @param failedRules Rule evaluations with outcome FAIL
 * @param unknownRules Rule evaluations with outcome UNKNOWN (applies but evidence missing)
 * @param notApplicableRules Rule evaluations with outcome NOT_APPLICABLE (does not apply to this
 *     concept)
 * @param serviceErrors Rule evaluations with outcome SERVICE_ERROR (provider/runtime failure, not a
 *     rule failure)
 * @param priorityFixes Top fixes sorted by severity
 * @param scoreCard UI-ready score card (label, color)
 * @param timelineData Beat-level timeline data for visualization
 * @param parserConfidence Parser's self-reported confidence (0.0-1.0) in the extracted Video Plan
 *     IR
 * @param parserWarnings Parser warnings about ambiguous or unparseable input
 * @param parserAssumptions Parser assumptions made when explicit evidence was absent
 * @param topStrengths Top-scoring quality families, human-readable
 * @param topWeaknesses Lowest-scoring quality families needing attention, human-readable
 * @param evidenceMissing Named IR sections the parser could not populate at all (e.g. "beats")
 */
public record QualityReportDto(
    double overallScore,
    String status,
    String rulesetVersion,
    int blockerCount,
    int criticalCount,
    int warningCount,
    Map<String, Double> familyScores,
    List<RuleEvaluationDto> failedRules,
    List<RuleEvaluationDto> unknownRules,
    List<RuleEvaluationDto> notApplicableRules,
    List<RuleEvaluationDto> serviceErrors,
    List<PriorityFixDto> priorityFixes,
    ScoreCardDto scoreCard,
    TimelineDataDto timelineData,
    double parserConfidence,
    List<String> parserWarnings,
    List<String> parserAssumptions,
    List<String> topStrengths,
    List<String> topWeaknesses,
    List<String> evidenceMissing,
    List<ScoreBreakdownDto> scoreBreakdowns,
    Map<String, Object> familyRadar,
    QualityProvenanceDto provenance,
    Map<String, Object> preRenderAssessment,
    Map<String, Object> videoPlanIr,
    Map<String, Object> familyAssessments) {

  /**
   * Backward-compatible constructor for callers that only know the original report shape.
   * Older service/tests do not provide prompt-intelligence fields yet.
   */
  public QualityReportDto(
      double overallScore,
      String status,
      String rulesetVersion,
      int blockerCount,
      int criticalCount,
      int warningCount,
      Map<String, Double> familyScores,
      List<RuleEvaluationDto> failedRules,
      List<RuleEvaluationDto> unknownRules,
      List<RuleEvaluationDto> notApplicableRules,
      List<RuleEvaluationDto> serviceErrors,
      List<PriorityFixDto> priorityFixes,
      ScoreCardDto scoreCard,
      TimelineDataDto timelineData,
      double parserConfidence,
      List<String> parserWarnings,
      List<String> parserAssumptions,
      List<String> topStrengths,
      List<String> topWeaknesses,
      List<String> evidenceMissing,
      List<ScoreBreakdownDto> scoreBreakdowns,
      Map<String, Object> familyRadar,
      QualityProvenanceDto provenance) {
    this(
        overallScore,
        status,
        rulesetVersion,
        blockerCount,
        criticalCount,
        warningCount,
        familyScores,
        failedRules,
        unknownRules,
        notApplicableRules,
        serviceErrors,
        priorityFixes,
        scoreCard,
        timelineData,
        parserConfidence,
        parserWarnings,
        parserAssumptions,
        topStrengths,
        topWeaknesses,
        evidenceMissing,
        scoreBreakdowns,
        familyRadar,
        provenance,
        Map.of(),
        Map.of(),
        Map.of());
  }
}
