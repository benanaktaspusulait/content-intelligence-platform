package com.pompom.creative.service;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Runs the production video-upscale script after a real video download. */
@Component
@Slf4j
public class VideoUpscaleService {

  private final Path scriptPath;
  private final boolean enabled;
  private final String targetResolution;
  private final long timeoutSeconds;

  @Autowired
  public VideoUpscaleService(
      @Value("${pompom.render.upscale.script:tools/upscale.sh}") String scriptPath,
      @Value("${pompom.render.upscale.enabled:true}") boolean enabled,
      @Value("${pompom.render.upscale.target-resolution:1920x1080}") String targetResolution,
      @Value("${pompom.render.upscale.timeout-seconds:900}") long timeoutSeconds) {
    this(Paths.get(scriptPath), enabled, targetResolution, timeoutSeconds);
  }

  VideoUpscaleService(
      Path scriptPath, boolean enabled, String targetResolution, long timeoutSeconds) {
    this.scriptPath = scriptPath;
    this.enabled = enabled;
    this.targetResolution = targetResolution;
    this.timeoutSeconds = Math.max(1, timeoutSeconds);
  }

  /**
   * Preserve the downloaded source and upscale the working path in place.
   */
  public UpscaleResult upscale(Path input) {
    Path video = input.toAbsolutePath().normalize();
    if (!enabled) {
      return new UpscaleResult(video, null);
    }
    if (!Files.isRegularFile(video)) {
      throw new IllegalArgumentException("Video to upscale is not a regular file: " + video);
    }

    Path original =
        video.resolveSibling(
            video.getFileName().toString().replaceFirst("\\.mp4$", "-source-480p.mp4"));
    try {
      Files.copy(video, original, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
    } catch (IOException error) {
      throw new IllegalStateException("Could not preserve downloaded source video", error);
    }

    Path script = resolveScriptPath();
    if (!Files.isRegularFile(script)) {
      throw new IllegalStateException("Video upscale script not found: " + script);
    }

    List<String> command =
        List.of("bash", script.toString(), "-r", targetResolution, video.toString());
    try {
      Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
      CompletableFuture<String> output = readAsync(process.getInputStream());
      if (!process.waitFor(timeoutSeconds, TimeUnit.SECONDS)) {
        process.destroyForcibly();
        output.cancel(true);
        throw new IllegalStateException(
            "Video upscale timed out after " + timeoutSeconds + " seconds");
      }
      String diagnostic = output.join().trim();
      if (process.exitValue() != 0) {
        throw new IllegalStateException(
            "Video upscale failed with exit code "
                + process.exitValue()
                + (diagnostic.isBlank() ? "" : ": " + diagnostic));
      }
      if (!Files.isRegularFile(video) || Files.size(video) == 0) {
        throw new IllegalStateException("Video upscale produced no usable output: " + video);
      }
      log.info("Upscaled video to {}: {}", targetResolution, video);
      return new UpscaleResult(video, original);
    } catch (InterruptedException error) {
      Thread.currentThread().interrupt();
      throw new IllegalStateException("Video upscale interrupted", error);
    } catch (IOException error) {
      throw new IllegalStateException("Could not start video upscale script", error);
    }
  }

  public record UpscaleResult(Path finalPath, Path originalPath) {}

  private Path resolveScriptPath() {
    if (scriptPath.isAbsolute()) {
      return scriptPath.normalize();
    }
    return Paths.get(System.getProperty("user.dir")).resolve(scriptPath).normalize();
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
}
