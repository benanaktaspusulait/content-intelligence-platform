package com.pompom.creative.api.controller;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.PublicationService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for publication management. */
@RestController
@RequestMapping("/api/v1/publications")
@Slf4j
@RequiredArgsConstructor
public class PublicationController {

  private final PublicationService publicationService;

  /** Queue a new publication job. */
  @PostMapping("/queue")
  public ResponseEntity<PublicationJob> queuePublication(
      @RequestBody QueuePublicationRequest request) {
    log.info(
        "Queueing publication: platform={}, renderAssetId={}",
        request.getPlatform(),
        request.getRenderAssetId());

    try {
      PlatformType platform = PlatformType.valueOf(request.getPlatform().toUpperCase());

      PublicationJob job =
          publicationService.queuePublication(
              platform,
              request.getRenderAssetId(),
              request.getPlatformAccountId(),
              request.getTitle(),
              request.getCaption(),
              request.getHashtags(),
              request.getIsPrivate());

      return ResponseEntity.ok(job);

    } catch (IllegalArgumentException e) {
      log.error("Invalid platform: {}", request.getPlatform());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get job by ID. */
  @GetMapping("/{jobId}")
  public ResponseEntity<PublicationJob> getJob(@PathVariable UUID jobId) {
    return publicationService
        .getJob(jobId)
        .map(ResponseEntity::ok)
        .orElse(ResponseEntity.notFound().build());
  }

  /** Get all jobs. */
  @GetMapping
  public ResponseEntity<List<PublicationJob>> getAllJobs(
      @RequestParam(required = false) String status) {
    if (status != null) {
      try {
        PublicationStatus statusEnum = PublicationStatus.valueOf(status.toUpperCase());
        return ResponseEntity.ok(publicationService.getJobsByStatus(statusEnum));
      } catch (IllegalArgumentException e) {
        return ResponseEntity.badRequest().build();
      }
    }

    return ResponseEntity.ok(publicationService.getAllJobs());
  }

  /** Get active jobs. */
  @GetMapping("/active")
  public ResponseEntity<List<PublicationJob>> getActiveJobs() {
    return ResponseEntity.ok(publicationService.getActiveJobs());
  }

  /** Cancel a job. */
  @PostMapping("/{jobId}/cancel")
  public ResponseEntity<Map<String, Object>> cancelJob(@PathVariable UUID jobId) {
    boolean cancelled = publicationService.cancelJob(jobId);

    if (cancelled) {
      return ResponseEntity.ok(Map.of("success", true, "message", "Job cancelled successfully"));
    } else {
      return ResponseEntity.ok(
          Map.of(
              "success",
              false,
              "message",
              "Job cannot be cancelled (already completed or not found)"));
    }
  }

  /** Get statistics. */
  @GetMapping("/statistics")
  public ResponseEntity<Map<String, Long>> getStatistics() {
    return ResponseEntity.ok(publicationService.getStatistics());
  }

  @Data
  public static class QueuePublicationRequest {
    private String platform;
    private UUID renderAssetId;
    private String platformAccountId;
    private String title;
    private String caption;
    private String hashtags;
    private Boolean isPrivate;
  }
}
