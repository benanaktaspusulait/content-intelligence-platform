package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "render_assets")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenderAsset {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "render_job_id", nullable = false)
  private RenderJob renderJob;

  @Column(name = "provider_job_id", length = 100)
  private String providerJobId;

  @Column(name = "provider_asset_id", length = 200)
  private String providerAssetId;

  @Column(name = "asset_source", length = 30)
  private String source;

  @Column(name = "parent_asset_id")
  private UUID parentAssetId;

  @Column(name = "character_refs", columnDefinition = "jsonb")
  private String characterRefsJson;

  @Column(name = "prompt_hash", length = 64)
  private String promptHash;

  @Column(name = "contract_hash", length = 64)
  private String contractHash;

  @Column(name = "original_width")
  private Integer originalWidth;

  @Column(name = "original_height")
  private Integer originalHeight;

  @Column(name = "final_width")
  private Integer finalWidth;

  @Column(name = "final_height")
  private Integer finalHeight;

  @Column(name = "processing_status", nullable = false, length = 30)
  @Builder.Default
  private String processingStatus = "REGISTERED";

  @Column(name = "processing_error", columnDefinition = "TEXT")
  private String processingError;

  @Column(name = "processing_attempt_count", nullable = false)
  @Builder.Default
  private Integer processingAttemptCount = 1;

  @Column(name = "credits_estimated", precision = 10, scale = 2)
  private BigDecimal creditsEstimated;

  @Column(name = "credits_actual", precision = 10, scale = 2)
  private BigDecimal creditsActual;

  @Column(name = "content_id", nullable = false)
  private Long contentId;

  @Enumerated(EnumType.STRING)
  @Column(name = "asset_type", nullable = false, length = 20)
  private AssetType assetType;

  @Column(name = "relative_path", nullable = false, columnDefinition = "TEXT")
  private String relativePath;

  @Column(name = "original_relative_path", columnDefinition = "TEXT")
  private String originalRelativePath;

  @Column(name = "original_file_size_bytes")
  private Long originalFileSizeBytes;

  @Column(name = "file_size_bytes", nullable = false)
  private Long fileSizeBytes;

  @Column(name = "duration_ms")
  private Integer durationMs;

  @Column(name = "width", nullable = false)
  private Integer width;

  @Column(name = "height", nullable = false)
  private Integer height;

  @Column(name = "frame_rate", columnDefinition = "NUMERIC(5,2)")
  private BigDecimal frameRate;

  @Column(name = "codec", length = 50)
  private String codec;

  @Column(name = "download_url", columnDefinition = "TEXT")
  private String downloadUrl;

  @Column(name = "downloaded_at", nullable = false)
  private Instant downloadedAt = Instant.now();

  @Column(name = "is_current", nullable = false)
  private Boolean isCurrent = true;

  @Column(name = "asset_version", nullable = false)
  private Integer assetVersion;

  @Column(name = "sha256", length = 64)
  private String sha256;

  @Column(name = "media_verified", nullable = false)
  private Boolean mediaVerified = false;

  @Column(name = "is_mock", nullable = false)
  private Boolean isMock = false;

  @Column(name = "quarantined", nullable = false)
  private Boolean quarantined = false;

  @Column(name = "video_id")
  private UUID videoId;

  @Column(name = "variant_id")
  private UUID variantId;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "entity_version", nullable = false)
  @Version
  private Integer entityVersion = 1;

  public enum AssetType {
    FIRST_FRAME,
    VIDEO
  }
}
