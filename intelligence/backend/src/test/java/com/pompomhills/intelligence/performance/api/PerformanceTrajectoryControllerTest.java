package com.pompomhills.intelligence.performance.api;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.performance.InterventionService;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class PerformanceTrajectoryControllerTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired InterventionService interventions;

  private PerformanceTrajectoryController controller() {
    return new PerformanceTrajectoryController(jdbc, interventions);
  }

  private UUID insertVideo() {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,'test.mp4',:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private void insertObservation(
      UUID videoId, Instant measuredAt, long views, String semantics, String source) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,platform,measurement_timestamp,metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,'instagram',:measured,:semantics,:views,:source)
            """)
        .param("video", videoId)
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("semantics", semantics)
        .param("views", views)
        .param("source", source)
        .update();
  }

  @Test
  void dailyIncrementObservationsProduceAPositiveCumulativeTrajectoryNotANegativeOne() {
    UUID videoId = insertVideo();
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    Instant t1 = Instant.parse("2026-01-02T00:00:00Z");
    insertObservation(videoId, t0, 1000L, "DAILY_INCREMENT", "CSV");
    insertObservation(videoId, t1, 300L, "DAILY_INCREMENT", "CSV");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.points()).hasSize(2);
    assertThat(view.points().get(0).views()).isEqualTo(1000L);
    assertThat(view.points().get(1).views()).isEqualTo(1300L);
    assertThat(view.points().get(1).deltaViews()).isEqualTo(300L);
    // Before this fix, this would have been -700.
  }

  @Test
  void mixedSourcesAreFlaggedAndReconciledToTheSourceWithMorePoints() {
    UUID videoId = insertVideo();
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    Instant t1 = Instant.parse("2026-01-02T00:00:00Z");
    Instant t2 = Instant.parse("2026-01-03T00:00:00Z");
    insertObservation(videoId, t0, 1000L, "CUMULATIVE", "CSV");
    insertObservation(videoId, t1, 1200L, "CUMULATIVE", "CSV");
    insertObservation(videoId, t2, 999999L, "SNAPSHOT", "API");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.sourcesPresent()).containsExactlyInAnyOrder("CSV", "API");
    assertThat(view.sourceReconciliationApplied()).isTrue();
    // CSV has 2 points, API has 1 - CSV wins, API's point is excluded from the series.
    assertThat(view.points()).hasSize(2);
    assertThat(view.points()).allSatisfy(p -> assertThat(p.views()).isLessThan(999999L));
  }

  @Test
  void singleSourceNeedsNoReconciliation() {
    UUID videoId = insertVideo();
    insertObservation(videoId, Instant.parse("2026-01-01T00:00:00Z"), 1000L, "CUMULATIVE", "CSV");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.sourcesPresent()).containsExactly("CSV");
    assertThat(view.sourceReconciliationApplied()).isFalse();
  }

  @Test
  void unknownSemanticsObservationsAreExcludedFromTheTrajectory() {
    UUID videoId = insertVideo();
    insertObservation(videoId, Instant.parse("2026-01-01T00:00:00Z"), 1000L, "CUMULATIVE", "CSV");
    insertObservation(videoId, Instant.parse("2026-01-02T00:00:00Z"), 50L, "UNKNOWN", "CSV");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.points()).hasSize(1);
  }
}
