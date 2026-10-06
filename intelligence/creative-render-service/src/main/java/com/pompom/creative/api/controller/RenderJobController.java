package com.pompom.creative.api.controller;

import com.pompom.creative.api.dto.RenderJobDto;
import com.pompom.creative.domain.ProviderJobState;
import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.ValidationEvidenceClientException;
import com.pompom.creative.evidence.ValidationEvidenceIncompleteRemoteException;
import com.pompom.creative.evidence.ValidationEvidenceNotFoundException;
import com.pompom.creative.evidence.ValidationEvidenceServiceException;
import com.pompom.creative.evidence.ValidationEvidenceTimeoutException;
import com.pompom.creative.postrender.PostRenderEvaluationRepository;
import com.pompom.creative.queue.IdempotencyKeyConflictException;
import com.pompom.creative.queue.QueueRenderJobRequest;
import com.pompom.creative.queue.QueueRenderJobResponse;
import com.pompom.creative.queue.RenderJobQueueService;
import com.pompom.creative.queue.ValidationEvidenceRejectedException;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.worker.RenderSubmissionStateService;
import java.net.URI;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

/** REST API controller for render jobs. */
@RestController
@RequestMapping("/api/v1/render-jobs")
@Slf4j
public class RenderJobController {

  private final RenderJobRepository renderJobRepo;
  private final RenderQaResultRepository qaResultRepo;
  private final RenderAttemptRepository renderAttemptRepo;
  private final RenderJobQueueService queueService;
  private final PostRenderEvaluationRepository postRenderEvaluationRepo;
  private final CreditTrackingService creditTrackingService;
  private final RenderSubmissionStateService submissionStateService;

  @Autowired
  public RenderJobController(
      RenderJobRepository renderJobRepo,
      RenderQaResultRepository qaResultRepo,
      RenderAttemptRepository renderAttemptRepo,
      RenderJobQueueService queueService,
      PostRenderEvaluationRepository postRenderEvaluationRepo,
      CreditTrackingService creditTrackingService,
      RenderSubmissionStateService submissionStateService) {
    this.renderJobRepo = renderJobRepo;
    this.qaResultRepo = qaResultRepo;
    this.renderAttemptRepo = renderAttemptRepo;
    this.queueService = queueService;
    this.postRenderEvaluationRepo = postRenderEvaluationRepo;
    this.creditTrackingService = creditTrackingService;
    this.submissionStateService = submissionStateService;
  }

  /** Compatibility constructor for queue-focused controller tests. */
  public RenderJobController(
      RenderJobRepository renderJobRepo,
      RenderQaResultRepository qaResultRepo,
      RenderJobQueueService queueService) {
    this(renderJobRepo, qaResultRepo, null, queueService, null, null, null);
  }

  /**
   * Queue a render job. Requires the {@code Idempotency-Key} header; the same key with the same
   * canonical payload replays the existing job (Idempotent-Replay: true), the same key with a
   * different payload is rejected with 409.
   */
  @PostMapping
  public ResponseEntity<QueueRenderJobResponse> queueRenderJob(
      @RequestHeader("Idempotency-Key") String idempotencyKey,
      @RequestBody QueueRenderJobRequest request) {
    log.info("POST /api/v1/render-jobs idempotencyKey={}", idempotencyKey);

    QueueRenderJobResponse response = queueService.queue(idempotencyKey, request);

    return ResponseEntity.accepted()
        .location(URI.create("/api/v1/render-jobs/" + response.renderJobId()))
        .header("Idempotent-Replay", String.valueOf(response.replay()))
        .body(response);
  }

