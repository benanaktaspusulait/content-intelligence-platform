package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.Map;

/**
 * Quality validation report from ML service.
 *
 * @param overallScore 0-100 quality score
 * @param status RENDER_READY, NEEDS_REVISION, or BLOCKED
 * @param rulesetVersion Ruleset version used
 * @param blockerCount Number of blocker-level failures
 * @param criticalCount Number of critical-level failures
 * @param warningCount Number of warning-level issues
 * @param familyScores Per-family scores (Concept Strength, Hook Strength, etc.)
 * @param failedRules List of failed rule evaluations
 * @param priorityFixes Top fixes sorted by severity
 * @param scoreCard UI-ready score card (label, color)
 * @param timelineData Beat-level timeline data for visualization
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
    List<PriorityFixDto> priorityFixes,
    ScoreCardDto scoreCard,
    TimelineDataDto timelineData) {}
