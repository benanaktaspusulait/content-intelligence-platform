package com.pompomhills.intelligence.rulegovernance;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RuleHealthRepository extends JpaRepository<RuleHealthEntity, UUID> {
  List<RuleHealthEntity> findByTenantIdOrderByLastEvaluatedAtDesc(String tenantId);
}
