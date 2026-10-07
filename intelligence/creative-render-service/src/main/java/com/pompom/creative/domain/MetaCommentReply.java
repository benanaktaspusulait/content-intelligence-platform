package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(
    name = "meta_comment_replies",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_meta_comment_reply_idempotency",
            columnNames = "idempotency_key"))
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetaCommentReply {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "comment_id", nullable = false)
  private MetaComment comment;

  @Column(name = "draft_text", columnDefinition = "TEXT", nullable = false)
  private String draftText;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 30)
  @Builder.Default
  private Status status = Status.DRAFT;

  @Column(name = "idempotency_key", nullable = false, length = 240)
  private String idempotencyKey;

  @Column(name = "approved_by", length = 200)
  private String approvedBy;

  @Column(name = "approved_at")
  private Instant approvedAt;

  @Column(name = "provider_reply_id", length = 200)
  private String providerReplyId;

  @Column(name = "error_message", columnDefinition = "TEXT")
  private String errorMessage;

  @Column(name = "sent_at")
  private Instant sentAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

  public enum Status {
    DRAFT,
    PENDING_APPROVAL,
    APPROVED,
    REJECTED,
    SENT,
    FAILED,
    RETRYABLE
  }

  public void submitForApproval() {
    requireStatus(Status.DRAFT, Status.RETRYABLE);
    status = Status.PENDING_APPROVAL;
    errorMessage = null;
  }

  public void approve(String reviewer) {
    if (reviewer == null || reviewer.isBlank())
      throw new IllegalArgumentException("reviewer is required");
    requireStatus(Status.PENDING_APPROVAL);
    status = Status.APPROVED;
    approvedBy = reviewer.trim();
    approvedAt = Instant.now();
  }

  public void reject(String reviewer, String reason) {
    if (reviewer == null || reviewer.isBlank())
      throw new IllegalArgumentException("reviewer is required");
    requireStatus(Status.PENDING_APPROVAL);
    status = Status.REJECTED;
    approvedBy = reviewer.trim();
    approvedAt = Instant.now();
    errorMessage = reason;
  }

  public void markSent(String providerReplyId) {
    requireStatus(Status.APPROVED);
    status = Status.SENT;
    this.providerReplyId = providerReplyId;
    sentAt = Instant.now();
    errorMessage = null;
  }

  public void markFailed(String message, boolean retryable) {
    if (status != Status.APPROVED && status != Status.RETRYABLE && status != Status.FAILED) {
      throw new IllegalStateException("Reply is not sendable in status " + status);
    }
    status = retryable ? Status.RETRYABLE : Status.FAILED;
    errorMessage = message;
  }

  private void requireStatus(Status... allowed) {
    for (Status value : allowed) if (status == value) return;
    throw new IllegalStateException("Reply is not valid in status " + status);
  }

  @PrePersist
  void prePersist() {
    Instant now = Instant.now();
    if (createdAt == null) createdAt = now;
    if (updatedAt == null) updatedAt = now;
  }

  @PreUpdate
  void preUpdate() {
    updatedAt = Instant.now();
  }
}
