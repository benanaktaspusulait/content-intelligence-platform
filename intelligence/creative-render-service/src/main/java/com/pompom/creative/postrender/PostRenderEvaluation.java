package com.pompom.creative.postrender;

import com.pompom.creative.domain.RenderAsset;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "post_render_evaluations")
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostRenderEvaluation {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "render_asset_id", nullable = false, updatable = false)
  private RenderAsset renderAsset;

  @Column(name = "render_attempt_id", updatable = false)
  private UUID renderAttemptId;

  @Column(name = "evidence_version", nullable = false, updatable = false)
  private String evidenceVersion;

  @Column(name = "post_render_ruleset_version", nullable = false, updatable = false)
  private String postRenderRulesetVersion;

  @Column(
      name = "analyzer_versions",
      nullable = false,
      columnDefinition = "jsonb",
      updatable = false)
  private String analyzerVersions;

  @Column(
      name = "evidence_snapshot",
      nullable = false,
      columnDefinition = "jsonb",
      updatable = false)
  private String evidenceSnapshot;

  @Enumerated(EnumType.STRING)
  @Column(name = "overall_decision", nullable = false, updatable = false)
  private PostRenderDecision overallDecision;

  @Column(name = "human_review_required", nullable = false, updatable = false)
  private boolean humanReviewRequired;

  @Column(name = "human_reviewed_at")
  private Instant humanReviewedAt;

  @Column(name = "human_reviewer")
  private String humanReviewer;

  @Column(name = "human_decision")
  private String humanDecision;

  @Column(name = "human_notes", columnDefinition = "TEXT")
  private String humanNotes;

  @Column(name = "started_at", nullable = false, updatable = false)
  private Instant startedAt;

  @Column(name = "completed_at", nullable = false, updatable = false)
  private Instant completedAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Version
  @Column(name = "entity_version", nullable = false)
  private Integer entityVersion = 1;

  public void recordHumanDecision(String reviewer, String decision, String notes) {
    if (!humanReviewRequired)
      throw new IllegalStateException("This evaluation does not require human review");
    if (humanReviewedAt != null)
      throw new IllegalStateException("This evaluation has already been reviewed");
    humanReviewedAt = Instant.now();
    humanReviewer = reviewer;
    humanDecision = decision;
    humanNotes = notes;
  }
}
