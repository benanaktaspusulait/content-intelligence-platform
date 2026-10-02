package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.Rule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface RuleRepository extends JpaRepository<Rule, UUID> {
    
    Optional<Rule> findByRuleCode(String ruleCode);
    
    @Query("SELECT r FROM Rule r WHERE r.active = true AND r.category = :category ORDER BY r.severity")
    List<Rule> findActiveByCategory(@Param("category") Rule.RuleCategory category);
    
    @Query("SELECT r FROM Rule r WHERE r.active = true AND r.severity IN :severities")
    List<Rule> findActiveBySeverities(@Param("severities") List<Rule.RuleSeverity> severities);
    
    List<Rule> findByActiveTrue();
}
