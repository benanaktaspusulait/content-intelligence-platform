package com.pompom.creative.api.controller;

import com.pompom.creative.notification.Notification;
import com.pompom.creative.notification.NotificationService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read and acknowledgement endpoints for persisted in-app notifications. */
@RestController
@RequestMapping("/api/v1/notifications")
@RequiredArgsConstructor
public class NotificationController {
  private final NotificationService service;

  @GetMapping
  public List<Notification> all() {
    return service.getAllNotifications();
  }

  @GetMapping("/unread")
  public List<Notification> unread() {
    return service.getUnreadNotifications();
  }

  @GetMapping("/count")
  public Map<String, Long> count() {
    return Map.of("unread", service.getUnreadCount());
  }

  @PostMapping("/{id}/read")
  public ResponseEntity<Void> markRead(@PathVariable UUID id) {
    service.markAsRead(id);
    return ResponseEntity.noContent().build();
  }

  @PostMapping("/read-all")
  public ResponseEntity<Void> markAllRead() {
    service.markAllAsRead();
    return ResponseEntity.noContent().build();
  }

  @DeleteMapping("/{id}")
  public ResponseEntity<Void> delete(@PathVariable UUID id) {
    service.deleteNotification(id);
    return ResponseEntity.noContent().build();
  }
}
