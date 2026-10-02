package com.pompomhills.intelligence.quality;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST API for Pompom Creative Quality Engine
 *
 * <p>Validates video prompts before render using ML-based quality analysis.
 *
 * <p><b>Not render-authorizing.</b> {@code POST /validate} here never links to a content/prompt
 * version and never populates the evidence fields {@link ValidationEvidenceService} requires, so
 * every record it creates is permanently {@code VALIDATION_EVIDENCE_INCOMPLETE} and can never
 * authorize a render job. Use it only for ad hoc / exploratory prompt scoring. Callers that need
 * render-authorizing evidence must use {@link IntelligenceQualityValidationController}'s {@code
 * POST /api/v1/intelligence/quality/validate} instead, which links the validation to a real
 * content/prompt version and persists the evidence fields the render queue gate consults.
 */
@RestController
@RequestMapping("/api/quality")
@Tag(name = "Quality Validation", description = "Video prompt quality validation and scoring")
public class QualityValidationController {

  private final QualityValidationService service;

  public QualityValidationController(QualityValidationService service) {
    this.service = service;
  }

  @PostMapping("/validate")
  @Operation(
      summary = "Validate video prompt (not render-authorizing)",
      description =
          "Analyzes prompt and returns quality score, status (RENDER_READY/NEEDS_REVISION/BLOCKED), and fix suggestions. "
              + "Does not link to a content/prompt version, so the resulting record can never authorize a render job. "
              + "Use POST /api/v1/intelligence/quality/validate for render-authorizing evidence.")
  public ResponseEntity<QualityReportDto> validatePrompt(
      @Valid @RequestBody ValidatePromptRequest request) {
    QualityReportDto report = service.validatePrompt(request.prompt(), request.rulesetVersion());
    return ResponseEntity.ok(report);
  }

  @PostMapping("/validate-batch")
  @Operation(
      summary = "Validate multiple prompts",
      description = "Batch validation for multiple prompts")
  public ResponseEntity<List<QualityReportDto>> validateBatch(
      @Valid @RequestBody ValidateBatchRequest request) {
    List<QualityReportDto> reports =
        service.validateBatch(request.prompts(), request.rulesetVersion());
    return ResponseEntity.ok(reports);
  }

  @PostMapping("/compare-versions")
  @Operation(
      summary = "Compare two prompt versions",
      description = "Detects regressions when applying fixes to a prompt")
  public ResponseEntity<RegressionReportDto> compareVersions(
      @Valid @RequestBody CompareVersionsRequest request) {
    RegressionReportDto report =
        service.compareVersions(
            request.promptBefore(),
            request.promptAfter(),
            request.versionBefore(),
            request.versionAfter());
    return ResponseEntity.ok(report);
  }

  @GetMapping("/rulesets")
  @Operation(
      summary = "List available rulesets",
      description = "Get all ruleset versions with metadata")
  public ResponseEntity<List<RulesetVersionDto>> listRulesets() {
    List<RulesetVersionDto> versions = service.listRulesets();
    return ResponseEntity.ok(versions);
  }

  @GetMapping("/rulesets/{version}")
  @Operation(
      summary = "Get ruleset info",
      description = "Get detailed information about a specific ruleset version")
  public ResponseEntity<RulesetVersionDto> getRuleset(@PathVariable String version) {
    RulesetVersionDto ruleset = service.getRuleset(version);
    return ResponseEntity.ok(ruleset);
  }

  @GetMapping("/rulesets/compare/{fromVersion}/{toVersion}")
  @Operation(
      summary = "Compare two rulesets",
      description = "Get migration guide and breaking changes between ruleset versions")
  public ResponseEntity<RulesetComparisonDto> compareRulesets(
      @PathVariable String fromVersion, @PathVariable String toVersion) {
    RulesetComparisonDto comparison = service.compareRulesets(fromVersion, toVersion);
    return ResponseEntity.ok(comparison);
  }

  @GetMapping("/health")
  @Operation(summary = "Health check", description = "Check ML service connectivity")
  public ResponseEntity<HealthDto> health() {
    HealthDto health = service.checkHealth();
    return ResponseEntity.ok(health);
  }

  @ExceptionHandler(QualityValidationException.class)
  public ResponseEntity<ErrorDto> handleValidationException(QualityValidationException ex) {
    ErrorDto error = new ErrorDto(ex.getMessage(), ex.getErrorCode());
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
  }

  @ExceptionHandler(MlServiceException.class)
  public ResponseEntity<ErrorDto> handleMlServiceException(MlServiceException ex) {
    ErrorDto error = new ErrorDto("ML service error: " + ex.getMessage(), "ML_SERVICE_ERROR");
    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(error);
  }
}
