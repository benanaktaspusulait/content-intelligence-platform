package com.pompomhills.intelligence.quality;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/** Append-only, explicit visual-gate evidence. The parent quality validation is never mutated. */
@Entity
@Table(name = "quality_validation_visual_evidence")
@Getter
@Setter
@NoArgsConstructor
public class ValidationVisualEvidenceEntity {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "validation_record_id", nullable = false, updatable = false)
  private Long validationRecordId;

  @Column(name = "content_id", nullable = false, updatable = false)
  private Long contentId;

  @Column(name = "prompt_version_id", nullable = false, updatable = false)
  private Long promptVersionId;

  @Column(name = "prompt_sha256", nullable = false, updatable = false, length = 64)
  private String promptSha256;

  @Column(name = "visual_gate", nullable = false, updatable = false, length = 32)
  private String visualGate;

  @Column(name = "status", nullable = false, updatable = false, length = 16)
  private String status;

  @Column(name = "evidence_set_id", updatable = false)
  private UUID evidenceSetId;

  @Column(name = "render_job_id", updatable = false)
  private UUID renderJobId;

  @Column(name = "render_asset_id", updatable = false)
  private UUID renderAssetId;

  @Column(name = "asset_type", updatable = false, length = 32)
  private String assetType;

  @Column(name = "asset_relative_path", updatable = false)
  private String assetRelativePath;

  @Column(name = "asset_sha256", updatable = false, length = 64)
  private String assetSha256;

  @Column(name = "provenance_json", columnDefinition = "jsonb", updatable = false)
  private String provenanceJson;

  @Column(name = "reason", nullable = false, updatable = false, columnDefinition = "TEXT")
  private String reason;

  @Column(name = "verification_id", updatable = false, length = 200)
  private String verificationId;

  @Column(name = "verified_at", updatable = false)
  private Instant verifiedAt;

  @Column(name = "submission_key", nullable = false, updatable = false, unique = true, length = 200)
  private String submissionKey;

  @Column(name = "submitted_at", nullable = false, updatable = false)
  private Instant submittedAt;
}
