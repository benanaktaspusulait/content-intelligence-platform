package com.pompom.creative.worker;

import com.pompom.creative.domain.PublicationAttempt;
import com.pompom.creative.domain.PublicationExecutionStage;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.MetaPublicationGuard;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.PlatformPublisher;
import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.creative.repository.PublicationAttemptRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/** Executes a claimed publication attempt without holding a transaction over remote HTTP I/O. */
@Component
public class PublicationAttemptOrchestrator {

  private final PublicationAttemptRepository attemptRepository;
  private final PublicationJobRepository jobRepository;
  private final Map<String, PlatformPublisher> publishers;
  private final TransactionTemplate transactionTemplate;
  private final MetaPublicationGuard metaPublicationGuard;

  public PublicationAttemptOrchestrator(
      PublicationAttemptRepository attemptRepository,
      PublicationJobRepository jobRepository,
      Map<String, PlatformPublisher> publishers,
      TransactionTemplate transactionTemplate,
      MetaPublicationGuard metaPublicationGuard) {
    this.attemptRepository = attemptRepository;
    this.jobRepository = jobRepository;
    this.publishers = publishers;
    this.transactionTemplate = transactionTemplate;
    this.metaPublicationGuard = metaPublicationGuard;
  }

  public void processAttempt(UUID attemptId, String leaseOwner) {
    PublicationWork work =
        transactionTemplate.execute(status -> markSubmitting(attemptId, leaseOwner));
    if (work == null) {
      return;
    }

    PublishResponse response;
    try {
      PlatformPublisher publisher = getPublisher(work.platform());
      if (publisher == null || !publisher.isConfigured()) {
        throw new IllegalStateException("Publisher is not configured for " + work.platform());
      }
      response = publisher.publish(work.request());
    } catch (Exception error) {
      markAmbiguous(attemptId, error.getMessage());
      return;
    }

    if (!Boolean.TRUE.equals(response.getSuccess())) {
      markAmbiguous(attemptId, response.getMessage());
      return;
    }
    transactionTemplate.executeWithoutResult(status -> markComplete(attemptId, response));
  }

  private PublicationWork markSubmitting(UUID attemptId, String leaseOwner) {
    PublicationAttempt attempt =
        attemptRepository
            .findById(attemptId)
            .orElseThrow(() -> new IllegalArgumentException("Publication attempt not found"));
    if (!leaseOwner.equals(attempt.getLeaseOwner())) {
      throw new LeaseNotOwnedException(attemptId, leaseOwner, attempt.getLeaseOwner());
    }
    if (attempt.getStage() != PublicationExecutionStage.QUEUED) {
      throw new IllegalStateException("Publication attempt is not queued");
    }
    PublicationJob job =
        jobRepository
            .findById(attempt.getPublicationJobId())
            .orElseThrow(() -> new IllegalArgumentException("Publication job not found"));
    try {
      if (metaPublicationGuard != null) {
        metaPublicationGuard.assertAllowed(job.getPlatform());
      }
    } catch (com.pompom.creative.oauth.MetaPublishingDisabledException disabled) {
      attempt.setStage(PublicationExecutionStage.CANCELLED);
      attempt.setErrorCode("META_PUBLISH_DISABLED");
      attempt.setErrorMessage(disabled.getMessage());
      attempt.setCompletedAt(Instant.now());
      clearLease(attempt);
      attemptRepository.save(attempt);
      job.updateStatus(PublicationStatus.FAILED);
      job.setErrorCode("META_PUBLISH_DISABLED");
      job.setErrorMessage(disabled.getMessage());
      jobRepository.save(job);
      return null;
    }
    if (job.getStatus() == PublicationStatus.CANCELLED) {
      attempt.setStage(PublicationExecutionStage.CANCELLED);
      attempt.setCompletedAt(Instant.now());
      clearLease(attempt);
      attemptRepository.save(attempt);
      return null;
    }

    attempt.setStage(PublicationExecutionStage.SUBMITTING);
    attempt.setStartedAt(Instant.now());
    attemptRepository.save(attempt);
    job.updateStatus(PublicationStatus.UPLOADING);
    job.setProgressPercent(10);
    jobRepository.save(job);

    PublishRequest request =
        PublishRequest.builder()
            .videoPath(job.getVideoPath())
            .platformAccountId(job.getPlatformAccountId())
            .idempotencyKey(job.getIdempotencyKey())
            .title(job.getTitle())
            .caption(job.getCaption())
            .hashtags(parseHashtags(job.getHashtags()))
            .isPrivate(job.getIsPrivate())
            .build();
    return new PublicationWork(job.getPlatform(), request);
  }

