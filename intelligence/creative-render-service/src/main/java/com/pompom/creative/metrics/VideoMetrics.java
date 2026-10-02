package com.pompom.creative.metrics;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/** Video metrics collected from platform APIs. Tracks views, engagement, retention over time. */
@Entity
@Table(name = "video_metrics")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VideoMetrics {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false)
  private PublicationJob publicationJob;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "platform_video_id", nullable = false, length = 100)
  private String platformVideoId;

  // Basic engagement metrics
  @Column(name = "views", nullable = false)
  private Long views = 0L;

  @Column(name = "likes", nullable = false)
  private Long likes = 0L;

  @Column(name = "comments", nullable = false)
  private Long comments = 0L;

  @Column(name = "shares", nullable = false)
  private Long shares = 0L;

  @Column(name = "saves", nullable = false)
  private Long saves = 0L;

  // Retention metrics
  @Column(name = "completion_rate", precision = 5, scale = 2)
  private BigDecimal completionRate; // 0-100%

  @Column(name = "avg_watch_time_seconds", precision = 6, scale = 2)
  private BigDecimal avgWatchTimeSeconds;

  @Column(name = "total_watch_time_seconds")
  private Long totalWatchTimeSeconds;

  @Column(name = "impressions")
  private Long impressions;

  @Column(name = "reach")
  private Long reach;

  @Column(name = "clicks")
  private Long clicks;

  // Platform-specific metrics (stored as JSON if needed)
  @Column(name = "platform_specific_data", columnDefinition = "jsonb")
  private String platformSpecificData;

  // Collection timing
  @Column(name = "collected_at", nullable = false)
  private Instant collectedAt;

  @Column(name = "time_since_publish_minutes", nullable = false)
  private Integer timeSincePublishMinutes; // T+30m, T+60m, etc.

  // Metadata
  @Column(name = "collection_source", length = 50)
  private String collectionSource; // API, MANUAL_ENTRY, ESTIMATED

  @Column(name = "is_final")
  private Boolean isFinal = false; // T+30d is final

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  /** Calculate engagement rate: (likes + comments + shares) / views * 100 */
  public BigDecimal calculateEngagementRate() {
    if (views == null || views == 0) {
      return BigDecimal.ZERO;
    }

    long totalEngagement =
        (likes != null ? likes : 0)
            + (comments != null ? comments : 0)
            + (shares != null ? shares : 0);

    return BigDecimal.valueOf(totalEngagement)
        .multiply(BigDecimal.valueOf(100))
        .divide(BigDecimal.valueOf(views), 2, java.math.RoundingMode.HALF_UP);
  }

  /** Calculate virality score: shares / views * 100 */
  public BigDecimal calculateViralityScore() {
    if (views == null || views == 0) {
      return BigDecimal.ZERO;
    }

    return BigDecimal.valueOf(shares != null ? shares : 0)
        .multiply(BigDecimal.valueOf(100))
        .divide(BigDecimal.valueOf(views), 2, java.math.RoundingMode.HALF_UP);
  }
}
