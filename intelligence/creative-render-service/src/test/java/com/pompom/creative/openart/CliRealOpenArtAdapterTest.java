package com.pompom.creative.openart;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtImageRequest;
import com.pompom.creative.openart.dto.OpenArtJobResponse;
import com.pompom.creative.openart.dto.OpenArtJobStatus;
import com.pompom.creative.openart.dto.OpenArtVideoRequest;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CliRealOpenArtAdapterTest {

  @TempDir Path tempDir;

  private HttpServer downloadServer;
  private Path commandLog;
  private Path executable;
  private CliRealOpenArtAdapter adapter;

  @BeforeEach
  void setUp() throws IOException {
    commandLog = tempDir.resolve("commands.log");
    executable = tempDir.resolve("openart-fixture.sh");

    downloadServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    downloadServer.createContext(
        "/asset.mp4",
        exchange -> {
          byte[] body = "fixture-video".getBytes(StandardCharsets.UTF_8);
          exchange.sendResponseHeaders(200, body.length);
          try (var output = exchange.getResponseBody()) {
            output.write(body);
          }
        });
    downloadServer.start();
    Files.writeString(executable, fixtureScript(), StandardCharsets.UTF_8);
    executable.toFile().setExecutable(true);

    adapter = new CliRealOpenArtAdapter(executable.toString(), "", 5, true, new ObjectMapper());
  }

  @AfterEach
  void tearDown() {
    if (downloadServer != null) {
      downloadServer.stop(0);
    }
  }

  @Test
  void submitsWithThePublishedCliSyntaxAndDownloadsTheCreationResult() throws Exception {
    OpenArtJobResponse response =
        adapter.generateVideo(
            OpenArtVideoRequest.builder()
                .promptText("a paper boat drifting")
                .model("kling-3-omni")
                .firstFrameImageId("/tmp/first-frame.png")
                .durationSeconds(8)
                .aspectRatio("16:9")
                .resolution("480p")
                .build());

    assertThat(response.getJobId()).isEqualTo("history-123");
    assertThat(response.getStatus()).isEqualTo("QUEUED");
    assertThat(response.getEstimatedCredits()).isEqualByComparingTo("12.5");

    OpenArtJobStatus status = adapter.getJobStatus(response.getJobId());
    assertThat(status.getStatus()).isEqualTo("COMPLETE");
    assertThat(status.getProgressPercent()).isEqualTo(100);

    Path destination = tempDir.resolve("render-v1.mp4");
    DownloadResult result = adapter.downloadAsset(response.getJobId(), destination);

    assertThat(Files.readString(destination)).isEqualTo("fixture-video");
    assertThat(result.getAssetPath()).isEqualTo(destination.toString());
    assertThat(result.getFileSizeBytes()).isEqualTo(13L);

    List<String> commands = Files.readAllLines(commandLog);
    assertThat(commands).anyMatch(line -> line.contains("generate video a paper boat drifting"));
    assertThat(commands)
        .anyMatch(
            line ->
                line.contains("--model kling-3-omni")
                    && line.contains("--image /tmp/first-frame.png")
                    && line.contains("--duration 8")
                    && line.contains("--aspect-ratio 16:9")
                    && line.contains("--resolution 480p")
                    && line.contains("--async")
                    && line.contains("--json"));
    assertThat(commands).anyMatch(line -> line.contains("creation get history-123"));
    assertThat(commands).noneMatch(line -> line.contains("generate-video"));
    assertThat(commands).noneMatch(line -> line.contains(" download "));
  }

  @Test
  void imageSubmissionIncludesEveryCharacterReference() throws Exception {
    OpenArtJobResponse response =
        adapter.generateImage(
            OpenArtImageRequest.builder()
                .promptText("Kiko and Mimi in the room")
                .model("nano-banana-2")
                .referenceImagePaths(List.of("/tmp/kiko.png", "/tmp/mimi.png"))
                .build());

    assertThat(response.getJobId()).isEqualTo("history-123");
    List<String> commands = Files.readAllLines(commandLog);
    assertThat(commands)
        .anyMatch(
            line ->
                line.contains("--image /tmp/kiko.png") && line.contains("--image /tmp/mimi.png"));
  }

  @Test
  void readsCreditBalanceFromTheAccountCommand() {
    assertThat(adapter.getCreditBalance()).isEqualByComparingTo("875.25");
  }

  @Test
  void mapsFailedCreationStatesToTheAdapterContract() {
    OpenArtJobStatus status = adapter.getJobStatus("failed-job");

    assertThat(status.getStatus()).isEqualTo("FAILED");
    assertThat(status.getErrorMessage()).isEqualTo("provider rejected request");
    assertThat(status.getProgressPercent()).isEqualTo(0);
    assertThat(status.isFailed()).isTrue();
  }

  private String fixtureScript() {
    String downloadUrl = "http://127.0.0.1:" + downloadServer.getAddress().getPort() + "/asset.mp4";
    return """
        #!/bin/sh
        printf '%%s\\n' "$*" >> '%s'
        if [ "$1" = "version" ] || [ "$1" = "--version" ]; then
          printf 'openart 0.1.1\\n'
          exit 0
        fi
        if [ "$1" = "account" ]; then
          printf '{\"credits\":875.25}\\n'
          exit 0
        fi
        if [ "$1" = "model" ] && [ "$2" = "cost" ]; then
          printf '{\"totalCredits\":12.5}\\n'
          exit 0
        fi
        if [ "$1" = "generate" ]; then
          printf '{\"historyId\":\"history-123\",\"status\":\"pending\"}\\n'
          exit 0
        fi
        if [ "$1" = "creation" ] && [ "$2" = "get" ]; then
          if [ "$3" = "failed-job" ]; then
            printf '{\"historyId\":\"failed-job\",\"status\":\"failed\",\"failed_reason\":\"provider rejected request\"}\\n'
          else
            printf '{\"historyId\":\"history-123\",\"status\":\"completed\",\"url\":\"%s\"}\\n'
          fi
          exit 0
        fi
        printf 'unexpected command\\n' >&2
        exit 2
        """
        .formatted(commandLog, downloadUrl);
  }
}
