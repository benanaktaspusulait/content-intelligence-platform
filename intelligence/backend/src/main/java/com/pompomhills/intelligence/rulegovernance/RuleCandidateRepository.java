package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RuleCandidateRepository extends JpaRepository<RuleCandidateEntity, UUID> {
  List<RuleCandidateEntity> findByTenantIdOrderByCreatedAtDesc(String tenantId);
  List<RuleCandidateEntity> findByTenantIdAndStatusOrderByCreatedAtDesc(String tenantId, CandidateStatus status);
  Optional<RuleCandidateEntity> findByTenantIdAndProposedRuleKeyAndScopeTypeAndScopeId(
      String tenantId, String key, ScopeType scopeType, String scopeId);
}
