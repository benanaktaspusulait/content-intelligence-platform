package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "render_qa_results")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenderQaResult {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "render_asset_id", nullable = false)
  private RenderAsset renderAsset;

  @Column(name = "prompt_version_id", nullable = false)
  private Long promptVersionId;

  @Enumerated(EnumType.STRING)
  @Column(name = "decision", nullable = false, length = 30)
  private QaDecision decision;

  @Column(name = "decision_reason", nullable = false, columnDefinition = "TEXT")
  private String decisionReason;

  @Column(name = "confidence", precision = 3, scale = 2)
  private BigDecimal confidence;

  @Column(name = "compliance_score", nullable = false)
  private Integer complianceScore;

  @Column(name = "compliance_issues", columnDefinition = "jsonb")
  private String complianceIssues;

  @Column(name = "has_dead_air", nullable = false)
  private Boolean hasDeadAir;

  @Column(name = "dead_air_segments", columnDefinition = "jsonb")
  private String deadAirSegments;

  @Column(name = "character_identity_verified", nullable = false)
  private Boolean characterIdentityVerified;

  @Column(name = "character_identity_issues", columnDefinition = "TEXT")
  private String characterIdentityIssues;

  @Column(name = "physics_consistent", nullable = false)
  private Boolean physicsConsistent;

  @Column(name = "physics_violations", columnDefinition = "TEXT")
  private String physicsViolations;

  @Column(name = "has_object_duplication", nullable = false)
  private Boolean hasObjectDuplication;

  @Column(name = "duplication_details", columnDefinition = "TEXT")
  private String duplicationDetails;

  @Column(name = "final_execution_score")
  private Integer finalExecutionScore;

  @Column(name = "final_execution_issues", columnDefinition = "TEXT")
  private String finalExecutionIssues;

  @Column(name = "requires_human_review", nullable = false)
  private Boolean requiresHumanReview = false;

  @Column(name = "human_reviewed_at")
  private Instant humanReviewedAt;

  @Column(name = "human_reviewer", length = 50)
  private String humanReviewer;

  @Column(name = "human_decision", length = 30)
  private String humanDecision;

  @Column(name = "human_notes", columnDefinition = "TEXT")
  private String humanNotes;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "entity_version", nullable = false)
  @Version
  private Integer entityVersion = 1;

  public enum QaDecision {
    ACCEPT,
    RERENDER,
    ABANDON
  }
}
