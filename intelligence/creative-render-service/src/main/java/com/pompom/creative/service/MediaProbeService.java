package com.pompom.creative.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Independently measures downloaded media. Provider-declared metadata is never trusted as proof.
 */
@Service
public class MediaProbeService {
  private final ObjectMapper objectMapper;
  private final String ffprobePath;
  private final Duration timeout;

  public MediaProbeService(
      ObjectMapper objectMapper,
      @Value("${pompom.media.ffprobe-path:ffprobe}") String ffprobePath,
      @Value("${pompom.media.probe-timeout:20s}") Duration timeout) {
    this.objectMapper = objectMapper;
    this.ffprobePath = ffprobePath;
    this.timeout = timeout;
  }

  public ProbeResult probe(Path path) {
    List<String> command =
        List.of(
            ffprobePath,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,width,height,r_frame_rate,codec_type",
            "-of",
            "json",
            path.toString());
    try {
      Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
      byte[] output = process.getInputStream().readAllBytes();
      if (!process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
        process.destroyForcibly();
        throw new IllegalStateException("Media probe timed out");
      }
      if (process.exitValue() != 0) {
        throw new IllegalStateException(
            "Media probe rejected downloaded bytes: "
                + new String(output, StandardCharsets.UTF_8).trim());
      }
      JsonNode root = objectMapper.readTree(output);
      JsonNode video = null;
      for (JsonNode stream : root.path("streams")) {
        if ("video".equals(stream.path("codec_type").asText())) {
          video = stream;
          break;
        }
      }
      if (video == null
          || video.path("width").asInt(0) <= 0
          || video.path("height").asInt(0) <= 0) {
        throw new IllegalStateException("Downloaded media has no measurable video/image stream");
      }
      Double durationSeconds =
          root.path("format").path("duration").isMissingNode()
              ? null
              : root.path("format").path("duration").asDouble();
      return new ProbeResult(
          video.path("width").asInt(),
          video.path("height").asInt(),
          durationSeconds == null ? null : (int) Math.round(durationSeconds * 1000),
          video.path("codec_name").asText(null),
          parseFrameRate(video.path("r_frame_rate").asText(null)));
    } catch (IOException error) {
      throw new IllegalStateException("Media probe runtime is unavailable", error);
    } catch (InterruptedException error) {
      Thread.currentThread().interrupt();
      throw new IllegalStateException("Media probe was interrupted", error);
    }
  }

  private BigDecimal parseFrameRate(String value) {
    if (value == null || value.isBlank() || "0/0".equals(value)) {
      return null;
    }
    String[] parts = value.split("/", 2);
    if (parts.length == 1) {
      return new BigDecimal(parts[0]);
    }
    BigDecimal denominator = new BigDecimal(parts[1]);
    return denominator.signum() == 0
        ? null
        : new BigDecimal(parts[0]).divide(denominator, 2, java.math.RoundingMode.HALF_UP);
  }

  public record ProbeResult(
      int width, int height, Integer durationMs, String codec, BigDecimal frameRate) {}
}
