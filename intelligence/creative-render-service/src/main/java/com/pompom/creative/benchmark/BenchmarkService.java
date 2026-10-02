package com.pompom.creative.benchmark;

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

/** Service for managing winner catalog and benchmark comparisons. */
@Service
@Slf4j
@RequiredArgsConstructor
public class BenchmarkService {

  private final WinnerEntryRepository winnerRepo;
  private final PerformanceClassificationRepository performanceRepo;
  private final VideoMetricsRepository metricsRepo;
  private final TrajectoryAnalysisRepository trajectoryRepo;
  private final PublicationJobRepository publicationJobRepo;

  /** Update winner catalog based on current performances. */
  @Transactional
  public CatalogUpdate updateCatalog() {
    log.info("Updating winner catalog");

    List<PerformanceClassification> performances = performanceRepo.findAll();

    if (performances.isEmpty()) {
      throw new IllegalStateException("No performance data available");
    }

    int added = 0;
    int updated = 0;

    for (PerformanceClassification perf : performances) {
      // Only catalog strong performers
      if (isWinnerCandidate(perf.getCategory())) {
        WinnerEntry entry = createOrUpdateWinnerEntry(perf);

        if (entry != null) {
          if (winnerRepo.findByPublicationJobId(perf.getPublicationJob().getId()).isPresent()) {
            updated++;
          } else {
            added++;
          }
        }
      }
    }

    // Calculate percentile ranks
    updatePercentileRanks();

    log.info("Catalog updated: {} added, {} updated", added, updated);

    return new CatalogUpdate(added, updated, winnerRepo.countWinners());
  }

  /** Get winner entry for a job. */
  @Transactional(readOnly = true)
  public WinnerEntry getWinnerEntry(UUID publicationJobId) {
    return winnerRepo.findByPublicationJobId(publicationJobId).orElse(null);
  }

  /** Get top performers by tier. */
  @Transactional(readOnly = true)
  public List<WinnerEntry> getTopPerformers(WinnerEntry.WinnerTier tier) {
    return winnerRepo.findTopPerformersByTier(tier);
  }

