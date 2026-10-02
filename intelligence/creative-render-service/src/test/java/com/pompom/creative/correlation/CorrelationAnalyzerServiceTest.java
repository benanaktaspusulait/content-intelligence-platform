package com.pompom.creative.correlation;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.performance.PerformanceClassification;
import com.pompom.creative.performance.PerformanceClassificationRepository;
import com.pompom.creative.repository.PublicationJobRepository;
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
class CorrelationAnalyzerServiceTest {

  @Mock private CorrelationAnalysisRepository correlationRepo;

  @Mock private PublicationJobRepository publicationJobRepo;

  @Mock private VideoMetricsRepository metricsRepo;

  @Mock private TrajectoryAnalysisRepository trajectoryRepo;

  @Mock private PerformanceClassificationRepository performanceRepo;

  @InjectMocks private CorrelationAnalyzerService service;

  @Test
  void testAnalyzeCorrelations_positiveCorrelation() {
    // Setup - high performance -> high views
    List<PerformanceClassification> classifications = createClassifications(10, true);
    setupMockData(classifications, true);

    when(performanceRepo.findAll()).thenReturn(classifications);
    when(correlationRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    CorrelationAnalysis result = service.analyzeCorrelations();

    // Verify
    assertNotNull(result);
    assertEquals(10, result.getSampleSize());
    assertNotNull(result.getOverallScoreVsViews());

    // Should have positive correlation
    assertTrue(result.getOverallScoreVsViews().compareTo(BigDecimal.ZERO) > 0);

    verify(correlationRepo).save(any());
  }

  @Test
  void testAnalyzeCorrelations_insufficientData() {
    // Setup - only 3 samples (need at least 5)
    List<PerformanceClassification> classifications = createClassifications(3, true);
    setupMockData(classifications, true);

    when(performanceRepo.findAll()).thenReturn(classifications);

    // Execute & Verify
    assertThrows(
        IllegalStateException.class,
        () -> {
          service.analyzeCorrelations();
        });
  }

  @Test
  void testAnalyzeCorrelations_confidenceScoring() {
    // Setup - different sample sizes
    List<PerformanceClassification> smallSample = createClassifications(8, true);
    List<PerformanceClassification> largeSample = createClassifications(50, true);

    setupMockData(smallSample, true);
    when(performanceRepo.findAll()).thenReturn(smallSample);
    when(correlationRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    CorrelationAnalysis smallAnalysis = service.analyzeCorrelations();

    setupMockData(largeSample, true);
    when(performanceRepo.findAll()).thenReturn(largeSample);

    CorrelationAnalysis largeAnalysis = service.analyzeCorrelations();

    // Verify - larger sample should have higher confidence
    assertTrue(
        largeAnalysis.getAnalysisConfidence().compareTo(smallAnalysis.getAnalysisConfidence())
            >= 0);
  }

  @Test
  void testGetLatestAnalysis() {
    // Setup
    CorrelationAnalysis analysis = createAnalysis();
    when(correlationRepo.findFirstByOrderByAnalyzedAtDesc()).thenReturn(Optional.of(analysis));

    // Execute
    CorrelationAnalysis result = service.getLatestAnalysis();

    // Verify
    assertNotNull(result);
    assertEquals(analysis.getId(), result.getId());
  }

  @Test
  void testGetAnalysisHistory() {
    // Setup
    List<CorrelationAnalysis> history = new ArrayList<>();
    history.add(createAnalysis());
    history.add(createAnalysis());

    when(correlationRepo.findTop10ByOrderByAnalyzedAtDesc()).thenReturn(history);

    // Execute
    List<CorrelationAnalysis> result = service.getAnalysisHistory();

    // Verify
    assertNotNull(result);
    assertEquals(2, result.size());
  }

  @Test
  void testInterpretCorrelation() {
    // Strong correlation
    assertEquals("STRONG", CorrelationAnalysis.interpretCorrelation(BigDecimal.valueOf(0.8)));
    assertEquals("STRONG", CorrelationAnalysis.interpretCorrelation(BigDecimal.valueOf(-0.75)));

    // Moderate correlation
    assertEquals("MODERATE", CorrelationAnalysis.interpretCorrelation(BigDecimal.valueOf(0.5)));
    assertEquals("MODERATE", CorrelationAnalysis.interpretCorrelation(BigDecimal.valueOf(-0.4)));

    // Weak correlation
    assertEquals("WEAK", CorrelationAnalysis.interpretCorrelation(BigDecimal.valueOf(0.2)));
    assertEquals("WEAK", CorrelationAnalysis.interpretCorrelation(BigDecimal.valueOf(-0.1)));

    // Null
    assertEquals("UNKNOWN", CorrelationAnalysis.interpretCorrelation(null));
  }

  // Helper methods

  private List<PerformanceClassification> createClassifications(
      int count, boolean correlatedWithViews) {
    List<PerformanceClassification> results = new ArrayList<>();

    PerformanceClassification.PerformanceCategory[] categories = {
      PerformanceClassification.PerformanceCategory.EARLY_REJECTION,
      PerformanceClassification.PerformanceCategory.WEAK,
      PerformanceClassification.PerformanceCategory.MEDIUM,
      PerformanceClassification.PerformanceCategory.STRONG_START,
      PerformanceClassification.PerformanceCategory.BREAKOUT,
      PerformanceClassification.PerformanceCategory.DELAYED_BREAKOUT,
      PerformanceClassification.PerformanceCategory.MULTI_WAVE,
      PerformanceClassification.PerformanceCategory.PERSISTENT_WINNER,
      PerformanceClassification.PerformanceCategory.LONG_TAIL,
      PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT
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

      results.add(perf);
    }

    return results;
  }

  private void setupMockData(
      List<PerformanceClassification> classifications, boolean correlatedWithPerformance) {
    for (int i = 0; i < classifications.size(); i++) {
      PerformanceClassification perf = classifications.get(i);
      UUID jobId = perf.getPublicationJob().getId();

      // Create metrics
      List<VideoMetrics> timeline = new ArrayList<>();
      VideoMetrics metrics =
          VideoMetrics.builder()
              .views(
                  correlatedWithPerformance
                      ? (long) (10000 + i * 5000)
                      : (long) (5000 + (i * 2371) % 50000))
              .likes(100L)
              .comments(10L)
              .shares(50L)
              .completionRate(
                  BigDecimal.valueOf(
                      correlatedWithPerformance ? (70 + i * 2) : (50 + (i * 13) % 40)))
              .build();

      timeline.add(metrics);
      when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);

      // Create trajectory
      TrajectoryAnalysis trajectory =
          TrajectoryAnalysis.builder()
              .velocityFirst24H(
                  BigDecimal.valueOf(
                      correlatedWithPerformance ? (500 + i * 200) : (100 + (i * 73) % 1000)))
              .build();

      when(trajectoryRepo.findByPublicationJobId(jobId)).thenReturn(Optional.of(trajectory));
    }
  }

  private CorrelationAnalysis createAnalysis() {
    return CorrelationAnalysis.builder()
        .id(UUID.randomUUID())
        .analysisName("Test Analysis")
        .sampleSize(10)
        .overallScoreVsViews(BigDecimal.valueOf(0.75))
        .visualQualityVsViews(BigDecimal.valueOf(0.68))
        .hookVsEngagement(BigDecimal.valueOf(0.72))
        .strongestCorrelationFactor("PERFORMANCE_CATEGORY")
        .strongestCorrelationValue(BigDecimal.valueOf(0.75))
        .analysisConfidence(BigDecimal.valueOf(70))
        .build();
  }
}
