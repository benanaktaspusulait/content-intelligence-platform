package com.pompom.creative.api.controller;

import com.pompom.creative.domain.PublicationAnalytics;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.AnalyticsService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for publication analytics. */
@RestController
@RequestMapping("/api/v1/analytics")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AnalyticsController {

  private final AnalyticsService analyticsService;

  /** Fetch/refresh analytics for a publication job. */
  @PostMapping("/fetch/{jobId}")
  public ResponseEntity<PublicationAnalytics> fetchAnalytics(@PathVariable UUID jobId) {
    log.info("Fetching analytics: jobId={}", jobId);

    try {
      PublicationAnalytics analytics = analyticsService.fetchAnalytics(jobId);

      if (analytics == null) {
        return ResponseEntity.notFound().build();
      }

      return ResponseEntity.ok(analytics);

    } catch (Exception e) {
      log.error("Failed to fetch analytics: jobId={}", jobId, e);
      return ResponseEntity.internalServerError().build();
    }
  }

  /** Get analytics for a publication job. */
  @GetMapping("/job/{jobId}")
  public ResponseEntity<PublicationAnalytics> getAnalytics(@PathVariable UUID jobId) {
    return analyticsService
        .getAnalytics(jobId)
        .map(ResponseEntity::ok)
        .orElse(ResponseEntity.notFound().build());
  }

  /** Get analytics by platform. */
  @GetMapping("/platform/{platform}")
  public ResponseEntity<List<PublicationAnalytics>> getAnalyticsByPlatform(
      @PathVariable String platform) {
    try {
      PlatformType platformType = PlatformType.valueOf(platform.toUpperCase());
      return ResponseEntity.ok(analyticsService.getAnalyticsByPlatform(platformType));
    } catch (IllegalArgumentException e) {
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get top performing posts by views. */
  @GetMapping("/top/views")
  public ResponseEntity<List<PublicationAnalytics>> getTopByViews(
      @RequestParam(defaultValue = "10") int limit) {
    return ResponseEntity.ok(analyticsService.getTopByViews(limit));
  }

  /** Get top performing posts by engagement. */
  @GetMapping("/top/engagement")
  public ResponseEntity<List<PublicationAnalytics>> getTopByEngagement(
      @RequestParam(defaultValue = "10") int limit) {
    return ResponseEntity.ok(analyticsService.getTopByEngagement(limit));
  }

  /** Get aggregated statistics. */
  @GetMapping("/stats")
  public ResponseEntity<Map<String, Object>> getAggregatedStats() {
    return ResponseEntity.ok(analyticsService.getAggregatedStats());
  }

  /** Get performance dashboard data. */
  @GetMapping("/dashboard")
  public ResponseEntity<Map<String, Object>> getDashboardData() {
    return ResponseEntity.ok(analyticsService.getDashboardData());
  }

  /** Trigger manual sync of all analytics. */
  @PostMapping("/sync")
  public ResponseEntity<Map<String, String>> syncAllAnalytics() {
    log.info("Manual analytics sync triggered");

    try {
      analyticsService.syncAllAnalytics();
      return ResponseEntity.ok(
          Map.of(
              "message", "Analytics sync started",
              "status", "processing"));
    } catch (Exception e) {
      log.error("Failed to start analytics sync", e);
      return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
    }
  }
}
