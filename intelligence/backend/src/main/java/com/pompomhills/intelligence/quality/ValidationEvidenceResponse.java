package com.pompomhills.intelligence.quality;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Immutable validation evidence snapshot for a single validation record.
 *
 * <p>Returned by the internal evidence endpoint that {@code creative-render-service} consults
 * before queueing a render job. {@code status} is recomputed from the stored fields on every read
 * (see {@link ValidationEvidenceService}) rather than trusted verbatim from the database, so
 * evidence can never report {@link ValidationDecisionStatus#RENDER_READY} while any required field
 * is absent.
 */
public record ValidationEvidenceResponse(
    long validationRecordId,
    long contentId,
    long promptVersionId,
    String promptSha256,
    ValidationDecisionStatus status,
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
    boolean firstFrameEligible,
    boolean finalVideoEligible,
    Map<String, Object> visualEvidence,
    String renderAuthorization) {

  /** Compatibility constructor for callers that predate the Family 8 authorization field. */
  public ValidationEvidenceResponse(
      long validationRecordId,
      long contentId,
      long promptVersionId,
      String promptSha256,
      ValidationDecisionStatus status,
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
      boolean firstFrameEligible,
      boolean finalVideoEligible,
      Map<String, Object> visualEvidence) {
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
        firstFrameEligible,
        finalVideoEligible,
        visualEvidence,
        null);
  }

  public ValidationEvidenceResponse(
      long validationRecordId,
      long contentId,
      long promptVersionId,
      String promptSha256,
      ValidationDecisionStatus status,
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
        false,
        false,
        Map.of(),
        null);
  }
}
