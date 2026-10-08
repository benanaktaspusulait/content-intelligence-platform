package com.pompomhills.intelligence.video;

import com.pompomhills.intelligence.character.VideoCharacterAssociationService;
import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.creative.CreativeAnalysisEntity;
import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.creative.CreativeFingerprintEntity;
import com.pompomhills.intelligence.creative.CreativeFingerprintRepository;
import com.pompomhills.intelligence.video.api.VideoDtos;
import com.pompomhills.intelligence.video.api.VideoDtos.AnalysisResponse;
import com.pompomhills.intelligence.video.api.VideoDtos.DirectoryIngestResponse;
import com.pompomhills.intelligence.video.api.VideoDtos.IngestError;
import com.pompomhills.intelligence.video.api.VideoDtos.MediaCharacter;
import com.pompomhills.intelligence.video.api.VideoDtos.MediaDirectory;
import com.pompomhills.intelligence.video.api.VideoDtos.MediaFile;
import com.pompomhills.intelligence.video.api.VideoDtos.PromptCard;
import com.pompomhills.intelligence.video.api.VideoDtos.PromptFile;
import com.pompomhills.intelligence.video.api.VideoDtos.PromptWorkspace;
import com.pompomhills.intelligence.video.api.VideoDtos.QualitySummary;
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
import org.springframework.jdbc.core.simple.JdbcClient;
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
  private final VideoCharacterAssociationService characterAssociations;
  private final JdbcClient jdbc;
  public static final String CURRENT_ANALYSIS_VERSION = "sampled-visual-motion-v5";
  public static final String V5_ANALYSIS_VERSION = "sampled-visual-motion-v5";
  public static final String V4_ANALYSIS_VERSION = "sampled-visual-motion-v4";

  public VideoService(
      VideoRepository videos,
      CreativeAnalysisRepository analyses,
      CreativeFingerprintRepository fingerprints,
      VideoPathAliasRepository pathAliases,
      VideoVariantRepository variants,
      MlVideoClient ml,
      PompomProperties properties,
      Clock clock,
      VideoCharacterAssociationService characterAssociations,
      JdbcClient jdbc) {
    this.videos = videos;
    this.analyses = analyses;
    this.fingerprints = fingerprints;
    this.pathAliases = pathAliases;
    this.variants = variants;
    this.ml = ml;
    this.properties = properties;
    this.clock = clock;
    this.characterAssociations = characterAssociations;
    this.jdbc = jdbc;
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
      // Character association writes through JdbcClient and has an FK to videos. Flush the
      // JPA insert before that best-effort reconciliation runs, otherwise PostgreSQL can reject
      // the association because the new video row is still only pending in the persistence context.
      entity =
          videos.saveAndFlush(
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
    try {
      characterAssociations.associate(
          entity.getId(), VideoCharacterAssociationService.Mode.MISSING_ONLY);
    } catch (RuntimeException ignored) {
      // Character reconciliation is best-effort during ingest; the explicit backfill can retry it.
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
    return mediaFiles(relativeDirectory, recursive, null, null, null);
  }

  @Transactional(readOnly = true)
  public List<MediaFile> mediaFiles(
      String relativeDirectory,
      boolean recursive,
      UUID characterId,
      String characterRole,
      Boolean unresolvedCharacter) {
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
    Map<UUID, List<MediaCharacter>> characters = loadMediaCharacters(resolvedByPath.values());
    return files.stream()
        .filter(
            path ->
                matchesCharacterFilter(
                    resolvedByPath.get(root.relativize(path).toString()),
                    characters,
                    characterId,
                    characterRole,
                    unresolvedCharacter))
        .map(path -> mapMediaFile(root, path, resolvedByPath, characters))
        .toList();
  }

  @Transactional(readOnly = true)
  public List<PromptFile> promptFiles(String relativeDirectory) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path directory = root.resolve(relativeDirectory).normalize();
    if (!directory.startsWith(root) || !Files.isDirectory(directory)) {
      throw new IllegalArgumentException(
          "Prompt directory must be inside the configured data root");
    }
    try (Stream<Path> stream = Files.walk(directory)) {
      return stream
          .filter(Files::isRegularFile)
          .filter(this::isPromptFile)
          .sorted(Comparator.comparing(Path::toString))
          .limit(5000)
          .map(
              file ->
                  new PromptFile(
                      file.getFileName().toString(),
                      root.relativize(file).toString(),
                      root.relativize(file.getParent()).toString(),
                      fileSize(file),
                      lastModified(file)))
          .toList();
    } catch (IOException error) {
      throw new IllegalStateException("Could not scan prompt files", error);
    }
  }

  @Transactional(readOnly = true)
  public List<VideoDtos.PromptDirectory> promptDirectories(String relativeDirectory) {
    Map<String, Long> counts =
        promptFiles(relativeDirectory).stream()
            .collect(
                java.util.stream.Collectors.groupingBy(
                    PromptFile::folder,
                    LinkedHashMap::new,
                    java.util.stream.Collectors.counting()));
    return counts.entrySet().stream()
        .sorted(Map.Entry.comparingByKey(String.CASE_INSENSITIVE_ORDER))
        .map(
            entry -> {
              String path = entry.getKey();
              String name = path.substring(path.lastIndexOf('/') + 1);
              return new VideoDtos.PromptDirectory(name, path, entry.getValue());
            })
        .toList();
  }

  @Transactional(readOnly = true)
  public List<PromptWorkspace> promptWorkspaces(String relativeDirectory) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path base = root.resolve(relativeDirectory).normalize();
    if (!base.startsWith(root) || !Files.isDirectory(base)) {
      throw new IllegalArgumentException(
          "Prompt workspace root must be inside the configured data root");
    }
    Map<String, VideoEntity> ingested =
        videos.findAll().stream()
            .collect(
                java.util.stream.Collectors.toMap(
                    VideoEntity::getRelativePath, video -> video, (first, ignored) -> first));
    Map<String, PromptCard> promptCards = promptQualityCards(relativeDirectory);
    try (Stream<Path> stream = Files.list(base)) {
      // Match Video Library: the picker contains only first-level folders. Files in
      // nested shot/video folders are aggregated into their top-level creative.
      return stream
          .filter(Files::isDirectory)
          .map(folder -> promptWorkspaceForFolder(root, folder, ingested, promptCards))
          .filter(java.util.Objects::nonNull)
          .sorted(Comparator.comparing(PromptWorkspace::folderPath, String.CASE_INSENSITIVE_ORDER))
          .toList();
    } catch (IOException error) {
      throw new IllegalStateException("Could not scan prompt workspaces", error);
    }
  }

  private Map<String, PromptCard> promptQualityCards(String relativeDirectory) {
    String prefix = relativeDirectory.replaceAll("/+$", "");
    return jdbc
        .sql(
            """
            SELECT c.source_path,c.title,c.id content_id,pv.id prompt_version_id,pv.version_number,
                   q.id validation_record_id,q.created_at analyzed_at,q.ruleset_version,q.overall_score,q.status,
                   q.report_json::jsonb->'preRenderAssessment'->>'creative_grade' creative_grade,
                   COALESCE(q.report_json::jsonb->'preRenderAssessment'->>'prompt_stage',q.report_json::jsonb->'preRenderAssessment'->>'readiness') readiness,
                   q.report_json::jsonb->'preRenderAssessment'->>'verdict' summary
            FROM contents c
            JOIN LATERAL (SELECT id,version_number,raw_text FROM prompt_versions WHERE content_id=c.id ORDER BY version_number DESC LIMIT 1) pv ON true
            LEFT JOIN LATERAL (
              SELECT id,created_at,ruleset_version,overall_score,status,report_json
              FROM quality_validations
              WHERE ((content_id=c.id AND prompt_version_id=pv.id) OR prompt_text=pv.raw_text)
              ORDER BY id DESC LIMIT 1
            ) q ON true
            WHERE c.source_path LIKE :prefix || '/%'
            """)
        .param("prefix", prefix)
        .query(
            (rs, ignored) -> {
              String source = rs.getString("source_path");
              Long validation = nullableLong(rs, "validation_record_id");
              java.math.BigDecimal score = rs.getBigDecimal("overall_score");
              QualitySummary quality =
                  validation == null
                      ? null
                      : new QualitySummary(
                          validation,
                          rs.getObject("analyzed_at", java.sql.Timestamp.class).toInstant(),
                          rs.getString("ruleset_version"),
                          score == null ? null : score.doubleValue(),
                          rs.getString("status"),
                          rs.getString("creative_grade"),
                          rs.getString("readiness"),
                          rs.getString("summary"));
              return new PromptCard(
                  source,
                  rs.getString("title"),
                  rs.getLong("content_id"),
                  rs.getLong("prompt_version_id"),
                  rs.getInt("version_number"),
                  quality);
            })
        .list()
        .stream()
        .collect(
            java.util.stream.Collectors.toMap(
                PromptCard::sourcePath,
                item -> item,
                (first, ignored) -> first,
                LinkedHashMap::new));
  }

  private PromptWorkspace promptWorkspaceForFolder(
      Path root,
      Path folder,
      Map<String, VideoEntity> ingested,
      Map<String, PromptCard> promptCards) {
    try (Stream<Path> descendants = Files.walk(folder)) {
      List<Path> files = descendants.filter(Files::isRegularFile).toList();
      List<Path> videoFiles = files.stream().filter(this::hasAllowedExtension).sorted().toList();
      List<Path> promptFiles = files.stream().filter(this::isPromptFile).sorted().toList();

      String folderPath = root.relativize(folder).toString().replace('\\', '/');
      List<String> videosInFolder =
          videoFiles.stream()
              .map(file -> root.relativize(file).toString().replace('\\', '/'))
              .toList();
      List<String> promptsInFolder =
          promptFiles.stream()
              .map(file -> root.relativize(file).toString().replace('\\', '/'))
              .toList();
      String selected = videosInFolder.size() == 1 ? videosInFolder.get(0) : null;
      VideoEntity selectedEntity = selected == null ? null : ingested.get(selected);
      boolean anyAnalysed =
          videosInFolder.stream()
              .map(ingested::get)
              .filter(java.util.Objects::nonNull)
              .anyMatch(
                  video ->
                      analyses.existsByVideoIdAndAnalysisVersion(
                          video.getId(), CURRENT_ANALYSIS_VERSION));
      String analysis = anyAnalysed ? "ANALYZED" : "NOT_ANALYZED";
      String promptStatus =
          promptsInFolder.isEmpty()
              ? "NO_PROMPT"
              : promptsInFolder.size() == 1 ? "AVAILABLE" : "AMBIGUOUS";
      Instant modified =
          files.stream()
              .map(this::lastModifiedInstant)
              .filter(java.util.Objects::nonNull)
              .max(Comparator.naturalOrder())
              .orElse(null);
      List<PromptCard> promptRecords =
          promptsInFolder.stream()
              .map(promptCards::get)
              .filter(java.util.Objects::nonNull)
              .toList();
      return new PromptWorkspace(
          folder.getFileName().toString(),
          folderPath,
          videosInFolder,
          selected,
          selectedEntity == null ? null : selectedEntity.getId(),
          promptStatus,
          promptsInFolder,
          analysis,
          modified == null ? null : modified.toString(),
          promptRecords);
    } catch (IOException error) {
      return null;
    }
  }

  @Transactional
  public PromptWorkspace createPromptWorkspaceFolder(String parentDirectory, String folderName) {
    if (folderName == null
        || !folderName.matches("[\\p{L}\\p{N}][\\p{L}\\p{N} ._-]{0,99}")
        || folderName.endsWith(".")
        || folderName.endsWith(" ")) {
      throw new IllegalArgumentException(
          "Folder name must use Unicode letters, numbers, spaces, dot, underscore, or hyphen");
    }
    String parentValue =
        parentDirectory == null || parentDirectory.isBlank() ? "library" : parentDirectory;
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path parent = root.resolve(parentValue).normalize();
    Path folder = parent.resolve(folderName).normalize();
    if (!parent.startsWith(root) || !folder.startsWith(root) || !Files.isDirectory(parent)) {
      throw new IllegalArgumentException("Folder must stay inside the configured project root");
    }
    try {
      Files.createDirectory(folder);
      String relative = root.relativize(folder).toString().replace('\\', '/');
      return new PromptWorkspace(
          folderName,
          relative,
          List.of(),
          null,
          null,
          "NO_PROMPT",
          List.of(),
          "NOT_ANALYZED",
          Instant.now().toString());
    } catch (java.nio.file.FileAlreadyExistsException error) {
      throw new IllegalArgumentException("Folder already exists");
    } catch (IOException error) {
      throw new IllegalStateException("Could not create prompt workspace folder", error);
    }
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  private Instant lastModifiedInstant(Path file) {
    try {
      return Files.getLastModifiedTime(file).toInstant();
    } catch (IOException ignored) {
      return null;
    }
  }

  private boolean isPromptFile(Path file) {
    String name = file.getFileName().toString().toLowerCase(java.util.Locale.ROOT);
    return List.of(".txt", ".md", ".json", ".yaml", ".yml").stream().anyMatch(name::endsWith)
        && !name.contains("image")
        && !name.contains("storyboard")
        && !name.endsWith(".jsonl");
  }

  @Transactional(readOnly = true)
  public boolean hasCurrentAnalysis(UUID videoId) {
    return hasAnalysis(videoId, CURRENT_ANALYSIS_VERSION);
  }

  @Transactional(readOnly = true)
  public boolean hasAnalysis(UUID videoId, String version) {
    return analyses.existsByVideoIdAndAnalysisVersion(videoId, version);
  }

  @Transactional
  public AnalysisResponse analyse(UUID videoId) {
    return analyse(videoId, CURRENT_ANALYSIS_VERSION);
  }

  @Transactional
  public AnalysisResponse analyse(UUID videoId, String analysisVersion) {
    var video =
        videos
            .findById(videoId)
            .orElseThrow(() -> new EntityNotFoundException("Video not found: " + videoId));
    video.markAnalysing();
    try {
      Map<String, Object> cachedSemantic =
          analyses
              .findFirstByVideoIdAndAnalysisVersionOrderByCreatedAtDesc(videoId, analysisVersion)
              .map(CreativeAnalysisEntity::getSemanticVideoEvidence)
              .orElse(Map.of());
      var result = ml.analyse(video.getRelativePath(), analysisVersion, cachedSemantic, true);
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

  @Transactional
  public void ensureCanonicalAssessments(UUID videoId, String analysisVersion) {
    analyses
        .findFirstByVideoIdAndAnalysisVersionOrderByCreatedAtDesc(videoId, analysisVersion)
        .ifPresent(
            analysis -> {
              Map<String, Object> temporal = analysis.getTemporalProfile();
              Map<String, Object> semantic = analysis.getSemanticVideoEvidence();
              if (!SemanticEvidenceAvailability.isAvailable(semantic)) return;
              Map<String, Object> canonical = ml.fuseSemanticEvidence(temporal, semantic);
              if (canonical.equals(temporal.get("canonicalAssessments"))) return;
              Map<String, Object> updatedTemporal = new LinkedHashMap<>(temporal);
              updatedTemporal.put("canonicalAssessments", canonical);
              Map<String, Object> raw = new LinkedHashMap<>(analysis.getRawResult());
              raw.put("temporalProfile", updatedTemporal);
              raw.put("canonicalAssessments", canonical);
              analysis.updateRawResult(raw);
              analyses.save(analysis);
            });
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
    raw.put("temporalProfile", result.evidence().getOrDefault("temporalProfile", Map.of()));
    raw.put("presentation", result.evidence().getOrDefault("presentation", Map.of()));
    raw.put("semanticVideoEvidence", result.semanticVideoEvidence());
    var analysis =
        analyses
            .findFirstByVideoIdAndAnalysisVersionOrderByCreatedAtDesc(
                video.getId(), result.analysisVersion())
            .orElseGet(
                () ->
                    new CreativeAnalysisEntity(
                        video,
                        result.analysisVersion(),
                        result.analysisType(),
                        result.primaryEngine(),
                        result.secondaryEngines(),
                        result.classification(),
                        result.motionHeuristicScore() == null ? 0.0 : result.motionHeuristicScore(),
                        result.measurementConfidence() == null
                            ? 0.0
                            : result.measurementConfidence(),
                        result.reason(),
                        result.storyboardPath(),
                        result.timeline(),
                        raw));
    if (analysis.getId() != null) {
      analysis.updateFrom(
          result.analysisType(),
          result.primaryEngine(),
          result.secondaryEngines(),
          result.classification(),
          result.motionHeuristicScore() == null ? 0.0 : result.motionHeuristicScore(),
          result.measurementConfidence() == null ? 0.0 : result.measurementConfidence(),
          result.reason(),
          result.storyboardPath(),
          result.timeline(),
          raw);
    }
    analysis = analyses.save(analysis);
    final CreativeAnalysisEntity persistedAnalysis = analysis;
    String featureVersion =
        "sampled-visual-motion-v4".equals(result.analysisVersion())
            ? "creative-fingerprint-v4"
            : "creative-fingerprint-v1";
    fingerprints
        .findByVideoIdAndFeatureVersion(video.getId(), featureVersion)
        .ifPresentOrElse(
            existing ->
                existing.updateFrom(persistedAnalysis, result.actionDnaScore(), result.features()),
            () ->
                fingerprints.save(
                    new CreativeFingerprintEntity(
                        video,
                        persistedAnalysis,
                        featureVersion,
                        result.actionDnaScore(),
                        result.features())));
    return persistedAnalysis;
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

  private MediaFile mapMediaFile(
      Path root,
      Path file,
      Map<String, VideoEntity> ingestedByPath,
      Map<UUID, List<MediaCharacter>> characters) {
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
        variantId,
        findThumbnail(root, file),
        ingested == null ? List.of() : characters.getOrDefault(ingested.getId(), List.of()));
  }

  private Map<UUID, List<MediaCharacter>> loadMediaCharacters(
      java.util.Collection<VideoEntity> values) {
    List<UUID> ids = values.stream().map(VideoEntity::getId).distinct().toList();
    if (ids.isEmpty()) return Map.of();
    Map<UUID, List<MediaCharacter>> result = new java.util.HashMap<>();
    jdbc.sql(
            "SELECT"
                + " vc.video_id,c.id,c.name,vc.participation,vc.role,vc.association_source,vc.confidence"
                + " FROM video_characters vc JOIN characters c ON c.id=vc.character_id WHERE"
                + " vc.video_id IN (:ids) ORDER BY CASE WHEN vc.participation='PRIMARY' THEN 0 ELSE"
                + " 1 END,c.name")
        .param("ids", ids)
        .query(
            (rs, ignored) -> {
              UUID videoId = rs.getObject("video_id", UUID.class);
              result
                  .computeIfAbsent(videoId, unused -> new ArrayList<>())
                  .add(
                      new MediaCharacter(
                          rs.getObject("id", UUID.class),
                          rs.getString("name"),
                          rs.getString("participation"),
                          rs.getString("role"),
                          rs.getString("association_source"),
                          rs.getString("confidence")));
              return videoId;
            })
        .list();
    return result;
  }

  private boolean matchesCharacterFilter(
      VideoEntity video,
      Map<UUID, List<MediaCharacter>> characters,
      UUID characterId,
      String characterRole,
      Boolean unresolvedCharacter) {
    List<MediaCharacter> linked =
        video == null ? List.of() : characters.getOrDefault(video.getId(), List.of());
    if (Boolean.TRUE.equals(unresolvedCharacter) && !linked.isEmpty()) return false;
    if (characterId != null
        && linked.stream().noneMatch(character -> character.id().equals(characterId))) return false;
    return characterRole == null
        || characterRole.isBlank()
        || linked.stream()
            .anyMatch(
                character ->
                    characterRole.equalsIgnoreCase(character.participation())
                        || characterRole.equalsIgnoreCase(character.role()));
  }

  private String findThumbnail(Path root, Path video) {
    Path parent = video.getParent();
    if (parent == null) return null;
    try (Stream<Path> siblings = Files.list(parent)) {
      List<Path> images =
          siblings
              .filter(Files::isRegularFile)
              .filter(this::hasImageExtension)
              .sorted(
                  Comparator.comparing(
                          (Path path) -> !isFirstFrameName(path.getFileName().toString()))
                      .thenComparing(path -> path.getFileName().toString().toLowerCase()))
              .toList();
      return images.isEmpty() ? null : root.relativize(images.get(0)).toString();
    } catch (IOException ignored) {
      return null;
    }
  }

  private boolean hasImageExtension(Path file) {
    String name = file.getFileName().toString().toLowerCase(java.util.Locale.ROOT);
    return name.endsWith(".png")
        || name.endsWith(".jpg")
        || name.endsWith(".jpeg")
        || name.endsWith(".webp");
  }

  private boolean isFirstFrameName(String filename) {
    String name = filename.toLowerCase(java.util.Locale.ROOT);
    return name.contains("first") || name.contains("frame") || name.contains("scene");
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
