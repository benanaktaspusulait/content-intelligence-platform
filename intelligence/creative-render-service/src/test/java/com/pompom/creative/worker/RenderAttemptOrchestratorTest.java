package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.*;
import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.OpenArtReferenceResolver;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtImageRequest;
import com.pompom.creative.openart.dto.OpenArtVideoRequest;
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
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.queue.ProductionLifecycleGuard;
import com.pompom.creative.queue.ValidationEvidencePolicy;
import com.pompom.creative.queue.ValidationEvidenceRejectedException;
import com.pompom.creative.visual.VisualReferencePlanningService;
import com.pompom.creative.workflow.PostFamilyAdmissionClient;
import com.pompom.creative.service.AssetLibraryManager;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.service.VideoUpscaleService;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.Map;
import java.util.HashMap;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

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
  @Mock private VideoUpscaleService videoUpscaleService;
  @Mock private OpenArtReferenceResolver referenceResolver;
  @Mock private RenderSubmissionStateService submissionStateService;
  @Mock private IntelligenceValidationEvidenceClient evidenceClient;
  @Mock private IntelligenceContentClient contentClient;
  @Mock private ValidationEvidencePolicy validationEvidencePolicy;
  @Mock private PostFamilyAdmissionClient workflowAdmission;
  @Mock private ProductionLifecycleGuard productionLifecycleGuard;
  @Mock private VisualReferencePlanningService visualReferencePlanning;

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
            videoUpscaleService,
            referenceResolver,
            new ObjectMapper());
    ReflectionTestUtils.setField(orchestrator, "evidenceClient", evidenceClient);
    ReflectionTestUtils.setField(orchestrator, "contentClient", contentClient);
    ReflectionTestUtils.setField(orchestrator, "validationEvidencePolicy", validationEvidencePolicy);
    ReflectionTestUtils.setField(orchestrator, "workflowAdmission", workflowAdmission);
    ReflectionTestUtils.setField(orchestrator, "productionLifecycleGuard", productionLifecycleGuard);
    ReflectionTestUtils.setField(orchestrator, "visualReferencePlanning", visualReferencePlanning);
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
            .creativeContractSnapshot("{\"intent\":{\"characterIntent\":{}}}")
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
    prepareValidFirstFrameAdmission();
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);
    when(referenceResolver.resolveCharacterReferences(anyString()))
        .thenReturn(List.of("/tmp/kiko.png", "/tmp/mimi.png"));
    when(openArtAdapter.generateImage(any()))
        .thenReturn(OpenArtJobResponse.builder().jobId("provider-job-1").status("QUEUED").build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    verify(submissionStateService).markSubmitting(attempt.getId(), LEASE_OWNER);
    verify(submissionStateService)
        .markSubmitted(
            attempt.getId(),
            job.getId(),
            "provider-job-1",
            null,
            RenderProviderOperation.FIRST_FRAME);
    ArgumentCaptor<OpenArtImageRequest> imageRequest =
        ArgumentCaptor.forClass(OpenArtImageRequest.class);
    verify(openArtAdapter).generateImage(imageRequest.capture());
    assertThat(imageRequest.getValue().getReferenceImagePaths())
        .containsExactly("/tmp/kiko.png", "/tmp/mimi.png");
    verify(validationEvidencePolicy).validate(any(), any(), any());
    verify(productionLifecycleGuard).assertEligible(eq(1L), eq(1L), eq("a".repeat(64)), any());
  }

  @Test
  void missingValidationRecordBlocksFirstFrameBeforeProviderDispatch() {
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(ValidationEvidenceRejectedException.class);

    verify(openArtAdapter, never()).generateImage(any());
    verify(submissionStateService, never()).markSubmitting(any(), anyString());
    verify(submissionStateService).markAdmissionRejected(eq(attempt.getId()), eq(job.getId()), eq(LEASE_OWNER), eq("RENDER_ADMISSION_UNAVAILABLE"), any());
  }

  @Test
  void queuedVideoStageTransportsAcceptedVisualReferenceBindingToProviderPayload() {
    job.setJobType(RenderJob.JobType.VIDEO);
    prepareValidVideoAdmission();
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);
    when(openArtAdapter.generateVideo(any())).thenReturn(OpenArtJobResponse.builder().jobId("provider-video-1").status("QUEUED").build());

    orchestrator.processAttempt(attempt.getId(), LEASE_OWNER);

    ArgumentCaptor<OpenArtVideoRequest> request = ArgumentCaptor.forClass(OpenArtVideoRequest.class);
    verify(openArtAdapter).generateVideo(request.capture());
    assertThat(request.getValue().getFirstFrameImageId()).isEqualTo("/data/content/1/visual-references/frame.png");
    assertThat(request.getValue().getDurationSeconds()).isEqualTo(8);
    verify(submissionStateService).markSubmitted(attempt.getId(), job.getId(), "provider-video-1", null, RenderProviderOperation.VIDEO);
    verify(validationEvidencePolicy).validate(any(), any(), any());
    verify(workflowAdmission).validate(any());
    verify(productionLifecycleGuard).assertEligible(eq(1L), eq(1L), eq("a".repeat(64)), any());
  }

  @Test
  void missingValidationRecordBlocksVideoBeforeProviderDispatch() {
    job.setJobType(RenderJob.JobType.VIDEO);
    job.setOpenartParams("{\"firstFrameImageId\":\"/frame.png\",\"visualReferencePlanId\":\"" + UUID.randomUUID() + "\"}");
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .hasMessageContaining("admission services are unavailable");

    verify(openArtAdapter, never()).generateVideo(any());
    verify(submissionStateService, never()).markSubmitting(any(), anyString());
    verify(submissionStateService).markAdmissionRejected(eq(attempt.getId()), eq(job.getId()), eq(LEASE_OWNER), eq("RENDER_ADMISSION_UNAVAILABLE"), any());
  }

  @Test
  void failedCurrentEvidenceBlocksVideoBeforeProviderDispatch() {
    job.setJobType(RenderJob.JobType.VIDEO);
    prepareValidVideoAdmission();
    doThrow(new ValidationEvidenceRejectedException("EVIDENCE_HAS_BLOCKERS", "failed evidence"))
        .when(validationEvidencePolicy).validate(any(), any(), any());
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(ValidationEvidenceRejectedException.class);

    verify(openArtAdapter, never()).generateVideo(any());
    verify(submissionStateService, never()).markSubmitting(any(), anyString());
    verify(submissionStateService).markAdmissionRejected(eq(attempt.getId()), eq(job.getId()), eq(LEASE_OWNER), eq("EVIDENCE_HAS_BLOCKERS"), any());
  }

  @Test
  void stalePromptSnapshotBlocksVideoBeforeProviderDispatch() {
    job.setJobType(RenderJob.JobType.VIDEO);
    prepareValidVideoAdmission();
    when(contentClient.fetch(1L, 1L)).thenReturn(new ContentPromptSnapshot(
        "v1", 1L, "Test Episode", "SHORT", "RENDER_READY", 1L, 1,
        "stale prompt", null, "b".repeat(64)));
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .hasMessageContaining("no longer matches");

    verify(openArtAdapter, never()).generateVideo(any());
    verify(submissionStateService, never()).markSubmitting(any(), anyString());
  }

  @Test
  void staleFirstFrameBindingBlocksVideoBeforeProviderDispatch() {
    job.setJobType(RenderJob.JobType.VIDEO);
    prepareValidVideoAdmission();
    doThrow(new IllegalStateException("stale frame"))
        .when(visualReferencePlanning).validateForRender(any(), any(), any(), any(), any(), any(), any());
    RenderAttempt attempt = attempt(RenderExecutionStage.QUEUED);

    assertThatThrownBy(() -> orchestrator.processAttempt(attempt.getId(), LEASE_OWNER))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .hasMessageContaining("first-frame plan or asset");

    verify(openArtAdapter, never()).generateVideo(any());
    verify(submissionStateService, never()).markSubmitting(any(), anyString());
  }

  private void prepareValidVideoAdmission() {
    String framePath = "/data/content/1/visual-references/frame.png";
    String frameSha = "f".repeat(64);
    UUID planId = UUID.randomUUID();
    job = RenderJob.builder().id(job.getId()).contentId(1L).promptVersionId(1L)
        .contentTitleSnapshot("Test Episode").promptVersionNumberSnapshot(1)
        .promptSha256("a".repeat(64)).promptTextSnapshot("a".repeat(120))
        .validationRecordId(99L).jobType(RenderJob.JobType.VIDEO).openartModel("mock_model")
        .creativeContractSnapshot("{\"intent\":{\"characterIntent\":{}}}")
        .status(RenderJob.RenderJobStatus.QUEUED).attemptNumber(1).maxAttempts(3).build();
    job.setOpenartParams("{\"firstFrameImageId\":\"" + framePath + "\",\"visualReferencePlanId\":\"" + planId
        + "\",\"durationSeconds\":8,\"aspectRatio\":\"9:16\",\"workflowProfile\":\"post-family-v1\",\"workflowReviewId\":\"" + UUID.randomUUID()
        + "\",\"workflowBindingHash\":\"" + "c".repeat(64) + "\"}");
    Map<String, Object> first = Map.of("status", "PASS", "evidenceSetId", "set-1", "assetId", "frame-1", "assetSha256", frameSha);
    Map<String, Object> silhouette = Map.of("status", "PASS", "evidenceSetId", "set-1", "assetId", "frame-1", "assetSha256", frameSha);
    ValidationEvidenceDto evidence = new ValidationEvidenceDto(99L, 1L, 1L, "a".repeat(64), "RENDER_READY", 0, 0, 0,
        "1.12", "local", "fixture", "v1", UUID.randomUUID(), Instant.now(), Instant.now(), Instant.now().plusSeconds(3600),
        false, true, Map.of("firstFrame", first, "silhouette", silhouette), "AUTHORIZED");
    lenient().when(evidenceClient.getEvidence(99L)).thenReturn(evidence);
    lenient().when(contentClient.fetch(1L, 1L)).thenReturn(new ContentPromptSnapshot(
        "v1", 1L, "Test Episode", "SHORT", "RENDER_READY", 1L, 1,
        "a".repeat(120), null, "a".repeat(64)));
    when(renderJobRepo.findById(job.getId())).thenReturn(Optional.of(job));
  }

  private void prepareValidFirstFrameAdmission() {
    job = RenderJob.builder().id(job.getId()).contentId(1L).promptVersionId(1L)
        .contentTitleSnapshot("Test Episode").promptVersionNumberSnapshot(1)
        .promptSha256("a".repeat(64)).promptTextSnapshot("a".repeat(120))
        .validationRecordId(98L).jobType(RenderJob.JobType.FIRST_FRAME).openartModel("mock_model")
        .creativeContractSnapshot("{\"intent\":{\"characterIntent\":{}}}")
        .status(RenderJob.RenderJobStatus.QUEUED).attemptNumber(1).maxAttempts(3).build();
    job.setOpenartParams("{\"paidCallAuthorization\":true,\"maxCostUsd\":10}");
    ValidationEvidenceDto evidence = new ValidationEvidenceDto(98L, 1L, 1L, "a".repeat(64),
        "PROMPT_READY", 0, 0, 0, "1.12", "local", "fixture", "v1",
        null, null, Instant.now(), Instant.now().plusSeconds(3600), true, false, Map.of(), null);
    lenient().when(evidenceClient.getEvidence(98L)).thenReturn(evidence);
    lenient().when(contentClient.fetch(1L, 1L)).thenReturn(new ContentPromptSnapshot(
        "v1", 1L, "Test Episode", "SHORT", "DRAFT", 1L, 1,
        "a".repeat(120), null, "a".repeat(64)));
    when(renderJobRepo.findById(job.getId())).thenReturn(Optional.of(job));
  }

  @Test
  void uncertainProviderSubmissionIsNotRetriedAutomatically() {
    prepareValidFirstFrameAdmission();
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
    when(assetLibraryManager.recordAsset(any(), any(), any()))
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
