package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.video.api.VideoDtos.MediaFile;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoServiceMediaFilesVariantTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  private static Path dataRoot;

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) throws IOException {
    dataRoot = Files.createTempDirectory("pompom-media-files-variant-test");
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add("pompom.data-root", () -> dataRoot.toString());
  }

  @Autowired private VideoService videoService;
  @Autowired private VideoRepository videos;
  @Autowired private VideoVariantRepository variants;

  @Test
  void mediaFilesResolvesVariantIdWhenGeneratedPathMatchesAFile() throws Exception {
    Files.createDirectories(dataRoot.resolve("VariantMediaFileTest"));
    Path original = dataRoot.resolve("VariantMediaFileTest/original.mp4");
    Path hookCut = dataRoot.resolve("VariantMediaFileTest/hook_cut.mp4");
    Files.write(original, new byte[] {1, 2, 3});
    Files.write(hookCut, new byte[] {4, 5, 6});

    VideoEntity video =
        videos.save(
            new VideoEntity(
                UUID.randomUUID(),
                UUID.randomUUID().toString(),
                "original.mp4",
                "VariantMediaFileTest/original.mp4",
                1000L,
                1080,
                1920,
                30.0,
                0.5625,
                "h264",
                true,
                null,
                Instant.now()));
    VideoVariantEntity variant =
        variants.save(
            new VideoVariantEntity(
                video,
                null,
                VideoVariantType.HOOK_COLD_OPEN,
                "VariantMediaFileTest/hook_cut.mp4",
                List.of()));

    List<MediaFile> files = videoService.mediaFiles("VariantMediaFileTest", false);

    MediaFile hookFile =
        files.stream().filter(file -> file.name().equals("hook_cut.mp4")).findFirst().orElseThrow();
    assertThat(hookFile.variantId()).isEqualTo(variant.getId());

    MediaFile originalFile =
        files.stream().filter(file -> file.name().equals("original.mp4")).findFirst().orElseThrow();
    assertThat(originalFile.variantId()).isNull();
  }
}
