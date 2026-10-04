package com.pompom.creative.service;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.repository.RenderAssetRepository;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Manages filesystem storage for downloaded render assets.
 *
 * <p>Responsibilities: - Generate filesystem paths for content assets - Create directory structure
 * on demand - Record downloaded assets in database - Track asset versions (v1, v2, v3...)
 *
 * <p>Filesystem structure: ${POMPOM_DATA_ROOT}/ content/ {content-id}/ first-frame-v1.png
 * first-frame-v2.png render-v1.mp4 render-v2.mp4
 */
@Service
@Slf4j
public class AssetLibraryManager {

  private final RenderAssetRepository assetRepo;
  private final MediaProbeService mediaProbeService;
  private final Path dataRoot;

  public AssetLibraryManager(
      RenderAssetRepository assetRepo,
      MediaProbeService mediaProbeService,
      @Value("${pompom.data.root:/tmp/pompom-data}") String dataRoot) {
    this.assetRepo = assetRepo;
    this.mediaProbeService = mediaProbeService;
    this.dataRoot = Paths.get(dataRoot);
    log.info("AssetLibraryManager initialized with data root: {}", this.dataRoot);
  }

  /**
   * Get the directory path for a content's assets, creating it if needed.
   *
   * @param contentId Content ID
   * @return Path to content directory (e.g., /data/content/123/)
   */
  public Path getContentDirectory(Long contentId) {
    Path dir = dataRoot.resolve("content").resolve(contentId.toString());

    try {
      if (!Files.exists(dir)) {
        Files.createDirectories(dir);
        log.info("Created content directory: {}", dir);
      }
    } catch (IOException e) {
      throw new RuntimeException("Failed to create directory: " + dir, e);
    }

    return dir;
  }

  /**
   * Generate a filesystem path for an asset.
   *
   * @param contentId Content ID
   * @param assetType FIRST_FRAME or VIDEO
   * @param version Version number (1, 2, 3...)
   * @return Full path to asset file
   */
  public Path getAssetPath(Long contentId, RenderAsset.AssetType assetType, int version) {
    Path dir = getContentDirectory(contentId);
    String filename = generateFilename(assetType, version);
    return dir.resolve(filename);
  }

  /**
   * Get the next version number for a content's asset type. Queries existing assets and returns max
   * version + 1.
   *
   * @param contentId Content ID
   * @param assetType FIRST_FRAME or VIDEO
   * @return Next version number (starts at 1)
   */
  public int getNextVersion(Long contentId, RenderAsset.AssetType assetType) {
    List<RenderAsset> assets = assetRepo.findByContentIdOrderByCreatedAtDesc(contentId);

    int maxVersion =
        assets.stream()
            .filter(a -> a.getAssetType() == assetType)
            .map(a -> extractVersionFromPath(a.getRelativePath()))
            .max(Integer::compare)
            .orElse(0);

    int nextVersion = maxVersion + 1;
    log.debug("Next version for content {} type {}: v{}", contentId, assetType, nextVersion);

    return nextVersion;
  }

