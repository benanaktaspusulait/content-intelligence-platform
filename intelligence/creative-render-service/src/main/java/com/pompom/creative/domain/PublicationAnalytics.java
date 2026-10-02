package com.pompom.creative.domain;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Publication analytics entity. Stores performance metrics for published content. */
@Entity
@Table(name = "publication_analytics")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PublicationAnalytics {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "publication_job_id", nullable = false)
  private UUID publicationJobId;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "platform_post_id", length = 100)
  private String platformPostId;

  @Column(name = "views")
  private Long views;

  @Column(name = "likes")
  private Long likes;

  @Column(name = "comments")
  private Long comments;

  @Column(name = "shares")
  private Long shares;

  @Column(name = "saves")
  private Long saves; // Instagram/TikTok

  @Column(name = "engagement_rate")
  private Double engagementRate;

  @Column(name = "watch_time_seconds")
  private Long watchTimeSeconds; // YouTube

  @Column(name = "average_view_duration_seconds")
  private Double averageViewDurationSeconds;

  @Column(name = "impressions")
  private Long impressions;

  @Column(name = "reach")
  private Long reach;

  @Column(name = "clicks")
  private Long clicks;

  @Column(name = "fetched_at", nullable = false)
  private Instant fetchedAt = Instant.now();

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt = Instant.now();

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }

  /** Calculate engagement rate if views available. */
  public void calculateEngagementRate() {
    if (views != null && views > 0) {
      long totalEngagements =
          (likes != null ? likes : 0)
              + (comments != null ? comments : 0)
              + (shares != null ? shares : 0)
              + (saves != null ? saves : 0);

      this.engagementRate = (double) totalEngagements / views * 100;
    }
  }

  /** Update metrics from new data. */
  public void updateMetrics(PublicationAnalytics newData) {
    this.views = newData.getViews();
    this.likes = newData.getLikes();
    this.comments = newData.getComments();
    this.shares = newData.getShares();
    this.saves = newData.getSaves();
    this.watchTimeSeconds = newData.getWatchTimeSeconds();
    this.averageViewDurationSeconds = newData.getAverageViewDurationSeconds();
    this.impressions = newData.getImpressions();
    this.reach = newData.getReach();
    this.clicks = newData.getClicks();
    this.fetchedAt = Instant.now();

    calculateEngagementRate();
  }
}
