package com.pompom.creative.performance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class PerformanceClassifierServiceTest {

  @Mock private PerformanceClassificationRepository classificationRepo;

  @Mock private VideoMetricsRepository metricsRepo;

  @Mock private PublicationJobRepository publicationJobRepo;

  @InjectMocks private PerformanceClassifierService classifierService;

  private PublicationJob testJob;

  @BeforeEach
  void setUp() {
    testJob =
        PublicationJob.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.TIKTOK)
            .status(PublicationStatus.PUBLISHED)
            .completedAt(Instant.now().minusSeconds(30 * 24 * 3600)) // 30 days ago
            .build();
  }

  @Test
  void classifyVideo_earlyRejection_classifiesCorrectly() {
    // Given: Low views in first 24h
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(100L, 30), // T+30m
            createMetrics(200L, 60), // T+1h
            createMetrics(500L, 1440) // T+24h - below 1K threshold
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then
    assertThat(classification.getCategory())
        .isEqualTo(PerformanceClassification.PerformanceCategory.EARLY_REJECTION);
    assertThat(classification.getFinalViews()).isEqualTo(500L);
    verify(classificationRepo).save(any(PerformanceClassification.class));
  }

  @Test
  void classifyVideo_breakout_classifiesCorrectly() {
    // Given: High velocity + high final views + HAS PLATEAU
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(5000L, 30), // T+30m
            createMetrics(15000L, 60), // T+1h
            createMetrics(50000L, 1440), // T+24h - >2K views/hour velocity
            createMetrics(99000L, 4320), // T+3d
            createMetrics(101000L, 10080), // T+7d - plateau (2% growth)
            createMetrics(103000L, 43200) // T+30d - plateau (2% growth)
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then
    assertThat(classification.getCategory())
        .isEqualTo(PerformanceClassification.PerformanceCategory.BREAKOUT);
    assertThat(classification.getVelocityScore()).isGreaterThan(BigDecimal.valueOf(2000));
    assertThat(classification.getFinalViews()).isGreaterThan(50000L);
    assertThat(classification.isWinner()).isTrue();
    assertThat(classification.getTier()).isEqualTo(1);
  }

  @Test
  void classifyVideo_delayedBreakout_classifiesCorrectly() {
    // Given: Low velocity early, high final views, HAS PLATEAU
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(500L, 30), // T+30m
            createMetrics(1000L, 60), // T+1h
            createMetrics(5000L, 1440), // T+24h - <2K views/hour velocity
            createMetrics(49000L, 4320), // T+3d - sudden spike
            createMetrics(50000L, 10080), // T+7d - plateau (2% growth)
            createMetrics(51000L, 43200) // T+30d - plateau (2% growth)
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then
    assertThat(classification.getCategory())
        .isEqualTo(PerformanceClassification.PerformanceCategory.DELAYED_BREAKOUT);
    assertThat(classification.getVelocityScore()).isLessThan(BigDecimal.valueOf(2000));
    assertThat(classification.getFinalViews()).isGreaterThan(50000L);
    assertThat(classification.isWinner()).isTrue();
    assertThat(classification.getTier()).isEqualTo(2);
  }

  @Test
  void classifyVideo_longTail_classifiesCorrectly() {
    // Given: Strong performance after day 7
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(2000L, 30),
            createMetrics(5000L, 1440),
            createMetrics(10000L, 10080), // T+7d
            createMetrics(20000L, 43200) // T+30d - 50% views after day 7
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then
    assertThat(classification.getCategory())
        .isEqualTo(PerformanceClassification.PerformanceCategory.LONG_TAIL);
    assertThat(classification.getTailStrength()).isGreaterThan(BigDecimal.valueOf(0.30));
    assertThat(classification.getTier()).isEqualTo(3);
  }

  @Test
  void classifyVideo_weak_classifiesCorrectly() {
    // Given: Low final views
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(500L, 30),
            createMetrics(1500L, 1440),
            createMetrics(3000L, 10080),
            createMetrics(4000L, 43200) // <5K threshold
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then
    assertThat(classification.getCategory())
        .isEqualTo(PerformanceClassification.PerformanceCategory.WEAK);
    assertThat(classification.getFinalViews()).isLessThan(5000L);
    assertThat(classification.isWinner()).isFalse();
    assertThat(classification.getTier()).isEqualTo(4);
  }

  @Test
  void classifyVideo_medium_classifiesCorrectly() {
    // Given: Average performance, no strong tail
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(1000L, 30),
            createMetrics(3000L, 1440),
            createMetrics(8000L, 10080), // T+7d
            createMetrics(10000L, 43200) // T+30d - only 2K views after day 7 (20% tail)
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then
    assertThat(classification.getCategory())
        .isEqualTo(PerformanceClassification.PerformanceCategory.MEDIUM);
    assertThat(classification.getFinalViews()).isBetween(5000L, 20000L);
    assertThat(classification.getTier()).isEqualTo(3);
  }

  @Test
  void classifyVideo_noMetrics_throwsException() {
    // Given
    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(List.of());

    // When/Then
    assertThatThrownBy(() -> classifierService.classifyVideo(testJob.getId()))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("No metrics available");
  }

  @Test
  void classifyVideo_jobNotFound_throwsException() {
    // Given
    UUID nonExistentId = UUID.randomUUID();
    when(publicationJobRepo.findById(nonExistentId)).thenReturn(Optional.empty());

    // When/Then
    assertThatThrownBy(() -> classifierService.classifyVideo(nonExistentId))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Publication job not found");
  }

  @Test
  void classifyVideo_calculatesConfidence_correctly() {
    // Given: Complete data set (6 points + final metrics)
    List<VideoMetrics> timeline =
        List.of(
            createMetrics(1000L, 30, false),
            createMetrics(2000L, 60, false),
            createMetrics(5000L, 360, false),
            createMetrics(10000L, 1440, false),
            createMetrics(15000L, 10080, false),
            createMetrics(20000L, 43200, true) // Final
            );

    when(publicationJobRepo.findById(testJob.getId())).thenReturn(Optional.of(testJob));
    when(metricsRepo.findMetricsTimeline(testJob.getId())).thenReturn(timeline);
    when(classificationRepo.save(any(PerformanceClassification.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PerformanceClassification classification = classifierService.classifyVideo(testJob.getId());

    // Then: High confidence (50 base + 20 for 6+ points + 30 for final = 100)
    assertThat(classification.getConfidenceScore()).isEqualByComparingTo("100.00");
  }

  private VideoMetrics createMetrics(Long views, int minutesSincePublish) {
    return createMetrics(views, minutesSincePublish, false);
  }

  private VideoMetrics createMetrics(Long views, int minutesSincePublish, boolean isFinal) {
    return VideoMetrics.builder()
        .id(UUID.randomUUID())
        .publicationJob(testJob)
        .views(views)
        .likes((long) (views * 0.03))
        .comments((long) (views * 0.002))
        .shares((long) (views * 0.01))
        .timeSincePublishMinutes(minutesSincePublish)
        .isFinal(isFinal)
        .collectedAt(Instant.now())
        .build();
  }
}
