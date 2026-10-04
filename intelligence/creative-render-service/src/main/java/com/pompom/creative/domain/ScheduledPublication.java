package com.pompom.creative.domain;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.time.Instant;
import java.time.ZoneId;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Scheduled publication entity. Represents a publication scheduled for future execution. */
@Entity
@Table(name = "scheduled_publications")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScheduledPublication {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "video_path", nullable = false, columnDefinition = "TEXT")
  private String videoPath;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "render_asset_id")
  private RenderAsset renderAsset;

  @Column(name = "platform_account_id", length = 200)
  private String platformAccountId;

  @Column(name = "title", length = 500)
  private String title;

  @Column(name = "caption", columnDefinition = "TEXT")
  private String caption;

  @Column(name = "hashtags", columnDefinition = "TEXT")
  private String hashtags;

  @Column(name = "is_private")
  private Boolean isPrivate;

  @Column(name = "scheduled_at", nullable = false)
  private Instant scheduledAt;

  @Column(name = "timezone", length = 50)
  private String timezone; // e.g., "Europe/Istanbul", "America/New_York"

  @Column(name = "is_executed", nullable = false)
  private Boolean isExecuted = false;

  @Column(name = "executed_at")
  private Instant executedAt;

  @Column(name = "publication_job_id")
  private UUID publicationJobId;

  @Column(name = "created_by", length = 100)
  private String createdBy;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt = Instant.now();

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }

  /** Check if scheduled time has passed. */
  public boolean isDue() {
    return !isExecuted && Instant.now().isAfter(scheduledAt);
  }

  /** Mark as executed. */
  public void markExecuted(UUID jobId) {
    this.isExecuted = true;
    this.executedAt = Instant.now();
    this.publicationJobId = jobId;
  }

  /** Get timezone or default. */
  public ZoneId getZoneId() {
    if (timezone != null && !timezone.isEmpty()) {
      return ZoneId.of(timezone);
    }
    return ZoneId.systemDefault();
  }
}
