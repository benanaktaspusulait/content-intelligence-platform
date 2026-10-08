package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ValidationEvidenceServiceTest {

  private QualityValidationRepository repository;
  private ValidationEvidenceService service;

  @BeforeEach
  void setUp() {
    repository = mock(QualityValidationRepository.class);
    service = new ValidationEvidenceService(repository);
  }

  @Test
  void returnsCompleteRecordAsRenderReady() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    when(repository.findById(42L)).thenReturn(Optional.of(entity));
    stubMatchingIndependentRevalidation(entity);

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.validationRecordId()).isEqualTo(42L);
    assertThat(evidence.status()).isEqualTo(ValidationDecisionStatus.RENDER_READY);
    assertThat(evidence.promptSha256()).hasSize(64);
    assertThat(evidence.independentRevalidationId()).isNotNull();
    assertThat(evidence.renderAuthorization()).isNull();
  }

  @Test
  void copiesFamily8RenderAuthorizationFromReportSnapshotInsteadOfLegacyStatus() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setReportJson(
        "{\"preRenderAssessment\":{\"prompt_stage\":\"READY_FOR_FIRST_FRAME\","
            + "\"render_authorization\":{\"status\":\"BLOCKED_PENDING_EVIDENCE\"},"
            + "\"family8\":{\"renderAuthorization\":{\"status\":\"AUTHORIZED\"}}}}");
    when(repository.findById(42L)).thenReturn(Optional.of(entity));
    stubMatchingIndependentRevalidation(entity);

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.renderAuthorization()).isEqualTo("AUTHORIZED");
  }

  @Test
  void copiesUnrecognizedFamily8RenderAuthorizationUnchanged() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setReportJson(
        "{\"preRenderAssessment\":{\"family8\":{\"renderAuthorization\":{\"status\":\"SOMETHING_NEW\"}}}}");
    when(repository.findById(42L)).thenReturn(Optional.of(entity));
    stubMatchingIndependentRevalidation(entity);

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.renderAuthorization()).isEqualTo("SOMETHING_NEW");
  }

  @Test
  void derivesFirstFrameEligibilityFromPersistedReportSnapshotWithoutRewritingParent() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("BLOCKED");
    entity.setReportJson(
        "{\"preRenderAssessment\":{\"prompt_stage\":\"READY_FOR_FIRST_FRAME\",\"render_authorization\":{\"status\":\"BLOCKED_PENDING_EVIDENCE\"}}}");
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.firstFrameEligible()).isTrue();
    assertThat(evidence.finalVideoEligible()).isFalse();
    assertThat(evidence.visualEvidence().get("firstFrame")).isNotNull();
    assertThat(entity.getReportJson()).contains("READY_FOR_FIRST_FRAME");
  }
  @Test
  void missingRecordThrowsNotFound() {
    when(repository.findById(404L)).thenReturn(Optional.empty());

    assertThatThrownBy(() -> service.getEvidence(404L))
        .isInstanceOf(ValidationEvidenceNotFoundException.class)
        .hasMessageContaining("404");
  }

  @Test
  void legacyRecordMissingContentLinkageIsIncomplete() {
    // Legacy rows created before this migration have no content/prompt linkage and no
    // immutable evidence fields populated - they must never be reported as usable evidence.
    QualityValidationEntity legacy = new QualityValidationEntity();
    legacy.setId(7L);
    legacy.setPromptText("legacy prompt text from before evidence tracking existed");
    legacy.setRulesetVersion("1.0");
    legacy.setOverallScore(80.0);
    legacy.setStatus("RENDER_READY");
    legacy.setCreatedAt(Instant.now());
    when(repository.findById(7L)).thenReturn(Optional.of(legacy));

    assertThatThrownBy(() -> service.getEvidence(7L))
        .isInstanceOf(ValidationEvidenceIncompleteException.class)
        .hasMessageContaining("7");
  }

  @Test
  void negativeBlockerCountIsIncomplete() {
    QualityValidationEntity entity = completeEntity();
    entity.setBlockerCount(-1);
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    assertThatThrownBy(() -> service.getEvidence(42L))
        .isInstanceOf(ValidationEvidenceIncompleteException.class);
  }

  @Test
  void malformedPromptHashIsIncomplete() {
    QualityValidationEntity entity = completeEntity();
    entity.setPromptSha256("not-a-valid-sha256");
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    assertThatThrownBy(() -> service.getEvidence(42L))
        .isInstanceOf(ValidationEvidenceIncompleteException.class);
  }

  @Test
  void missingSemanticIdentityCannotBeRenderReadyEvenWhenStatusSaysSo() {
    // The ML service does not yet populate semantic/producibility/independent-revalidation
    // identity (added later in Slice C). Evidence missing those fields must never be surfaced
    // as RENDER_READY, regardless of what the stored status column says, so a render queue
    // gate built against this evidence can never fabricate authorization.
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setSemanticProvider(null);
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.status()).isNotEqualTo(ValidationDecisionStatus.RENDER_READY);
    assertThat(evidence.status()).isEqualTo(ValidationDecisionStatus.NEEDS_REVISION);
  }

  @Test
  void missingIndependentRevalidationCannotBeRenderReady() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setIndependentRevalidationId(null);
    entity.setIndependentlyRevalidatedAt(null);
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.status()).isEqualTo(ValidationDecisionStatus.NEEDS_REVISION);
  }

  @Test
  void expiredEvidenceCannotBeRenderReady() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setExpiresAt(Instant.now().minusSeconds(1));
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.status()).isEqualTo(ValidationDecisionStatus.NEEDS_REVISION);
  }

  @Test
  void evidenceWithNoExpiryIsTreatedAsAlreadyExpired() {
    // expiresAt is only ever populated once a freshness policy exists upstream (today it is
    // always null). Absence must never be read as "never expires".
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setExpiresAt(null);
    when(repository.findById(42L)).thenReturn(Optional.of(entity));

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.status()).isEqualTo(ValidationDecisionStatus.NEEDS_REVISION);
  }

  @Test
  void unexpiredEvidenceWithAllFieldsPresentIsRenderReady() {
    QualityValidationEntity entity = completeEntity();
    entity.setStatus("RENDER_READY");
    entity.setExpiresAt(Instant.now().plusSeconds(3600));
    when(repository.findById(42L)).thenReturn(Optional.of(entity));
    stubMatchingIndependentRevalidation(entity);

    ValidationEvidenceResponse evidence = service.getEvidence(42L);

    assertThat(evidence.status()).isEqualTo(ValidationDecisionStatus.RENDER_READY);
  }

  /**
   * resolveStatus cross-references entity.getIndependentRevalidationId() against a SEPARATE
   * stored row (via repository.findByValidationRunId) to confirm the independent revalidation
   * genuinely exists, matches this record's evidence identity, and is itself a clean
   * RENDER_READY run - this is what makes "independent" real rather than a self-referential
   * field. Any test exercising the RENDER_READY path must stub this second row too, or the
   * cross-reference legitimately (and correctly) fails closed to NEEDS_REVISION.
   */
  private void stubMatchingIndependentRevalidation(QualityValidationEntity primary) {
    QualityValidationEntity revalidation = new QualityValidationEntity();
    revalidation.setId(primary.getId() + 1000);
    revalidation.setValidationRunId(primary.getIndependentRevalidationId());
    revalidation.setContentId(primary.getContentId());
    revalidation.setPromptVersionId(primary.getPromptVersionId());
    revalidation.setPromptSha256(primary.getPromptSha256());
    revalidation.setDeterministicRulesetVersion(primary.getDeterministicRulesetVersion());
    revalidation.setSemanticProvider(primary.getSemanticProvider());
    revalidation.setSemanticModelVersion(primary.getSemanticModelVersion());
    revalidation.setProducibilityValidatorVersion(primary.getProducibilityValidatorVersion());
    revalidation.setStatus("RENDER_READY");
    revalidation.setBlockerCount(0);
    revalidation.setCriticalCount(0);
    revalidation.setValidatedAt(primary.getIndependentlyRevalidatedAt());
    when(repository.findByValidationRunId(primary.getIndependentRevalidationId()))
        .thenReturn(Optional.of(revalidation));
  }

  private QualityValidationEntity completeEntity() {
    QualityValidationEntity entity = new QualityValidationEntity();
    entity.setId(42L);
    entity.setContentId(10L);
    entity.setPromptVersionId(11L);
    entity.setPromptText("a".repeat(120));
    entity.setPromptSha256("a".repeat(64));
    entity.setRulesetVersion("1.0");
    entity.setOverallScore(95.0);
    entity.setStatus("NEEDS_REVISION");
    entity.setBlockerCount(0);
    entity.setCriticalCount(0);
    entity.setWarningCount(0);
    entity.setDeterministicRulesetVersion("1.0");
    entity.setSemanticProvider("openai");
    entity.setSemanticModelVersion("gpt-4o-2026-01");
    entity.setProducibilityValidatorVersion("1.0");
    entity.setIndependentRevalidationId(UUID.randomUUID());
    entity.setIndependentlyRevalidatedAt(Instant.now());
    entity.setValidatedAt(Instant.now());
    entity.setExpiresAt(Instant.now().plusSeconds(3600));
    entity.setCreatedAt(Instant.now());
    return entity;
  }
}
