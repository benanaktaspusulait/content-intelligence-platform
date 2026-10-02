package com.pompom.creative.notification;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

@Repository
public interface NotificationRepository extends JpaRepository<Notification, UUID> {

  /** Find all unread notifications ordered by creation date (newest first). */
  List<Notification> findByIsReadFalseOrderByCreatedAtDesc();

  /** Find all notifications ordered by creation date (newest first). */
  List<Notification> findAllByOrderByCreatedAtDesc();

  /** Find notifications by type. */
  List<Notification> findByTypeOrderByCreatedAtDesc(Notification.NotificationType type);

  /** Find notifications by priority. */
  List<Notification> findByPriorityOrderByCreatedAtDesc(Notification.Priority priority);

  /** Count unread notifications. */
  long countByIsReadFalse();

  /** Find recent unread high-priority notifications. */
  @Query(
      "SELECT n FROM Notification n WHERE n.isRead = false "
          + "AND n.priority IN ('HIGH', 'URGENT') "
          + "AND n.createdAt > :since "
          + "ORDER BY n.priority DESC, n.createdAt DESC")
  List<Notification> findRecentHighPriority(Instant since);

  /** Delete old read notifications. */
  void deleteByIsReadTrueAndCreatedAtBefore(Instant before);
}
