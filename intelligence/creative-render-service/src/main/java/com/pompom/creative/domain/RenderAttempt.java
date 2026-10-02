package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/**
 * One durable attempt at executing a {@link RenderJob}. A job's attempts form an append-only
 * sequence (attempt_number starting at 1, unique per render_job_id): a rerender inserts attempt N+1
 * rather than mutating or rewinding an existing attempt row, so the full execution history of a job
 * is always reconstructable.
 *
 * <p>A worker claims an attempt by acquiring its lease ({@link #leaseOwner}/{@link
 * #leaseExpiresAt}), executes exactly the attempt's current {@link #stage}, persists the next
 * stage, and releases or renews the lease - never more than one stage transition per claim. This
 * replaces the previous single long-lived transaction and recursive rerender in {@code
 * RenderJobOrchestrator} with a design safe for multiple concurrent worker processes.
 */
@Entity
@Table(
    name = "render_attempts",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_render_attempts_job_attempt_number",
            columnNames = {"render_job_id", "attempt_number"}))
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenderAttempt {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Setter(AccessLevel.NONE)
  @Column(name = "render_job_id", nullable = false, updatable = false)
  private UUID renderJobId;

  @Setter(AccessLevel.NONE)
  @Column(name = "attempt_number", nullable = false, updatable = false)
  private Integer attemptNumber;

  @Enumerated(EnumType.STRING)
  @Column(name = "stage", nullable = false, length = 30)
  private RenderExecutionStage stage;

  @Column(name = "provider_job_id", length = 100)
  private String providerJobId;

  /**
   * The {@link RenderAsset} recorded by the DOWNLOADING stage for this attempt, read back by the
   * POST_RENDER_QA stage on a later (possibly different-process) claim. Null until DOWNLOADING
   * completes.
   */
  @Column(name = "asset_id")
  private UUID assetId;

  @Enumerated(EnumType.STRING)
  @Column(name = "provider_job_state", length = 20)
  private ProviderJobState providerJobState;

  @Column(name = "poll_count", nullable = false)
  @Builder.Default
  private Integer pollCount = 0;

  @Column(name = "next_poll_at")
  private Instant nextPollAt;

  @Column(name = "eligible_at", nullable = false)
  @Builder.Default
  private Instant eligibleAt = Instant.now();

  @Column(name = "lease_owner", length = 100)
  private String leaseOwner;

  @Column(name = "lease_expires_at")
  private Instant leaseExpiresAt;

  @Column(name = "lease_heartbeat_at")
  private Instant leaseHeartbeatAt;

  @Column(name = "error_code", length = 50)
  private String errorCode;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @Column(name = "terminal_reason", columnDefinition = "TEXT")
  private String terminalReason;

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

  @Column(name = "entity_version", nullable = false)
  @Version
  private Integer entityVersion;

  @PrePersist
  public void prePersist() {
    Instant now = Instant.now();
    if (this.createdAt == null) {
      this.createdAt = now;
    }
    if (this.updatedAt == null) {
      this.updatedAt = now;
    }
    if (this.eligibleAt == null) {
      this.eligibleAt = now;
    }
    if (this.pollCount == null) {
      this.pollCount = 0;
    }
  }

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }

  /**
   * Builds the first attempt (attempt_number 1, stage QUEUED) for a newly queued job. Both render
   * job creation paths ({@code RenderJobOrchestrator.persistQueuedJob} and {@code
   * RenderJobQueueService.createAfterEvidenceValidation}) must insert this row in the same
   * transaction as the job itself, or the job would have nothing for a worker to ever claim; this
   * factory keeps that construction in one place so the two call sites can't drift apart.
   */
  public static RenderAttempt firstAttemptFor(UUID renderJobId) {
    return RenderAttempt.builder()
        .renderJobId(renderJobId)
        .attemptNumber(1)
        .stage(RenderExecutionStage.QUEUED)
        .pollCount(0)
        .eligibleAt(Instant.now())
        .build();
  }

  /**
   * Terminal stages are never claimable - this specific attempt row never transitions again.
   * Delegates to {@link RenderExecutionStage#isUnclaimable()}, the single source of truth also used
   * to build the claim query's SQL exclusion list in {@code JdbcRenderAttemptClaimRepository}.
   */
  public boolean isTerminal() {
    return stage.isUnclaimable();
  }
}
