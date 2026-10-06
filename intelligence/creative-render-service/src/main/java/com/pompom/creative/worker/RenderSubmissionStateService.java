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
 * OpenArt accepts the request but before the history id is persisted, the attempt remains {@link
 * RenderExecutionStage#SUBMITTING} and is never automatically submitted a second time.
 */
@Component
@RequiredArgsConstructor
public class RenderSubmissionStateService {

  private static final String UNCERTAIN_CODE = "PROVIDER_SUBMISSION_UNCERTAIN";
  private static final String CANCELLED_CODE = "CANCELLED_BY_OPERATOR";
  private static final String CANCELLED_SUBMISSION_CODE = "CANCELLED_DURING_SUBMISSION";

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

  public void markSubmitted(
      UUID attemptId, UUID jobId, String providerJobId, BigDecimal estimatedCredits) {
    markSubmitted(
        attemptId,
        jobId,
        providerJobId,
        estimatedCredits,
        com.pompom.creative.domain.RenderProviderOperation.VIDEO);
  }

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public void markSubmitted(
      UUID attemptId,
      UUID jobId,
      String providerJobId,
      BigDecimal estimatedCredits,
      com.pompom.creative.domain.RenderProviderOperation operation) {
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

    job.setOpenartJobId(providerJobId);
    if (job.getStatus() == RenderJob.RenderJobStatus.ABANDONED
        && CANCELLED_CODE.equals(job.getErrorCode())) {
      String message =
          "Operator cancelled while OpenArt submission was in flight; reconcile history "
              + providerJobId;
      attempt.setProviderJobId(providerJobId);
      attempt.setProviderOperation(operation);
      attempt.setProviderJobState(com.pompom.creative.domain.ProviderJobState.UNKNOWN);
      attempt.setStage(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
      attempt.setErrorCode(CANCELLED_SUBMISSION_CODE);
      attempt.setErrorMessage(message);
      attempt.setTerminalReason(message);
      attempt.setCompletedAt(Instant.now());
      releaseLease(attempt);
      attemptRepository.save(attempt);
      jobRepository.save(job);
      return;
    }

    attempt.setProviderJobId(providerJobId);
    attempt.setProviderOperation(operation);
    attempt.setStage(RenderExecutionStage.PROVIDER_QUEUED);
    releaseLease(attempt);
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
    boolean cancelled =
        job.getStatus() == RenderJob.RenderJobStatus.ABANDONED
            && CANCELLED_CODE.equals(job.getErrorCode());
    String message =
        submissionError == null || submissionError.getMessage() == null
            ? "OpenArt submission outcome is unknown"
            : submissionError.getMessage();

    attempt.setStage(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
    attempt.setErrorCode(cancelled ? "CANCELLED_SUBMISSION_UNCERTAIN" : UNCERTAIN_CODE);
    attempt.setErrorMessage(message);
    attempt.setTerminalReason(message);
    attempt.setCompletedAt(Instant.now());
    releaseLease(attempt);

    if (!cancelled) {
      job.setStatus(RenderJob.RenderJobStatus.FAILED);
      job.setFailedAt(Instant.now());
      job.setErrorCode(UNCERTAIN_CODE);
      job.setErrorMessage(message);
    }
    attemptRepository.save(attempt);
    jobRepository.save(job);
  }

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public void attachProviderJob(UUID attemptId, String providerJobId) {
    if (providerJobId == null || providerJobId.isBlank()) {
      throw new IllegalArgumentException("Provider history id must not be blank");
    }
    RenderAttempt attempt = findAttempt(attemptId);
    requireReconciliation(attempt);
    RenderJob job = findJob(attempt.getRenderJobId());

    attempt.setProviderJobId(providerJobId);
    attempt.setProviderJobState(com.pompom.creative.domain.ProviderJobState.UNKNOWN);
    attempt.setStage(RenderExecutionStage.PROVIDER_QUEUED);
    attempt.setNextPollAt(Instant.now());
    attempt.setErrorCode(null);
    attempt.setErrorMessage(null);
    attempt.setTerminalReason(null);
    attempt.setCompletedAt(null);
    releaseLease(attempt);

    job.setOpenartJobId(providerJobId);
    job.setStatus(RenderJob.RenderJobStatus.GENERATING);
    job.setFailedAt(null);
    job.setErrorCode(null);
    job.setErrorMessage(null);
    attemptRepository.save(attempt);
    jobRepository.save(job);
  }

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public void abandonUncertainSubmission(UUID attemptId, String reason) {
    RenderAttempt attempt = findAttempt(attemptId);
    requireReconciliation(attempt);
    RenderJob job = findJob(attempt.getRenderJobId());
    String message =
        reason == null || reason.isBlank()
            ? "Operator abandoned an uncertain OpenArt submission"
            : reason;

    attempt.setStage(RenderExecutionStage.ABANDONED);
    attempt.setErrorCode("PROVIDER_SUBMISSION_UNCERTAIN");
    attempt.setErrorMessage(message);
    attempt.setTerminalReason(message);
    attempt.setCompletedAt(Instant.now());
    releaseLease(attempt);
    job.setStatus(RenderJob.RenderJobStatus.ABANDONED);
    job.setFailedAt(Instant.now());
    job.setErrorCode("PROVIDER_SUBMISSION_UNCERTAIN");
    job.setErrorMessage(message);
    // Keep the estimate reservation: the operator has explicitly acknowledged that a remote
    // history may exist, so releasing the budget would undercount a possible provider charge.
    attemptRepository.save(attempt);
    jobRepository.save(job);
  }

  private void requireReconciliation(RenderAttempt attempt) {
    if (attempt.getStage() != RenderExecutionStage.NEEDS_HUMAN_REVIEW
        || (attempt.getErrorCode() == null
            || (!attempt.getErrorCode().startsWith("PROVIDER_SUBMISSION")
                && !attempt.getErrorCode().startsWith("CANCELLED_SUBMISSION")))) {
      throw new IllegalStateException("Attempt is not awaiting submission reconciliation");
    }
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
