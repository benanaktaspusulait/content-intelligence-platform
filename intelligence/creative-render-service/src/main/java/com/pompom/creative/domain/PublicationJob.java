package com.pompom.creative.domain;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Publication job entity. Tracks upload progress and status for social media publishing. */
@Entity
@Table(name = "publication_jobs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PublicationJob {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 20)
  private PublicationStatus status;

  @Column(name = "video_path", nullable = false, columnDefinition = "TEXT")
  private String videoPath;

  @Column(name = "title", length = 500)
  private String title;

  @Column(name = "caption", columnDefinition = "TEXT")
  private String caption;

  @Column(name = "hashtags", columnDefinition = "TEXT")
  private String hashtags; // JSON array or comma-separated

  @Column(name = "is_private")
  private Boolean isPrivate;

  @Column(name = "platform_post_id", length = 100)
  private String platformPostId;

  @Column(name = "platform_video_id", length = 100)
  private String platformVideoId;

  @Column(name = "post_url", columnDefinition = "TEXT")
  private String postUrl;

  @Column(name = "progress_percent")
  private Integer progressPercent;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @Column(name = "retry_count")
  private Integer retryCount = 0;

  @Column(name = "max_retries")
  private Integer maxRetries = 3;

  @Column(name = "queued_at", nullable = false)
  private Instant queuedAt = Instant.now();

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt = Instant.now();

  // Strategic tracking fields (V25)
  @Column(name = "manual_intervention")
  private Boolean manualIntervention = false;

  @Column(name = "intervention_type", length = 50)
  private String interventionType;

  @Column(name = "intervention_timestamp")
  private Instant interventionTimestamp;

  @Column(name = "intervention_notes", columnDefinition = "TEXT")
  private String interventionNotes;

  @Column(name = "is_prime_slot")
  private Boolean isPrimeSlot = false;

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }

  /** Update status and timestamp accordingly. */
  public void updateStatus(PublicationStatus newStatus) {
    this.status = newStatus;
    this.updatedAt = Instant.now();

    switch (newStatus) {
      case UPLOADING:
        if (this.startedAt == null) {
          this.startedAt = Instant.now();
        }
        break;
      case PUBLISHED:
      case FAILED:
      case CANCELLED:
        if (this.completedAt == null) {
          this.completedAt = Instant.now();
        }
        break;
    }
  }

  /** Check if job can be retried. */
  public boolean canRetry() {
    return this.status == PublicationStatus.FAILED && this.retryCount < this.maxRetries;
  }

  /** Increment retry count. */
  public void incrementRetry() {
    this.retryCount++;
  }

  /** Check if job is in a terminal state. */
  public boolean isTerminal() {
    return this.status == PublicationStatus.PUBLISHED
        || this.status == PublicationStatus.FAILED
        || this.status == PublicationStatus.CANCELLED;
  }
}
