package com.pompom.creative.api.controller;

import com.pompom.creative.api.dto.RenderJobDto;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.ValidationEvidenceClientException;
import com.pompom.creative.evidence.ValidationEvidenceIncompleteRemoteException;
import com.pompom.creative.evidence.ValidationEvidenceNotFoundException;
import com.pompom.creative.evidence.ValidationEvidenceServiceException;
import com.pompom.creative.evidence.ValidationEvidenceTimeoutException;
import com.pompom.creative.queue.IdempotencyKeyConflictException;
import com.pompom.creative.queue.QueueRenderJobRequest;
import com.pompom.creative.queue.QueueRenderJobResponse;
import com.pompom.creative.queue.RenderJobQueueService;
import com.pompom.creative.queue.ValidationEvidenceRejectedException;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import java.net.URI;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST API controller for render jobs. */
@RestController
@RequestMapping("/api/v1/render-jobs")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class RenderJobController {

  private final RenderJobRepository renderJobRepo;
  private final RenderQaResultRepository qaResultRepo;
  private final RenderJobQueueService queueService;

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
            .errorMessage(job.getErrorMessage());

    // Load QA result if exists
    qaResultRepo
        .findTopByRenderAsset_RenderJob_IdOrderByCreatedAtDesc(job.getId())
        .ifPresent(
            qaResult -> {
              builder.qaResult(
                  RenderJobDto.QaResultDto.builder()
                      .id(qaResult.getId())
                      .decision(qaResult.getDecision().name())
                      .decisionReason(qaResult.getDecisionReason())
                      .complianceScore(qaResult.getComplianceScore())
                      .confidence(
                          qaResult.getConfidence() != null
                              ? qaResult.getConfidence().doubleValue()
                              : null)
                      .hasDeadAir(qaResult.getHasDeadAir())
                      .characterIdentityVerified(qaResult.getCharacterIdentityVerified())
                      .characterIdentityIssues(qaResult.getCharacterIdentityIssues())
                      .requiresHumanReview(qaResult.getRequiresHumanReview())
                      .build());
            });

    return builder.build();
  }
}
