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

/** A/B test entity for comparing content variations. */
@Entity
@Table(name = "ab_tests")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ABTest {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  /** Test name/description. */
  @Column(name = "name", nullable = false)
  private String name;

  /** Test hypothesis. */
  @Column(name = "hypothesis", columnDefinition = "TEXT")
  private String hypothesis;

  /** Test status. */
  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false)
  @Builder.Default
  private TestStatus status = TestStatus.DRAFT;

  /** Platform being tested. */
  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false)
  private PlatformType platform;

  /** Variant A publication job ID. */
  @Column(name = "variant_a_job_id")
  private UUID variantAJobId;

  /** Variant A description. */
  @Column(name = "variant_a_description", columnDefinition = "TEXT")
  private String variantADescription;

  /** Variant B publication job ID. */
  @Column(name = "variant_b_job_id")
  private UUID variantBJobId;

  /** Variant B description. */
  @Column(name = "variant_b_description", columnDefinition = "TEXT")
  private String variantBDescription;

  /** Primary metric to compare. */
  @Column(name = "primary_metric", length = 50)
  private String primaryMetric; // views, engagement_rate, completion_rate, etc.

  /** Winner variant (A or B). */
  @Column(name = "winner", length = 10)
  private String winner;

  /** Statistical significance (p-value). */
  @Column(name = "p_value", precision = 10, scale = 8)
  private BigDecimal pValue;

  /** Confidence level (%). */
  @Column(name = "confidence_level", precision = 5, scale = 2)
  private BigDecimal confidenceLevel;

  /** Effect size (difference between variants). */
  @Column(name = "effect_size", precision = 10, scale = 4)
  private BigDecimal effectSize;

  /** Test conclusion. */
  @Column(name = "conclusion", columnDefinition = "TEXT")
  private String conclusion;

  /** Test created timestamp. */
  @Column(name = "created_at", nullable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  /** Test started timestamp. */
  @Column(name = "started_at")
  private Instant startedAt;

  /** Test completed timestamp. */
  @Column(name = "completed_at")
  private Instant completedAt;

  public enum TestStatus {
    DRAFT,
    RUNNING,
    ANALYZING,
    COMPLETED,
    CANCELLED
  }
}
