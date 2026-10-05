package com.pompom.creative.service;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.ScheduleStatus;
import com.pompom.creative.domain.ScheduledPublication;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.ScheduledPublicationRepository;
import com.pompom.creative.worker.ScheduledPublicationClaimRepository;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Scheduled publishing service. Manages scheduled publications and executes them at scheduled time.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class ScheduledPublishingService {

  private final ScheduledPublicationRepository scheduledPublicationRepository;
  private final PublicationService publicationService;
  private final RenderAssetRepository renderAssetRepository;
  private final AssetLibraryManager assetLibraryManager;
  private final PublicationJobRepository publicationJobRepository;
  private final ScheduledPublicationClaimRepository claimRepository;
  private final String leaseOwner = "schedule-worker-" + UUID.randomUUID();

  @Value("${pompom.publication.scheduler.batch-size:20}")
  private int batchSize;

  @Value("${pompom.publication.scheduler.lease-duration:PT2M}")
  private Duration leaseDuration;

  /**
   * Schedule a publication for future execution.
   *
   * @param platform Target platform
   * @param renderAssetId canonical render asset identity
   * @param platformAccountId explicit target platform account
   * @param title Video title
   * @param caption Video caption
   * @param hashtags Hashtags
   * @param isPrivate Whether video should be private
   * @param scheduledAt When to publish (Instant)
   * @param timezone Timezone for scheduling
   * @return Scheduled publication
   */
  @Transactional
  public ScheduledPublication schedulePublication(
      PlatformType platform,
      UUID renderAssetId,
      String platformAccountId,
      String title,
      String caption,
      String hashtags,
      Boolean isPrivate,
      Instant scheduledAt,
      String timezone) {
    log.info(
        "Scheduling publication: platform={}, scheduledAt={}, timezone={}",
        platform,
        scheduledAt,
        timezone);

    // Validate scheduled time is in future
    if (scheduledAt.isBefore(Instant.now())) {
      throw new IllegalArgumentException("Scheduled time must be in the future");
    }
    if (platformAccountId == null || platformAccountId.isBlank()) {
      throw new IllegalArgumentException("platformAccountId is required");
    }
    ZoneId resolvedZone = ZoneId.of(timezone != null ? timezone : "UTC");
    RenderAsset asset =
        renderAssetRepository
            .findById(renderAssetId)
            .orElseThrow(() -> new IllegalArgumentException("Render asset not found"));

    ScheduledPublication scheduled =
        ScheduledPublication.builder()
            .platform(platform)
            .videoPath(assetLibraryManager.resolveStoredPath(asset).toString())
            .renderAsset(asset)
            .platformAccountId(platformAccountId)
            .title(title)
            .caption(caption)
            .hashtags(hashtags)
            .isPrivate(isPrivate)
            .scheduledAt(scheduledAt)
            .timezone(resolvedZone.getId())
            .isExecuted(false)
            .scheduleStatus(ScheduleStatus.SCHEDULED)
            .build();

    ScheduledPublication saved = scheduledPublicationRepository.save(scheduled);

    log.info("Publication scheduled: id={}, scheduledAt={}", saved.getId(), scheduledAt);

    return saved;
  }

  /** Schedule publication using ZonedDateTime. */
  @Transactional
  public ScheduledPublication schedulePublication(
      PlatformType platform,
      UUID renderAssetId,
      String platformAccountId,
      String title,
      String caption,
      String hashtags,
      Boolean isPrivate,
      ZonedDateTime scheduledAt) {
    ScheduledPublication scheduled =
        schedulePublication(
            platform,
            renderAssetId,
            platformAccountId,
            title,
            caption,
            hashtags,
            isPrivate,
            scheduledAt.toInstant(),
            scheduledAt.getZone().getId());
    scheduled.setOriginalLocalTime(scheduledAt.toLocalDateTime());
    return scheduledPublicationRepository.save(scheduled);
  }

  /** Process scheduled publications. Runs every minute to check for due publications. */
  @Scheduled(cron = "0 * * * * *") // Every minute
  public void processScheduledPublications() {
    log.debug("Processing scheduled publications");

    Instant now = Instant.now();
    Duration effectiveLeaseDuration = leaseDuration == null ? Duration.ofMinutes(2) : leaseDuration;
    List<UUID> claimed =
        claimRepository.claimDueSchedules(leaseOwner, now, now.plus(effectiveLeaseDuration), batchSize);

    if (claimed.isEmpty()) {
      log.debug("No due publications found");
      return;
    }

    log.info("Claimed {} due publications", claimed.size());

    for (UUID scheduleId : claimed) {
      try {
        executeClaimedPublication(scheduleId, leaseOwner);
      } catch (Exception e) {
        log.error("Failed to execute scheduled publication: id={}", scheduleId, e);
      }
    }
  }

  @Transactional
  public void executeClaimedPublication(UUID scheduleId, String owner) {
    ScheduledPublication scheduled =
        scheduledPublicationRepository.findById(scheduleId).orElseThrow();
    if (scheduled.getScheduleStatus() != ScheduleStatus.CLAIMED
        || !owner.equals(scheduled.getLeaseOwner())) {
      throw new IllegalStateException("Scheduled publication lease is not owned by caller");
    }
    executeScheduledPublication(scheduled);
  }

  /** Execute a scheduled publication. */
  @Transactional
  public void executeScheduledPublication(ScheduledPublication scheduled) {
    log.info(
        "Executing scheduled publication: id={}, platform={}",
        scheduled.getId(),
        scheduled.getPlatform());

    // Queue publication
    PublicationJob job =
        publicationService.queuePublication(
            scheduled.getPlatform(),
            scheduled.getRenderAsset().getId(),
            scheduled.getPlatformAccountId(),
            scheduled.getTitle(),
            scheduled.getCaption(),
            scheduled.getHashtags(),
            scheduled.getIsPrivate());

    // Mark as executed
    scheduled.markExecuted(job.getId());
    scheduledPublicationRepository.save(scheduled);

    log.info(
        "Scheduled publication executed: scheduleId={}, jobId={}", scheduled.getId(), job.getId());
  }

  /** Get scheduled publication by ID. */
  @Transactional(readOnly = true)
  public Optional<ScheduledPublication> getScheduled(UUID scheduleId) {
    return scheduledPublicationRepository.findById(scheduleId);
  }

  /** Get all scheduled publications. */
  @Transactional(readOnly = true)
  public List<ScheduledPublication> getAllScheduled() {
    return scheduledPublicationRepository.findAllByOrderByScheduledAtAsc();
  }

  /** Get pending scheduled publications. */
  @Transactional(readOnly = true)
  public List<ScheduledPublication> getPendingScheduled() {
    return scheduledPublicationRepository.findByIsExecutedFalse();
  }

  /** Get pending scheduled publications for platform. */
  @Transactional(readOnly = true)
  public List<ScheduledPublication> getPendingScheduledByPlatform(PlatformType platform) {
    return scheduledPublicationRepository.findByPlatformAndIsExecutedFalse(platform);
  }

  /** Cancel scheduled publication. */
  @Transactional
  public boolean cancelScheduled(UUID scheduleId) {
    Optional<ScheduledPublication> scheduledOpt =
        scheduledPublicationRepository.findById(scheduleId);

    if (scheduledOpt.isEmpty()) {
      return false;
    }

    ScheduledPublication scheduled = scheduledOpt.get();

    if (scheduled.getScheduleStatus() != ScheduleStatus.SCHEDULED) {
      log.warn("Cannot cancel already executed scheduled publication: id={}", scheduleId);
      return false;
    }

    scheduled.setScheduleStatus(ScheduleStatus.CANCELLED);
    scheduled.setCancellationRequestedAt(Instant.now());
    scheduledPublicationRepository.save(scheduled);
    log.info("Scheduled publication cancelled: id={}", scheduleId);

    return true;
  }

  /** Update scheduled time. */
  @Transactional
  public boolean reschedule(UUID scheduleId, Instant newScheduledAt) {
    Optional<ScheduledPublication> scheduledOpt =
        scheduledPublicationRepository.findById(scheduleId);

    if (scheduledOpt.isEmpty()) {
      return false;
    }

    ScheduledPublication scheduled = scheduledOpt.get();

    if (scheduled.getScheduleStatus() != ScheduleStatus.SCHEDULED) {
      log.warn("Cannot reschedule already executed publication: id={}", scheduleId);
      return false;
    }

    if (newScheduledAt.isBefore(Instant.now())) {
      throw new IllegalArgumentException("New scheduled time must be in the future");
    }

    scheduled.setScheduledAt(newScheduledAt);
    scheduledPublicationRepository.save(scheduled);

    log.info("Publication rescheduled: id={}, newTime={}", scheduleId, newScheduledAt);

    return true;
  }

  /** Get statistics. */
  @Transactional(readOnly = true)
  public java.util.Map<String, Long> getStatistics() {
    return java.util.Map.of(
        "pending", scheduledPublicationRepository.countByIsExecutedFalse(),
        "executed", scheduledPublicationRepository.countByIsExecutedTrue(),
        "total", scheduledPublicationRepository.count());
  }

  @Scheduled(fixedDelayString = "${pompom.publication.scheduler.reconcile-interval:30s}")
  @Transactional
  public void reconcileEnqueuedSchedules() {
    for (ScheduledPublication scheduled :
        scheduledPublicationRepository.findByScheduleStatus(ScheduleStatus.ENQUEUED)) {
      if (scheduled.getPublicationJobId() == null) {
        continue;
      }
      publicationJobRepository
          .findById(scheduled.getPublicationJobId())
          .ifPresent(
              job -> {
                if (job.getStatus() == com.pompom.creative.domain.PublicationStatus.PUBLISHED) {
                  scheduled.setScheduleStatus(ScheduleStatus.PUBLICATION_SUCCEEDED);
                  scheduledPublicationRepository.save(scheduled);
                } else if (job.getStatus() == com.pompom.creative.domain.PublicationStatus.FAILED) {
                  scheduled.setScheduleStatus(ScheduleStatus.PUBLICATION_FAILED);
                  scheduledPublicationRepository.save(scheduled);
                }
              });
    }
  }
}
