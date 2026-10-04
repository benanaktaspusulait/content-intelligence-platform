package com.pompom.creative.service;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderQaResult;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.PlatformPublisher;
import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Publication service for managing social media publishing jobs. Implements state machine: QUEUED →
 * UPLOADING → PROCESSING → PUBLISHED/FAILED
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class PublicationService {

  private final PublicationJobRepository publicationJobRepository;
  private final RenderAssetRepository renderAssetRepository;
  private final RenderQaResultRepository qaResultRepository;
  private final AssetLibraryManager assetLibraryManager;
  private final Map<String, PlatformPublisher> publishers;

  /**
   * Queue a publication job.
   *
   * @param platform Target platform
   * @param renderAssetId canonical render asset identity
   * @param platformAccountId explicit target account identity
   * @param title Video title
   * @param caption Video caption
   * @param hashtags Hashtags (comma-separated or JSON array)
   * @param isPrivate Whether video should be private
   * @return Created job
   */
  @Transactional
  public PublicationJob queuePublication(
      PlatformType platform,
      UUID renderAssetId,
      String platformAccountId,
      String title,
      String caption,
      String hashtags,
      Boolean isPrivate) {
    RenderAsset asset = resolvePublishableAsset(renderAssetId);
    if (platformAccountId == null || platformAccountId.isBlank()) {
      throw new IllegalArgumentException("platformAccountId is required");
    }
    Path assetPath = assetLibraryManager.resolveStoredPath(asset);
    if (!Files.isRegularFile(assetPath)) {
      throw new IllegalStateException("Canonical asset file is unavailable");
    }
    if (!asset.getSha256().equals(assetLibraryManager.checksum(assetPath))) {
      throw new IllegalStateException("Canonical asset checksum does not match stored evidence");
    }
    log.info(
        "Queueing publication: platform={}, renderAssetId={}, account={}",
        platform,
        renderAssetId,
        platformAccountId);

    PublicationJob job =
        PublicationJob.builder()
            .platform(platform)
            .status(PublicationStatus.QUEUED)
            .videoPath(assetPath.toString())
            .renderAsset(asset)
            .videoId(asset.getVideoId())
            .variantId(asset.getVariantId())
            .platformAccountId(platformAccountId)
            .title(title)
            .caption(caption)
            .hashtags(hashtags)
            .isPrivate(isPrivate)
            .queuedAt(Instant.now())
            .build();

    PublicationJob saved = publicationJobRepository.save(job);

    log.info("Publication queued: jobId={}", saved.getId());

    // Start async publishing
    publishAsync(saved.getId());

    return saved;
  }

  private RenderAsset resolvePublishableAsset(UUID renderAssetId) {
    if (renderAssetId == null) {
      throw new IllegalArgumentException("renderAssetId is required");
    }
    RenderAsset asset =
        renderAssetRepository
            .findById(renderAssetId)
            .orElseThrow(() -> new IllegalArgumentException("Render asset not found"));
    if (asset.getAssetType() != RenderAsset.AssetType.VIDEO) {
      throw new IllegalArgumentException("Only video assets can be published");
    }
    if (!Boolean.TRUE.equals(asset.getIsCurrent())
        || Boolean.TRUE.equals(asset.getIsMock())
        || Boolean.TRUE.equals(asset.getQuarantined())
        || !Boolean.TRUE.equals(asset.getMediaVerified())
        || asset.getSha256() == null
        || asset.getVariantId() == null) {
      throw new IllegalStateException("Asset does not satisfy production publication invariants");
    }
    RenderQaResult qa =
        qaResultRepository
            .findTopByRenderAssetIdOrderByCreatedAtDesc(renderAssetId)
            .orElseThrow(() -> new IllegalStateException("Post-render QA evidence is missing"));
    if (qa.getDecision() != RenderQaResult.QaDecision.ACCEPT) {
      throw new IllegalStateException("Post-render QA has not accepted this asset");
    }
    if (Boolean.TRUE.equals(qa.getRequiresHumanReview())
        && !"APPROVED".equals(qa.getHumanDecision())) {
      throw new IllegalStateException("Required human review has not approved this asset");
    }
    return asset;
  }

  /** Publish job asynchronously. */
  @Async
  @Transactional
  public void publishAsync(UUID jobId) {
    log.info("Starting async publication: jobId={}", jobId);

    Optional<PublicationJob> jobOpt = publicationJobRepository.findById(jobId);
    if (jobOpt.isEmpty()) {
      log.error("Publication job not found: jobId={}", jobId);
      return;
    }

    PublicationJob job = jobOpt.get();

    try {
      // Update to UPLOADING
      updateJobStatus(job, PublicationStatus.UPLOADING, 0);

      // Get publisher for platform
      PlatformPublisher publisher = getPublisher(job.getPlatform());

      if (publisher == null || !publisher.isConfigured()) {
        throw new RuntimeException("Publisher not configured for platform: " + job.getPlatform());
      }

      // Build publish request
      PublishRequest request =
          PublishRequest.builder()
              .videoPath(job.getVideoPath())
              .title(job.getTitle())
              .caption(job.getCaption())
              .hashtags(parseHashtags(job.getHashtags()))
              .isPrivate(job.getIsPrivate())
              .build();

      // Update to PROCESSING
      updateJobStatus(job, PublicationStatus.PROCESSING, 50);

      // Publish
      PublishResponse response = publisher.publish(request);

      // Check result
      if (response.getSuccess()) {
        job.setPlatformPostId(response.getPlatformPostId());
        job.setPlatformVideoId(response.getPlatformVideoId());
        job.setPostUrl(response.getPostUrl());
        updateJobStatus(job, PublicationStatus.PUBLISHED, 100);

        log.info("Publication successful: jobId={}, postUrl={}", jobId, response.getPostUrl());
      } else {
        throw new RuntimeException(response.getMessage());
      }

    } catch (Exception e) {
      log.error("Publication failed: jobId={}", jobId, e);

      job.setErrorMessage(e.getMessage());
      job.incrementRetry();

      if (job.canRetry()) {
        log.info("Retrying publication: jobId={}, attempt={}", jobId, job.getRetryCount() + 1);
        updateJobStatus(job, PublicationStatus.QUEUED, 0);
        publishAsync(jobId); // Retry
      } else {
        updateJobStatus(job, PublicationStatus.FAILED, job.getProgressPercent());
      }
    }
  }

  /** Update job status. */
  @Transactional
  public void updateJobStatus(
      PublicationJob job, PublicationStatus status, Integer progressPercent) {
    job.updateStatus(status);
    job.setProgressPercent(progressPercent);
    publicationJobRepository.save(job);

    log.debug(
        "Job status updated: jobId={}, status={}, progress={}%",
        job.getId(), status, progressPercent);
  }

  /** Get job by ID. */
  @Transactional(readOnly = true)
  public Optional<PublicationJob> getJob(UUID jobId) {
    return publicationJobRepository.findById(jobId);
  }

  /** Get all jobs. */
  @Transactional(readOnly = true)
  public List<PublicationJob> getAllJobs() {
    return publicationJobRepository.findAllByOrderByQueuedAtDesc();
  }

  /** Get jobs by status. */
  @Transactional(readOnly = true)
  public List<PublicationJob> getJobsByStatus(PublicationStatus status) {
    return publicationJobRepository.findByStatus(status);
  }

  /** Get active jobs (not terminal). */
  @Transactional(readOnly = true)
  public List<PublicationJob> getActiveJobs() {
    List<PublicationStatus> activeStatuses =
        List.of(
            PublicationStatus.QUEUED, PublicationStatus.UPLOADING, PublicationStatus.PROCESSING);
    return publicationJobRepository.findByStatusIn(activeStatuses);
  }

  /** Cancel a job. */
  @Transactional
  public boolean cancelJob(UUID jobId) {
    Optional<PublicationJob> jobOpt = publicationJobRepository.findById(jobId);

    if (jobOpt.isEmpty()) {
      return false;
    }

    PublicationJob job = jobOpt.get();

    // Can only cancel if not terminal
    if (!job.isTerminal()) {
      updateJobStatus(job, PublicationStatus.CANCELLED, job.getProgressPercent());
      log.info("Job cancelled: jobId={}", jobId);
      return true;
    }

    return false;
  }

  /** Get statistics. */
  @Transactional(readOnly = true)
  public Map<String, Long> getStatistics() {
    return Map.of(
        "queued", publicationJobRepository.countByStatus(PublicationStatus.QUEUED),
        "uploading", publicationJobRepository.countByStatus(PublicationStatus.UPLOADING),
        "processing", publicationJobRepository.countByStatus(PublicationStatus.PROCESSING),
        "published", publicationJobRepository.countByStatus(PublicationStatus.PUBLISHED),
        "failed", publicationJobRepository.countByStatus(PublicationStatus.FAILED),
        "cancelled", publicationJobRepository.countByStatus(PublicationStatus.CANCELLED));
  }

  /** Get publisher for platform. */
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

  /** Parse hashtags from string. */
  private List<String> parseHashtags(String hashtags) {
    if (hashtags == null || hashtags.isEmpty()) {
      return List.of();
    }

    // Simple comma-separated parsing
    return List.of(hashtags.split(",")).stream()
        .map(String::trim)
        .filter(s -> !s.isEmpty())
        .collect(Collectors.toList());
  }
}
