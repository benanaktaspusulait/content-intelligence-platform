package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationAttempt;
import com.pompom.creative.domain.PublicationExecutionStage;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.PlatformPublisher;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.creative.repository.PublicationAttemptRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.TransactionCallback;
import org.springframework.transaction.support.TransactionTemplate;

@ExtendWith(MockitoExtension.class)
class PublicationAttemptOrchestratorTest {

  @Mock private PublicationAttemptRepository attemptRepository;
  @Mock private PublicationJobRepository jobRepository;
  @Mock private PlatformPublisher publisher;
  @Mock private TransactionTemplate transactionTemplate;

  private UUID jobId;
  private UUID attemptId;
  private PublicationJob job;
  private PublicationAttempt attempt;
  private PublicationAttemptOrchestrator orchestrator;

  @BeforeEach
  void setUp() {
    jobId = UUID.randomUUID();
    attemptId = UUID.randomUUID();
    job =
        PublicationJob.builder()
            .id(jobId)
            .platform(PlatformType.YOUTUBE)
            .status(PublicationStatus.QUEUED)
            .videoPath("/internal/render-assets/video.mp4")
            .platformAccountId("youtube-account")
            .idempotencyKey("publish-key")
            .title("A short")
            .caption("A caption")
            .hashtags("one,two")
            .isPrivate(false)
            .build();
    attempt =
        PublicationAttempt.builder()
            .id(attemptId)
            .publicationJobId(jobId)
            .attemptNumber(1)
            .stage(PublicationExecutionStage.QUEUED)
            .eligibleAt(Instant.now())
            .leaseOwner("worker-1")
            .leaseExpiresAt(Instant.now().plusSeconds(60))
            .build();

    orchestrator =
        new PublicationAttemptOrchestrator(
            attemptRepository,
            jobRepository,
            Map.of("youTubeShortsPublisher", publisher),
            transactionTemplate);
  }

  @Test
  void processAttempt_publishesAndPersistsAuthoritativeIdentity() {
    runTransactionCallbacks();
    when(attemptRepository.findById(attemptId)).thenReturn(Optional.of(attempt));
    when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
    when(publisher.isConfigured()).thenReturn(true);
    when(publisher.publish(any()))
        .thenReturn(PublishResponse.success("post-1", "https://youtu.be/post-1"));

    orchestrator.processAttempt(attemptId, "worker-1");

    assertThat(attempt.getStage()).isEqualTo(PublicationExecutionStage.COMPLETE);
    assertThat(attempt.getPlatformPostId()).isEqualTo("post-1");
    assertThat(attempt.getAuthoritativePermalink()).isEqualTo("https://youtu.be/post-1");
    assertThat(job.getStatus()).isEqualTo(PublicationStatus.PUBLISHED);
    assertThat(job.getPostUrl()).isEqualTo("https://youtu.be/post-1");
    assertThat(attempt.getLeaseOwner()).isNull();
    verify(publisher).publish(any());
  }

  @Test
  void reconcileExpiredSubmission_capturesRemoteResultWithoutRepublishing() {
    attempt.setStage(PublicationExecutionStage.SUBMITTING);
    attempt.setLeaseExpiresAt(Instant.now().minusSeconds(5));
    attempt.setPlatformVideoId("remote-video-1");
    job.setStatus(PublicationStatus.UPLOADING);
    runTransactionCallbacks();
    when(attemptRepository.findByStageAndLeaseExpiresAtBefore(
            eq(PublicationExecutionStage.SUBMITTING), any()))
        .thenReturn(List.of(attempt));
    when(attemptRepository.findById(attemptId)).thenReturn(Optional.of(attempt));
    when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
    when(publisher.isConfigured()).thenReturn(true);
    when(publisher.reconcile(any(), isNull(), eq("remote-video-1")))
        .thenReturn(Optional.of(PublishResponse.success("post-2", "https://youtu.be/post-2")));

    orchestrator.reconcileExpiredSubmissions();

    assertThat(attempt.getStage()).isEqualTo(PublicationExecutionStage.COMPLETE);
    assertThat(attempt.getPlatformPostId()).isEqualTo("post-2");
    assertThat(job.getStatus()).isEqualTo(PublicationStatus.PUBLISHED);
    verify(publisher, never()).publish(any());
    verify(publisher).reconcile(any(), isNull(), eq("remote-video-1"));
  }

  private void runTransactionCallbacks() {
    when(transactionTemplate.execute(any(TransactionCallback.class)))
        .thenAnswer(
            invocation ->
                invocation.<TransactionCallback<Object>>getArgument(0).doInTransaction(null));
    doAnswer(
            invocation -> {
              invocation
                  .<java.util.function.Consumer<TransactionStatus>>getArgument(0)
                  .accept(null);
              return null;
            })
        .when(transactionTemplate)
        .executeWithoutResult(any());
  }
}
