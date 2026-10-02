package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.intelligence.IntelligenceContentNotFoundException;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import java.math.BigDecimal;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * {@link RenderJobOrchestrator} now only queues jobs; execution of a queued job's stages has moved
 * to {@code RenderAttemptOrchestrator.processAttempt} in the {@code worker} package (see {@code
 * RenderAttemptOrchestratorTest}), which replaced this class's previous single-long- transaction
 * {@code executeRenderJob} and its recursive rerender.
 */
@ExtendWith(MockitoExtension.class)
class RenderJobOrchestratorTest {

  private static final String PROMPT_SHA = "a".repeat(64);

  @Mock private RenderJobRepository renderJobRepo;

  @Mock private RenderAttemptRepository renderAttemptRepo;

  @Mock private IntelligenceContentClient intelligenceContentClient;

  @Mock private CreditTrackingService creditTrackingService;

  @Mock private BudgetAlertService budgetAlertService;

  @Mock private WebSocketEventPublisher webSocketEventPublisher;

  private RenderJobOrchestrator orchestrator;

  @BeforeEach
  void setUp() {
    orchestrator =
        new RenderJobOrchestrator(
            renderJobRepo,
            renderAttemptRepo,
            intelligenceContentClient,
            creditTrackingService,
            budgetAlertService,
            webSocketEventPublisher);
  }

  private static ContentPromptSnapshot snapshot() {
    return new ContentPromptSnapshot(
        "v1",
        1L,
        "Test Episode",
        "EPISODE",
        "RENDER_READY",
        1L,
        1,
        "Test prompt: Kiko playing in Central Square",
        "{}",
        PROMPT_SHA);
  }

  @Test
  void queueRenderJob_createsJobWithQueuedStatus() {
    // Given: the intelligence service returns an immutable snapshot
    when(intelligenceContentClient.fetch(1L, 1L)).thenReturn(snapshot());
    when(creditTrackingService.canAffordRender(any())).thenReturn(true);
    when(creditTrackingService.getEstimatedCost(any())).thenReturn(new BigDecimal("10"));

    RenderJob savedJob =
        RenderJob.builder()
            .id(UUID.randomUUID())
            .contentId(1L)
            .promptVersionId(1L)
            .contentTitleSnapshot("Test Episode")
            .promptVersionNumberSnapshot(1)
            .promptSha256(PROMPT_SHA)
            .promptTextSnapshot("Test prompt: Kiko playing in Central Square")
            .jobType(RenderJob.JobType.FIRST_FRAME)
            .openartModel("mock_model")
            .status(RenderJob.RenderJobStatus.QUEUED)
            .attemptNumber(1)
            .maxAttempts(3)
            .build();

    when(renderJobRepo.save(any(RenderJob.class))).thenReturn(savedJob);

    // When: Queue a render job
    UUID jobId = orchestrator.queueRenderJob(1L, 1L, RenderJob.JobType.FIRST_FRAME);

    // Then: Job is created with QUEUED status via the HTTP snapshot boundary
    assertThat(jobId).isNotNull();

    verify(intelligenceContentClient).fetch(1L, 1L);
    verify(renderJobRepo)
        .save(
            argThat(
                job ->
                    job.getContentId().equals(1L)
                        && job.getPromptVersionId().equals(1L)
                        && "Test Episode".equals(job.getContentTitleSnapshot())
                        && PROMPT_SHA.equals(job.getPromptSha256())
                        && "Test prompt: Kiko playing in Central Square"
                            .equals(job.getPromptTextSnapshot())));
  }

  @Test
  void queueRenderJob_createsFirstAttemptForWorkerToClaim() {
    // Given: the intelligence service returns an immutable snapshot
    when(intelligenceContentClient.fetch(1L, 1L)).thenReturn(snapshot());
    when(creditTrackingService.canAffordRender(any())).thenReturn(true);
    when(creditTrackingService.getEstimatedCost(any())).thenReturn(new BigDecimal("10"));

    UUID jobId = UUID.randomUUID();
    RenderJob savedJob =
        RenderJob.builder()
            .id(jobId)
            .contentId(1L)
            .promptVersionId(1L)
            .contentTitleSnapshot("Test Episode")
            .promptVersionNumberSnapshot(1)
            .promptSha256(PROMPT_SHA)
            .promptTextSnapshot("Test prompt: Kiko playing in Central Square")
            .jobType(RenderJob.JobType.FIRST_FRAME)
            .openartModel("mock_model")
            .status(RenderJob.RenderJobStatus.QUEUED)
            .attemptNumber(1)
            .maxAttempts(3)
            .build();
    when(renderJobRepo.save(any(RenderJob.class))).thenReturn(savedJob);

    // When: Queue a render job
    orchestrator.queueRenderJob(1L, 1L, RenderJob.JobType.FIRST_FRAME);

    // Then: A durable attempt 1 row exists in stage QUEUED - nothing else would ever be eligible
    // for a worker to claim.
    verify(renderAttemptRepo)
        .save(
            argThat(
                (RenderAttempt attempt) ->
                    attempt.getRenderJobId().equals(jobId)
                        && attempt.getAttemptNumber() == 1
                        && attempt.getStage() == RenderExecutionStage.QUEUED));
  }

  @Test
  void queueRenderJob_contentPromptNotFound_propagatesTypedException() {
    // Given: The intelligence service reports the content/prompt pair is unknown
    Long nonExistentContentId = 999999L;
    when(creditTrackingService.canAffordRender(any())).thenReturn(true);
    when(intelligenceContentClient.fetch(nonExistentContentId, 1L))
        .thenThrow(new IntelligenceContentNotFoundException(nonExistentContentId, 1L));

    // When/Then: Queueing surfaces the typed boundary exception
    assertThatThrownBy(
            () ->
                orchestrator.queueRenderJob(
                    nonExistentContentId, 1L, RenderJob.JobType.FIRST_FRAME))
        .isInstanceOf(IntelligenceContentNotFoundException.class);
  }

  @Test
  void queueRenderJob_promptVersionNotFound_propagatesTypedException() {
    // Given: Prompt version does not belong to the content
    Long nonExistentPromptId = 999999L;
    when(creditTrackingService.canAffordRender(any())).thenReturn(true);
    when(intelligenceContentClient.fetch(1L, nonExistentPromptId))
        .thenThrow(new IntelligenceContentNotFoundException(1L, nonExistentPromptId));

    // When/Then: Queueing surfaces the typed boundary exception
    assertThatThrownBy(
            () ->
                orchestrator.queueRenderJob(1L, nonExistentPromptId, RenderJob.JobType.FIRST_FRAME))
        .isInstanceOf(IntelligenceContentNotFoundException.class);
  }
}
