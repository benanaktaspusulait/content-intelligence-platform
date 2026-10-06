package com.pompom.creative.api.controller;

import com.pompom.creative.api.MediaResourceService;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.VisualEvidenceSubmissionDto;
import com.pompom.creative.evidence.VisualEvidenceSubmissionResponse;
import com.pompom.creative.repository.RenderAssetRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read-only access to durable render assets and their media metadata. */
@RestController
@RequestMapping("/api/v1/render-assets")
public class RenderAssetController {
  private final RenderAssetRepository assets;
  private final IntelligenceValidationEvidenceClient evidenceClient;
  private final MediaResourceService mediaResources;

  public RenderAssetController(RenderAssetRepository assets) {
    this(assets, null, null);
  }

  public RenderAssetController(
      RenderAssetRepository assets, IntelligenceValidationEvidenceClient evidenceClient) {
    this(assets, evidenceClient, null);
  }

  @org.springframework.beans.factory.annotation.Autowired
  public RenderAssetController(
      RenderAssetRepository assets,
      IntelligenceValidationEvidenceClient evidenceClient,
      MediaResourceService mediaResources) {
    this.assets = assets;
    this.evidenceClient = evidenceClient;
    this.mediaResources = mediaResources;
  }

  @GetMapping("/{id}")
  public ResponseEntity<AssetView> get(@PathVariable UUID id) {
    return assets
        .findById(id)
        .map(asset -> ResponseEntity.ok(toView(asset)))
        .orElseGet(() -> ResponseEntity.notFound().build());
  }

  @GetMapping("/by-job/{jobId}")
  public List<AssetView> byJob(@PathVariable UUID jobId) {
    return assets.findByRenderJobId(jobId).stream().map(this::toView).toList();
  }

  @GetMapping("/{id}/media")
  public ResponseEntity<?> media(
      @PathVariable UUID id, @RequestHeader(value = "Range", required = false) String rangeHeader) {
    RenderAsset asset = findAsset(id);
    if (mediaResources == null) {
      return ResponseEntity.status(HttpStatus.NOT_IMPLEMENTED).build();
    }
    MediaResourceService.ResolvedMedia media = mediaResources.resolve(asset);
    HttpHeaders headers = new HttpHeaders();
    headers.set(HttpHeaders.ACCEPT_RANGES, "bytes");
    headers.setContentType(media.mediaType());
    if (rangeHeader == null || rangeHeader.isBlank()) {
      headers.setContentLength(media.length());
      return ResponseEntity.ok().headers(headers).body(media.resource());
    }

    MediaResourceService.RangedMedia region = mediaResources.range(media, rangeHeader);
    org.springframework.http.HttpRange httpRange =
        org.springframework.http.HttpRange.parseRanges(rangeHeader).getFirst();
    long start = httpRange.getRangeStart(media.length());
    long end = httpRange.getRangeEnd(media.length());
    headers.set(HttpHeaders.CONTENT_RANGE, "bytes " + start + "-" + end + "/" + media.length());
    headers.setContentLength(end - start + 1);
    return ResponseEntity.status(HttpStatus.PARTIAL_CONTENT)
        .headers(headers)
        .body(region.resource());
  }

  @GetMapping("/{id}/download")
  public ResponseEntity<Resource> download(@PathVariable UUID id) {
    RenderAsset asset = findAsset(id);
    if (mediaResources == null) {
      return ResponseEntity.status(HttpStatus.NOT_IMPLEMENTED).build();
    }
    MediaResourceService.ResolvedMedia media = mediaResources.resolve(asset);
    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(media.mediaType());
    headers.setContentLength(media.length());
    headers.setContentDisposition(
        ContentDisposition.attachment().filename(media.filename()).build());
    return ResponseEntity.ok().headers(headers).body(media.resource());
  }

  private RenderAsset findAsset(UUID id) {
    return assets
        .findById(id)
        .orElseThrow(
            () ->
                new org.springframework.web.server.ResponseStatusException(
                    HttpStatus.NOT_FOUND, "Asset not found"));
  }

  @PostMapping("/{id}/visual-evidence")
  public ResponseEntity<VisualEvidenceSubmissionResponse> submitVisualEvidence(
      @PathVariable UUID id, @RequestBody VisualEvidenceSubmissionRequest request) {
    RenderAsset asset =
        assets
            .findById(id)
            .orElseThrow(
                () ->
                    new org.springframework.web.server.ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Asset not found"));
    if (asset.getAssetType() != RenderAsset.AssetType.FIRST_FRAME) {
      throw new org.springframework.web.server.ResponseStatusException(
          HttpStatus.UNPROCESSABLE_ENTITY, "Only FIRST_FRAME assets can supply visual evidence");
    }
    if (evidenceClient == null || asset.getRenderJob().getValidationRecordId() == null) {
      throw new org.springframework.web.server.ResponseStatusException(
          HttpStatus.UNPROCESSABLE_ENTITY, "Asset has no linked validation evidence");
    }
    VisualEvidenceSubmissionDto payload =
        new VisualEvidenceSubmissionDto(
            asset.getRenderJob().getValidationRecordId(),
            asset.getContentId(),
            asset.getRenderJob().getPromptVersionId(),
            asset.getRenderJob().getPromptSha256(),
            request.gate(),
            request.status(),
            request.evidenceSetId(),
            asset.getRenderJob().getId(),
            asset.getId(),
            asset.getAssetType().name(),
            asset.getRelativePath(),
            asset.getSha256(),
            request.provenance(),
            request.reason(),
            request.verificationId(),
            request.verifiedAt(),
            request.submissionKey());
    return ResponseEntity.status(HttpStatus.CREATED)
        .body(evidenceClient.submitVisualEvidence(payload));
  }

  public record VisualEvidenceSubmissionRequest(
      String gate,
      String status,
      UUID evidenceSetId,
      Map<String, Object> provenance,
      String reason,
      String verificationId,
      Instant verifiedAt,
      String submissionKey) {}

  private AssetView toView(RenderAsset asset) {
    return new AssetView(
        asset.getId(),
        asset.getRenderJob().getId(),
        asset.getContentId(),
        asset.getAssetType().name(),
        asset.getRelativePath(),
        asset.getFileSizeBytes(),
        asset.getDurationMs(),
        asset.getWidth(),
        asset.getHeight(),
        asset.getFrameRate(),
        asset.getCodec(),
        asset.getDownloadUrl(),
        asset.getDownloadedAt(),
        asset.getIsCurrent(),
        asset.getAssetVersion(),
        asset.getSha256(),
        asset.getMediaVerified(),
        asset.getIsMock(),
        asset.getQuarantined(),
        asset.getVideoId(),
        asset.getVariantId(),
        asset.getCreatedAt());
  }

  public record AssetView(
      UUID id,
      UUID renderJobId,
      Long contentId,
      String assetType,
      String relativePath,
      Long fileSizeBytes,
      Integer durationMs,
      Integer width,
      Integer height,
      BigDecimal frameRate,
      String codec,
      String downloadUrl,
      Instant downloadedAt,
      Boolean current,
      Integer assetVersion,
      String sha256,
      Boolean mediaVerified,
      Boolean mock,
      Boolean quarantined,
      UUID videoId,
      UUID variantId,
      Instant createdAt) {}
}
