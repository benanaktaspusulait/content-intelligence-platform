package com.pompomhills.intelligence.video.api;

import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.VideoStatus;
import jakarta.validation.Valid;
import java.nio.charset.StandardCharsets;
import java.util.List;
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
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/videos")
public class VideoController {
  private final VideoService service;
  private final MediaContentService mediaContent;

  public VideoController(VideoService service, MediaContentService mediaContent) {
    this.service = service;
    this.mediaContent = mediaContent;
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
      @RequestParam(defaultValue = "true") boolean recursive) {
    return service.mediaFiles(relativeDirectory, recursive);
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

  @PostMapping("/{id}/analysis")
  public VideoDtos.AnalysisResponse analyse(@PathVariable UUID id) {
    return service.analyse(id);
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
