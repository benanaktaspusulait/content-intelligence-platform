package com.pompom.creative.api.controller;

import com.pompom.creative.domain.ScheduledPublication;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.ScheduledPublishingService;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for scheduled publications. */
@RestController
@RequestMapping("/api/v1/scheduled")
@Slf4j
@RequiredArgsConstructor
public class ScheduledPublicationController {

  private final ScheduledPublishingService scheduledPublishingService;

  /** Schedule a publication. */
  @PostMapping
  public ResponseEntity<ScheduledPublication> schedulePublication(
      @RequestBody SchedulePublicationRequest request) {
    log.info(
        "Scheduling publication: platform={}, scheduledAt={}",
        request.getPlatform(),
        request.getScheduledAt());

    try {
      PlatformType platform = PlatformType.valueOf(request.getPlatform().toUpperCase());

      // Parse scheduled time
      ZonedDateTime scheduledAt =
          parseScheduledTime(request.getScheduledAt(), request.getTimezone());

      ScheduledPublication scheduled =
          scheduledPublishingService.schedulePublication(
              platform,
              request.getRenderAssetId(),
              request.getPlatformAccountId(),
              request.getTitle(),
              request.getCaption(),
              request.getHashtags(),
              request.getIsPrivate(),
              scheduledAt);

      return ResponseEntity.ok(scheduled);

    } catch (IllegalArgumentException e) {
      log.error("Invalid request: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    } catch (Exception e) {
      log.error("Failed to schedule publication", e);
      return ResponseEntity.internalServerError().build();
    }
  }

  /** Get scheduled publication by ID. */
  @GetMapping("/{scheduleId}")
  public ResponseEntity<ScheduledPublication> getScheduled(@PathVariable UUID scheduleId) {
    return scheduledPublishingService
        .getScheduled(scheduleId)
        .map(ResponseEntity::ok)
        .orElse(ResponseEntity.notFound().build());
  }

  /** Get all scheduled publications. */
  @GetMapping
  public ResponseEntity<List<ScheduledPublication>> getAllScheduled(
      @RequestParam(required = false) String status,
      @RequestParam(required = false) String platform) {
    if ("pending".equalsIgnoreCase(status)) {
      if (platform != null) {
        try {
          PlatformType platformType = PlatformType.valueOf(platform.toUpperCase());
          return ResponseEntity.ok(
              scheduledPublishingService.getPendingScheduledByPlatform(platformType));
        } catch (IllegalArgumentException e) {
          return ResponseEntity.badRequest().build();
        }
      }
      return ResponseEntity.ok(scheduledPublishingService.getPendingScheduled());
    }

    return ResponseEntity.ok(scheduledPublishingService.getAllScheduled());
  }

  /** Cancel scheduled publication. */
  @DeleteMapping("/{scheduleId}")
  public ResponseEntity<Map<String, Object>> cancelScheduled(@PathVariable UUID scheduleId) {
    boolean cancelled = scheduledPublishingService.cancelScheduled(scheduleId);

    if (cancelled) {
      return ResponseEntity.ok(
          Map.of("success", true, "message", "Scheduled publication cancelled"));
    } else {
      return ResponseEntity.ok(
          Map.of("success", false, "message", "Cannot cancel (not found or already executed)"));
    }
  }

  /** Reschedule publication. */
  @PutMapping("/{scheduleId}/reschedule")
  public ResponseEntity<Map<String, Object>> reschedule(
      @PathVariable UUID scheduleId, @RequestBody RescheduleRequest request) {
    try {
      ZonedDateTime newScheduledAt =
          parseScheduledTime(request.getScheduledAt(), request.getTimezone());

      boolean rescheduled =
          scheduledPublishingService.reschedule(scheduleId, newScheduledAt.toInstant());

      if (rescheduled) {
        return ResponseEntity.ok(
            Map.of(
                "success",
                true,
                "message",
                "Publication rescheduled",
                "newScheduledAt",
                newScheduledAt.toString()));
      } else {
        return ResponseEntity.ok(
            Map.of(
                "success", false, "message", "Cannot reschedule (not found or already executed)"));
      }

    } catch (IllegalArgumentException e) {
      return ResponseEntity.badRequest().body(Map.of("success", false, "message", e.getMessage()));
    }
  }

  /** Get statistics. */
  @GetMapping("/statistics")
  public ResponseEntity<Map<String, Long>> getStatistics() {
    return ResponseEntity.ok(scheduledPublishingService.getStatistics());
  }

  /** Parse scheduled time from string. */
  private ZonedDateTime parseScheduledTime(String scheduledAtStr, String timezone) {
    ZoneId zoneId =
        timezone != null && !timezone.isEmpty() ? ZoneId.of(timezone) : ZoneId.systemDefault();

    // Try parsing as ISO instant first
    try {
      Instant instant = Instant.parse(scheduledAtStr);
      return instant.atZone(zoneId);
    } catch (Exception e) {
      // Try parsing as ISO zoned datetime
      return ZonedDateTime.parse(scheduledAtStr);
    }
  }

  @Data
  public static class SchedulePublicationRequest {
    private String platform;
    private UUID renderAssetId;
    private String platformAccountId;
    private String title;
    private String caption;
    private String hashtags;
    private Boolean isPrivate;
    private String scheduledAt; // ISO 8601 format
    private String timezone; // e.g., "Europe/Istanbul"
  }

  @Data
  public static class RescheduleRequest {
    private String scheduledAt; // ISO 8601 format
    private String timezone;
  }
}
