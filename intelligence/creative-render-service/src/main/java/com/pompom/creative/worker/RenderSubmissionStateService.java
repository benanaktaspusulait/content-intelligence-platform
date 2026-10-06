package com.pompom.creative.worker;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Commits the durable boundary around an external OpenArt submission.
 *
 * <p>The intent transaction must commit before the CLI is invoked. If the process dies after
 * OpenArt accepts the request but before the history id is persisted, the attempt remains
 * {@link RenderExecutionStage#SUBMITTING} and is never automatically submitted a second time.
 */
@Component
@RequiredArgsConstructor
public class RenderSubmissionStateService {

  private static final String UNCERTAIN_CODE = "PROVIDER_SUBMISSION_UNCERTAIN";

  private final RenderAttemptRepository attemptRepository;
  private final RenderJobRepository jobRepository;

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public RenderJob markSubmitting(UUID attemptId, String leaseOwner) {
    RenderAttempt attempt = findAttempt(attemptId);
    requireLease(attempt, leaseOwner);
    if (attempt.getStage() != RenderExecutionStage.QUEUED) {
      throw new IllegalStateException(
          "Attempt " + attemptId + " is not queued for provider submission");
    }

    RenderJob job = findJob(attempt.getRenderJobId());
    Instant now = Instant.now();
    attempt.setStage(RenderExecutionStage.SUBMITTING);
    attempt.setStartedAt(now);
    releaseLease(attempt);
    job.setStatus(RenderJob.RenderJobStatus.GENERATING);
    if (job.getStartedAt() == null) {
      job.setStartedAt(now);
    }
    attemptRepository.save(attempt);
    jobRepository.save(job);
    return job;
  }

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public void markSubmitted(
      UUID attemptId, UUID jobId, String providerJobId, BigDecimal estimatedCredits) {
    if (providerJobId == null || providerJobId.isBlank()) {
      throw new IllegalArgumentException("OpenArt returned an empty history id");
    }
    RenderAttempt attempt = findAttempt(attemptId);
    if (attempt.getStage() != RenderExecutionStage.SUBMITTING) {
      throw new IllegalStateException(
          "Attempt " + attemptId + " is not awaiting submission completion");
    }
    RenderJob job = findJob(jobId);
    if (!job.getId().equals(attempt.getRenderJobId())) {
      throw new IllegalStateException("Submission attempt and render job do not match");
    }

    attempt.setProviderJobId(providerJobId);
    attempt.setStage(RenderExecutionStage.PROVIDER_QUEUED);
    releaseLease(attempt);
    job.setOpenartJobId(providerJobId);
    if (estimatedCredits != null) {
      job.setCreditsEstimated(estimatedCredits);
    }
    job.setStatus(RenderJob.RenderJobStatus.GENERATING);
    attemptRepository.save(attempt);
    jobRepository.save(job);
  }

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public void markUncertain(UUID attemptId, UUID jobId, Exception submissionError) {
    RenderAttempt attempt = findAttempt(attemptId);
    RenderJob job = findJob(jobId);
    String message =
        submissionError == null || submissionError.getMessage() == null
            ? "OpenArt submission outcome is unknown"
            : submissionError.getMessage();

    attempt.setStage(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
    attempt.setErrorCode(UNCERTAIN_CODE);
    attempt.setErrorMessage(message);
    attempt.setTerminalReason(message);
    attempt.setCompletedAt(Instant.now());
    releaseLease(attempt);

    job.setStatus(RenderJob.RenderJobStatus.FAILED);
    job.setFailedAt(Instant.now());
    job.setErrorCode(UNCERTAIN_CODE);
    job.setErrorMessage(message);
    attemptRepository.save(attempt);
    jobRepository.save(job);
  }

  private RenderAttempt findAttempt(UUID attemptId) {
    return attemptRepository
        .findById(attemptId)
        .orElseThrow(() -> new IllegalArgumentException("RenderAttempt not found: " + attemptId));
  }

  private RenderJob findJob(UUID jobId) {
    return jobRepository
        .findById(jobId)
        .orElseThrow(() -> new IllegalArgumentException("RenderJob not found: " + jobId));
  }

  private void requireLease(RenderAttempt attempt, String leaseOwner) {
    if (!leaseOwner.equals(attempt.getLeaseOwner())) {
      throw new LeaseNotOwnedException(attempt.getId(), leaseOwner, attempt.getLeaseOwner());
    }
  }

  private void releaseLease(RenderAttempt attempt) {
    attempt.setLeaseOwner(null);
    attempt.setLeaseExpiresAt(null);
    attempt.setLeaseHeartbeatAt(null);
  }
}
