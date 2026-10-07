package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(
    name = "meta_comment_delivery_attempts",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_meta_comment_delivery_attempt",
            columnNames = {"reply_id", "attempt_number"}))
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetaCommentDeliveryAttempt {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "reply_id", nullable = false)
  private MetaCommentReply reply;

  @Column(name = "attempt_number", nullable = false)
  private Integer attemptNumber;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 30)
  private Status status;

  @Column(name = "provider_request_id", length = 200)
  private String providerRequestId;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @Column(name = "started_at", nullable = false)
  @Builder.Default
  private Instant startedAt = Instant.now();

  @Column(name = "completed_at")
  private Instant completedAt;

  public enum Status {
    SUBMITTING,
    SENT,
    FAILED,
    RETRYABLE
  }
}
