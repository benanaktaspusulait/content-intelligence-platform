package com.pompom.creative.openart;

import com.pompom.creative.openart.dto.*;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class CliMockOpenArtAdapter implements OpenArtAdapter {

  private final Path workDir;
  private final Map<String, String> jobStatuses = new HashMap<>();
  private BigDecimal creditBalance = BigDecimal.valueOf(100.0);

  public CliMockOpenArtAdapter(Path workDir) {
    this.workDir = workDir;
  }

  @Override
  public OpenArtJobResponse generateImage(OpenArtImageRequest request) {
    String jobId = "mock-img-" + UUID.randomUUID().toString();
    jobStatuses.put(jobId, "COMPLETE"); // Mock completes immediately

    log.info("Mock: Generated image job {} for prompt: {}", jobId, request.getPromptText());

    return OpenArtJobResponse.builder()
        .jobId(jobId)
        .status("QUEUED")
        .estimatedCredits(BigDecimal.valueOf(2.5))
        .build();
  }

  @Override
  public OpenArtJobResponse generateVideo(OpenArtVideoRequest request) {
    String jobId = "mock-vid-" + UUID.randomUUID().toString();
    jobStatuses.put(jobId, "COMPLETE"); // Mock completes immediately

    log.info("Mock: Generated video job {} for prompt: {}", jobId, request.getPromptText());

    return OpenArtJobResponse.builder()
        .jobId(jobId)
        .status("QUEUED")
        .estimatedCredits(BigDecimal.valueOf(15.0))
        .build();
  }

  @Override
  public OpenArtJobStatus getJobStatus(String jobId) {
    String status = jobStatuses.getOrDefault(jobId, "UNKNOWN");

    return OpenArtJobStatus.builder()
        .jobId(jobId)
        .status(status)
        .progressPercent(status.equals("COMPLETE") ? 100 : 50)
        .build();
  }

  @Override
  public DownloadResult downloadAsset(String jobId, Path destination) {
    try {
      // Create mock file (1x1 pixel PNG for images, empty MP4 for videos)
      byte[] mockData =
          jobId.startsWith("mock-img-") ? createMockImageBytes() : createMockVideoBytes();

      Files.createDirectories(destination.getParent());
      Files.write(destination, mockData);

      log.info("Mock: Downloaded asset {} to {}", jobId, destination);

      boolean isImage = jobId.startsWith("mock-img-");
      return DownloadResult.builder()
          .assetPath(destination.toString())
          .fileSizeBytes((long) mockData.length)
          .width(isImage ? 1920 : 1920)
          .height(isImage ? 1080 : 1080)
          .durationMs(isImage ? null : 15000)
          .codec(isImage ? null : "h264")
          .build();

    } catch (IOException e) {
      throw new RuntimeException("Failed to create mock asset", e);
    }
  }

  @Override
  public BigDecimal getCreditBalance() {
    return creditBalance;
  }

  @Override
  public boolean isAvailable() {
    return true;
  }

  private byte[] createMockImageBytes() {
    // Minimal 1x1 PNG (67 bytes)
    return new byte[] {
      (byte) 0x89,
      0x50,
      0x4E,
      0x47,
      0x0D,
      0x0A,
      0x1A,
      0x0A,
      0x00,
      0x00,
      0x00,
      0x0D,
      0x49,
      0x48,
      0x44,
      0x52,
      0x00,
      0x00,
      0x00,
      0x01,
      0x00,
      0x00,
      0x00,
      0x01,
      0x08,
      0x06,
      0x00,
      0x00,
      0x00,
      0x1F,
      0x15,
      (byte) 0xC4,
      (byte) 0x89,
      0x00,
      0x00,
      0x00,
      0x0A,
      0x49,
      0x44,
      0x41,
      0x54,
      0x78,
      (byte) 0x9C,
      0x63,
      0x00,
      0x01,
      0x00,
      0x00,
      0x05,
      0x00,
      0x01,
      0x0D,
      0x0A,
      0x2D,
      (byte) 0xB4,
      0x00,
      0x00,
      0x00,
      0x00,
      0x49,
      0x45,
      0x4E,
      0x44,
      (byte) 0xAE,
      0x42,
      0x60,
      (byte) 0x82
    };
  }

  private byte[] createMockVideoBytes() {
    // Minimal MP4 header (placeholder, not valid video)
    return "MOCK_VIDEO_DATA".getBytes();
  }
}