  /**
   * Record a downloaded asset in the database. Creates a RenderAsset entity from the download
   * result.
   *
   * @param job Render job that produced this asset
   * @param downloadResult Download metadata from OpenArt adapter
   * @return Saved RenderAsset entity
   */
  @Transactional
  public RenderAsset recordAsset(RenderJob job, DownloadResult downloadResult) {
    log.info("Recording asset for job {} at path: {}", job.getId(), downloadResult.getAssetPath());

    // Convert absolute path to relative path (relative to data root)
    Path absolutePath = Paths.get(downloadResult.getAssetPath());
    Path normalizedRoot = dataRoot.toAbsolutePath().normalize();
    Path normalizedAsset = absolutePath.toAbsolutePath().normalize();
    if (!normalizedAsset.startsWith(normalizedRoot)) {
      throw new IllegalArgumentException("Downloaded asset is outside the configured data root");
    }
    if (!Files.isRegularFile(normalizedAsset)) {
      throw new IllegalArgumentException("Downloaded asset is not a regular file");
    }
    String relativePath = dataRoot.relativize(absolutePath).toString();

    // Determine asset type from job type
    RenderAsset.AssetType assetType =
        job.getJobType() == RenderJob.JobType.FIRST_FRAME
            ? RenderAsset.AssetType.FIRST_FRAME
            : RenderAsset.AssetType.VIDEO;
    int assetVersion = extractVersionFromPath(relativePath);
    if (assetVersion < 1) {
      throw new IllegalArgumentException("Asset path does not contain an explicit version");
    }
    String checksum = sha256(normalizedAsset);
    boolean mock = job.getOpenartJobId() != null && job.getOpenartJobId().startsWith("mock-");
    MediaProbeService.ProbeResult measured = mock ? null : mediaProbeService.probe(normalizedAsset);

    // Create asset entity
    RenderAsset asset =
        RenderAsset.builder()
            .renderJob(job)
            .contentId(job.getContentId())
            .assetType(assetType)
            .relativePath(relativePath)
            .fileSizeBytes(downloadResult.getFileSizeBytes())
            .width(measured == null ? downloadResult.getWidth() : measured.width())
            .height(measured == null ? downloadResult.getHeight() : measured.height())
            .durationMs(measured == null ? downloadResult.getDurationMs() : measured.durationMs())
            .codec(measured == null ? downloadResult.getCodec() : measured.codec())
            .frameRate(measured == null ? null : measured.frameRate())
            .downloadUrl(null) // Not stored in mock implementation
            .isCurrent(true)
            .assetVersion(assetVersion)
            .sha256(checksum)
            .mediaVerified(measured != null)
            .isMock(mock)
            .quarantined(false)
            .build();

    asset = assetRepo.save(asset);
    log.info(
        "Recorded asset {} for content {}: type={}, size={} bytes",
        asset.getId(),
        job.getContentId(),
        assetType,
        asset.getFileSizeBytes());

    return asset;
  }

  /**
   * Generate filename based on asset type and version.
   *
   * @param assetType FIRST_FRAME or VIDEO
   * @param version Version number
   * @return Filename (e.g., "first-frame-v1.png" or "render-v2.mp4")
   */
  private String generateFilename(RenderAsset.AssetType assetType, int version) {
    if (assetType == RenderAsset.AssetType.FIRST_FRAME) {
      return String.format("first-frame-v%d.png", version);
    } else {
      return String.format("render-v%d.mp4", version);
    }
  }

  /**
   * Extract version number from asset path. Matches patterns like "first-frame-v1.png" or
   * "render-v2.mp4".
   *
   * @param path Asset relative path
   * @return Version number, or 0 if not found
   */
  private int extractVersionFromPath(String path) {
    Pattern pattern = Pattern.compile("v(\\d+)");
    Matcher matcher = pattern.matcher(path);

    if (matcher.find()) {
      return Integer.parseInt(matcher.group(1));
    }

    return 0;
  }

  /** Resolve an asset path without allowing traversal outside the configured storage root. */
  public Path resolveStoredPath(RenderAsset asset) {
    Path resolved = dataRoot.toAbsolutePath().normalize().resolve(asset.getRelativePath()).normalize();
    if (!resolved.startsWith(dataRoot.toAbsolutePath().normalize())) {
      throw new IllegalArgumentException("Asset path escapes the configured data root");
    }
    return resolved;
  }

  public String checksum(Path path) {
    return sha256(path.toAbsolutePath().normalize());
  }

  private String sha256(Path path) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      try (var input = Files.newInputStream(path)) {
        byte[] buffer = new byte[8192];
        int read;
        while ((read = input.read(buffer)) >= 0) {
          digest.update(buffer, 0, read);
        }
      }
      return HexFormat.of().formatHex(digest.digest());
    } catch (IOException | NoSuchAlgorithmException error) {
      throw new IllegalStateException("Unable to checksum asset", error);
    }
  }
}
