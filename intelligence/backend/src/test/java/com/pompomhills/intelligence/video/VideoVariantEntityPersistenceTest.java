package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoVariantEntityPersistenceTest {

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

  @Autowired VideoRepository videos;
  @Autowired VideoVariantRepository variants;

  private VideoEntity insertVideo(String relativePath) {
    return videos.save(
        new VideoEntity(
            UUID.randomUUID(),
            UUID.randomUUID().toString(),
            "test.mp4",
            relativePath,
            15000,
            1080,
            1920,
            30.0,
            0.5625,
            "h264",
            true,
            null,
            Instant.now()));
  }

  @Test
  void persistsAndReadsBackAVariantWithNoParent() {
    VideoEntity video = insertVideo("library/a.mp4");
    VideoVariantEntity variant =
        new VideoVariantEntity(
            video, null, VideoVariantType.ORIGINAL, "library/variants/a-original.mp4", List.of());

    VideoVariantEntity saved = variants.save(variant);

    VideoVariantEntity reloaded = variants.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getVideo().getId()).isEqualTo(video.getId());
    assertThat(reloaded.getParentVariant()).isNull();
    assertThat(reloaded.getVariantType()).isEqualTo(VideoVariantType.ORIGINAL);
    assertThat(reloaded.getGeneratedPath()).isEqualTo("library/variants/a-original.mp4");
    assertThat(reloaded.getCreatedAt()).isNotNull();
  }

  @Test
  void persistsAVariantWithAParentVariant() {
    VideoEntity video = insertVideo("library/b.mp4");
    VideoVariantEntity original =
        variants.save(
            new VideoVariantEntity(
                video, null, VideoVariantType.ORIGINAL, "library/variants/b-original.mp4", List.of()));
    VideoVariantEntity hook =
        new VideoVariantEntity(
            video, original, VideoVariantType.HOOK_COLD_OPEN, "library/variants/b-hook.mp4", List.of());

    VideoVariantEntity saved = variants.save(hook);

    VideoVariantEntity reloaded = variants.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getParentVariant().getId()).isEqualTo(original.getId());
  }

  @Test
  void rejectsADuplicateGeneratedPathAtTheDatabase() {
    VideoEntity video = insertVideo("library/c.mp4");
    variants.saveAndFlush(
        new VideoVariantEntity(
            video, null, VideoVariantType.ORIGINAL, "library/variants/shared-path.mp4", List.of()));
    VideoVariantEntity duplicate =
        new VideoVariantEntity(
            video, null, VideoVariantType.TRIMMED, "library/variants/shared-path.mp4", List.of());

    assertThatThrownBy(() -> variants.saveAndFlush(duplicate))
        .isInstanceOf(DataIntegrityViolationException.class);
  }

  @Test
  void persistsNonEmptyEditOperations() {
    VideoEntity video = insertVideo("library/d.mp4");
    VideoVariantEntity variant =
        new VideoVariantEntity(
            video,
            null,
            VideoVariantType.CUSTOM_EDIT,
            "library/variants/d-custom.mp4",
            List.of(java.util.Map.of("op", "trim", "startMs", 0, "endMs", 15000)));

    VideoVariantEntity saved = variants.saveAndFlush(variant);

    VideoVariantEntity reloaded = variants.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getEditOperations()).hasSize(1);
  }
}
