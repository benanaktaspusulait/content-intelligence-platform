package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "governed_ruleset_changesets")
@Getter
@NoArgsConstructor
public class RulesetChangesetEntity {
  @Id @GeneratedValue private UUID id;
  @Column(nullable = false) private String tenantId;
  @Column(nullable = false) private String parentRulesetVersion;
  @Column(nullable = false) private String proposedRulesetVersion;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private ChangesetStatus status;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<String> addedRules;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<String> modifiedRules;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<String> retiredRules;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<UUID> candidateIds;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<UUID> approvalIds;
  @Column(nullable = false, updatable = false) private Instant generatedAt = Instant.now();
  private Instant activatedAt;
  private String activatedBy;
  @JdbcTypeCode(SqlTypes.JSON) private Map<String, Object> validationSummary;

  public RulesetChangesetEntity(String tenantId, String parentRulesetVersion, String proposedRulesetVersion, List<UUID> candidateIds) {
    this.tenantId = tenantId;
    this.parentRulesetVersion = parentRulesetVersion;
    this.proposedRulesetVersion = proposedRulesetVersion;
    this.candidateIds = candidateIds;
    this.status = ChangesetStatus.DRAFT;
    this.addedRules = List.of();
    this.modifiedRules = List.of();
    this.retiredRules = List.of();
    this.approvalIds = List.of();
  }
  public void setStatus(ChangesetStatus status) { this.status = status; }
  public void setActivatedAt(Instant value) { this.activatedAt = value; }
  public void setActivatedBy(String value) { this.activatedBy = value; }
  public UUID getId() { return id; }
}
