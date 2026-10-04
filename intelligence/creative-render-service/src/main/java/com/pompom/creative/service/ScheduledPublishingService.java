package com.pompom.creative.service;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.ScheduledPublication;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.ScheduledPublicationRepository;
import com.pompom.creative.repository.RenderAssetRepository;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
            .timezone(timezone != null ? timezone : ZoneId.systemDefault().getId())
            .isExecuted(false)
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
    return schedulePublication(
        platform,
        renderAssetId,
        platformAccountId,
        title,
        caption,
        hashtags,
        isPrivate,
        scheduledAt.toInstant(),
        scheduledAt.getZone().getId());
  }

  /** Process scheduled publications. Runs every minute to check for due publications. */
  @Scheduled(cron = "0 * * * * *") // Every minute
  @Transactional
  public void processScheduledPublications() {
    log.debug("Processing scheduled publications");

    Instant now = Instant.now();
    List<ScheduledPublication> duePublications =
        scheduledPublicationRepository.findByIsExecutedFalseAndScheduledAtBefore(now);

    if (duePublications.isEmpty()) {
      log.debug("No due publications found");
      return;
    }

    log.info("Found {} due publications", duePublications.size());

    for (ScheduledPublication scheduled : duePublications) {
      try {
        executeScheduledPublication(scheduled);
      } catch (Exception e) {
        log.error("Failed to execute scheduled publication: id={}", scheduled.getId(), e);
      }
    }
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

    if (scheduled.getIsExecuted()) {
      log.warn("Cannot cancel already executed scheduled publication: id={}", scheduleId);
      return false;
    }

    scheduledPublicationRepository.delete(scheduled);
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

    if (scheduled.getIsExecuted()) {
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
}
