package com.pompom.creative.benchmark;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.performance.PerformanceClassification;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/** Catalog entry for top-performing videos. Tracks winners for benchmarking and comparison. */
@Entity
@Table(name = "winner_entries")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WinnerEntry {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false, unique = true)
  private PublicationJob publicationJob;

  @Enumerated(EnumType.STRING)
  @Column(name = "winner_tier", nullable = false, length = 30)
  private WinnerTier winnerTier;

  @Enumerated(EnumType.STRING)
  @Column(name = "performance_category", nullable = false, length = 30)
  private PerformanceClassification.PerformanceCategory performanceCategory;

  // Key metrics snapshot
  @Column(name = "total_views", nullable = false)
  private Long totalViews;

  @Column(name = "total_engagement", nullable = false)
  private Long totalEngagement; // likes + comments + shares

  @Column(name = "engagement_rate", precision = 5, scale = 2)
  private BigDecimal engagementRate;

  @Column(name = "completion_rate", precision = 5, scale = 2)
  private BigDecimal completionRate;

  @Column(name = "velocity_first_24h", precision = 10, scale = 2)
  private BigDecimal velocityFirst24H;

  @Column(name = "tail_strength", precision = 5, scale = 4)
  private BigDecimal tailStrength;

  // Trajectory characteristics
  @Column(name = "trajectory_shape", length = 30)
  private String trajectoryShape;

  @Column(name = "peak_day")
  private Integer peakDay;

  @Column(name = "wave_count")
  private Integer waveCount;

  // Benchmark scores
  @Column(name = "benchmark_score", precision = 5, scale = 2)
  private BigDecimal benchmarkScore; // 0-100 composite score

  @Column(name = "percentile_rank", precision = 5, scale = 2)
  private BigDecimal percentileRank; // 0-100 percentile among all videos

  // Winner metadata
  @Column(name = "added_at", nullable = false, updatable = false)
  private Instant addedAt = Instant.now();

  @Column(name = "last_updated", nullable = false)
  private Instant lastUpdated = Instant.now();

  @Column(name = "notes", columnDefinition = "TEXT")
  private String notes;

  /** Winner tier classification. */
  public enum WinnerTier {
    PLATINUM, // Top 1% - exceptional breakouts
    GOLD, // Top 5% - strong performers
    SILVER, // Top 10% - above average performers
    BRONZE // Top 25% - good performers
  }

  /** Calculate composite benchmark score. Weighted combination of key metrics. */
  public void calculateBenchmarkScore() {
    BigDecimal score = BigDecimal.ZERO;

    // Views component (30%)
    BigDecimal viewsScore = BigDecimal.valueOf(Math.min(totalViews / 1000.0, 100));
    score = score.add(viewsScore.multiply(BigDecimal.valueOf(0.3)));

    // Engagement rate component (25%)
    if (engagementRate != null) {
      BigDecimal engagementScore = engagementRate.min(BigDecimal.valueOf(100));
      score = score.add(engagementScore.multiply(BigDecimal.valueOf(0.25)));
    }

    // Velocity component (20%)
    if (velocityFirst24H != null) {
      BigDecimal velocityScore =
          BigDecimal.valueOf(Math.min(velocityFirst24H.doubleValue() / 50.0, 100));
      score = score.add(velocityScore.multiply(BigDecimal.valueOf(0.2)));
    }

    // Completion rate component (15%)
    if (completionRate != null) {
      score = score.add(completionRate.multiply(BigDecimal.valueOf(0.15)));
    }

    // Tail strength component (10%)
    if (tailStrength != null) {
      BigDecimal tailScore = tailStrength.multiply(BigDecimal.valueOf(100));
      score = score.add(tailScore.multiply(BigDecimal.valueOf(0.1)));
    }

    this.benchmarkScore = score.min(BigDecimal.valueOf(100));
  }
}
