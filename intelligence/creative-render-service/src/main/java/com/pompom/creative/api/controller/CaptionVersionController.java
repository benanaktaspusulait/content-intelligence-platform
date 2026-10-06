package com.pompom.creative.api.controller;

import com.pompom.creative.domain.CaptionVersion;
import com.pompom.creative.repository.CaptionVersionRepository;
import java.util.List;
import java.util.UUID;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Durable, append-only social copy versions for reviewed render assets. */
@RestController
@RequestMapping("/api/v1/captions/versions")
@RequiredArgsConstructor
public class CaptionVersionController {
  private final CaptionVersionRepository repository;

  @GetMapping
  public List<CaptionVersion> list(@RequestParam UUID renderAssetId) {
    return repository.findByRenderAssetIdOrderByCreatedAtDesc(renderAssetId);
  }

  @PostMapping
  public ResponseEntity<?> save(@RequestBody SaveCaptionRequest request) {
    if (request.renderAssetId == null
        || request.platform == null
        || request.platform.isBlank()
        || request.caption == null
        || request.caption.isBlank()) {
      return ResponseEntity.badRequest().body("renderAssetId, platform and caption are required");
    }
    CaptionVersion version =
        repository.save(
            CaptionVersion.builder()
                .renderAssetId(request.renderAssetId)
                .platform(request.platform.trim().toUpperCase())
                .caption(request.caption)
                .hashtags(request.hashtags)
                .source(
                    request.source == null || request.source.isBlank()
                        ? "GENERATED"
                        : request.source.trim().toUpperCase())
                .createdBy(request.createdBy)
                .build());
    return ResponseEntity.status(HttpStatus.CREATED).body(version);
  }

  @Data
  public static class SaveCaptionRequest {
    private UUID renderAssetId;
    private String platform;
    private String caption;
    private String hashtags;
    private String source;
    private String createdBy;
  }
}
