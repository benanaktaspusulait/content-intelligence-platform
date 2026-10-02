package com.pompom.creative.export;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Export service for publication data. Supports CSV and JSON export formats. */
@Service
@Slf4j
@RequiredArgsConstructor
public class ExportService {

  private final PublicationJobRepository publicationJobRepository;
  private final ObjectMapper objectMapper;

  /**
   * Export publication jobs to CSV.
   *
   * @param platform Filter by platform (optional)
   * @param status Filter by status (optional)
   * @param startDate Filter by start date (optional)
   * @param endDate Filter by end date (optional)
   * @return CSV data as byte array
   */
  @Transactional(readOnly = true)
  public byte[] exportToCSV(
      PlatformType platform, PublicationStatus status, Instant startDate, Instant endDate) {
    log.info("Exporting publications to CSV: platform={}, status={}", platform, status);

    List<PublicationJob> jobs =
        publicationJobRepository.findJobsForExport(platform, status, startDate, endDate);

    try (ByteArrayOutputStream baos = new ByteArrayOutputStream();
        OutputStreamWriter writer = new OutputStreamWriter(baos, StandardCharsets.UTF_8)) {

      // Write CSV header
      writer.write(
          "ID,Platform,Status,Title,Caption,Hashtags,Video Path,Platform Post ID,Post URL,");
      writer.write("Progress %,Error Message,Queued At,Started At,Completed At\n");

      // Write data rows
      DateTimeFormatter formatter = DateTimeFormatter.ISO_INSTANT;

      for (PublicationJob job : jobs) {
        writer.write(escapeCsv(job.getId().toString()));
        writer.write(",");
        writer.write(escapeCsv(job.getPlatform().name()));
        writer.write(",");
        writer.write(escapeCsv(job.getStatus().name()));
        writer.write(",");
        writer.write(escapeCsv(job.getTitle()));
        writer.write(",");
        writer.write(escapeCsv(job.getCaption()));
        writer.write(",");
        writer.write(escapeCsv(job.getHashtags()));
        writer.write(",");
        writer.write(escapeCsv(job.getVideoPath()));
        writer.write(",");
        writer.write(escapeCsv(job.getPlatformPostId()));
        writer.write(",");
        writer.write(escapeCsv(job.getPostUrl()));
        writer.write(",");
        writer.write(job.getProgressPercent() != null ? job.getProgressPercent().toString() : "");
        writer.write(",");
        writer.write(escapeCsv(job.getErrorMessage()));
        writer.write(",");
        writer.write(job.getQueuedAt() != null ? formatter.format(job.getQueuedAt()) : "");
        writer.write(",");
        writer.write(job.getStartedAt() != null ? formatter.format(job.getStartedAt()) : "");
        writer.write(",");
        writer.write(job.getCompletedAt() != null ? formatter.format(job.getCompletedAt()) : "");
        writer.write("\n");
      }

      writer.flush();

      log.info("CSV export complete: {} rows", jobs.size());
      return baos.toByteArray();

    } catch (IOException e) {
      log.error("Failed to export to CSV", e);
      throw new RuntimeException("CSV export failed", e);
    }
  }

  /**
   * Export publication jobs to JSON.
   *
   * @param platform Filter by platform (optional)
   * @param status Filter by status (optional)
   * @param startDate Filter by start date (optional)
   * @param endDate Filter by end date (optional)
   * @return JSON data as byte array
   */
  @Transactional(readOnly = true)
  public byte[] exportToJSON(
      PlatformType platform, PublicationStatus status, Instant startDate, Instant endDate) {
    log.info("Exporting publications to JSON: platform={}, status={}", platform, status);

    List<PublicationJob> jobs =
        publicationJobRepository.findJobsForExport(platform, status, startDate, endDate);

    try {
      byte[] json = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsBytes(jobs);

      log.info("JSON export complete: {} items", jobs.size());
      return json;

    } catch (IOException e) {
      log.error("Failed to export to JSON", e);
      throw new RuntimeException("JSON export failed", e);
    }
  }

