package com.pompom.creative.performance;

import com.pompom.creative.domain.PublicationJob;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * Performance classification for a video. Categorizes videos based on their performance trajectory.
 */
@Entity
@Table(name = "performance_classifications")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceClassification {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false, unique = true)
  private PublicationJob publicationJob;

  @Enumerated(EnumType.STRING)
  @Column(name = "category", nullable = false, length = 30)
  private PerformanceCategory category;

  @Column(name = "confidence_score", nullable = false, precision = 5, scale = 2)
  private BigDecimal confidenceScore; // 0-100

  // Key metrics at classification time
  @Column(name = "final_views")
  private Long finalViews;

  @Column(name = "final_engagement_rate", precision = 5, scale = 2)
  private BigDecimal finalEngagementRate;

  @Column(name = "peak_views")
  private Long peakViews;

  @Column(name = "peak_day")
  private Integer peakDay;

  // Growth characteristics
  @Column(name = "velocity_score", precision = 5, scale = 2)
  private BigDecimal velocityScore; // Views per hour in first 24h

  @Column(name = "acceleration_score", precision = 5, scale = 2)
  private BigDecimal accelerationScore; // Change in velocity

  @Column(name = "plateau_detected")
  private Boolean plateauDetected;

  @Column(name = "plateau_day")
  private Integer plateauDay;

  @Column(name = "tail_strength", precision = 5, scale = 2)
  private BigDecimal tailStrength; // Views after day 7 / Total views

  // Wave detection
  @Column(name = "primary_wave_day")
  private Integer primaryWaveDay;

  @Column(name = "secondary_wave_day")
  private Integer secondaryWaveDay;

  @Column(name = "wave_count")
  private Integer waveCount;

  // Classification metadata
  @Column(name = "classification_reason", columnDefinition = "TEXT")
  private String classificationReason;

  @Column(name = "classified_at", nullable = false)
  private Instant classifiedAt = Instant.now();

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  // Strategic success tier (V25)
  @Column(name = "success_tier", length = 20)
  private String successTier;

  /** Performance categories based on ROADMAP.md Phase 4 spec. */
  public enum PerformanceCategory {
    /**
     * Video failed early - views stalled within first 6 hours. Typically <1000 views in first 24h.
     */
    EARLY_REJECTION,

    /**
     * Low performance - minimal engagement throughout lifecycle. Typically 1K-5K final views, low
     * engagement rate.
     */
    WEAK,

    /**
     * Average performance - steady but unremarkable growth. Typically 5K-20K final views, medium
     * engagement.
     */
    MEDIUM,

    /** Strong early traction but plateaus quickly. High velocity in first 24h, then flattens. */
    STRONG_START,

    /**
     * Exceptional early and sustained growth - viral hit. >50K views, high velocity, sustained
     * engagement.
     */
    BREAKOUT,

    /**
     * Slow start, then viral acceleration after day 2-3. Algorithm pickup or secondary platform
     * surge.
     */
    DELAYED_BREAKOUT,

    /** Multiple distinct growth waves. Primary wave + secondary wave(s) from re-shares/features. */
    MULTI_WAVE,

    /** Consistent strong performance without decay. High views, sustained engagement >7 days. */
    PERSISTENT_WINNER,

    /**
     * Strong tail performance - views continue after day 7. >30% of total views occur after day 7.
     */
    LONG_TAIL,

    /**
     * Evergreen content - sustained growth beyond 30 days. Views continue to grow, no plateau
     * detected.
     */
    EVERGREEN_BREAKOUT
  }

  /** Check if this is a winning performance. */
  public boolean isWinner() {
    return category == PerformanceCategory.BREAKOUT
        || category == PerformanceCategory.DELAYED_BREAKOUT
        || category == PerformanceCategory.MULTI_WAVE
        || category == PerformanceCategory.PERSISTENT_WINNER
        || category == PerformanceCategory.EVERGREEN_BREAKOUT;
  }

  /** Get performance tier (1-4, higher is better). */
  public int getTier() {
    return switch (category) {
      case BREAKOUT, EVERGREEN_BREAKOUT, PERSISTENT_WINNER -> 1; // Top tier
      case DELAYED_BREAKOUT, MULTI_WAVE -> 2; // Strong tier
      case STRONG_START, LONG_TAIL, MEDIUM -> 3; // Medium tier
      case WEAK, EARLY_REJECTION -> 4; // Weak tier
    };
  }
}
