package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
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
class VideoServiceIngestAnalysisTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  private static Path dataRoot;

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) throws Exception {
    dataRoot = Files.createTempDirectory("pompom-ingest-analysis-test");
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add("pompom.data-root", () -> dataRoot.toString());
  }

  @Autowired private VideoService videoService;
  @Autowired private CreativeAnalysisRepository analyses;
  @MockitoBean private MlVideoClient ml;
  @Autowired private PompomProperties properties;

  @BeforeEach
  void setUp() throws Exception {
    Files.createDirectories(properties.dataRoot().resolve("library/IngestAnalysisTest"));
  }

  @Test
  void ingestPersistsTheFullCreativeAnalysisWithoutASecondMlCall() throws Exception {
    Path file = properties.dataRoot().resolve("library/IngestAnalysisTest/clip.mp4");
    Files.write(file, new byte[] {9, 9, 9});

    var metadata =
        new MlVideoClient.Metadata(15000L, 1080, 1920, 30.0, 0.5625, "h264", true, "hash-ingest-1");
    var response =
        new MlVideoClient.MlAnalysisResponse(
            "v1",
            metadata,
            "creative-v3",
            "engine-a",
            List.of(),
            "GOOD",
            0.82,
            0.9,
            "Clear hook and payoff",
            "library/IngestAnalysisTest/storyboard.png",
            List.of(Map.of("t", 0, "beat", "hook")),
            Map.of("featureA", 1.0),
            Map.of("raw", "evidence"));
    when(ml.analyse(any())).thenReturn(response);

    var ingested = videoService.ingest("library/IngestAnalysisTest/clip.mp4", null);

    assertThat(analyses.existsByVideoId(ingested.id())).isTrue();
    var persisted = analyses.findFirstByVideoIdOrderByCreatedAtDesc(ingested.id()).orElseThrow();
    assertThat(persisted.getAnalysisVersion()).isEqualTo("creative-v3");
    assertThat(persisted.getClassification()).isEqualTo("GOOD");
    assertThat(ingested.status()).isEqualTo("ANALYSED");

    org.mockito.Mockito.verify(ml, org.mockito.Mockito.times(1)).analyse(any());
  }
}
