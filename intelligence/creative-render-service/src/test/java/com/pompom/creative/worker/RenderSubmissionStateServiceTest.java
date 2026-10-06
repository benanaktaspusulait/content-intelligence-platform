package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import java.math.BigDecimal;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RenderSubmissionStateServiceTest {

  private static final String OWNER = "worker-1";

  @Mock private RenderAttemptRepository attemptRepository;
  @Mock private RenderJobRepository jobRepository;

  private RenderSubmissionStateService service;
  private RenderAttempt attempt;
  private RenderJob job;

  @BeforeEach
  void setUp() {
    service = new RenderSubmissionStateService(attemptRepository, jobRepository);
    UUID jobId = UUID.randomUUID();
    attempt =
        RenderAttempt.builder()
            .id(UUID.randomUUID())
            .renderJobId(jobId)
            .attemptNumber(1)
            .stage(RenderExecutionStage.QUEUED)
            .leaseOwner(OWNER)
            .build();
    job =
        RenderJob.builder()
            .id(jobId)
            .contentId(1L)
            .promptVersionId(1L)
            .contentTitleSnapshot("Episode")
            .promptVersionNumberSnapshot(1)
            .promptSha256("a".repeat(64))
            .promptTextSnapshot("prompt")
            .jobType(RenderJob.JobType.VIDEO)
            .openartModel("kling-3-omni")
            .build();
    when(attemptRepository.findById(attempt.getId())).thenReturn(Optional.of(attempt));
    when(jobRepository.findById(job.getId())).thenReturn(Optional.of(job));
  }

  @Test
  void markSubmittingCommitsAnUnclaimableIntentBeforeProviderCall() {
    RenderJob prepared = service.markSubmitting(attempt.getId(), OWNER);

    assertThat(prepared.getId()).isEqualTo(job.getId());
    assertThat(attempt.getStage()).isEqualTo(RenderExecutionStage.SUBMITTING);
    assertThat(attempt.getLeaseOwner()).isNull();
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.GENERATING);
    verify(attemptRepository).save(attempt);
    verify(jobRepository).save(job);
  }

  @Test
  void markSubmittedRecordsTheProviderIdentityAndMakesTheAttemptPollable() {
    attempt.setStage(RenderExecutionStage.SUBMITTING);
    attempt.setLeaseOwner(null);

    service.markSubmitted(attempt.getId(), job.getId(), "history-123", new BigDecimal("12.5"));

    assertThat(attempt.getStage()).isEqualTo(RenderExecutionStage.PROVIDER_QUEUED);
    assertThat(attempt.getProviderJobId()).isEqualTo("history-123");
    assertThat(job.getOpenartJobId()).isEqualTo("history-123");
    assertThat(job.getCreditsEstimated()).isEqualByComparingTo("12.5");
    verify(attemptRepository).save(attempt);
    verify(jobRepository).save(job);
  }

  @Test
  void submittedProviderJobDoesNotResurrectAnOperatorCancellation() {
    attempt.setStage(RenderExecutionStage.SUBMITTING);
    attempt.setLeaseOwner(null);
    job.setStatus(RenderJob.RenderJobStatus.ABANDONED);
    job.setErrorCode("CANCELLED_BY_OPERATOR");

    service.markSubmitted(attempt.getId(), job.getId(), "history-123", new BigDecimal("12.5"));

    assertThat(attempt.getStage()).isEqualTo(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
    assertThat(attempt.getProviderJobId()).isEqualTo("history-123");
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.ABANDONED);
    assertThat(job.getOpenartJobId()).isEqualTo("history-123");
  }

  @Test
  void attachProviderJobReleasesHumanReviewBackToPolling() {
    attempt.setStage(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
    attempt.setErrorCode("PROVIDER_SUBMISSION_UNCERTAIN");
    attempt.setLeaseOwner(null);
    job.setStatus(RenderJob.RenderJobStatus.FAILED);

    service.attachProviderJob(attempt.getId(), "history-456");

    assertThat(attempt.getStage()).isEqualTo(RenderExecutionStage.PROVIDER_QUEUED);
    assertThat(attempt.getProviderJobId()).isEqualTo("history-456");
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.GENERATING);
    assertThat(job.getOpenartJobId()).isEqualTo("history-456");
  }

  @Test
  void abandonUncertainSubmissionRemainsTerminalAndConservative() {
    attempt.setStage(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
    attempt.setErrorCode("PROVIDER_SUBMISSION_UNCERTAIN");
    attempt.setLeaseOwner(null);

    service.abandonUncertainSubmission(attempt.getId(), "checked OpenArt and found no history");

    assertThat(attempt.getStage()).isEqualTo(RenderExecutionStage.ABANDONED);
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.ABANDONED);
    assertThat(job.getErrorCode()).isEqualTo("PROVIDER_SUBMISSION_UNCERTAIN");
  }

  @Test
  void markUncertainPreventsAutomaticResubmission() {
    attempt.setStage(RenderExecutionStage.SUBMITTING);
    attempt.setLeaseOwner(null);

    service.markUncertain(
        attempt.getId(), job.getId(), new IllegalStateException("connection lost"));

    assertThat(attempt.getStage()).isEqualTo(RenderExecutionStage.NEEDS_HUMAN_REVIEW);
    assertThat(attempt.getErrorCode()).isEqualTo("PROVIDER_SUBMISSION_UNCERTAIN");
    assertThat(job.getStatus()).isEqualTo(RenderJob.RenderJobStatus.FAILED);
    assertThat(job.getErrorCode()).isEqualTo("PROVIDER_SUBMISSION_UNCERTAIN");
    verify(attemptRepository).save(attempt);
    verify(jobRepository).save(job);
  }
}
