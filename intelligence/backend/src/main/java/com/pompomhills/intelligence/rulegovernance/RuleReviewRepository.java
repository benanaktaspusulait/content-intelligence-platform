package com.pompomhills.intelligence.rulegovernance;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RuleReviewRepository extends JpaRepository<RuleReviewEntity, UUID> {
  List<RuleReviewEntity> findByCandidateIdOrderByCreatedAtAsc(UUID candidateId);
}
