package com.pompom.creative.domain;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Webhook event entity. Stores incoming webhook events from social media platforms. */
@Entity
@Table(name = "webhook_events")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WebhookEvent {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "event_type", nullable = false, length = 100)
  private String eventType; // e.g., "video.processing_complete", "video.published"

  @Column(name = "platform_post_id", length = 100)
  private String platformPostId;

  @Column(name = "publication_job_id")
  private UUID publicationJobId;

  @Column(name = "payload", columnDefinition = "TEXT", nullable = false)
  private String payload; // JSON payload from platform

  @Column(name = "signature", columnDefinition = "TEXT")
  private String signature; // Webhook signature for verification

  @Column(name = "is_processed", nullable = false)
  private Boolean isProcessed = false;

  @Column(name = "processed_at")
  private Instant processedAt;

  @Column(name = "processing_error", columnDefinition = "TEXT")
  private String processingError;

  @Column(name = "retry_count")
  private Integer retryCount = 0;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt = Instant.now();

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }

  /** Mark event as processed. */
  public void markProcessed() {
    this.isProcessed = true;
    this.processedAt = Instant.now();
  }

  /** Mark event as failed with error. */
  public void markFailed(String error) {
    this.processingError = error;
    this.retryCount++;
  }

  /** Check if event can be retried. */
  public boolean canRetry() {
    return !isProcessed && retryCount < 3;
  }
}
