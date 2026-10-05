package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "governed_rule_conflicts")
@Getter
@NoArgsConstructor
public class RuleConflictEntity {
  @Id @GeneratedValue private UUID id;
  @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "candidate_id") private RuleCandidateEntity candidate;
  @Column(nullable = false) private String tenantId;
  @Column(nullable = false) private String conflictingRuleKey;
  @Column(nullable = false) private String conflictType;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private ScopeType candidateScopeType;
  private String candidateScopeId;
  @Enumerated(EnumType.STRING) private ScopeType existingScopeType;
  private String existingScopeId;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private OverridePolicy overridePolicy;
  @Column(nullable = false) private String resolutionStatus = "OPEN";
  @Column(columnDefinition = "TEXT") private String resolutionNote;
  private String resolvedBy;
  private Instant resolvedAt;
  @Column(nullable = false, updatable = false) private Instant createdAt = Instant.now();

  public RuleConflictEntity(
      RuleCandidateEntity candidate,
      String tenantId,
      String conflictingRuleKey,
      String conflictType,
      OverridePolicy overridePolicy) {
    this.candidate = candidate;
    this.tenantId = tenantId;
    this.conflictingRuleKey = conflictingRuleKey;
    this.conflictType = conflictType;
    this.candidateScopeType = candidate.getScopeType();
    this.candidateScopeId = candidate.getScopeId();
    this.overridePolicy = overridePolicy;
  }

  public void resolve(String reviewer, String note) {
    this.resolutionStatus = "RESOLVED";
    this.resolvedBy = reviewer;
    this.resolutionNote = note;
    this.resolvedAt = Instant.now();
  }
}
