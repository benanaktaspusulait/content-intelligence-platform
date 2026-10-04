package com.pompom.creative.openart;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.openart.dto.*;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Real OpenArt adapter using OpenArt CLI tool.
 *
 * <p>Prerequisites: - OpenArt CLI installed and accessible in PATH - OpenArt API key configured
 *
 * <p>CLI commands (example): - openart generate-image --prompt "..." --output-dir /path - openart
 * generate-video --prompt "..." --first-frame /path --output-dir /path - openart status --job-id
 * <id> - openart download --job-id <id> --output /path - openart credits
 *
 * <p>Note: Actual CLI command syntax depends on OpenArt's official CLI tool. This is a template
 * that needs to be adjusted based on actual CLI documentation.
 */
@Slf4j
@Component("realOpenArtAdapter")
public class CliRealOpenArtAdapter implements OpenArtAdapter {

  private final ObjectMapper objectMapper = new ObjectMapper();

  @Value("${pompom.openart.cli.path:openart}")
  private String cliPath;

  @Value("${pompom.openart.api-key:}")
  private String apiKey;

  @Value("${pompom.openart.cli.timeout-seconds:300}")
  private long timeoutSeconds;

  @Value("${pompom.openart.enabled:false}")
  private boolean enabled;

  @Override
  public OpenArtJobResponse generateImage(OpenArtImageRequest request) {
    if (!enabled) {
      throw new IllegalStateException(
          "OpenArt adapter is not enabled. Set pompom.openart.enabled=true");
    }

    checkAvailability();

    log.info(
        "Generating image via OpenArt CLI: model={}, style={}",
        request.getModel(),
        request.getStyle());

    try {
      List<String> command = buildImageGenerateCommand(request);
      String output = executeCommand(command);

      // Parse CLI output to extract job ID
      JsonNode response = objectMapper.readTree(output);
      String jobId = response.get("job_id").asText();
      BigDecimal estimatedCredits = new BigDecimal(response.get("estimated_credits").asText());

      log.info(
          "OpenArt image generation started: jobId={}, estimatedCredits={}",
          jobId,
          estimatedCredits);

      return OpenArtJobResponse.builder()
          .jobId(jobId)
          .status("QUEUED")
          .estimatedCredits(estimatedCredits)
          .build();

    } catch (Exception e) {
      log.error("Failed to generate image via OpenArt CLI", e);
      throw new RuntimeException("OpenArt image generation failed: " + e.getMessage(), e);
    }
  }

  @Override
  public OpenArtJobResponse generateVideo(OpenArtVideoRequest request) {
    if (!enabled) {
      throw new IllegalStateException(
          "OpenArt adapter is not enabled. Set pompom.openart.enabled=true");
    }

    checkAvailability();

    log.info(
        "Generating video via OpenArt CLI: duration={}s, firstFrame={}",
        request.getDurationSeconds(),
        request.getFirstFrameImageId());

    try {
      List<String> command = buildVideoGenerateCommand(request);
      String output = executeCommand(command);

      // Parse CLI output
      JsonNode response = objectMapper.readTree(output);
      String jobId = response.get("job_id").asText();
      BigDecimal estimatedCredits = new BigDecimal(response.get("estimated_credits").asText());

      log.info(
          "OpenArt video generation started: jobId={}, estimatedCredits={}",
          jobId,
          estimatedCredits);

      return OpenArtJobResponse.builder()
          .jobId(jobId)
          .status("QUEUED")
          .estimatedCredits(estimatedCredits)
          .build();

    } catch (Exception e) {
      log.error("Failed to generate video via OpenArt CLI", e);
      throw new RuntimeException("OpenArt video generation failed: " + e.getMessage(), e);
    }
  }

  @Override
  public OpenArtJobStatus getJobStatus(String jobId) {
    if (!enabled) {
      throw new IllegalStateException("OpenArt adapter is not enabled");
    }

    log.debug("Checking job status: jobId={}", jobId);

    try {
      List<String> command = buildStatusCommand(jobId);
      String output = executeCommand(command);

      // Parse CLI output
      JsonNode response = objectMapper.readTree(output);
      String status = response.get("status").asText();
      int progressPercent = response.get("progress_percent").asInt();
      String errorMessage = response.has("error") ? response.get("error").asText() : null;

      OpenArtJobStatus jobStatus =
          OpenArtJobStatus.builder()
              .jobId(jobId)
              .status(status)
              .progressPercent(progressPercent)
              .errorMessage(errorMessage)
              .build();

      log.debug("Job status: jobId={}, status={}, progress={}%", jobId, status, progressPercent);

      return jobStatus;

    } catch (Exception e) {
      log.error("Failed to get job status from OpenArt CLI", e);
      throw new RuntimeException("Failed to get job status: " + e.getMessage(), e);
    }
  }

