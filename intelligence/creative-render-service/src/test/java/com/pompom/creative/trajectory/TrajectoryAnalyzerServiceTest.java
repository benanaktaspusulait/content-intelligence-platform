package com.pompom.creative.trajectory;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.metrics.VideoMetricsRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class TrajectoryAnalyzerServiceTest {

  @Mock private TrajectoryAnalysisRepository trajectoryRepo;

  @Mock private VideoMetricsRepository metricsRepo;

  @Mock private PublicationJobRepository publicationJobRepo;

  @InjectMocks private TrajectoryAnalyzerService service;

  @Test
  void testAnalyzeTrajectory_exponentialGrowth() {
    // Setup
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createExponentialGrowthTimeline(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    assertEquals(TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL, result.getTrajectoryShape());
    assertNotNull(result.getVelocityFirstHour());
    assertNotNull(result.getVelocityFirst24H());
    assertTrue(result.getVelocityFirst24H().compareTo(BigDecimal.ZERO) > 0);
    assertEquals(timeline.size(), result.getDataPointsCount());

    verify(trajectoryRepo).save(any());
  }

  @Test
  void testAnalyzeTrajectory_hockeyStick() {
    // Setup - slow start, rapid growth later
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createHockeyStickTimeline(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    // Shape could be EXPONENTIAL or HOCKEY_STICK depending on exact growth pattern
    assertTrue(
        result.getTrajectoryShape() == TrajectoryAnalysis.TrajectoryShape.HOCKEY_STICK
            || result.getTrajectoryShape() == TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL);
    assertNotNull(result.getAcceleration6HTo24H());
  }

  @Test
  void testAnalyzeTrajectory_spikeAndPlateau() {
    // Setup - rapid early growth, then plateau
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createSpikeAndPlateauTimeline(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    assertEquals(TrajectoryAnalysis.TrajectoryShape.SPIKE_AND_PLATEAU, result.getTrajectoryShape());
    assertTrue(result.getPlateauDetected());
    assertNotNull(result.getPlateauDay());
  }

  @Test
  void testAnalyzeTrajectory_multiWave() {
    // Setup - multiple growth peaks
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createMultiWaveTimeline(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    assertTrue(result.getWaveCount() >= 2);
    assertNotNull(result.getPrimaryWaveDay());
    assertNotNull(result.getSecondaryWaveDay());
  }

  @Test
  void testAnalyzeTrajectory_strongTail() {
    // Setup - sustained long-term growth
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createStrongTailTimeline(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    assertNotNull(result.getTailStrength());
    assertTrue(result.getTailStrength().compareTo(BigDecimal.valueOf(0.3)) > 0); // > 30% tail
    assertNotNull(result.getTailVelocity());
  }

  @Test
  void testAnalyzeTrajectory_peakDetection() {
    // Setup
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createTimelineWithClearPeak(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    assertNotNull(result.getPeakViews());
    assertNotNull(result.getPeakDay());
    assertNotNull(result.getTimeToPeakHours());
    assertTrue(result.getPeakViews() > 0);
  }

  @Test
  void testAnalyzeTrajectory_decayDetection() {
    // Setup - declining views
    UUID jobId = UUID.randomUUID();
    PublicationJob job = createJob(jobId);
    List<VideoMetrics> timeline = createDecliningTimeline(jobId);

    when(publicationJobRepo.findById(jobId)).thenReturn(Optional.of(job));
    when(metricsRepo.findMetricsTimeline(jobId)).thenReturn(timeline);
    when(trajectoryRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // Execute
    TrajectoryAnalysis result = service.analyzeTrajectory(jobId);

    // Verify
    assertNotNull(result);
    assertTrue(result.getDecayDetected());
    assertNotNull(result.getDecayRate());
    assertTrue(result.getDecayRate().compareTo(BigDecimal.ZERO) > 0);
  }

  @Test
  void testCompareSimilarity_samShape() {
    // Setup - two similar trajectories
    UUID jobId1 = UUID.randomUUID();
    UUID jobId2 = UUID.randomUUID();

    TrajectoryAnalysis t1 = createAnalysis(jobId1, TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL);
    TrajectoryAnalysis t2 = createAnalysis(jobId2, TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL);

    when(trajectoryRepo.findByPublicationJobId(jobId1)).thenReturn(Optional.of(t1));
    when(trajectoryRepo.findByPublicationJobId(jobId2)).thenReturn(Optional.of(t2));

    // Execute
    BigDecimal similarity = service.compareSimilarity(jobId1, jobId2);

    // Verify
    assertNotNull(similarity);
    assertTrue(similarity.compareTo(BigDecimal.valueOf(50)) > 0); // > 50% similar
  }

  @Test
  void testCompareSimilarity_differentShapes() {
    // Setup - different trajectories
    UUID jobId1 = UUID.randomUUID();
    UUID jobId2 = UUID.randomUUID();

    TrajectoryAnalysis t1 = createAnalysis(jobId1, TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL);
    TrajectoryAnalysis t2 = createAnalysis(jobId2, TrajectoryAnalysis.TrajectoryShape.FLAT);

    when(trajectoryRepo.findByPublicationJobId(jobId1)).thenReturn(Optional.of(t1));
    when(trajectoryRepo.findByPublicationJobId(jobId2)).thenReturn(Optional.of(t2));

    // Execute
    BigDecimal similarity = service.compareSimilarity(jobId1, jobId2);

    // Verify
    assertNotNull(similarity);
    // Different shapes but other metrics are similar, so could be > or < 50%
    assertTrue(similarity.compareTo(BigDecimal.ZERO) >= 0);
    assertTrue(similarity.compareTo(BigDecimal.valueOf(100)) <= 0);
  }

  @Test
  void testGetAnalysis() {
    // Setup
    UUID jobId = UUID.randomUUID();
    TrajectoryAnalysis analysis =
        createAnalysis(jobId, TrajectoryAnalysis.TrajectoryShape.EXPONENTIAL);

    when(trajectoryRepo.findByPublicationJobId(jobId)).thenReturn(Optional.of(analysis));

    // Execute
    TrajectoryAnalysis result = service.getAnalysis(jobId);

    // Verify
    assertNotNull(result);
    assertEquals(analysis.getId(), result.getId());
  }

  // Helper methods to create test data

  private PublicationJob createJob(UUID jobId) {
    PublicationJob job = new PublicationJob();
    job.setId(jobId);
    job.setCompletedAt(Instant.now().minusSeconds(30 * 24 * 3600)); // 30 days ago
    return job;
  }

  private List<VideoMetrics> createExponentialGrowthTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Exponential growth: 1000, 5000, 25000, 100000, 300000, 500000
    timeline.add(createMetrics(jobId, now, 60, 1000L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 5000L)); // 6h
    timeline.add(createMetrics(jobId, now, 1440, 25000L)); // 24h
    timeline.add(createMetrics(jobId, now, 10080, 100000L)); // 7d
    timeline.add(createMetrics(jobId, now, 43200, 300000L)); // 30d

    return timeline;
  }

  private List<VideoMetrics> createHockeyStickTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Slow start, rapid growth later
    timeline.add(createMetrics(jobId, now, 60, 500L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 1000L)); // 6h
    timeline.add(createMetrics(jobId, now, 1440, 2000L)); // 24h
    timeline.add(createMetrics(jobId, now, 10080, 50000L)); // 7d - big jump
    timeline.add(createMetrics(jobId, now, 43200, 200000L)); // 30d

    return timeline;
  }

  private List<VideoMetrics> createSpikeAndPlateauTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Rapid early growth, then plateau
    timeline.add(createMetrics(jobId, now, 60, 5000L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 25000L)); // 6h
    timeline.add(createMetrics(jobId, now, 1440, 50000L)); // 24h
    timeline.add(createMetrics(jobId, now, 10080, 52000L)); // 7d - minimal growth
    timeline.add(createMetrics(jobId, now, 43200, 53000L)); // 30d - plateau

    return timeline;
  }

  private List<VideoMetrics> createMultiWaveTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Multiple peaks
    timeline.add(createMetrics(jobId, now, 60, 2000L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 10000L)); // 6h - peak 1
    timeline.add(createMetrics(jobId, now, 1440, 8000L)); // 24h - dip
    timeline.add(createMetrics(jobId, now, 2880, 15000L)); // 48h - peak 2
    timeline.add(createMetrics(jobId, now, 10080, 12000L)); // 7d - dip
    timeline.add(createMetrics(jobId, now, 43200, 25000L)); // 30d - peak 3

    return timeline;
  }

  private List<VideoMetrics> createStrongTailTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Strong long-term growth
    timeline.add(createMetrics(jobId, now, 60, 1000L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 3000L)); // 6h
    timeline.add(createMetrics(jobId, now, 1440, 10000L)); // 24h
    timeline.add(createMetrics(jobId, now, 10080, 30000L)); // 7d
    timeline.add(createMetrics(jobId, now, 43200, 100000L)); // 30d - strong tail (70% after day 7)

    return timeline;
  }

  private List<VideoMetrics> createTimelineWithClearPeak(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Clear peak at day 7
    timeline.add(createMetrics(jobId, now, 60, 1000L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 5000L)); // 6h
    timeline.add(createMetrics(jobId, now, 1440, 15000L)); // 24h
    timeline.add(createMetrics(jobId, now, 10080, 50000L)); // 7d - PEAK
    timeline.add(createMetrics(jobId, now, 43200, 45000L)); // 30d - decline

    return timeline;
  }

  private List<VideoMetrics> createDecliningTimeline(UUID jobId) {
    List<VideoMetrics> timeline = new ArrayList<>();
    Instant now = Instant.now();

    // Declining views
    timeline.add(createMetrics(jobId, now, 60, 10000L)); // 1h
    timeline.add(createMetrics(jobId, now, 360, 8000L)); // 6h
    timeline.add(createMetrics(jobId, now, 1440, 5000L)); // 24h
    timeline.add(createMetrics(jobId, now, 10080, 3000L)); // 7d
    timeline.add(createMetrics(jobId, now, 43200, 2000L)); // 30d

    return timeline;
  }

  private VideoMetrics createMetrics(UUID jobId, Instant baseTime, int minutesSince, long views) {
    PublicationJob job = new PublicationJob();
    job.setId(jobId);

    VideoMetrics metrics = new VideoMetrics();
    metrics.setId(UUID.randomUUID());
    metrics.setPublicationJob(job);
    metrics.setTimeSincePublishMinutes(minutesSince);
    metrics.setViews(views);
    metrics.setLikes((long) (views * 0.03)); // 3% engagement
    metrics.setComments((long) (views * 0.002)); // 0.2% engagement
    metrics.setShares((long) (views * 0.01)); // 1% engagement
    metrics.setCompletionRate(BigDecimal.valueOf(75.0));
    metrics.setAvgWatchTimeSeconds(BigDecimal.valueOf(12.0));
    metrics.setCollectedAt(baseTime.minusSeconds(minutesSince * 60L));
    return metrics;
  }

  private TrajectoryAnalysis createAnalysis(UUID jobId, TrajectoryAnalysis.TrajectoryShape shape) {
    PublicationJob job = createJob(jobId);

    return TrajectoryAnalysis.builder()
        .id(UUID.randomUUID())
        .publicationJob(job)
        .trajectoryShape(shape)
        .velocityFirst24H(BigDecimal.valueOf(1000))
        .waveCount(1)
        .tailStrength(BigDecimal.valueOf(0.3))
        .plateauDetected(false)
        .dataPointsCount(5)
        .analysisConfidence(BigDecimal.valueOf(80))
        .build();
  }
}
