package com.pompom.creative.metrics;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.metrics.client.PlatformMetricsClient;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import com.pompom.creative.websocket.dto.MetricsUpdateEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Service for collecting video metrics from platform APIs. Scheduled to run every 5 minutes to
 * check for due collection jobs.
 */
@Service
@Slf4j
public class MetricsCollectorService {

  private final MetricsCollectionJobRepository collectionJobRepo;
  private final JdbcMetricsCollectionClaimRepository claimRepository;
  private final PerformanceObservationPublisher observationPublisher;
  private final VideoMetricsRepository metricsRepo;
  private final PublicationJobRepository publicationJobRepo;
  private final List<PlatformMetricsClient> metricsClients;
  private final WebSocketEventPublisher webSocketPublisher;

  @Value("${metrics.use-real-api:false}")
  private boolean useRealApi;

  // Map of platform clients for easy lookup
  private Map<PlatformType, PlatformMetricsClient> clientsByPlatform;

  @Autowired
  public MetricsCollectorService(
      MetricsCollectionJobRepository collectionJobRepo,
      JdbcMetricsCollectionClaimRepository claimRepository,
      PerformanceObservationPublisher observationPublisher,
      VideoMetricsRepository metricsRepo,
      PublicationJobRepository publicationJobRepo,
      List<PlatformMetricsClient> metricsClients,
      WebSocketEventPublisher webSocketPublisher) {
    this.collectionJobRepo = collectionJobRepo;
    this.claimRepository = claimRepository;
    this.observationPublisher = observationPublisher;
    this.metricsRepo = metricsRepo;
    this.publicationJobRepo = publicationJobRepo;
    this.metricsClients = metricsClients;
    this.webSocketPublisher = webSocketPublisher;
  }

  /** Compatibility constructor for direct service tests that do not exercise scheduled claims. */
  public MetricsCollectorService(
      MetricsCollectionJobRepository collectionJobRepo,
      VideoMetricsRepository metricsRepo,
      PublicationJobRepository publicationJobRepo,
      List<PlatformMetricsClient> metricsClients,
      WebSocketEventPublisher webSocketPublisher) {
    this(
        collectionJobRepo,
        null,
        null,
        metricsRepo,
        publicationJobRepo,
        metricsClients,
        webSocketPublisher);
  }

  @jakarta.annotation.PostConstruct
  public void init() {
    clientsByPlatform =
        metricsClients.stream()
            .collect(Collectors.toMap(PlatformMetricsClient::getPlatform, Function.identity()));
    log.info("Initialized metrics clients for platforms: {}", clientsByPlatform.keySet());
  }

  // Collection points: Strategic decision #5 - expanded checkpoints
  // T+15m, T+30m, T+60m, T+90m, T+120m, T+3h, T+6h, T+12h, T+24h, T+48h, T+7d, T+30d
  private static final List<CollectionPoint> COLLECTION_POINTS =
      List.of(
          new CollectionPoint("T+15M", 15),
          new CollectionPoint("T+30M", 30),
          new CollectionPoint("T+1H", 60),
          new CollectionPoint("T+90M", 90),
          new CollectionPoint("T+2H", 120),
          new CollectionPoint("T+3H", 180),
          new CollectionPoint("T+6H", 360),
          new CollectionPoint("T+12H", 720),
          new CollectionPoint("T+24H", 1440),
          new CollectionPoint("T+48H", 2880),
          new CollectionPoint("T+7D", 10080),
          new CollectionPoint("T+30D", 43200));

  /** Schedule collection jobs for a newly published video. */
  @Transactional
  public List<MetricsCollectionJob> scheduleCollection(UUID publicationJobId) {
    log.info("Scheduling metrics collection for publication job: {}", publicationJobId);

    PublicationJob job =
        publicationJobRepo
            .findById(publicationJobId)
            .orElseThrow(
                () ->
                    new IllegalArgumentException("Publication job not found: " + publicationJobId));

    if (job.getCompletedAt() == null) {
      throw new IllegalStateException("Cannot schedule collection for unpublished job");
    }

    Instant publishedAt = job.getCompletedAt();

    return COLLECTION_POINTS.stream()
        .map(
            point -> {
              MetricsCollectionJob collectionJob =
                  MetricsCollectionJob.builder()
                      .publicationJob(job)
                      .collectionPoint(point.name())
                      .scheduledAt(publishedAt.plus(Duration.ofMinutes(point.minutes())))
                      .status(MetricsCollectionJob.JobStatus.PENDING)
                      .retryCount(0)
                      .maxRetries(3)
                      .build();

              return collectionJobRepo.save(collectionJob);
            })
        .toList();
  }

  /** Process due collection jobs (runs every 5 minutes). */
  @Scheduled(cron = "0 */5 * * * *") // Every 5 minutes
  public void processDueJobs() {
    if (claimRepository == null) {
      throw new IllegalStateException("Durable metrics claim repository is not configured");
    }
    Instant now = Instant.now();
    String leaseOwner = "metrics-" + UUID.randomUUID();
    List<UUID> claimedIds =
        claimRepository.claimDueJobs(leaseOwner, now, now.plus(Duration.ofMinutes(10)), 25);

    if (claimedIds.isEmpty()) {
      log.debug("No due metrics collection jobs");
      return;
    }

    log.info("Processing {} claimed metrics collection jobs", claimedIds.size());

    for (UUID jobId : claimedIds) {
      MetricsCollectionJob job = collectionJobRepo.findById(jobId).orElse(null);
      if (job == null) {
        continue;
      }
      try {
        collectMetrics(job);
      } catch (Exception e) {
        log.error("Failed to collect metrics for job: {}", job.getId(), e);
        handleFailure(job, e.getMessage());
      }
    }
  }

