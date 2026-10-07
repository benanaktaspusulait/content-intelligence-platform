package com.pompom.creative.domain;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(
    name = "meta_comment_threads",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_meta_comment_thread_external",
            columnNames = {"platform", "external_thread_key"}))
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetaCommentThread {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "external_account_id", nullable = false, length = 200)
  private String externalAccountId;

  @Column(name = "external_object_id", nullable = false, length = 200)
  private String externalObjectId;

  @Column(name = "external_thread_key", nullable = false, length = 420)
  private String externalThreadKey;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 30)
  @Builder.Default
  private Status status = Status.OPEN;

  @Column(name = "last_provider_event_at")
  private Instant lastProviderEventAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

  public enum Status {
    OPEN,
    CLOSED,
    ARCHIVED
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
