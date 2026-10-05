package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "governed_rule_candidates")
public class RuleCandidateEntity {
  @Id @GeneratedValue private UUID id;
  @Column(nullable = false) private String tenantId;
  @Column(nullable = false, length = 200) private String proposedRuleKey;
  @Column(nullable = false, length = 300) private String proposedRuleName;
  @Column(nullable = false, columnDefinition = "TEXT") private String proposedDefinition;
  private String proposedFamily;
  private String proposedSeverity;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private ScopeType scopeType;
  private String scopeId;
  @Column(nullable = false, columnDefinition = "TEXT") private String hypothesis;
  @Column(columnDefinition = "TEXT") private String rationale;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private EvidenceLevel evidenceLevel;
  @Column(nullable = false) private int supportingVideoCount;
  @Column(nullable = false) private int supportingPublicationCount;
  @Column(nullable = false) private int supportingObservationCount;
  private Double effectEstimate;
  @JdbcTypeCode(SqlTypes.JSON) private Map<String, Object> confidenceInterval;
  @JdbcTypeCode(SqlTypes.JSON) private Map<String, Object> baselineComparison;
  private UUID sourceDatasetSnapshotId;
  @Column(nullable = false) private String analysisMethod;
  @Column(nullable = false) private String analysisVersion;
  private String featureSchemaVersion;
  private String modelVersion;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<String> knownConfounders;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<String> knownLimitations;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<UUID> supportingEvidenceIds;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private List<String> conflictingRuleIds;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private RiskTier riskTier;
  @Column(columnDefinition = "TEXT") private String recommendedAction;
  @Enumerated(EnumType.STRING) @Column(nullable = false) private CandidateStatus status;
  private String reviewer;
  private Instant reviewedAt;
  @Column(columnDefinition = "TEXT") private String reviewComment;
  @Version private long entityVersion;
  @CreationTimestamp @Column(nullable = false, updatable = false) private Instant createdAt;
  @UpdateTimestamp @Column(nullable = false) private Instant updatedAt;

  protected RuleCandidateEntity() {}

  public RuleCandidateEntity(
      String tenantId,
      String proposedRuleKey,
      String proposedRuleName,
      String proposedDefinition,
      String hypothesis,
      ScopeType scopeType,
      String scopeId,
      EvidenceLevel evidenceLevel,
      RiskTier riskTier,
      String analysisMethod,
      String analysisVersion) {
    this.tenantId = tenantId;
    this.proposedRuleKey = proposedRuleKey;
    this.proposedRuleName = proposedRuleName;
    this.proposedDefinition = proposedDefinition;
    this.hypothesis = hypothesis;
    this.scopeType = scopeType;
    this.scopeId = scopeId;
    this.evidenceLevel = evidenceLevel;
    this.riskTier = riskTier;
    this.analysisMethod = analysisMethod;
    this.analysisVersion = analysisVersion;
    this.status = CandidateStatus.PROPOSED;
    this.knownConfounders = List.of();
    this.knownLimitations = List.of();
    this.supportingEvidenceIds = List.of();
    this.conflictingRuleIds = List.of();
  }

  public UUID getId() { return id; }
  public String getTenantId() { return tenantId; }
  public String getProposedRuleKey() { return proposedRuleKey; }
  public String getProposedRuleName() { return proposedRuleName; }
  public String getProposedDefinition() { return proposedDefinition; }
  public ScopeType getScopeType() { return scopeType; }
  public String getScopeId() { return scopeId; }
  public EvidenceLevel getEvidenceLevel() { return evidenceLevel; }
  public CandidateStatus getStatus() { return status; }
  public RiskTier getRiskTier() { return riskTier; }
  public String getAnalysisMethod() { return analysisMethod; }
  public String getAnalysisVersion() { return analysisVersion; }
  public int getSupportingObservationCount() { return supportingObservationCount; }
  public List<UUID> getSupportingEvidenceIds() { return supportingEvidenceIds; }
  public List<String> getKnownConfounders() { return knownConfounders; }
  public void setStatus(CandidateStatus status) { this.status = status; }
  public void setReviewer(String reviewer) { this.reviewer = reviewer; }
  public void setReviewedAt(Instant reviewedAt) { this.reviewedAt = reviewedAt; }
  public void setReviewComment(String reviewComment) { this.reviewComment = reviewComment; }
  public void setSupportingObservationCount(int value) { this.supportingObservationCount = value; }
  public void setSupportingEvidenceIds(List<UUID> value) { this.supportingEvidenceIds = value; }
  public void setKnownConfounders(List<String> value) { this.knownConfounders = value; }
}
