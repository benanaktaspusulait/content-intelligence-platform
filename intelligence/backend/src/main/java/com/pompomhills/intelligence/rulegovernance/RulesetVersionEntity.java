package com.pompomhills.intelligence.rulegovernance;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "governed_ruleset_versions")
@Getter
@NoArgsConstructor
public class RulesetVersionEntity {
  @Id @GeneratedValue private UUID id;
  @Column(nullable = false) private String tenantId;
  @Column(nullable = false) private String rulesetVersion;
  private String parentRulesetVersion;
  @OneToOne(fetch = FetchType.LAZY) @JoinColumn(name = "source_changeset_id") private RulesetChangesetEntity sourceChangeset;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private Map<String, Object> rulesDocument;
  @Column(nullable = false) private String status;
  private Instant activatedAt;
  private String activatedBy;
  @Column(nullable = false, updatable = false) private Instant createdAt = Instant.now();

  public RulesetVersionEntity(String tenantId, String rulesetVersion, String parent, RulesetChangesetEntity source, Map<String, Object> document) {
    this.tenantId = tenantId;
    this.rulesetVersion = rulesetVersion;
    this.parentRulesetVersion = parent;
    this.sourceChangeset = source;
    this.rulesDocument = document;
    this.status = "VALIDATED";
  }
  public void activate(String reviewer) {
    this.status = "ACTIVE";
    this.activatedAt = Instant.now();
    this.activatedBy = reviewer;
  }
}
