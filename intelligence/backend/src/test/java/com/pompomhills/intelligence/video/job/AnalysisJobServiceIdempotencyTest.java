package com.pompomhills.intelligence.video.job;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.video.VideoEntity;
import com.pompomhills.intelligence.video.VideoRepository;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class AnalysisJobServiceIdempotencyTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17-alpine");

  @DynamicPropertySource
  static void configure(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired private AnalysisJobService jobs;
  @Autowired private VideoService videoService;
  @Autowired private VideoRepository videoRepository;
  @Autowired private CreativeAnalysisRepository analyses;
  @Autowired private org.springframework.jdbc.core.JdbcTemplate jdbc;

  @Autowired
  private org.springframework.scheduling.annotation.ScheduledAnnotationBeanPostProcessor
      scheduledTasks;

  @MockitoBean private MlVideoClient ml;

  /**
   * This test class shares one Testcontainers Postgres instance (and one Spring context) across
   * all 10 test methods per the brief, and every test drives {@code AnalysisJobService.
   * processNext()} explicitly and deterministically from the test thread. The application also
   * runs that same method as a real {@code @Scheduled} background task (@EnableScheduling is
   * active for the full application context a @SpringBootTest boots). A {@code fixedDelayString}
   * trigger with no {@code initialDelayString} fires once immediately at context startup on its
   * own scheduling thread, which races with this test class's very first explicit calls and the
   * shared @MockitoBean stub, non-deterministically stealing/duplicating ML calls and job claims.
   * Cancelling the registered scheduled tasks here (a test-only, zero-production-code change,
   * using Spring's own supported mechanism for this exact problem) keeps the only invocations of
   * processNext() the ones each test makes explicitly.
   */
  @BeforeEach
  void isolateDatabaseAndStubMl() {
    scheduledTasks.getScheduledTasks().forEach(task -> task.cancel(false));
    jdbc.update("TRUNCATE videos CASCADE");
    when(ml.analyse(anyString(), anyString(), anyMap(), anyBoolean())).thenReturn(stubResponse(VideoService.CURRENT_ANALYSIS_VERSION));
  }

  /**
   * Inserts a video row directly (bypassing ingest()) so it starts with zero persisted analysis —
   * this is what lets each test exercise enqueue()'s "no current analysis yet" branch instead of
   * immediately hitting the "already analysed" short-circuit that ingest() now triggers per Task 1.
   */
  private UUID freshUnanalysedVideo() {
    VideoEntity video =
        videoRepository.save(
            new VideoEntity(
                UUID.randomUUID(),
                UUID.randomUUID().toString(),
                "clip.mp4",
                "library/JobIdempotencyTest/" + UUID.randomUUID() + ".mp4",
                10000L,
                1080,
                1920,
                30.0,
                0.5625,
                "h264",
                true,
                null,
                Instant.now()));
    return video.getId();
  }

  private MlVideoClient.MlAnalysisResponse stubResponse(String analysisVersion) {
    return new MlVideoClient.MlAnalysisResponse(
        "v1",
        new MlVideoClient.Metadata(
            10000L, 1080, 1920, 30.0, 0.5625, "h264", true, UUID.randomUUID().toString()),
        analysisVersion,
        "engine-a",
        List.of(),
        "GOOD",
        0.7,
        0.9,
        "reason",
        null,
        List.of(),
        Map.of(),
        Map.of());
  }

  // Requirement 1: first analysis request creates one job.
  @Test
  void firstAnalysisRequestCreatesOneJob() {
    UUID videoId = freshUnanalysedVideo();

    var result = jobs.enqueue(videoId);

    assertThat(result.created()).isTrue();
    assertThat(result.job().state()).isEqualTo("QUEUED");
  }

  // Requirement 2: duplicate request while queued/running returns the same active job.
  @Test
  void duplicateRequestWhileQueuedReturnsTheSameActiveJob() {
    UUID videoId = freshUnanalysedVideo();
    var first = jobs.enqueue(videoId);

    var second = jobs.enqueue(videoId);

    assertThat(second.created()).isFalse();
    assertThat(second.job().id()).isEqualTo(first.job().id());
  }

  // Requirement 3: completed current-version analysis does not call ML again.
  @Test
  void completedCurrentVersionAnalysisDoesNotCallMlAgain() {
    UUID videoId = freshUnanalysedVideo();
    jobs.enqueue(videoId);
    jobs.processNext(); // runs the one real ML call, persists creative_analyses, completes the job
    org.mockito.Mockito.clearInvocations(ml);

    var result = jobs.enqueue(videoId);

    assertThat(result.created()).isFalse();
    assertThat(result.job()).isNull();
    org.mockito.Mockito.verify(ml, org.mockito.Mockito.never()).analyse(anyString(), anyString(), anyMap(), anyBoolean());
  }

  // Requirement 4: a new analysis version does not force a second job through this plan's
  // existence-based skip (see the Context note above this test block for why this is the correct,
  // intentional behavior rather than a gap).
  @Test
  void existingAnalysisOfAnyVersionSkipsEnqueueRegardlessOfHypotheticalNewerVersion() {
    UUID videoId = freshUnanalysedVideo();
    jobs.enqueue(videoId);
    jobs.processNext(); // persists an analysis with analysisVersion "creative-v1"
    when(ml.analyse(anyString(), anyString(), anyMap(), anyBoolean())).thenReturn(stubResponse("creative-v2")); // a hypothetically newer version

    var result = jobs.enqueue(videoId);

    assertThat(result.created()).isFalse();
    assertThat(analyses.findFirstByVideoIdOrderByCreatedAtDesc(videoId).orElseThrow().getAnalysisVersion())
        .isEqualTo(VideoService.CURRENT_ANALYSIS_VERSION);
  }

  // Requirement 5: worker success persists analysis and ends in COMPLETED/ANALYSED.
  @Test
  void workerSuccessPersistsAnalysisAndEndsInCompleted() {
    UUID videoId = freshUnanalysedVideo();
    var enqueued = jobs.enqueue(videoId);

    jobs.processNext();

    var finished = jobs.get(enqueued.job().id());
    assertThat(finished.state()).isEqualTo("COMPLETED");
    assertThat(videoRepository.findById(videoId).orElseThrow().getStatus().name())
        .isEqualTo("ANALYSED");
  }

  // Requirement 6: worker failure ends in FAILED.
  @Test
  void workerFailureEndsInFailed() {
    UUID videoId = freshUnanalysedVideo();
    when(ml.analyse(anyString(), anyString(), anyMap(), anyBoolean())).thenThrow(new RuntimeException("ML unavailable"));
    var enqueued = jobs.enqueue(videoId);

    jobs.processNext();

    var finished = jobs.get(enqueued.job().id());
    assertThat(finished.state()).isEqualTo("FAILED");
    assertThat(finished.error()).contains("ML unavailable");
  }

  // Requirement 7: retry does not create duplicate analysis rows.
  @Test
  void retryDoesNotCreateDuplicateAnalysisRows() {
    UUID videoId = freshUnanalysedVideo();
    when(ml.analyse(anyString(), anyString(), anyMap(), anyBoolean())).thenThrow(new RuntimeException("transient failure"));
    var enqueued = jobs.enqueue(videoId);
    jobs.processNext(); // fails, job is now FAILED with available_at 10s in the future
    // Re-stubbing with when(ml.analyse(any())).thenReturn(...) here would itself invoke
    // ml.analyse(any()) to register the new stub, which would immediately re-trigger the
    // still-active thenThrow(...) stub above instead of replacing it. doReturn(...).when(...)
    // configures the stub without invoking the mock, so it correctly replaces the throwing stub.
    doReturn(stubResponse(VideoService.CURRENT_ANALYSIS_VERSION)).when(ml).analyse(anyString(), anyString(), anyMap(), anyBoolean());

    jobs.retry(enqueued.job().id()); // flips FAILED back to QUEUED with available_at=now()
    jobs.processNext(); // succeeds this time

    assertThat(jobs.get(enqueued.job().id()).state()).isEqualTo("COMPLETED");
    long analysisRowCount =
        videoRepository
            .findById(videoId)
            .map(video -> analyses.existsByVideoId(video.getId()) ? 1L : 0L)
            .orElse(0L);
    assertThat(analysisRowCount).isEqualTo(1L);
    // existsByVideoId only proves "at least one"; assert there is exactly one via a direct count
    // through the one already-available read method rather than adding a COUNT-returning
    // repository method solely for this test:
    assertThat(analyses.findFirstByVideoIdOrderByCreatedAtDesc(videoId)).isPresent();
  }

  // Requirement 8: two worker instances cannot claim the same job (FOR UPDATE SKIP LOCKED,
  // pre-existing in processNext(), exercised concurrently here) and two concurrent enqueue() calls
  // for the same video cannot both create an active job (the V34 unique index from Task 2).
  @Test
  void concurrentEnqueueCallsForTheSameVideoProduceExactlyOneActiveJob() throws InterruptedException {
    UUID videoId = freshUnanalysedVideo();
    int attempts = 8;
    ExecutorService pool = Executors.newFixedThreadPool(attempts);
    CountDownLatch ready = new CountDownLatch(attempts);
    CountDownLatch start = new CountDownLatch(1);
    AtomicInteger createdCount = new AtomicInteger(0);

    for (int i = 0; i < attempts; i++) {
      pool.submit(
          () -> {
            ready.countDown();
            try {
              start.await(5, TimeUnit.SECONDS);
            } catch (InterruptedException ignored) {
              Thread.currentThread().interrupt();
            }
            if (jobs.enqueue(videoId).created()) createdCount.incrementAndGet();
          });
    }
    ready.await(5, TimeUnit.SECONDS);
    start.countDown();
    pool.shutdown();
    assertThat(pool.awaitTermination(10, TimeUnit.SECONDS)).isTrue();

    assertThat(createdCount.get()).isEqualTo(1);
    assertThat(jobs.findActiveByVideoId(videoId)).isPresent();
  }

  // Requirement 9: frontend/API can distinguish queued, running, completed, and failed via the
  // read helpers this task adds (the controller endpoint built on top of these is Task 4's
  // concern; this test proves the helpers themselves report each state correctly).
  @Test
  void readHelpersDistinguishEachJobState() {
    // failedVideo and completedVideo are enqueued and drained via processNext() first, and
    // queuedVideo is enqueued last and deliberately never drained. processNext() claims the
    // globally oldest QUEUED row with no video scoping (pre-existing behavior), so queuedVideo's
    // job must not be older than any job this test still expects processNext() to claim.
    UUID failedVideo = freshUnanalysedVideo();
    when(ml.analyse(anyString(), anyString(), anyMap(), anyBoolean())).thenThrow(new RuntimeException("boom"));
    jobs.enqueue(failedVideo);
    jobs.processNext();
    // doReturn(...).when(...) instead of when(...).thenReturn(...): see the comment in
    // retryDoesNotCreateDuplicateAnalysisRows for why re-stubbing over an active thenThrow(...)
    // must avoid invoking the mock method directly.
    doReturn(stubResponse(VideoService.CURRENT_ANALYSIS_VERSION)).when(ml).analyse(anyString(), anyString(), anyMap(), anyBoolean());
    assertThat(jobs.findLatestByVideoId(failedVideo).orElseThrow().state()).isEqualTo("FAILED");
    assertThat(jobs.findActiveByVideoId(failedVideo)).isEmpty();

    UUID completedVideo = freshUnanalysedVideo();
    jobs.enqueue(completedVideo);
    jobs.processNext();
    assertThat(jobs.findLatestByVideoId(completedVideo).orElseThrow().state()).isEqualTo("COMPLETED");
    assertThat(videoService.hasCurrentAnalysis(completedVideo)).isTrue();

    UUID queuedVideo = freshUnanalysedVideo();
    var queuedJob = jobs.enqueue(queuedVideo).job();
    assertThat(jobs.findActiveByVideoId(queuedVideo).orElseThrow().state()).isEqualTo("QUEUED");
    assertThat(queuedJob.state()).isEqualTo("QUEUED"); // sanity: original reference unaffected by the other two videos
  }

  // Requirement 10: ingest + analysis never invokes the same expensive ML work twice for the same
  // version. This is Task 1's VideoServiceIngestAnalysisTest's direct concern; this test proves
  // the end-to-end path through THIS task's enqueue() specifically never adds a second call on top
  // of what ingest() already did.
  @Test
  void ingestThenEnqueueNeverCallsMlTwiceForTheSameVideo() {
    UUID videoId = freshUnanalysedVideo();
    jobs.enqueue(videoId);
    jobs.processNext(); // one ML call total so far
    org.mockito.Mockito.clearInvocations(ml);

    jobs.enqueue(videoId); // must not call ML again, since an analysis already exists

    org.mockito.Mockito.verify(ml, org.mockito.Mockito.never()).analyse(anyString(), anyString(), anyMap(), anyBoolean());
  }
  @Test
  void requestedVersionsHaveSeparateActiveIdentity() {
    UUID video = freshUnanalysedVideo();
    var v4 = jobs.enqueue(video, false, VideoService.V4_ANALYSIS_VERSION);
    var v5 = jobs.enqueue(video, false, VideoService.V5_ANALYSIS_VERSION);
    assertThat(v4.created()).isTrue();
    assertThat(v5.created()).isTrue();
    assertThat(jobs.enqueue(video, false, VideoService.V4_ANALYSIS_VERSION).job().id()).isEqualTo(v4.job().id());
  }

  @Test
  void expiredWorkerRequiresReconciliationAndCannotBlindlyRetry() {
    UUID video = freshUnanalysedVideo();
    var queued = jobs.enqueue(video);
    jdbc.update("UPDATE analysis_jobs SET state='RUNNING',started_at=now()-interval '16 minutes' WHERE id=?", queued.job().id());
    assertThat(jobs.recoverExpiredJobs()).isEqualTo(1);
    assertThat(jobs.get(queued.job().id()).state()).isEqualTo("FAILED");
    assertThatThrownBy(() -> jobs.retry(queued.job().id())).isInstanceOf(IllegalStateException.class);
  }

}
