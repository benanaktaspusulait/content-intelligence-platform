package com.pompomhills.intelligence.quality;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
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
  private final String mlServiceUrl;
  private final HttpClient httpClient;

  public QualityMlClient(
      @Value("${ml.service.url:http://localhost:8001}") String mlServiceUrl,
      RestClient.Builder restClientBuilder) {
    this.mlServiceUrl = mlServiceUrl;
    this.httpClient = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
    this.mlObjectMapper =
        new ObjectMapper().setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
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
            rulesetVersion != null ? rulesetVersion : "latest",
            "evaluation_stage",
            "PRE_RENDER");

    try {
      String requestBody = mlObjectMapper.writeValueAsString(request);
      HttpRequest httpRequest =
          HttpRequest.newBuilder(
                  URI.create(mlServiceUrl + "/api/v1/quality/validate"))
              .header("Content-Type", "application/json")
              .POST(HttpRequest.BodyPublishers.ofString(requestBody, StandardCharsets.UTF_8))
              .build();
      HttpResponse<String> response =
          httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
      String body = response.body();
      if (response.statusCode() >= 400 && response.statusCode() < 500) {
        throw new QualityValidationException(
            "Validation failed: HTTP " + response.statusCode() + " " + body,
            "VALIDATION_ERROR");
      }
      if (response.statusCode() >= 500) {
        throw new MlServiceException("ML service error: HTTP " + response.statusCode());
      }
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
