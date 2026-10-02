package com.pompom.creative.analytics;

import com.pompom.creative.benchmark.WinnerEntryRepository;
import com.pompom.creative.correlation.CorrelationAnalysis;
import com.pompom.creative.correlation.CorrelationAnalysisRepository;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.performance.PerformanceClassification;
import com.pompom.creative.performance.PerformanceClassificationRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Predictive analytics service for forecasting video performance.
 *
 * <p>Uses historical data to predict: - Success probability - Expected views and engagement -
 * Performance category - Viral potential
 *
 * <p>Prediction model based on: - Quality scores (visual, hook, pacing, emotional, brand) -
 * Historical performance patterns - Correlation analysis results - Winner catalog benchmarks
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class PredictiveAnalyticsService {

  private final PerformancePredictionRepository predictionRepo;
  private final PerformanceClassificationRepository performanceRepo;
  private final CorrelationAnalysisRepository correlationRepo;
  private final WinnerEntryRepository winnerRepo;

  private static final String MODEL_VERSION = "v1.0-basic";

  /**
   * Predict performance for content based on quality scores.
   *
   * @param contentId Content ID
   * @param platform Target platform
   * @param visualQuality Visual quality score (0-100)
   * @param hookQuality Hook quality score (0-100)
   * @param pacingQuality Pacing quality score (0-100)
   * @param emotionalQuality Emotional quality score (0-100)
   * @param brandQuality Brand quality score (0-100)
   * @return Performance prediction
   */
  @Transactional
  public PerformancePrediction predictPerformance(
      Long contentId,
      PlatformType platform,
      BigDecimal visualQuality,
      BigDecimal hookQuality,
      BigDecimal pacingQuality,
      BigDecimal emotionalQuality,
      BigDecimal brandQuality) {
    log.info("Predicting performance: contentId={}, platform={}", contentId, platform);

    // Calculate overall quality score
    BigDecimal overallQuality =
        calculateOverallQuality(
            visualQuality, hookQuality, pacingQuality, emotionalQuality, brandQuality);

    // Get historical performance data
    List<PerformanceClassification> historicalPerformances =
        performanceRepo.findAll().stream()
            .filter(p -> p.getPublicationJob().getPlatform() == platform)
            .toList();

    // Get correlation insights
    CorrelationAnalysis correlations =
        correlationRepo.findFirstByOrderByAnalyzedAtDesc().orElse(null);

    // Calculate predictions
    BigDecimal successProbability =
        calculateSuccessProbability(overallQuality, historicalPerformances, correlations);

    String predictedCategory =
        predictCategory(overallQuality, successProbability, historicalPerformances);

    Long predictedViews24h = predictViews24h(overallQuality, platform, historicalPerformances);

    Long predictedViews7d = predictViews7d(predictedViews24h, predictedCategory);

    BigDecimal predictedEngagement = predictEngagementRate(overallQuality, correlations);

    BigDecimal viralPotential =
        calculateViralPotential(overallQuality, hookQuality, predictedCategory);

    BigDecimal confidenceLevel =
        calculateConfidenceLevel(historicalPerformances.size(), correlations);

    String recommendation =
        generateRecommendation(overallQuality, predictedCategory, viralPotential);

    // Create prediction
    PerformancePrediction prediction =
        PerformancePrediction.builder()
            .contentId(contentId)
            .platform(platform)
            .qualityScore(overallQuality)
            .successProbability(successProbability)
            .predictedCategory(predictedCategory)
            .predictedViews24h(predictedViews24h)
            .predictedViews7d(predictedViews7d)
            .predictedEngagementRate(predictedEngagement)
            .viralPotential(viralPotential)
            .confidenceLevel(confidenceLevel)
            .modelVersion(MODEL_VERSION)
            .recommendation(recommendation)
            .build();

    prediction = predictionRepo.save(prediction);

    log.info(
        "Prediction created: id={}, successProb={}%, viralPotential={}",
        prediction.getId(), successProbability, viralPotential);

    return prediction;
  }

  /** Calculate overall quality score (weighted average). */
  private BigDecimal calculateOverallQuality(
      BigDecimal visual,
      BigDecimal hook,
      BigDecimal pacing,
      BigDecimal emotional,
      BigDecimal brand) {
    // Weights: hook 30%, visual 25%, pacing 20%, emotional 15%, brand 10%
    return visual
        .multiply(BigDecimal.valueOf(0.25))
        .add(hook.multiply(BigDecimal.valueOf(0.30)))
        .add(pacing.multiply(BigDecimal.valueOf(0.20)))
        .add(emotional.multiply(BigDecimal.valueOf(0.15)))
        .add(brand.multiply(BigDecimal.valueOf(0.10)))
        .setScale(2, RoundingMode.HALF_UP);
  }

  /** Calculate success probability based on quality and historical data. */
  private BigDecimal calculateSuccessProbability(
      BigDecimal quality,
      List<PerformanceClassification> historical,
      CorrelationAnalysis correlations) {
    // Base probability from quality score
    BigDecimal baseProbability =
        quality.multiply(BigDecimal.valueOf(0.8)).setScale(2, RoundingMode.HALF_UP);

    // Adjust based on correlation strength (if available)
    if (correlations != null && correlations.getOverallScoreVsViews() != null) {
      BigDecimal correlation = correlations.getOverallScoreVsViews();
      BigDecimal adjustment = correlation.multiply(BigDecimal.valueOf(10));
      baseProbability = baseProbability.add(adjustment);
    }

    // Ensure 0-100 range
    if (baseProbability.compareTo(BigDecimal.valueOf(100)) > 0) {
      baseProbability = BigDecimal.valueOf(100);
    }
    if (baseProbability.compareTo(BigDecimal.ZERO) < 0) {
      baseProbability = BigDecimal.ZERO;
    }

    return baseProbability.setScale(2, RoundingMode.HALF_UP);
  }

  /** Predict performance category. */
  private String predictCategory(
      BigDecimal quality, BigDecimal successProb, List<PerformanceClassification> historical) {
    if (quality.compareTo(BigDecimal.valueOf(85)) >= 0
        && successProb.compareTo(BigDecimal.valueOf(80)) >= 0) {
      return "BREAKOUT";
    } else if (quality.compareTo(BigDecimal.valueOf(75)) >= 0
        && successProb.compareTo(BigDecimal.valueOf(70)) >= 0) {
      return "STRONG_START";
    } else if (quality.compareTo(BigDecimal.valueOf(65)) >= 0) {
      return "MEDIUM";
    } else {
      return "WEAK";
    }
  }

  /** Predict views at T+24h. */
  private Long predictViews24h(
      BigDecimal quality, PlatformType platform, List<PerformanceClassification> historical) {
    // Base views from quality (1000 - 50000 range)
    long baseViews = 1000 + (long) (quality.doubleValue() * 490);

    // Adjust by platform average (if data available)
    if (!historical.isEmpty()) {
      double avgMultiplier = 1.2; // Platform-specific multiplier
      baseViews = (long) (baseViews * avgMultiplier);
    }

    return baseViews;
  }

  /** Predict views at T+7d based on 24h views and category. */
  private Long predictViews7d(Long views24h, String category) {
    double multiplier =
        switch (category) {
          case "BREAKOUT", "EVERGREEN_BREAKOUT" -> 8.0;
          case "STRONG_START", "PERSISTENT_WINNER" -> 5.0;
          case "DELAYED_BREAKOUT", "MULTI_WAVE" -> 6.0;
          case "LONG_TAIL" -> 4.0;
          case "MEDIUM" -> 3.0;
          default -> 2.0;
        };

    return (long) (views24h * multiplier);
  }

  /** Predict engagement rate. */
  private BigDecimal predictEngagementRate(BigDecimal quality, CorrelationAnalysis correlations) {
    // Base engagement from quality (2% - 8% range)
    BigDecimal baseEngagement =
        BigDecimal.valueOf(2.0).add(quality.multiply(BigDecimal.valueOf(0.06)));

    return baseEngagement.setScale(2, RoundingMode.HALF_UP);
  }

  /** Calculate viral potential. */
  private BigDecimal calculateViralPotential(
      BigDecimal quality, BigDecimal hookQuality, String predictedCategory) {
    // Viral potential heavily weighted by hook quality
    BigDecimal potential =
        hookQuality
            .multiply(BigDecimal.valueOf(0.6))
            .add(quality.multiply(BigDecimal.valueOf(0.4)));

    // Boost if predicted as breakout
    if ("BREAKOUT".equals(predictedCategory) || "EVERGREEN_BREAKOUT".equals(predictedCategory)) {
      potential = potential.multiply(BigDecimal.valueOf(1.2));
    }

    // Cap at 100
    if (potential.compareTo(BigDecimal.valueOf(100)) > 0) {
      potential = BigDecimal.valueOf(100);
    }

    return potential.setScale(2, RoundingMode.HALF_UP);
  }

  /** Calculate confidence level based on data availability. */
  private BigDecimal calculateConfidenceLevel(
      int historicalCount, CorrelationAnalysis correlations) {
    // Base confidence from historical data
    BigDecimal confidence = BigDecimal.valueOf(30); // Base 30%

    if (historicalCount >= 50) {
      confidence = confidence.add(BigDecimal.valueOf(40));
    } else if (historicalCount >= 20) {
      confidence = confidence.add(BigDecimal.valueOf(25));
    } else if (historicalCount >= 10) {
      confidence = confidence.add(BigDecimal.valueOf(15));
    }

    // Add confidence from correlation analysis
    if (correlations != null && correlations.getAnalysisConfidence() != null) {
      confidence =
          confidence.add(correlations.getAnalysisConfidence().multiply(BigDecimal.valueOf(0.3)));
    }

    // Cap at 95% (never 100%)
    if (confidence.compareTo(BigDecimal.valueOf(95)) > 0) {
      confidence = BigDecimal.valueOf(95);
    }

    return confidence.setScale(2, RoundingMode.HALF_UP);
  }

  /** Generate actionable recommendation. */
  private String generateRecommendation(
      BigDecimal quality, String category, BigDecimal viralPotential) {
    StringBuilder rec = new StringBuilder();

    if (quality.compareTo(BigDecimal.valueOf(80)) >= 0) {
      rec.append("✅ High-quality content. Ready to publish. ");
    } else if (quality.compareTo(BigDecimal.valueOf(60)) >= 0) {
      rec.append("⚠️ Good quality but room for improvement. ");
    } else {
      rec.append("❌ Quality below threshold. Consider regenerating. ");
    }

    if (viralPotential.compareTo(BigDecimal.valueOf(70)) >= 0) {
      rec.append("🔥 High viral potential! ");
    }

    rec.append(String.format("Predicted category: %s.", category));

    return rec.toString();
  }

  /** Get prediction by content ID. */
  @Transactional(readOnly = true)
  public List<PerformancePrediction> getPredictionsByContent(Long contentId) {
    return predictionRepo.findByContentId(contentId);
  }
}
