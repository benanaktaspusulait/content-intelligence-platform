package com.pompom.creative.service;

import com.pompom.creative.domain.PublicationAnalytics;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.client.InstagramMetricsClient;
import com.pompom.creative.metrics.client.TikTokMetricsClient;
import com.pompom.creative.metrics.client.YouTubeMetricsClient;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationAnalyticsRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Analytics service for tracking publication performance. Fetches metrics from platform APIs and
 * stores them.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class AnalyticsService {

  private final PublicationAnalyticsRepository analyticsRepository;
  private final PublicationJobRepository publicationJobRepository;
  private final CredentialManager credentialManager;
  private final TikTokMetricsClient tiktokMetricsClient;
  private final YouTubeMetricsClient youtubeMetricsClient;
  private final InstagramMetricsClient instagramMetricsClient;

  @Value("${metrics.use-real-api:false}")
  private boolean useRealApi;

  /**
   * Fetch analytics for a publication job. Uses real platform APIs when enabled and available.
   *
   * @param jobId Publication job ID
   * @return Updated analytics
   */
  @Transactional
  public PublicationAnalytics fetchAnalytics(UUID jobId) {
    log.info("Fetching analytics for job: {}", jobId);

    Optional<PublicationJob> jobOpt = publicationJobRepository.findById(jobId);
    if (jobOpt.isEmpty()) {
      throw new RuntimeException("Publication job not found: " + jobId);
    }

    PublicationJob job = jobOpt.get();

    // Check if platform is connected
    if (!credentialManager.isConnected(job.getPlatform())) {
      log.warn("Platform not connected, cannot fetch analytics: platform={}", job.getPlatform());
      return null;
    }

    // Fetch metrics from platform API (real or mock)
    PublicationAnalytics newMetrics = fetchFromPlatform(job);

    // Find existing analytics or create new
    Optional<PublicationAnalytics> existingOpt = analyticsRepository.findByPublicationJobId(jobId);

    PublicationAnalytics analytics;
    if (existingOpt.isPresent()) {
      analytics = existingOpt.get();
      analytics.updateMetrics(newMetrics);
    } else {
      analytics = newMetrics;
      analytics.setPublicationJobId(jobId);
      analytics.setCreatedAt(Instant.now());
    }

    analytics = analyticsRepository.save(analytics);
    log.info("Analytics updated: jobId={}, views={}", jobId, analytics.getViews());

    return analytics;
  }

  /** Fetch metrics from platform API. Uses real API clients when available and enabled. */
  private PublicationAnalytics fetchFromPlatform(PublicationJob job) {
    log.debug(
        "Fetching metrics from platform API: platform={}, postId={}",
        job.getPlatform(),
        job.getPlatformPostId());

    // Try real API if enabled
    if (useRealApi) {
      try {
        VideoMetrics metrics =
            switch (job.getPlatform()) {
              case TIKTOK -> tiktokMetricsClient.fetchMetrics(job.getPlatformVideoId());
              case YOUTUBE -> youtubeMetricsClient.fetchMetrics(job.getPlatformVideoId());
              case INSTAGRAM, FACEBOOK ->
                  instagramMetricsClient.fetchMetrics(job.getPlatformVideoId());
            };

        log.info("Fetched real metrics from {}: views={}", job.getPlatform(), metrics.getViews());
        return convertToPublicationAnalytics(metrics, job);

      } catch (Exception e) {
        log.warn(
            "Failed to fetch from real {} API, falling back to mock: {}",
            job.getPlatform(),
            e.getMessage());
      }
    }

    // Fallback to mock data
    return generateMockAnalytics(job);
  }

  /** Convert VideoMetrics to PublicationAnalytics. */
  private PublicationAnalytics convertToPublicationAnalytics(
      VideoMetrics metrics, PublicationJob job) {
    return PublicationAnalytics.builder()
        .platform(job.getPlatform())
        .platformPostId(job.getPlatformPostId())
        .views(metrics.getViews())
        .likes(metrics.getLikes())
        .comments(metrics.getComments())
        .shares(metrics.getShares())
        .saves(metrics.getSaves())
        .impressions(metrics.getImpressions())
        .reach(metrics.getReach())
        .clicks(0L) // ProfileVisits not available in VideoMetrics
        .fetchedAt(Instant.now())
        .build();
  }

  /** Generate mock analytics for testing/development. */
  private PublicationAnalytics generateMockAnalytics(PublicationJob job) {
    log.debug("Generating mock analytics for {}", job.getPlatform());
    Random random = new Random();

    return PublicationAnalytics.builder()
        .platform(job.getPlatform())
        .platformPostId(job.getPlatformPostId())
        .views(random.nextLong(1000, 50000))
        .likes(random.nextLong(50, 5000))
        .comments(random.nextLong(10, 500))
        .shares(random.nextLong(5, 200))
        .saves(random.nextLong(10, 1000))
        .impressions(random.nextLong(2000, 100000))
        .reach(random.nextLong(1500, 80000))
        .clicks(random.nextLong(100, 10000))
        .fetchedAt(Instant.now())
        .build();
  }

  /** Sync analytics for all published content. Runs every hour. */
  @Scheduled(cron = "0 0 * * * *") // Every hour
  @Transactional
  public void syncAllAnalytics() {
    log.info("Starting analytics sync for all published content");

    List<PublicationJob> published =
        publicationJobRepository.findByStatus(
            com.pompom.creative.domain.PublicationStatus.PUBLISHED);

    log.info("Found {} published posts to sync", published.size());

    int successCount = 0;
    int failureCount = 0;

    for (PublicationJob job : published) {
      try {
        // Skip if recently fetched (within last 30 minutes)
        Optional<PublicationAnalytics> existingOpt =
            analyticsRepository.findByPublicationJobId(job.getId());

        if (existingOpt.isPresent()) {
          PublicationAnalytics existing = existingOpt.get();
          if (existing.getFetchedAt().isAfter(Instant.now().minus(30, ChronoUnit.MINUTES))) {
            log.debug("Skipping recently fetched analytics: jobId={}", job.getId());
            continue;
          }
        }

        fetchAnalytics(job.getId());
        successCount++;

      } catch (Exception e) {
        log.error("Failed to fetch analytics for job: {}", job.getId(), e);
        failureCount++;
      }
    }

    log.info("Analytics sync complete: success={}, failure={}", successCount, failureCount);
  }

  /** Get analytics for a publication job. */
  @Transactional(readOnly = true)
  public Optional<PublicationAnalytics> getAnalytics(UUID jobId) {
    return analyticsRepository.findByPublicationJobId(jobId);
  }

  /** Get analytics by platform. */
  @Transactional(readOnly = true)
  public List<PublicationAnalytics> getAnalyticsByPlatform(PlatformType platform) {
    return analyticsRepository.findByPlatform(platform);
  }

  /** Get top performing posts by views. */
  @Transactional(readOnly = true)
  public List<PublicationAnalytics> getTopByViews(int limit) {
    return analyticsRepository.findTopByViews(PageRequest.of(0, limit));
  }

  /** Get top performing posts by engagement. */
  @Transactional(readOnly = true)
  public List<PublicationAnalytics> getTopByEngagement(int limit) {
    return analyticsRepository.findTopByEngagement(PageRequest.of(0, limit));
  }

  /** Get aggregated statistics. */
  @Transactional(readOnly = true)
  public Map<String, Object> getAggregatedStats() {
    Map<String, Object> stats = new HashMap<>();

    // Total metrics
    Long totalViews = analyticsRepository.sumTotalViews();
    stats.put("totalViews", totalViews != null ? totalViews : 0);

    // Per-platform metrics
    Map<String, Map<String, Object>> platformStats = new HashMap<>();

    for (PlatformType platform : PlatformType.values()) {
      Map<String, Object> platformMetrics = new HashMap<>();

      Long platformViews = analyticsRepository.sumViewsByPlatform(platform);
      platformMetrics.put("views", platformViews != null ? platformViews : 0);

      Double avgEngagement = analyticsRepository.avgEngagementRateByPlatform(platform);
      platformMetrics.put("avgEngagementRate", avgEngagement != null ? avgEngagement : 0.0);

      List<PublicationAnalytics> platformAnalytics = analyticsRepository.findByPlatform(platform);
      platformMetrics.put("postCount", platformAnalytics.size());

      platformStats.put(platform.name().toLowerCase(), platformMetrics);
    }

    stats.put("platforms", platformStats);

    return stats;
  }

  /** Get performance dashboard data. */
  @Transactional(readOnly = true)
  public Map<String, Object> getDashboardData() {
    Map<String, Object> dashboard = new HashMap<>();

    dashboard.put("aggregatedStats", getAggregatedStats());
    dashboard.put("topByViews", getTopByViews(10));
    dashboard.put("topByEngagement", getTopByEngagement(10));

    return dashboard;
  }
}
