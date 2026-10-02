package com.pompom.creative.api.controller;

import com.pompom.creative.benchmark.BenchmarkService;
import com.pompom.creative.benchmark.WinnerEntry;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for winner catalog and benchmarking. */
@RestController
@RequestMapping("/api/v1/benchmark")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class BenchmarkController {

  private final BenchmarkService benchmarkService;

  /** Update winner catalog. */
  @PostMapping("/catalog/update")
  public ResponseEntity<BenchmarkService.CatalogUpdate> updateCatalog() {
    log.info("Updating winner catalog");

    try {
      BenchmarkService.CatalogUpdate result = benchmarkService.updateCatalog();
      return ResponseEntity.ok(result);

    } catch (IllegalStateException e) {
      log.error("Catalog update failed: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get winner entry for a job. */
  @GetMapping("/winner/{publicationJobId}")
  public ResponseEntity<WinnerEntry> getWinnerEntry(@PathVariable UUID publicationJobId) {
    log.info("Fetching winner entry: {}", publicationJobId);

    WinnerEntry entry = benchmarkService.getWinnerEntry(publicationJobId);

    if (entry == null) {
      return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok(entry);
  }

  /** Get top performers by tier. */
  @GetMapping("/top/{tier}")
  public ResponseEntity<List<WinnerEntry>> getTopPerformers(
      @PathVariable WinnerEntry.WinnerTier tier) {
    log.info("Fetching top performers: tier={}", tier);

    List<WinnerEntry> winners = benchmarkService.getTopPerformers(tier);

    return ResponseEntity.ok(winners);
  }

  /** Compare job against benchmarks. */
  @GetMapping("/compare/{publicationJobId}")
  public ResponseEntity<BenchmarkService.BenchmarkComparison> compareAgainstBenchmarks(
      @PathVariable UUID publicationJobId) {
    log.info("Comparing against benchmarks: {}", publicationJobId);

    try {
      BenchmarkService.BenchmarkComparison comparison =
          benchmarkService.compareAgainstBenchmarks(publicationJobId);

      return ResponseEntity.ok(comparison);

    } catch (IllegalArgumentException e) {
      log.error("Comparison failed: {}", e.getMessage());
      return ResponseEntity.notFound().build();
    }
  }

  /** Get catalog statistics. */
  @GetMapping("/stats")
  public ResponseEntity<BenchmarkService.CatalogStats> getCatalogStats() {
    log.info("Fetching catalog statistics");

    BenchmarkService.CatalogStats stats = benchmarkService.getCatalogStats();

    return ResponseEntity.ok(stats);
  }
}