  /** Compare a job against winner benchmarks. */
  @Transactional(readOnly = true)
  public BenchmarkComparison compareAgainstBenchmarks(UUID publicationJobId) {
    // Get job's performance
    PerformanceClassification perf =
        performanceRepo
            .findByPublicationJobId(publicationJobId)
            .orElseThrow(() -> new IllegalArgumentException("Performance not found"));

    List<VideoMetrics> timeline = metricsRepo.findMetricsTimeline(publicationJobId);
    if (timeline.isEmpty()) {
      throw new IllegalArgumentException("No metrics available");
    }

    VideoMetrics finalMetrics = timeline.get(timeline.size() - 1);
    TrajectoryAnalysis trajectory =
        trajectoryRepo.findByPublicationJobId(publicationJobId).orElse(null);

    // Calculate job's benchmark score
    BigDecimal jobScore = calculateBenchmarkScore(finalMetrics, trajectory);

    // Get averages by tier
    BigDecimal platinumAvg =
        winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.PLATINUM);
    BigDecimal goldAvg = winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.GOLD);
    BigDecimal silverAvg = winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.SILVER);
    BigDecimal bronzeAvg = winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.BRONZE);

    // Find similar winners (same trajectory shape)
    List<WinnerEntry> similarWinners = new ArrayList<>();
    if (trajectory != null && trajectory.getTrajectoryShape() != null) {
      similarWinners = winnerRepo.findByTrajectoryShape(trajectory.getTrajectoryShape().name());
    }

    return new BenchmarkComparison(
        publicationJobId,
        jobScore,
        platinumAvg != null ? platinumAvg : BigDecimal.ZERO,
        goldAvg != null ? goldAvg : BigDecimal.ZERO,
        silverAvg != null ? silverAvg : BigDecimal.ZERO,
        bronzeAvg != null ? bronzeAvg : BigDecimal.ZERO,
        similarWinners.size(),
        !similarWinners.isEmpty() ? calculateAverageScore(similarWinners) : BigDecimal.ZERO);
  }

  /** Get catalog statistics. */
  @Transactional(readOnly = true)
  public CatalogStats getCatalogStats() {
    long totalWinners = winnerRepo.countWinners();
    long platinumCount = winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.PLATINUM).size();
    long goldCount = winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.GOLD).size();
    long silverCount = winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.SILVER).size();
    long bronzeCount = winnerRepo.findByWinnerTier(WinnerEntry.WinnerTier.BRONZE).size();

    BigDecimal avgPlatinum =
        winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.PLATINUM);
    BigDecimal avgGold = winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.GOLD);
    BigDecimal avgSilver = winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.SILVER);
    BigDecimal avgBronze = winnerRepo.getAverageBenchmarkScoreByTier(WinnerEntry.WinnerTier.BRONZE);

    return new CatalogStats(
        totalWinners,
        platinumCount,
        goldCount,
        silverCount,
        bronzeCount,
        avgPlatinum != null ? avgPlatinum : BigDecimal.ZERO,
        avgGold != null ? avgGold : BigDecimal.ZERO,
        avgSilver != null ? avgSilver : BigDecimal.ZERO,
        avgBronze != null ? avgBronze : BigDecimal.ZERO);
  }

  // Private helper methods

  private boolean isWinnerCandidate(PerformanceClassification.PerformanceCategory category) {
    return category == PerformanceClassification.PerformanceCategory.BREAKOUT
        || category == PerformanceClassification.PerformanceCategory.EVERGREEN_BREAKOUT
        || category == PerformanceClassification.PerformanceCategory.PERSISTENT_WINNER
        || category == PerformanceClassification.PerformanceCategory.STRONG_START
        || category == PerformanceClassification.PerformanceCategory.DELAYED_BREAKOUT;
  }

  private WinnerEntry createOrUpdateWinnerEntry(PerformanceClassification perf) {
    UUID jobId = perf.getPublicationJob().getId();

    // Get metrics
    List<VideoMetrics> timeline = metricsRepo.findMetricsTimeline(jobId);
    if (timeline.isEmpty()) {
      return null;
    }

    VideoMetrics finalMetrics = timeline.get(timeline.size() - 1);
    TrajectoryAnalysis trajectory = trajectoryRepo.findByPublicationJobId(jobId).orElse(null);

    // Create or update entry
    WinnerEntry entry =
        winnerRepo
            .findByPublicationJobId(jobId)
            .orElse(WinnerEntry.builder().publicationJob(perf.getPublicationJob()).build());

    // Update fields
    entry.setPerformanceCategory(perf.getCategory());
    entry.setTotalViews(finalMetrics.getViews());

    long totalEngagement =
        (finalMetrics.getLikes() != null ? finalMetrics.getLikes() : 0)
            + (finalMetrics.getComments() != null ? finalMetrics.getComments() : 0)
            + (finalMetrics.getShares() != null ? finalMetrics.getShares() : 0);
    entry.setTotalEngagement(totalEngagement);
    entry.setEngagementRate(finalMetrics.calculateEngagementRate());
    entry.setCompletionRate(finalMetrics.getCompletionRate());

    if (trajectory != null) {
      entry.setVelocityFirst24H(trajectory.getVelocityFirst24H());
      entry.setTailStrength(trajectory.getTailStrength());
      entry.setTrajectoryShape(
          trajectory.getTrajectoryShape() != null ? trajectory.getTrajectoryShape().name() : null);
      entry.setPeakDay(trajectory.getPeakDay());
      entry.setWaveCount(trajectory.getWaveCount());
    }

    // Calculate benchmark score
    entry.calculateBenchmarkScore();

    // Determine tier
    entry.setWinnerTier(determineTier(entry.getBenchmarkScore()));

    entry.setLastUpdated(java.time.Instant.now());

    return winnerRepo.save(entry);
  }

  private WinnerEntry.WinnerTier determineTier(BigDecimal benchmarkScore) {
    if (benchmarkScore.compareTo(BigDecimal.valueOf(90)) >= 0) {
      return WinnerEntry.WinnerTier.PLATINUM;
    } else if (benchmarkScore.compareTo(BigDecimal.valueOf(75)) >= 0) {
      return WinnerEntry.WinnerTier.GOLD;
    } else if (benchmarkScore.compareTo(BigDecimal.valueOf(60)) >= 0) {
      return WinnerEntry.WinnerTier.SILVER;
    } else {
      return WinnerEntry.WinnerTier.BRONZE;
    }
  }

  private void updatePercentileRanks() {
    List<WinnerEntry> allWinners = winnerRepo.findAllByBenchmarkScore();
    int totalCount = allWinners.size();

    for (int i = 0; i < allWinners.size(); i++) {
      WinnerEntry winner = allWinners.get(i);
      BigDecimal percentile =
          BigDecimal.valueOf(100.0 * (totalCount - i) / totalCount)
              .setScale(2, RoundingMode.HALF_UP);
      winner.setPercentileRank(percentile);
    }

    winnerRepo.saveAll(allWinners);
  }

  private BigDecimal calculateBenchmarkScore(VideoMetrics metrics, TrajectoryAnalysis trajectory) {
    BigDecimal score = BigDecimal.ZERO;

    // Views component (30%)
    BigDecimal viewsScore = BigDecimal.valueOf(Math.min(metrics.getViews() / 1000.0, 100));
    score = score.add(viewsScore.multiply(BigDecimal.valueOf(0.3)));

    // Engagement rate component (25%)
    BigDecimal engagementRate = metrics.calculateEngagementRate();
    if (engagementRate != null) {
      score = score.add(engagementRate.multiply(BigDecimal.valueOf(0.25)));
    }

    // Velocity component (20%)
    if (trajectory != null && trajectory.getVelocityFirst24H() != null) {
      BigDecimal velocityScore =
          BigDecimal.valueOf(Math.min(trajectory.getVelocityFirst24H().doubleValue() / 50.0, 100));
      score = score.add(velocityScore.multiply(BigDecimal.valueOf(0.2)));
    }

    // Completion rate component (15%)
    if (metrics.getCompletionRate() != null) {
      score = score.add(metrics.getCompletionRate().multiply(BigDecimal.valueOf(0.15)));
    }

    // Tail strength component (10%)
    if (trajectory != null && trajectory.getTailStrength() != null) {
      BigDecimal tailScore = trajectory.getTailStrength().multiply(BigDecimal.valueOf(100));
      score = score.add(tailScore.multiply(BigDecimal.valueOf(0.1)));
    }

    return score.min(BigDecimal.valueOf(100));
  }

  private BigDecimal calculateAverageScore(List<WinnerEntry> winners) {
    if (winners.isEmpty()) {
      return BigDecimal.ZERO;
    }

    BigDecimal sum =
        winners.stream()
            .map(WinnerEntry::getBenchmarkScore)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

    return sum.divide(BigDecimal.valueOf(winners.size()), 2, RoundingMode.HALF_UP);
  }

  // DTOs

  public record CatalogUpdate(int added, int updated, long totalWinners) {}

  public record BenchmarkComparison(
      UUID publicationJobId,
      BigDecimal jobScore,
      BigDecimal platinumAvg,
      BigDecimal goldAvg,
      BigDecimal silverAvg,
      BigDecimal bronzeAvg,
      int similarWinnersCount,
      BigDecimal similarWinnersAvgScore) {}

  public record CatalogStats(
      long totalWinners,
      long platinumCount,
      long goldCount,
      long silverCount,
      long bronzeCount,
      BigDecimal avgPlatinumScore,
      BigDecimal avgGoldScore,
      BigDecimal avgSilverScore,
      BigDecimal avgBronzeScore) {}
}
