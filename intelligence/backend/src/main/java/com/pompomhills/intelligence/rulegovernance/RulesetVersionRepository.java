package com.pompomhills.intelligence.rulegovernance;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RulesetVersionRepository extends JpaRepository<RulesetVersionEntity, UUID> {
  Optional<RulesetVersionEntity> findByTenantIdAndRulesetVersion(String tenantId, String version);
  Optional<RulesetVersionEntity> findFirstByTenantIdAndStatusOrderByCreatedAtDesc(String tenantId, String status);
}
