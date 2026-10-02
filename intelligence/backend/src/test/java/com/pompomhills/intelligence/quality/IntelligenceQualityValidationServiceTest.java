package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.content.ContentPromptNotFoundException;
import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.content.ContentPromptSnapshot;
import java.time.Duration;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * Covers {@link IntelligenceQualityValidationService}, which is what backs the public {@code POST
 * /api/v1/intelligence/quality/validate} endpoint: it calls the ML service, persists the result as
 * a {@link QualityValidationEntity}, and - only when the request is linked to a real content/prompt
 * version - fills in the evidence fields {@link ValidationEvidenceService} requires for render
 * authorization.
 */
class IntelligenceQualityValidationServiceTest {

  private static final Duration EVIDENCE_FRESHNESS_TTL = Duration.ofHours(24);

  private QualityMlClient mlClient;
  private QualityValidationRepository repository;
  private ContentPromptQueryService contentPrompts;
  private IntelligenceQualityValidationService service;

  @BeforeEach
  void setUp() {
    mlClient = mock(QualityMlClient.class);
    repository = mock(QualityValidationRepository.class);
    contentPrompts = mock(ContentPromptQueryService.class);
    service =
        new IntelligenceQualityValidationService(
            mlClient, repository, contentPrompts, EVIDENCE_FRESHNESS_TTL);
    // Mirrors real JPA save(): assigns a generated ID as a side effect and returns the same
    // (now-identified) instance, the way Spring Data's save() behaves for a new entity.
    when(repository.save(any()))
        .thenAnswer(
            invocation -> {
              QualityValidationEntity entity = invocation.getArgument(0);
              entity.setId(1L);
              return entity;
            });
  }

  @Test
  void linkedValidationUsesStoredImmutablePromptTextNotTheRequestBody() {
    String storedPromptText = "b".repeat(150);
    ContentPromptSnapshot snapshot =
        new ContentPromptSnapshot(
            "v1",
            10L,
            "Title",
            "EPISODE",
            "DRAFT",
            11L,
            1,
            storedPromptText,
            null,
            "deadbeef".repeat(8));
    when(contentPrompts.load(10L, 11L)).thenReturn(snapshot);
    when(mlClient.validatePrompt(storedPromptText, "1.0")).thenReturn(sampleReport());

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("a".repeat(150), "1.0", 10L, 11L);

    service.validateAndPersistEvidence(request);

    verify(mlClient).validatePrompt(storedPromptText, "1.0");
  }

  @Test
  void linkedValidationPersistsEvidenceFieldsFromTheSnapshot() {
    String storedPromptText = "c".repeat(150);
    ContentPromptSnapshot snapshot =
        new ContentPromptSnapshot(
            "v1",
            10L,
            "Title",
            "EPISODE",
            "DRAFT",
            11L,
            1,
            storedPromptText,
            null,
            "feedface".repeat(8));
    when(contentPrompts.load(10L, 11L)).thenReturn(snapshot);
    when(mlClient.validatePrompt(storedPromptText, "1.0")).thenReturn(sampleReport());

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest(
            "ignored body text here, at least 100 chars long xx", "1.0", 10L, 11L);

    service.validateAndPersistEvidence(request);

    ArgumentCaptor<QualityValidationEntity> captor =
        ArgumentCaptor.forClass(QualityValidationEntity.class);
    verify(repository).save(captor.capture());
    QualityValidationEntity saved = captor.getValue();
    assertThat(saved.getContentId()).isEqualTo(10L);
    assertThat(saved.getPromptVersionId()).isEqualTo(11L);
    assertThat(saved.getPromptSha256()).isEqualTo("feedface".repeat(8));
    assertThat(saved.getPromptText()).isEqualTo(storedPromptText);
    assertThat(saved.getDeterministicRulesetVersion()).isEqualTo("1.0");
    assertThat(saved.getValidatedAt()).isNotNull();
  }

  @Test
  void linkedValidationSetsExpiresAtOneFreshnessTtlAfterValidatedAt() {
    ContentPromptSnapshot snapshot =
        new ContentPromptSnapshot(
            "v1",
            10L,
            "Title",
            "EPISODE",
            "DRAFT",
            11L,
            1,
            "d".repeat(150),
            null,
            "beefbeef".repeat(8));
    when(contentPrompts.load(10L, 11L)).thenReturn(snapshot);
    when(mlClient.validatePrompt(any(), any())).thenReturn(sampleReport());

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("e".repeat(150), "1.0", 10L, 11L);

    service.validateAndPersistEvidence(request);

    ArgumentCaptor<QualityValidationEntity> captor =
        ArgumentCaptor.forClass(QualityValidationEntity.class);
    verify(repository).save(captor.capture());
    QualityValidationEntity saved = captor.getValue();
    assertThat(saved.getExpiresAt())
        .isCloseTo(
            saved.getValidatedAt().plus(EVIDENCE_FRESHNESS_TTL),
            org.assertj.core.api.Assertions.within(Duration.ofSeconds(1)));
  }

