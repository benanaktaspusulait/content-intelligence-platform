package com.pompom.creative.postrender;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "post_render_rule_results")
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostRenderRuleResultEntity {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "evaluation_id", nullable = false, updatable = false)
  private PostRenderEvaluation evaluation;

  @Column(name = "rule_id", nullable = false, updatable = false)
  private String ruleId;

  @Column(name = "rule_version", nullable = false, updatable = false)
  private String ruleVersion;

  @Column(name = "ruleset_version", nullable = false, updatable = false)
  private String rulesetVersion;

  @Column(name = "stage", nullable = false, updatable = false)
  private String stage;

  @Column(name = "family", nullable = false, updatable = false)
  private String family;

  @Enumerated(EnumType.STRING)
  @Column(name = "severity", nullable = false, updatable = false)
  private PostRenderSeverity severity;

  @Enumerated(EnumType.STRING)
  @Column(name = "outcome", nullable = false, updatable = false)
  private PostRenderOutcome outcome;

  @Column(name = "message", nullable = false, columnDefinition = "TEXT", updatable = false)
  private String message;

  @Column(name = "actual_value", columnDefinition = "jsonb", updatable = false)
  private String actualValue;

  @Column(
      name = "expected_condition",
      nullable = false,
      columnDefinition = "jsonb",
      updatable = false)
  private String expectedCondition;

  @Column(
      name = "evidence_references",
      nullable = false,
      columnDefinition = "jsonb",
      updatable = false)
  private String evidenceReferences;

  @Column(name = "evaluator", nullable = false, updatable = false)
  private String evaluator;

  @Column(name = "review_required", nullable = false, updatable = false)
  private boolean reviewRequired;

  @Column(name = "evaluated_at", nullable = false, updatable = false)
  private Instant evaluatedAt;
}
