package com.pompom.creative.queue;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.BudgetAlertService;
import com.pompom.creative.service.CreditTrackingService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.AbstractPlatformTransactionManager;
import org.springframework.transaction.support.DefaultTransactionStatus;

/**
 * {@link RenderJobQueueService#queue} must create a render job only when {@link
 * ValidationEvidencePolicy} accepts the fetched evidence, must create zero rows on any rejection,
 * and must treat a repeated {@code Idempotency-Key} as a replay (same canonical payload) or a
 * conflict (different payload) rather than a second job.
 */
class RenderJobQueueServiceTest {

  private RenderJobRepository repository;
  private RenderAttemptRepository attemptRepository;
  private IntelligenceValidationEvidenceClient evidenceClient;
  private IntelligenceContentClient contentClient;
  private CreditTrackingService creditTrackingService;
  private BudgetAlertService budgetAlertService;
  private ValidationEvidencePolicy policy;
  private RequestFingerprint fingerprints;
  private RenderJobQueueService service;

  @BeforeEach
  void setUp() {
    repository = mock(RenderJobRepository.class);
    attemptRepository = mock(RenderAttemptRepository.class);
    evidenceClient = mock(IntelligenceValidationEvidenceClient.class);
    contentClient = mock(IntelligenceContentClient.class);
    creditTrackingService = mock(CreditTrackingService.class);
    budgetAlertService = mock(BudgetAlertService.class);
    policy = new ValidationEvidencePolicy();
    fingerprints = new RequestFingerprint(new ObjectMapper());
    service =
        new RenderJobQueueService(
            repository,
            attemptRepository,
            evidenceClient,
            contentClient,
            policy,
            fingerprints,
            creditTrackingService,
            budgetAlertService,
            new NoOpTransactionManager());
    lenient().when(contentClient.fetch(10L, 11L)).thenReturn(promptSnapshot());
    lenient().when(creditTrackingService.canAffordRender(any())).thenReturn(true);
    lenient().when(creditTrackingService.getEstimatedCost(any())).thenReturn(BigDecimal.TEN);

    // Mirrors real JPA save(): assigns a generated ID as a side effect for a new entity.
    when(repository.save(any(RenderJob.class)))
        .thenAnswer(
            invocation -> {
              RenderJob job = invocation.getArgument(0);
              if (job.getId() == null) {
                job.setId(UUID.randomUUID());
              }
              return job;
            });
  }

  @Test
  void queuesANewJobWhenEvidenceIsAcceptedAndKeyIsUnused() {
    when(repository.findByIdempotencyKey("key-1")).thenReturn(Optional.empty());
    when(evidenceClient.getEvidence(42L)).thenReturn(renderReadyEvidence());

    QueueRenderJobResponse response = service.queue("key-1", request());

    assertThat(response.replay()).isFalse();
    assertThat(response.renderJobId()).isNotNull();

    ArgumentCaptor<RenderJob> captor = ArgumentCaptor.forClass(RenderJob.class);
    verify(repository).save(captor.capture());
    RenderJob saved = captor.getValue();
    assertThat(saved.getContentId()).isEqualTo(10L);
    assertThat(saved.getPromptVersionId()).isEqualTo(11L);
    assertThat(saved.getValidationRecordId()).isEqualTo(42L);
    assertThat(saved.getIdempotencyKey()).isEqualTo("key-1");
    assertThat(saved.getRequestFingerprint()).matches("^[0-9a-f]{64}$");

    // The first durable RenderAttempt row must exist in the same transaction - this is the only
    // production path reachable from the HTTP controller, so without this a queued job would
    // have nothing for a worker to ever claim.
    ArgumentCaptor<RenderAttempt> attemptCaptor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(attemptRepository).save(attemptCaptor.capture());
    RenderAttempt savedAttempt = attemptCaptor.getValue();
    assertThat(savedAttempt.getRenderJobId()).isEqualTo(saved.getId());
    assertThat(savedAttempt.getAttemptNumber()).isEqualTo(1);
    assertThat(savedAttempt.getStage()).isEqualTo(RenderExecutionStage.QUEUED);
  }

