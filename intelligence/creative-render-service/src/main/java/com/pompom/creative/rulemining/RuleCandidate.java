package com.pompom.creative.rulemining;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * Mined rule candidate from performance pattern analysis. Represents an actionable insight: "IF
 * condition THEN likely_outcome (confidence%)"
 */
@Entity
@Table(name = "rule_candidates")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RuleCandidate {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "rule_name", nullable = false, length = 200)
  private String ruleName;

  @Column(name = "rule_description", nullable = false, columnDefinition = "TEXT")
  private String ruleDescription;

  // Rule pattern: IF <condition> THEN <outcome>
  @Column(name = "condition", nullable = false, columnDefinition = "TEXT")
  private String condition; // e.g., "trajectory_shape = HOCKEY_STICK AND velocity_first_24h > 500"

  @Column(name = "outcome", nullable = false, columnDefinition = "TEXT")
  private String outcome; // e.g., "category = BREAKOUT"

  @Enumerated(EnumType.STRING)
  @Column(name = "rule_type", nullable = false, length = 30)
  private RuleType ruleType;

  @Enumerated(EnumType.STRING)
  @Column(name = "rule_category", nullable = false, length = 30)
  private RuleCategory ruleCategory;

  // Statistical evidence
  @Column(name = "support_count", nullable = false)
  private Integer supportCount; // Number of cases matching the rule

  @Column(name = "total_cases", nullable = false)
  private Integer totalCases; // Total cases analyzed

  @Column(name = "confidence", precision = 5, scale = 2, nullable = false)
  private BigDecimal confidence; // 0-100%: P(outcome | condition)

  @Column(name = "lift", precision = 5, scale = 2)
  private BigDecimal lift; // Lift score: P(condition AND outcome) / (P(condition) * P(outcome))

  // Actionability
  @Column(name = "is_actionable", nullable = false)
  private Boolean isActionable = true;

  @Column(name = "action_recommendation", columnDefinition = "TEXT")
  private String actionRecommendation; // What to do with this rule

  // Validation
  @Enumerated(EnumType.STRING)
  @Column(name = "validation_status", length = 30)
  private ValidationStatus validationStatus = ValidationStatus.CANDIDATE;

  @Column(name = "validated_at")
  private Instant validatedAt;

  @Column(name = "validation_notes", columnDefinition = "TEXT")
  private String validationNotes;

  // Metadata
  @Column(name = "mining_run_id")
  private UUID miningRunId;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  /** Rule type classification. */
  public enum RuleType {
    TRAJECTORY_PATTERN, // Based on trajectory shape/velocity
    PERFORMANCE_THRESHOLD, // Based on performance metrics thresholds
    CORRELATION_INSIGHT, // Based on correlation analysis
    TEMPORAL_PATTERN, // Based on time-series patterns
    COMPOSITE // Combination of multiple factors
  }

  /** Rule category for organization. */
  public enum RuleCategory {
    EARLY_DETECTION, // Predict performance in first 24h
    BREAKOUT_SIGNAL, // Identify breakout candidates
    OPTIMIZATION_HINT, // Suggest optimization strategies
    WARNING_SIGNAL, // Identify underperforming content
    BENCHMARK_RULE // Define success benchmarks
  }

  /** Validation status. */
  public enum ValidationStatus {
    CANDIDATE, // Newly mined, not validated
    VALIDATED, // Human reviewed and approved
    REJECTED, // Human reviewed and rejected
    IN_USE, // Actively used in production
    DEPRECATED // No longer valid/relevant
  }

  /**
   * Calculate rule quality score (0-100). Based on: confidence (50%), support count (30%), lift
   * (20%)
   */
  public BigDecimal calculateQualityScore() {
    BigDecimal confScore = confidence.multiply(BigDecimal.valueOf(0.5));

    // Support score: higher is better, capped at 100
    BigDecimal supportScore =
        BigDecimal.valueOf(Math.min(supportCount * 10, 100)).multiply(BigDecimal.valueOf(0.3));

    // Lift score: >1 is good, normalize to 0-100
    BigDecimal liftScore =
        lift != null
            ? lift.subtract(BigDecimal.ONE)
                .multiply(BigDecimal.valueOf(50))
                .min(BigDecimal.valueOf(100))
            : BigDecimal.ZERO;
    liftScore = liftScore.multiply(BigDecimal.valueOf(0.2));

    return confScore.add(supportScore).add(liftScore);
  }
}
