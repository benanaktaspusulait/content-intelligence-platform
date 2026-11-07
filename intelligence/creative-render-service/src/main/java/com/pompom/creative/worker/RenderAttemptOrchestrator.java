package com.pompom.creative.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.ProviderJobState;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.domain.RenderProviderOperation;
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.OpenArtReferenceResolver;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtImageRequest;
import com.pompom.creative.openart.dto.OpenArtJobResponse;
import com.pompom.creative.openart.dto.OpenArtJobStatus;
import com.pompom.creative.openart.dto.OpenArtVideoRequest;
import com.pompom.creative.postrender.PostRenderEvaluationService;
import com.pompom.creative.qa.QaAnalysisResult;
import com.pompom.creative.qa.QaDecisionEngine;
import com.pompom.creative.qa.QaService;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.AssetLibraryManager;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.service.VideoUpscaleService;
import com.pompom.creative.queue.QueueRenderJobRequest;
import com.pompom.creative.queue.ValidationEvidencePolicy;
import com.pompom.creative.queue.ValidationEvidenceRejectedException;
import com.pompom.creative.queue.ProductionLifecycleGuard;
import com.pompom.creative.visual.VisualReferencePlanningService;
import com.pompom.creative.workflow.PostFamilyAdmissionClient;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import com.pompom.creative.websocket.dto.RenderProgressEvent;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Executes exactly one {@link RenderExecutionStage} of one {@link RenderAttempt} per call.
 *
 * <p>This replaces the previous {@code RenderJobOrchestrator.executeRenderJob} - a single long
 * transaction that ran every stage of a render to completion in one call, with a recursive
 * self-call on rerender. That design meant a worker crash mid-render lost all progress and had no
 * well-defined resumption point, and a long rerender chain grew the call stack without bound.
 *
 * <p>Here, a worker claims an attempt (see {@code RenderAttemptClaimRepository}), acquiring its
 * lease, then calls {@link #processAttempt}. Each call: validates the caller still holds the lease,
 * executes exactly the attempt's current stage, persists the next stage, and releases or renews the
 * lease - never more than one stage transition. A worker that dies between calls leaves a resumable
 * attempt row behind; the next poller simply reclaims it once its lease expires. Rerender inserts a
 * new attempt row (attempt_number + 1) instead of recursing.
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class RenderAttemptOrchestrator {

  /** How long to wait before polling the provider again while PROVIDER_QUEUED. */
  private static final Duration POLL_BACKOFF = Duration.ofSeconds(10);

  private final RenderJobRepository renderJobRepo;
  private final RenderAttemptRepository renderAttemptRepo;
  private final RenderAssetRepository renderAssetRepo;
  private final OpenArtAdapter openArtAdapter;
  private final AssetLibraryManager assetLibraryManager;
  private final QaService qaService;
  private final PostRenderEvaluationService postRenderEvaluationService;
  private final WebSocketEventPublisher webSocketPublisher;
  private final RenderSubmissionStateService submissionStateService;
  private final CreditTrackingService creditTrackingService;
  private final VideoUpscaleService videoUpscaleService;
  private final OpenArtReferenceResolver referenceResolver;
  private final ObjectMapper objectMapper;

  // The worker repeats the queue's existing admission checks immediately before dispatch.
  // These are optional only for constructor compatibility; a missing dependency blocks video.
  @Autowired(required = false) private IntelligenceValidationEvidenceClient evidenceClient;
  @Autowired(required = false) private IntelligenceContentClient contentClient;
  @Autowired(required = false) private ValidationEvidencePolicy validationEvidencePolicy;
  @Autowired(required = false) private PostFamilyAdmissionClient workflowAdmission;
  @Autowired(required = false) private ProductionLifecycleGuard productionLifecycleGuard;
  @Autowired(required = false) private VisualReferencePlanningService visualReferencePlanning;

  @Value("${pompom.openart.max-polls:180}")
  private int maxProviderPolls;

  /**
   * Process exactly one stage of the given attempt.
   *
   * @param attemptId the attempt to process
   * @param leaseOwner the identity the caller believes holds the attempt's lease; must match the
   *     attempt's current {@code leaseOwner} or {@link LeaseNotOwnedException} is thrown and
   *     nothing else happens
   */
  @Transactional
  public void processAttempt(UUID attemptId, String leaseOwner) {
    RenderAttempt attempt =
        renderAttemptRepo
            .findById(attemptId)
            .orElseThrow(
                () -> new IllegalArgumentException("RenderAttempt not found: " + attemptId));

    if (!leaseOwner.equals(attempt.getLeaseOwner())) {
      throw new LeaseNotOwnedException(attemptId, leaseOwner, attempt.getLeaseOwner());
    }

    if (attempt.getStage() == RenderExecutionStage.QUEUED) {
      submit(attemptId, leaseOwner);
      return;
    }

    RenderJob job =
        renderJobRepo
            .findById(attempt.getRenderJobId())
            .orElseThrow(
                () ->
                    new IllegalArgumentException(
                        "RenderJob not found: " + attempt.getRenderJobId()));

    log.info(
        "Processing attempt {} (job={}, stage={}, leaseOwner={})",
        attemptId,
        job.getId(),
        attempt.getStage(),
        leaseOwner);

    switch (attempt.getStage()) {
      case PROVIDER_QUEUED -> poll(attempt, job);
      case DOWNLOADING -> download(attempt, job);
      case POST_RENDER_QA -> evaluateQa(attempt, job);
      default ->
          throw new IllegalStateException(
              "Attempt " + attemptId + " is not in a processable stage: " + attempt.getStage());
    }
  }

  /**
   * Persist a submission intent in its own transaction before invoking the external provider. An
   * uncertain outcome is terminal for automatic processing; retrying it blindly could spend a
   * second provider generation.
   */
  private void submit(UUID attemptId, String leaseOwner) {
    RenderAttempt queuedAttempt = renderAttemptRepo.findById(attemptId)
        .orElseThrow(() -> new IllegalArgumentException("RenderAttempt not found: " + attemptId));
    RenderJob queuedJob = renderJobRepo.findById(queuedAttempt.getRenderJobId())
        .orElseThrow(() -> new IllegalArgumentException("RenderJob not found: " + queuedAttempt.getRenderJobId()));
    try {
      if (queuedJob.getJobType() == RenderJob.JobType.VIDEO) {
        revalidateVideoAdmission(queuedJob);
      } else {
        revalidateFirstFrameAdmission(queuedJob);
      }
    } catch (RuntimeException rejected) {
      submissionStateService.markAdmissionRejected(
          attemptId, queuedJob.getId(), leaseOwner,
          rejected instanceof ValidationEvidenceRejectedException evidenceRejected
              ? evidenceRejected.getErrorCode() : "RENDER_ADMISSION_REJECTED",
          rejected.getMessage());
      throw rejected;
    }
    RenderJob job = submissionStateService.markSubmitting(attemptId, leaseOwner);
    RenderAttempt attempt =
        renderAttemptRepo
            .findById(attemptId)
            .orElseThrow(
                () -> new IllegalArgumentException("RenderAttempt not found: " + attemptId));
    RenderProviderOperation operation;
    OpenArtJobResponse response;
    try {
      operation = chooseProviderOperation(job, attempt);
      response =
          operation == RenderProviderOperation.FIRST_FRAME
              ? submitFirstFrame(job)
              : submitVideo(job, attempt);
      if (response == null || response.getJobId() == null || response.getJobId().isBlank()) {
        throw new IllegalStateException("OpenArt returned an empty history id");
      }
    } catch (Exception error) {
      submissionStateService.markUncertain(attemptId, job.getId(), error);
      if (error instanceof RuntimeException runtimeException) {
        throw runtimeException;
      }
      throw new IllegalStateException("OpenArt submission failed", error);
    }

    submissionStateService.markSubmitted(
        attemptId, job.getId(), response.getJobId(), response.getEstimatedCredits(), operation);
    RenderJob submittedJob = renderJobRepo.findById(job.getId()).orElse(job);
    publishProgress(submittedJob, "Submitted to provider", 10);
  }

  private void revalidateFirstFrameAdmission(RenderJob job) {
    if (job.getValidationRecordId() == null || evidenceClient == null || contentClient == null
        || validationEvidencePolicy == null || productionLifecycleGuard == null) {
      throw new ValidationEvidenceRejectedException(
          "RENDER_ADMISSION_UNAVAILABLE", "Current first-frame validation admission is unavailable; provider dispatch is blocked");
    }
    if (job.getPromptSha256() == null || !job.getPromptSha256().matches("[0-9a-f]{64}")) {
      throw new ValidationEvidenceRejectedException(
          "PROMPT_BINDING_INVALID", "Queued prompt hash is missing or invalid");
    }
    Map<String, Object> params = objectMapper.convertValue(
        providerParameters(job), new com.fasterxml.jackson.core.type.TypeReference<>() {});
    QueueRenderJobRequest request = new QueueRenderJobRequest(
        job.getContentId(), job.getPromptVersionId(), job.getValidationRecordId(),
        job.getJobType(), job.getOpenartModel(), params, job.getPromptSha256());
    ValidationEvidenceDto evidence = evidenceClient.getEvidence(job.getValidationRecordId());
    if (evidence == null || evidence.validationRecordId() != job.getValidationRecordId()) {
      throw new ValidationEvidenceRejectedException(
          "VALIDATION_EVIDENCE_MISMATCH", "Current first-frame evidence is missing or belongs to another record");
    }
    validationEvidencePolicy.validate(request, evidence, Instant.now());
    ContentPromptSnapshot current = contentClient.fetch(job.getContentId(), job.getPromptVersionId());
    if (current.contentId() != job.getContentId()
        || current.promptVersionId() != job.getPromptVersionId()
        || !job.getPromptSha256().equals(current.promptSha256())
        || !job.getPromptSha256().equals(evidence.promptSha256())
        || current.promptText() == null || current.promptText().isBlank()) {
      throw new ValidationEvidenceRejectedException(
          "PROMPT_SNAPSHOT_STALE", "Current first-frame prompt no longer matches the queued validation binding");
    }
    productionLifecycleGuard.assertEligible(
        job.getContentId(), job.getPromptVersionId(), job.getPromptSha256(), params);
  }

  private void revalidateVideoAdmission(RenderJob job) {
    if (job.getValidationRecordId() == null || evidenceClient == null
        || contentClient == null || validationEvidencePolicy == null
        || workflowAdmission == null || productionLifecycleGuard == null
        || visualReferencePlanning == null) {
      throw new ValidationEvidenceRejectedException(
          "RENDER_ADMISSION_UNAVAILABLE", "Current validation admission services are unavailable; provider dispatch is blocked");
    }
    if (job.getPromptSha256() == null || !job.getPromptSha256().matches("[0-9a-f]{64}")) {
      throw new ValidationEvidenceRejectedException(
          "PROMPT_BINDING_INVALID", "Queued prompt hash is missing or invalid");
    }
    Map<String, Object> params = objectMapper.convertValue(
        providerParameters(job), new com.fasterxml.jackson.core.type.TypeReference<>() {});
    QueueRenderJobRequest request = new QueueRenderJobRequest(
        job.getContentId(), job.getPromptVersionId(), job.getValidationRecordId(),
        job.getJobType(), job.getOpenartModel(), params, job.getPromptSha256());
    ValidationEvidenceDto evidence = evidenceClient.getEvidence(job.getValidationRecordId());
    if (evidence == null || evidence.validationRecordId() != job.getValidationRecordId()) {
      throw new ValidationEvidenceRejectedException(
          "VALIDATION_EVIDENCE_MISMATCH", "Current validation evidence is missing or belongs to another record");
    }
    validationEvidencePolicy.validate(request, evidence, Instant.now());
    workflowAdmission.validate(request);
    ContentPromptSnapshot current = contentClient.fetch(job.getContentId(), job.getPromptVersionId());
    if (current.contentId() != job.getContentId()
        || current.promptVersionId() != job.getPromptVersionId()
        || !job.getPromptSha256().equals(current.promptSha256())
        || !job.getPromptSha256().equals(evidence.promptSha256())
        || !"RENDER_READY".equals(current.contentStatus())
        || current.promptText() == null || current.promptText().isBlank()) {
      throw new ValidationEvidenceRejectedException(
          "PROMPT_SNAPSHOT_STALE", "Current canonical prompt/content no longer matches the queued validation binding");
    }
    productionLifecycleGuard.assertEligible(
        job.getContentId(), job.getPromptVersionId(), job.getPromptSha256(), params);
    Object rawPlanId = params.get("visualReferencePlanId");
    Object rawFrame = params.get("firstFrameImageId");
    if (rawPlanId == null || rawFrame == null || String.valueOf(rawFrame).isBlank()) {
      throw new ValidationEvidenceRejectedException(
          "FIRST_FRAME_REVIEW_REQUIRED", "A reviewed first-frame asset is required immediately before video dispatch");
    }
    String expectedFrameSha = "";
    Object frame = evidence.visualEvidence() == null ? null : evidence.visualEvidence().get("firstFrame");
    if (frame instanceof Map<?, ?> frameMap && frameMap.get("assetSha256") != null) {
      expectedFrameSha = String.valueOf(frameMap.get("assetSha256"));
    }
    if (!expectedFrameSha.matches("[0-9a-f]{64}")) {
      throw new ValidationEvidenceRejectedException(
          "FIRST_FRAME_REVIEW_REQUIRED", "Current validation evidence has no verified first-frame hash");
    }
    try {
      visualReferencePlanning.validateForRender(
          UUID.fromString(String.valueOf(rawPlanId)), job.getContentId(), job.getPromptVersionId(),
          String.valueOf(rawFrame), job.getOpenartModel(), params, expectedFrameSha);
    } catch (RuntimeException invalidFrame) {
      throw new ValidationEvidenceRejectedException(
          "FIRST_FRAME_BINDING_STALE", "Current first-frame plan or asset no longer matches validation evidence");
    }
  }

  private RenderProviderOperation chooseProviderOperation(RenderJob job, RenderAttempt attempt) {
    if (job.getJobType() == RenderJob.JobType.FIRST_FRAME) {
      return RenderProviderOperation.FIRST_FRAME;
    }
    JsonNode parameters = providerParameters(job);
    if (textOrNull(parameters, "firstFrameImageId") != null
        || attempt.getFirstFrameAssetId() != null) {
      return RenderProviderOperation.VIDEO;
    }
    return referenceResolver.resolveCharacterReferences(job.getCreativeContractSnapshot()).isEmpty()
        ? RenderProviderOperation.VIDEO
        : RenderProviderOperation.FIRST_FRAME;
  }

  private OpenArtJobResponse submitFirstFrame(RenderJob job) {
    OpenArtImageRequest request =
        OpenArtImageRequest.builder()
            .promptText(
                job.getGenerationPromptSnapshot() == null
                    ? job.getPromptTextSnapshot()
                    : job.getGenerationPromptSnapshot())
            .model(job.getOpenartModel())
            .referenceImagePaths(
                referenceResolver.resolveCharacterReferences(job.getCreativeContractSnapshot()))
            .build();
    return openArtAdapter.generateImage(request);
  }

  private OpenArtJobResponse submitVideo(RenderJob job, RenderAttempt attempt) {
    JsonNode parameters = providerParameters(job);
    String firstFrameImageId = textOrNull(parameters, "firstFrameImageId");
    if (firstFrameImageId == null && attempt.getFirstFrameAssetId() != null) {
      RenderAsset firstFrame =
          renderAssetRepo
              .findById(attempt.getFirstFrameAssetId())
              .orElseThrow(
                  () ->
                      new IllegalStateException(
                          "First-frame asset not found: " + attempt.getFirstFrameAssetId()));
      firstFrameImageId = assetLibraryManager.resolveStoredPath(firstFrame).toString();
    }
    OpenArtVideoRequest request =
        OpenArtVideoRequest.builder()
            .promptText(
                job.getGenerationPromptSnapshot() == null
                    ? job.getPromptTextSnapshot()
                    : job.getGenerationPromptSnapshot())
            .model(job.getOpenartModel())
            .firstFrameImageId(firstFrameImageId)
            .durationSeconds(parameters.path("durationSeconds").asInt(15))
            .aspectRatio(parameters.path("aspectRatio").asText("16:9"))
            .resolution("480p")
            .build();
    return openArtAdapter.generateVideo(request);
  }

  private JsonNode providerParameters(RenderJob job) {
    try {
      return job.getOpenartParams() == null
          ? objectMapper.createObjectNode()
          : objectMapper.readTree(job.getOpenartParams());
    } catch (Exception error) {
      throw new IllegalStateException("Persisted provider parameters are invalid", error);
    }
  }

  private String textOrNull(JsonNode parameters, String field) {
    JsonNode value = parameters.get(field);
    return value == null || value.isNull() || value.asText().isBlank() ? null : value.asText();
  }

  /**
   * PROVIDER_QUEUED: poll the provider once. Only an explicit SUCCEEDED/COMPLETE status advances to
   * DOWNLOADING; FAILED moves to FAILED with the provider's error; anything else (including
   * unrecognized/UNKNOWN statuses) stays PROVIDER_QUEUED and schedules another poll. An attempt
   * must never be treated as complete on an ambiguous or unknown provider response.
   */
  private void poll(RenderAttempt attempt, RenderJob job) {
    OpenArtJobStatus status = openArtAdapter.getJobStatus(attempt.getProviderJobId());
    if (status == null) {
      status = OpenArtJobStatus.builder().status("UNKNOWN").progressPercent(0).build();
    }
    ProviderJobState state = mapProviderState(status);
    int pollCount = attempt.getPollCount() == null ? 1 : attempt.getPollCount() + 1;
    attempt.setProviderJobState(state);
    attempt.setPollCount(pollCount);

    if (state == ProviderJobState.SUCCEEDED) {
      attempt.setStage(RenderExecutionStage.DOWNLOADING);
      job.setStatus(RenderJob.RenderJobStatus.DOWNLOADING);
      java.math.BigDecimal credits = status.getCreditsUsed();
      if (credits == null) {
        credits = job.getCreditsEstimated();
      }
      if (credits != null && credits.signum() >= 0) {
        creditTrackingService.recordProviderUsageIfAbsent(
            job,
            credits,
            status.getCreditsUsed() == null ? "estimate-fallback" : "provider-status");
      }
    } else if (state == ProviderJobState.FAILED || state == ProviderJobState.CANCELLED) {
      settleProviderFailure(job, status, state);
      failProviderAttempt(attempt, job, state, status.getErrorMessage());
    } else if (maxProviderPolls > 0 && pollCount >= maxProviderPolls) {
      failProviderAttempt(
          attempt,
          job,
          ProviderJobState.FAILED,
          "Provider did not finish within " + maxProviderPolls + " polls");
      attempt.setErrorCode("PROVIDER_TIMEOUT");
      job.setErrorCode("PROVIDER_TIMEOUT");
    } else {
      // RUNNING, QUEUED, or UNKNOWN: stay PROVIDER_QUEUED and poll again later.
      attempt.setNextPollAt(Instant.now().plus(POLL_BACKOFF));
      job.setStatus(RenderJob.RenderJobStatus.POLLING);
    }

    releaseLease(attempt);
    renderAttemptRepo.save(attempt);
    renderJobRepo.save(job);
    publishProgress(job, "Polling provider", status == null ? null : status.getProgressPercent());
  }

  private void settleProviderFailure(
      RenderJob job, OpenArtJobStatus status, ProviderJobState state) {
    if (status.getCreditsUsed() != null && job.getOpenartJobId() != null) {
      creditTrackingService.recordProviderUsageIfAbsent(
          job, status.getCreditsUsed(), "provider-" + state.name().toLowerCase());
    } else {
      creditTrackingService.releaseEstimateIfPresent(job, "provider-" + state.name().toLowerCase());
    }
  }

  private void failProviderAttempt(
      RenderAttempt attempt, RenderJob job, ProviderJobState state, String providerMessage) {
    String message =
        providerMessage == null || providerMessage.isBlank()
            ? "OpenArt provider reported " + state
            : providerMessage;
    attempt.setStage(RenderExecutionStage.FAILED);
    attempt.setErrorCode("PROVIDER_" + state.name());
    attempt.setErrorMessage(message);
    attempt.setCompletedAt(Instant.now());
    job.setStatus(RenderJob.RenderJobStatus.FAILED);
    job.setFailedAt(Instant.now());
    job.setErrorCode("PROVIDER_" + state.name());
    job.setErrorMessage(message);
  }

  private ProviderJobState mapProviderState(OpenArtJobStatus status) {
    if (status == null) {
      return ProviderJobState.UNKNOWN;
    }
    if (status.isFailed()) {
      return "CANCELLED".equalsIgnoreCase(status.getStatus())
          ? ProviderJobState.CANCELLED
          : ProviderJobState.FAILED;
    }
    if (status.isComplete()) {
      return ProviderJobState.SUCCEEDED;
    }
    String raw = status.getStatus();
    if (raw == null) {
      return ProviderJobState.UNKNOWN;
    }
    return switch (raw.trim().toUpperCase(java.util.Locale.ROOT).replace('-', '_')) {
      case "QUEUED", "PENDING", "CREATED", "SUBMITTED" -> ProviderJobState.QUEUED;
      case "RUNNING", "PROCESSING", "IN_PROGRESS", "GENERATING" -> ProviderJobState.RUNNING;
      case "CANCELLED", "CANCELED" -> ProviderJobState.CANCELLED;
      default -> ProviderJobState.UNKNOWN;
    };
  }

  /** DOWNLOADING: download the finished asset and record it, then move to POST_RENDER_QA. */
  private void download(RenderAttempt attempt, RenderJob job) {
    RenderProviderOperation operation =
        attempt.getProviderOperation() == null
            ? (job.getJobType() == RenderJob.JobType.FIRST_FRAME
                ? RenderProviderOperation.FIRST_FRAME
                : RenderProviderOperation.VIDEO)
            : attempt.getProviderOperation();
    RenderAsset.AssetType assetType =
        operation == RenderProviderOperation.FIRST_FRAME
            ? RenderAsset.AssetType.FIRST_FRAME
            : RenderAsset.AssetType.VIDEO;

    int version = assetLibraryManager.getNextVersion(job.getContentId(), assetType);
    Path assetPath = assetLibraryManager.getAssetPath(job.getContentId(), assetType, version);

    DownloadResult downloadResult =
        openArtAdapter.downloadAsset(attempt.getProviderJobId(), assetPath);
    if (operation == RenderProviderOperation.VIDEO
        && (job.getOpenartJobId() == null || !job.getOpenartJobId().startsWith("mock-"))) {
      VideoUpscaleService.UpscaleResult upscale = videoUpscaleService.upscale(assetPath);
      if (upscale.originalPath() != null) {
        downloadResult.setOriginalAssetPath(upscale.originalPath().toString());
      }
    }
    RenderAsset asset = assetLibraryManager.recordAsset(job, attempt, downloadResult);
    try {
      asset.setCharacterRefsJson(
          objectMapper.writeValueAsString(
              referenceResolver.resolveCharacterReferences(job.getCreativeContractSnapshot())));
      renderAssetRepo.save(asset);
    } catch (Exception error) {
      throw new IllegalStateException("Unable to persist character reference lineage", error);
    }

    if (operation == RenderProviderOperation.FIRST_FRAME
        && job.getJobType() == RenderJob.JobType.VIDEO) {
      attempt.setFirstFrameAssetId(asset.getId());
      attempt.setAssetId(null);
      attempt.setStage(RenderExecutionStage.QUEUED);
      job.setStatus(RenderJob.RenderJobStatus.QUEUED);
      releaseLease(attempt);
      renderAttemptRepo.save(attempt);
      renderJobRepo.save(job);
      publishProgress(job, "First frame ready; queuing video", 45);
      return;
    }

    attempt.setAssetId(asset.getId());
    attempt.setStage(RenderExecutionStage.POST_RENDER_QA);
    job.setStatus(RenderJob.RenderJobStatus.DOWNLOADING);
    releaseLease(attempt);

    renderAttemptRepo.save(attempt);
    renderJobRepo.save(job);
    publishProgress(job, "Downloaded asset", 70);
  }

  /**
   * POST_RENDER_QA: run QA against the asset recorded by the DOWNLOADING stage and act on the
   * decision - ACCEPT completes the attempt and job; RERENDER inserts a new attempt (attempt_number
   * + 1) instead of recursing back into stage execution; ABANDON marks both the attempt and job
   * terminal.
   */
  private void evaluateQa(RenderAttempt attempt, RenderJob job) {
    if (attempt.getAssetId() == null) {
      throw new IllegalStateException(
          "Attempt " + attempt.getId() + " reached POST_RENDER_QA with no assetId recorded");
    }

    RenderAsset asset =
        renderAssetRepo
            .findById(attempt.getAssetId())
            .orElseThrow(
                () ->
                    new IllegalStateException(
                        "RenderAsset not found for attempt " + attempt.getId()));

    QaAnalysisResult qaResult = null;
    String qaStatus = "NOT_EVALUATED";
    try {
      // Video QC below performs local inspection; legacy character QA can make paid calls.
      // It must not be invoked automatically merely because rendering completed.
      if (asset.getAssetType() != RenderAsset.AssetType.VIDEO) {
        qaResult = qaService.analyzeAsset(asset);
        qaStatus = "AVAILABLE";
      }
    } catch (QaService.QaDependencyUnavailableException error) {
      qaStatus = "SERVICE_ERROR";
      log.warn(
          "QA helper evidence unavailable for asset {}: {}", asset.getId(), error.getMessage());
    }
    var evaluation =
        postRenderEvaluationService.evaluate(asset, attempt.getId(), qaResult, qaStatus);
    String reason =
        "Post-render "
            + evaluation.evaluation().getOverallDecision()
            + " under "
            + evaluation.evaluation().getPostRenderRulesetVersion();
    switch (evaluation.evaluation().getOverallDecision()) {
      case PASS ->
          accept(
              attempt,
              job,
              new QaDecisionEngine.QaDecision(
                  com.pompom.creative.domain.RenderQaResult.QaDecision.ACCEPT, reason, false));
      case HUMAN_REVIEW -> {
        attempt.setStage(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
        attempt.setTerminalReason(reason);
        attempt.setCompletedAt(Instant.now());
        renderAttemptRepo.save(attempt);
        job.setStatus(RenderJob.RenderJobStatus.COMPLETE);
        job.setCompletedAt(Instant.now());
        renderJobRepo.save(job);
        publishProgress(job, "Human review required", 100);
      }
      case FAIL, SYSTEM_ERROR ->
          abandon(
              attempt,
              job,
              new QaDecisionEngine.QaDecision(
                  com.pompom.creative.domain.RenderQaResult.QaDecision.ABANDON, reason, false));
    }
  }

  private void accept(RenderAttempt attempt, RenderJob job, QaDecisionEngine.QaDecision decision) {
    attempt.setStage(RenderExecutionStage.COMPLETE);
    attempt.setCompletedAt(Instant.now());
    renderAttemptRepo.save(attempt);

    job.setStatus(RenderJob.RenderJobStatus.COMPLETE);
    job.setCompletedAt(Instant.now());
    renderJobRepo.save(job);

    log.info("Attempt {} accepted: {}", attempt.getId(), decision.reason());
    publishProgress(job, "Accepted", 100);
  }

  private void rerender(
      RenderAttempt attempt, RenderJob job, QaDecisionEngine.QaDecision decision) {
    int attemptsSoFar =
        renderAttemptRepo.findByRenderJobIdOrderByAttemptNumberAsc(job.getId()).size();

    if (attemptsSoFar >= job.getMaxAttempts()) {
      log.warn(
          "Job {} max attempts reached ({}), abandoning instead of rerendering",
          job.getId(),
          job.getMaxAttempts());
      abandon(attempt, job, decision);
      return;
    }

    // RETRY_WAIT is a dead end for this specific row - the new attempt below drives the job
    // forward instead, and processAttempt has no case for RETRY_WAIT. The lease must still be
    // cleared (not just left to expire): JdbcRenderAttemptClaimRepository excludes RETRY_WAIT
    // from eligibility outright, so an un-cleared lease here would otherwise sit stale forever
    // with nothing to ever release it.
    attempt.setStage(RenderExecutionStage.RETRY_WAIT);
    attempt.setCompletedAt(Instant.now());
    releaseLease(attempt);
    renderAttemptRepo.save(attempt);

    RenderAttempt nextAttempt =
        RenderAttempt.builder()
            .renderJobId(job.getId())
            .attemptNumber(attempt.getAttemptNumber() + 1)
            .stage(RenderExecutionStage.QUEUED)
            .pollCount(0)
            .eligibleAt(Instant.now())
            .build();
    renderAttemptRepo.save(nextAttempt);
    job.setAttemptNumber(nextAttempt.getAttemptNumber());
    job.setStatus(RenderJob.RenderJobStatus.QUEUED);
    renderJobRepo.save(job);

    log.info(
        "Attempt {} rerendering as attempt {}: {}",
        attempt.getId(),
        nextAttempt.getAttemptNumber(),
        decision.reason());
    publishProgress(job, "Rerendering", 50);
  }

  private void abandon(RenderAttempt attempt, RenderJob job, QaDecisionEngine.QaDecision decision) {
    attempt.setStage(RenderExecutionStage.ABANDONED);
    attempt.setTerminalReason(decision.reason());
    attempt.setCompletedAt(Instant.now());
    renderAttemptRepo.save(attempt);

    job.setStatus(RenderJob.RenderJobStatus.ABANDONED);
    job.setFailedAt(Instant.now());
    job.setErrorCode("QA_FAILURE");
    job.setErrorMessage(decision.reason());
    renderJobRepo.save(job);

    log.warn("Attempt {} abandoned: {}", attempt.getId(), decision.reason());
    publishProgress(job, "Abandoned", null);
  }

  private void releaseLease(RenderAttempt attempt) {
    attempt.setLeaseOwner(null);
    attempt.setLeaseExpiresAt(null);
    attempt.setLeaseHeartbeatAt(null);
  }

  private void publishProgress(RenderJob job, String currentStep, Integer progressPercent) {
    try {
      RenderProgressEvent event =
          RenderProgressEvent.builder()
              .type(RenderProgressEvent.EventType.PROGRESS_UPDATE)
              .jobId(job.getId())
              .status(job.getStatus().name())
              .progressPercent(progressPercent)
              .currentStep(currentStep)
              .errorMessage(job.getErrorMessage())
              .build();
      webSocketPublisher.publishRenderProgress(event);
    } catch (Exception e) {
      log.warn("Failed to publish WebSocket event for job {}: {}", job.getId(), e.getMessage());
    }
  }
}
