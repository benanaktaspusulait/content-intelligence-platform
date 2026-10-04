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

  @Column(name = "content_id", nullable = false)
  private Long contentId;

  @Enumerated(EnumType.STRING)
  @Column(name = "asset_type", nullable = false, length = 20)
  private AssetType assetType;

  @Column(name = "relative_path", nullable = false, columnDefinition = "TEXT")
  private String relativePath;

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
