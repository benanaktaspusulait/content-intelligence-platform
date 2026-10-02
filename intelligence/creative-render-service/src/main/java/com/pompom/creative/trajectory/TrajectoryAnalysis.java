package com.pompom.creative.trajectory;

import com.pompom.creative.domain.PublicationJob;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * Detailed trajectory analysis for a video. Stores time-series characteristics, growth patterns,
 * wave detection results.
 */
@Entity
@Table(name = "trajectory_analyses")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrajectoryAnalysis {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false, unique = true)
  private PublicationJob publicationJob;

  // Growth velocity metrics
  @Column(name = "velocity_first_hour", precision = 10, scale = 2)
  private BigDecimal velocityFirstHour; // Views per hour in first hour

  @Column(name = "velocity_first_6h", precision = 10, scale = 2)
  private BigDecimal velocityFirst6H; // Average views/hour in first 6 hours

  @Column(name = "velocity_first_24h", precision = 10, scale = 2)
  private BigDecimal velocityFirst24H; // Average views/hour in first 24 hours

  @Column(name = "velocity_day_1_to_7", precision = 10, scale = 2)
  private BigDecimal velocityDay1To7; // Average views/hour from day 1-7

  @Column(name = "velocity_day_7_to_30", precision = 10, scale = 2)
  private BigDecimal velocityDay7To30; // Average views/hour from day 7-30

  // Acceleration metrics (change in velocity)
  @Column(name = "acceleration_1h_to_6h", precision = 10, scale = 2)
  private BigDecimal acceleration1HTo6H;

  @Column(name = "acceleration_6h_to_24h", precision = 10, scale = 2)
  private BigDecimal acceleration6HTo24H;

  @Column(name = "acceleration_day_1_to_7", precision = 10, scale = 2)
  private BigDecimal accelerationDay1To7;

  // Peak detection
  @Column(name = "peak_views")
  private Long peakViews;

  @Column(name = "peak_timestamp")
  private Instant peakTimestamp;

  @Column(name = "peak_day")
  private Integer peakDay;

  @Column(name = "time_to_peak_hours")
  private Integer timeToPeakHours;

  // Plateau detection
  @Column(name = "plateau_detected")
  private Boolean plateauDetected = false;

  @Column(name = "plateau_timestamp")
  private Instant plateauTimestamp;

  @Column(name = "plateau_day")
  private Integer plateauDay;

  @Column(name = "plateau_views")
  private Long plateauViews;

  // Decay detection
  @Column(name = "decay_detected")
  private Boolean decayDetected = false;

  @Column(name = "decay_rate", precision = 5, scale = 2)
  private BigDecimal decayRate; // Percentage decline per day after peak

  // Wave detection
  @Column(name = "wave_count")
  private Integer waveCount = 0;

  @Column(name = "primary_wave_day")
  private Integer primaryWaveDay;

  @Column(name = "primary_wave_views")
  private Long primaryWaveViews;

  @Column(name = "secondary_wave_day")
  private Integer secondaryWaveDay;

  @Column(name = "secondary_wave_views")
  private Long secondaryWaveViews;

  @Column(name = "tertiary_wave_day")
  private Integer tertiaryWaveDay;

  @Column(name = "tertiary_wave_views")
  private Long tertiaryWaveViews;

  // Tail analysis
  @Column(name = "tail_strength", precision = 5, scale = 4)
  private BigDecimal tailStrength; // Views after day 7 / Total views

  @Column(name = "tail_velocity", precision = 10, scale = 2)
  private BigDecimal tailVelocity; // Average views/hour after day 7

  @Column(name = "tail_sustainability_score", precision = 5, scale = 2)
  private BigDecimal tailSustainabilityScore; // 0-100 score for sustained growth

  // Overall trajectory shape
  @Enumerated(EnumType.STRING)
  @Column(name = "trajectory_shape", length = 30)
  private TrajectoryShape trajectoryShape;

  @Column(name = "growth_pattern", length = 50)
  private String growthPattern; // EXPONENTIAL, LINEAR, LOGARITHMIC, PLATEAU, DECLINE

  // Analysis metadata
  @Column(name = "data_points_count")
  private Integer dataPointsCount;

  @Column(name = "analysis_confidence", precision = 5, scale = 2)
  private BigDecimal analysisConfidence; // 0-100

  @Column(name = "analyzed_at", nullable = false)
  private Instant analyzedAt = Instant.now();

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  /** Trajectory shape patterns. */
  public enum TrajectoryShape {
    HOCKEY_STICK, // Slow start then rapid growth
    EXPONENTIAL, // Consistent exponential growth
    LINEAR, // Steady linear growth
    S_CURVE, // Sigmoid growth (slow-fast-slow)
    SPIKE_AND_PLATEAU, // Rapid growth then flat
    SPIKE_AND_DECAY, // Rapid growth then decline
    MULTI_WAVE, // Multiple growth waves
    FLAT, // No significant growth
    DECLINING // Negative growth
  }
}
