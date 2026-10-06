package com.pompom.creative.openart;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtImageRequest;
import com.pompom.creative.openart.dto.OpenArtJobResponse;
import com.pompom.creative.openart.dto.OpenArtJobStatus;
import com.pompom.creative.openart.dto.OpenArtVideoRequest;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * OpenArt adapter backed by the published OpenArt CLI contract.
 *
 * <p>The CLI owns authentication (OAuth credentials in {@code ~/.openart}, or {@code
 * OPENART_TOKEN}). Generation is submitted with {@code --async}; status is read with {@code
 * creation get}; and the result URL returned by the creation endpoint is downloaded by this adapter
 * because the CLI intentionally does not expose a separate download command.
 */
@Slf4j
@Component("realOpenArtAdapter")
public class CliRealOpenArtAdapter implements OpenArtAdapter {

  private static final Set<String> ID_FIELDS =
      Set.of("historyId", "history_id", "generationId", "generation_id", "id", "job_id");
  private static final Set<String> STATUS_FIELDS = Set.of("status", "state");
  private static final Set<String> ERROR_FIELDS =
      Set.of("errorMessage", "error_message", "failed_reason", "failedReason", "error");
  private static final Set<String> URL_FIELDS = Set.of("url", "videoUrl", "downloadUrl");
  private static final Set<String> CREDIT_FIELDS =
      Set.of("totalCredits", "credits", "unitCredits", "cost", "creditsUsed");

  private final ObjectMapper objectMapper;
  private final HttpClient httpClient;
  private final String cliPath;
  private final String openArtToken;
  private final long timeoutSeconds;
  private final boolean enabled;

