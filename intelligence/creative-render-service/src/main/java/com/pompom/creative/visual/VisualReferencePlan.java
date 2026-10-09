package com.pompom.creative.visual;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Immutable prompt-bound planning snapshot; paid generation is never implicit in this record. */
@Entity
@Table(name = "visual_reference_plans")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VisualReferencePlan {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @OneToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "render_job_id", nullable = false, unique = true)
  private com.pompom.creative.domain.RenderJob renderJob;

  @Column(name = "content_id", nullable = false)
  private Long contentId;

  @Column(name = "prompt_version_id", nullable = false)
  private Long promptVersionId;

  @Column(name = "prompt_sha256", nullable = false, length = 64)
  private String promptSha256;

  @Column(name = "provider", nullable = false, length = 80)
  private String provider;

  @Column(name = "model", nullable = false, length = 120)
  private String model;

  @Column(name = "first_frame_status", nullable = false, length = 40)
  private String firstFrameStatus;

  @Column(name = "strategy", nullable = false, length = 60)
  private String strategy;

  @Column(name = "validation_status", nullable = false, length = 40)
  private String validationStatus;

  @Column(name = "recommendation", nullable = false, columnDefinition = "jsonb")
  private String recommendationJson;

  @Column(name = "capabilities", nullable = false, columnDefinition = "jsonb")
  private String capabilitiesJson;

  @Column(name = "cost_estimate", nullable = false, columnDefinition = "jsonb")
  private String costEstimateJson;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  @Builder.Default
  private Instant updatedAt = Instant.now();

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
