package com.pompom.creative.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "caption_versions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CaptionVersion {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "render_asset_id", nullable = false, updatable = false)
  private UUID renderAssetId;

  @Column(nullable = false, length = 30, updatable = false)
  private String platform;

  @Column(nullable = false, columnDefinition = "TEXT", updatable = false)
  private String caption;

  @Column(columnDefinition = "TEXT", updatable = false)
  private String hashtags;

  @Column(nullable = false, length = 30, updatable = false)
  @Builder.Default
  private String source = "GENERATED";

  @Column(name = "created_by", length = 120, updatable = false)
  private String createdBy;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "entity_version", nullable = false)
  @Builder.Default
  private Integer entityVersion = 1;

  @PrePersist
  void prePersist() {
    if (createdAt == null) createdAt = Instant.now();
    if (source == null || source.isBlank()) source = "GENERATED";
    if (entityVersion == null) entityVersion = 1;
  }
}
