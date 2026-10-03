package com.pompomhills.intelligence.quality;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

/** Validation history record stored in PostgreSQL. */
@Entity
@Table(name = "quality_validations")
public class QualityValidationEntity {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "prompt_id")
  private Long promptId; // FK to video prompts table (optional)

  @Column(name = "prompt_text", columnDefinition = "TEXT", nullable = false)
  private String promptText;

  @Column(name = "ruleset_version", length = 10, nullable = false)
  private String rulesetVersion;

  @Column(name = "overall_score", nullable = false)
  private Double overallScore;

  @Column(name = "status", length = 20, nullable = false)
  private String status;

  @Column(name = "blocker_count", nullable = false)
  private Integer blockerCount = 0;

  @Column(name = "critical_count", nullable = false)
  private Integer criticalCount = 0;

  @Column(name = "warning_count", nullable = false)
  private Integer warningCount = 0;

  @Column(name = "failed_rules", columnDefinition = "TEXT")
  private String failedRules; // Comma-separated rule IDs

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  // --- Immutable validation evidence (Slice B Task 1) ---
  // All nullable: legacy rows predate this migration, and semantic/producibility/independent
  // revalidation identity cannot be populated until the ML service's quality pipeline (Slice C)
  // exists. ValidationEvidenceService treats any gap here as evidence that can never resolve to
  // RENDER_READY, so render authorization is never fabricated from an incomplete record.

  @Column(name = "content_id")
  private Long contentId;

  @Column(name = "prompt_version_id")
  private Long promptVersionId;

  @Column(name = "prompt_sha256", length = 64)
  private String promptSha256;

  @Column(name = "deterministic_ruleset_version", length = 20)
  private String deterministicRulesetVersion;

  @Column(name = "semantic_provider", length = 50)
  private String semanticProvider;

  @Column(name = "semantic_model_version", length = 100)
  private String semanticModelVersion;

  @Column(name = "producibility_validator_version", length = 20)
  private String producibilityValidatorVersion;

  @Column(name = "independent_revalidation_id")
  private UUID independentRevalidationId;

  @Column(name = "validation_run_id")
  private UUID validationRunId;

  @Column(name = "independently_revalidated_at")
  private Instant independentlyRevalidatedAt;

  @Column(name = "validated_at")
  private Instant validatedAt;

  @Column(name = "expires_at")
  private Instant expiresAt;

  @PrePersist
  protected void onCreate() {
    createdAt = Instant.now();
  }

  // Getters and setters

  public Long getId() {
    return id;
  }

  public void setId(Long id) {
    this.id = id;
  }

  public Long getPromptId() {
    return promptId;
  }

  public void setPromptId(Long promptId) {
    this.promptId = promptId;
  }

  public String getPromptText() {
    return promptText;
  }

  public void setPromptText(String promptText) {
    this.promptText = promptText;
  }

  public String getRulesetVersion() {
    return rulesetVersion;
  }

  public void setRulesetVersion(String rulesetVersion) {
    this.rulesetVersion = rulesetVersion;
  }

  public Double getOverallScore() {
    return overallScore;
  }

  public void setOverallScore(Double overallScore) {
    this.overallScore = overallScore;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public Integer getBlockerCount() {
    return blockerCount;
  }

  public void setBlockerCount(Integer blockerCount) {
    this.blockerCount = blockerCount;
  }

  public Integer getCriticalCount() {
    return criticalCount;
  }

  public void setCriticalCount(Integer criticalCount) {
    this.criticalCount = criticalCount;
  }

  public Integer getWarningCount() {
    return warningCount;
  }

  public void setWarningCount(Integer warningCount) {
    this.warningCount = warningCount;
  }

  public String getFailedRules() {
    return failedRules;
  }

  public void setFailedRules(String failedRules) {
    this.failedRules = failedRules;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public void setCreatedAt(Instant createdAt) {
    this.createdAt = createdAt;
  }

  public Long getContentId() {
    return contentId;
  }

  public void setContentId(Long contentId) {
    this.contentId = contentId;
  }

  public Long getPromptVersionId() {
    return promptVersionId;
  }

  public void setPromptVersionId(Long promptVersionId) {
    this.promptVersionId = promptVersionId;
  }

  public String getPromptSha256() {
    return promptSha256;
  }

  public void setPromptSha256(String promptSha256) {
    this.promptSha256 = promptSha256;
  }

  public String getDeterministicRulesetVersion() {
    return deterministicRulesetVersion;
  }

  public void setDeterministicRulesetVersion(String deterministicRulesetVersion) {
    this.deterministicRulesetVersion = deterministicRulesetVersion;
  }

  public String getSemanticProvider() {
    return semanticProvider;
  }

  public void setSemanticProvider(String semanticProvider) {
    this.semanticProvider = semanticProvider;
  }

  public String getSemanticModelVersion() {
    return semanticModelVersion;
  }

  public void setSemanticModelVersion(String semanticModelVersion) {
    this.semanticModelVersion = semanticModelVersion;
  }

  public String getProducibilityValidatorVersion() {
    return producibilityValidatorVersion;
  }

  public void setProducibilityValidatorVersion(String producibilityValidatorVersion) {
    this.producibilityValidatorVersion = producibilityValidatorVersion;
  }

  public UUID getIndependentRevalidationId() {
    return independentRevalidationId;
  }

  public UUID getValidationRunId() {
    return validationRunId;
  }

  public void setValidationRunId(UUID validationRunId) {
    this.validationRunId = validationRunId;
  }

  public void setIndependentRevalidationId(UUID independentRevalidationId) {
    this.independentRevalidationId = independentRevalidationId;
  }

  public Instant getIndependentlyRevalidatedAt() {
    return independentlyRevalidatedAt;
  }

  public void setIndependentlyRevalidatedAt(Instant independentlyRevalidatedAt) {
    this.independentlyRevalidatedAt = independentlyRevalidatedAt;
  }

  public Instant getValidatedAt() {
    return validatedAt;
  }

  public void setValidatedAt(Instant validatedAt) {
    this.validatedAt = validatedAt;
  }

  public Instant getExpiresAt() {
    return expiresAt;
  }

  public void setExpiresAt(Instant expiresAt) {
    this.expiresAt = expiresAt;
  }
}
