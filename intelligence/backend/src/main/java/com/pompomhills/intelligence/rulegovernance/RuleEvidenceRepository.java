package com.pompomhills.intelligence.rulegovernance;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RuleEvidenceRepository extends JpaRepository<RuleEvidenceEntity, UUID> {
  List<RuleEvidenceEntity> findByCandidateIdOrderByCreatedAtAsc(UUID candidateId);
}
