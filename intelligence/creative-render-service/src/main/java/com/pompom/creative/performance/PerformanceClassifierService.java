package com.pompom.creative.performance;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Service for classifying video performance into categories. Analyzes metrics timeline to determine
 * trajectory and pattern.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class PerformanceClassifierService {

  private final PerformanceClassificationRepository classificationRepo;
  private final VideoMetricsRepository metricsRepo;
  private final PublicationJobRepository publicationJobRepo;

  // Classification thresholds
  private static final long EARLY_REJECTION_THRESHOLD = 1000L; // <1K views in 24h
  private static final long WEAK_THRESHOLD = 5000L; // <5K final views
  private static final long MEDIUM_THRESHOLD = 20000L; // <20K final views
  private static final long BREAKOUT_THRESHOLD = 50000L; // >50K views
  private static final BigDecimal TAIL_STRENGTH_THRESHOLD =
      new BigDecimal("0.30"); // >30% views after day 7
  private static final BigDecimal HIGH_VELOCITY_THRESHOLD =
      new BigDecimal("2000"); // >2K views/hour in first 24h

  /**
   * Classify video performance based on collected metrics. Requires at least T+7D metrics for
   * accurate classification.
   */
  @Transactional
  public PerformanceClassification classifyVideo(UUID publicationJobId) {
    log.info("Classifying video performance: jobId={}", publicationJobId);

    PublicationJob job =
        publicationJobRepo
            .findById(publicationJobId)
            .orElseThrow(() -> new IllegalArgumentException("Publication job not found"));

    List<VideoMetrics> timeline = metricsRepo.findMetricsTimeline(publicationJobId);

    if (timeline.isEmpty()) {
      throw new IllegalStateException("No metrics available for classification");
    }

    // Calculate trajectory characteristics
    TrajectoryData trajectory = analyzeTrajectory(timeline);

    // Determine category
    PerformanceClassification.PerformanceCategory category =
        determineCategory(timeline, trajectory);

    // Calculate confidence
    BigDecimal confidence = calculateConfidence(timeline, category);

    // Build classification
    PerformanceClassification classification =
        PerformanceClassification.builder()
            .publicationJob(job)
            .category(category)
            .confidenceScore(confidence)
            .finalViews(trajectory.finalViews)
            .finalEngagementRate(trajectory.finalEngagementRate)
            .peakViews(trajectory.peakViews)
            .peakDay(trajectory.peakDay)
            .velocityScore(trajectory.velocity)
            .accelerationScore(trajectory.acceleration)
            .plateauDetected(trajectory.plateauDetected)
            .plateauDay(trajectory.plateauDay)
            .tailStrength(trajectory.tailStrength)
            .primaryWaveDay(trajectory.primaryWaveDay)
            .secondaryWaveDay(trajectory.secondaryWaveDay)
            .waveCount(trajectory.waveCount)
            .classificationReason(buildReason(category, trajectory))
            .build();

    classification = classificationRepo.save(classification);

    log.info(
        "Video classified: jobId={}, category={}, confidence={}, views={}",
        publicationJobId,
        category,
        confidence,
        trajectory.finalViews);

    return classification;
  }

  /** Get classification for a video (if exists). */
  @Transactional(readOnly = true)
  public PerformanceClassification getClassification(UUID publicationJobId) {
    return classificationRepo.findByPublicationJobId(publicationJobId).orElse(null);
  }

  /** Get all winners (top-tier performances). */
  @Transactional(readOnly = true)
  public List<PerformanceClassification> getWinners() {
    return classificationRepo.findWinners();
  }

  /** Get videos by category. */
  @Transactional(readOnly = true)
  public List<PerformanceClassification> getByCategory(
      PerformanceClassification.PerformanceCategory category) {
    return classificationRepo.findByCategory(category);
  }

  /** Analyze metrics timeline to extract trajectory characteristics. */
  private TrajectoryData analyzeTrajectory(List<VideoMetrics> timeline) {
    TrajectoryData data = new TrajectoryData();

    if (timeline.isEmpty()) {
      return data;
    }

    // Final metrics (last collection point)
    VideoMetrics finalMetrics = timeline.get(timeline.size() - 1);
    data.finalViews = finalMetrics.getViews();
    data.finalEngagementRate = finalMetrics.calculateEngagementRate();

    // Find peak
    long maxViews = 0;
    int peakIndex = 0;
    for (int i = 0; i < timeline.size(); i++) {
      long views = timeline.get(i).getViews();
      if (views > maxViews) {
        maxViews = views;
        peakIndex = i;
      }
    }
    data.peakViews = maxViews;
    data.peakDay = estimateDay(timeline.get(peakIndex).getTimeSincePublishMinutes());

    // Calculate velocity (views/hour in first 24h)
    VideoMetrics first24h = findClosestMetrics(timeline, 1440); // 24 hours
    if (first24h != null) {
      data.velocity =
          BigDecimal.valueOf(first24h.getViews())
              .divide(BigDecimal.valueOf(24), 2, RoundingMode.HALF_UP);
    }

    // Calculate acceleration (change in velocity between first 6h and 24h)
    VideoMetrics first6h = findClosestMetrics(timeline, 360); // 6 hours
    if (first6h != null && first24h != null) {
      BigDecimal velocity6h =
          BigDecimal.valueOf(first6h.getViews())
              .divide(BigDecimal.valueOf(6), 2, RoundingMode.HALF_UP);
      BigDecimal velocity24h = data.velocity;
      data.acceleration = velocity24h.subtract(velocity6h);
    }

    // Detect plateau (growth stops)
    data.plateauDetected = detectPlateau(timeline);
    if (data.plateauDetected) {
      data.plateauDay = findPlateauDay(timeline);
    }

    // Calculate tail strength (views after day 7 / total views)
    VideoMetrics day7 = findClosestMetrics(timeline, 7 * 24 * 60); // 7 days
    if (day7 != null && finalMetrics.getViews() > 0) {
      long viewsAfterDay7 = finalMetrics.getViews() - day7.getViews();
      data.tailStrength =
          BigDecimal.valueOf(viewsAfterDay7)
              .divide(BigDecimal.valueOf(finalMetrics.getViews()), 4, RoundingMode.HALF_UP);
    }

    // Detect waves
    List<Integer> waveDays = detectWaves(timeline);
    data.waveCount = waveDays.size();
    if (!waveDays.isEmpty()) {
      data.primaryWaveDay = waveDays.get(0);
      if (waveDays.size() > 1) {
        data.secondaryWaveDay = waveDays.get(1);
      }
    }

    return data;
  }

  /** Determine performance category based on trajectory. */
  private PerformanceClassification.PerformanceCategory determineCategory(
      List<VideoMetrics> timeline, TrajectoryData trajectory) {
    // EARLY_REJECTION: Failed within 24h
    VideoMetrics first24h = findClosestMetrics(timeline, 1440);
    if (first24h != null && first24h.getViews() < EARLY_REJECTION_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.EARLY_REJECTION;
    }

    // BREAKOUT: High velocity + high final views + has plateau
    if (trajectory.velocity != null
        && trajectory.velocity.compareTo(HIGH_VELOCITY_THRESHOLD) > 0
        && trajectory.finalViews > BREAKOUT_THRESHOLD
        && trajectory.plateauDetected) {
      return PerformanceClassification.PerformanceCategory.BREAKOUT;
    }

    // EVERGREEN_BREAKOUT: No plateau, sustained growth >50K views (must be checked after BREAKOUT)
    if (!trajectory.plateauDetected && trajectory.finalViews > BREAKOUT_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT;
    }

    // DELAYED_BREAKOUT: Low velocity early but high final views
    if (trajectory.velocity != null
        && trajectory.velocity.compareTo(HIGH_VELOCITY_THRESHOLD) < 0
        && trajectory.finalViews > BREAKOUT_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.DELAYED_BREAKOUT;
    }

    // MULTI_WAVE: Multiple growth waves detected
    if (trajectory.waveCount > 1 && trajectory.finalViews > MEDIUM_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.MULTI_WAVE;
    }

    // PERSISTENT_WINNER: High views + no plateau (but below breakout threshold)
    if (!trajectory.plateauDetected && trajectory.finalViews > MEDIUM_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.PERSISTENT_WINNER;
    }

    // LONG_TAIL: Strong tail performance (check before MEDIUM)
    if (trajectory.tailStrength != null
        && trajectory.tailStrength.compareTo(TAIL_STRENGTH_THRESHOLD) > 0
        && trajectory.finalViews >= WEAK_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.LONG_TAIL;
    }

    // STRONG_START: High velocity but plateaued
    if (trajectory.velocity != null
        && trajectory.velocity.compareTo(HIGH_VELOCITY_THRESHOLD) > 0
        && trajectory.plateauDetected) {
      return PerformanceClassification.PerformanceCategory.STRONG_START;
    }

    // WEAK: Low final views
    if (trajectory.finalViews < WEAK_THRESHOLD) {
      return PerformanceClassification.PerformanceCategory.WEAK;
    }

    // MEDIUM: Default category for average performance
    return PerformanceClassification.PerformanceCategory.MEDIUM;
  }

  /** Calculate classification confidence (0-100). */
  private BigDecimal calculateConfidence(
      List<VideoMetrics> timeline, PerformanceClassification.PerformanceCategory category) {
    // Base confidence on data completeness
    BigDecimal baseConfidence = BigDecimal.valueOf(50);

    // More data points = higher confidence
    if (timeline.size() >= 6) {
      baseConfidence = baseConfidence.add(BigDecimal.valueOf(20));
    } else if (timeline.size() >= 4) {
      baseConfidence = baseConfidence.add(BigDecimal.valueOf(10));
    }

    // Final metrics available = higher confidence
    boolean hasFinalMetrics =
        timeline.stream().anyMatch(m -> m.getIsFinal() != null && m.getIsFinal());
    if (hasFinalMetrics) {
      baseConfidence = baseConfidence.add(BigDecimal.valueOf(30));
    } else {
      baseConfidence = baseConfidence.add(BigDecimal.valueOf(15));
    }

    return baseConfidence.min(BigDecimal.valueOf(100));
  }

  /** Build human-readable classification reason. */
  private String buildReason(
      PerformanceClassification.PerformanceCategory category, TrajectoryData trajectory) {
    return String.format(
        "%s classification: %,d final views, velocity=%.0f views/hour, "
            + "tail strength=%.1f%%, waves=%d, plateau=%s",
        category,
        trajectory.finalViews,
        trajectory.velocity != null ? trajectory.velocity.doubleValue() : 0.0,
        trajectory.tailStrength != null
            ? trajectory.tailStrength.multiply(BigDecimal.valueOf(100)).doubleValue()
            : 0.0,
        trajectory.waveCount,
        trajectory.plateauDetected ? "yes" : "no");
  }

  // Helper methods

  private VideoMetrics findClosestMetrics(List<VideoMetrics> timeline, int targetMinutes) {
    return timeline.stream()
        .min(
            (a, b) ->
                Math.abs(a.getTimeSincePublishMinutes() - targetMinutes)
                    - Math.abs(b.getTimeSincePublishMinutes() - targetMinutes))
        .orElse(null);
  }

  private int estimateDay(int minutes) {
    return minutes / (24 * 60);
  }

  private boolean detectPlateau(List<VideoMetrics> timeline) {
    if (timeline.size() < 3) return false;

    // Check ONLY the last 2-3 intervals for flat growth (<5% increase)
    int flatCount = 0;
    int startIndex = Math.max(1, timeline.size() - 3); // Start from 3rd-to-last or index 1

    for (int i = timeline.size() - 1; i >= startIndex; i--) {
      long prevViews = timeline.get(i - 1).getViews();
      long currentViews = timeline.get(i).getViews();

      if (prevViews > 0) {
        double growthRate = (double) (currentViews - prevViews) / prevViews;
        if (growthRate <= 0.05) { // ≤5% growth = flat
          flatCount++;
        }
      }
    }

    // If at least 2 of the last intervals are flat, it's a plateau
    return flatCount >= 2;
  }

  private Integer findPlateauDay(List<VideoMetrics> timeline) {
    for (int i = 1; i < timeline.size(); i++) {
      long prevViews = timeline.get(i - 1).getViews();
      long currentViews = timeline.get(i).getViews();

      if (prevViews > 0) {
        double growthRate = (double) (currentViews - prevViews) / prevViews;
        if (growthRate < 0.05) {
          return estimateDay(timeline.get(i).getTimeSincePublishMinutes());
        }
      }
    }
    return null;
  }

  private List<Integer> detectWaves(List<VideoMetrics> timeline) {
    // Simplified wave detection: find local maxima
    List<Integer> waveDays = new java.util.ArrayList<>();

    for (int i = 1; i < timeline.size() - 1; i++) {
      long prev = timeline.get(i - 1).getViews();
      long current = timeline.get(i).getViews();
      long next = timeline.get(i + 1).getViews();

      // Local maximum
      if (current > prev && current > next) {
        waveDays.add(estimateDay(timeline.get(i).getTimeSincePublishMinutes()));
      }
    }

    return waveDays;
  }

  /** Internal data class for trajectory analysis. */
  private static class TrajectoryData {
    Long finalViews = 0L;
    BigDecimal finalEngagementRate = BigDecimal.ZERO;
    Long peakViews = 0L;
    Integer peakDay = 0;
    BigDecimal velocity = BigDecimal.ZERO;
    BigDecimal acceleration = BigDecimal.ZERO;
    Boolean plateauDetected = false;
    Integer plateauDay = null;
    BigDecimal tailStrength = BigDecimal.ZERO;
    Integer primaryWaveDay = null;
    Integer secondaryWaveDay = null;
    Integer waveCount = 0;
  }
}
