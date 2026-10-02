package com.pompom.creative.correlation;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * Statistical correlation analysis between quality scores and performance metrics. Calculates
 * Pearson correlation coefficients for various quality-performance pairs.
 */
@Entity
@Table(name = "correlation_analyses")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CorrelationAnalysis {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "analysis_name", nullable = false, length = 100)
  private String analysisName;

  @Column(name = "description", columnDefinition = "text")
  private String description;

  // Sample size
  @Column(name = "sample_size", nullable = false)
  private Integer sampleSize;

  // Visual Quality correlations
  @Column(name = "visual_quality_vs_views", precision = 5, scale = 4)
  private BigDecimal visualQualityVsViews; // Pearson r

  @Column(name = "visual_quality_vs_engagement", precision = 5, scale = 4)
  private BigDecimal visualQualityVsEngagement;

  @Column(name = "visual_quality_vs_completion", precision = 5, scale = 4)
  private BigDecimal visualQualityVsCompletion;

  @Column(name = "visual_quality_vs_velocity", precision = 5, scale = 4)
  private BigDecimal visualQualityVsVelocity;

  // Hook Effectiveness correlations
  @Column(name = "hook_vs_views", precision = 5, scale = 4)
  private BigDecimal hookVsViews;

  @Column(name = "hook_vs_engagement", precision = 5, scale = 4)
  private BigDecimal hookVsEngagement;

  @Column(name = "hook_vs_completion", precision = 5, scale = 4)
  private BigDecimal hookVsCompletion;

  @Column(name = "hook_vs_velocity", precision = 5, scale = 4)
  private BigDecimal hookVsVelocity;

  // Pacing correlations
  @Column(name = "pacing_vs_views", precision = 5, scale = 4)
  private BigDecimal pacingVsViews;

  @Column(name = "pacing_vs_engagement", precision = 5, scale = 4)
  private BigDecimal pacingVsEngagement;

  @Column(name = "pacing_vs_completion", precision = 5, scale = 4)
  private BigDecimal pacingVsCompletion;

  @Column(name = "pacing_vs_velocity", precision = 5, scale = 4)
  private BigDecimal pacingVsVelocity;

  // Emotional Impact correlations
  @Column(name = "emotional_vs_views", precision = 5, scale = 4)
  private BigDecimal emotionalVsViews;

  @Column(name = "emotional_vs_engagement", precision = 5, scale = 4)
  private BigDecimal emotionalVsEngagement;

  @Column(name = "emotional_vs_completion", precision = 5, scale = 4)
  private BigDecimal emotionalVsCompletion;

  @Column(name = "emotional_vs_velocity", precision = 5, scale = 4)
  private BigDecimal emotionalVsVelocity;

  // Brand Consistency correlations
  @Column(name = "brand_vs_views", precision = 5, scale = 4)
  private BigDecimal brandVsViews;

  @Column(name = "brand_vs_engagement", precision = 5, scale = 4)
  private BigDecimal brandVsEngagement;

  @Column(name = "brand_vs_completion", precision = 5, scale = 4)
  private BigDecimal brandVsCompletion;

  @Column(name = "brand_vs_velocity", precision = 5, scale = 4)
  private BigDecimal brandVsVelocity;

  // Overall Quality Score correlations
  @Column(name = "overall_score_vs_views", precision = 5, scale = 4)
  private BigDecimal overallScoreVsViews;

  @Column(name = "overall_score_vs_engagement", precision = 5, scale = 4)
  private BigDecimal overallScoreVsEngagement;

  @Column(name = "overall_score_vs_completion", precision = 5, scale = 4)
  private BigDecimal overallScoreVsCompletion;

  @Column(name = "overall_score_vs_velocity", precision = 5, scale = 4)
  private BigDecimal overallScoreVsVelocity;

  // Statistical significance
  @Column(name = "strongest_correlation_factor", length = 50)
  private String
      strongestCorrelationFactor; // VISUAL_QUALITY, HOOK, PACING, EMOTIONAL, BRAND, OVERALL

  @Column(name = "strongest_correlation_value", precision = 5, scale = 4)
  private BigDecimal strongestCorrelationValue;

  @Column(name = "weakest_correlation_factor", length = 50)
  private String weakestCorrelationFactor;

  @Column(name = "weakest_correlation_value", precision = 5, scale = 4)
  private BigDecimal weakestCorrelationValue;

  // Analysis metadata
  @Column(name = "p_value_threshold", precision = 5, scale = 4)
  private BigDecimal pValueThreshold = BigDecimal.valueOf(0.05); // 95% confidence

  @Column(name = "analysis_confidence", precision = 5, scale = 2)
  private BigDecimal analysisConfidence; // 0-100

  @Column(name = "analyzed_at", nullable = false)
  private Instant analyzedAt = Instant.now();

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  /** Interpret correlation strength. |r| < 0.3: weak, 0.3-0.7: moderate, > 0.7: strong */
  public static String interpretCorrelation(BigDecimal r) {
    if (r == null) return "UNKNOWN";

    BigDecimal abs = r.abs();
    if (abs.compareTo(BigDecimal.valueOf(0.7)) > 0) {
      return "STRONG";
    } else if (abs.compareTo(BigDecimal.valueOf(0.3)) > 0) {
      return "MODERATE";
    } else {
      return "WEAK";
    }
  }
}
