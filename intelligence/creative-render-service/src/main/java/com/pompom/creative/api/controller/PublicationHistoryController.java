package com.pompom.creative.api.controller;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.export.ExportService;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for publication history and export. */
@RestController
@RequestMapping("/api/v1/history")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class PublicationHistoryController {

  private final PublicationJobRepository publicationJobRepository;
  private final ExportService exportService;

  /** Search and filter publications with pagination. */
  @GetMapping("/search")
  public ResponseEntity<Page<PublicationJob>> searchPublications(
      @RequestParam(required = false) String platform,
      @RequestParam(required = false) String status,
      @RequestParam(required = false) String startDate,
      @RequestParam(required = false) String endDate,
      @RequestParam(required = false) String keyword,
      @RequestParam(defaultValue = "0") int page,
      @RequestParam(defaultValue = "20") int size,
      @RequestParam(defaultValue = "queuedAt") String sortBy,
      @RequestParam(defaultValue = "DESC") String sortDirection) {
    log.info(
        "Searching publications: platform={}, status={}, keyword={}", platform, status, keyword);

    try {
      // Parse parameters
      PlatformType platformType =
          platform != null && !platform.isEmpty()
              ? PlatformType.valueOf(platform.toUpperCase())
              : null;

      PublicationStatus statusEnum =
          status != null && !status.isEmpty()
              ? PublicationStatus.valueOf(status.toUpperCase())
              : null;

      Instant startInstant =
          startDate != null && !startDate.isEmpty() ? Instant.parse(startDate) : null;

      Instant endInstant = endDate != null && !endDate.isEmpty() ? Instant.parse(endDate) : null;

      // Create pageable
      Sort sort =
          Sort.by(
              sortDirection.equalsIgnoreCase("DESC") ? Sort.Direction.DESC : Sort.Direction.ASC,
              sortBy);
      PageRequest pageable = PageRequest.of(page, size, sort);

      // Search
      Page<PublicationJob> results =
          publicationJobRepository.searchJobs(
              platformType, statusEnum, startInstant, endInstant, keyword, pageable);

      log.info("Search results: {} items", results.getTotalElements());
      return ResponseEntity.ok(results);

    } catch (IllegalArgumentException | DateTimeParseException e) {
      log.error("Invalid search parameters", e);
      return ResponseEntity.badRequest().build();
    }
  }

  /** Export publications to CSV. */
  @GetMapping("/export/csv")
  public ResponseEntity<byte[]> exportCSV(
      @RequestParam(required = false) String platform,
      @RequestParam(required = false) String status,
      @RequestParam(required = false) String startDate,
      @RequestParam(required = false) String endDate) {
    log.info("Exporting publications to CSV");

    try {
      PlatformType platformType =
          platform != null && !platform.isEmpty()
              ? PlatformType.valueOf(platform.toUpperCase())
              : null;

      PublicationStatus statusEnum =
          status != null && !status.isEmpty()
              ? PublicationStatus.valueOf(status.toUpperCase())
              : null;

      Instant startInstant =
          startDate != null && !startDate.isEmpty() ? Instant.parse(startDate) : null;

      Instant endInstant = endDate != null && !endDate.isEmpty() ? Instant.parse(endDate) : null;

      byte[] csv = exportService.exportToCSV(platformType, statusEnum, startInstant, endInstant);

      HttpHeaders headers = new HttpHeaders();
      headers.setContentType(MediaType.parseMediaType("text/csv"));
      headers.setContentDispositionFormData("attachment", "publications.csv");
      headers.setContentLength(csv.length);

      return ResponseEntity.ok().headers(headers).body(csv);

    } catch (Exception e) {
      log.error("CSV export failed", e);
      return ResponseEntity.internalServerError().build();
    }
  }

  /** Export publications to JSON. */
  @GetMapping("/export/json")
  public ResponseEntity<byte[]> exportJSON(
      @RequestParam(required = false) String platform,
      @RequestParam(required = false) String status,
      @RequestParam(required = false) String startDate,
      @RequestParam(required = false) String endDate) {
    log.info("Exporting publications to JSON");

    try {
      PlatformType platformType =
          platform != null && !platform.isEmpty()
              ? PlatformType.valueOf(platform.toUpperCase())
              : null;

      PublicationStatus statusEnum =
          status != null && !status.isEmpty()
              ? PublicationStatus.valueOf(status.toUpperCase())
              : null;

      Instant startInstant =
          startDate != null && !startDate.isEmpty() ? Instant.parse(startDate) : null;

      Instant endInstant = endDate != null && !endDate.isEmpty() ? Instant.parse(endDate) : null;

      byte[] json = exportService.exportToJSON(platformType, statusEnum, startInstant, endInstant);

      HttpHeaders headers = new HttpHeaders();
      headers.setContentType(MediaType.APPLICATION_JSON);
      headers.setContentDispositionFormData("attachment", "publications.json");
      headers.setContentLength(json.length);

      return ResponseEntity.ok().headers(headers).body(json);

    } catch (Exception e) {
      log.error("JSON export failed", e);
      return ResponseEntity.internalServerError().build();
    }
  }

  /** Generate publication report. */
  @GetMapping("/report")
  public ResponseEntity<ExportService.PublicationReport> generateReport(
      @RequestParam(required = false) String startDate,
      @RequestParam(required = false) String endDate) {
    log.info("Generating publication report");

    try {
      Instant startInstant =
          startDate != null && !startDate.isEmpty()
              ? Instant.parse(startDate)
              : Instant.now().minusSeconds(30 * 24 * 3600); // Last 30 days

      Instant endInstant =
          endDate != null && !endDate.isEmpty() ? Instant.parse(endDate) : Instant.now();

      ExportService.PublicationReport report =
          exportService.generateReport(startInstant, endInstant);

      return ResponseEntity.ok(report);

    } catch (Exception e) {
      log.error("Report generation failed", e);
      return ResponseEntity.internalServerError().build();
    }
  }
}
