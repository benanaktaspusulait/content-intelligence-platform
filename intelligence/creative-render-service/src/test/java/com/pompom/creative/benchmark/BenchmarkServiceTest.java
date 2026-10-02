package com.pompom.creative.benchmark;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
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
class BenchmarkServiceTest {

  @Mock private WinnerEntryRepository winnerRepo;

  @Mock private PerformanceClassificationRepository performanceRepo;

  @Mock private VideoMetricsRepository metricsRepo;

  @Mock private TrajectoryAnalysisRepository trajectoryRepo;

  @Mock private PublicationJobRepository publicationJobRepo;

  @InjectMocks private BenchmarkService service;

  @Test
  void testUpdateCatalog_success() {
    // Setup
    List<PerformanceClassification> performances = createPerformances(10);

    when(performanceRepo.findAll()).thenReturn(performances);

    for (PerformanceClassification perf : performances) {
      UUID jobId = perf.getPublicationJob().getId();
      when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(createMetricsTimeline(jobId));
      when(trajectoryRepo.findByPublicationJobId(jobId))
          .thenReturn(Optional.of(createTrajectory(jobId)));
      when(winnerRepo.findByPublicationJobId(jobId)).thenReturn(Optional.empty());
    }

    when(winnerRepo.save(any())).thenAnswer(i -> i.getArgument(0));
    when(winnerRepo.findAllByBenchmarkScore()).thenReturn(new ArrayList<>());
    when(winnerRepo.saveAll(anyList())).thenAnswer(i -> i.getArgument(0));
    when(winnerRepo.countWinners()).thenReturn(5L);

    // Execute
    BenchmarkService.CatalogUpdate result = service.updateCatalog();

    // Verify
    assertNotNull(result);
    assertTrue(result.added() >= 0);
    assertEquals(5L, result.totalWinners());

    verify(winnerRepo, atLeastOnce()).save(any());
  }

  @Test
  void testUpdateCatalog_noData() {
    // Setup
    when(performanceRepo.findAll()).thenReturn(new ArrayList<>());

    // Execute & Verify
    assertThrows(
        IllegalStateException.class,
        () -> {
          service.updateCatalog();
        });
  }

  @Test
  void testGetWinnerEntry() {
    // Setup
    UUID jobId = UUID.randomUUID();
    WinnerEntry entry = createWinnerEntry(jobId);

    when(winnerRepo.findByPublicationJobId(jobId)).thenReturn(Optional.of(entry));

    // Execute
    WinnerEntry result = service.getWinnerEntry(jobId);

    // Verify
    assertNotNull(result);
    assertEquals(entry.getId(), result.getId());
  }

  @Test
  void testGetTopPerformers() {
    // Setup
    List<WinnerEntry> winners = createWinnerEntries(5);

    when(winnerRepo.findTopPerformersByTier(WinnerEntry.WinnerTier.PLATINUM)).thenReturn(winners);

    // Execute
    List<WinnerEntry> result = service.getTopPerformers(WinnerEntry.WinnerTier.PLATINUM);

    // Verify
    assertNotNull(result);
    assertEquals(5, result.size());
  }

