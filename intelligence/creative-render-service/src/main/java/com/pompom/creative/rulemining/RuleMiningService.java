package com.pompom.creative.rulemining;

import com.pompom.creative.correlation.CorrelationAnalysis;
import com.pompom.creative.correlation.CorrelationAnalysisRepository;
import com.pompom.creative.performance.PerformanceClassification;
import com.pompom.creative.performance.PerformanceClassificationRepository;
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
 * Service for mining actionable rules from performance patterns. Generates rule candidates using
 * association rule mining principles.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class RuleMiningService {

  private final RuleCandidateRepository ruleRepo;
  private final PerformanceClassificationRepository performanceRepo;
  private final TrajectoryAnalysisRepository trajectoryRepo;
  private final CorrelationAnalysisRepository correlationRepo;

  /** Mine rules from current performance data. */
  @Transactional
  public MiningResult mineRules() {
    log.info("Starting rule mining");

    UUID miningRunId = UUID.randomUUID();
    List<RuleCandidate> rules = new ArrayList<>();

    // Fetch data
    List<PerformanceClassification> performances = performanceRepo.findAll();
    List<TrajectoryAnalysis> trajectories = trajectoryRepo.findAll();
    CorrelationAnalysis correlation =
        correlationRepo.findFirstByOrderByAnalyzedAtDesc().orElse(null);

    if (performances.size() < 10) {
      throw new IllegalStateException(
          "Insufficient data for rule mining (need at least 10 performances)");
    }

    // Mine trajectory-based rules
    rules.addAll(mineTrajectoryRules(performances, trajectories, miningRunId));

    // Mine threshold-based rules
    rules.addAll(mineThresholdRules(performances, trajectories, miningRunId));

    // Mine correlation-based rules
    if (correlation != null) {
      rules.addAll(mineCorrelationRules(correlation, miningRunId));
    }

    // Mine temporal pattern rules
    rules.addAll(mineTemporalRules(performances, trajectories, miningRunId));

    // Save all rules
    rules = ruleRepo.saveAll(rules);

    log.info("Rule mining complete: {} rules generated", rules.size());

    return new MiningResult(miningRunId, rules.size(), rules);
  }

  /** Get all rules for a mining run. */
  @Transactional(readOnly = true)
  public List<RuleCandidate> getRulesByRunId(UUID runId) {
    return ruleRepo.findByMiningRunId(runId);
  }

  /** Get actionable rules. */
  @Transactional(readOnly = true)
  public List<RuleCandidate> getActionableRules() {
    return ruleRepo.findActionableRules();
  }

  /** Get high-confidence rules. */
  @Transactional(readOnly = true)
  public List<RuleCandidate> getHighConfidenceRules(BigDecimal minConfidence) {
    return ruleRepo.findHighConfidenceRules(minConfidence);
  }

  // Private mining methods

  /**
   * Mine rules from trajectory patterns. Example: "IF trajectory_shape = HOCKEY_STICK THEN likely
   * BREAKOUT"
   */
  private List<RuleCandidate> mineTrajectoryRules(
      List<PerformanceClassification> performances,
      List<TrajectoryAnalysis> trajectories,
      UUID miningRunId) {
    List<RuleCandidate> rules = new ArrayList<>();

    // Build trajectory -> performance mapping
    for (TrajectoryAnalysis.TrajectoryShape shape : TrajectoryAnalysis.TrajectoryShape.values()) {
      int shapeCount = 0;
      int breakoutCount = 0;
      int strongCount = 0;

      for (TrajectoryAnalysis traj : trajectories) {
        if (traj.getTrajectoryShape() != shape) continue;

        shapeCount++;

        // Find matching performance
        PerformanceClassification perf =
            performances.stream()
                .filter(p -> p.getPublicationJob().getId().equals(traj.getPublicationJob().getId()))
                .findFirst()
                .orElse(null);

        if (perf != null) {
          if (perf.getCategory() == PerformanceClassification.PerformanceCategory.BREAKOUT
              || perf.getCategory()
                  == PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT) {
            breakoutCount++;
          }
          if (perf.getCategory() == PerformanceClassification.PerformanceCategory.STRONG_START
              || perf.getCategory()
                  == PerformanceClassification.PerformanceCategory.PERSISTENT_WINNER) {
            strongCount++;
          }
        }
      }

      // Generate rules if confidence is high enough
      if (shapeCount >= 3) {
        // Breakout rule
        if (breakoutCount > 0) {
          BigDecimal confidence =
              BigDecimal.valueOf(breakoutCount)
                  .multiply(BigDecimal.valueOf(100))
                  .divide(BigDecimal.valueOf(shapeCount), 2, RoundingMode.HALF_UP);

          if (confidence.compareTo(BigDecimal.valueOf(50)) >= 0) {
            RuleCandidate rule =
                RuleCandidate.builder()
                    .ruleName("Trajectory " + shape + " → Breakout")
                    .ruleDescription(
                        "Videos with " + shape + " trajectory tend to become breakouts")
                    .condition("trajectory_shape = " + shape)
                    .outcome("category IN (BREAKOUT, EVERGREEN_BREAKOUT)")
                    .ruleType(RuleCandidate.RuleType.TRAJECTORY_PATTERN)
                    .ruleCategory(RuleCandidate.RuleCategory.BREAKOUT_SIGNAL)
                    .supportCount(breakoutCount)
                    .totalCases(performances.size())
                    .confidence(confidence)
                    .lift(BigDecimal.valueOf(1.5)) // Simplified
                    .isActionable(true)
                    .actionRecommendation(
                        "Monitor videos with "
                            + shape
                            + " trajectory closely for scaling opportunities")
                    .miningRunId(miningRunId)
                    .build();

            rules.add(rule);
          }
        }
      }
    }

    return rules;
  }

  /** Mine threshold-based rules. Example: "IF velocity_first_24h > 2000 THEN likely BREAKOUT" */
  private List<RuleCandidate> mineThresholdRules(
      List<PerformanceClassification> performances,
      List<TrajectoryAnalysis> trajectories,
      UUID miningRunId) {
    List<RuleCandidate> rules = new ArrayList<>();

    // Velocity threshold rule
    int highVelocityCount = 0;
    int highVelocityBreakout = 0;

    for (TrajectoryAnalysis traj : trajectories) {
      if (traj.getVelocityFirst24H() != null
          && traj.getVelocityFirst24H().compareTo(BigDecimal.valueOf(2000)) > 0) {

        highVelocityCount++;

        PerformanceClassification perf =
            performances.stream()
                .filter(p -> p.getPublicationJob().getId().equals(traj.getPublicationJob().getId()))
                .findFirst()
                .orElse(null);

        if (perf != null
            && (perf.getCategory() == PerformanceClassification.PerformanceCategory.BREAKOUT
                || perf.getCategory()
                    == PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT)) {
          highVelocityBreakout++;
        }
      }
    }

    if (highVelocityCount >= 3) {
      BigDecimal confidence =
          BigDecimal.valueOf(highVelocityBreakout)
              .multiply(BigDecimal.valueOf(100))
              .divide(BigDecimal.valueOf(highVelocityCount), 2, RoundingMode.HALF_UP);

      if (confidence.compareTo(BigDecimal.valueOf(70)) >= 0) {
        RuleCandidate rule =
            RuleCandidate.builder()
                .ruleName("High Velocity → Breakout")
                .ruleDescription("Videos with >2000 views/hour in first 24h tend to break out")
                .condition("velocity_first_24h > 2000")
                .outcome("category IN (BREAKOUT, EVERGREEN_BREAKOUT)")
                .ruleType(RuleCandidate.RuleType.PERFORMANCE_THRESHOLD)
                .ruleCategory(RuleCandidate.RuleCategory.EARLY_DETECTION)
                .supportCount(highVelocityBreakout)
                .totalCases(performances.size())
                .confidence(confidence)
                .lift(BigDecimal.valueOf(2.0))
                .isActionable(true)
                .actionRecommendation("Fast-track high velocity videos for immediate promotion")
                .miningRunId(miningRunId)
                .build();

        rules.add(rule);
      }
    }

    return rules;
  }

  /** Mine correlation-based rules. Example: "IF overall_score high THEN views high (r=0.75)" */
  private List<RuleCandidate> mineCorrelationRules(
      CorrelationAnalysis correlation, UUID miningRunId) {
    List<RuleCandidate> rules = new ArrayList<>();

    // Strong correlation → actionable insight
    if (correlation.getOverallScoreVsViews() != null
        && correlation.getOverallScoreVsViews().abs().compareTo(BigDecimal.valueOf(0.7)) > 0) {

      BigDecimal r = correlation.getOverallScoreVsViews();
      BigDecimal confidence = r.abs().multiply(BigDecimal.valueOf(100));

      RuleCandidate rule =
          RuleCandidate.builder()
              .ruleName("Quality Score → Performance")
              .ruleDescription("Strong correlation (r=" + r + ") between quality score and views")
              .condition("overall_score >= 80")
              .outcome("high_views (correlation: " + r + ")")
              .ruleType(RuleCandidate.RuleType.CORRELATION_INSIGHT)
              .ruleCategory(RuleCandidate.RuleCategory.OPTIMIZATION_HINT)
              .supportCount(correlation.getSampleSize())
              .totalCases(correlation.getSampleSize())
              .confidence(confidence)
              .lift(BigDecimal.valueOf(1.8))
              .isActionable(true)
              .actionRecommendation("Prioritize quality optimization to improve view performance")
              .miningRunId(miningRunId)
              .build();

      rules.add(rule);
    }

    return rules;
  }

  /** Mine temporal pattern rules. Example: "IF plateau_day <= 2 THEN likely SPIKE_AND_PLATEAU" */
  private List<RuleCandidate> mineTemporalRules(
      List<PerformanceClassification> performances,
      List<TrajectoryAnalysis> trajectories,
      UUID miningRunId) {
    List<RuleCandidate> rules = new ArrayList<>();

    // Early plateau detection
    int earlyPlateauCount = 0;
    int earlyPlateauWeak = 0;

    for (TrajectoryAnalysis traj : trajectories) {
      if (traj.getPlateauDetected() != null
          && traj.getPlateauDetected()
          && traj.getPlateauDay() != null
          && traj.getPlateauDay() <= 2) {

        earlyPlateauCount++;

        PerformanceClassification perf =
            performances.stream()
                .filter(p -> p.getPublicationJob().getId().equals(traj.getPublicationJob().getId()))
                .findFirst()
                .orElse(null);

        if (perf != null
            && (perf.getCategory() == PerformanceClassification.PerformanceCategory.WEAK
                || perf.getCategory()
                    == PerformanceClassification.PerformanceCategory.EARLY_REJECTION)) {
          earlyPlateauWeak++;
        }
      }
    }

    if (earlyPlateauCount >= 3) {
      BigDecimal confidence =
          BigDecimal.valueOf(earlyPlateauWeak)
              .multiply(BigDecimal.valueOf(100))
              .divide(BigDecimal.valueOf(earlyPlateauCount), 2, RoundingMode.HALF_UP);

      if (confidence.compareTo(BigDecimal.valueOf(60)) >= 0) {
        RuleCandidate rule =
            RuleCandidate.builder()
                .ruleName("Early Plateau → Weak Performance")
                .ruleDescription("Videos plateauing within 2 days tend to underperform")
                .condition("plateau_detected = true AND plateau_day <= 2")
                .outcome("category IN (WEAK, EARLY_REJECTION)")
                .ruleType(RuleCandidate.RuleType.TEMPORAL_PATTERN)
                .ruleCategory(RuleCandidate.RuleCategory.WARNING_SIGNAL)
                .supportCount(earlyPlateauWeak)
                .totalCases(performances.size())
                .confidence(confidence)
                .lift(BigDecimal.valueOf(1.6))
                .isActionable(true)
                .actionRecommendation(
                    "Videos with early plateau need immediate intervention or reoptimization")
                .miningRunId(miningRunId)
                .build();

        rules.add(rule);
      }
    }

    return rules;
  }

  /** Mining result DTO. */
  public record MiningResult(UUID miningRunId, int rulesGenerated, List<RuleCandidate> rules) {}
}
