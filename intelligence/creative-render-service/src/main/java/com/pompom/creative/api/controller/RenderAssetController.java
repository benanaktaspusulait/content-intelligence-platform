package com.pompom.creative.api.controller;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.repository.RenderAssetRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read-only access to durable render assets and their media metadata. */
@RestController
@RequestMapping("/api/v1/render-assets")
public class RenderAssetController {
  private final RenderAssetRepository assets;

  public RenderAssetController(RenderAssetRepository assets) {
    this.assets = assets;
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
