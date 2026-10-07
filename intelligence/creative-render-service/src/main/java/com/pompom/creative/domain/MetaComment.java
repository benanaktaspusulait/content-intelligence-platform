package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(
    name = "meta_comments",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_meta_comment_external",
            columnNames = {"thread_id", "external_comment_id"}))
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetaComment {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "thread_id", nullable = false)
  private MetaCommentThread thread;

  @Column(name = "external_comment_id", nullable = false, length = 200)
  private String externalCommentId;

  @Column(name = "external_parent_comment_id", length = 200)
  private String externalParentCommentId;

  @Column(name = "external_author_id", length = 200)
  private String externalAuthorId;

  @Column(name = "author_display_name", length = 240)
  private String authorDisplayName;

  @Column(name = "text", columnDefinition = "TEXT", nullable = false)
  private String text;

  @Enumerated(EnumType.STRING)
  @Column(name = "direction", nullable = false, length = 20)
  @Builder.Default
  private Direction direction = Direction.INBOUND;

  @Enumerated(EnumType.STRING)
  @Column(name = "moderation_status", nullable = false, length = 30)
  @Builder.Default
  private ModerationStatus moderationStatus = ModerationStatus.RECEIVED;

  @Column(name = "provider_permalink", columnDefinition = "TEXT")
  private String providerPermalink;

  @Column(name = "provider_created_at")
  private Instant providerCreatedAt;

  @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
  @Column(name = "metadata", columnDefinition = "jsonb")
  private String metadataJson;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

  public enum Direction {
    INBOUND,
    OUTBOUND
  }

  public enum ModerationStatus {
    RECEIVED,
    PENDING_REVIEW,
    APPROVED,
    REJECTED,
    RESOLVED
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
