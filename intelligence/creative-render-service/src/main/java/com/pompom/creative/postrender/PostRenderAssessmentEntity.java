package com.pompom.creative.postrender;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "post_render_assessments")
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostRenderAssessmentEntity {
  @Id @GeneratedValue(strategy = GenerationType.UUID) private UUID id;

  @OneToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "evaluation_id", nullable = false, unique = true, updatable = false)
  private PostRenderEvaluation evaluation;

  @Column(name = "grade", nullable = false, length = 20, updatable = false)
  private String grade;
  @Column(name = "label", nullable = false, length = 120, updatable = false)
  private String label;
  @Column(name = "verdict", nullable = false, columnDefinition = "TEXT", updatable = false)
  private String verdict;
  @Column(name = "evidence_coverage_percent", nullable = false, updatable = false)
  private Integer evidenceCoveragePercent;
  @Column(name = "assessment_version", nullable = false, length = 80, updatable = false)
  private String assessmentVersion;
  @Column(name = "snapshot", nullable = false, columnDefinition = "jsonb", updatable = false)
  private String snapshot;
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();
}
