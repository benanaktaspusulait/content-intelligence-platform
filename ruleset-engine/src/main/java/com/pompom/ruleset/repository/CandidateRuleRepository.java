package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.CandidateRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface CandidateRuleRepository extends JpaRepository<CandidateRule, UUID> {
    
    List<CandidateRule> findByStatus(CandidateRule.CandidateStatus status);
    
    List<CandidateRule> findByStatusOrderByCreatedAtDesc(CandidateRule.CandidateStatus status);
}
