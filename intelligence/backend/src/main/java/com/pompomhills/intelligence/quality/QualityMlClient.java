package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * HTTP client for Python ML service.
 *
 * <p>Communicates with FastAPI/Flask ML service running quality engine.
 */
@Component
public class QualityMlClient {

  private static final Logger log = LoggerFactory.getLogger(QualityMlClient.class);

  private final RestClient restClient;

  public QualityMlClient(
      @Value("${ml.service.url:http://localhost:8001}") String mlServiceUrl,
      RestClient.Builder restClientBuilder) {
    this.restClient =
        restClientBuilder
            .baseUrl(mlServiceUrl)
            .defaultHeader("Content-Type", "application/json")
            .build();

    log.info("ML client initialized with base URL: {}", mlServiceUrl);
  }

  /**
   * Validate a prompt.
   *
   * @param prompt Prompt text
   * @param rulesetVersion Version (null = latest)
   * @return Quality report
   */
  public QualityReportDto validatePrompt(String prompt, String rulesetVersion) {
    log.debug("Calling ML service: /validate");

    var request =
        Map.of(
            "prompt",
            prompt,
            "ruleset_version",
            rulesetVersion != null ? rulesetVersion : "latest");

    try {
      return restClient
          .post()
          .uri("/api/v1/quality/validate")
          .body(request)
          .retrieve()
          .onStatus(
              HttpStatusCode::is4xxClientError,
              (req, res) -> {
                throw new QualityValidationException(
                    "Validation failed: " + res.getStatusText(), "VALIDATION_ERROR");
              })
          .onStatus(
              HttpStatusCode::is5xxServerError,
              (req, res) -> {
                throw new MlServiceException("ML service error: " + res.getStatusText());
              })
          .body(QualityReportDto.class);

    } catch (Exception ex) {
      log.error("ML service call failed", ex);
      throw new MlServiceException("Failed to call ML service: " + ex.getMessage(), ex);
    }
  }

  /**
   * Compare two prompt versions.
   *
   * @param promptBefore Original
   * @param promptAfter Revised
   * @param versionBefore Label
   * @param versionAfter Label
   * @return Regression report
   */
  public RegressionReportDto compareVersions(
      String promptBefore, String promptAfter, String versionBefore, String versionAfter) {
    log.debug("Calling ML service: /compare-versions");

    var request =
        Map.of(
            "prompt_before",
            promptBefore,
            "prompt_after",
            promptAfter,
            "version_before",
            versionBefore != null ? versionBefore : "before",
            "version_after",
            versionAfter != null ? versionAfter : "after");

    return restClient
        .post()
        .uri("/api/v1/quality/compare-versions")
        .body(request)
        .retrieve()
        .body(RegressionReportDto.class);
  }

  /**
   * List all ruleset versions.
   *
   * @return List of versions
   */
  public List<RulesetVersionDto> listRulesets() {
    log.debug("Calling ML service: /rulesets");

    return restClient
        .get()
        .uri("/api/v1/quality/rulesets")
        .retrieve()
        .body(
            new org.springframework.core.ParameterizedTypeReference<List<RulesetVersionDto>>() {});
  }

  /**
   * Get specific ruleset.
   *
   * @param version Version string
   * @return Ruleset metadata
   */
  public RulesetVersionDto getRuleset(String version) {
    log.debug("Calling ML service: /rulesets/{}", version);

    return restClient
        .get()
        .uri("/api/v1/quality/rulesets/{version}", version)
        .retrieve()
        .onStatus(
            HttpStatusCode::is4xxClientError,
            (req, res) -> {
              throw new QualityValidationException(
                  "Ruleset not found: " + version, "RULESET_NOT_FOUND");
            })
        .body(RulesetVersionDto.class);
  }

  /**
   * Compare two rulesets.
   *
   * @param fromVersion Starting version
   * @param toVersion Target version
   * @return Comparison
   */
  public RulesetComparisonDto compareRulesets(String fromVersion, String toVersion) {
    log.debug("Calling ML service: /rulesets/compare");

    return restClient
        .get()
        .uri("/api/v1/quality/rulesets/compare/{from}/{to}", fromVersion, toVersion)
        .retrieve()
        .body(RulesetComparisonDto.class);
  }

  /**
   * Health check.
   *
   * @return Health status
   */
  public HealthDto checkHealth() {
    log.debug("Calling ML service: /health");

    try {
      return restClient.get().uri("/api/v1/quality/health").retrieve().body(HealthDto.class);
    } catch (Exception ex) {
      return new HealthDto("DOWN", ex.getMessage());
    }
  }
}
