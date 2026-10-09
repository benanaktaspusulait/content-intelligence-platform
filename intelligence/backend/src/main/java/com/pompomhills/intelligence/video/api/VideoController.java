package com.pompomhills.intelligence.video.api;

import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.VideoStatus;
import com.pompomhills.intelligence.video.job.AnalysisJobService;
import com.pompomhills.intelligence.video.platform.PlatformCreativeReadinessService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.core.io.Resource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/videos")
public class VideoController {
  private final VideoService service;
  private final MediaContentService mediaContent;
  private final AnalysisJobService jobService;
  private final CreativeAnalysisRepository analyses;
  private final PlatformCreativeReadinessService platformReadiness;
  private final VideoAnalysisPdfService analysisPdf;

  @Autowired
  public VideoController(
      VideoService service,
      MediaContentService mediaContent,
      AnalysisJobService jobService,
      CreativeAnalysisRepository analyses,
      PlatformCreativeReadinessService platformReadiness,
      VideoAnalysisPdfService analysisPdf) {
    this.service = service;
    this.mediaContent = mediaContent;
    this.jobService = jobService;
    this.analyses = analyses;
    this.platformReadiness = platformReadiness;
    this.analysisPdf = analysisPdf;
  }

  public VideoController(
      VideoService service,
      MediaContentService mediaContent,
      AnalysisJobService jobService,
      CreativeAnalysisRepository analyses) {
    this(service, mediaContent, jobService, analyses, null, new VideoAnalysisPdfService());
  }

  @PostMapping("/ingest")
  public VideoDtos.VideoResponse ingest(@Valid @RequestBody VideoDtos.IngestRequest request) {
    return service.ingest(request.relativePath(), request.seriesId());
  }

  @PostMapping("/ingest-directory")
  public VideoDtos.DirectoryIngestResponse ingestDirectory(
      @Valid @RequestBody VideoDtos.DirectoryIngestRequest request) {
    return service.ingestDirectory(
        request.relativeDirectory(), request.seriesId(), request.recursive());
  }

  @GetMapping("/media-directories")
  public List<VideoDtos.MediaDirectory> mediaDirectories(
      @RequestParam(defaultValue = "library") String relativeDirectory) {
    return service.mediaDirectories(relativeDirectory);
  }

  @GetMapping("/media-files")
  public List<VideoDtos.MediaFile> mediaFiles(
      @RequestParam String relativeDirectory,
      @RequestParam(defaultValue = "true") boolean recursive,
      @RequestParam(required = false) UUID characterId,
      @RequestParam(required = false) String characterRole,
      @RequestParam(required = false) Boolean unresolvedCharacter) {
    return service.mediaFiles(relativeDirectory, recursive, characterId, characterRole, unresolvedCharacter);
  }

  @GetMapping("/prompt-files")
  public List<VideoDtos.PromptFile> promptFiles(
      @RequestParam(defaultValue = "library") String relativeDirectory) {
    return service.promptFiles(relativeDirectory);
  }

  @GetMapping("/prompt-directories")
  public List<VideoDtos.PromptDirectory> promptDirectories(
      @RequestParam(defaultValue = "library") String relativeDirectory) {
    return service.promptDirectories(relativeDirectory);
  }

  @GetMapping("/prompt-workspaces")
  public List<VideoDtos.PromptWorkspace> promptWorkspaces(
      @RequestParam(defaultValue = "library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026") String relativeDirectory) {
    return service.promptWorkspaces(relativeDirectory);
  }

  @PostMapping("/prompt-workspaces/folders")
  public VideoDtos.PromptWorkspace createPromptWorkspaceFolder(
      @RequestBody VideoDtos.CreatePromptWorkspaceFolderRequest request) {
    return service.createPromptWorkspaceFolder(request.parentDirectory(), request.folderName());
  }

  @GetMapping("/content")
  public ResponseEntity<Resource> content(@RequestParam("path") String relativePath) {
    var media = mediaContent.resolve(relativePath);
    String filename =
        media.resource().getFilename() == null ? "video" : media.resource().getFilename();
    return ResponseEntity.ok()
        .contentType(MediaType.parseMediaType(media.contentType()))
        .contentLength(media.contentLength())
        .header(HttpHeaders.ACCEPT_RANGES, "bytes")
        .header(
            HttpHeaders.CONTENT_DISPOSITION,
            ContentDisposition.inline()
                .filename(filename, StandardCharsets.UTF_8)
                .build()
                .toString())
        .body(media.resource());
  }

  @GetMapping("/metadata")
  public VideoDtos.MetadataFile metadata(@RequestParam("path") String relativePath) {
    return new VideoDtos.MetadataFile(relativePath, mediaContent.readMetadata(relativePath));
  }

  @PutMapping("/metadata")
  public VideoDtos.MetadataFile updateMetadata(
      @Valid @RequestBody VideoDtos.MetadataUpdateRequest request) {
    mediaContent.writeMetadata(request.relativePath(), request.content());
    return new VideoDtos.MetadataFile(request.relativePath(), request.content());
  }

