package com.pompom.creative.export;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ExportServiceTest {

  @Mock private PublicationJobRepository publicationJobRepository;

  @InjectMocks private ExportService exportService;

  private List<PublicationJob> testJobs;

  @BeforeEach
  void setUp() {
    ObjectMapper objectMapper = new ObjectMapper();
    objectMapper.registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());
    objectMapper.disable(
        com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    exportService = new ExportService(publicationJobRepository, objectMapper);

    testJobs =
        List.of(
            PublicationJob.builder()
                .id(UUID.randomUUID())
                .platform(PlatformType.TIKTOK)
                .status(PublicationStatus.PUBLISHED)
                .title("Test Video 1")
                .caption("Caption 1")
                .hashtags("tag1,tag2")
                .videoPath("/tmp/video1.mp4")
                .queuedAt(Instant.now())
                .build(),
            PublicationJob.builder()
                .id(UUID.randomUUID())
                .platform(PlatformType.YOUTUBE)
                .status(PublicationStatus.PUBLISHED)
                .title("Test Video 2")
                .caption("Caption 2")
                .videoPath("/tmp/video2.mp4")
                .queuedAt(Instant.now())
                .build());
  }

  @Test
  void exportToCSV_validData_generatesCSV() {
    // Given
    when(publicationJobRepository.findJobsForExport(any(), any(), any(), any()))
        .thenReturn(testJobs);

    // When
    byte[] csv = exportService.exportToCSV(null, null, null, null);

    // Then
    assertThat(csv).isNotEmpty();

    String csvContent = new String(csv, StandardCharsets.UTF_8);
    assertThat(csvContent).contains("ID,Platform,Status");
    assertThat(csvContent).contains("TIKTOK");
    assertThat(csvContent).contains("YOUTUBE");
    assertThat(csvContent).contains("Test Video 1");
    assertThat(csvContent).contains("Test Video 2");
  }

  @Test
  void exportToCSV_withSpecialCharacters_escapesCorrectly() {
    // Given
    PublicationJob jobWithComma =
        PublicationJob.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.FACEBOOK)
            .status(PublicationStatus.PUBLISHED)
            .title("Title, with comma")
            .caption("Caption with \"quotes\"")
            .queuedAt(Instant.now())
            .build();

    when(publicationJobRepository.findJobsForExport(any(), any(), any(), any()))
        .thenReturn(List.of(jobWithComma));

    // When
    byte[] csv = exportService.exportToCSV(null, null, null, null);

    // Then
    String csvContent = new String(csv, StandardCharsets.UTF_8);
    assertThat(csvContent).contains("\"Title, with comma\"");
    assertThat(csvContent).contains("\"Caption with \"\"quotes\"\"\"");
  }

  @Test
  void exportToJSON_validData_generatesJSON() throws Exception {
    // Given
    when(publicationJobRepository.findJobsForExport(any(), any(), any(), any()))
        .thenReturn(testJobs);

    // When
    byte[] json = exportService.exportToJSON(null, null, null, null);

    // Then
    assertThat(json).isNotEmpty();

    String jsonContent = new String(json, StandardCharsets.UTF_8);
    assertThat(jsonContent).contains("TIKTOK");
    assertThat(jsonContent).contains("YOUTUBE");
    assertThat(jsonContent).contains("Test Video 1");
  }

  @Test
  void generateReport_calculatesMetricsCorrectly() {
    // Given
    List<PublicationJob> jobs =
        List.of(
            createJob(PlatformType.TIKTOK, PublicationStatus.PUBLISHED),
            createJob(PlatformType.TIKTOK, PublicationStatus.PUBLISHED),
            createJob(PlatformType.TIKTOK, PublicationStatus.FAILED),
            createJob(PlatformType.YOUTUBE, PublicationStatus.PUBLISHED),
            createJob(PlatformType.FACEBOOK, PublicationStatus.QUEUED));

    when(publicationJobRepository.findJobsForExport(any(), any(), any(), any())).thenReturn(jobs);

    Instant start = Instant.now().minusSeconds(86400);
    Instant end = Instant.now();

    // When
    ExportService.PublicationReport report = exportService.generateReport(start, end);

    // Then
    assertThat(report.getTotalPublications()).isEqualTo(5);
    assertThat(report.getPublishedCount()).isEqualTo(3);
    assertThat(report.getFailedCount()).isEqualTo(1);
    assertThat(report.getInProgressCount()).isEqualTo(1);
    assertThat(report.getSuccessRate()).isEqualTo(60.0); // 3/5 * 100

    // Check platform metrics
    assertThat(report.getPlatformMetrics()).containsKey("tiktok");
    assertThat(report.getPlatformMetrics().get("tiktok").getTotal()).isEqualTo(3);
    assertThat(report.getPlatformMetrics().get("tiktok").getPublished()).isEqualTo(2);
  }

  @Test
  void generateReport_emptyData_handlesGracefully() {
    // Given
    when(publicationJobRepository.findJobsForExport(any(), any(), any(), any()))
        .thenReturn(List.of());

    // When
    ExportService.PublicationReport report =
        exportService.generateReport(Instant.now(), Instant.now());

    // Then
    assertThat(report.getTotalPublications()).isEqualTo(0);
    assertThat(report.getSuccessRate()).isEqualTo(0.0);
  }

  @Test
  void platformMetrics_calculatesSuccessRate() {
    // Given
    ExportService.PlatformMetrics metrics = new ExportService.PlatformMetrics(10, 7);

    // When/Then
    assertThat(metrics.getTotal()).isEqualTo(10);
    assertThat(metrics.getPublished()).isEqualTo(7);
    assertThat(metrics.getSuccessRate()).isEqualTo(70.0);
  }

  @Test
  void platformMetrics_zeroTotal_handlesGracefully() {
    // Given
    ExportService.PlatformMetrics metrics = new ExportService.PlatformMetrics(0, 0);

    // When/Then
    assertThat(metrics.getSuccessRate()).isEqualTo(0.0);
  }

  private PublicationJob createJob(PlatformType platform, PublicationStatus status) {
    return PublicationJob.builder()
        .id(UUID.randomUUID())
        .platform(platform)
        .status(status)
        .queuedAt(Instant.now())
        .build();
  }
}
