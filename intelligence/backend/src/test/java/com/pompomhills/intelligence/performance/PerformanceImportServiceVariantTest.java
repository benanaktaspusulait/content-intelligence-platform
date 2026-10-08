package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

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
class PerformanceImportServiceVariantTest {

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
  void correctedExportPreservesOriginalAndRequiresExactObservationIdentity() {
    UUID video = insertVideo("corrected-" + UUID.randomUUID() + ".mp4");
    String headers =
        "videoid,platformcontentid,publicationtimestamp,measurementtimestamp,metricsemantics,views,correction_of_id\n";
    String identity =
        video + ",18446744073709551615,2026-01-01T00:00:00Z,2026-01-04T00:00:00Z,CUMULATIVE,";
    var original =
        importService.preview(
            new MockMultipartFile(
                "file", "original.csv", "text/csv", (headers + identity + "100,\n").getBytes()),
            "instagram",
            "UTC");
    importService.commit(original.batchId());
    UUID old =
        jdbc.sql("SELECT id FROM performance_observations WHERE video_id=:id")
            .param("id", video)
            .query(UUID.class)
            .single();
    var corrected =
        importService.preview(
            new MockMultipartFile(
                "file",
                "corrected.csv",
                "text/csv",
                (headers + identity + "120," + old + "\n").getBytes()),
            "instagram",
            "UTC",
            original.batchId(),
            "Corrected source export");
    importService.commit(corrected.batchId());
    importService.commit(corrected.batchId());
    assertThat(importService.rows(original.batchId()).getFirst().observationId()).isEqualTo(old);
    assertThat(importService.rows(corrected.batchId()).getFirst().correctionOfObservationId())
        .isEqualTo(old);
    assertThat(importService.rows(corrected.batchId()).getFirst().correctionReason())
        .isEqualTo("Corrected source export");
    assertThat(importService.get(corrected.batchId()).correctionOfBatchId())
        .isEqualTo(original.batchId());
    assertThat(
            jdbc.sql("SELECT views FROM performance_observations WHERE id=:id")
                .param("id", old)
                .query(Long.class)
                .single())
        .isEqualTo(100);
    assertThat(
            jdbc.sql("SELECT views FROM effective_performance_observations WHERE video_id=:id")
                .param("id", video)
                .query(Long.class)
                .list())
        .containsExactly(120L);
    assertThat(
            jdbc.sql("SELECT count(*) FROM performance_observations WHERE video_id=:id")
                .param("id", video)
                .query(Long.class)
                .single())
        .isEqualTo(2);
    var bad =
        importService.preview(
            new MockMultipartFile(
                "file",
                "bad.csv",
                "text/csv",
                (headers
                        + identity.replace("18446744073709551615", "different-publication")
                        + "130,"
                        + old
                        + "\n")
                    .getBytes()),
            "instagram",
            "UTC",
            original.batchId(),
            "Incorrect identity fixture");
    assertThatThrownBy(() -> importService.commit(bad.batchId()))
        .isInstanceOf(IllegalArgumentException.class);
    assertThat(importService.get(bad.batchId()).status()).isEqualTo("PREVIEWED");
    assertThat(
            jdbc.sql("SELECT count(*) FROM performance_observations WHERE video_id=:id")
                .param("id", video)
                .query(Long.class)
                .single())
        .isEqualTo(2);
  }

  @Test
  void importRowWithAnExplicitVariantIdPersistsItOnTheObservation() throws IOException {
    UUID videoId = insertVideo("my-video.mp4");
    UUID variantId = insertVariant(videoId);
    String csv =
        "videoid,variantid,views,metricsemantics,measurementtimestamp\n"
            + videoId
            + ","
            + variantId
            + ",1000,CUMULATIVE,2026-01-01T00:00:00Z\n";
    var upload = new MockMultipartFile("file", "import.csv", "text/csv", csv.getBytes());

    var preview = importService.preview(upload, "instagram", "UTC");
    importService.commit(preview.batchId());

    UUID persistedVariant =
        jdbc.sql("SELECT variant_id FROM performance_observations WHERE video_id=:video")
            .param("video", videoId)
            .query(UUID.class)
            .optional()
            .orElse(null);
    assertThat(persistedVariant).isEqualTo(variantId);
  }