  @ExceptionHandler(ValidationEvidenceRejectedException.class)
  ResponseEntity<ProblemDetail> rejected(ValidationEvidenceRejectedException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_ENTITY, error.getMessage());
    problem.setTitle("Validation evidence rejected");
    problem.setProperty("errorCode", error.getErrorCode());
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(problem);
  }

  @ExceptionHandler(IdempotencyKeyConflictException.class)
  ResponseEntity<ProblemDetail> conflict(IdempotencyKeyConflictException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, error.getMessage());
    problem.setTitle("Idempotency key conflict");
    return ResponseEntity.status(HttpStatus.CONFLICT).body(problem);
  }

  @ExceptionHandler({
    ValidationEvidenceNotFoundException.class,
    ValidationEvidenceIncompleteRemoteException.class
  })
  ResponseEntity<ProblemDetail> evidenceUnusable(ValidationEvidenceClientException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_ENTITY, error.getMessage());
    problem.setTitle("Validation evidence is not usable for render authorization");
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(problem);
  }

  @ExceptionHandler({
    ValidationEvidenceServiceException.class,
    ValidationEvidenceTimeoutException.class
  })
  ResponseEntity<ProblemDetail> evidenceServiceUnavailable(
      ValidationEvidenceClientException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, error.getMessage());
    problem.setTitle("Intelligence validation evidence service unavailable");
    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(problem);
  }

  /** Get all render jobs with pagination. */
  @GetMapping
  public ResponseEntity<Page<RenderJobDto>> getRenderJobs(
      @RequestParam(defaultValue = "0") int page,
      @RequestParam(defaultValue = "20") int size,
      @RequestParam(defaultValue = "createdAt") String sortBy,
      @RequestParam(defaultValue = "DESC") String sortDir) {
    log.info("GET /api/v1/render-jobs page={}, size={}", page, size);

    Sort.Direction direction =
        sortDir.equalsIgnoreCase("DESC") ? Sort.Direction.DESC : Sort.Direction.ASC;

    Pageable pageable = PageRequest.of(page, size, Sort.by(direction, sortBy));

    Page<RenderJob> jobsPage = renderJobRepo.findAll(pageable);

    Page<RenderJobDto> dtoPage = jobsPage.map(this::toDto);

    return ResponseEntity.ok(dtoPage);
  }

  /** Get render job by ID. */
  @GetMapping("/{id}")
  public ResponseEntity<RenderJobDto> getRenderJobById(@PathVariable UUID id) {
    log.info("GET /api/v1/render-jobs/{}", id);

    Optional<RenderJob> job = renderJobRepo.findById(id);

    if (job.isEmpty()) {
      return ResponseEntity.notFound().build();
    }

    RenderJobDto dto = toDto(job.get());

    return ResponseEntity.ok(dto);
  }

  /** Stop a queued or active job locally. A remote provider job is never misreported as deleted. */
  @PostMapping("/{id}/cancel")
  @Transactional
  public ResponseEntity<?> cancelRenderJob(@PathVariable UUID id) {
    Optional<RenderJob> found = renderJobRepo.findById(id);
    if (found.isEmpty()) return ResponseEntity.notFound().build();
    RenderJob job = found.get();
    if (job.getStatus() == RenderJob.RenderJobStatus.COMPLETE
        || job.getStatus() == RenderJob.RenderJobStatus.ABANDONED) {
      return ResponseEntity.badRequest()
          .body(java.util.Map.of("message", "Render job is already terminal"));
    }
    RenderAttempt attempt =
        renderAttemptRepo.findTopByRenderJobIdOrderByAttemptNumberDesc(id).orElse(null);
    boolean remoteSubmissionUncertain =
        attempt != null
            && (attempt.getStage() == RenderExecutionStage.SUBMITTING
                || attempt.getProviderJobId() != null);
    if (attempt != null && !attempt.isTerminal()) {
      attempt.setStage(RenderExecutionStage.ABANDONED);
      attempt.setTerminalReason("Cancelled by operator");
      attempt.setCompletedAt(Instant.now());
      attempt.setLeaseOwner(null);
      attempt.setLeaseExpiresAt(null);
      renderAttemptRepo.save(attempt);
    }
    job.setStatus(RenderJob.RenderJobStatus.ABANDONED);
    job.setFailedAt(Instant.now());
    job.setErrorCode("CANCELLED_BY_OPERATOR");
    job.setErrorMessage("Cancelled by operator; any remote provider job was not deleted");
    if (creditTrackingService != null && !remoteSubmissionUncertain) {
      creditTrackingService.releaseEstimateIfPresent(job, "operator-cancel");
    }
    renderJobRepo.save(job);
    return ResponseEntity.ok(
        java.util.Map.of("success", true, "message", "Render job cancelled locally"));
  }

  /**
   * Resolve an uncertain OpenArt submission without blindly creating a second provider job. Provide
   * {@code providerJobId} to attach an observed OpenArt history, or {@code action=ABANDON} to close
   * the local attempt while retaining its conservative credit reservation.
   */
  @PostMapping("/{id}/reconcile-submission")
  public ResponseEntity<?> reconcileSubmission(
      @PathVariable UUID id, @RequestBody java.util.Map<String, String> request) {
    if (submissionStateService == null) {
      return ResponseEntity.status(HttpStatus.NOT_IMPLEMENTED)
          .body(java.util.Map.of("message", "Submission reconciliation is not configured"));
    }
    RenderAttempt attempt =
        renderAttemptRepo == null
            ? null
            : renderAttemptRepo.findTopByRenderJobIdOrderByAttemptNumberDesc(id).orElse(null);
    if (attempt == null) {
      return ResponseEntity.notFound().build();
    }

    String providerJobId = request.get("providerJobId");
    if (providerJobId != null && !providerJobId.isBlank()) {
      submissionStateService.attachProviderJob(attempt.getId(), providerJobId);
      return ResponseEntity.ok(
          java.util.Map.of("success", true, "message", "Provider history attached"));
    }
    if ("ABANDON".equalsIgnoreCase(request.get("action"))) {
      submissionStateService.abandonUncertainSubmission(
          attempt.getId(), request.getOrDefault("reason", "Operator reconciliation abandoned"));
      return ResponseEntity.ok(
          java.util.Map.of("success", true, "message", "Uncertain submission abandoned"));
    }
    return ResponseEntity.badRequest()
        .body(
            java.util.Map.of(
                "message", "Provide providerJobId or action=ABANDON to reconcile the submission"));
  }

  /** Queue a new durable attempt for a failed job while preserving the previous attempt history. */
  @PostMapping("/{id}/retry")
  @Transactional
  public ResponseEntity<?> retryRenderJob(@PathVariable UUID id) {
    Optional<RenderJob> found = renderJobRepo.findById(id);
    if (found.isEmpty()) return ResponseEntity.notFound().build();
    RenderJob job = found.get();
    RenderAttempt previous =
        renderAttemptRepo.findTopByRenderJobIdOrderByAttemptNumberDesc(id).orElse(null);
    if (previous == null
        || !(previous.getStage() == RenderExecutionStage.FAILED
            || previous.getStage() == RenderExecutionStage.ABANDONED)) {
      return ResponseEntity.badRequest()
          .body(java.util.Map.of("message", "Only failed or abandoned jobs can be retried"));
    }
    if ((previous.getStage() == RenderExecutionStage.FAILED
            || previous.getStage() == RenderExecutionStage.ABANDONED)
        && ("PROVIDER_SUBMISSION_UNCERTAIN".equals(job.getErrorCode())
            || (previous.getProviderJobId() != null
                && previous.getProviderJobState() != ProviderJobState.SUCCEEDED
                && previous.getProviderJobState() != ProviderJobState.FAILED
                && previous.getProviderJobState() != ProviderJobState.CANCELLED))) {
      return ResponseEntity.badRequest()
          .body(
              java.util.Map.of(
                  "message", "Remote OpenArt job is not terminal; reconcile it before retrying"));
    }
    int nextNumber = previous.getAttemptNumber() + 1;
    if (nextNumber > job.getMaxAttempts()) {
      return ResponseEntity.badRequest()
          .body(java.util.Map.of("message", "Maximum render attempts reached"));
    }
    if (creditTrackingService != null) {
      creditTrackingService.reserveAdditionalAttempt(job);
    }
    renderAttemptRepo.save(
        RenderAttempt.builder()
            .renderJobId(id)
            .attemptNumber(nextNumber)
            .stage(RenderExecutionStage.QUEUED)
            .pollCount(0)
            .eligibleAt(Instant.now())
            .build());
    job.setAttemptNumber(nextNumber);
    job.setStatus(RenderJob.RenderJobStatus.QUEUED);
    job.setFailedAt(null);
    job.setErrorCode(null);
    job.setErrorMessage(null);
    renderJobRepo.save(job);
    return ResponseEntity.ok(
        java.util.Map.of(
            "success", true, "message", "Render retry queued", "attemptNumber", nextNumber));
  }

  /** Get render jobs by status. */
  @GetMapping("/by-status/{status}")
  public ResponseEntity<List<RenderJobDto>> getRenderJobsByStatus(@PathVariable String status) {
    log.info("GET /api/v1/render-jobs/by-status/{}", status);

    RenderJob.RenderJobStatus jobStatus;
    try {
      jobStatus = RenderJob.RenderJobStatus.valueOf(status.toUpperCase());
    } catch (IllegalArgumentException e) {
      return ResponseEntity.badRequest().build();
    }

    List<RenderJob> jobs = renderJobRepo.findByStatus(jobStatus);

    List<RenderJobDto> dtos = jobs.stream().map(this::toDto).toList();

    return ResponseEntity.ok(dtos);
  }

  /** Get render jobs by content ID. */
  @GetMapping("/by-content/{contentId}")
  public ResponseEntity<List<RenderJobDto>> getRenderJobsByContentId(@PathVariable Long contentId) {
    log.info("GET /api/v1/render-jobs/by-content/{}", contentId);

    List<RenderJob> jobs = renderJobRepo.findByContentIdOrderByCreatedAtDesc(contentId);

    List<RenderJobDto> dtos = jobs.stream().map(this::toDto).toList();

    return ResponseEntity.ok(dtos);
  }

  /** Convert RenderJob entity to DTO. */
  private RenderJobDto toDto(RenderJob job) {
    RenderJobDto.RenderJobDtoBuilder builder =
        RenderJobDto.builder()
            .id(job.getId())
            .contentId(job.getContentId())
            .contentTitle(job.getContentTitleSnapshot())
            .promptVersionId(job.getPromptVersionId())
            .promptVersionNumber(job.getPromptVersionNumberSnapshot())
            .jobType(job.getJobType().name())
            .status(job.getStatus().name())
            .attemptNumber(job.getAttemptNumber())
            .maxAttempts(job.getMaxAttempts())
            .openartJobId(job.getOpenartJobId())
            .creditsEstimated(job.getCreditsEstimated())
            .creditsActual(job.getCreditsActual())
            .queuedAt(job.getQueuedAt())
            .startedAt(job.getStartedAt())
            .completedAt(job.getCompletedAt())
            .failedAt(job.getFailedAt())
            .errorCode(job.getErrorCode())
            .errorMessage(job.getErrorMessage())
            .attempts(
                renderAttemptRepo == null
                    ? List.of()
                    : renderAttemptRepo
                        .findByRenderJobIdOrderByAttemptNumberAsc(job.getId())
                        .stream()
                        .map(
                            attempt ->
                                RenderJobDto.AttemptDto.builder()
                                    .id(attempt.getId())
                                    .attemptNumber(attempt.getAttemptNumber())
                                    .stage(attempt.getStage().name())
                                    .providerJobId(attempt.getProviderJobId())
                                    .assetId(attempt.getAssetId())
                                    .startedAt(attempt.getStartedAt())
                                    .completedAt(attempt.getCompletedAt())
                                    .errorCode(attempt.getErrorCode())
                                    .errorMessage(attempt.getErrorMessage())
                                    .build())
                        .toList());

    if (postRenderEvaluationRepo != null) {
      postRenderEvaluationRepo
          .findTopByRenderAsset_RenderJob_IdOrderByCreatedAtDesc(job.getId())
          .ifPresent(
              evaluation ->
                  builder.qaResult(
                      RenderJobDto.QaResultDto.builder()
                          .id(evaluation.getId())
                          .decision(evaluation.getOverallDecision().name())
                          .decisionReason(
                              "Post-render evaluation " + evaluation.getPostRenderRulesetVersion())
                          .requiresHumanReview(evaluation.isHumanReviewRequired())
                          .evidenceVersion(evaluation.getEvidenceVersion())
                          .rulesetVersion(evaluation.getPostRenderRulesetVersion())
                          .humanDecision(evaluation.getHumanDecision())
                          .canonicalPostRender(true)
                          .build()));
    } else {
      qaResultRepo
          .findTopByRenderAsset_RenderJob_IdOrderByCreatedAtDesc(job.getId())
          .ifPresent(
              qaResult ->
                  builder.qaResult(
                      RenderJobDto.QaResultDto.builder()
                          .id(qaResult.getId())
                          .decision(qaResult.getDecision().name())
                          .decisionReason(qaResult.getDecisionReason())
                          .complianceScore(qaResult.getComplianceScore())
                          .confidence(
                              qaResult.getConfidence() == null
                                  ? null
                                  : qaResult.getConfidence().doubleValue())
                          .hasDeadAir(qaResult.getHasDeadAir())
                          .characterIdentityVerified(qaResult.getCharacterIdentityVerified())
                          .characterIdentityIssues(qaResult.getCharacterIdentityIssues())
                          .requiresHumanReview(qaResult.getRequiresHumanReview())
                          .canonicalPostRender(false)
                          .build()));
    }

    return builder.build();
  }
}
