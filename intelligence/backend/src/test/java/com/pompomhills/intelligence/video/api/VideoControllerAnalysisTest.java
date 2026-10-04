package com.pompomhills.intelligence.video.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.video.VideoEntity;
import com.pompomhills.intelligence.video.VideoRepository;
import com.pompomhills.intelligence.video.job.AnalysisJobService;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient
@Testcontainers(disabledWithoutDocker = true)
class VideoControllerAnalysisTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17-alpine");

  @DynamicPropertySource
  static void configure(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired private RestTestClient rest;
  @Autowired private VideoRepository videoRepository;
  @Autowired private AnalysisJobService analysisJobService;
  @Autowired private org.springframework.jdbc.core.JdbcTemplate jdbc;

  @Autowired
  private org.springframework.scheduling.annotation.ScheduledAnnotationBeanPostProcessor
      scheduledTasks;

  @MockitoBean private MlVideoClient ml;

  /**
   * Test isolation fix carried forward from Task 3's AnalysisJobServiceIdempotencyTest: this class
   * shares one Testcontainers Postgres instance and Spring context across all its test methods, and
   * analysisJobService.processNext() claims the globally-oldest QUEUED row with no per-video
   * scoping. Without cancelling the @Scheduled poller (which fires once immediately at context
   * startup regardless of its configured fixedDelayString) and truncating videos between tests,
   * tests here would non-deterministically steal each other's jobs/ML stub invocations.
   */
  @BeforeEach
  void isolateDatabaseAndStubMl() {
    scheduledTasks.getScheduledTasks().forEach(task -> task.cancel(false));
    jdbc.update("TRUNCATE videos CASCADE");
    when(ml.analyse(any())).thenReturn(stubResponse());
  }

  @Test
  void firstAnalysisRequestReturns202WithAQueuedJob() {
    var video = freshUnanalysedVideo();

    var response =
        rest.post()
            .uri("/api/v1/videos/" + video.getId() + "/analysis")
            .exchange()
            .returnResult(VideoDtos.AnalysisStatusResponse.class);

    assertThat(response.getStatus()).isEqualTo(HttpStatus.ACCEPTED);
    assertThat(response.getResponseBody().jobState()).isEqualTo("QUEUED");
    assertThat(response.getResponseBody().hasCompletedAnalysis()).isFalse();
  }

  @Test
  void statusEndpointReflectsCurrentState() {
    var video = freshUnanalysedVideo();
    var status =
        rest.get()
            .uri("/api/v1/videos/" + video.getId() + "/analysis/status")
            .exchange()
            .returnResult(VideoDtos.AnalysisStatusResponse.class)
            .getResponseBody();
    assertThat(status.jobState()).isEqualTo("NOT_STARTED");
  }

  @Test
  void duplicateAnalysisRequestWhileActiveReturns202WithTheSameJob() {
    var video = freshUnanalysedVideo();
    var first =
        rest.post()
            .uri("/api/v1/videos/" + video.getId() + "/analysis")
            .exchange()
            .returnResult(VideoDtos.AnalysisStatusResponse.class);

    var second =
        rest.post()
            .uri("/api/v1/videos/" + video.getId() + "/analysis")
            .exchange()
            .returnResult(VideoDtos.AnalysisStatusResponse.class);

    assertThat(second.getStatus()).isEqualTo(HttpStatus.ACCEPTED);
    assertThat(second.getResponseBody().jobId()).isEqualTo(first.getResponseBody().jobId());
    assertThat(second.getResponseBody().hasCompletedAnalysis()).isFalse();
  }

  @Test
  void analysisRequestAfterCompletionReturns200WithTheExistingResult() {
    var video = freshUnanalysedVideo();
    rest.post()
        .uri("/api/v1/videos/" + video.getId() + "/analysis")
        .exchange()
        .returnResult(VideoDtos.AnalysisStatusResponse.class);
    // Drive the job to completion the same way the real worker would, by invoking the service
    // directly rather than waiting on the @Scheduled poller's real-world 2s delay in a test.
    analysisJobService.processNext();

    var response =
        rest.post()
            .uri("/api/v1/videos/" + video.getId() + "/analysis")
            .exchange()
            .returnResult(VideoDtos.AnalysisStatusResponse.class);

    assertThat(response.getStatus()).isEqualTo(HttpStatus.OK);
    assertThat(response.getResponseBody().hasCompletedAnalysis()).isTrue();
    assertThat(response.getResponseBody().classification()).isEqualTo("GOOD");
  }

  private VideoEntity freshUnanalysedVideo() {
    return videoRepository.save(
        new VideoEntity(
            UUID.randomUUID(),
            UUID.randomUUID().toString(),
            "clip.mp4",
            "library/ControllerAnalysisTest/" + UUID.randomUUID() + ".mp4",
            10000L,
            1080,
            1920,
            30.0,
            0.5625,
            "h264",
            true,
            null,
            java.time.Instant.now()));
  }

  private MlVideoClient.MlAnalysisResponse stubResponse() {
    return new MlVideoClient.MlAnalysisResponse(
        "v1",
        new MlVideoClient.Metadata(10000L, 1080, 1920, 30.0, 0.5625, "h264", true, "h"),
        "creative-v1",
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
}