  @Test
  void testCompareAgainstBenchmarks() {
    // Setup
    UUID jobId = UUID.randomUUID();
    PerformanceClassification perf =
        createPerformance(jobId, PerformanceClassification.PerformanceCategory.BREAKOUT);

    when(performanceRepo.findByPublicationJobId(jobId)).thenReturn(Optional.of(perf));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(createMetricsTimeline(jobId));
    when(trajectoryRepo.findByPublicationJobId(jobId))
        .thenReturn(Optional.of(createTrajectory(jobId)));

    when(winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.PLATINUM))
        .thenReturn(BigDecimal.valueOf(90));
    when(winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.GOLD))
        .thenReturn(BigDecimal.valueOf(75));
    when(winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.SILVER))
        .thenReturn(BigDecimal.valueOf(60));
    when(winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.BRONZE))
        .thenReturn(BigDecimal.valueOf(50));

    when(winnerRepo.findByTrajectoryShape(any())).thenReturn(createWinnerEntries(3));

    // Execute
    BenchmarkService.BenchmarkComparison result = service.compareAgainstBenchmarks(jobId);

    // Verify
    assertNotNull(result);
    assertNotNull(result.jobScore());
    assertEquals(BigDecimal.valueOf(90), result.platinumAvg());
    assertEquals(3, result.similarWinnersCount());
  }

  @Test
  void testGetCatalogStats() {
    // Setup
    when(winnerRepo.countWinners()).thenReturn(100L);
    when(winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.PLATINUM))
        .thenReturn(createWinnerEntries(1));
    when(winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.GOLD))
        .thenReturn(createWinnerEntries(5));
    when(winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.SILVER))
        .thenReturn(createWinnerEntries(10));
    when(winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.BRONZE))
        .thenReturn(createWinnerEntries(25));

    when(winnerRepo.getAverageBenchmarkScoreByTier(any())).thenReturn(BigDecimal.valueOf(70));

    // Execute
    BenchmarkService.CatalogStats result = service.getCatalogStats();

    // Verify
    assertNotNull(result);
    assertEquals(100L, result.totalWinners());
    assertEquals(1L, result.platinumCount());
    assertEquals(5L, result.goldCount());
  }

  @Test
  void testWinnerEntry_calculateBenchmarkScore() {
    // Setup
    WinnerEntry entry =
        WinnerEntry.builder()
            .totalViews(50000L)
            .engagementRate(BigDecimal.valueOf(5.0))
            .velocityFirst24H(BigDecimal.valueOf(2000))
            .completionRate(BigDecimal.valueOf(80))
            .tailStrength(BigDecimal.valueOf(0.3))
            .build();

    // Execute
    entry.calculateBenchmarkScore();

    // Verify
    assertNotNull(entry.getBenchmarkScore());
    assertTrue(entry.getBenchmarkScore().compareTo(BigDecimal.ZERO) > 0);
    assertTrue(entry.getBenchmarkScore().compareTo(BigDecimal.valueOf(100)) <= 0);
  }

  // Helper methods

  private List<PerformanceClassification> createPerformances(int count) {
    List<PerformanceClassification> performances = new ArrayList<>();

    PerformanceClassification.PerformanceCategory[] categories = {
      PerformanceClassification.PerformanceCategory.BREAKOUT,
      PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT,
      PerformanceClassification.PerformanceCategory.PERSISTENT_WINNER,
      PerformanceClassification.PerformanceCategory.STRONG_START
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

  private PerformanceClassification createPerformance(
      UUID jobId, PerformanceClassification.PerformanceCategory category) {
    PublicationJob job = new PublicationJob();
    job.setId(jobId);

    return PerformanceClassification.builder()
        .id(UUID.randomUUID())
        .publicationJob(job)
        .category(category)
        .build();
  }

  private List<VideoMetrics> createMetricsTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();

    PublicationJob job = new PublicationJob();
    job.setId(jobId);

    VideoMetrics metrics =
        VideoMetrics.builder()
            .id(UUID.randomUUID())
            .publicationJob(job)
            .views(50000L)
            .likes(2500L)
            .comments(100L)
            .shares(500L)
            .completionRate(BigDecimal.valueOf(75))
            .build();

    timeline.add(metrics);

    return timeline;
  }

  private TrajectoryAnalysis createTrajectory(UUID jobId) {
    PublicationJob job = new PublicationJob();
    job.setId(jobId);

    return TrajectoryAnalysis.builder()
        .id(UUID.randomUUID())
        .publicationJob(job)
        .trajectoryShape(TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL)
        .velocityFirst24H(BigDecimal.valueOf(2000))
        .tailStrength(BigDecimal.valueOf(0.3))
        .peakDay(7)
        .waveCount(1)
        .build();
  }

  private WinnerEntry createWinnerEntry(UUID jobId) {
    PublicationJob job = new PublicationJob();
    job.setId(jobId);

    WinnerEntry entry =
        WinnerEntry.builder()
            .id(UUID.randomUUID())
            .publicationJob(job)
            .winnerTier(WinnerEntry.WinnerTier.PLATINUM)
            .performanceCategory(PerformanceClassification.PerformanceCategory.BREAKOUT)
            .totalViews(100000L)
            .totalEngagement(5000L)
            .benchmarkScore(BigDecimal.valueOf(85))
            .build();

    return entry;
  }

  private List<WinnerEntry> createWinnerEntries(int count) {
    List<WinnerEntry> entries = new ArrayList<>();

    for (int i = 0; i < count; i++) {
      entries.add(createWinnerEntry(UUID.randomUUID()));
    }

    return entries;
  }
}