  @Override
  public DownloadResult downloadAsset(String jobId, Path destination) {
    if (!enabled) {
      throw new IllegalStateException("OpenArt adapter is not enabled");
    }

    log.info("Downloading asset: jobId={}, destination={}", jobId, destination);

    try {
      // Ensure parent directory exists
      Files.createDirectories(destination.getParent());

      List<String> command = buildDownloadCommand(jobId, destination);
      String output = executeCommand(command);

      // Parse download result
      JsonNode response = objectMapper.readTree(output);

      DownloadResult result =
          DownloadResult.builder()
              .assetPath(destination.toString())
              .fileSizeBytes(Files.size(destination))
              .width(response.has("width") ? response.get("width").asInt() : null)
              .height(response.has("height") ? response.get("height").asInt() : null)
              .durationMs(response.has("duration_ms") ? response.get("duration_ms").asInt() : null)
              .codec(response.has("codec") ? response.get("codec").asText() : null)
              .build();

      log.info(
          "Asset downloaded successfully: jobId={}, size={} bytes",
          jobId,
          result.getFileSizeBytes());

      return result;

    } catch (Exception e) {
      log.error("Failed to download asset from OpenArt", e);
      throw new RuntimeException("Asset download failed: " + e.getMessage(), e);
    }
  }

  @Override
  public BigDecimal getCreditBalance() {
    if (!enabled) {
      return BigDecimal.ZERO;
    }

    log.debug("Fetching credit balance from OpenArt");

    try {
      List<String> command = buildCreditsCommand();
      String output = executeCommand(command);

      JsonNode response = objectMapper.readTree(output);
      BigDecimal balance = new BigDecimal(response.get("balance").asText());

      log.info("OpenArt credit balance: {}", balance);

      return balance;

    } catch (Exception e) {
      log.error("Failed to get credit balance from OpenArt CLI", e);
      return BigDecimal.ZERO;
    }
  }

  @Override
  public boolean isAvailable() {
    if (!enabled) {
      return false;
    }

    try {
      // Test CLI availability with version or help command
      List<String> command = List.of(cliPath, "--version");
      executeCommand(command);
      return true;
    } catch (Exception e) {
      log.warn("OpenArt CLI not available: {}", e.getMessage());
      return false;
    }
  }

  /** Check if OpenArt CLI is available, throw exception if not. */
  private void checkAvailability() {
    if (!isAvailable()) {
      throw new IllegalStateException(
          "OpenArt CLI is not available. Please install OpenArt CLI and configure API key.");
    }
  }

  /** Build CLI command for image generation. */
  private List<String> buildImageGenerateCommand(OpenArtImageRequest request) {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("generate-image");
    command.add("--prompt");
    command.add(request.getPromptText());

    if (request.getModel() != null) {
      command.add("--model");
      command.add(request.getModel());
    }

    if (request.getStyle() != null) {
      command.add("--style");
      command.add(request.getStyle());
    }

    if (request.getAspectRatio() != null) {
      command.add("--aspect-ratio");
      command.add(request.getAspectRatio());
    }

    command.add("--output-format");
    command.add("json");

    return command;
  }

  /** Build CLI command for video generation. */
  private List<String> buildVideoGenerateCommand(OpenArtVideoRequest request) {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("generate-video");
    command.add("--prompt");
    command.add(request.getPromptText());

    if (request.getModel() != null) {
      command.add("--model");
      command.add(request.getModel());
    }

    if (request.getFirstFrameImageId() != null) {
      command.add("--first-frame");
      command.add(request.getFirstFrameImageId());
    }

    if (request.getDurationSeconds() != null) {
      command.add("--duration");
      command.add(String.valueOf(request.getDurationSeconds()));
    }

    command.add("--output-format");
    command.add("json");

    return command;
  }

  /** Build CLI command for job status check. */
  private List<String> buildStatusCommand(String jobId) {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("status");
    command.add("--job-id");
    command.add(jobId);

    command.add("--output-format");
    command.add("json");

    return command;
  }

  /** Build CLI command for asset download. */
  private List<String> buildDownloadCommand(String jobId, Path destination) {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("download");
    command.add("--job-id");
    command.add(jobId);
    command.add("--output");
    command.add(destination.toString());

    command.add("--output-format");
    command.add("json");

    return command;
  }

  /** Build CLI command for credit balance check. */
  private List<String> buildCreditsCommand() {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("credits");

    command.add("--output-format");
    command.add("json");

    return command;
  }

  /** Execute CLI command and return output. */
  private String executeCommand(List<String> command) throws IOException, InterruptedException {
    log.debug("Executing OpenArt command: executable={}, operation={}", command.get(0), command.get(1));

    ProcessBuilder processBuilder = new ProcessBuilder(command);
    if (apiKey != null && !apiKey.isBlank()) {
      processBuilder.environment().put("OPENART_API_KEY", apiKey);
    }
    processBuilder.redirectErrorStream(true);

    Process process = processBuilder.start();

    // Read output
    StringBuilder output = new StringBuilder();
    try (BufferedReader reader =
        new BufferedReader(new InputStreamReader(process.getInputStream()))) {
      String line;
      while ((line = reader.readLine()) != null) {
        output.append(line).append("\n");
      }
    }

    // Wait for completion with timeout
    boolean completed = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);

    if (!completed) {
      process.destroyForcibly();
      throw new RuntimeException("Command timed out after " + timeoutSeconds + " seconds");
    }

    int exitCode = process.exitValue();
    if (exitCode != 0) {
      throw new RuntimeException(
          "Command failed with exit code " + exitCode + ": " + output.toString());
    }

    return output.toString();
  }
}
