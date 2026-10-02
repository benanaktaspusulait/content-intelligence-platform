package com.pompom.creative.api.controller;

import com.pompom.creative.correlation.CorrelationAnalysis;
import com.pompom.creative.correlation.CorrelationAnalyzerService;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for correlation analysis. */
@RestController
@RequestMapping("/api/v1/correlation")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class CorrelationController {

  private final CorrelationAnalyzerService analyzerService;

  /** Perform correlation analysis. */
  @PostMapping("/analyze")
  public ResponseEntity<CorrelationAnalysis> analyzeCorrelations() {
    log.info("Starting correlation analysis");

    try {
      CorrelationAnalysis analysis = analyzerService.analyzeCorrelations();
      return ResponseEntity.ok(analysis);

    } catch (IllegalStateException e) {
      log.error("Analysis failed: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get latest correlation analysis. */
  @GetMapping("/latest")
  public ResponseEntity<CorrelationAnalysis> getLatest() {
    log.info("Fetching latest correlation analysis");

    CorrelationAnalysis analysis = analyzerService.getLatestAnalysis();

    if (analysis == null) {
      return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok(analysis);
  }

  /** Get correlation analysis history. */
  @GetMapping("/history")
  public ResponseEntity<List<CorrelationAnalysis>> getHistory() {
    log.info("Fetching correlation analysis history");

    List<CorrelationAnalysis> history = analyzerService.getAnalysisHistory();

    return ResponseEntity.ok(history);
  }
}