  @Test
  void rejectsAndCreatesNoRowWhenEvidenceIsNotRenderReady() {
    when(repository.findByIdempotencyKey("key-1")).thenReturn(Optional.empty());
    when(evidenceClient.getEvidence(42L)).thenReturn(withStatus(renderReadyEvidence(), "BLOCKED"));

    assertThatThrownBy(() -> service.queue("key-1", request()))
        .isInstanceOf(ValidationEvidenceRejectedException.class);

    verify(repository, never()).save(any());
  }

  @Test
  void replaysTheExistingJobWhenKeyAndPayloadMatch() {
    RenderJob existing = existingJobFor("key-1", request());
    when(repository.findByIdempotencyKey("key-1")).thenReturn(Optional.of(existing));

    QueueRenderJobResponse response = service.queue("key-1", request());

    assertThat(response.replay()).isTrue();
    assertThat(response.renderJobId()).isEqualTo(existing.getId());
    verify(repository, never()).save(any());
    // A replay must never re-contact intelligence or re-run the policy: the job already exists.
    verify(evidenceClient, never()).getEvidence(anyLong());
  }

  @Test
  void rejectsWithConflictWhenKeyMatchesButPayloadDiffers() {
    RenderJob existing = existingJobFor("key-1", request());
    when(repository.findByIdempotencyKey("key-1")).thenReturn(Optional.of(existing));

    QueueRenderJobRequest differentPayload =
        new QueueRenderJobRequest(
            10L, 11L, 42L, RenderJob.JobType.VIDEO, "a-different-model", Map.of(), null);

    assertThatThrownBy(() -> service.queue("key-1", differentPayload))
        .isInstanceOf(IdempotencyKeyConflictException.class);

    verify(repository, never()).save(any());
  }

  private RenderJob existingJobFor(String idempotencyKey, QueueRenderJobRequest request) {
    return RenderJob.builder()
        .id(UUID.randomUUID())
        .contentId(request.contentId())
        .promptVersionId(request.promptVersionId())
        .contentTitleSnapshot("title")
        .promptVersionNumberSnapshot(1)
        .promptSha256("a".repeat(64))
        .promptTextSnapshot("a".repeat(120))
        .validationRecordId(request.validationRecordId())
        .evidenceDeterministicRulesetVersion("1.0")
        .evidenceSemanticProvider("openai")
        .evidenceSemanticModelVersion("gpt-4o")
        .evidenceProducibilityValidatorVersion("1.0")
        .evidenceIndependentRevalidationId(UUID.randomUUID())
        .evidenceIndependentlyRevalidatedAt(Instant.now())
        .evidenceValidatedAt(Instant.now())
        .idempotencyKey(idempotencyKey)
        .requestFingerprint(fingerprints.sha256(request))
        .jobType(request.jobType())
        .openartModel(request.openartModel())
        .build();
  }

  private QueueRenderJobRequest request() {
    return new QueueRenderJobRequest(
        10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 1), null);
  }

  private ValidationEvidenceDto renderReadyEvidence() {
    Instant now = Instant.now();
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
        now.plusSeconds(3600));
  }

  private ContentPromptSnapshot promptSnapshot() {
    return new ContentPromptSnapshot(
        "v1",
        10L,
        "Kiko Episode",
        "REEL",
        "RENDER_READY",
        11L,
        3,
        "a".repeat(120),
        "{}",
        "a".repeat(64));
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

  /**
   * No real transactional resource is in play against a mocked repository, so this fake just runs
   * the transaction callback directly - it exists purely to satisfy {@code RenderJobQueueService}'s
   * {@link org.springframework.transaction.PlatformTransactionManager} dependency in a unit test,
   * not to exercise any transaction semantics (those are covered against real Postgres by {@code
   * RenderJobIdempotencyPostgresTest}).
   */
  private static final class NoOpTransactionManager extends AbstractPlatformTransactionManager {
    @Override
    protected Object doGetTransaction() {
      return new Object();
    }

    @Override
    protected void doBegin(Object transaction, TransactionDefinition definition) {}

    @Override
    protected void doCommit(DefaultTransactionStatus status) {}

    @Override
    protected void doRollback(DefaultTransactionStatus status) {}
  }
}
