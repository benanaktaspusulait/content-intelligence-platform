package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/** Durable execution record for one publication side-effect attempt. */
@Entity
@Table(
    name = "publication_attempts",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_publication_attempt_job_number",
            columnNames = {"publication_job_id", "attempt_number"}))
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PublicationAttempt {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "publication_job_id", nullable = false, updatable = false)
  private UUID publicationJobId;

  @Column(name = "attempt_number", nullable = false, updatable = false)
  private Integer attemptNumber;

  @Enumerated(EnumType.STRING)
  @Column(name = "stage", nullable = false, length = 30)
  private PublicationExecutionStage stage;

  @Column(name = "eligible_at", nullable = false)
  private Instant eligibleAt;

  @Column(name = "lease_owner", length = 100)
  private String leaseOwner;

  @Column(name = "lease_expires_at")
  private Instant leaseExpiresAt;

  @Column(name = "provider_submission_id", length = 200)
  private String providerSubmissionId;

  @Column(name = "platform_post_id", length = 200)
  private String platformPostId;

  @Column(name = "platform_video_id", length = 200)
  private String platformVideoId;

  @Column(name = "authoritative_permalink", columnDefinition = "TEXT")
  private String authoritativePermalink;

  @Column(name = "error_code", length = 80)
  private String errorCode;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Builder.Default
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Builder.Default
  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt = Instant.now();

  @Version
  @Column(name = "entity_version", nullable = false)
  private Integer entityVersion;

  @PreUpdate
  void preUpdate() {
    updatedAt = Instant.now();
  }

  public static PublicationAttempt firstAttemptFor(UUID publicationJobId) {
    return PublicationAttempt.builder()
        .publicationJobId(publicationJobId)
        .attemptNumber(1)
        .stage(PublicationExecutionStage.QUEUED)
        .eligibleAt(Instant.now())
        .build();
  }
}
