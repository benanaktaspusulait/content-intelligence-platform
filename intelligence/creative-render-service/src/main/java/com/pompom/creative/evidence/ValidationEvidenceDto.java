package com.pompom.creative.evidence;

import java.time.Instant;
import java.util.UUID;

/**
 * Mirrors the intelligence backend's {@code ValidationEvidenceResponse} contract (see {@code
 * com.pompomhills.intelligence.quality.ValidationEvidenceResponse} in the intelligence backend
 * module). The render service never maps intelligence-owned tables as JPA relationships; this
 * record is the HTTP boundary snapshot {@link IntelligenceValidationEvidenceClient} returns.
 */
public record ValidationEvidenceDto(
    long validationRecordId,
    long contentId,
    long promptVersionId,
    String promptSha256,
    String status,
    int blockerCount,
    int criticalCount,
    int warningCount,
    String deterministicRulesetVersion,
    String semanticProvider,
    String semanticModelVersion,
    String producibilityValidatorVersion,
    UUID independentRevalidationId,
    Instant independentlyRevalidatedAt,
    Instant validatedAt,
    Instant expiresAt,
    boolean firstFrameEligible) {

  public ValidationEvidenceDto(
      long validationRecordId,
      long contentId,
      long promptVersionId,
      String promptSha256,
      String status,
      int blockerCount,
      int criticalCount,
      int warningCount,
      String deterministicRulesetVersion,
      String semanticProvider,
      String semanticModelVersion,
      String producibilityValidatorVersion,
      UUID independentRevalidationId,
      Instant independentlyRevalidatedAt,
      Instant validatedAt,
      Instant expiresAt) {
    this(
        validationRecordId,
        contentId,
        promptVersionId,
        promptSha256,
        status,
        blockerCount,
        criticalCount,
        warningCount,
        deterministicRulesetVersion,
        semanticProvider,
        semanticModelVersion,
        producibilityValidatorVersion,
        independentRevalidationId,
        independentlyRevalidatedAt,
        validatedAt,
        expiresAt,
        false);
  }
}
