package com.pompom.creative.analytics;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Performance prediction entity. Stores pre-publish predictions for content. */
@Entity
@Table(name = "performance_predictions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformancePrediction {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  /** Content ID being predicted. */
  @Column(name = "content_id", nullable = false)
  private Long contentId;

  /** Target platform. */
  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false)
  private PlatformType platform;

  /** Quality score (from QA). */
  @Column(name = "quality_score", precision = 5, scale = 2)
  private BigDecimal qualityScore;

  /** Predicted success probability (0-100%). */
  @Column(name = "success_probability", precision = 5, scale = 2)
  private BigDecimal successProbability;

  /** Predicted performance category. */
  @Column(name = "predicted_category", length = 50)
  private String predictedCategory;

  /** Predicted views at T+24h. */
  @Column(name = "predicted_views_24h")
  private Long predictedViews24h;

  /** Predicted views at T+7d. */
  @Column(name = "predicted_views_7d")
  private Long predictedViews7d;

  /** Predicted engagement rate (%). */
  @Column(name = "predicted_engagement_rate", precision = 5, scale = 2)
  private BigDecimal predictedEngagementRate;

  /** Viral potential score (0-100). */
  @Column(name = "viral_potential", precision = 5, scale = 2)
  private BigDecimal viralPotential;

  /** Confidence level (0-100%). */
  @Column(name = "confidence_level", precision = 5, scale = 2)
  private BigDecimal confidenceLevel;

  /** Prediction model version. */
  @Column(name = "model_version", length = 50)
  private String modelVersion;

  /** Features used for prediction (JSON). */
  @Column(name = "features_used", columnDefinition = "TEXT")
  private String featuresUsed;

  /** Recommendation summary. */
  @Column(name = "recommendation", columnDefinition = "TEXT")
  private String recommendation;

  /** Actual publication job ID (if published). */
  @Column(name = "publication_job_id")
  private UUID publicationJobId;

  /** Prediction timestamp. */
  @Column(name = "predicted_at", nullable = false)
  @Builder.Default
  private Instant predictedAt = Instant.now();
}
