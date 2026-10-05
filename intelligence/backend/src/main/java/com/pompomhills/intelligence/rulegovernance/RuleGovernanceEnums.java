package com.pompomhills.intelligence.rulegovernance;

public final class RuleGovernanceEnums {
  private RuleGovernanceEnums() {}

  public enum CandidateStatus {
    PROPOSED,
    NEEDS_MORE_EVIDENCE,
    EXPERIMENT_REQUIRED,
    READY_FOR_REVIEW,
    APPROVED,
    REJECTED,
    SUPERSEDED,
    WITHDRAWN
  }

  public enum EvidenceLevel {
    OBSERVED_ASSOCIATION,
    SUPPORTED_PATTERN,
    CONTROLLED_EXPERIMENT,
    CAUSAL_EVIDENCE
  }

  public enum EvidenceType {
    OBSERVATIONAL,
    SUPPORTED_PATTERN,
    CONTROLLED_EXPERIMENT,
    CAUSAL_ANALYSIS
  }

  public enum ScopeType {
    GLOBAL,
    INDUSTRY_OR_DOMAIN,
    BRAND_OR_ACCOUNT,
    CONTENT_FAMILY
  }

  public enum OverridePolicy {
    OVERRIDABLE,
    REQUIRES_APPROVAL,
    NON_OVERRIDABLE
  }

  public enum RiskTier {
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL
  }

  public enum ReviewDecision {
    APPROVE,
    REJECT,
    REQUEST_MORE_EVIDENCE,
    REQUIRE_EXPERIMENT,
    SUPERSEDE_EXISTING_RULE
  }

  public enum ChangesetStatus {
    DRAFT,
    VALIDATED,
    APPROVED,
    ACTIVATED,
    REJECTED
  }

  public enum RuleHealthStatus {
    ACTIVE,
    EVIDENCE_WEAKENING,
    REVALIDATION_REQUIRED,
    SUPERSEDED,
    RETIRED
  }
}
