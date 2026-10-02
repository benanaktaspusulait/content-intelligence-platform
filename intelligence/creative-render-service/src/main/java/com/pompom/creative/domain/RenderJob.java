package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "render_jobs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenderJob {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  // Immutable content/prompt snapshot: captured at queue time and never mutated afterwards, so a
  // render always reproduces exactly the prompt it was created from. No public setters are
  // generated (@Setter(AccessLevel.NONE)) and the columns are updatable=false.
  @Setter(AccessLevel.NONE)
  @Column(name = "content_id", nullable = false, updatable = false)
  private Long contentId;

  @Setter(AccessLevel.NONE)
  @Column(name = "prompt_version_id", nullable = false, updatable = false)
  private Long promptVersionId;

  @Setter(AccessLevel.NONE)
  @Column(name = "content_title_snapshot", nullable = false, updatable = false)
  private String contentTitleSnapshot;

  @Setter(AccessLevel.NONE)
  @Column(name = "prompt_version_number_snapshot", nullable = false, updatable = false)
  private Integer promptVersionNumberSnapshot;

  @Setter(AccessLevel.NONE)
  @Column(name = "prompt_sha256", length = 64, nullable = false, updatable = false)
  private String promptSha256;

  @Setter(AccessLevel.NONE)
  @Column(
      name = "prompt_text_snapshot",
      columnDefinition = "TEXT",
      nullable = false,
      updatable = false)
  private String promptTextSnapshot;

  // Immutable validation evidence snapshot: the accepted ValidationEvidenceDto this job was
  // queued against, copied in at queue time per the design doc ("The accepted evidence is copied
  // into the render job transaction"). Never mutated after insert. Nullable: legacy rows copied
  // by V2 predate this evidence model and carry no evidence; RenderJobQueueService (the only
  // path that creates a row with evidence) always populates every field here.
  @Setter(AccessLevel.NONE)
  @Column(name = "validation_record_id", updatable = false)
  private Long validationRecordId;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_deterministic_ruleset_version", updatable = false)
  private String evidenceDeterministicRulesetVersion;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_semantic_provider", updatable = false)
  private String evidenceSemanticProvider;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_semantic_model_version", updatable = false)
  private String evidenceSemanticModelVersion;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_producibility_validator_version", updatable = false)
  private String evidenceProducibilityValidatorVersion;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_independent_revalidation_id", updatable = false)
  private UUID evidenceIndependentRevalidationId;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_independently_revalidated_at", updatable = false)
  private Instant evidenceIndependentlyRevalidatedAt;

  @Setter(AccessLevel.NONE)
  @Column(name = "evidence_validated_at", updatable = false)
  private Instant evidenceValidatedAt;

  // Idempotency: a client-supplied key (the Idempotency-Key header) plus a canonical fingerprint
  // of the request payload. The combination lets RenderJobQueueService distinguish a legitimate
  // replay (same key, same fingerprint - return the existing job) from a conflicting reuse of the
  // same key with different parameters (same key, different fingerprint - 409). Nullable for the
  // same legacy-row reason as the evidence fields above.
  @Setter(AccessLevel.NONE)
  @Column(name = "idempotency_key", updatable = false, unique = true)
  private String idempotencyKey;

  @Setter(AccessLevel.NONE)
  @Column(name = "request_fingerprint", length = 64, updatable = false)
  private String requestFingerprint;

  @Enumerated(EnumType.STRING)
  @Column(name = "job_type", nullable = false, length = 20)
  private JobType jobType;

  @Column(name = "openart_job_id", length = 100)
  private String openartJobId;

  @Column(name = "openart_model", nullable = false, length = 50)
  private String openartModel;

  @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
  @Column(name = "openart_params", columnDefinition = "jsonb")
  private String openartParams;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 30)
  @Builder.Default
  private RenderJobStatus status = RenderJobStatus.QUEUED;

  @Column(name = "attempt_number", nullable = false)
  @Builder.Default
  private Integer attemptNumber = 1;

  @Column(name = "max_attempts", nullable = false)
  @Builder.Default
  private Integer maxAttempts = 3;

  @Column(name = "credits_estimated", precision = 10, scale = 2)
  private BigDecimal creditsEstimated;

  @Column(name = "credits_actual", precision = 10, scale = 2)
  private BigDecimal creditsActual;

  @Column(name = "queued_at", nullable = false)
  @Builder.Default
  private Instant queuedAt = Instant.now();

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Column(name = "failed_at")
  private Instant failedAt;

  @Column(name = "error_code", length = 50)
  private String errorCode;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

  @Column(name = "entity_version", nullable = false)
  @Version
  private Integer entityVersion = 1;

  public enum JobType {
    FIRST_FRAME,
    VIDEO
  }

  public enum RenderJobStatus {
    QUEUED,
    GENERATING,
    POLLING,
    DOWNLOADING,
    COMPLETE,
    FAILED,
    ABANDONED
  }

  @PrePersist
  public void prePersist() {
    Instant now = Instant.now();
    if (this.createdAt == null) {
      this.createdAt = now;
    }
    if (this.updatedAt == null) {
      this.updatedAt = now;
    }
    if (this.queuedAt == null) {
      this.queuedAt = now;
    }
    if (this.status == null) {
      this.status = RenderJobStatus.QUEUED;
    }
    if (this.attemptNumber == null) {
      this.attemptNumber = 1;
    }
    if (this.maxAttempts == null) {
      this.maxAttempts = 3;
    }
  }

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }
}
