package com.pompomhills.intelligence.platformstate;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
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
class PlatformStateServicePublicationVariantTest {

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

  @Test
  void recordingTwoVariantsOnTheSamePlatformKeepsBothPublicationsIndependentlyRetrievable() {
    UUID videoId = insertVideo();
    UUID variantA = insertVariant(videoId);
    UUID variantB = insertVariant(videoId);

    var publicationA =
        service.recordPublication(
            videoId,
            new PlatformStateService.PublicationRequest(
                variantA, "instagram", "post-a", "https://instagram.com/p/a", Instant.now(),
                "UTC", false, "CSV", "variant A publication"),
            "test-user");
    var publicationB =
        service.recordPublication(
            videoId,
            new PlatformStateService.PublicationRequest(
                variantB, "instagram", "post-b", "https://instagram.com/p/b", Instant.now(),
                "UTC", false, "CSV", "variant B publication"),
            "test-user");

    // The read-path regression is only observable by re-reading variant A's publication
    // AFTER variant B's row has been inserted on the same video+platform. recordPublication()'s
    // own return value for A (captured above, before B exists) cannot expose the bug - at that
    // point A's row is the only / most recent one for video+platform either way. Calling
    // recordPublication() again for A with unchanged fields exercises the UPDATE branch (A's
    // row is `existing`) and then re-reads via publication(): under the pre-fix read path
    // (ORDER BY created_at DESC LIMIT 1, no variant filter), B's row is now the most recently
    // created video+platform row, so the stale read would incorrectly return "post-b" for A.
    var publicationARereadAfterB =
        service.recordPublication(
            videoId,
            new PlatformStateService.PublicationRequest(
                variantA, "instagram", "post-a", "https://instagram.com/p/a", Instant.now(),
                "UTC", false, "CSV", "variant A publication"),
            "test-user");

    assertThat(publicationA.platformContentId()).isEqualTo("post-a");
    assertThat(publicationB.platformContentId()).isEqualTo("post-b");
    assertThat(publicationARereadAfterB.platformContentId()).isEqualTo("post-a");
  }
}
