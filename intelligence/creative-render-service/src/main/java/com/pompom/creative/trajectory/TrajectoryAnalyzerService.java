package com.pompom.creative.trajectory;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Service for detailed trajectory analysis of video performance. Analyzes velocity, acceleration,
 * waves, plateau, decay patterns.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class TrajectoryAnalyzerService {

  private final TrajectoryAnalysisRepository trajectoryRepo;
  private final VideoMetricsRepository metricsRepo;
  private final PublicationJobRepository publicationJobRepo;

  /** Perform detailed trajectory analysis. */
  @Transactional
  public TrajectoryAnalysis analyzeTrajectory(UUID publicationJobId) {
    log.info("Analyzing trajectory: jobId={}", publicationJobId);

    PublicationJob job =
        publicationJobRepo
            .findById(publicationJobId)
            .orElseThrow(() -> new IllegalArgumentException("Publication job not found"));

    List<VideoMetrics> timeline = metricsRepo.findMetricsTimeline(publicationJobId);

    if (timeline.isEmpty()) {
      throw new IllegalStateException("No metrics available for trajectory analysis");
    }

    TrajectoryAnalysis.TrajectoryAnalysisBuilder builder =
        TrajectoryAnalysis.builder().publicationJob(job).dataPointsCount(timeline.size());

    // Calculate velocity metrics
    calculateVelocityMetrics(timeline, builder);

    // Calculate acceleration metrics
    calculateAccelerationMetrics(timeline, builder);

    // Detect peak
    detectPeak(timeline, job.getCompletedAt(), builder);

    // Detect plateau
    detectPlateau(timeline, job.getCompletedAt(), builder);

    // Detect decay
    detectDecay(timeline, builder);

    // Detect waves
    detectWaves(timeline, job.getCompletedAt(), builder);

    // Analyze tail
    analyzeTail(timeline, builder);

    // Determine trajectory shape
    determineShape(timeline, builder);

    // Calculate confidence
    BigDecimal confidence = calculateConfidence(timeline);
    builder.analysisConfidence(confidence);

    TrajectoryAnalysis analysis = builder.build();
    analysis = trajectoryRepo.save(analysis);

    log.info(
        "Trajectory analyzed: jobId={}, shape={}, waves={}, confidence={}",
        publicationJobId,
        analysis.getTrajectoryShape(),
        analysis.getWaveCount(),
        confidence);

    return analysis;
  }

  /** Get trajectory analysis (if exists). */
  @Transactional(readOnly = true)
  public TrajectoryAnalysis getAnalysis(UUID publicationJobId) {
    return trajectoryRepo.findByPublicationJobId(publicationJobId).orElse(null);
  }

  /** Compare two trajectories for similarity. */
  @Transactional(readOnly = true)
  public BigDecimal compareSimilarity(UUID jobId1, UUID jobId2) {
    TrajectoryAnalysis t1 = getAnalysis(jobId1);
    TrajectoryAnalysis t2 = getAnalysis(jobId2);

    if (t1 == null || t2 == null) {
      return BigDecimal.ZERO;
    }

    // Simple similarity score based on key metrics
    BigDecimal similarity = BigDecimal.ZERO;
    int matchCount = 0;

    // Shape match (30% weight)
    if (t1.getTrajectoryShape() == t2.getTrajectoryShape()) {
      similarity = similarity.add(BigDecimal.valueOf(30));
    }

    // Velocity similarity (20% weight)
    if (t1.getVelocityFirst24H() != null && t2.getVelocityFirst24H() != null) {
      BigDecimal ratio =
          t1.getVelocityFirst24H()
              .min(t2.getVelocityFirst24H())
              .divide(
                  t1.getVelocityFirst24H().max(t2.getVelocityFirst24H()), 2, RoundingMode.HALF_UP);
      similarity = similarity.add(ratio.multiply(BigDecimal.valueOf(20)));
      matchCount++;
    }

    // Wave count similarity (20% weight)
    if (t1.getWaveCount() != null && t2.getWaveCount() != null) {
      int waveMin = Math.min(t1.getWaveCount(), t2.getWaveCount());
      int waveMax = Math.max(t1.getWaveCount(), t2.getWaveCount());
      if (waveMax > 0) {
        BigDecimal waveRatio =
            BigDecimal.valueOf(waveMin)
                .divide(BigDecimal.valueOf(waveMax), 2, RoundingMode.HALF_UP);
        similarity = similarity.add(waveRatio.multiply(BigDecimal.valueOf(20)));
      }
      matchCount++;
    }

    // Tail strength similarity (15% weight)
    if (t1.getTailStrength() != null && t2.getTailStrength() != null) {
      BigDecimal ratio =
          t1.getTailStrength()
              .min(t2.getTailStrength())
              .divide(t1.getTailStrength().max(t2.getTailStrength()), 2, RoundingMode.HALF_UP);
      similarity = similarity.add(ratio.multiply(BigDecimal.valueOf(15)));
      matchCount++;
    }

    // Plateau similarity (15% weight)
    if (t1.getPlateauDetected() != null && t2.getPlateauDetected() != null) {
      if (t1.getPlateauDetected().equals(t2.getPlateauDetected())) {
        similarity = similarity.add(BigDecimal.valueOf(15));
      }
      matchCount++;
    }

    return similarity;
  }

  // Private analysis methods

  private void calculateVelocityMetrics(
      List<VideoMetrics> timeline, TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    // First hour
    VideoMetrics first1h = findClosestMetrics(timeline, 60);
    if (first1h != null) {
      builder.velocityFirstHour(BigDecimal.valueOf(first1h.getViews()));
    }

    // First 6 hours
    VideoMetrics first6h = findClosestMetrics(timeline, 360);
    if (first6h != null) {
      builder.velocityFirst6H(
          BigDecimal.valueOf(first6h.getViews())
              .divide(BigDecimal.valueOf(6), 2, RoundingMode.HALF_UP));
    }

    // First 24 hours
    VideoMetrics first24h = findClosestMetrics(timeline, 1440);
    if (first24h != null) {
      builder.velocityFirst24H(
          BigDecimal.valueOf(first24h.getViews())
              .divide(BigDecimal.valueOf(24), 2, RoundingMode.HALF_UP));
    }

    // Day 1-7
    VideoMetrics day7 = findClosestMetrics(timeline, 7 * 24 * 60);
    if (day7 != null && first24h != null) {
      long viewsDiff = day7.getViews() - first24h.getViews();
      BigDecimal hours = BigDecimal.valueOf(6 * 24); // 6 days
      builder.velocityDay1To7(BigDecimal.valueOf(viewsDiff).divide(hours, 2, RoundingMode.HALF_UP));
    }

    // Day 7-30
    VideoMetrics day30 = findClosestMetrics(timeline, 30 * 24 * 60);
    if (day30 != null && day7 != null) {
      long viewsDiff = day30.getViews() - day7.getViews();
      BigDecimal hours = BigDecimal.valueOf(23 * 24); // 23 days
      builder.velocityDay7To30(
          BigDecimal.valueOf(viewsDiff).divide(hours, 2, RoundingMode.HALF_UP));
    }
  }

  private void calculateAccelerationMetrics(
      List<VideoMetrics> timeline, TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    VideoMetrics first1h = findClosestMetrics(timeline, 60);
    VideoMetrics first6h = findClosestMetrics(timeline, 360);
    VideoMetrics first24h = findClosestMetrics(timeline, 1440);
    VideoMetrics day7 = findClosestMetrics(timeline, 7 * 24 * 60);

    // 1h to 6h acceleration
    if (first1h != null && first6h != null) {
      BigDecimal vel1h = BigDecimal.valueOf(first1h.getViews());
      BigDecimal vel6h =
          BigDecimal.valueOf(first6h.getViews())
              .divide(BigDecimal.valueOf(6), 2, RoundingMode.HALF_UP);
      builder.acceleration1HTo6H(vel6h.subtract(vel1h));
    }

    // 6h to 24h acceleration
    if (first6h != null && first24h != null) {
      BigDecimal vel6h =
          BigDecimal.valueOf(first6h.getViews())
              .divide(BigDecimal.valueOf(6), 2, RoundingMode.HALF_UP);
      BigDecimal vel24h =
          BigDecimal.valueOf(first24h.getViews())
              .divide(BigDecimal.valueOf(24), 2, RoundingMode.HALF_UP);
      builder.acceleration6HTo24H(vel24h.subtract(vel6h));
    }

    // Day 1 to 7 acceleration
    if (first24h != null && day7 != null) {
      BigDecimal vel24h =
          BigDecimal.valueOf(first24h.getViews())
              .divide(BigDecimal.valueOf(24), 2, RoundingMode.HALF_UP);
      long viewsDiff = day7.getViews() - first24h.getViews();
      BigDecimal vel7d =
          BigDecimal.valueOf(viewsDiff).divide(BigDecimal.valueOf(6 * 24), 2, RoundingMode.HALF_UP);
      builder.accelerationDay1To7(vel7d.subtract(vel24h));
    }
  }

  private void detectPeak(
      List<VideoMetrics> timeline,
      Instant publishedAt,
      TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    long maxViews = 0;
    VideoMetrics peakMetrics = null;

    for (VideoMetrics metrics : timeline) {
      if (metrics.getViews() > maxViews) {
        maxViews = metrics.getViews();
        peakMetrics = metrics;
      }
    }

    if (peakMetrics != null) {
      builder.peakViews(maxViews);
      builder.peakTimestamp(peakMetrics.getCollectedAt());
      builder.peakDay(peakMetrics.getTimeSincePublishMinutes() / (24 * 60));

      long hoursToPeak = Duration.between(publishedAt, peakMetrics.getCollectedAt()).toHours();
      builder.timeToPeakHours((int) hoursToPeak);
    }
  }

  private void detectPlateau(
      List<VideoMetrics> timeline,
      Instant publishedAt,
      TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    if (timeline.size() < 3) return;

    // Find where growth rate drops below 5%
    for (int i = 2; i < timeline.size(); i++) {
      long prevViews = timeline.get(i - 1).getViews();
      long currentViews = timeline.get(i).getViews();

      if (prevViews > 0) {
        double growthRate = (double) (currentViews - prevViews) / prevViews;
        if (growthRate < 0.05) {
          builder.plateauDetected(true);
          builder.plateauTimestamp(timeline.get(i).getCollectedAt());
          builder.plateauDay(timeline.get(i).getTimeSincePublishMinutes() / (24 * 60));
          builder.plateauViews(currentViews);
          break;
        }
      }
    }
  }

  private void detectDecay(
      List<VideoMetrics> timeline, TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    if (timeline.size() < 3) return;

    // Check if views are declining in last 2-3 data points
    int declineCount = 0;
    BigDecimal totalDeclineRate = BigDecimal.ZERO;

    for (int i = timeline.size() - 1; i >= Math.max(1, timeline.size() - 3); i--) {
      long prevViews = timeline.get(i - 1).getViews();
      long currentViews = timeline.get(i).getViews();

      if (currentViews < prevViews) {
        declineCount++;
        BigDecimal declineRate =
            BigDecimal.valueOf(prevViews - currentViews)
                .divide(BigDecimal.valueOf(prevViews), 4, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100));
        totalDeclineRate = totalDeclineRate.add(declineRate);
      }
    }

    if (declineCount >= 2) {
      builder.decayDetected(true);
      builder.decayRate(
          totalDeclineRate.divide(BigDecimal.valueOf(declineCount), 2, RoundingMode.HALF_UP));
    }
  }

  private void detectWaves(
      List<VideoMetrics> timeline,
      Instant publishedAt,
      TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    List<WavePeak> peaks = new ArrayList<>();

    // Find local maxima
    for (int i = 1; i < timeline.size() - 1; i++) {
      long prev = timeline.get(i - 1).getViews();
      long current = timeline.get(i).getViews();
      long next = timeline.get(i + 1).getViews();

      if (current > prev && current > next) {
        peaks.add(new WavePeak(timeline.get(i).getTimeSincePublishMinutes() / (24 * 60), current));
      }
    }

    builder.waveCount(peaks.size());

    if (!peaks.isEmpty()) {
      builder.primaryWaveDay(peaks.get(0).day);
      builder.primaryWaveViews(peaks.get(0).views);
    }
    if (peaks.size() > 1) {
      builder.secondaryWaveDay(peaks.get(1).day);
      builder.secondaryWaveViews(peaks.get(1).views);
    }
    if (peaks.size() > 2) {
      builder.tertiaryWaveDay(peaks.get(2).day);
      builder.tertiaryWaveViews(peaks.get(2).views);
    }
  }

  private void analyzeTail(
      List<VideoMetrics> timeline, TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    VideoMetrics day7 = findClosestMetrics(timeline, 7 * 24 * 60);
    VideoMetrics finalMetrics = timeline.get(timeline.size() - 1);

    if (day7 != null && finalMetrics.getViews() > 0) {
      long tailViews = finalMetrics.getViews() - day7.getViews();
      BigDecimal tailStrength =
          BigDecimal.valueOf(tailViews)
              .divide(BigDecimal.valueOf(finalMetrics.getViews()), 4, RoundingMode.HALF_UP);
      builder.tailStrength(tailStrength);

      // Tail velocity
      long tailHours =
          (finalMetrics.getTimeSincePublishMinutes() - day7.getTimeSincePublishMinutes()) / 60;
      if (tailHours > 0) {
        BigDecimal tailVelocity =
            BigDecimal.valueOf(tailViews)
                .divide(BigDecimal.valueOf(tailHours), 2, RoundingMode.HALF_UP);
        builder.tailVelocity(tailVelocity);

        // Sustainability score (based on velocity maintenance)
        VideoMetrics day1 = findClosestMetrics(timeline, 24 * 60);
        if (day1 != null) {
          BigDecimal initialVelocity =
              BigDecimal.valueOf(day1.getViews())
                  .divide(BigDecimal.valueOf(24), 2, RoundingMode.HALF_UP);
          if (initialVelocity.compareTo(BigDecimal.ZERO) > 0) {
            BigDecimal sustainabilityRatio =
                tailVelocity.divide(initialVelocity, 2, RoundingMode.HALF_UP);
            BigDecimal sustainabilityScore =
                sustainabilityRatio.multiply(BigDecimal.valueOf(100)).min(BigDecimal.valueOf(100));
            builder.tailSustainabilityScore(sustainabilityScore);
          }
        }
      }
    }
  }

  private void determineShape(
      List<VideoMetrics> timeline, TrajectoryAnalysis.TrajectoryAnalysisBuilder builder) {
    if (timeline.size() < 3) {
      builder.trajectoryShape(TrajectoryAnalysis.TrajectoryShape.FLAT);
      builder.growthPattern("INSUFFICIENT_DATA");
      return;
    }

    // Analyze growth pattern
    long firstViews = timeline.get(0).getViews();
    long midViews = timeline.get(timeline.size() / 2).getViews();
    long lastViews = timeline.get(timeline.size() - 1).getViews();

    boolean hasGrowth = lastViews > firstViews * 1.5;
    boolean earlyGrowth = midViews > firstViews * 2;
    boolean lateGrowth = lastViews > midViews * 2;

    // Determine shape
    if (!hasGrowth) {
      builder.trajectoryShape(TrajectoryAnalysis.TrajectoryShape.FLAT);
      builder.growthPattern("MINIMAL_GROWTH");
    } else if (lateGrowth && !earlyGrowth) {
      builder.trajectoryShape(TrajectoryAnalysis.TrajectoryShape.HOCKEY_STICK);
      builder.growthPattern("DELAYED_EXPONENTIAL");
    } else if (earlyGrowth && !lateGrowth) {
      builder.trajectoryShape(TrajectoryAnalysis.TrajectoryShape.SPIKE_AND_PLATEAU);
      builder.growthPattern("EARLY_PEAK");
    } else if (earlyGrowth && lateGrowth) {
      builder.trajectoryShape(TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL);
      builder.growthPattern("SUSTAINED_EXPONENTIAL");
    } else {
      builder.trajectoryShape(TrajectoryAnalysis.TrajectoryShape.LINEAR);
      builder.growthPattern("STEADY_LINEAR");
    }
  }

  private BigDecimal calculateConfidence(List<VideoMetrics> timeline) {
    BigDecimal confidence = BigDecimal.valueOf(50);

    if (timeline.size() >= 6) {
      confidence = confidence.add(BigDecimal.valueOf(30));
    } else if (timeline.size() >= 4) {
      confidence = confidence.add(BigDecimal.valueOf(15));
    }

    boolean hasFinal = timeline.stream().anyMatch(m -> m.getIsFinal() != null && m.getIsFinal());
    if (hasFinal) {
      confidence = confidence.add(BigDecimal.valueOf(20));
    }

    return confidence.min(BigDecimal.valueOf(100));
  }

  private VideoMetrics findClosestMetrics(List<VideoMetrics> timeline, int targetMinutes) {
    return timeline.stream()
        .min(
            (a, b) ->
                Math.abs(a.getTimeSincePublishMinutes() - targetMinutes)
                    - Math.abs(b.getTimeSincePublishMinutes() - targetMinutes))
        .orElse(null);
  }

  private record WavePeak(int day, long views) {}
}
