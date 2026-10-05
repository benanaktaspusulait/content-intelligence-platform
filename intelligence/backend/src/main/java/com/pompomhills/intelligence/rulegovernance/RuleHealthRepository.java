package com.pompomhills.intelligence.rulegovernance;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import java.time.Instant;

public interface RuleHealthRepository extends JpaRepository<RuleHealthEntity, UUID> {
  List<RuleHealthEntity> findByTenantIdOrderByLastEvaluatedAtDesc(String tenantId);
  Optional<RuleHealthEntity> findByTenantIdAndRuleKeyAndRulesetVersionAndScopeTypeAndScopeId(
      String tenantId, String ruleKey, String rulesetVersion, RuleGovernanceEnums.ScopeType scopeType, String scopeId);
  List<RuleHealthEntity> findByReviewDueAtBeforeAndStatusNot(Instant now, RuleGovernanceEnums.RuleHealthStatus status);
}
