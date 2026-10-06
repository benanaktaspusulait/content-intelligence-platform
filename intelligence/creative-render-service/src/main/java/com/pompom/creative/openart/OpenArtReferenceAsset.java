package com.pompom.creative.openart;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "openart_reference_assets")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OpenArtReferenceAsset {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "canonical_key", nullable = false, length = 160)
  private String canonicalKey;

  @Column(name = "display_name", nullable = false, length = 240)
  private String displayName;

  @Enumerated(EnumType.STRING)
  @Column(name = "source", nullable = false, length = 30)
  private ReferenceSource source;

  @Column(name = "media_type", nullable = false, length = 30)
  private String mediaType;

  @Column(name = "provider_asset_id", length = 200)
  private String providerAssetId;

  @Column(name = "provider_url", columnDefinition = "TEXT")
  private String providerUrl;

  @Column(name = "local_path", columnDefinition = "TEXT")
  private String localPath;

  @Column(name = "sha256", length = 64)
  private String sha256;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 30)
  @Builder.Default
  private ReferenceStatus status = ReferenceStatus.AVAILABLE;

  @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
  @Column(name = "metadata", columnDefinition = "jsonb")
  private String metadataJson;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

  public enum ReferenceSource {
    LOCAL,
    OPENART_WORKSPACE
  }

  public enum ReferenceStatus {
    AVAILABLE,
    MISSING,
    UNSUPPORTED,
    ERROR
  }

  @jakarta.persistence.PrePersist
  void prePersist() {
    Instant now = Instant.now();
    if (createdAt == null) createdAt = now;
    if (updatedAt == null) updatedAt = now;
  }

  @jakarta.persistence.PreUpdate
  void preUpdate() {
    updatedAt = Instant.now();
  }
}
