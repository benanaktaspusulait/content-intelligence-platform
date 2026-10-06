package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.*;
import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtJobResponse;
import com.pompom.creative.openart.dto.OpenArtJobStatus;
import com.pompom.creative.postrender.PostRenderDecision;
import com.pompom.creative.postrender.PostRenderEvaluation;
import com.pompom.creative.postrender.PostRenderEvaluationService;
import com.pompom.creative.qa.QaAnalysisResult;
import com.pompom.creative.qa.QaService;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.AssetLibraryManager;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * One-stage-per-call orchestration: {@link RenderAttemptOrchestrator#processAttempt} must validate
 * lease ownership, execute exactly the attempt's current stage, persist exactly the next stage, and
 * never recurse into executing a subsequent stage within the same call - that is what makes a
 * single claim safe to run on a worker that may be killed between any two stages.
 */
@ExtendWith(MockitoExtension.class)
class RenderAttemptOrchestratorTest {

  private static final String LEASE_OWNER = "worker-1";

  @Mock private RenderJobRepository renderJobRepo;
  @Mock private RenderAttemptRepository renderAttemptRepo;
  @Mock private RenderAssetRepository renderAssetRepo;
  @Mock private OpenArtAdapter openArtAdapter;
  @Mock private AssetLibraryManager assetLibraryManager;
  @Mock private QaService qaService;
  @Mock private PostRenderEvaluationService postRenderEvaluationService;
  @Mock private WebSocketEventPublisher webSocketEventPublisher;
  @Mock private CreditTrackingService creditTrackingService;
  @Mock private RenderSubmissionStateService submissionStateService;

  private RenderAttemptOrchestrator orchestrator;
  private RenderJob job;

  @BeforeEach
  void setUp() {
    orchestrator =
        new RenderAttemptOrchestrator(
            renderJobRepo,
            renderAttemptRepo,
            renderAssetRepo,
            openArtAdapter,
            assetLibraryManager,
            qaService,
            postRenderEvaluationService,
            webSocketEventPublisher,
            submissionStateService,
            creditTrackingService,
            new ObjectMapper());
    job =
        RenderJob.builder()
            .id(UUID.randomUUID())
            .contentId(1L)
            .promptVersionId(1L)
            .contentTitleSnapshot("Test Episode")
            .promptVersionNumberSnapshot(1)
            .promptSha256("a".repeat(64))
            .promptTextSnapshot("a".repeat(120))
            .jobType(RenderJob.JobType.FIRST_FRAME)
            .openartModel("mock_model")
            .status(RenderJob.RenderJobStatus.QUEUED)
            .attemptNumber(1)
            .maxAttempts(3)
            .build();
    lenient().when(renderJobRepo.findById(job.getId())).thenReturn(Optional.of(job));
  }

  private RenderAttempt attempt(RenderExecutionStage stage) {
    RenderAttempt attempt =
        RenderAttempt.builder()
            .id(UUID.randomUUID())
            .renderJobId(job.getId())
            .attemptNumber(1)
            .stage(stage)
            .pollCount(0)
            .leaseOwner(LEASE_OWNER)
            .build();
    lenient().when(renderAttemptRepo.findById(attempt.getId())).thenReturn(Optional.of(attempt));
    lenient()
        .when(submissionStateService.markSubmitting(attempt.getId(), LEASE_OWNER))
        .thenReturn(job);
    return attempt;
  }

  @Test
  void rejectsProcessingWhenLeaseOwnerDoesNotMatch() {
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);
    attempt.setLeaseOwner("someone-else");

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(LeaseNotOwnedException.class);

    verifyNoInteractions(openArtAdapter);
  }

  @Test
  void queuedStageSubmitsToProviderAndAdvancesToProviderQueued() {
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);
    when(openArtAdapter.generateImage(any()))
        .thenReturn(OpenArtJobResponse.builder().jobId("provider-job-1").status("QUEUED").build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    verify(submissionStateService).markSubmitting(attempt.getId(), LEASE_OWNER);
    verify(submissionStateService)
        .markSubmitted(attempt.getId(), job.getId(), "provider-job-1", null);
    verify(openArtAdapter).generateImage(any());
  }

  @Test
  void uncertainProviderSubmissionIsNotRetriedAutomatically() {
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);
    when(openArtAdapter.generateImage(any()))
        .thenThrow(new IllegalStateException("connection lost after submit"));

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("connection lost");

    verify(submissionStateService).markSubmitting(attempt.getId(), LEASE_OWNER);
    verify(submissionStateService)
        .markUncertain(eq(attempt.getId()), eq(job.getId()), any(IllegalStateException.class));
  }

  @Test
  void providerQueuedStagePollsAndStaysQueuedWhenProviderStillRunning() {
    RenderAttempt attempt = attempt(RenderExecutionStage.PROVIDER_QUEUED);
    attempt.setProviderJobId("provider-job-1");
    when(openArtAdapter.getJobStatus("provider-job-1"))
        .thenReturn(OpenArtJobStatus.builder().jobId("provider-job-1").status("RUNNING").build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    RenderAttempt saved = captor.getValue();
    assertThat(saved.getStage()).isEqualTo(RenderExecutionStage.PROVIDER_QUEUED);
    assertThat(saved.getProviderJobState()).isEqualTo(ProviderJobState.RUNNING);
    assertThat(saved.getPollCount()).isEqualTo(1);
    assertThat(saved.getNextPollAt()).isAfter(Instant.now());
    verify(openArtAdapter, never()).downloadAsset(any(), any());
  }

  @Test
  void providerQueuedStageAdvancesToDownloadingOnlyWhenProviderSucceeded() {
    RenderAttempt attempt = attempt(RenderExecutionStage.PROVIDER_QUEUED);
    attempt.setProviderJobId("provider-job-1");
    when(openArtAdapter.getJobStatus("provider-job-1"))
        .thenReturn(
            OpenArtJobStatus.builder()
                .jobId("provider-job-1")
                .status("COMPLETE")
                .creditsUsed(new BigDecimal("12.5"))
                .build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    assertThat(captor.getValue().getStage()).isEqualTo(RenderExecutionStage.DOWNLOADING);
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.DOWNLOADING);
    verify(creditTrackingService)
        .recordProviderUsageIfAbsent(job, new BigDecimal("12.5"), "provider-status");
    verify(openArtAdapter, never()).downloadAsset(any(), any());
  }

  @Test
  void providerQueuedStageFailsAttemptWhenProviderFailed() {
    RenderAttempt attempt = attempt(RenderExecutionStage.PROVIDER_QUEUED);
    attempt.setProviderJobId("provider-job-1");
    when(openArtAdapter.getJobStatus("provider-job-1"))
        .thenReturn(
            OpenArtJobStatus.builder()
                .jobId("provider-job-1")
                .status("FAILED")
                .errorMessage("provider blew up")
                .build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    assertThat(captor.getValue().getStage()).isEqualTo(RenderExecutionStage.FAILED);
    assertThat(captor.getValue().getErrorMessage()).contains("provider blew up");
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.FAILED);
    assertThat(job.getErrorCode()).isEqualTo("PROVIDER_FAILED");
  }

  @Test
  void unknownProviderStateNeverCompletesAndSchedulesAnotherPoll() {
    RenderAttempt attempt = attempt(RenderExecutionStage.PROVIDER_QUEUED);
    attempt.setProviderJobId("provider-job-1");
    when(openArtAdapter.getJobStatus("provider-job-1"))
        .thenReturn(
            OpenArtJobStatus.builder().jobId("provider-job-1").status("SOMETHING_WEIRD").build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    assertThat(captor.getValue().getStage()).isEqualTo(RenderExecutionStage.PROVIDER_QUEUED);
    assertThat(captor.getValue().getProviderJobState()).isEqualTo(ProviderJobState.UNKNOWN);
    verify(openArtAdapter, never()).downloadAsset(any(), any());
  }

  @Test
  void downloadingStageAdvancesToPostRenderQaAfterDownload() {
    RenderAttempt attempt = attempt(RenderExecutionStage.DOWNLOADING);
    attempt.setProviderJobId("provider-job-1");
    when(assetLibraryManager.getNextVersion(any(), any())).thenReturn(1);
    when(assetLibraryManager.getAssetPath(any(), any(), anyInt()))
        .thenReturn(Path.of(System.getProperty("java.io.tmpdir"), "asset.mp4"));
    when(openArtAdapter.downloadAsset(any(), any()))
        .thenReturn(DownloadResult.builder().assetPath("/tmp/asset.mp4").build());
    when(assetLibraryManager.recordAsset(any(), any()))
        .thenReturn(RenderAsset.builder().id(UUID.randomUUID()).build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    RenderAttempt saved = captor.getValue();
    assertThat(saved.getStage()).isEqualTo(RenderExecutionStage.POST_RENDER_QA);
    // POST_RENDER_QA is claimable (not terminal) - the lease must be released here too, exactly
    // like every other non-terminal stage transition, or the attempt sits unclaimable until the
    // downloading worker's lease naturally expires.
    assertThat(saved.getLeaseOwner()).isNull();
    assertThat(saved.getLeaseExpiresAt()).isNull();
  }

  @Test
  void postRenderQaAcceptCompletesTheAttemptAndJob() {
    RenderAttempt attempt = attempt(RenderExecutionStage.POST_RENDER_QA);
    RenderAsset asset = RenderAsset.builder().id(UUID.randomUUID()).renderJob(job).build();
    attempt.setAssetId(asset.getId());
    when(renderAssetRepo.findById(asset.getId())).thenReturn(Optional.of(asset));
    when(qaService.analyzeAsset(any()))
        .thenReturn(QaAnalysisResult.builder().complianceScore(100).build());
    when(postRenderEvaluationService.evaluate(any(), any(), any(), any()))
        .thenReturn(evaluation(asset, PostRenderDecision.PASS));

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> attemptCaptor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(attemptCaptor.capture());
    assertThat(attemptCaptor.getValue().getStage()).isEqualTo(RenderExecutionStage.COMPLETE);

    verify(renderJobRepo).save(argThat(j -> j.getStatus() == RenderJob.RenderJobStatus.COMPLETE));
  }

  @Test
  void postRenderQaFailAbandonsWithoutUsingLegacyDecisionEngine() {
    RenderAttempt attempt = attempt(RenderExecutionStage.POST_RENDER_QA);
    RenderAsset asset = RenderAsset.builder().id(UUID.randomUUID()).renderJob(job).build();
    attempt.setAssetId(asset.getId());
    when(renderAssetRepo.findById(asset.getId())).thenReturn(Optional.of(asset));
    when(qaService.analyzeAsset(any()))
        .thenReturn(QaAnalysisResult.builder().complianceScore(50).build());
    when(postRenderEvaluationService.evaluate(any(), any(), any(), any()))
        .thenReturn(evaluation(asset, PostRenderDecision.FAIL));

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    assertThat(captor.getValue().getStage()).isEqualTo(RenderExecutionStage.ABANDONED);
    verify(renderJobRepo).save(argThat(j -> j.getStatus() == RenderJob.RenderJobStatus.ABANDONED));
  }

  @Test
  void postRenderQaAbandonMarksAttemptAbandonedAndJobAbandoned() {
    RenderAttempt attempt = attempt(RenderExecutionStage.POST_RENDER_QA);
    RenderAsset asset = RenderAsset.builder().id(UUID.randomUUID()).renderJob(job).build();
    attempt.setAssetId(asset.getId());
    when(renderAssetRepo.findById(asset.getId())).thenReturn(Optional.of(asset));
    when(qaService.analyzeAsset(any()))
        .thenReturn(QaAnalysisResult.builder().characterIdentityVerified(false).build());
    when(postRenderEvaluationService.evaluate(any(), any(), any(), any()))
        .thenReturn(evaluation(asset, PostRenderDecision.FAIL));

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<RenderAttempt> captor = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(captor.capture());
    assertThat(captor.getValue().getStage()).isEqualTo(RenderExecutionStage.ABANDONED);

    verify(renderJobRepo).save(argThat(j -> j.getStatus() == RenderJob.RenderJobStatus.ABANDONED));
  }

  @Test
  void postRenderQaWithNoRecordedAssetFailsWithClearError() {
    // An attempt should never reach POST_RENDER_QA without assetId set (download() always sets
    // it before advancing), but if it somehow did, the failure must be a clear, diagnosable
    // IllegalStateException rather than an opaque exception from calling findById(null).
    RenderAttempt attempt = attempt(RenderExecutionStage.POST_RENDER_QA);

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining(attempt.getId().toString());

    verifyNoInteractions(renderAssetRepo, qaService, postRenderEvaluationService);
  }

  private PostRenderEvaluationService.EvaluationResult evaluation(
      RenderAsset asset, PostRenderDecision decision) {
    PostRenderEvaluation evaluation =
        PostRenderEvaluation.builder()
            .id(UUID.randomUUID())
            .renderAsset(asset)
            .renderAttemptId(UUID.randomUUID())
            .evidenceVersion("render-evidence-v1")
            .postRenderRulesetVersion("POST_RENDER_RULESET_1.0")
            .analyzerVersions("{}")
            .evidenceSnapshot("{}")
            .overallDecision(decision)
            .humanReviewRequired(decision == PostRenderDecision.HUMAN_REVIEW)
            .startedAt(Instant.now())
            .completedAt(Instant.now())
            .build();
    return new PostRenderEvaluationService.EvaluationResult(evaluation, null, List.of());
  }
}
