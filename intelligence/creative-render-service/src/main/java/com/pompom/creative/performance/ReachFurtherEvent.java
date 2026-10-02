package com.pompom.creative.performance;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * Reach Further event tracking. Records when Reach Further status is detected and tracks
 * performance impact.
 */
@Entity
@Table(name = "reach_further_events")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReachFurtherEvent {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false)
  private PublicationJob publicationJob;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "detected_at", nullable = false)
  private Instant detectedAt;

  // Performance snapshots
  @Column(name = "views_before")
  private Long viewsBefore;

  @Column(name = "views_1h_after")
  private Long views1hAfter;

  @Column(name = "views_3h_after")
  private Long views3hAfter;

  @Column(name = "views_6h_after")
  private Long views6hAfter;

  @Column(name = "views_24h_after")
  private Long views24hAfter;

  // Audience distribution
  @Column(name = "country_distribution_snapshot", columnDefinition = "TEXT")
  private String countryDistributionSnapshot; // JSON: {"US": 45.2, "TR": 23.1, ...}

  @Column(name = "follower_percentage", precision = 5, scale = 2)
  private BigDecimal followerPercentage;

  @Column(name = "non_follower_percentage", precision = 5, scale = 2)
  private BigDecimal nonFollowerPercentage;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  /** Calculate growth rate from before to 24h after. */
  public Double getGrowthRate() {
    if (viewsBefore == null || viewsBefore == 0 || views24hAfter == null) {
      return null;
    }
    return ((double) (views24hAfter - viewsBefore) / viewsBefore) * 100.0;
  }

  /** Check if this is a strong Reach Further event (>50% non-follower, significant growth). */
  public boolean isStrongReachFurther() {
    return nonFollowerPercentage != null
        && nonFollowerPercentage.compareTo(new BigDecimal("50.0")) > 0
        && getGrowthRate() != null
        && getGrowthRate() > 100.0;
  }
}