  public CliRealOpenArtAdapter(
      @Value("${pompom.openart.cli.path:openart}") String cliPath,
      @Value("${pompom.openart.token:}") String openArtToken,
      @Value("${pompom.openart.cli.timeout-seconds:300}") long timeoutSeconds,
      @Value("${pompom.openart.enabled:false}") boolean enabled,
      ObjectMapper objectMapper) {
    this.cliPath = cliPath;
    this.openArtToken = openArtToken;
    this.timeoutSeconds = Math.max(1, timeoutSeconds);
    this.enabled = enabled;
    this.objectMapper = objectMapper;
    this.httpClient =
        HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(this.timeoutSeconds))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();
  }

  @Override
  public OpenArtJobResponse generateImage(OpenArtImageRequest request) {
    requireEnabled();
    checkCliAvailable();

    try {
      JsonNode response = runJsonCommand(buildImageGenerateCommand(request));
      String jobId = requiredText(response, ID_FIELDS, "history id");
      BigDecimal estimatedCredits = firstDecimal(response, CREDIT_FIELDS);
      if (estimatedCredits == null) {
        estimatedCredits = quoteCredits(request.getModel(), "text2image");
      }

      return OpenArtJobResponse.builder()
          .jobId(jobId)
          .status(normalizeStatus(firstText(response, STATUS_FIELDS), "QUEUED"))
          .estimatedCredits(estimatedCredits)
          .build();
    } catch (Exception error) {
      throw providerException("image generation", error);
    }
  }

  @Override
  public OpenArtJobResponse generateVideo(OpenArtVideoRequest request) {
    requireEnabled();
    checkCliAvailable();

    try {
      JsonNode response = runJsonCommand(buildVideoGenerateCommand(request));
      String jobId = requiredText(response, ID_FIELDS, "history id");
      BigDecimal estimatedCredits = firstDecimal(response, CREDIT_FIELDS);
      if (estimatedCredits == null) {
        estimatedCredits = quoteCredits(request.getModel(), "text2video");
      }

      return OpenArtJobResponse.builder()
          .jobId(jobId)
          .status(normalizeStatus(firstText(response, STATUS_FIELDS), "QUEUED"))
          .estimatedCredits(estimatedCredits)
          .build();
    } catch (Exception error) {
      throw providerException("video generation", error);
    }
  }

  @Override
  public OpenArtJobStatus getJobStatus(String jobId) {
    requireEnabled();
    if (jobId == null || jobId.isBlank()) {
      throw new IllegalArgumentException("OpenArt history id must not be blank");
    }

    try {
      JsonNode response = runJsonCommand(buildStatusCommand(jobId));
      String rawStatus = firstText(response, STATUS_FIELDS);
      String status = normalizeStatus(rawStatus, "UNKNOWN");
      Integer progress =
          firstInteger(response, Set.of("progressPercent", "progress_percent", "progress"));
      if (progress == null) {
        progress = "COMPLETE".equals(status) ? 100 : 0;
      }
      BigDecimal creditsUsed =
          firstDecimal(response, Set.of("creditsUsed", "credits_used", "credits"));

      return OpenArtJobStatus.builder()
          .jobId(jobId)
          .status(status)
          .progressPercent(progress)
          .errorMessage(firstText(response, ERROR_FIELDS))
          .creditsUsed(creditsUsed)
          .build();
    } catch (Exception error) {
      throw providerException("status lookup", error);
    }
  }

  @Override
  public DownloadResult downloadAsset(String jobId, Path destination) {
    requireEnabled();
    if (jobId == null || jobId.isBlank()) {
      throw new IllegalArgumentException("OpenArt history id must not be blank");
    }

    Path temporaryFile = null;
    try {
      JsonNode creation = runJsonCommand(buildStatusCommand(jobId));
      String status = normalizeStatus(firstText(creation, STATUS_FIELDS), "UNKNOWN");
      if ("FAILED".equals(status) || "CANCELLED".equals(status)) {
        throw new IllegalStateException(
            "OpenArt creation cannot be downloaded: " + firstText(creation, ERROR_FIELDS));
      }
      String resultUrl = requiredText(creation, URL_FIELDS, "result URL");
      URI uri = URI.create(resultUrl);
      if (!"http".equalsIgnoreCase(uri.getScheme()) && !"https".equalsIgnoreCase(uri.getScheme())) {
        throw new IllegalStateException("OpenArt result URL must use http or https");
      }

      Path parent = destination.toAbsolutePath().normalize().getParent();
      if (parent != null) {
        Files.createDirectories(parent);
      }
      temporaryFile = Files.createTempFile(parent, ".openart-", ".part");

      HttpRequest request =
          HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(timeoutSeconds)).GET().build();
      HttpResponse<Path> response =
          httpClient.send(request, HttpResponse.BodyHandlers.ofFile(temporaryFile));
      if (response.statusCode() < 200 || response.statusCode() >= 300) {
        throw new IOException("OpenArt result download returned HTTP " + response.statusCode());
      }

      Files.move(
          temporaryFile,
          destination,
          StandardCopyOption.REPLACE_EXISTING,
          StandardCopyOption.ATOMIC_MOVE);
      temporaryFile = null;

      return DownloadResult.builder()
          .assetPath(destination.toString())
          .fileSizeBytes(Files.size(destination))
          .width(firstInteger(creation, Set.of("width")))
          .height(firstInteger(creation, Set.of("height")))
          .durationMs(firstInteger(creation, Set.of("durationMs", "duration_ms")))
          .codec(firstText(creation, Set.of("codec", "video_codec")))
          .build();
    } catch (java.nio.file.AtomicMoveNotSupportedException error) {
      if (temporaryFile == null) {
        throw providerException("asset download", error);
      }
      try {
        Files.move(temporaryFile, destination, StandardCopyOption.REPLACE_EXISTING);
        temporaryFile = null;
        return DownloadResult.builder()
            .assetPath(destination.toString())
            .fileSizeBytes(Files.size(destination))
            .build();
      } catch (IOException moveError) {
        throw providerException("asset download", moveError);
      }
    } catch (Exception error) {
      throw providerException("asset download", error);
    } finally {
      if (temporaryFile != null) {
        try {
          Files.deleteIfExists(temporaryFile);
        } catch (IOException cleanupError) {
          log.warn("Could not remove temporary OpenArt download {}", temporaryFile, cleanupError);
        }
      }
    }
  }

  @Override
  public BigDecimal getCreditBalance() {
    requireEnabled();
    try {
      JsonNode response = runJsonCommand(buildCreditsCommand());
      BigDecimal balance = firstDecimal(response, Set.of("credits", "balance", "totalCredits"));
      if (balance == null) {
        throw new IllegalStateException("OpenArt account response did not contain credits");
      }
      return balance;
    } catch (Exception error) {
      throw providerException("credit balance lookup", error);
    }
  }

  @Override
  public boolean isAvailable() {
    if (!enabled) {
      return false;
    }
    try {
      executeCommand(List.of(cliPath, "version"));
      // Account access verifies both the CLI binary and the persisted OAuth/token credential.
      executeCommand(buildCreditsCommand());
      return true;
    } catch (Exception error) {
      log.warn("OpenArt CLI is not ready: {}", error.getMessage());
      return false;
    }
  }

  private void requireEnabled() {
    if (!enabled) {
      throw new IllegalStateException(
          "OpenArt adapter is not enabled. Set pompom.openart.enabled=true");
    }
  }

  private void checkCliAvailable() {
    try {
      executeCommand(List.of(cliPath, "version"));
    } catch (Exception error) {
      throw new IllegalStateException(
          "OpenArt CLI is not available at '" + cliPath + "'. Install it and run openart login.",
          error);
    }
  }

  private List<String> buildImageGenerateCommand(OpenArtImageRequest request) {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("generate");
    command.add("image");
    command.add(requiredRequestText(request.getPromptText(), "image prompt"));
    addOption(command, "--model", request.getModel());
    command.add("--async");
    command.add("--json");
    command.add("--no-input");
    return command;
  }

  private List<String> buildVideoGenerateCommand(OpenArtVideoRequest request) {
    List<String> command = new ArrayList<>();
    command.add(cliPath);
    command.add("generate");
    command.add("video");
    command.add(requiredRequestText(request.getPromptText(), "video prompt"));
    addOption(command, "--model", request.getModel());
    addOption(command, "--image", request.getFirstFrameImageId());
    if (request.getDurationSeconds() != null) {
      command.add("--duration");
      command.add(String.valueOf(request.getDurationSeconds()));
    }
    addOption(command, "--aspect-ratio", request.getAspectRatio());
    addOption(command, "--resolution", request.getResolution());
    command.add("--async");
    command.add("--json");
    command.add("--no-input");
    return command;
  }

  private List<String> buildStatusCommand(String jobId) {
    return List.of(cliPath, "creation", "get", jobId, "--json", "--no-input");
  }

  private List<String> buildCreditsCommand() {
    return List.of(cliPath, "account", "--json", "--no-input");
  }

  private List<String> buildModelCostCommand(String model, String mode) {
    return List.of(
        cliPath, "model", "cost", "--model", model, "--mode", mode, "--json", "--no-input");
  }

  private BigDecimal quoteCredits(String model, String mode) {
    if (model == null || model.isBlank()) {
      return null;
    }
    try {
      return firstDecimal(runJsonCommand(buildModelCostCommand(model, mode)), CREDIT_FIELDS);
    } catch (Exception error) {
      log.warn("Could not quote OpenArt credits for model {}: {}", model, error.getMessage());
      return null;
    }
  }

  private JsonNode runJsonCommand(List<String> command) throws IOException, InterruptedException {
    CommandResult result = executeCommand(command);
    try {
      return parseJson(result.stdout());
    } catch (RuntimeException parseError) {
      throw new IllegalStateException(
          "OpenArt CLI returned invalid JSON: "
              + parseError.getMessage()
              + "; stderr="
              + result.stderr(),
          parseError);
    }
  }

  private CommandResult executeCommand(List<String> command)
      throws IOException, InterruptedException {
    log.debug(
        "Executing OpenArt command: executable={}, operation={}", command.get(0), command.get(1));

    ProcessBuilder processBuilder = new ProcessBuilder(command);
    if (openArtToken != null && !openArtToken.isBlank()) {
      processBuilder.environment().put("OPENART_TOKEN", openArtToken);
    }

    Process process = processBuilder.start();
    CompletableFuture<String> stdout = readAsync(process.getInputStream());
    CompletableFuture<String> stderr = readAsync(process.getErrorStream());

    if (!process.waitFor(timeoutSeconds, TimeUnit.SECONDS)) {
      process.destroyForcibly();
      stdout.cancel(true);
      stderr.cancel(true);
      throw new IllegalStateException(
          "OpenArt command timed out after " + timeoutSeconds + " seconds");
    }

    String stdoutText = joinStream(stdout);
    String stderrText = joinStream(stderr);
    if (process.exitValue() != 0) {
      String diagnostic = stderrText.isBlank() ? stdoutText : stderrText;
      throw new IllegalStateException(
          "OpenArt command failed with exit code "
              + process.exitValue()
              + ": "
              + diagnostic.trim());
    }
    return new CommandResult(stdoutText, stderrText);
  }

  private CompletableFuture<String> readAsync(InputStream stream) {
    return CompletableFuture.supplyAsync(
        () -> {
          try (stream) {
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
          } catch (IOException error) {
            throw new UncheckedIOException(error);
          }
        });
  }

  private String joinStream(CompletableFuture<String> stream) {
    try {
      return stream.join();
    } catch (RuntimeException error) {
      throw new IllegalStateException("Could not read OpenArt CLI output", error);
    }
  }

  private JsonNode parseJson(String output) {
    String trimmed = output == null ? "" : output.trim();
    if (trimmed.isEmpty()) {
      throw new IllegalStateException("empty stdout");
    }
    try {
      return objectMapper.readTree(trimmed);
    } catch (IOException firstError) {
      int objectStart = trimmed.indexOf('{');
      int objectEnd = trimmed.lastIndexOf('}');
      if (objectStart >= 0 && objectEnd > objectStart) {
        try {
          return objectMapper.readTree(trimmed.substring(objectStart, objectEnd + 1));
        } catch (IOException ignored) {
          // Fall through to the original diagnostic.
        }
      }
      throw new IllegalStateException(firstError.getMessage(), firstError);
    }
  }

  private String requiredText(JsonNode root, Set<String> fields, String description) {
    String value = firstText(root, fields);
    if (value == null || value.isBlank()) {
      throw new IllegalStateException("OpenArt response did not contain " + description);
    }
    return value;
  }

  private String requiredRequestText(String value, String description) {
    if (value == null || value.isBlank()) {
      throw new IllegalArgumentException(description + " must not be blank");
    }
    return value;
  }

  private void addOption(List<String> command, String option, String value) {
    if (value != null && !value.isBlank()) {
      command.add(option);
      command.add(value);
    }
  }

  private String firstText(JsonNode root, Set<String> fields) {
    JsonNode value = findNode(root, fields);
    if (value == null || value.isNull() || value.isContainerNode()) {
      return null;
    }
    return value.asText();
  }

  private BigDecimal firstDecimal(JsonNode root, Set<String> fields) {
    JsonNode value = findNode(root, fields);
    if (value == null || value.isNull() || value.isContainerNode()) {
      return null;
    }
    try {
      return new BigDecimal(value.asText());
    } catch (NumberFormatException ignored) {
      return null;
    }
  }

  private Integer firstInteger(JsonNode root, Set<String> fields) {
    BigDecimal decimal = firstDecimal(root, fields);
    return decimal == null ? null : decimal.intValue();
  }

  private JsonNode findNode(JsonNode root, Set<String> fields) {
    if (root == null || root.isNull()) {
      return null;
    }
    if (root.isObject()) {
      for (String field : fields) {
        JsonNode direct = root.get(field);
        if (direct != null && !direct.isNull()) {
          return direct;
        }
      }
      var fieldsIterator = root.fields();
      while (fieldsIterator.hasNext()) {
        JsonNode nested = findNode(fieldsIterator.next().getValue(), fields);
        if (nested != null) {
          return nested;
        }
      }
    } else if (root.isArray()) {
      for (JsonNode item : root) {
        JsonNode nested = findNode(item, fields);
        if (nested != null) {
          return nested;
        }
      }
    }
    return null;
  }

  private String normalizeStatus(String rawStatus, String fallback) {
    if (rawStatus == null || rawStatus.isBlank()) {
      return fallback;
    }
    String status = rawStatus.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
    return switch (status) {
      case "PENDING", "QUEUED", "CREATED", "SUBMITTED" -> "QUEUED";
      case "RUNNING", "PROCESSING", "IN_PROGRESS", "GENERATING" -> "RUNNING";
      case "COMPLETE", "COMPLETED", "SUCCEEDED", "SUCCESS", "DONE" -> "COMPLETE";
      case "FAILED", "FAILURE", "ERROR", "ERRORED", "EXPIRED" -> "FAILED";
      case "CANCELLED", "CANCELED" -> "CANCELLED";
      default -> "UNKNOWN";
    };
  }

  private RuntimeException providerException(String operation, Exception error) {
    if (error instanceof RuntimeException runtimeException
        && runtimeException.getMessage() != null
        && runtimeException.getMessage().startsWith("OpenArt " + operation + " failed")) {
      return runtimeException;
    }
    log.error("OpenArt {} failed: {}", operation, error.getMessage(), error);
    return new IllegalStateException(
        "OpenArt " + operation + " failed: " + error.getMessage(), error);
  }

  private record CommandResult(String stdout, String stderr) {}
}
