package com.pompomhills.intelligence.rulegovernance;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RuleConflictRepository extends JpaRepository<RuleConflictEntity, UUID> {
  List<RuleConflictEntity> findByCandidateIdOrderByCreatedAtAsc(UUID candidateId);
  long countByCandidateIdAndResolutionStatus(UUID candidateId, String status);
}
