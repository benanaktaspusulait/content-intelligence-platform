package com.pompom.creative.api;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.service.AssetLibraryManager;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.ResourceRegion;
import org.springframework.http.HttpRange;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import static org.springframework.http.HttpStatus.NOT_FOUND;
import static org.springframework.http.HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE;

/** Resolves stored assets into safe browser-streamable resources and byte ranges. */
@Service
public class MediaResourceService {

  private final AssetLibraryManager assetLibraryManager;

  public MediaResourceService(AssetLibraryManager assetLibraryManager) {
    this.assetLibraryManager = assetLibraryManager;
  }

  public ResolvedMedia resolve(RenderAsset asset) {
    if (Boolean.TRUE.equals(asset.getQuarantined())) {
      throw new ResponseStatusException(NOT_FOUND, "Asset is quarantined");
    }
    Path path = assetLibraryManager.resolveStoredPath(asset);
    if (!Files.isRegularFile(path)) {
      throw new ResponseStatusException(NOT_FOUND, "Asset file not found");
    }
    try {
      return new ResolvedMedia(
          new FileSystemResource(path),
          Files.size(path),
          mediaType(path),
          path.getFileName().toString());
    } catch (IOException error) {
      throw new ResponseStatusException(NOT_FOUND, "Asset file cannot be read", error);
    }
  }

  public ResourceRegion range(ResolvedMedia media, String rangeHeader) {
    try {
      List<HttpRange> ranges = HttpRange.parseRanges(rangeHeader);
      if (ranges.size() != 1) {
        throw new ResponseStatusException(
            REQUESTED_RANGE_NOT_SATISFIABLE, "Only one byte range is supported");
      }
      return ranges.getFirst().toResourceRegion(media.resource(), media.length());
    } catch (IllegalArgumentException error) {
      throw new ResponseStatusException(REQUESTED_RANGE_NOT_SATISFIABLE, "Invalid byte range", error);
    }
  }

  private MediaType mediaType(Path path) {
    try {
      String detected = Files.probeContentType(path);
      if (detected != null) return MediaType.parseMediaType(detected);
    } catch (Exception ignored) {
      // Use the durable asset type/path fallback below.
    }
    String name = path.getFileName().toString().toLowerCase(java.util.Locale.ROOT);
    if (name.endsWith(".mp4")) return MediaType.valueOf("video/mp4");
    if (name.endsWith(".png")) return MediaType.IMAGE_PNG;
    if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return MediaType.IMAGE_JPEG;
    return MediaType.APPLICATION_OCTET_STREAM;
  }

  public record ResolvedMedia(Resource resource, long length, MediaType mediaType, String filename) {}
}
