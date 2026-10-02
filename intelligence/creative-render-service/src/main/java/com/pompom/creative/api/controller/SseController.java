package com.pompom.creative.api.controller;

import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.notification.Notification;
import com.pompom.creative.notification.NotificationRepository;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * Server-Sent Events (SSE) controller for real-time updates.
 *
 * <p>SSE is simpler than WebSocket for one-way server-to-client communication. Suitable for: -
 * Status updates - Progress monitoring - Notifications - Live metrics
 *
 * <p>Clients connect via EventSource API: const eventSource = new
 * EventSource('/api/v1/sse/notifications'); eventSource.addEventListener('notification', (event) =>
 * { const data = JSON.parse(event.data); console.log(data); });
 */
@RestController
@RequestMapping("/api/v1/sse")
@Slf4j
@RequiredArgsConstructor
public class SseController {

  private final NotificationRepository notificationRepo;
  private final VideoMetricsRepository metricsRepo;

  // Active SSE connections
  private final List<SseEmitter> notificationEmitters = new CopyOnWriteArrayList<>();
  private final ScheduledExecutorService executor = Executors.newScheduledThreadPool(2);

  /**
   * SSE endpoint for notifications. Sends real-time notifications to client.
   *
   * <p>Usage: const eventSource = new EventSource('/api/v1/sse/notifications');
   * eventSource.onmessage = (event) => console.log(JSON.parse(event.data));
   */
  @GetMapping(value = "/notifications", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
  public SseEmitter streamNotifications() {
    log.info("New SSE connection for notifications");

    SseEmitter emitter = new SseEmitter(Long.MAX_VALUE); // No timeout
    notificationEmitters.add(emitter);

    // Remove emitter on completion or error
    emitter.onCompletion(
        () -> {
          log.debug("SSE notification connection completed");
          notificationEmitters.remove(emitter);
        });

    emitter.onTimeout(
        () -> {
          log.debug("SSE notification connection timed out");
          notificationEmitters.remove(emitter);
        });

    emitter.onError(
        (ex) -> {
          log.error("SSE notification connection error", ex);
          notificationEmitters.remove(emitter);
        });

    // Send initial data
    try {
      List<Notification> unread = notificationRepo.findByIsReadFalseOrderByCreatedAtDesc();
      emitter.send(SseEmitter.event().name("initial").data(unread));
    } catch (IOException e) {
      log.error("Failed to send initial notifications", e);
      emitter.completeWithError(e);
    }

    // Schedule periodic updates (every 30 seconds)
    scheduleNotificationUpdates(emitter);

    return emitter;
  }

  /** SSE endpoint for metrics updates. Streams metrics for a specific publication job. */
  @GetMapping(value = "/metrics/{publicationJobId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
  public SseEmitter streamMetrics(@PathVariable UUID publicationJobId) {
    log.info("New SSE connection for metrics: jobId={}", publicationJobId);

    SseEmitter emitter = new SseEmitter(3600000L); // 1 hour timeout

    emitter.onCompletion(
        () -> log.debug("SSE metrics connection completed: jobId={}", publicationJobId));
    emitter.onTimeout(
        () -> log.debug("SSE metrics connection timed out: jobId={}", publicationJobId));
    emitter.onError(
        (ex) -> log.error("SSE metrics connection error: jobId={}", publicationJobId, ex));

    // Send initial metrics
    try {
      List<VideoMetrics> metrics = metricsRepo.findByPublicationJobId(publicationJobId);
      emitter.send(SseEmitter.event().name("initial").data(metrics));
    } catch (IOException e) {
      log.error("Failed to send initial metrics", e);
      emitter.completeWithError(e);
    }

    // Schedule periodic updates (every 60 seconds)
    scheduleMetricsUpdates(emitter, publicationJobId);

    return emitter;
  }

  /** SSE endpoint for heartbeat/keepalive. Sends ping every 15 seconds to keep connection alive. */
  @GetMapping(value = "/heartbeat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
  public SseEmitter heartbeat() {
    log.info("New SSE heartbeat connection");

    SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);

    emitter.onCompletion(() -> log.debug("SSE heartbeat connection completed"));
    emitter.onTimeout(() -> log.debug("SSE heartbeat connection timed out"));
    emitter.onError((ex) -> log.error("SSE heartbeat connection error", ex));

    // Send ping every 15 seconds
    executor.scheduleAtFixedRate(
        () -> {
          try {
            emitter.send(SseEmitter.event().name("ping").data("pong"));
          } catch (Exception e) {
            log.error("Failed to send heartbeat", e);
            emitter.completeWithError(e);
          }
        },
        0,
        15,
        TimeUnit.SECONDS);

    return emitter;
  }

  /** Schedule periodic notification updates. */
  private void scheduleNotificationUpdates(SseEmitter emitter) {
    executor.scheduleAtFixedRate(
        () -> {
          try {
            List<Notification> unread = notificationRepo.findByIsReadFalseOrderByCreatedAtDesc();
            emitter.send(SseEmitter.event().name("update").data(unread));
          } catch (Exception e) {
            log.error("Failed to send notification update", e);
            emitter.completeWithError(e);
          }
        },
        30,
        30,
        TimeUnit.SECONDS);
  }

  /** Schedule periodic metrics updates. */
  private void scheduleMetricsUpdates(SseEmitter emitter, UUID publicationJobId) {
    executor.scheduleAtFixedRate(
        () -> {
          try {
            List<VideoMetrics> metrics = metricsRepo.findByPublicationJobId(publicationJobId);
            emitter.send(SseEmitter.event().name("update").data(metrics));
          } catch (Exception e) {
            log.error("Failed to send metrics update", e);
            emitter.completeWithError(e);
          }
        },
        60,
        60,
        TimeUnit.SECONDS);
  }
}
