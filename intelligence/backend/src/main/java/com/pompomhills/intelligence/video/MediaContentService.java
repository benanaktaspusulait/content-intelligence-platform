package com.pompomhills.intelligence.video;

import com.pompomhills.intelligence.common.config.PompomProperties;
import jakarta.persistence.EntityNotFoundException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;

@Service
public class MediaContentService {
  private final PompomProperties properties;

  public MediaContentService(PompomProperties properties) {
    this.properties = properties;
  }

  public MediaContent resolve(String relativePath) {
    if (relativePath == null || relativePath.isBlank()) {
      throw new IllegalArgumentException("Media path is required");
    }

    Path configuredRoot = properties.dataRoot().toAbsolutePath().normalize();
    Path candidate = configuredRoot.resolve(relativePath).normalize();
    if (!candidate.startsWith(configuredRoot)) {
      throw new IllegalArgumentException("Media path must stay inside the configured data root");
    }
    if (!Files.exists(candidate)) {
      throw new EntityNotFoundException("Media file not found: " + relativePath);
    }

    try {
      Path root = configuredRoot.toRealPath();
      Path file = candidate.toRealPath();
      if (!file.startsWith(root)) {
        throw new IllegalArgumentException("Media path must stay inside the configured data root");
      }
      if (!Files.isRegularFile(file)) {
        throw new IllegalArgumentException("Media path must identify a regular file");
      }

      String extension = extension(file);
      if (!properties.allowedVideoExtensions().contains(extension)) {
        throw new IllegalArgumentException("Unsupported video extension: " + extension);
      }

      String contentType = Files.probeContentType(file);
      if (contentType == null || !contentType.startsWith("video/")) {
        contentType =
            switch (extension) {
              case "mov" -> "video/quicktime";
              case "m4v" -> "video/x-m4v";
              default -> "video/mp4";
            };
      }
      return new MediaContent(new FileSystemResource(file), contentType, Files.size(file));
    } catch (IOException error) {
      throw new IllegalStateException("Could not open media file", error);
    }
  }

  public String readMetadata(String relativePath) {
    if (relativePath == null || relativePath.isBlank()) {
      throw new IllegalArgumentException("Metadata path is required");
    }

    Path configuredRoot = properties.dataRoot().toAbsolutePath().normalize();
    Path candidate = configuredRoot.resolve(relativePath).normalize();
    if (!candidate.startsWith(configuredRoot)) {
      throw new IllegalArgumentException("Metadata path must stay inside the configured data root");
    }

    String filename = candidate.getFileName() == null
        ? ""
        : candidate.getFileName().toString().toLowerCase(Locale.ROOT);
    if (!filename.equals("social.md") && !filename.equals("youtube.md")) {
      throw new IllegalArgumentException("Only social.md and youtube.md metadata are readable");
    }

    try {
      Path root = configuredRoot.toRealPath();
      Path file = candidate.toRealPath();
      if (!file.startsWith(root) || !Files.isRegularFile(file)) {
        throw new EntityNotFoundException("Metadata file not found: " + relativePath);
      }
      if (Files.size(file) > 256 * 1024) {
        throw new IllegalArgumentException("Metadata file is too large");
      }
      return Files.readString(file, StandardCharsets.UTF_8);
    } catch (IOException error) {
      throw new IllegalStateException("Could not read metadata file", error);
    }
  }

  private String extension(Path file) {
    String name = file.getFileName().toString();
    int separator = name.lastIndexOf('.');
    return separator < 0 ? "" : name.substring(separator + 1).toLowerCase(Locale.ROOT);
  }

  public record MediaContent(Resource resource, String contentType, long contentLength) {}
}
