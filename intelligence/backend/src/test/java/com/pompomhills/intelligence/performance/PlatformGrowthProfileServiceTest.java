package com.pompomhills.intelligence.performance;

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
class PlatformGrowthProfileServiceTest {

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
  @Autowired PlatformGrowthProfileService service;

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
      UUID videoId,
      Instant publishedAt,
      Instant measuredAt,
      long views,
      String semantics,
      String source) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,platform,publication_timestamp,measurement_timestamp,
               metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,'instagram',:published,:measured,:semantics,:views,:source)
            """)
        .param("video", videoId)
        .param("published", OffsetDateTime.ofInstant(publishedAt, ZoneOffset.UTC))
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("semantics", semantics)
        .param("views", views)
        .param("source", source)
        .update();
  }

  @Test
  void checkpointWithinToleranceOfTargetHorizonIsMarkedWithinTolerance() {
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    // 23h50m after publish - within a reasonable tolerance of the 24h target.
    insertObservation(
        videoId, published, published.plusSeconds(23 * 3600L + 50 * 60L), 5000L, "CUMULATIVE", "CSV");

    var profile = service.profile(videoId, "instagram", Instant.now());

    assertThat(profile.views24h()).isNotNull();
    assertThat(profile.views24h().withinTolerance()).isTrue();
  }

  @Test
  void checkpointFarOutsideToleranceOfTargetHorizonIsMarkedNotWithinTolerance() {
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    // Only a 1h observation exists; the audit's exact failure case for the "24h" label.
    insertObservation(videoId, published, published.plusSeconds(3600L), 100L, "CUMULATIVE", "CSV");

    var profile = service.profile(videoId, "instagram", Instant.now());

    assertThat(profile.views24h()).isNotNull();
    assertThat(profile.views24h().withinTolerance()).isFalse();
    // The real measurement time is still exposed, so a caller can show "closest available: 1h".
    assertThat(profile.views24h().measuredAt()).isEqualTo(published.plusSeconds(3600L));
  }

  @Test
  void dailyIncrementObservationsAreAccumulatedBeforeComputingCheckpoints() {
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, published, published, 1000L, "DAILY_INCREMENT", "CSV");
    insertObservation(
        videoId, published, published.plusSeconds(6 * 3600L), 500L, "DAILY_INCREMENT", "CSV");

    var profile = service.profile(videoId, "instagram", Instant.now());

    assertThat(profile.views6h().views()).isEqualTo(1500L);
  }
}
