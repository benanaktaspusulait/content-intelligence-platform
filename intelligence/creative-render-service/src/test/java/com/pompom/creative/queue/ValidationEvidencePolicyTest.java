package com.pompom.creative.queue;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Every predicate here corresponds to a hard precondition from the design doc (Slice B item 5,
 * "Enforce immutable validation evidence"): status RENDER_READY, zero blocker/critical counts,
 * independent revalidation present, content/prompt identity and prompt hash matching the request,
 * every required version identity present, and evidence not expired. {@link
 * ValidationEvidencePolicy#validate} must throw {@link ValidationEvidenceRejectedException} for
 * every violation and return normally only when every predicate passes.
 */
class ValidationEvidencePolicyTest {

  private final ValidationEvidencePolicy policy = new ValidationEvidencePolicy();
  private final Instant now = Instant.parse("2026-01-01T12:00:00Z");

  @Test
  void acceptsCompleteRenderReadyEvidenceMatchingTheRequest() {
    QueueRenderJobRequest request = request();
    ValidationEvidenceDto evidence = renderReadyEvidence();

    assertThatCode(() -> policy.validate(request, evidence, now)).doesNotThrowAnyException();
  }

  @Test
  void rejectsNonReadyStatus() {
    QueueRenderJobRequest request = request();
    ValidationEvidenceDto evidence = withStatus(renderReadyEvidence(), "NEEDS_REVISION");

    assertThatThrownBy(() -> policy.validate(request, evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_NOT_RENDER_READY");
  }

  @Test
  void rejectsNonzeroBlockerCount() {
    ValidationEvidenceDto evidence = withBlockerCount(renderReadyEvidence(), 1);

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_HAS_BLOCKERS");
  }

  @Test
  void rejectsNonzeroCriticalCount() {
    ValidationEvidenceDto evidence = withCriticalCount(renderReadyEvidence(), 1);

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_HAS_CRITICALS");
  }

  @Test
  void rejectsAbsentIndependentRevalidationId() {
    ValidationEvidenceDto base = renderReadyEvidence();
    ValidationEvidenceDto evidence =
        new ValidationEvidenceDto(
            base.validationRecordId(),
            base.contentId(),
            base.promptVersionId(),
            base.promptSha256(),
            base.status(),
            base.blockerCount(),
            base.criticalCount(),
            base.warningCount(),
            base.deterministicRulesetVersion(),
            base.semanticProvider(),
            base.semanticModelVersion(),
            base.producibilityValidatorVersion(),
            null,
            null,
            base.validatedAt(),
            base.expiresAt());

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_NOT_INDEPENDENTLY_REVALIDATED");
  }

  @Test
  void rejectsContentIdMismatch() {
    QueueRenderJobRequest mismatched =
        new QueueRenderJobRequest(
            999L,
            request().promptVersionId(),
            request().validationRecordId(),
            request().jobType(),
            request().openartModel(),
            request().openartParams(),
            null);

    assertThatThrownBy(() -> policy.validate(mismatched, renderReadyEvidence(), now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_IDENTITY_MISMATCH");
  }

  @Test
  void rejectsPromptVersionIdMismatch() {
    QueueRenderJobRequest mismatched =
        new QueueRenderJobRequest(
            request().contentId(),
            999L,
            request().validationRecordId(),
            request().jobType(),
            request().openartModel(),
            request().openartParams(),
            null);

    assertThatThrownBy(() -> policy.validate(mismatched, renderReadyEvidence(), now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_IDENTITY_MISMATCH");
  }

  @Test
  void rejectsRequestPromptHashMismatchingEvidencePromptHash() {
    QueueRenderJobRequest mismatched =
        new QueueRenderJobRequest(
            request().contentId(),
            request().promptVersionId(),
            request().validationRecordId(),
            request().jobType(),
            request().openartModel(),
            request().openartParams(),
            "b".repeat(64));

    assertThatThrownBy(() -> policy.validate(mismatched, renderReadyEvidence(), now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_PROMPT_HASH_MISMATCH");
  }

  @Test
  void acceptsWhenRequestPromptHashIsAbsent() {
    // The request-side hash is an optional defense-in-depth check (callers that already have the
    // immutable prompt text may supply it); its absence is not itself a rejection.
    assertThatCode(() -> policy.validate(request(), renderReadyEvidence(), now))
        .doesNotThrowAnyException();
  }

  @Test
  void rejectsMalformedOrAbsentPromptHash() {
    ValidationEvidenceDto evidence = withPromptSha256(renderReadyEvidence(), null);

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_PROMPT_HASH_INVALID");
  }

  @Test
  void rejectsAbsentDeterministicRulesetVersion() {
    ValidationEvidenceDto base = renderReadyEvidence();
    ValidationEvidenceDto evidence =
        new ValidationEvidenceDto(
            base.validationRecordId(),
            base.contentId(),
            base.promptVersionId(),
            base.promptSha256(),
            base.status(),
            base.blockerCount(),
            base.criticalCount(),
            base.warningCount(),
            null,
            base.semanticProvider(),
            base.semanticModelVersion(),
            base.producibilityValidatorVersion(),
            base.independentRevalidationId(),
            base.independentlyRevalidatedAt(),
            base.validatedAt(),
            base.expiresAt());

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_VERSIONS_INCOMPLETE");
  }

  @Test
  void rejectsAbsentSemanticOrProducibilityVersions() {
    ValidationEvidenceDto base = renderReadyEvidence();
    ValidationEvidenceDto evidence =
        new ValidationEvidenceDto(
            base.validationRecordId(),
            base.contentId(),
            base.promptVersionId(),
            base.promptSha256(),
            base.status(),
            base.blockerCount(),
            base.criticalCount(),
            base.warningCount(),
            base.deterministicRulesetVersion(),
            null,
            base.semanticModelVersion(),
            base.producibilityValidatorVersion(),
            base.independentRevalidationId(),
            base.independentlyRevalidatedAt(),
            base.validatedAt(),
            base.expiresAt());

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_VERSIONS_INCOMPLETE");
  }

  @Test
  void rejectsExpiredEvidence() {
    Instant afterExpiry = renderReadyEvidence().expiresAt().plusSeconds(1);

    assertThatThrownBy(() -> policy.validate(request(), renderReadyEvidence(), afterExpiry))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_EXPIRED");
  }

  @Test
  void rejectsEvidenceWithNoExpiry() {
    ValidationEvidenceDto base = renderReadyEvidence();
    ValidationEvidenceDto evidence =
        new ValidationEvidenceDto(
            base.validationRecordId(),
            base.contentId(),
            base.promptVersionId(),
            base.promptSha256(),
            base.status(),
            base.blockerCount(),
            base.criticalCount(),
            base.warningCount(),
            base.deterministicRulesetVersion(),
            base.semanticProvider(),
            base.semanticModelVersion(),
            base.producibilityValidatorVersion(),
            base.independentRevalidationId(),
            base.independentlyRevalidatedAt(),
            base.validatedAt(),
            null);

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_EXPIRED");
  }

  @Test
  void rejectsVideoWhenVisualEvidenceIsPending() {
    ValidationEvidenceDto base = renderReadyEvidence();
    ValidationEvidenceDto pending =
        new ValidationEvidenceDto(
            base.validationRecordId(),
            base.contentId(),
            base.promptVersionId(),
            base.promptSha256(),
            base.status(),
            base.blockerCount(),
            base.criticalCount(),
            base.warningCount(),
            base.deterministicRulesetVersion(),
            base.semanticProvider(),
            base.semanticModelVersion(),
            base.producibilityValidatorVersion(),
            base.independentRevalidationId(),
            base.independentlyRevalidatedAt(),
            base.validatedAt(),
            base.expiresAt(),
            false,
            false,
            Map.of(
                "firstFrame",
                Map.of("status", "PENDING"),
                "silhouette",
                Map.of("status", "PENDING")));
    assertThatThrownBy(() -> policy.validate(request(), pending, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("VISUAL_EVIDENCE_PENDING");
  }

  @Test
  void firstFrameMayUsePromptStageEligibilityWhileFinalVideoEvidenceIsPending() {
    QueueRenderJobRequest firstFrame =
        new QueueRenderJobRequest(
            10L, 11L, 42L, RenderJob.JobType.FIRST_FRAME, "model-x", Map.of("seed", 1), null);
    ValidationEvidenceDto pendingVideoEvidence =
        new ValidationEvidenceDto(
            42L,
            10L,
            11L,
            "a".repeat(64),
            "BLOCKED",
            2,
            3,
            0,
            "1.5",
            "openai",
            "gpt-4o",
            null,
            null,
            null,
            now.minusSeconds(60),
            now.plusSeconds(3600),
            true,
            false,
            Map.of());

    assertThatCode(() -> policy.validate(firstFrame, pendingVideoEvidence, now))
        .doesNotThrowAnyException();
  }

  @Test
  void firstFrameWithoutPromptStageEligibilityStillFailsClosed() {
    QueueRenderJobRequest firstFrame =
        new QueueRenderJobRequest(
            10L, 11L, 42L, RenderJob.JobType.FIRST_FRAME, "model-x", Map.of("seed", 1), null);
    ValidationEvidenceDto evidence =
        new ValidationEvidenceDto(
            42L,
            10L,
            11L,
            "a".repeat(64),
            "BLOCKED",
            0,
            0,
            0,
            "1.5",
            "openai",
            "gpt-4o",
            null,
            null,
            null,
            now.minusSeconds(60),
            now.plusSeconds(3600),
            false,
            false,
            Map.of());

    assertThatThrownBy(() -> policy.validate(firstFrame, evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("FIRST_FRAME_NOT_ELIGIBLE");
  }

  @Test
  void rejectsFinalRenderWhenCanonicalAuthorizationIsBlockedDespiteLegacyReadyStatus() {
    ValidationEvidenceDto evidence = withRenderAuthorization(renderReadyEvidence(), "BLOCKED_PENDING_EVIDENCE");

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_NOT_RENDER_AUTHORIZED");
  }

  @Test
  void rejectsFinalRenderWhenCanonicalAuthorizationIsMissing() {
    ValidationEvidenceDto evidence = withRenderAuthorization(renderReadyEvidence(), null);

    assertThatThrownBy(() -> policy.validate(request(), evidence, now))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(ex -> ((ValidationEvidenceRejectedException) ex).getErrorCode())
        .isEqualTo("EVIDENCE_NOT_RENDER_AUTHORIZED");
  }

  private QueueRenderJobRequest request() {
    return new QueueRenderJobRequest(
        10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 1), null);
  }

  private ValidationEvidenceDto renderReadyEvidence() {
    return new ValidationEvidenceDto(
        42L,
        10L,
        11L,
        "a".repeat(64),
        "RENDER_READY",
        0,
        0,
        0,
        "1.0",
        "openai",
        "gpt-4o",
        "1.0",
        UUID.randomUUID(),
        now.minusSeconds(60),
        now.minusSeconds(60),
        now.plusSeconds(3600),
        false,
        true,
        visualPasses());
  }

  private ValidationEvidenceDto withRenderAuthorization(
      ValidationEvidenceDto base, String renderAuthorization) {
    return new ValidationEvidenceDto(
        base.validationRecordId(),
        base.contentId(),
        base.promptVersionId(),
        base.promptSha256(),
        base.status(),
        base.blockerCount(),
        base.criticalCount(),
        base.warningCount(),
        base.deterministicRulesetVersion(),
        base.semanticProvider(),
        base.semanticModelVersion(),
        base.producibilityValidatorVersion(),
        base.independentRevalidationId(),
        base.independentlyRevalidatedAt(),
        base.validatedAt(),
        base.expiresAt(),
        base.firstFrameEligible(),
        base.finalVideoEligible(),
        base.visualEvidence(),
        renderAuthorization);
  }

  private Map<String, Object> visualPasses() {
    String evidenceSet = UUID.randomUUID().toString();
    String asset = UUID.randomUUID().toString();
    String hash = "b".repeat(64);
    Map<String, Object> gate =
        Map.of(
            "status", "PASS", "evidenceSetId", evidenceSet, "assetId", asset, "assetSha256", hash);
    return Map.of("firstFrame", gate, "silhouette", gate, "finalVideoEligible", true);
  }

  private ValidationEvidenceDto withStatus(ValidationEvidenceDto base, String status) {
    return new ValidationEvidenceDto(
        base.validationRecordId(),
        base.contentId(),
        base.promptVersionId(),
        base.promptSha256(),
        status,
        base.blockerCount(),
        base.criticalCount(),
        base.warningCount(),
        base.deterministicRulesetVersion(),
        base.semanticProvider(),
        base.semanticModelVersion(),
        base.producibilityValidatorVersion(),
        base.independentRevalidationId(),
        base.independentlyRevalidatedAt(),
        base.validatedAt(),
        base.expiresAt());
  }

  private ValidationEvidenceDto withBlockerCount(ValidationEvidenceDto base, int blockerCount) {
    return new ValidationEvidenceDto(
        base.validationRecordId(),
        base.contentId(),
        base.promptVersionId(),
        base.promptSha256(),
        base.status(),
        blockerCount,
        base.criticalCount(),
        base.warningCount(),
        base.deterministicRulesetVersion(),
        base.semanticProvider(),
        base.semanticModelVersion(),
        base.producibilityValidatorVersion(),
        base.independentRevalidationId(),
        base.independentlyRevalidatedAt(),
        base.validatedAt(),
        base.expiresAt());
  }

  private ValidationEvidenceDto withCriticalCount(ValidationEvidenceDto base, int criticalCount) {
    return new ValidationEvidenceDto(
        base.validationRecordId(),
        base.contentId(),
        base.promptVersionId(),
        base.promptSha256(),
        base.status(),
        base.blockerCount(),
        criticalCount,
        base.warningCount(),
        base.deterministicRulesetVersion(),
        base.semanticProvider(),
        base.semanticModelVersion(),
        base.producibilityValidatorVersion(),
        base.independentRevalidationId(),
        base.independentlyRevalidatedAt(),
        base.validatedAt(),
        base.expiresAt());
  }

  private ValidationEvidenceDto withPromptSha256(ValidationEvidenceDto base, String promptSha256) {
    return new ValidationEvidenceDto(
        base.validationRecordId(),
        base.contentId(),
        base.promptVersionId(),
        promptSha256,
        base.status(),
        base.blockerCount(),
        base.criticalCount(),
        base.warningCount(),
        base.deterministicRulesetVersion(),
        base.semanticProvider(),
        base.semanticModelVersion(),
        base.producibilityValidatorVersion(),
        base.independentRevalidationId(),
        base.independentlyRevalidatedAt(),
        base.validatedAt(),
        base.expiresAt());
  }
}
