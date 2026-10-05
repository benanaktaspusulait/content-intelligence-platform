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
@Table(name = "governed_rule_health")
@Getter
@NoArgsConstructor
public class RuleHealthEntity {
  @Id @GeneratedValue private UUID id;
  @Column(nullable = false) private String tenantId;
  @Column(nullable = false) private String ruleKey;
  @Column(nullable = false) private String rulesetVersion;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private ScopeType scopeType;
  private String scopeId;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private RuleHealthStatus status;
  private Instant firstSupportedAt;
  private Instant lastSupportedAt;
  private Instant lastEvaluatedAt;
  @Column(nullable = false) private int currentSupportingSampleSize;
  private String supportTrend;
  private Double currentEffectEstimate;
  private Instant reviewDueAt;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private Map<String, Object> details;

  public RuleHealthEntity(String tenantId, String ruleKey, String rulesetVersion, ScopeType scopeType, String scopeId) {
    this.tenantId = tenantId;
    this.ruleKey = ruleKey;
    this.rulesetVersion = rulesetVersion;
    this.scopeType = scopeType;
    this.scopeId = scopeId;
    this.status = RuleHealthStatus.ACTIVE;
    this.details = Map.of();
  }

  public void revalidate(int sampleSize, Double effect, RuleHealthStatus nextStatus, String trend, Instant now) {
    if (firstSupportedAt == null) firstSupportedAt = now;
    lastSupportedAt = now;
    lastEvaluatedAt = now;
    currentSupportingSampleSize = sampleSize;
    currentEffectEstimate = effect;
    supportTrend = trend;
    status = nextStatus;
  }

  public void markRevalidationRequired() {
    if (status != RuleHealthStatus.SUPERSEDED && status != RuleHealthStatus.RETIRED) {
      status = RuleHealthStatus.REVALIDATION_REQUIRED;
    }
  }
}