  @Test
  void unlinkedValidationNeverCallsContentLookupAndPersistsWithoutEvidenceLinkage() {
    when(mlClient.validatePrompt(any(), any())).thenReturn(sampleReport());

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("x".repeat(150), "1.0", null, null);

    service.validateAndPersistEvidence(request);

    verifyNoInteractions(contentPrompts);
    ArgumentCaptor<QualityValidationEntity> captor =
        ArgumentCaptor.forClass(QualityValidationEntity.class);
    verify(repository).save(captor.capture());
    assertThat(captor.getValue().getContentId()).isNull();
    assertThat(captor.getValue().getPromptSha256()).isNull();
    assertThat(captor.getValue().getExpiresAt()).isNull();
  }

  @Test
  void unlinkedValidationStillRecordsValidatedAt() {
    // Even though an unlinked record can never become render-ready, validatedAt is a general
    // "when was this validation produced" timestamp that every persisted record should carry.
    when(mlClient.validatePrompt(any(), any())).thenReturn(sampleReport());

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("x".repeat(150), "1.0", null, null);

    service.validateAndPersistEvidence(request);

    ArgumentCaptor<QualityValidationEntity> captor =
        ArgumentCaptor.forClass(QualityValidationEntity.class);
    verify(repository).save(captor.capture());
    assertThat(captor.getValue().getValidatedAt()).isNotNull();
  }

  @Test
  void returnsTheValidationRecordIdFromTheSavedEntity() {
    when(mlClient.validatePrompt(any(), any())).thenReturn(sampleReport());

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("x".repeat(150), "1.0", null, null);

    IntelligenceValidateResponse response = service.validateAndPersistEvidence(request);

    assertThat(response.validationRecordId()).isEqualTo(1L);
    assertThat(response.report()).isEqualTo(sampleReport());
  }

  @Test
  void linkedRequestAcceptsAShortOrBlankPromptBodySinceItIsDiscarded() {
    ContentPromptSnapshot snapshot =
        new ContentPromptSnapshot(
            "v1",
            10L,
            "Title",
            "EPISODE",
            "DRAFT",
            11L,
            1,
            "f".repeat(150),
            null,
            "cafebabe".repeat(8));
    when(contentPrompts.load(10L, 11L)).thenReturn(snapshot);
    when(mlClient.validatePrompt(any(), any())).thenReturn(sampleReport());

    // Deliberately short/placeholder body text - must not be rejected, since a linked request
    // never actually uses this field.
    IntelligenceValidateRequest request = new IntelligenceValidateRequest("x", "1.0", 10L, 11L);

    IntelligenceValidateResponse response = service.validateAndPersistEvidence(request);

    assertThat(response.validationRecordId()).isEqualTo(1L);
  }

  @Test
  void unlinkedRequestWithBlankPromptBodyIsRejected() {
    IntelligenceValidateRequest request = new IntelligenceValidateRequest(" ", "1.0", null, null);

    org.assertj.core.api.Assertions.assertThatThrownBy(
            () -> service.validateAndPersistEvidence(request))
        .isInstanceOf(IllegalArgumentException.class);
    verifyNoInteractions(mlClient);
  }

  @Test
  void unlinkedRequestWithTooShortPromptBodyIsRejected() {
    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("too short", "1.0", null, null);

    org.assertj.core.api.Assertions.assertThatThrownBy(
            () -> service.validateAndPersistEvidence(request))
        .isInstanceOf(IllegalArgumentException.class);
    verifyNoInteractions(mlClient);
  }

  @Test
  void propagatesContentPromptNotFoundForAnInvalidLink() {
    when(contentPrompts.load(10L, 999L)).thenThrow(new ContentPromptNotFoundException(10L, 999L));

    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("x".repeat(150), "1.0", 10L, 999L);

    org.assertj.core.api.Assertions.assertThatThrownBy(
            () -> service.validateAndPersistEvidence(request))
        .isInstanceOf(ContentPromptNotFoundException.class);
    verifyNoInteractions(mlClient);
  }

  private QualityReportDto sampleReport() {
    return new QualityReportDto(
        95.0,
        "RENDER_READY",
        "1.0",
        0,
        0,
        0,
        Map.of(),
        java.util.List.of(),
        java.util.List.of(),
        new ScoreCardDto(95.0, "Excellent", "green"),
        new TimelineDataDto(java.util.List.of(), java.util.List.of(), java.util.List.of()));
  }
}