  private void markComplete(UUID attemptId, PublishResponse response) {
    PublicationAttempt attempt = attemptRepository.findById(attemptId).orElseThrow();
    PublicationJob job = jobRepository.findById(attempt.getPublicationJobId()).orElseThrow();

    attempt.setStage(PublicationExecutionStage.COMPLETE);
    attempt.setPlatformPostId(response.getPlatformPostId());
    attempt.setPlatformVideoId(response.getPlatformVideoId());
    attempt.setAuthoritativePermalink(response.getPostUrl());
    attempt.setCompletedAt(Instant.now());
    clearLease(attempt);
    attemptRepository.save(attempt);

    job.setPlatformPostId(response.getPlatformPostId());
    job.setPlatformVideoId(response.getPlatformVideoId());
    job.setPostUrl(response.getPostUrl());
    job.setProgressPercent(100);
    job.updateStatus(PublicationStatus.PUBLISHED);
    jobRepository.save(job);
  }

  private void markAmbiguous(UUID attemptId, String message) {
    transactionTemplate.executeWithoutResult(
        status -> {
          PublicationAttempt attempt = attemptRepository.findById(attemptId).orElseThrow();
          PublicationJob job = jobRepository.findById(attempt.getPublicationJobId()).orElseThrow();
          attempt.setStage(PublicationExecutionStage.AMBIGUOUS);
          attempt.setErrorCode("REMOTE_OUTCOME_AMBIGUOUS");
          attempt.setErrorMessage(message);
          attempt.setCompletedAt(Instant.now());
          clearLease(attempt);
          attemptRepository.save(attempt);

          job.setErrorMessage(message);
          job.updateStatus(PublicationStatus.FAILED);
          jobRepository.save(job);
        });
  }

  public void reconcileExpiredSubmissions() {
    List<UUID> expiredIds =
        transactionTemplate.execute(
            status ->
                attemptRepository
                    .findByStageAndLeaseExpiresAtBefore(
                        PublicationExecutionStage.SUBMITTING, Instant.now())
                    .stream()
                    .map(PublicationAttempt::getId)
                    .toList());
    if (expiredIds == null) {
      return;
    }
    for (UUID attemptId : expiredIds) {
      ReconciliationWork work =
          transactionTemplate.execute(status -> loadReconciliationWork(attemptId));
      if (work == null) {
        continue;
      }
      Optional<PublishResponse> response =
          Optional.ofNullable(getPublisher(work.platform()))
              .filter(PlatformPublisher::isConfigured)
              .flatMap(
                  publisher ->
                      publisher.reconcile(
                          work.request(), work.platformPostId(), work.platformVideoId()));
      if (response.isPresent() && Boolean.TRUE.equals(response.get().getSuccess())) {
        transactionTemplate.executeWithoutResult(status -> markComplete(attemptId, response.get()));
      } else {
        markAmbiguous(
            attemptId, "Remote outcome could not be reconciled; no blind retry was performed");
      }
    }
  }

  private ReconciliationWork loadReconciliationWork(UUID attemptId) {
    PublicationAttempt attempt = attemptRepository.findById(attemptId).orElse(null);
    if (attempt == null) {
      return null;
    }
    PublicationJob job = jobRepository.findById(attempt.getPublicationJobId()).orElseThrow();
    return new ReconciliationWork(
        job.getPlatform(),
        buildRequest(job),
        attempt.getPlatformPostId(),
        attempt.getPlatformVideoId());
  }

  private PublishRequest buildRequest(PublicationJob job) {
    return PublishRequest.builder()
        .videoPath(job.getVideoPath())
        .platformAccountId(job.getPlatformAccountId())
        .idempotencyKey(job.getIdempotencyKey())
        .title(job.getTitle())
        .caption(job.getCaption())
        .hashtags(parseHashtags(job.getHashtags()))
        .isPrivate(job.getIsPrivate())
        .build();
  }

  private void clearLease(PublicationAttempt attempt) {
    attempt.setLeaseOwner(null);
    attempt.setLeaseExpiresAt(null);
  }

  private PlatformPublisher getPublisher(PlatformType platform) {
    String beanName =
        switch (platform) {
          case TIKTOK -> "tikTokPublisher";
          case YOUTUBE -> "youTubeShortsPublisher";
          case FACEBOOK -> "facebookPublisher";
          case INSTAGRAM -> "instagramReelsPublisher";
        };
    return publishers.get(beanName);
  }

  private List<String> parseHashtags(String hashtags) {
    if (hashtags == null || hashtags.isBlank()) {
      return List.of();
    }
    return Arrays.stream(hashtags.split(","))
        .map(String::trim)
        .filter(value -> !value.isEmpty())
        .toList();
  }

  private record PublicationWork(PlatformType platform, PublishRequest request) {}

  private record ReconciliationWork(
      PlatformType platform,
      PublishRequest request,
      String platformPostId,
      String platformVideoId) {}
}
