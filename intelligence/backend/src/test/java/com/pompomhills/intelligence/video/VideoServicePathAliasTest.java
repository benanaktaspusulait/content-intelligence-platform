package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.video.api.VideoDtos;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
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
class VideoServicePathAliasTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  private static Path dataRoot;

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) throws IOException {
    dataRoot = Files.createTempDirectory("pompom-path-alias-test");
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add("pompom.data-root", () -> dataRoot.toString());
  }

  @Autowired VideoService service;
  @Autowired VideoRepository videos;
  @Autowired VideoPathAliasRepository aliases;

  // VideoService.ingest() calls MlVideoClient.analyse(), a real HTTP client with no mock
  // configuration wired for @SpringBootTest in this module (confirmed: no existing test calls
  // ingest(), and pompom.ml-base-url has no test override). Replacing the bean with a Mockito
  // mock avoids a real network call while still exercising the real content-hash dedup logic,
  // since the stub returns the actual SHA-256 of the bytes written to disk below.
  @MockitoBean MlVideoClient ml;

  private Path original;
  private Path duplicate;

  @BeforeEach
  void setUp() throws IOException {
    byte[] bytes = "identical-fake-video-bytes-for-hash-matching".getBytes();
    original = dataRoot.resolve("original.mp4");
    duplicate = dataRoot.resolve("duplicate-copy.mp4");
    Files.write(original, bytes);
    Files.write(duplicate, bytes);

    String sha256 = sha256Hex(bytes);
    var metadata =
        new MlVideoClient.Metadata(15000L, 1080, 1920, 30.0, 0.5625, "h264", true, sha256);
    var response =
        new MlVideoClient.MlAnalysisResponse(
            "v1",
            metadata,
            "analysis-v1",
            "primary-engine",
            List.of(),
            "GOOD",
            0.5,
            0.9,
            "reason",
            "storyboard.json",
            List.of(),
            java.util.Map.of(),
            java.util.Map.of());
    when(ml.analyse(anyString())).thenReturn(response);
  }

  private static String sha256Hex(byte[] bytes) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(digest.digest(bytes));
    } catch (NoSuchAlgorithmException error) {
      throw new IllegalStateException(error);
    }
  }

  @AfterEach
  void tearDown() throws IOException {
    Files.deleteIfExists(original);
    Files.deleteIfExists(duplicate);
  }

  @Test
  void ingestingADuplicateContentHashRecordsAPathAliasInsteadOfDiscardingIt() {
    VideoDtos.VideoResponse first = service.ingest("original.mp4", null);

    VideoDtos.VideoResponse second = service.ingest("duplicate-copy.mp4", null);

    // The second ingest resolves to the SAME canonical video (same content hash), not a new row.
    assertThat(second.id()).isEqualTo(first.id());
    List<VideoPathAliasEntity> recorded = aliases.findAllByVideoId(first.id());
    assertThat(recorded).hasSize(1);
    assertThat(recorded.get(0).getRelativePath()).isEqualTo("duplicate-copy.mp4");
  }

  @Test
  void mediaFilesReportsAnAliasedPathAsIngestedWithTheCanonicalVideoId() {
    VideoDtos.VideoResponse first = service.ingest("original.mp4", null);
    service.ingest("duplicate-copy.mp4", null);

    List<VideoDtos.MediaFile> files = service.mediaFiles("", true);

    VideoDtos.MediaFile aliasedFile =
        files.stream().filter(file -> file.relativePath().equals("duplicate-copy.mp4")).findFirst().orElseThrow();
    assertThat(aliasedFile.ingested()).isTrue();
    assertThat(aliasedFile.videoId()).isEqualTo(first.id());
  }

  @Test
  void ingestingTheSamePathTwiceDoesNotCreateADuplicateAlias() {
    service.ingest("original.mp4", null);
    service.ingest("duplicate-copy.mp4", null);
    VideoDtos.VideoResponse first = videos.findByContentHash(
            videos.findAllByRelativePathIn(List.of("original.mp4")).get(0).getContentHash())
        .map(entity -> service.get(entity.getId()))
        .orElseThrow();

    service.ingest("duplicate-copy.mp4", null);

    assertThat(aliases.findAllByVideoId(first.id())).hasSize(1);
  }
}
