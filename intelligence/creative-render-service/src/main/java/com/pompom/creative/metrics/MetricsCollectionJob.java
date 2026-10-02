package com.pompom.creative.metrics;

import com.pompom.creative.domain.PublicationJob;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/** Scheduled metrics collection job. Collects metrics at: T+30m, T+1h, T+6h, T+24h, T+7d, T+30d */
@Entity
@Table(name = "metrics_collection_jobs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricsCollectionJob {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "publication_job_id", nullable = false)
  private PublicationJob publicationJob;

  @Column(name = "collection_point", nullable = false, length = 20)
  private String collectionPoint; // T+30M, T+1H, T+6H, T+24H, T+7D, T+30D

  @Column(name = "scheduled_at", nullable = false)
  private Instant scheduledAt;

  @Column(name = "executed_at")
  private Instant executedAt;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 20)
  private JobStatus status = JobStatus.PENDING;

  @Column(name = "retry_count")
  private Integer retryCount = 0;

  @Column(name = "max_retries")
  private Integer maxRetries = 3;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "collected_metrics_id")
  private VideoMetrics collectedMetrics;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  public enum JobStatus {
    PENDING,
    IN_PROGRESS,
    COMPLETED,
    FAILED,
    SKIPPED
  }

  /** Check if job should be executed. */
  public boolean isDue() {
    return status == JobStatus.PENDING && scheduledAt != null && Instant.now().isAfter(scheduledAt);
  }

  /** Check if job can be retried. */
  public boolean canRetry() {
    return status == JobStatus.FAILED
        && retryCount != null
        && maxRetries != null
        && retryCount < maxRetries;
  }
}
