package com.pompom.creative.rulemining;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.*;

import com.pompom.creative.correlation.CorrelationAnalysis;
import com.pompom.creative.correlation.CorrelationAnalysisRepository;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.performance.PerformanceClassification;
import com.pompom.creative.performance.PerformanceClassificationRepository;
import com.pompom.creative.trajectory.TrajectoryAnalysis;
import com.pompom.creative.trajectory.TrajectoryAnalysisRepository;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RuleMiningServiceTest {

  @Mock private RuleCandidateRepository ruleRepo;

  @Mock private PerformanceClassificationRepository performanceRepo;

  @Mock private TrajectoryAnalysisRepository trajectoryRepo;

  @Mock private CorrelationAnalysisRepository correlationRepo;

  @InjectMocks private RuleMiningService service;

  @Test
  void testMineRules_success() {
    // Setup
    List<PerformanceClassification> performances = createPerformances(15);
    List<TrajectoryAnalysis> trajectories = createTrajectories(15, performances);
    CorrelationAnalysis correlation = createCorrelation();

    when(performanceRepo.findAll()).thenReturn(performances);
    when(trajectoryRepo.findAll()).thenReturn(trajectories);
    when(correlationRepo.findFirstByOrderByAnalyzedAtDesc()).thenReturn(Optional.of(correlation));
    when(ruleRepo.saveAll(anyList())).thenAnswer(i -> i.getArgument(0));

    // Execute
    RuleMiningService.MiningResult result = service.mineRules();

    // Verify
    assertNotNull(result);
    assertNotNull(result.miningRunId());
    assertTrue(result.rulesGenerated() > 0);
    assertNotNull(result.rules());

    verify(ruleRepo).saveAll(anyList());
  }

  @Test
  void testMineRules_insufficientData() {
    // Setup - only 5 performances (need at least 10)
    List<PerformanceClassification> performances = createPerformances(5);
    List<TrajectoryAnalysis> trajectories = createTrajectories(5, performances);

    when(performanceRepo.findAll()).thenReturn(performances);
    when(trajectoryRepo.findAll()).thenReturn(trajectories);

    // Execute & Verify
    assertThrows(
        IllegalStateException.class,
        () -> {
          service.mineRules();
        });
  }

  @Test
  void testGetRulesByRunId() {
    // Setup
    UUID runId = UUID.randomUUID();
    List<RuleCandidate> rules = createRules(3, runId);

    when(ruleRepo.findByMiningRunId(runId)).thenReturn(rules);

    // Execute
    List<RuleCandidate> result = service.getRulesByRunId(runId);

    // Verify
    assertNotNull(result);
    assertEquals(3, result.size());
  }

  @Test
  void testGetActionableRules() {
    // Setup
    List<RuleCandidate> rules = createRules(5, UUID.randomUUID());

    when(ruleRepo.findActionableRules()).thenReturn(rules);

    // Execute
    List<RuleCandidate> result = service.getActionableRules();

    // Verify
    assertNotNull(result);
    assertEquals(5, result.size());
  }

  @Test
  void testGetHighConfidenceRules() {
    // Setup
    BigDecimal minConfidence = BigDecimal.valueOf(80);
    List<RuleCandidate> rules = createRules(3, UUID.randomUUID());

    when(ruleRepo.findHighConfidenceRules(minConfidence)).thenReturn(rules);

    // Execute
    List<RuleCandidate> result = service.getHighConfidenceRules(minConfidence);

    // Verify
    assertNotNull(result);
    assertEquals(3, result.size());
  }

  @Test
  void testRuleCandidate_calculateQualityScore() {
    // Setup
    RuleCandidate rule =
        RuleCandidate.builder()
            .confidence(BigDecimal.valueOf(80))
            .supportCount(10)
            .lift(BigDecimal.valueOf(2.0))
            .build();

    // Execute
    BigDecimal qualityScore = rule.calculateQualityScore();

    // Verify
    assertNotNull(qualityScore);
    assertTrue(qualityScore.compareTo(BigDecimal.ZERO) > 0);
    assertTrue(qualityScore.compareTo(BigDecimal.valueOf(100)) <= 0);
  }

  // Helper methods

  private List<PerformanceClassification> createPerformances(int count) {
    List<PerformanceClassification> performances = new ArrayList<>();

    PerformanceClassification.PerformanceCategory[] categories = {
      PerformanceClassification.PerformanceCategory.BREAKOUT,
      PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT,
      PerformanceClassification.PerformanceCategory.STRONG_START,
      PerformanceClassification.PerformanceCategory.PERSISTENT_WINNER,
      PerformanceClassification.PerformanceCategory.MEDIUM,
      PerformanceClassification.PerformanceCategory.WEAK,
      PerformanceClassification.PerformanceCategory.EARLY_REJECTION
    };

    for (int i = 0; i < count; i++) {
      UUID jobId = UUID.randomUUID();
      PublicationJob job = new PublicationJob();
      job.setId(jobId);

      PerformanceClassification perf =
          PerformanceClassification.builder()
              .id(UUID.randomUUID())
              .publicationJob(job)
              .category(categories[i % categories.length])
              .build();

      performances.add(perf);
    }

    return performances;
  }

  private List<TrajectoryAnalysis> createTrajectories(
      int count, List<PerformanceClassification> performances) {
    List<TrajectoryAnalysis> trajectories = new ArrayList<>();

    TrajectoryAnalysis.TrajectoryShape[] shapes = {
      TrajectoryAnalysis.TrajectoryShape.HOCKEY_STICK,
      TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL,
      TrajectoryAnalysis.TrajectoryShape.SPIKE_AND_PLATEAU,
      TrajectoryAnalysis.TrajectoryShape.MULTI_WAVE,
      TrajectoryAnalysis.TrajectoryShape.LINEAR
    };

    for (int i = 0; i < count && i < performances.size(); i++) {
      PublicationJob job = performances.get(i).getPublicationJob();

      TrajectoryAnalysis traj =
          TrajectoryAnalysis.builder()
              .id(UUID.randomUUID())
              .publicationJob(job)
              .trajectoryShape(shapes[i % shapes.length])
              .velocityFirst24H(BigDecimal.valueOf(1000 + i * 500))
              .plateauDetected(i % 3 == 0)
              .plateauDay(i % 3 == 0 ? (i % 5) : null)
              .build();

      trajectories.add(traj);
    }

    return trajectories;
  }

  private CorrelationAnalysis createCorrelation() {
    return CorrelationAnalysis.builder()
        .id(UUID.randomUUID())
        .analysisName("Test Correlation")
        .sampleSize(20)
        .overallScoreVsViews(BigDecimal.valueOf(0.75))
        .analysisConfidence(BigDecimal.valueOf(85))
        .build();
  }

  private List<RuleCandidate> createRules(int count, UUID miningRunId) {
    List<RuleCandidate> rules = new ArrayList<>();

    for (int i = 0; i < count; i++) {
      RuleCandidate rule =
          RuleCandidate.builder()
              .id(UUID.randomUUID())
              .ruleName("Test Rule " + i)
              .ruleDescription("Test description " + i)
              .condition("test_condition_" + i)
              .outcome("test_outcome_" + i)
              .ruleType(RuleCandidate.RuleType.TRAJECTORY_PATTERN)
              .ruleCategory(RuleCandidate.RuleCategory.BREAKOUT_SIGNAL)
              .supportCount(10 + i)
              .totalCases(20)
              .confidence(BigDecimal.valueOf(70 + i))
              .lift(BigDecimal.valueOf(1.5))
              .isActionable(true)
              .miningRunId(miningRunId)
              .build();

      rules.add(rule);
    }

    return rules;
  }
}
