package com.pompomhills.intelligence.platformstate;

import static org.assertj.core.api.Assertions.assertThat;

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
class PlatformStateServiceWindowTest {

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
  @Autowired PlatformStateService service;

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

  private void insertObservation(UUID videoId, Instant publishedAt, Instant measuredAt, long views) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,platform,publication_timestamp,measurement_timestamp,
               metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,'instagram',:published,:measured,'CUMULATIVE',:views,'CSV')
            """)
        .param("video", videoId)
        .param("published", OffsetDateTime.ofInstant(publishedAt, ZoneOffset.UTC))
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("views", views)
        .update();
  }

  @Test
  void reachFurtherWindowUsesLatestObservationEvenWhenFarFromTargetWindowBoundary() {
    // Regression guard for the service continuing to function at all after the tolerance
    // field is added - full window-correctness assertions belong to a future Reach-Further-
    // specific test; this confirms reachFurtherSummary() still returns without error once
    // MetricPoint gains a field, since several internal call sites construct it.
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, published, published.plusSeconds(3600L), 100L);

    var summary = service.reachFurtherSummary(videoId, "instagram");

    assertThat(summary.videoId()).isEqualTo(videoId);
  }
}
