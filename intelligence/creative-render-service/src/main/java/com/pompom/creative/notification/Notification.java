package com.pompom.creative.notification;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

/** In-app notification entity. */
@Entity
@Table(name = "notifications")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Notification {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  /** Notification type. */
  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private NotificationType type;

  /** Notification title. */
  @Column(nullable = false)
  private String title;

  /** Notification message. */
  @Column(columnDefinition = "TEXT")
  private String message;

  /** Related entity ID (render job, publication job, etc.). */
  private UUID relatedEntityId;

  /** Related entity type (RENDER_JOB, PUBLICATION_JOB, METRICS, etc.). */
  private String relatedEntityType;

  /** Link/URL to navigate to. */
  private String link;

  /** Priority level. */
  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  @Builder.Default
  private Priority priority = Priority.NORMAL;

  /** Whether notification has been read. */
  @Column(nullable = false)
  @Builder.Default
  private Boolean isRead = false;

  /** Creation timestamp. */
  @Column(nullable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  /** Read timestamp. */
  private Instant readAt;

  public enum NotificationType {
    RENDER_STARTED,
    RENDER_COMPLETED,
    RENDER_FAILED,
    PUBLICATION_SUCCESS,
    PUBLICATION_FAILED,
    METRICS_MILESTONE,
    PERFORMANCE_ALERT,
    BUDGET_WARNING,
    SYSTEM_INFO
  }

  public enum Priority {
    LOW,
    NORMAL,
    HIGH,
    URGENT
  }
}
