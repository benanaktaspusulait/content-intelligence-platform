package com.pompom.creative.service;

import com.pompom.creative.domain.PublicationAttempt;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderQaResult;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationAttemptRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import com.pompom.creative.postrender.PostRenderDecision;
import com.pompom.creative.postrender.PostRenderEvaluation;
import com.pompom.creative.postrender.PostRenderEvaluationRepository;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
  private final PublicationAttemptRepository publicationAttemptRepository;
  private final RenderAssetRepository renderAssetRepository;
  private final RenderQaResultRepository qaResultRepository;
  private final PostRenderEvaluationRepository postRenderEvaluationRepository;
  private final AssetLibraryManager assetLibraryManager;

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
    String idempotencyKey =
        publicationFingerprint(
            platform, asset.getSha256(), platformAccountId, title, caption, hashtags, isPrivate);
    Optional<PublicationJob> existing =
        publicationJobRepository.findByIdempotencyKey(idempotencyKey);
    if (existing.isPresent()) {
      return existing.get();
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
            .idempotencyKey(idempotencyKey)
            .title(title)
            .caption(caption)
            .hashtags(hashtags)
            .isPrivate(isPrivate)
            .queuedAt(Instant.now())
            .build();

    PublicationJob saved = publicationJobRepository.save(job);
    publicationAttemptRepository.save(PublicationAttempt.firstAttemptFor(saved.getId()));
    log.info("Publication durably queued: jobId={}", saved.getId());

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
    Optional<PostRenderEvaluation> canonical = postRenderEvaluationRepository == null
        ? Optional.empty()
        : postRenderEvaluationRepository.findTopByRenderAssetIdOrderByCreatedAtDesc(renderAssetId);
    if (canonical.isPresent()) {
      PostRenderEvaluation evaluation = canonical.get();
      if (evaluation.getOverallDecision() == PostRenderDecision.FAIL
          || evaluation.getOverallDecision() == PostRenderDecision.SYSTEM_ERROR) {
        throw new IllegalStateException("Post-render QA has not accepted this asset");
      }
      if (evaluation.getOverallDecision() == PostRenderDecision.HUMAN_REVIEW
          && !"APPROVED".equals(evaluation.getHumanDecision())) {
        throw new IllegalStateException("Required human review has not approved this asset");
      }
    } else {
      RenderQaResult qa = qaResultRepository.findTopByRenderAssetIdOrderByCreatedAtDesc(renderAssetId)
          .orElseThrow(() -> new IllegalStateException("Post-render QA evidence is missing"));
      if (qa.getDecision() != RenderQaResult.QaDecision.ACCEPT) {
        throw new IllegalStateException("Post-render QA has not accepted this asset");
      }
      if (Boolean.TRUE.equals(qa.getRequiresHumanReview()) && !"APPROVED".equals(qa.getHumanDecision())) {
        throw new IllegalStateException("Required human review has not approved this asset");
      }
    }
    return asset;
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

    // Once remote submission begins, local cancellation cannot truthfully imply remote removal.
    if (job.getStatus() == PublicationStatus.QUEUED) {
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

  private String publicationFingerprint(
      PlatformType platform,
      String assetSha256,
      String accountId,
      String title,
      String caption,
      String hashtags,
      Boolean isPrivate) {
    String normalized =
        String.join(
            "\n",
            platform.name(),
            assetSha256,
            accountId.trim(),
            value(title),
            value(caption),
            value(hashtags),
            String.valueOf(Boolean.TRUE.equals(isPrivate)));
    try {
      return java.util.HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256")
                  .digest(normalized.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception error) {
      throw new IllegalStateException("Unable to compute publication idempotency key", error);
    }
  }

  private String value(String value) {
    return value == null ? "" : value.trim();
  }
}
