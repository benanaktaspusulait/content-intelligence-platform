package com.pompomhills.intelligence.rulegovernance;

import java.util.Optional;
import java.util.UUID;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RulesetChangesetRepository extends JpaRepository<RulesetChangesetEntity, UUID> {
  Optional<RulesetChangesetEntity> findByTenantIdAndProposedRulesetVersion(String tenantId, String version);
  List<RulesetChangesetEntity> findByTenantIdOrderByGeneratedAtDesc(String tenantId);
}
