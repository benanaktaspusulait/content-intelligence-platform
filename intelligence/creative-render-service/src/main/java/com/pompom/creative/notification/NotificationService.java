package com.pompom.creative.notification;

import com.pompom.creative.websocket.WebSocketEventPublisher;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Service for managing in-app notifications. */
@Service
@Slf4j
@RequiredArgsConstructor
public class NotificationService {

  private final NotificationRepository notificationRepo;
  private final WebSocketEventPublisher webSocketPublisher;

  /** Create and save a new notification. */
  @Transactional
  public Notification createNotification(
      Notification.NotificationType type,
      String title,
      String message,
      UUID relatedEntityId,
      String relatedEntityType,
      String link,
      Notification.Priority priority) {
    log.info("Creating notification: type={}, title={}", type, title);

    Notification notification =
        Notification.builder()
            .type(type)
            .title(title)
            .message(message)
            .relatedEntityId(relatedEntityId)
            .relatedEntityType(relatedEntityType)
            .link(link)
            .priority(priority)
            .isRead(false)
            .createdAt(Instant.now())
            .build();

    notification = notificationRepo.save(notification);

    // Publish via WebSocket (to all users in this simple version)
    webSocketPublisher.broadcastToTopic("/topic/notifications", notification);

    return notification;
  }

  /** Get all unread notifications. */
  @Transactional(readOnly = true)
  public List<Notification> getUnreadNotifications() {
    return notificationRepo.findByIsReadFalseOrderByCreatedAtDesc();
  }

  /** Get all notifications. */
  @Transactional(readOnly = true)
  public List<Notification> getAllNotifications() {
    return notificationRepo.findAllByOrderByCreatedAtDesc();
  }

  /** Mark notification as read. */
  @Transactional
  public void markAsRead(UUID notificationId) {
    log.info("Marking notification as read: id={}", notificationId);

    Notification notification =
        notificationRepo
            .findById(notificationId)
            .orElseThrow(
                () -> new IllegalArgumentException("Notification not found: " + notificationId));

    notification.setIsRead(true);
    notification.setReadAt(Instant.now());
    notificationRepo.save(notification);
  }

  /** Mark all notifications as read. */
  @Transactional
  public void markAllAsRead() {
    log.info("Marking all notifications as read");

    List<Notification> unread = notificationRepo.findByIsReadFalseOrderByCreatedAtDesc();
    Instant now = Instant.now();

    unread.forEach(
        n -> {
          n.setIsRead(true);
          n.setReadAt(now);
        });

    notificationRepo.saveAll(unread);
  }

  /** Get unread notification count. */
  @Transactional(readOnly = true)
  public long getUnreadCount() {
    return notificationRepo.countByIsReadFalse();
  }

  /** Delete notification. */
  @Transactional
  public void deleteNotification(UUID notificationId) {
    log.info("Deleting notification: id={}", notificationId);
    notificationRepo.deleteById(notificationId);
  }

  /** Clean up old read notifications (older than 30 days). */
  @Transactional
  public void cleanupOldNotifications() {
    log.info("Cleaning up old notifications");
    Instant thirtyDaysAgo = Instant.now().minus(java.time.Duration.ofDays(30));
    notificationRepo.deleteByIsReadTrueAndCreatedAtBefore(thirtyDaysAgo);
  }
}
