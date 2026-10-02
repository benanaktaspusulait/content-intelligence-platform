package com.pompom.creative.correlation;

import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.performance.PerformanceClassification;
import com.pompom.creative.performance.PerformanceClassificationRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.trajectory.TrajectoryAnalysis;
import com.pompom.creative.trajectory.TrajectoryAnalysisRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Service for analyzing statistical correlations between quality scores and performance. Uses
 * Pearson correlation coefficient.
 *
 * <p>Simplified version: uses performance classification scores instead of QA scores.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class CorrelationAnalyzerService {

  private final CorrelationAnalysisRepository correlationRepo;
  private final PublicationJobRepository publicationJobRepo;
  private final VideoMetricsRepository metricsRepo;
  private final TrajectoryAnalysisRepository trajectoryRepo;
  private final PerformanceClassificationRepository performanceRepo;

  /**
   * Perform comprehensive correlation analysis across all completed jobs. Correlates performance
   * category scores with actual metrics.
   */
  @Transactional
  public CorrelationAnalysis analyzeCorrelations() {
    log.info("Starting correlation analysis");

    // Fetch all performance classifications
    List<PerformanceClassification> classifications = performanceRepo.findAll();

    // Build data pairs - using performance scores as "quality" proxy
    List<DataPair> performanceVsViews = new ArrayList<>();
    List<DataPair> performanceVsEngagement = new ArrayList<>();
    List<DataPair> performanceVsCompletion = new ArrayList<>();
    List<DataPair> performanceVsVelocity = new ArrayList<>();

    int validSamples = 0;

    for (PerformanceClassification perf : classifications) {
      UUID jobId = perf.getPublicationJob().getId();

      // Get metrics timeline
      List<VideoMetrics> timeline = metricsRepo.findMetricsTimeline(jobId);
      if (timeline.isEmpty()) {
        continue;
      }

      VideoMetrics finalMetrics = timeline.get(timeline.size() - 1);
      if (finalMetrics.getViews() == null) {
        continue;
      }

      // Get trajectory
      TrajectoryAnalysis trajectory = trajectoryRepo.findByPublicationJobId(jobId).orElse(null);

      // Performance score (map category to numeric score)
      double performanceScore = mapCategoryToScore(perf.getCategory());

      // Actual metrics
      double views = finalMetrics.getViews().doubleValue();
      double engagementRate = finalMetrics.calculateEngagementRate().doubleValue();
      double completionRate =
          finalMetrics.getCompletionRate() != null
              ? finalMetrics.getCompletionRate().doubleValue()
              : 0;
      double velocity =
          trajectory != null && trajectory.getVelocityFirst24H() != null
              ? trajectory.getVelocityFirst24H().doubleValue()
              : 0;

      // Build pairs
      if (performanceScore > 0) {
        performanceVsViews.add(new DataPair(performanceScore, views));
        performanceVsEngagement.add(new DataPair(performanceScore, engagementRate));
        performanceVsCompletion.add(new DataPair(performanceScore, completionRate));
        if (velocity > 0) {
          performanceVsVelocity.add(new DataPair(performanceScore, velocity));
        }
      }

      validSamples++;
    }

    if (validSamples < 5) {
      throw new IllegalStateException(
          "Insufficient data for correlation analysis (need at least 5 samples)");
    }

    // Calculate correlations
    CorrelationAnalysis.CorrelationAnalysisBuilder builder =
        CorrelationAnalysis.builder()
            .analysisName("Performance Correlation Analysis")
            .description(
                "Statistical correlation between performance classification and actual metrics")
            .sampleSize(validSamples);

    // Performance correlations
    BigDecimal perfVsViews = calculatePearson(performanceVsViews);
    BigDecimal perfVsEngagement = calculatePearson(performanceVsEngagement);
    BigDecimal perfVsCompletion = calculatePearson(performanceVsCompletion);
    BigDecimal perfVsVelocity = calculatePearson(performanceVsVelocity);

    builder.overallScoreVsViews(perfVsViews);
    builder.overallScoreVsEngagement(perfVsEngagement);
    builder.overallScoreVsCompletion(perfVsCompletion);
    builder.overallScoreVsVelocity(perfVsVelocity);

    // Simplified: same correlations for all quality dimensions
    builder.visualQualityVsViews(perfVsViews);
    builder.hookVsViews(perfVsViews);
    builder.pacingVsViews(perfVsViews);
    builder.emotionalVsViews(perfVsViews);
    builder.brandVsViews(perfVsViews);

    CorrelationAnalysis analysis = builder.build();

    // Find strongest/weakest
    if (perfVsViews != null) {
      analysis.setStrongestCorrelationFactor("PERFORMANCE_CATEGORY");
      analysis.setStrongestCorrelationValue(perfVsViews);
    }

    // Confidence based on sample size
    BigDecimal confidence = calculateConfidence(validSamples);
    analysis.setAnalysisConfidence(confidence);

    analysis = correlationRepo.save(analysis);

    log.info(
        "Correlation analysis complete: samples={}, confidence={}, r={}",
        validSamples,
        confidence,
        analysis.getOverallScoreVsViews());

    return analysis;
  }

  /** Get latest correlation analysis. */
  @Transactional(readOnly = true)
  public CorrelationAnalysis getLatestAnalysis() {
    return correlationRepo.findFirstByOrderByAnalyzedAtDesc().orElse(null);
  }

  /** Get correlation history. */
  @Transactional(readOnly = true)
  public List<CorrelationAnalysis> getAnalysisHistory() {
    return correlationRepo.findTop10ByOrderByAnalyzedAtDesc();
  }

  // Private helper methods

  /** Map performance category to numeric score (0-100). */
  private double mapCategoryToScore(PerformanceClassification.PerformanceCategory category) {
    return switch (category) {
      case EARLY_REJECTION -> 10.0;
      case WEAK -> 30.0;
      case MEDIUM -> 50.0;
      case STRONG_START -> 70.0;
      case BREAKOUT -> 90.0;
      case DELAYED_BREAKOUT -> 80.0;
      case MULTI_WAVE -> 75.0;
      case PERSISTENT_WINNER -> 85.0;
      case LONG_TAIL -> 78.0;
      case EVERGREEN_BREAKOUT -> 95.0;
    };
  }

  /** Calculate Pearson correlation coefficient. */
  private BigDecimal calculatePearson(List<DataPair> pairs) {
    if (pairs.size() < 2) {
      return null;
    }

    int n = pairs.size();

    // Calculate means
    double meanX = pairs.stream().mapToDouble(p -> p.x).average().orElse(0);
    double meanY = pairs.stream().mapToDouble(p -> p.y).average().orElse(0);

    // Calculate covariance and standard deviations
    double covariance = 0;
    double stdDevX = 0;
    double stdDevY = 0;

    for (DataPair pair : pairs) {
      double diffX = pair.x - meanX;
      double diffY = pair.y - meanY;

      covariance += diffX * diffY;
      stdDevX += diffX * diffX;
      stdDevY += diffY * diffY;
    }

    // Pearson r
    double denominator = Math.sqrt(stdDevX * stdDevY);
    if (denominator == 0) {
      return BigDecimal.ZERO;
    }

    double r = covariance / denominator;

    return BigDecimal.valueOf(r).setScale(4, RoundingMode.HALF_UP);
  }

  private BigDecimal calculateConfidence(int sampleSize) {
    if (sampleSize < 5) return BigDecimal.valueOf(20);
    if (sampleSize < 10) return BigDecimal.valueOf(50);
    if (sampleSize < 30) return BigDecimal.valueOf(70);
    if (sampleSize < 100) return BigDecimal.valueOf(85);
    return BigDecimal.valueOf(95);
  }

  /** Data pair for correlation calculation. */
  private record DataPair(double x, double y) {}
}
