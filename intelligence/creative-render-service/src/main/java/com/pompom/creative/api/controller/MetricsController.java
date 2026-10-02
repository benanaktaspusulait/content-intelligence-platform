package com.pompom.creative.api.controller;

import com.pompom.creative.metrics.MetricsCollectionJob;
import com.pompom.creative.metrics.MetricsCollectionJobRepository;
import com.pompom.creative.metrics.MetricsCollectorService;
import com.pompom.creative.metrics.VideoMetrics;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for video metrics collection. */
@RestController
@RequestMapping("/api/v1/metrics")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class MetricsController {

  private final MetricsCollectorService metricsCollectorService;
  private final MetricsCollectionJobRepository collectionJobRepo;

  /** Schedule metrics collection for a published video. */
  @PostMapping("/schedule/{publicationJobId}")
  public ResponseEntity<ScheduleResponse> scheduleCollection(@PathVariable UUID publicationJobId) {
    log.info("Scheduling metrics collection: jobId={}", publicationJobId);

    try {
      List<MetricsCollectionJob> jobs =
          metricsCollectorService.scheduleCollection(publicationJobId);

      return ResponseEntity.ok(
          new ScheduleResponse(
              publicationJobId,
              jobs.size(),
              jobs.stream().map(j -> j.getId().toString()).toList()));

    } catch (IllegalArgumentException e) {
      log.error("Invalid publication job: {}", publicationJobId, e);
      return ResponseEntity.notFound().build();
    } catch (IllegalStateException e) {
      log.error("Cannot schedule collection: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Collect metrics for a specific job immediately. */
  @PostMapping("/collect/{collectionJobId}")
  public ResponseEntity<VideoMetrics> collectNow(@PathVariable UUID collectionJobId) {
    log.info("Manual metrics collection trigger: jobId={}", collectionJobId);

    try {
      MetricsCollectionJob collectionJob =
          collectionJobRepo
              .findById(collectionJobId)
              .orElseThrow(
                  () ->
                      new IllegalArgumentException("Collection job not found: " + collectionJobId));

      VideoMetrics metrics = metricsCollectorService.collectMetrics(collectionJob);
      return ResponseEntity.ok(metrics);

    } catch (IllegalArgumentException e) {
      log.error("Collection job not found: {}", collectionJobId);
      return ResponseEntity.notFound().build();
    } catch (Exception e) {
      log.error("Collection failed", e);
      return ResponseEntity.internalServerError().build();
    }
  }

  /** Get metrics timeline for a video. */
  @GetMapping("/timeline/{publicationJobId}")
  public ResponseEntity<List<VideoMetrics>> getTimeline(@PathVariable UUID publicationJobId) {
    log.info("Fetching metrics timeline: jobId={}", publicationJobId);

    List<VideoMetrics> timeline = metricsCollectorService.getMetricsTimeline(publicationJobId);
    return ResponseEntity.ok(timeline);
  }

  /** Record manual metrics entry. */
  @PostMapping("/manual")
  public ResponseEntity<VideoMetrics> recordManual(@RequestBody ManualMetricsRequest request) {
    log.info(
        "Recording manual metrics: jobId={}, views={}",
        request.publicationJobId(),
        request.views());

    try {
      VideoMetrics metrics =
          metricsCollectorService.recordManualMetrics(
              request.publicationJobId(),
              request.views(),
              request.likes(),
              request.comments(),
              request.shares(),
              request.minutesSincePublish());

      return ResponseEntity.ok(metrics);

    } catch (IllegalArgumentException e) {
      log.error("Invalid request", e);
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get latest metrics for a video. */
  @GetMapping("/latest/{publicationJobId}")
  public ResponseEntity<VideoMetrics> getLatest(@PathVariable UUID publicationJobId) {
    log.info("Fetching latest metrics: jobId={}", publicationJobId);

    List<VideoMetrics> timeline = metricsCollectorService.getMetricsTimeline(publicationJobId);

    if (timeline.isEmpty()) {
      return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok(timeline.get(timeline.size() - 1));
  }

  // DTOs

  public record ScheduleResponse(
      UUID publicationJobId, int collectionPointsScheduled, List<String> collectionJobIds) {}

  public record ManualMetricsRequest(
      UUID publicationJobId,
      Long views,
      Long likes,
      Long comments,
      Long shares,
      Integer minutesSincePublish) {}
}
