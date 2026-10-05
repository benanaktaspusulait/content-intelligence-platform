package com.pompomhills.intelligence.rulegovernance;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RulesetChangesetRepository extends JpaRepository<RulesetChangesetEntity, UUID> {
  Optional<RulesetChangesetEntity> findByTenantIdAndProposedRulesetVersion(String tenantId, String version);
}
