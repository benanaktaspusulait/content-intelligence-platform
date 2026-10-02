package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Service layer for quality validation operations.
 *
 * <p>Orchestrates calls to Python ML service and manages validation history.
 */
@Service
@Transactional
public class QualityValidationService {

  private static final Logger log = LoggerFactory.getLogger(QualityValidationService.class);

  private final QualityMlClient mlClient;
  private final QualityValidationRepository repository;

  public QualityValidationService(
      QualityMlClient mlClient, QualityValidationRepository repository) {
    this.mlClient = mlClient;
    this.repository = repository;
  }

  /**
   * Validate a single prompt and store result.
   *
   * @param prompt Video prompt text
   * @param rulesetVersion Ruleset version (null = latest)
   * @return Quality report with score, status, and fixes
   */
  public QualityReportDto validatePrompt(String prompt, String rulesetVersion) {
    log.info("Validating prompt with ruleset version: {}", rulesetVersion);

    try {
      // Call ML service
      QualityReportDto report = mlClient.validatePrompt(prompt, rulesetVersion);

      // Persist validation
      QualityValidationEntity entity = new QualityValidationEntity();
      entity.setPromptText(prompt);
      entity.setRulesetVersion(report.rulesetVersion());
      entity.setOverallScore(report.overallScore());
      entity.setStatus(report.status());
      entity.setBlockerCount(report.blockerCount());
      entity.setCriticalCount(report.criticalCount());
      entity.setWarningCount(report.warningCount());
      entity.setFailedRules(
          report.failedRules().stream()
              .map(RuleEvaluationDto::ruleId)
              .collect(Collectors.joining(",")));

      repository.save(entity);

      log.info(
          "Validation complete: score={}, status={}, id={}",
          report.overallScore(),
          report.status(),
          entity.getId());

      return report;

    } catch (Exception ex) {
      log.error("Validation failed", ex);
      throw new MlServiceException("Failed to validate prompt: " + ex.getMessage(), ex);
    }
  }

  /**
   * Validate multiple prompts in batch.
   *
   * @param prompts List of prompt texts
   * @param rulesetVersion Ruleset version (null = latest)
   * @return List of quality reports
   */
  public List<QualityReportDto> validateBatch(List<String> prompts, String rulesetVersion) {
    log.info("Batch validating {} prompts", prompts.size());

    return prompts.stream()
        .map(prompt -> validatePrompt(prompt, rulesetVersion))
        .collect(Collectors.toList());
  }

  /**
   * Compare two prompt versions for regression detection.
   *
   * @param promptBefore Original prompt
   * @param promptAfter Revised prompt
   * @param versionBefore Version label for before
   * @param versionAfter Version label for after
   * @return Regression report
   */
  public RegressionReportDto compareVersions(
      String promptBefore, String promptAfter, String versionBefore, String versionAfter) {
    log.info("Comparing versions: {} -> {}", versionBefore, versionAfter);

    try {
      return mlClient.compareVersions(promptBefore, promptAfter, versionBefore, versionAfter);
    } catch (Exception ex) {
      log.error("Version comparison failed", ex);
      throw new MlServiceException("Failed to compare versions: " + ex.getMessage(), ex);
    }
  }

  /**
   * List all available ruleset versions.
   *
   * @return List of ruleset versions with metadata
   */
  public List<RulesetVersionDto> listRulesets() {
    log.debug("Fetching available rulesets");

    try {
      return mlClient.listRulesets();
    } catch (Exception ex) {
      log.error("Failed to list rulesets", ex);
      throw new MlServiceException("Failed to list rulesets: " + ex.getMessage(), ex);
    }
  }

  /**
   * Get detailed information about a specific ruleset.
   *
   * @param version Ruleset version
   * @return Ruleset metadata
   */
  public RulesetVersionDto getRuleset(String version) {
    log.debug("Fetching ruleset: {}", version);

    try {
      return mlClient.getRuleset(version);
    } catch (Exception ex) {
      log.error("Failed to get ruleset {}", version, ex);
      throw new QualityValidationException("Ruleset not found: " + version, "RULESET_NOT_FOUND");
    }
  }

  /**
   * Compare two ruleset versions.
   *
   * @param fromVersion Starting version
   * @param toVersion Target version
   * @return Comparison with breaking changes and migration notes
   */
  public RulesetComparisonDto compareRulesets(String fromVersion, String toVersion) {
    log.debug("Comparing rulesets: {} -> {}", fromVersion, toVersion);

    try {
      return mlClient.compareRulesets(fromVersion, toVersion);
    } catch (Exception ex) {
      log.error("Failed to compare rulesets", ex);
      throw new MlServiceException("Failed to compare rulesets: " + ex.getMessage(), ex);
    }
  }

  /**
   * Check ML service health.
   *
   * @return Health status
   */
  public HealthDto checkHealth() {
    try {
      return mlClient.checkHealth();
    } catch (Exception ex) {
      log.warn("ML service health check failed", ex);
      return new HealthDto("DOWN", "ML service unavailable: " + ex.getMessage());
    }
  }

  /**
   * Get validation history for a prompt.
   *
   * @param promptId Prompt ID (from video table)
   * @return List of historical validations
   */
  public List<QualityValidationEntity> getValidationHistory(Long promptId) {
    return repository.findByPromptIdOrderByCreatedAtDesc(promptId);
  }

  /**
   * Get validation statistics.
   *
   * @return Aggregated stats
   */
  public ValidationStatsDto getStats() {
    long totalValidations = repository.count();
    long renderReady = repository.countByStatus("RENDER_READY");
    long blocked = repository.countByStatus("BLOCKED");
    long needsRevision = repository.countByStatus("NEEDS_REVISION");
    Double avgScore = repository.averageScore();

    return new ValidationStatsDto(
        totalValidations, renderReady, blocked, needsRevision, avgScore != null ? avgScore : 0.0);
  }
}
