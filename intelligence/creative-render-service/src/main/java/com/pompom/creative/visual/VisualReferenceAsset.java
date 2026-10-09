package com.pompom.creative.visual;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** A role-specific image binding; a generic image is never silently treated as a first frame. */
@Entity
@Table(name = "visual_reference_assets")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VisualReferenceAsset {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "plan_id", nullable = false)
  private VisualReferencePlan plan;

  @Column(name = "role", nullable = false, length = 40)
  private String role;

  @Column(name = "source_kind", nullable = false, length = 20)
  private String sourceKind;

  @Column(name = "render_asset_id")
  private UUID renderAssetId;

  @Column(name = "canonical_key", length = 240)
  private String canonicalKey;

  @Column(name = "relative_path", columnDefinition = "TEXT")
  private String relativePath;

  @Column(name = "provider_asset_id", length = 200)
  private String providerAssetId;

  @Column(name = "sha256", length = 64)
  private String sha256;

  @Column(name = "prompt_sha256", length = 64)
  private String promptSha256;

  @Column(name = "intended_beat_id", length = 160)
  private String intendedBeatId;

  @Column(name = "intended_state", columnDefinition = "TEXT")
  private String intendedState;

  @Column(name = "validation_status", nullable = false, length = 40)
  private String validationStatus;

  @Column(name = "validation_evidence", nullable = false, columnDefinition = "jsonb")
  private String validationEvidenceJson;

  @Column(name = "accepted", nullable = false)
  private boolean accepted;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();
}
