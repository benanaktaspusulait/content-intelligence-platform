package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "governed_rule_reviews")
@Getter
@NoArgsConstructor
public class RuleReviewEntity {
  @Id @GeneratedValue private UUID id;
  @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "candidate_id") private RuleCandidateEntity candidate;
  @Column(nullable = false) private String tenantId;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private ReviewDecision decision;
  @Column(nullable = false) private String reviewer;
  @Column(columnDefinition = "TEXT") private String reason;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private Map<String, Object> evidenceSnapshot;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private java.util.List<UUID> conflictsReviewed;
  private String resultingAction;
  @Column(nullable = false, updatable = false) private Instant createdAt = Instant.now();

  public RuleReviewEntity(
      RuleCandidateEntity candidate,
      String tenantId,
      ReviewDecision decision,
      String reviewer,
      String reason,
      Map<String, Object> evidenceSnapshot,
      java.util.List<UUID> conflictsReviewed,
      String resultingAction) {
    this.candidate = candidate;
    this.tenantId = tenantId;
    this.decision = decision;
    this.reviewer = reviewer;
    this.reason = reason;
    this.evidenceSnapshot = evidenceSnapshot == null ? Map.of() : evidenceSnapshot;
    this.conflictsReviewed = conflictsReviewed == null ? java.util.List.of() : conflictsReviewed;
    this.resultingAction = resultingAction;
  }
}
