package com.pompom.creative.websocket;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

/**
 * Service for publishing events to WebSocket clients.
 *
 * <p>Uses SimpMessagingTemplate to send messages to: - Topics (broadcast to all subscribers) -
 * Queues (user-specific messages)
 *
 * <p>Topics: - /topic/render/progress - Render job progress - /topic/metrics/updates - Metrics
 * updates - /topic/performance/alerts - Performance alerts - /topic/publication/updates -
 * Publication status updates
 *
 * <p>User-specific: - /queue/notifications - Personal notifications
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class WebSocketEventPublisher {

  private final SimpMessagingTemplate messagingTemplate;

  /**
   * Broadcast message to all subscribers of a topic.
   *
   * @param topic Topic destination (e.g., "/topic/render/progress")
   * @param payload Message payload
   */
  public void broadcastToTopic(String topic, Object payload) {
    log.debug("Broadcasting to topic: {}", topic);
    messagingTemplate.convertAndSend(topic, payload);
  }

  /**
   * Send message to specific user's queue.
   *
   * @param username Username
   * @param destination Destination queue (e.g., "/queue/notifications")
   * @param payload Message payload
   */
  public void sendToUser(String username, String destination, Object payload) {
    log.debug("Sending to user {}: {}", username, destination);
    messagingTemplate.convertAndSendToUser(username, destination, payload);
  }

  /** Broadcast render job progress update. */
  public void publishRenderProgress(Object progressUpdate) {
    broadcastToTopic("/topic/render/progress", progressUpdate);
  }

  /** Broadcast metrics update. */
  public void publishMetricsUpdate(Object metricsUpdate) {
    broadcastToTopic("/topic/metrics/updates", metricsUpdate);
  }

  /** Broadcast performance alert. */
  public void publishPerformanceAlert(Object alert) {
    broadcastToTopic("/topic/performance/alerts", alert);
  }

  /** Broadcast publication update. */
  public void publishPublicationUpdate(Object publicationUpdate) {
    broadcastToTopic("/topic/publication/updates", publicationUpdate);
  }

  /** Send notification to specific user. */
  public void sendNotificationToUser(String username, Object notification) {
    sendToUser(username, "/queue/notifications", notification);
  }
}
