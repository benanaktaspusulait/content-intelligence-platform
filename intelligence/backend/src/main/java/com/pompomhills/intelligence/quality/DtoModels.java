package com.pompomhills.intelligence.quality;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;

// ===== Request DTOs =====

record ValidateBatchRequest(@NotEmpty List<String> prompts, String rulesetVersion) {}

record CompareVersionsRequest(
    @NotNull String promptBefore,
    @NotNull String promptAfter,
    String versionBefore,
    String versionAfter) {}

// ===== Response DTOs =====

record RuleEvaluationDto(
    String ruleId,
    String ruleName,
    String family,
    String severity,
    String outcome,
    String message,
    Double actualValue,
    Double thresholdValue) {}

record PriorityFixDto(
    String ruleId,
    String ruleName,
    String family,
    String severity,
    String issue,
    String recommendation,
    String impact) {}

record ScoreCardDto(double score, String label, String color) {}

record TimelineDataDto(
    List<BeatDto> beats,
    List<ConsequenceMarkerDto> consequenceMarkers,
    List<StateSegmentDto> stateSegments) {}

record BeatDto(
    double startTime,
    double endTime,
    String action,
    String consequence,
    int intensity,
    boolean isNewConsequence) {}

record ConsequenceMarkerDto(double time, String consequence, String type) {}

record StateSegmentDto(String stateId, double startTime, double endTime, double percentage) {}

record RegressionReportDto(
    String versionBefore,
    String versionAfter,
    boolean hasRegressions,
    double scoreBefore,
    double scoreAfter,
    double scoreDelta,
    String statusBefore,
    String statusAfter,
    boolean statusImproved,
    List<RegressionIssueDto> criticalRegressions,
    List<RegressionIssueDto> warningRegressions,
    List<String> fixedRules,
    List<String> improvedFamilies,
    List<String> degradedFamilies,
    boolean netImprovement,
    String recommendation,
    String summary) {}

record RegressionIssueDto(
    String ruleId,
    String ruleName,
    String family,
    String severity,
    String beforeStatus,
    String afterStatus,
    Double beforeValue,
    Double afterValue,
    double scoreDelta,
    String message,
    String recommendation) {}

record RulesetVersionDto(
    String version,
    String releaseDate,
    String description,
    String rulesetPath,
    List<String> learnedFrom,
    List<String> deprecatedRules,
    boolean isBreaking,
    String changelog,
    List<RuleChangeDto> changes) {}

record RuleChangeDto(
    String ruleId,
    String changeType,
    Map<String, Object> oldValue,
    Map<String, Object> newValue,
    String reason,
    boolean breakingChange) {}

record RulesetComparisonDto(
    String versionFrom,
    String versionTo,
    boolean isBackwardCompatible,
    List<RuleChangeDto> breakingChanges,
    List<String> newRules,
    List<String> removedRules,
    List<String> modifiedRules,
    String migrationNotes) {}

record HealthDto(String status, String message) {}

record ErrorDto(String message, String errorCode) {}

record ValidationStatsDto(
    long totalValidations,
    long renderReady,
    long blocked,
    long needsRevision,
    double averageScore) {}
