package com.pompom.creative.metrics;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MetricsCollectorServiceTest {

  @Mock private MetricsCollectionJobRepository collectionJobRepo;

  @Mock private VideoMetricsRepository metricsRepo;

  @Mock private PublicationJobRepository publicationJobRepo;

  @InjectMocks private MetricsCollectorService metricsCollectorService;

  private PublicationJob testJob;

  @BeforeEach
  void setUp() {
    testJob =
        PublicationJob.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.TIKTOK)
            .status(PublicationStatus.PUBLISHED)
            .platformPostId("video123")
            .completedAt(Instant.now().minusSeconds(3600)) // 1 hour ago
            .build();
  }

  @Test
  void scheduleCollection_validJob_creates12CollectionPoints() {
    // MetricsCollectorService.COLLECTION_POINTS was intentionally expanded from the original
    // 6 checkpoints to 12 ("Strategic decision #5 - expanded checkpoints"); this test asserts
    // the current production checkpoint set rather than the superseded 6-point one.
    // Given
    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(collectionJobRepo.save(any(MetricsCollectionJob.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    List<MetricsCollectionJob> jobs = metricsCollectorService.scheduleCollection(testJob.getId());

    // Then
    assertThat(jobs).hasSize(12);
    assertThat(jobs)
        .extracting(MetricsCollectionJob::getCollectionPoint)
        .containsExactly(
            "T+15M", "T+30M", "T+1H", "T+90M", "T+2H", "T+3H", "T+6H", "T+12H", "T+24H", "T+48H",
            "T+7D", "T+30D");
    assertThat(jobs).allMatch(j -> j.getStatus() == MetricsCollectionJob.JobStatus.PENDING);

    verify(collectionJobRepo, times(12)).save(any(MetricsCollectionJob.class));
  }

  @Test
  void scheduleCollection_unpublishedJob_throwsException() {
    // Given
    PublicationJob unpublishedJob =
        PublicationJob.builder()
            .id(UUID.randomUUID())
            .status(PublicationStatus.QUEUED)
            .completedAt(null)
            .build();

    when(publicationJobRepo.findById(unpublishedJob.getId()))
        .thenReturn(Optional.of(unpublishedJob));

    // When/Then
    assertThatThrownBy(() -> metricsCollectorService.scheduleCollection(unpublishedJob.getId()))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("Cannot schedule collection for unpublished job");
  }

  @Test
  void scheduleCollection_jobNotFound_throwsException() {
    // Given
    UUID nonExistentId = UUID.randomUUID();
    when(publicationJobRepo.findById(nonExistentId)).thenReturn(Optional.empty());

    // When/Then
    assertThatThrownBy(() -> metricsCollectorService.scheduleCollection(nonExistentId))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Publication job not found");
  }

  @Test
  void collectMetrics_validJob_savesMetrics() {
    // Given
    MetricsCollectionJob collectionJob =
        MetricsCollectionJob.builder()
            .id(UUID.randomUUID())
            .publicationJob(testJob)
            .collectionPoint("T+1H")
            .scheduledAt(Instant.now())
            .status(MetricsCollectionJob.JobStatus.PENDING)
            .build();

    when(collectionJobRepo.save(any(MetricsCollectionJob.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    when(metricsRepo.save(any(VideoMetrics.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    VideoMetrics metrics = metricsCollectorService.collectMetrics(collectionJob);

    // Then
    assertThat(metrics).isNotNull();
    assertThat(metrics.getPlatform()).isEqualTo(PlatformType.TIKTOK);
    assertThat(metrics.getPlatformVideoId()).isEqualTo("video123");
    assertThat(metrics.getViews()).isGreaterThan(0);
    assertThat(metrics.getLikes()).isGreaterThan(0);
    assertThat(metrics.getCollectionSource()).isEqualTo("API");

    verify(metricsRepo).save(any(VideoMetrics.class));
    verify(collectionJobRepo, times(2)).save(any(MetricsCollectionJob.class));

    assertThat(collectionJob.getStatus()).isEqualTo(MetricsCollectionJob.JobStatus.COMPLETED);
    assertThat(collectionJob.getExecutedAt()).isNotNull();
  }

  @Test
  void collectMetrics_finalCollectionPoint_marksFinal() {
    // Given
    MetricsCollectionJob collectionJob =
        MetricsCollectionJob.builder()
            .id(UUID.randomUUID())
            .publicationJob(testJob)
            .collectionPoint("T+30D")
            .scheduledAt(Instant.now())
            .status(MetricsCollectionJob.JobStatus.PENDING)
            .build();

    when(collectionJobRepo.save(any(MetricsCollectionJob.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    ArgumentCaptor<VideoMetrics> metricsCaptor = ArgumentCaptor.forClass(VideoMetrics.class);
    when(metricsRepo.save(metricsCaptor.capture()))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    metricsCollectorService.collectMetrics(collectionJob);

    // Then
    VideoMetrics savedMetrics = metricsCaptor.getValue();
    assertThat(savedMetrics.getIsFinal()).isTrue();
  }

  @Test
  void recordManualMetrics_validData_savesMetrics() {
    // Given
    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.save(any(VideoMetrics.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    VideoMetrics metrics =
        metricsCollectorService.recordManualMetrics(testJob.getId(), 10000L, 500L, 50L, 100L, 60);

    // Then
    assertThat(metrics).isNotNull();
    assertThat(metrics.getViews()).isEqualTo(10000L);
    assertThat(metrics.getLikes()).isEqualTo(500L);
    assertThat(metrics.getComments()).isEqualTo(50L);
    assertThat(metrics.getShares()).isEqualTo(100L);
    assertThat(metrics.getTimeSincePublishMinutes()).isEqualTo(60);
    assertThat(metrics.getCollectionSource()).isEqualTo("MANUAL_ENTRY");

    verify(metricsRepo).save(any(VideoMetrics.class));
  }

  @Test
  void getMetricsTimeline_returnsChronologicalData() {
    // Given
    List<VideoMetrics> mockTimeline =
        List.of(createMetrics(1000L, 30), createMetrics(2500L, 60), createMetrics(5000L, 360));

    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(mockTimeline);

    // When
    List<VideoMetrics> timeline = metricsCollectorService.getMetricsTimeline(testJob.getId());

    // Then
    assertThat(timeline).hasSize(3);
    assertThat(timeline.get(0).getViews()).isEqualTo(1000L);
    assertThat(timeline.get(1).getViews()).isEqualTo(2500L);
    assertThat(timeline.get(2).getViews()).isEqualTo(5000L);
  }

  @Test
  void videoMetrics_calculateEngagementRate_correctCalculation() {
    // Given
    VideoMetrics metrics =
        VideoMetrics.builder().views(1000L).likes(50L).comments(10L).shares(5L).build();

    // When
    var engagementRate = metrics.calculateEngagementRate();

    // Then (50+10+5)/1000*100 = 6.5%
    assertThat(engagementRate).isEqualByComparingTo("6.50");
  }

  @Test
  void videoMetrics_calculateViralityScore_correctCalculation() {
    // Given
    VideoMetrics metrics = VideoMetrics.builder().views(1000L).shares(15L).build();

    // When
    var viralityScore = metrics.calculateViralityScore();

    // Then 15/1000*100 = 1.5%
    assertThat(viralityScore).isEqualByComparingTo("1.50");
  }

  private VideoMetrics createMetrics(Long views, Integer minutesSincePublish) {
    return VideoMetrics.builder()
        .id(UUID.randomUUID())
        .publicationJob(testJob)
        .views(views)
        .timeSincePublishMinutes(minutesSincePublish)
        .collectedAt(Instant.now())
        .build();
  }
}
