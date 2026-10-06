package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.domain.RenderProviderOperation;
import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.OpenArtReferenceResolver;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtJobResponse;
import com.pompom.creative.postrender.PostRenderEvaluationService;
import com.pompom.creative.qa.QaService;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.AssetLibraryManager;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.service.VideoUpscaleService;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RenderAutomaticFirstFrameTest {

  private static final String OWNER = "worker-1";

  @Mock private RenderJobRepository renderJobRepo;
  @Mock private RenderAttemptRepository renderAttemptRepo;
  @Mock private RenderAssetRepository renderAssetRepo;
  @Mock private OpenArtAdapter openArtAdapter;
  @Mock private AssetLibraryManager assetLibraryManager;
  @Mock private QaService qaService;
  @Mock private PostRenderEvaluationService postRenderEvaluationService;
  @Mock private WebSocketEventPublisher webSocketPublisher;
  @Mock private RenderSubmissionStateService submissionStateService;
  @Mock private CreditTrackingService creditTrackingService;
  @Mock private VideoUpscaleService videoUpscaleService;
  @Mock private OpenArtReferenceResolver referenceResolver;

  private RenderAttemptOrchestrator orchestrator;
  private RenderJob job;
  private RenderAttempt attempt;

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
            webSocketPublisher,
            submissionStateService,
            creditTrackingService,
            videoUpscaleService,
            referenceResolver,
            new ObjectMapper());
    job =
        RenderJob.builder()
            .id(UUID.randomUUID())
            .contentId(1L)
            .promptVersionId(1L)
            .contentTitleSnapshot("Episode")
            .promptVersionNumberSnapshot(1)
            .promptSha256("a".repeat(64))
            .promptTextSnapshot("Kiko and Mimi")
            .generationPromptSnapshot("Kiko and Mimi")
            .creativeContractSnapshot("{\"intent\":{\"characterIntent\":{}}}")
            .jobType(RenderJob.JobType.VIDEO)
            .openartModel("byte-plus-seedance-2-mini")
            .status(RenderJob.RenderJobStatus.QUEUED)
            .maxAttempts(3)
            .build();
    attempt =
        RenderAttempt.builder()
            .id(UUID.randomUUID())
            .renderJobId(job.getId())
            .attemptNumber(1)
            .stage(RenderExecutionStage.QUEUED)
            .pollCount(0)
            .leaseOwner(OWNER)
            .build();
    when(renderAttemptRepo.findById(attempt.getId())).thenReturn(Optional.of(attempt));
    when(renderJobRepo.findById(job.getId())).thenReturn(Optional.of(job));
    lenient().when(submissionStateService.markSubmitting(attempt.getId(), OWNER)).thenReturn(job);
    lenient()
        .when(referenceResolver.resolveCharacterReferences(anyString()))
        .thenReturn(
            List.of(
                "/data/library/01-CHARACTERS/kiko.png", "/data/library/01-CHARACTERS/mimi.png"));
  }

  @Test
  void videoWithoutFirstFrameSubmitsCharacterReferencesAsFirstFrameGeneration() {
    when(openArtAdapter.generateImage(any()))
        .thenReturn(OpenArtJobResponse.builder().jobId("first-frame-history").build());

    orchestrator.processAttempt(attempt.getId(), OWNER);

    verify(openArtAdapter).generateImage(any());
    verify(submissionStateService)
        .markSubmitted(
            attempt.getId(),
            job.getId(),
            "first-frame-history",
            null,
            RenderProviderOperation.FIRST_FRAME);
  }

  @Test
  void completedFirstFrameQueuesVideoInsteadOfRunningQaOnTheIntermediateImage() {
    attempt.setStage(RenderExecutionStage.DOWNLOADING);
    attempt.setProviderJobId("first-frame-history");
    attempt.setProviderOperation(RenderProviderOperation.FIRST_FRAME);
    Path destination = Path.of("/data/content/1/first-frame-v1.png");
    RenderAsset firstFrame = RenderAsset.builder().id(UUID.randomUUID()).build();
    when(assetLibraryManager.getNextVersion(1L, RenderAsset.AssetType.FIRST_FRAME)).thenReturn(1);
    when(assetLibraryManager.getAssetPath(1L, RenderAsset.AssetType.FIRST_FRAME, 1))
        .thenReturn(destination);
    when(openArtAdapter.downloadAsset("first-frame-history", destination))
        .thenReturn(DownloadResult.builder().assetPath(destination.toString()).build());
    when(assetLibraryManager.recordAsset(eq(job), any(), any())).thenReturn(firstFrame);

    orchestrator.processAttempt(attempt.getId(), OWNER);

    ArgumentCaptor<RenderAttempt> saved = ArgumentCaptor.forClass(RenderAttempt.class);
    verify(renderAttemptRepo).save(saved.capture());
    assertThat(saved.getValue().getStage()).isEqualTo(RenderExecutionStage.QUEUED);
    assertThat(saved.getValue().getFirstFrameAssetId()).isEqualTo(firstFrame.getId());
    assertThat(saved.getValue().getProviderOperation())
        .isEqualTo(RenderProviderOperation.FIRST_FRAME);
  }
}