  /**
   * Generate publication report.
   *
   * @param startDate Start date for report
   * @param endDate End date for report
   * @return Report data
   */
  @Transactional(readOnly = true)
  public PublicationReport generateReport(Instant startDate, Instant endDate) {
    log.info("Generating publication report: {} to {}", startDate, endDate);

    List<PublicationJob> jobs =
        publicationJobRepository.findJobsForExport(null, null, startDate, endDate);

    PublicationReport report = new PublicationReport();
    report.setStartDate(startDate);
    report.setEndDate(endDate);
    report.setTotalPublications(jobs.size());

    // Calculate metrics
    long published =
        jobs.stream().filter(j -> j.getStatus() == PublicationStatus.PUBLISHED).count();
    long failed = jobs.stream().filter(j -> j.getStatus() == PublicationStatus.FAILED).count();
    long inProgress =
        jobs.stream()
            .filter(
                j ->
                    j.getStatus() == PublicationStatus.QUEUED
                        || j.getStatus() == PublicationStatus.UPLOADING
                        || j.getStatus() == PublicationStatus.PROCESSING)
            .count();

    report.setPublishedCount(published);
    report.setFailedCount(failed);
    report.setInProgressCount(inProgress);
    report.setSuccessRate(jobs.isEmpty() ? 0.0 : (double) published / jobs.size() * 100);

    // Per-platform breakdown
    for (PlatformType platform : PlatformType.values()) {
      long platformJobs = jobs.stream().filter(j -> j.getPlatform() == platform).count();
      long platformPublished =
          jobs.stream()
              .filter(
                  j -> j.getPlatform() == platform && j.getStatus() == PublicationStatus.PUBLISHED)
              .count();

      report.addPlatformMetric(platform.name().toLowerCase(), platformJobs, platformPublished);
    }

    log.info("Report generated: {} total publications", report.getTotalPublications());
    return report;
  }

  /** Escape CSV field. */
  private String escapeCsv(String field) {
    if (field == null) {
      return "";
    }

    // If field contains comma, quote, or newline, wrap in quotes and escape quotes
    if (field.contains(",") || field.contains("\"") || field.contains("\n")) {
      return "\"" + field.replace("\"", "\"\"") + "\"";
    }

    return field;
  }

  /** Publication report data class. */
  public static class PublicationReport {
    private Instant startDate;
    private Instant endDate;
    private int totalPublications;
    private long publishedCount;
    private long failedCount;
    private long inProgressCount;
    private double successRate;
    private java.util.Map<String, PlatformMetrics> platformMetrics = new java.util.HashMap<>();

    public void addPlatformMetric(String platform, long total, long published) {
      platformMetrics.put(platform, new PlatformMetrics(total, published));
    }

    // Getters and setters
    public Instant getStartDate() {
      return startDate;
    }

    public void setStartDate(Instant startDate) {
      this.startDate = startDate;
    }

    public Instant getEndDate() {
      return endDate;
    }

    public void setEndDate(Instant endDate) {
      this.endDate = endDate;
    }

    public int getTotalPublications() {
      return totalPublications;
    }

    public void setTotalPublications(int totalPublications) {
      this.totalPublications = totalPublications;
    }

    public long getPublishedCount() {
      return publishedCount;
    }

    public void setPublishedCount(long publishedCount) {
      this.publishedCount = publishedCount;
    }

    public long getFailedCount() {
      return failedCount;
    }

    public void setFailedCount(long failedCount) {
      this.failedCount = failedCount;
    }

    public long getInProgressCount() {
      return inProgressCount;
    }

    public void setInProgressCount(long inProgressCount) {
      this.inProgressCount = inProgressCount;
    }

    public double getSuccessRate() {
      return successRate;
    }

    public void setSuccessRate(double successRate) {
      this.successRate = successRate;
    }

    public java.util.Map<String, PlatformMetrics> getPlatformMetrics() {
      return platformMetrics;
    }
  }

  /** Platform metrics data class. */
  public static class PlatformMetrics {
    private final long total;
    private final long published;

    public PlatformMetrics(long total, long published) {
      this.total = total;
      this.published = published;
    }

    public long getTotal() {
      return total;
    }

    public long getPublished() {
      return published;
    }

    public double getSuccessRate() {
      return total == 0 ? 0.0 : (double) published / total * 100;
    }
  }
}
