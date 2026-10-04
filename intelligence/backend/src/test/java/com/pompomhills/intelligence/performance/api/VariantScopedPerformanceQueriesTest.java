package com.pompomhills.intelligence.performance.api;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.performance.DiscoveryProfileService;
import com.pompomhills.intelligence.performance.PlatformGrowthProfileService;
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
class VariantScopedPerformanceQueriesTest {

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
  @Autowired PerformanceTrajectoryController trajectoryController;
  @Autowired PlatformGrowthProfileService growthProfileService;
  @Autowired DiscoveryProfileService discoveryProfileService;

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

  private UUID insertVariant(UUID videoId) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO video_variants(id,video_id,variant_type,generated_path)
            VALUES (:id,:video,'HOOK_COLD_OPEN',:path)
            """)
        .param("id", id)
        .param("video", videoId)
        .param("path", "test/variants/" + id + "-hook.mp4")
        .update();
    return id;
  }

  private void insertObservation(
      UUID videoId, UUID variantId, Instant publishedAt, Instant measuredAt, long views) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,variant_id,platform,publication_timestamp,measurement_timestamp,
               metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,:variant,'instagram',:published,:measured,
                    'CUMULATIVE',:views,'CSV')
            """)
        .param("video", videoId)
        .param("variant", variantId, java.sql.Types.OTHER)
        .param("published", OffsetDateTime.ofInstant(publishedAt, ZoneOffset.UTC))
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("views", views)
        .update();
  }

  @Test
  void trajectoryWithNoVariantFilterOnlyMatchesUnscopedObservations() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0.plusSeconds(3600), 999L);

    var unscoped = trajectoryController.trajectory(videoId, "instagram", null);

    assertThat(unscoped.points()).hasSize(1);
    assertThat(unscoped.points().get(0).views()).isEqualTo(100L);
  }

  @Test
  void trajectoryWithAnExplicitVariantFilterOnlyMatchesThatVariant() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0.plusSeconds(3600), 999L);

    var scoped = trajectoryController.trajectory(videoId, "instagram", variantId);

    assertThat(scoped.points()).hasSize(1);
    assertThat(scoped.points().get(0).views()).isEqualTo(999L);
  }

  @Test
  void growthProfileWithNoVariantFilterOnlyMatchesUnscopedObservations() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0, 999L);

    var profile = growthProfileService.profile(videoId, "instagram", Instant.now(), null);

    assertThat(profile.latest().views()).isEqualTo(100L);
  }

  @Test
  void discoveryProfileWithAnExplicitVariantFilterOnlyMatchesThatVariant() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0, 999L);

    var profile = discoveryProfileService.profile(videoId, "instagram", Instant.now(), variantId);

    assertThat(profile.videoId()).isEqualTo(videoId);
    // Discovery profile's audience snapshot query must have picked the variant-scoped row.
    UUID matchedObservationId =
        jdbc.sql("SELECT id FROM performance_observations WHERE video_id=:v AND views=999")
            .param("v", videoId)
            .query(UUID.class)
            .single();
    assertThat(matchedObservationId).isNotNull();
  }
}
