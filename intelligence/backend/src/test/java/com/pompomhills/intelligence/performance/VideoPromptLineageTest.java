package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import com.pompomhills.intelligence.video.context.VideoCreativeContextService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import java.io.IOException;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;


@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoPromptLineageTest {
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
  @Autowired PerformanceImportService importService;

  protected UUID insertVideo(String filename) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,:name,:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("name", filename)
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }


  @Autowired VideoCreativeContextService contexts;

  @Test
  void folderVersionsStayAmbiguousUntilExactOperatorSelectionAndReconstructionNeverBecomesOriginal() {
    UUID video = insertVideo("source.mp4");
    String folder = "test";
    Long content = jdbc.sql("INSERT INTO contents(title,type,source_path) VALUES ('lineage','REEL',:path) RETURNING id")
        .param("path", folder + "/prompt-" + video + ".txt").query(Long.class).single();
    Long first = jdbc.sql("INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES (:content,1,'Original text') RETURNING id")
        .param("content", content).query(Long.class).single();
    jdbc.sql("INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES (:content,2,'Newer text')")
        .param("content", content).update();
    var ambiguous = contexts.get(video);
    assertThat(ambiguous.prompt()).isNull();
    assertThat(ambiguous.evidenceStatus()).isEqualTo("PROMPT_AMBIGUOUS");
    contexts.link(video, first, "ORIGINAL", "Operator checked original generation record");
    assertThat(contexts.get(video).prompt().promptVersionId()).isEqualTo(first);
    assertThat(contexts.get(video).prompt().rawText()).isEqualTo("Original text");
    contexts.link(video, first, "RECONSTRUCTED", "Candidate reconstructed from clip");
    assertThat(contexts.get(video).prompt()).isNull();
    assertThatThrownBy(() -> contexts.link(video, first, "ORIGINAL", " ")).isInstanceOf(IllegalArgumentException.class);
  }
}