  /** Collect metrics for a specific job. */
  @Transactional
  public VideoMetrics collectMetrics(MetricsCollectionJob job) {
    log.info("Collecting metrics: job={}, point={}", job.getId(), job.getCollectionPoint());

    job.setStatus(MetricsCollectionJob.JobStatus.IN_PROGRESS);
    job.setExecutedAt(Instant.now());
    collectionJobRepo.save(job);

    PublicationJob pubJob = job.getPublicationJob();

    // Calculate time since publish
    long minutesSincePublish = Duration.between(pubJob.getCompletedAt(), Instant.now()).toMinutes();

    // Collect from platform API (mock for now)
    VideoMetrics metrics =
        collectFromPlatform(
            pubJob.getPlatform(), pubJob.getPlatformPostId(), (int) minutesSincePublish);

    metrics.setPublicationJob(pubJob);
    metrics.setTimeSincePublishMinutes((int) minutesSincePublish);
    metrics.setCollectionSource("API");
    metrics.setIsFinal("T+30D".equals(job.getCollectionPoint()));

    metrics = metricsRepo.save(metrics);
    if (observationPublisher != null) {
      observationPublisher.publish(pubJob, job, metrics);
    }

    job.setStatus(MetricsCollectionJob.JobStatus.COMPLETED);
    job.setCollectedMetrics(metrics);
    clearLease(job);
    collectionJobRepo.save(job);

    log.info(
        "Metrics collected: job={}, views={}, likes={}",
        job.getId(),
        metrics.getViews(),
        metrics.getLikes());

    // Publish WebSocket event
    publishMetricsUpdateEvent(pubJob, job.getCollectionPoint(), metrics);

    return metrics;
  }

  /** Manual metrics entry (fallback when API unavailable). */
  @Transactional
  public VideoMetrics recordManualMetrics(
      UUID publicationJobId,
      Long views,
      Long likes,
      Long comments,
      Long shares,
      Integer minutesSincePublish) {
    log.info("Recording manual metrics: job={}, views={}", publicationJobId, views);

    PublicationJob job =
        publicationJobRepo
            .findById(publicationJobId)
            .orElseThrow(() -> new IllegalArgumentException("Publication job not found"));

    VideoMetrics metrics =
        VideoMetrics.builder()
            .publicationJob(job)
            .platform(job.getPlatform())
            .platformVideoId(job.getPlatformPostId())
            .views(views)
            .likes(likes)
            .comments(comments)
            .shares(shares)
            .collectedAt(Instant.now())
            .timeSincePublishMinutes(minutesSincePublish)
            .collectionSource("MANUAL_ENTRY")
            .build();

    return metricsRepo.save(metrics);
  }

  /** Get metrics timeline for a video. */
  @Transactional(readOnly = true)
  public List<VideoMetrics> getMetricsTimeline(UUID publicationJobId) {
    return metricsRepo.findMetricsTimeline(publicationJobId);
  }

  /**
   * Collect metrics from the configured platform API. Unavailable evidence remains unavailable;
   * production persistence never receives generated fallback values.
   */
  private VideoMetrics collectFromPlatform(
      PlatformType platform, String platformVideoId, int minutesSincePublish) {
    log.debug(
        "Collecting from {}: videoId={}, age={}min",
        platform,
        platformVideoId,
        minutesSincePublish);

    if (!useRealApi) {
      throw new IllegalStateException("Platform metrics API collection is disabled");
    }
    PlatformMetricsClient client = clientsByPlatform.get(platform);
    if (client == null) {
      throw new IllegalStateException("No metrics client is configured for " + platform);
    }
    try {
      VideoMetrics metrics = client.fetchMetrics(platformVideoId);
      log.info("Metrics collected from real {} API: views={}", platform, metrics.getViews());
      return metrics;
    } catch (Exception error) {
      throw new IllegalStateException("Platform metrics are unavailable for " + platform, error);
    }
  }

  /** Handle collection failure. */
  private void handleFailure(MetricsCollectionJob job, String errorMessage) {
    job.setStatus(MetricsCollectionJob.JobStatus.FAILED);
    job.setErrorMessage(errorMessage);
    job.setRetryCount(job.getRetryCount() + 1);
    clearLease(job);
    collectionJobRepo.save(job);

    log.warn(
        "Metrics collection failed: job={}, retry={}/{}, error={}",
        job.getId(),
        job.getRetryCount(),
        job.getMaxRetries(),
        errorMessage);
  }

  private void clearLease(MetricsCollectionJob job) {
    job.setLeaseOwner(null);
    job.setLeaseExpiresAt(null);
  }

  /** Publish WebSocket metrics update event. */
  private void publishMetricsUpdateEvent(
      PublicationJob publicationJob, String collectionPoint, VideoMetrics metrics) {
    try {
      MetricsUpdateEvent event =
          MetricsUpdateEvent.builder()
              .type(MetricsUpdateEvent.EventType.METRICS_COLLECTED)
              .publicationJobId(publicationJob.getId())
              .platform(publicationJob.getPlatform())
              .platformVideoId(publicationJob.getPlatformPostId())
              .collectionPoint(collectionPoint)
              .views(metrics.getViews())
              .likes(metrics.getLikes())
              .comments(metrics.getComments())
              .shares(metrics.getShares())
              .engagementRate(metrics.calculateEngagementRate())
              .viralityScore(metrics.calculateViralityScore())
              .build();

      webSocketPublisher.publishMetricsUpdate(event);
    } catch (Exception e) {
      log.warn("Failed to publish WebSocket metrics event: {}", e.getMessage());
    }
  }

  private record CollectionPoint(String name, int minutes) {}
}
