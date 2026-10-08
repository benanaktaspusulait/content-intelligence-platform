package com.pompom.metapublisher.storage;

import com.pompom.metapublisher.MetaPublisherProperties;
import com.pompom.publishercontract.PublishCommand;
import java.io.IOException;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/** Explicitly configured local/dev storage; it never exposes a local path implicitly. */
@Component
public class ConfiguredPublicMediaStorage implements PublicMediaStorage {

  private final MetaPublisherProperties properties;
  private final Map<String, Path> ownedMedia = new ConcurrentHashMap<>();

  public ConfiguredPublicMediaStorage(MetaPublisherProperties properties) {
    this.properties = properties;
  }

  @Override
  public Optional<HostedMedia> host(PublishCommand command) {
    String assetReference = command.assetReference();
    if (PublicMediaStorage.isSafeHttpsUrl(assetReference)) {
      return Optional.of(new HostedMedia(assetReference, false));
    }
    if (isHttps(assetReference) || isHttp(assetReference)) {
      return Optional.empty();
    }

    String backend = normalized(properties.storageBackend());
    return switch (backend) {
      case "none", "off", "disabled", "" -> Optional.empty();
      case "template", "url" -> templateMedia(command);
      case "public_dir", "dir", "local" -> publicDirectoryMedia(command);
      default -> Optional.empty();
    };
  }

  @Override
  public void cleanup(String url) {
    Path target = ownedMedia.remove(url);
    if (target == null || !properties.storageCleanup()) {
      return;
    }
    try {
      Files.deleteIfExists(target);
    } catch (IOException ignored) {
      // Cleanup is best effort and must not change a provider result.
    }
  }

  private Optional<HostedMedia> templateMedia(PublishCommand command) {
    String template = properties.storageUrlTemplate();
    if (template == null || template.isBlank()) {
      return Optional.empty();
    }
    String filename = filename(command.assetReference());
    String url =
        template
            .replace("{filename}", filename)
            .replace("{stem}", stem(filename))
            .replace("{content_id}", command.publicationJobId().toString());
    if (!PublicMediaStorage.isSafeHttpsUrl(url)) {
      return Optional.empty();
    }
    return Optional.of(new HostedMedia(url, false));
  }

  private Optional<HostedMedia> publicDirectoryMedia(PublishCommand command) {
    String directoryValue = properties.storageDirectory();
    String baseUrl = properties.storageBaseUrl();
    if (directoryValue == null
        || directoryValue.isBlank()
        || !PublicMediaStorage.isSafeHttpsUrl(baseUrl)) {
      return Optional.empty();
    }
    Path source = Path.of(command.assetReference());
    if (!Files.isRegularFile(source)) {
      return Optional.empty();
    }
    try {
      Path directory = Path.of(directoryValue).toAbsolutePath().normalize();
      Files.createDirectories(directory);
      String objectName = UUID.randomUUID() + "-" + filename(command.assetReference());
      Path target = directory.resolve(objectName).normalize();
      if (!target.getParent().equals(directory)) {
        return Optional.empty();
      }
      Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
      String url = trimTrailingSlash(baseUrl) + "/" + objectName;
      ownedMedia.put(url, target);
      return Optional.of(new HostedMedia(url, true));
    } catch (IOException | RuntimeException failure) {
      return Optional.empty();
    }
  }

  private boolean isHttp(String value) {
    try {
      URI uri = URI.create(value);
      return "http".equalsIgnoreCase(uri.getScheme());
    } catch (IllegalArgumentException ignored) {
      return false;
    }
  }

  private String normalized(String value) {
    return value == null ? "" : value.trim().toLowerCase();
  }

  private String filename(String value) {
    try {
      Path path = Path.of(value);
      String name = path.getFileName() == null ? "video.mp4" : path.getFileName().toString();
      String safe = name.replaceAll("[^A-Za-z0-9._-]", "-");
      return safe.isBlank() ? "video.mp4" : safe;
    } catch (RuntimeException ignored) {
      return "video.mp4";
    }
  }

  private String stem(String filename) {
    int dot = filename.lastIndexOf('.');
    return dot > 0 ? filename.substring(0, dot) : filename;
  }

  private String trimTrailingSlash(String value) {
    return value.replaceAll("/+$", "");
  }
}
