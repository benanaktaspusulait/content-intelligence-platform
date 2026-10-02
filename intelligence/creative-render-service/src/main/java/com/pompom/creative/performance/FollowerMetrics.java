package com.pompom.creative.performance;

import com.pompom.creative.domain.PublicationJob;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * Follower metrics and conversion tracking. Tracks follower growth, profile visits, and audience
 * discovery metrics per video.
 */
@Entity
@Table(name = "follower_metrics")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FollowerMetrics {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false)
  private PublicationJob publicationJob;

  // Follower growth
  @Column(name = "followers_before")
  private Integer followersBefore;

  @Column(name = "followers_after")
  private Integer followersAfter;

  @Column(name = "followers_gained")
  private Integer followersGained;

  @Column(name = "profile_visits")
  private Integer profileVisits;

  @Column(name = "follower_conversion_rate", precision = 5, scale = 2)
  private BigDecimal followerConversionRate; // (followers_gained / profile_visits) * 100

  // Audience composition
  @Column(name = "us_audience_percentage", precision = 5, scale = 2)
  private BigDecimal usAudiencePercentage;

  @Column(name = "non_follower_percentage", precision = 5, scale = 2)
  private BigDecimal nonFollowerPercentage;

  // Geographic breakdown
  @Column(name = "top_countries", columnDefinition = "TEXT")
  private String topCountries; // JSON: [{"country": "US", "percentage": 45.2}, ...]

  // Discovery score (non-follower 65% + US audience 35%)
  @Column(name = "discovery_score", precision = 5, scale = 2)
  private BigDecimal discoveryScore;

  // Timestamps
  @Column(name = "measured_at", nullable = false)
  private Instant measuredAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  /** Calculate follower conversion rate from followers gained and profile visits. */
  public void calculateConversionRate() {
    if (profileVisits != null && profileVisits > 0 && followersGained != null) {
      this.followerConversionRate =
          BigDecimal.valueOf(followersGained)
              .multiply(BigDecimal.valueOf(100))
              .divide(BigDecimal.valueOf(profileVisits), 2, RoundingMode.HALF_UP);
    }
  }

  /**
   * Calculate discovery score from non-follower % and US audience %. Formula: (nonFollower * 0.65)
   * + (usAudience * 0.35)
   */
  public void calculateDiscoveryScore() {
    if (nonFollowerPercentage != null && usAudiencePercentage != null) {
      BigDecimal nonFollowerWeight = nonFollowerPercentage.multiply(new BigDecimal("0.65"));
      BigDecimal usAudienceWeight = usAudiencePercentage.multiply(new BigDecimal("0.35"));
      this.discoveryScore =
          nonFollowerWeight.add(usAudienceWeight).setScale(2, RoundingMode.HALF_UP);
    }
  }

  /** Check if this is a strong discovery video (high non-follower %, US reach). */
  public boolean isStrongDiscovery() {
    return discoveryScore != null && discoveryScore.compareTo(new BigDecimal("50.0")) > 0;
  }

  /** Check if this is a strong follower converter (>5% conversion). */
  public boolean isStrongConverter() {
    return followerConversionRate != null
        && followerConversionRate.compareTo(new BigDecimal("5.0")) > 0;
  }

  @PrePersist
  @PreUpdate
  public void calculateMetrics() {
    // Auto-calculate followers gained
    if (followersBefore != null && followersAfter != null) {
      this.followersGained = followersAfter - followersBefore;
    }

    // Auto-calculate rates
    calculateConversionRate();
    calculateDiscoveryScore();
  }
}