  @PostMapping("/{id}/analysis")
  public ResponseEntity<VideoDtos.AnalysisStatusResponse> analyse(
      @PathVariable UUID id,
      @RequestParam(defaultValue = "false") boolean force,
      @RequestParam(defaultValue = VideoService.CURRENT_ANALYSIS_VERSION) String analysisVersion) {
    jobService.enqueue(id, force, analysisVersion);
    var status = statusFor(id, analysisVersion);
    return status.hasCompletedAnalysis()
        ? ResponseEntity.ok(status)
        : ResponseEntity.accepted().body(status);
  }

  @GetMapping("/{id}/analysis/status")
  public VideoDtos.AnalysisStatusResponse status(
      @PathVariable UUID id,
      @RequestParam(defaultValue = VideoService.CURRENT_ANALYSIS_VERSION) String analysisVersion) {
    return statusFor(id, analysisVersion);
  }

  @GetMapping(value = "/{id}/analysis/report.pdf", produces = MediaType.APPLICATION_PDF_VALUE)
  public ResponseEntity<byte[]> exportAnalysisPdf(@PathVariable UUID id) {
    var status = statusFor(id, VideoService.CURRENT_ANALYSIS_VERSION);
    var video = service.get(id);
    byte[] pdf = analysisPdf.render(video.originalFilename(), status);
    String filename = video.originalFilename().replaceAll("[^A-Za-z0-9._-]+", "-") + "-analysis-report.pdf";
    return ResponseEntity.ok()
        .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename(filename).build().toString())
        .contentType(MediaType.APPLICATION_PDF)
        .body(pdf);
  }

  @GetMapping("/{id}/platform-readiness")
  public ResponseEntity<Map<String, Object>> platformReadiness(
      @PathVariable UUID id, @RequestParam String platform) {
    if (platformReadiness == null) {
      return ResponseEntity.status(503).body(Map.of("error", "Platform readiness service unavailable"));
    }
    return ResponseEntity.ok(platformReadiness.assess(id, platform));
  }

  private VideoDtos.AnalysisStatusResponse statusFor(UUID id, String analysisVersion) {
    service.ensureCanonicalAssessments(id, analysisVersion);
    var active = jobService.findActiveByIdentity(id, analysisVersion);
    if (active.isPresent()) {
      var job = active.get();
      return new VideoDtos.AnalysisStatusResponse(
          id, false, job.id().toString(), job.state(), job.attempts(), job.maxAttempts(),
          job.error(), null, null, null, null, null, null, null);
    }
    if (analyses.existsByVideoIdAndAnalysisVersion(id, analysisVersion)) {
      var analysis = analyses
          .findFirstByVideoIdAndAnalysisVersionOrderByCreatedAtDesc(id, analysisVersion)
          .orElseThrow();
      boolean legacy = "LEGACY".equals(analysis.getAnalysisType());
      return new VideoDtos.AnalysisStatusResponse(
          id,
          true,
          null,
          "COMPLETED",
          null,
          null,
          null,
          analysis.getId(),
          analysis.getClassification(),
          legacy ? analysis.getActionDnaScore() : null,
          legacy ? analysis.getConfidence() : null,
          analysis.getReason(),
          analysis.getStoryboardPath(),
          analysis.getAnalysisVersion(),
          analysis.getAnalysisType(),
          legacy ? null : analysis.getMotionHeuristicScore(),
          legacy ? null : analysis.getMeasurementConfidence(),
          analysis.getMeasurementQuality(),
          analysis.getSampling(),
          analysis.getMotion(),
          analysis.getVisualSimilarity(),
          analysis.getDarkFrameCandidates(),
          analysis.getTimeline(),
          analysis.getTemporalProfile(),
          analysis.getPresentation(),
          analysis.getSemanticVideoEvidence());
    }
    var latest = jobService.findLatestByIdentity(id, analysisVersion);
    if (latest.isEmpty()) {
      var legacy = analyses.findFirstByVideoIdOrderByCreatedAtDesc(id);
      if (legacy.isPresent() && "LEGACY".equals(legacy.get().getAnalysisType())) {
        var analysis = legacy.get();
        return new VideoDtos.AnalysisStatusResponse(
            id,
            true,
            null,
            "COMPLETED",
            null,
            null,
            null,
            analysis.getId(),
            analysis.getClassification(),
            analysis.getActionDnaScore(),
            analysis.getConfidence(),
            analysis.getReason(),
            analysis.getStoryboardPath(),
            analysis.getAnalysisVersion(),
            "LEGACY",
            null,
            null,
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            List.of(),
            List.of(),
            Map.of(),
            Map.of(),
            Map.of());
      }
      return new VideoDtos.AnalysisStatusResponse(
          id,
          false,
          null,
          "NOT_STARTED",
          null,
          null,
          null,
          null,
          null,
          null,
          null,
          null,
          null,
          null);
    }
    var job = latest.get();
    return new VideoDtos.AnalysisStatusResponse(
        id,
        false,
        job.id().toString(),
        job.state(),
        job.attempts(),
        job.maxAttempts(),
        job.error(),
        null,
        null,
        null,
        null,
        null,
        null,
        null);
  }

  @GetMapping
  public Page<VideoDtos.VideoResponse> list(
      @RequestParam(required = false) VideoStatus status, Pageable pageable) {
    return service.list(status, pageable);
  }

  @GetMapping("/{id}")
  public VideoDtos.VideoResponse get(@PathVariable UUID id) {
    return service.get(id);
  }
}
