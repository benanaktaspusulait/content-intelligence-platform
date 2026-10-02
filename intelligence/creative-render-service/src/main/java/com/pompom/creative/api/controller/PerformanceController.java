package com.pompom.creative.api.controller;

import com.pompom.creative.performance.PerformanceClassification;
import com.pompom.creative.performance.PerformanceClassifierService;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for video performance classification. */
@RestController
@RequestMapping("/api/v1/performance")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class PerformanceController {

  private final PerformanceClassifierService classifierService;

  /** Classify video performance. */
  @PostMapping("/classify/{publicationJobId}")
  public ResponseEntity<PerformanceClassification> classifyVideo(
      @PathVariable UUID publicationJobId) {
    log.info("Classifying video: jobId={}", publicationJobId);

    try {
      PerformanceClassification classification = classifierService.classifyVideo(publicationJobId);
      return ResponseEntity.ok(classification);

    } catch (IllegalArgumentException e) {
      log.error("Job not found: {}", publicationJobId);
      return ResponseEntity.notFound().build();
    } catch (IllegalStateException e) {
      log.error("Classification failed: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get classification for a video. */
  @GetMapping("/{publicationJobId}")
  public ResponseEntity<PerformanceClassification> getClassification(
      @PathVariable UUID publicationJobId) {
    log.info("Fetching classification: jobId={}", publicationJobId);

    PerformanceClassification classification =
        classifierService.getClassification(publicationJobId);

    if (classification == null) {
      return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok(classification);
  }

  /** Get all winners (top-tier performances). */
  @GetMapping("/winners")
  public ResponseEntity<List<PerformanceClassification>> getWinners() {
    log.info("Fetching winners");

    List<PerformanceClassification> winners = classifierService.getWinners();
    return ResponseEntity.ok(winners);
  }

  /** Get videos by category. */
  @GetMapping("/category/{category}")
  public ResponseEntity<List<PerformanceClassification>> getByCategory(
      @PathVariable String category) {
    log.info("Fetching videos by category: {}", category);

    try {
      PerformanceClassification.PerformanceCategory categoryEnum =
          PerformanceClassification.PerformanceCategory.valueOf(category.toUpperCase());

      List<PerformanceClassification> videos = classifierService.getByCategory(categoryEnum);
      return ResponseEntity.ok(videos);

    } catch (IllegalArgumentException e) {
      log.error("Invalid category: {}", category);
      return ResponseEntity.badRequest().build();
    }
  }
}
