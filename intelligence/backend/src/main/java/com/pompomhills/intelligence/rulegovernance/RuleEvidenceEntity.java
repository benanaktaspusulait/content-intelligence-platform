package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "governed_rule_evidence")
@Getter
@NoArgsConstructor
public class RuleEvidenceEntity {
  @Id @GeneratedValue private UUID id;
  @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "candidate_id") private RuleCandidateEntity candidate;
  @Column(nullable = false) private String tenantId;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private EvidenceType evidenceType;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private EvidenceLevel evidenceLevel;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private ScopeType scopeType;
  private String scopeId;
  private UUID datasetSnapshotId;
  private UUID videoId;
  private UUID variantId;
  private UUID publicationId;
  @Column(nullable = false) private String metric;
  private String horizon;
  private Double observedEffect;
  @JdbcTypeCode(SqlTypes.JSON) private Map<String, Object> uncertainty;
  @Column(nullable = false) private int sampleSize;
  private Instant periodStart;
  private Instant periodEnd;
  private String platform;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private Map<String, Object> provenance;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private java.util.List<String> confounderControls;
  @Column(nullable = false) private String analysisMethod;
  @Column(nullable = false) private String analysisVersion;
  private String featureSchemaVersion;
  private String modelVersion;
  @CreationTimestamp @Column(nullable = false, updatable = false) private Instant createdAt;

  public RuleEvidenceEntity(
      RuleCandidateEntity candidate,
      String tenantId,
      EvidenceType evidenceType,
      EvidenceLevel evidenceLevel,
      ScopeType scopeType,
      String scopeId,
      String metric,
      int sampleSize,
      String analysisMethod,
      String analysisVersion) {
    this.candidate = candidate;
    this.tenantId = tenantId;
    this.evidenceType = evidenceType;
    this.evidenceLevel = evidenceLevel;
    this.scopeType = scopeType;
    this.scopeId = scopeId;
    this.metric = metric;
    this.sampleSize = sampleSize;
    this.analysisMethod = analysisMethod;
    this.analysisVersion = analysisVersion;
    this.provenance = Map.of();
    this.confounderControls = java.util.List.of();
  }

  public void setObservedEffect(Double observedEffect) { this.observedEffect = observedEffect; }
  public void setUncertainty(Map<String, Object> uncertainty) { this.uncertainty = uncertainty; }
  public void setPlatform(String platform) { this.platform = platform; }
  public void setHorizon(String horizon) { this.horizon = horizon; }
  public void setProvenance(Map<String, Object> provenance) { this.provenance = provenance; }
  public void setConfounderControls(java.util.List<String> controls) { this.confounderControls = controls; }
}
