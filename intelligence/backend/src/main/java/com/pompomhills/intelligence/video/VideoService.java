package com.pompomhills.intelligence.video;

import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.creative.CreativeAnalysisEntity;
import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.creative.CreativeFingerprintEntity;
import com.pompomhills.intelligence.creative.CreativeFingerprintRepository;
import com.pompomhills.intelligence.video.api.VideoDtos.AnalysisResponse;
import com.pompomhills.intelligence.video.api.VideoDtos.DirectoryIngestResponse;
import com.pompomhills.intelligence.video.api.VideoDtos.IngestError;
import com.pompomhills.intelligence.video.api.VideoDtos.MediaDirectory;
import com.pompomhills.intelligence.video.api.VideoDtos.MediaFile;
import com.pompomhills.intelligence.video.api.VideoDtos.VideoResponse;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import jakarta.persistence.EntityNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VideoService {
  private final VideoRepository videos;
  private final CreativeAnalysisRepository analyses;
  private final CreativeFingerprintRepository fingerprints;
  private final VideoPathAliasRepository pathAliases;
  private final VideoVariantRepository variants;
  private final MlVideoClient ml;
  private final PompomProperties properties;
  private final Clock clock;
  public static final String CURRENT_ANALYSIS_VERSION = "sampled-visual-motion-v2";

  public VideoService(
      VideoRepository videos,
      CreativeAnalysisRepository analyses,
      CreativeFingerprintRepository fingerprints,
      VideoPathAliasRepository pathAliases,
      VideoVariantRepository variants,
      MlVideoClient ml,
      PompomProperties properties,
      Clock clock) {
    this.videos = videos;
    this.analyses = analyses;
    this.fingerprints = fingerprints;
    this.pathAliases = pathAliases;
    this.variants = variants;
    this.ml = ml;
    this.properties = properties;
    this.clock = clock;
  }

  @Transactional
  public VideoResponse ingest(String relativePath, UUID seriesId) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path file = root.resolve(relativePath).normalize();
    if (!file.startsWith(root) || !Files.isRegularFile(file))
      throw new IllegalArgumentException(
          "Video path must be a file inside the configured data root");
    String extension = file.getFileName().toString().replaceFirst("^.*\\.", "").toLowerCase();
    if (!properties.allowedVideoExtensions().contains(extension))
      throw new IllegalArgumentException("Unsupported video extension: " + extension);
    var result = ml.analyse(root.relativize(file).toString());
    var metadata = result.metadata();
    String relative = root.relativize(file).toString();
    var entity = videos.findByContentHash(metadata.sha256()).orElse(null);
    if (entity != null) {
      if (!entity.getRelativePath().equals(relative)
          && pathAliases.findByRelativePath(relative).isEmpty()) {
        pathAliases.save(new VideoPathAliasEntity(entity, relative, metadata.sha256()));
      }
    } else {
      entity =
          videos.save(
              new VideoEntity(
                  UUID.randomUUID(),
                  metadata.sha256(),
                  file.getFileName().toString(),
                  relative,
                  metadata.durationMs(),
                  metadata.width(),
                  metadata.height(),
                  metadata.fps(),
                  metadata.aspectRatio(),
                  metadata.codec(),
                  metadata.audioPresent(),
                  seriesId,
                  clock.instant()));
    }
    if (!analyses.existsByVideoIdAndAnalysisVersion(entity.getId(), result.analysisVersion())) {
      persistCreativeAnalysis(entity, result);
      entity.markAnalysed();
    }
    return map(entity);
  }

  public DirectoryIngestResponse ingestDirectory(
      String relativeDirectory, UUID seriesId, boolean recursive) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path directory = root.resolve(relativeDirectory).normalize();
    if (!directory.startsWith(root) || !Files.isDirectory(directory)) {
      throw new IllegalArgumentException("Video directory must be inside the configured data root");
    }
    var files = new ArrayList<Path>();
    try (Stream<Path> stream = recursive ? Files.walk(directory) : Files.list(directory)) {
      stream
          .filter(Files::isRegularFile)
          .filter(this::hasAllowedExtension)
          .sorted(Comparator.comparing(Path::toString))
          .limit(1000)
          .forEach(files::add);
    } catch (IOException error) {
      throw new IllegalStateException("Could not scan video directory", error);
    }
    var ingested = new ArrayList<VideoResponse>();
    var errors = new ArrayList<IngestError>();
    for (Path file : files) {
      String relativePath = root.relativize(file).toString();
      try {
        ingested.add(ingest(relativePath, seriesId));
      } catch (RuntimeException error) {
        errors.add(new IngestError(relativePath, error.getMessage()));
      }
    }
    return new DirectoryIngestResponse(relativeDirectory, files.size(), ingested, errors);
  }

  public List<MediaDirectory> mediaDirectories(String relativeDirectory) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path directory = root.resolve(relativeDirectory).normalize();
    if (!directory.startsWith(root) || !Files.isDirectory(directory)) {
      throw new IllegalArgumentException("Media directory must be inside the configured data root");
    }
    try (Stream<Path> children = Files.list(directory)) {
      return children
          .filter(Files::isDirectory)
          .sorted(Comparator.comparing(path -> path.getFileName().toString().toLowerCase()))
          .map(
              path ->
                  new MediaDirectory(
                      path.getFileName().toString(),
                      root.relativize(path).toString(),
                      countVideos(path)))
          .toList();
    } catch (IOException error) {
      throw new IllegalStateException("Could not list media directories", error);
    }
  }

  @Transactional(readOnly = true)
  public List<MediaFile> mediaFiles(String relativeDirectory, boolean recursive) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path directory = root.resolve(relativeDirectory).normalize();
    if (!directory.startsWith(root) || !Files.isDirectory(directory)) {
      throw new IllegalArgumentException("Media directory must be inside the configured data root");
    }

    List<Path> files;
    try (Stream<Path> stream = recursive ? Files.walk(directory) : Files.list(directory)) {
      files =
          stream
              .filter(Files::isRegularFile)
              .filter(this::hasAllowedExtension)
              .sorted(Comparator.comparing(Path::toString))
              .limit(1000)
              .toList();
    } catch (IOException error) {
      throw new IllegalStateException("Could not list media files", error);
    }

    List<String> relativePaths =
        files.stream().map(path -> root.relativize(path).toString()).toList();
    Map<String, VideoEntity> ingestedByPath =
        relativePaths.isEmpty()
            ? Map.of()
            : videos.findAllByRelativePathIn(relativePaths).stream()
                .collect(
                    java.util.stream.Collectors.toMap(
                        VideoEntity::getRelativePath, video -> video, (first, ignored) -> first));

    List<String> unmatchedPaths =
        relativePaths.stream().filter(path -> !ingestedByPath.containsKey(path)).toList();
    Map<String, VideoEntity> aliasedByPath = new java.util.HashMap<>();
    if (!unmatchedPaths.isEmpty()) {
      for (String path : unmatchedPaths) {
        pathAliases
            .findByRelativePath(path)
            .ifPresent(alias -> aliasedByPath.put(path, alias.getVideo()));
      }
    }

    Map<String, VideoEntity> resolvedByPath = new java.util.HashMap<>(ingestedByPath);
    resolvedByPath.putAll(aliasedByPath);
    return files.stream().map(path -> mapMediaFile(root, path, resolvedByPath)).toList();
  }

  @Transactional(readOnly = true)
  public boolean hasCurrentAnalysis(UUID videoId) {
    return analyses.existsByVideoIdAndAnalysisVersion(videoId, CURRENT_ANALYSIS_VERSION);
  }

  @Transactional
  public AnalysisResponse analyse(UUID videoId) {
    var video =
        videos
            .findById(videoId)
            .orElseThrow(() -> new EntityNotFoundException("Video not found: " + videoId));
    video.markAnalysing();
    try {
      var result = ml.analyse(video.getRelativePath());
    var analysis = persistCreativeAnalysis(video, result);
      video.markAnalysed();
      return new AnalysisResponse(
          analysis.getId(),
          videoId,
          analysis.getPrimaryEngine(),
          analysis.getSecondaryEngines(),
          analysis.getClassification(),
          analysis.getMotionHeuristicScore(),
          analysis.getConfidence(),
          result.features(),
          analysis.getStoryboardPath());
    } catch (RuntimeException error) {
      video.markFailed();
      throw error;
    }
  }

  private CreativeAnalysisEntity persistCreativeAnalysis(
      VideoEntity video, MlVideoClient.MlAnalysisResponse result) {
    var raw = new LinkedHashMap<String, Object>();
    raw.put("contractVersion", result.contractVersion());
    raw.put("evidence", result.evidence());
    raw.put("analysisType", result.analysisType());
    raw.put("measurementQuality", result.measurementQuality());
    raw.put("sampling", result.sampling());
    raw.put("motion", result.motion());
    raw.put("visualSimilarity", result.visualSimilarity());
    raw.put("darkFrameCandidates", result.darkFrameCandidates());
    var analysis =
        analyses.save(
            new CreativeAnalysisEntity(
                video,
                result.analysisVersion(),
                result.analysisType(),
                result.primaryEngine(),
                result.secondaryEngines(),
                result.classification(),
                result.motionHeuristicScore() == null ? 0.0 : result.motionHeuristicScore(),
                result.measurementConfidence() == null ? 0.0 : result.measurementConfidence(),
                result.reason(),
                result.storyboardPath(),
                result.timeline(),
                raw));
    fingerprints.save(
        new CreativeFingerprintEntity(
            video, analysis, "creative-fingerprint-v1", result.actionDnaScore(), result.features()));
    return analysis;
  }

  @Transactional(readOnly = true)
  public Page<VideoResponse> list(VideoStatus status, Pageable pageable) {
    return status == null
        ? videos.findAll(pageable).map(this::map)
        : videos.findByStatus(status, pageable).map(this::map);
  }

  @Transactional(readOnly = true)
  public VideoResponse get(UUID id) {
    return videos
        .findById(id)
        .map(this::map)
        .orElseThrow(() -> new EntityNotFoundException("Video not found: " + id));
  }

  private VideoResponse map(VideoEntity v) {
    return new VideoResponse(
        v.getId(),
        v.getOriginalFilename(),
        v.getRelativePath(),
        v.getDurationMs(),
        v.getWidth(),
        v.getHeight(),
        v.getFps(),
        v.getAspectRatio(),
        v.getCodec(),
        v.isAudioPresent(),
        v.getStatus().name(),
        v.getSeriesId(),
        v.getIngestedAt());
  }

  private boolean hasAllowedExtension(Path file) {
    String name = file.getFileName().toString();
    int separator = name.lastIndexOf('.');
    return separator >= 0
        && properties
            .allowedVideoExtensions()
            .contains(name.substring(separator + 1).toLowerCase());
  }

  private MediaFile mapMediaFile(Path root, Path file, Map<String, VideoEntity> ingestedByPath) {
    String relativePath = root.relativize(file).toString();
    VideoEntity ingested = ingestedByPath.get(relativePath);
    UUID variantId =
        variants.findByGeneratedPath(relativePath).map(VideoVariantEntity::getId).orElse(null);
    return new MediaFile(
        file.getFileName().toString(),
        relativePath,
        fileSize(file),
        lastModified(file),
        ingested != null,
        ingested == null ? null : ingested.getId(),
        ingested == null ? null : ingested.getStatus().name(),
        variantId);
  }

  private Long fileSize(Path file) {
    try {
      return Files.size(file);
    } catch (IOException ignored) {
      return null;
    }
  }

  private Instant lastModified(Path file) {
    try {
      return Files.getLastModifiedTime(file).toInstant();
    } catch (IOException ignored) {
      return null;
    }
  }

  private long countVideos(Path directory) {
    try (Stream<Path> files = Files.walk(directory)) {
      return files
          .filter(Files::isRegularFile)
          .filter(this::hasAllowedExtension)
          .limit(10_000)
          .count();
    } catch (IOException error) {
      return 0;
    }
  }
}
