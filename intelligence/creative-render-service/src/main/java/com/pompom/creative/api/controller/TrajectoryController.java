package com.pompom.creative.api.controller;

import com.pompom.creative.trajectory.TrajectoryAnalysis;
import com.pompom.creative.trajectory.TrajectoryAnalyzerService;
import java.math.BigDecimal;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for trajectory analysis. */
@RestController
@RequestMapping("/api/v1/trajectory")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class TrajectoryController {

  private final TrajectoryAnalyzerService analyzerService;

  /** Analyze trajectory for a video. */
  @PostMapping("/analyze/{publicationJobId}")
  public ResponseEntity<TrajectoryAnalysis> analyzeTrajectory(@PathVariable UUID publicationJobId) {
    log.info("Analyzing trajectory: jobId={}", publicationJobId);

    try {
      TrajectoryAnalysis analysis = analyzerService.analyzeTrajectory(publicationJobId);
      return ResponseEntity.ok(analysis);

    } catch (IllegalArgumentException e) {
      log.error("Job not found: {}", publicationJobId);
      return ResponseEntity.notFound().build();
    } catch (IllegalStateException e) {
      log.error("Analysis failed: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get trajectory analysis. */
  @GetMapping("/{publicationJobId}")
  public ResponseEntity<TrajectoryAnalysis> getAnalysis(@PathVariable UUID publicationJobId) {
    log.info("Fetching trajectory: jobId={}", publicationJobId);

    TrajectoryAnalysis analysis = analyzerService.getAnalysis(publicationJobId);

    if (analysis == null) {
      return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok(analysis);
  }

  /** Compare similarity between two trajectories. */
  @GetMapping("/compare")
  public ResponseEntity<SimilarityResponse> compareSimilarity(
      @RequestParam UUID jobId1, @RequestParam UUID jobId2) {
    log.info("Comparing trajectories: {} vs {}", jobId1, jobId2);

    BigDecimal similarity = analyzerService.compareSimilarity(jobId1, jobId2);

    return ResponseEntity.ok(new SimilarityResponse(jobId1, jobId2, similarity));
  }

  public record SimilarityResponse(UUID jobId1, UUID jobId2, BigDecimal similarityScore) {}
}
