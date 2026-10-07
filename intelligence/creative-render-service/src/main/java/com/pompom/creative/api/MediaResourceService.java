package com.pompom.creative.api;

import static org.springframework.http.HttpStatus.NOT_FOUND;
import static org.springframework.http.HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.service.AssetLibraryManager;
import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpRange;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/** Resolves stored assets into safe browser-streamable resources and byte ranges. */
@Service
public class MediaResourceService {

  private final AssetLibraryManager assetLibraryManager;

  public MediaResourceService(AssetLibraryManager assetLibraryManager) {
    this.assetLibraryManager = assetLibraryManager;
  }

  public ResolvedMedia resolve(RenderAsset asset) {
    return resolveAt(asset, assetLibraryManager.resolveStoredPath(asset));
  }

  public ResolvedMedia resolveOriginal(RenderAsset asset) {
    return resolveAt(asset, assetLibraryManager.resolveOriginalPath(asset));
  }

  private ResolvedMedia resolveAt(RenderAsset asset, Path path) {
    if (Boolean.TRUE.equals(asset.getQuarantined())) {
      throw new ResponseStatusException(NOT_FOUND, "Asset is quarantined");
    }
    if (!Files.isRegularFile(path)) {
      throw new ResponseStatusException(NOT_FOUND, "Asset file not found");
    }
    try {
      return new ResolvedMedia(
          new FileSystemResource(path),
          path,
          Files.size(path),
          mediaType(path),
          path.getFileName().toString());
    } catch (IOException error) {
      throw new ResponseStatusException(NOT_FOUND, "Asset file cannot be read", error);
    }
  }

  public RangedMedia range(ResolvedMedia media, String rangeHeader) {
    try {
      List<HttpRange> ranges = HttpRange.parseRanges(rangeHeader);
      if (ranges.size() != 1) {
        throw new ResponseStatusException(
            REQUESTED_RANGE_NOT_SATISFIABLE, "Only one byte range is supported");
      }
      HttpRange range = ranges.getFirst();
      long start = range.getRangeStart(media.length());
      long end = range.getRangeEnd(media.length());
      InputStream input = Files.newInputStream(media.path());
      skipFully(input, start);
      return new RangedMedia(
          new InputStreamResource(new LimitedInputStream(input, end - start + 1)), start, end);
    } catch (IOException | IllegalArgumentException error) {
      throw new ResponseStatusException(
          REQUESTED_RANGE_NOT_SATISFIABLE, "Invalid byte range", error);
    }
  }

  private void skipFully(InputStream input, long bytes) throws IOException {
    long remaining = bytes;
    while (remaining > 0) {
      long skipped = input.skip(remaining);
      if (skipped <= 0) {
        if (input.read() < 0) throw new IOException("Range starts beyond media length");
        skipped = 1;
      }
      remaining -= skipped;
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

  public record ResolvedMedia(
      Resource resource, Path path, long length, MediaType mediaType, String filename) {}

  public record RangedMedia(Resource resource, long start, long end) {}

  private static final class LimitedInputStream extends FilterInputStream {
    private long remaining;

    private LimitedInputStream(InputStream input, long remaining) {
      super(input);
      this.remaining = remaining;
    }

    @Override
    public int read() throws IOException {
      if (remaining == 0) return -1;
      int value = super.read();
      if (value >= 0) remaining--;
      return value;
    }

    @Override
    public int read(byte[] buffer, int offset, int length) throws IOException {
      if (remaining == 0) return -1;
      int read = super.read(buffer, offset, (int) Math.min(length, remaining));
      if (read > 0) remaining -= read;
      return read;
    }
  }
}
