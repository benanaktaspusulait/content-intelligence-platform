package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationAnalytics;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.client.InstagramMetricsClient;
import com.pompom.creative.metrics.client.TikTokMetricsClient;
import com.pompom.creative.metrics.client.YouTubeMetricsClient;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationAnalyticsRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class AnalyticsServiceTest {

  @Mock private PublicationAnalyticsRepository analyticsRepository;

  @Mock private PublicationJobRepository publicationJobRepository;

  @Mock private CredentialManager credentialManager;

  @Mock private TikTokMetricsClient tiktokMetricsClient;

  @Mock private YouTubeMetricsClient youtubeMetricsClient;

  @Mock private InstagramMetricsClient instagramMetricsClient;

  private AnalyticsService analyticsService;

  @BeforeEach
  void setUp() {
    analyticsService =
        new AnalyticsService(
            analyticsRepository,
            publicationJobRepository,
            credentialManager,
            tiktokMetricsClient,
            youtubeMetricsClient,
            instagramMetricsClient);
    ReflectionTestUtils.setField(analyticsService, "useRealApi", true);
  }

  @Test
  void fetchAnalytics_newJob_createsAnalytics() throws Exception {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationJob job =
        PublicationJob.builder()
            .id(jobId)
            .platform(PlatformType.TIKTOK)
            .platformPostId("post-123")
            .platformVideoId("video-123")
            .status(PublicationStatus.PUBLISHED)
            .build();

    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.of(job));
    when(credentialManager.isConnected(PlatformType.TIKTOK)).thenReturn(true);
    when(analyticsRepository.findByPublicationJobId(jobId)).thenReturn(Optional.empty());
    when(analyticsRepository.save(any(PublicationAnalytics.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    when(tiktokMetricsClient.fetchMetrics("video-123"))
        .thenReturn(observedMetrics(PlatformType.TIKTOK, "video-123", 1_234L, 45L));

    // When
    PublicationAnalytics result = analyticsService.fetchAnalytics(jobId);

    // Then
    assertThat(result).isNotNull();
    assertThat(result.getPublicationJobId()).isEqualTo(jobId);
    assertThat(result.getPlatform()).isEqualTo(PlatformType.TIKTOK);
    assertThat(result.getViews()).isEqualTo(1_234L);

    verify(analyticsRepository).save(any(PublicationAnalytics.class));
  }

  @Test
  void fetchAnalytics_existingAnalytics_updatesMetrics() throws Exception {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationJob job =
        PublicationJob.builder()
            .id(jobId)
            .platform(PlatformType.YOUTUBE)
            .platformPostId("video-456")
            .platformVideoId("video-456")
            .status(PublicationStatus.PUBLISHED)
            .build();

    PublicationAnalytics existing =
        PublicationAnalytics.builder()
            .id(UUID.randomUUID())
            .publicationJobId(jobId)
            .platform(PlatformType.YOUTUBE)
            .views(1000L)
            .likes(50L)
            .build();

    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.of(job));
    when(credentialManager.isConnected(PlatformType.YOUTUBE)).thenReturn(true);
    when(analyticsRepository.findByPublicationJobId(jobId)).thenReturn(Optional.of(existing));
    when(analyticsRepository.save(any(PublicationAnalytics.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    when(youtubeMetricsClient.fetchMetrics("video-456"))
        .thenReturn(observedMetrics(PlatformType.YOUTUBE, "video-456", 2_500L, 100L));

    // When
    PublicationAnalytics result = analyticsService.fetchAnalytics(jobId);

    // Then
    assertThat(result.getId()).isEqualTo(existing.getId());
    assertThat(result.getViews()).isEqualTo(2_500L);

    verify(analyticsRepository).save(existing);
  }

  @Test
  void fetchAnalytics_platformNotConnected_returnsNull() {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationJob job = PublicationJob.builder().id(jobId).platform(PlatformType.FACEBOOK).build();

    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.of(job));
    when(credentialManager.isConnected(PlatformType.FACEBOOK)).thenReturn(false);

    // When
    PublicationAnalytics result = analyticsService.fetchAnalytics(jobId);

    // Then
    assertThat(result).isNull();
    verify(analyticsRepository, never()).save(any());
  }

  @Test
  void getAnalytics_existingAnalytics_returnsData() {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationAnalytics analytics =
        PublicationAnalytics.builder().publicationJobId(jobId).views(5000L).likes(250L).build();

    when(analyticsRepository.findByPublicationJobId(jobId)).thenReturn(Optional.of(analytics));

    // When
    Optional<PublicationAnalytics> result = analyticsService.getAnalytics(jobId);

    // Then
    assertThat(result).isPresent();
    assertThat(result.get().getViews()).isEqualTo(5000L);
  }

  @Test
  void getAnalyticsByPlatform_returnsFilteredList() {
    // Given
    List<PublicationAnalytics> tiktokAnalytics =
        List.of(
            PublicationAnalytics.builder().platform(PlatformType.TIKTOK).build(),
            PublicationAnalytics.builder().platform(PlatformType.TIKTOK).build());

    when(analyticsRepository.findByPlatform(PlatformType.TIKTOK)).thenReturn(tiktokAnalytics);

    // When
    List<PublicationAnalytics> result =
        analyticsService.getAnalyticsByPlatform(PlatformType.TIKTOK);

    // Then
    assertThat(result).hasSize(2);
    assertThat(result).allMatch(a -> a.getPlatform() == PlatformType.TIKTOK);
  }

  @Test
  void getAggregatedStats_calculatesCorrectly() {
    // Given
    when(analyticsRepository.sumTotalViews()).thenReturn(100000L);
    when(analyticsRepository.sumViewsByPlatform(any())).thenReturn(25000L);
    when(analyticsRepository.avgEngagementRateByPlatform(any())).thenReturn(5.5);
    when(analyticsRepository.findByPlatform(any())).thenReturn(List.of());

    // When
    Map<String, Object> stats = analyticsService.getAggregatedStats();

    // Then
    assertThat(stats).containsKey("totalViews");
    assertThat(stats).containsKey("platforms");
    assertThat(stats.get("totalViews")).isEqualTo(100000L);
  }

  @Test
  void publicationAnalytics_calculateEngagementRate_computesCorrectly() {
    // Given
    PublicationAnalytics analytics =
        PublicationAnalytics.builder()
            .views(1000L)
            .likes(50L)
            .comments(20L)
            .shares(10L)
            .saves(5L)
            .build();

    // When
    analytics.calculateEngagementRate();

    // Then
    // (50 + 20 + 10 + 5) / 1000 * 100 = 8.5%
    assertThat(analytics.getEngagementRate()).isEqualTo(8.5);
  }

  @Test
  void publicationAnalytics_updateMetrics_updatesAllFields() {
    // Given
    PublicationAnalytics existing = PublicationAnalytics.builder().views(100L).likes(5L).build();

    PublicationAnalytics newData =
        PublicationAnalytics.builder().views(1000L).likes(50L).comments(20L).shares(10L).build();

    // When
    existing.updateMetrics(newData);

    // Then
    assertThat(existing.getViews()).isEqualTo(1000L);
    assertThat(existing.getLikes()).isEqualTo(50L);
    assertThat(existing.getComments()).isEqualTo(20L);
    assertThat(existing.getShares()).isEqualTo(10L);
    assertThat(existing.getEngagementRate()).isNotNull();
  }

  private VideoMetrics observedMetrics(
      PlatformType platform, String videoId, Long views, Long likes) {
    return VideoMetrics.builder()
        .platform(platform)
        .platformVideoId(videoId)
        .views(views)
        .likes(likes)
        .comments(12L)
        .shares(3L)
        .saves(1L)
        .collectedAt(java.time.Instant.now())
        .build();
  }
}