  @Test
  void importRowWithAVariantIdThatBelongsToADifferentVideoLeavesVariantNull() throws IOException {
    UUID videoId = insertVideo("another-video.mp4");
    UUID otherVideoId = insertVideo("unrelated-video.mp4");
    UUID variantOfOtherVideo = insertVariant(otherVideoId);
    String csv =
        "videoid,variantid,views,metricsemantics,measurementtimestamp\n"
            + videoId
            + ","
            + variantOfOtherVideo
            + ",1000,CUMULATIVE,2026-01-01T00:00:00Z\n";
    var upload = new MockMultipartFile("file", "import.csv", "text/csv", csv.getBytes());

    var preview = importService.preview(upload, "instagram", "UTC");
    importService.commit(preview.batchId());

    UUID persistedVariant =
        jdbc.sql("SELECT variant_id FROM performance_observations WHERE video_id=:video")
            .param("video", videoId)
            .query(UUID.class)
            .optional()
            .orElse(null);
    assertThat(persistedVariant).isNull();
  }

  @Test
  void importRowWithNoVariantIdLeavesVariantNull() throws IOException {
    UUID videoId = insertVideo("no-variant-video.mp4");
    String csv =
        "videoid,views,metricsemantics,measurementtimestamp\n"
            + videoId
            + ",1000,CUMULATIVE,2026-01-01T00:00:00Z\n";
    var upload = new MockMultipartFile("file", "import.csv", "text/csv", csv.getBytes());

    var preview = importService.preview(upload, "instagram", "UTC");
    importService.commit(preview.batchId());

    UUID persistedVariant =
        jdbc.sql("SELECT variant_id FROM performance_observations WHERE video_id=:video")
            .param("video", videoId)
            .query(UUID.class)
            .optional()
            .orElse(null);
    assertThat(persistedVariant).isNull();
  }

  @Test
  void manualMatchPersistsExactVariantAndClearsItWhenOriginalIsSelected() {
    UUID video = insertVideo("manual.mp4");
    UUID variant = insertVariant(video);
    String csv = "filename,views\nmissing-" + UUID.randomUUID() + ".mp4,100\n";
    var preview =
        importService.preview(
            new MockMultipartFile("file", "manual.csv", "text/csv", csv.getBytes()),
            "instagram",
            "UTC");
    UUID row = importService.rows(preview.batchId()).getFirst().id();
    importService.resolve(preview.batchId(), row, video, variant, "Verified edited publication");
    assertThat(importService.rows(preview.batchId()).getFirst().matchedVariantId())
        .isEqualTo(variant);
    importService.resolve(preview.batchId(), row, video, null, "Corrected to original publication");
    assertThat(importService.rows(preview.batchId()).getFirst().matchedVariantId()).isNull();
  }

  @Test
  void manualMatchRejectsCrossVideoVariantWithoutChangingTheRow() {
    UUID video = insertVideo("manual-target.mp4");
    UUID foreignVariant = insertVariant(insertVideo("foreign.mp4"));
    String csv = "filename,views\nmissing-" + UUID.randomUUID() + ".mp4,100\n";
    var preview =
        importService.preview(
            new MockMultipartFile("file", "manual.csv", "text/csv", csv.getBytes()),
            "instagram",
            "UTC");
    UUID row = importService.rows(preview.batchId()).getFirst().id();
    assertThatThrownBy(
            () ->
                importService.resolve(
                    preview.batchId(), row, video, foreignVariant, "Wrong selection"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThat(importService.rows(preview.batchId()).getFirst().matchedVideoId()).isNull();
  }

  @Test
  void duplicateBytesWithDifferentContextAreNotSilentlyReused() {
    String csv = "filename,views\nunknown-" + UUID.randomUUID() + ".mp4,100\n";
    var file = new MockMultipartFile("file", "context.csv", "text/csv", csv.getBytes());
    var first = importService.preview(file, "instagram", "UTC");
    assertThat(importService.preview(file, "instagram", "UTC").batchId())
        .isEqualTo(first.batchId());
    assertThatThrownBy(() -> importService.preview(file, "facebook", "UTC"))
        .isInstanceOf(IllegalStateException.class);
    assertThatThrownBy(() -> importService.preview(file, "instagram", "Europe/London"))
        .isInstanceOf(IllegalStateException.class);
  }
}
