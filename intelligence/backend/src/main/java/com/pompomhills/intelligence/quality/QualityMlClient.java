package com.pompomhills.intelligence.quality;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
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
  private final ObjectMapper mlObjectMapper;

  public QualityMlClient(
      @Value("${ml.service.url:http://localhost:8001}") String mlServiceUrl,
      RestClient.Builder restClientBuilder) {
    this.restClient =
        restClientBuilder
            .baseUrl(mlServiceUrl)
            .defaultHeader("Content-Type", "application/json")
            .build();
    this.mlObjectMapper =
        new ObjectMapper().setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

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
            rulesetVersion != null ? rulesetVersion : "latest",
            "evaluation_stage",
            "PRE_RENDER");

    try {
      String body =
          restClient
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
          .body(String.class);
      return readBody(body, QualityReportDto.class);

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

    String body =
        restClient
        .post()
        .uri("/api/v1/quality/compare-versions")
        .body(request)
        .retrieve()
        .body(String.class);
    return readBody(body, RegressionReportDto.class);
  }

  /**
   * List all ruleset versions.
   *
   * @return List of versions
   */
  public List<RulesetVersionDto> listRulesets() {
    log.debug("Calling ML service: /rulesets");

    String body =
        restClient
        .get()
        .uri("/api/v1/quality/rulesets")
        .retrieve()
        .body(String.class);
    return readBody(body, new TypeReference<List<RulesetVersionDto>>() {});
  }

  /**
   * Get specific ruleset.
   *
   * @param version Version string
   * @return Ruleset metadata
   */
  public RulesetVersionDto getRuleset(String version) {
    log.debug("Calling ML service: /rulesets/{}", version);

    String body =
        restClient
        .get()
        .uri("/api/v1/quality/rulesets/{version}", version)
        .retrieve()
        .onStatus(
            HttpStatusCode::is4xxClientError,
            (req, res) -> {
              throw new QualityValidationException(
                  "Ruleset not found: " + version, "RULESET_NOT_FOUND");
            })
        .body(String.class);
    return readBody(body, RulesetVersionDto.class);
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

    String body =
        restClient
        .get()
        .uri("/api/v1/quality/rulesets/compare/{from}/{to}", fromVersion, toVersion)
        .retrieve()
        .body(String.class);
    return readBody(body, RulesetComparisonDto.class);
  }

  /**
   * Health check.
   *
   * @return Health status
   */
  public HealthDto checkHealth() {
    log.debug("Calling ML service: /health");

    try {
      String body =
          restClient.get().uri("/api/v1/quality/health").retrieve().body(String.class);
      return readBody(body, HealthDto.class);
    } catch (Exception ex) {
      return new HealthDto("DOWN", ex.getMessage());
    }
  }

  private <T> T readBody(String body, Class<T> type) {
    if (body == null || body.isBlank()) {
      throw new MlServiceException("ML service returned an empty response");
    }
    try {
      return mlObjectMapper.readValue(body, type);
    } catch (JsonProcessingException error) {
      throw new MlServiceException("ML service returned an incompatible response", error);
    }
  }

  private <T> T readBody(String body, TypeReference<T> type) {
    if (body == null || body.isBlank()) {
      throw new MlServiceException("ML service returned an empty response");
    }
    try {
      return mlObjectMapper.readValue(body, type);
    } catch (JsonProcessingException error) {
      throw new MlServiceException("ML service returned an incompatible response", error);
    }
  }
}
