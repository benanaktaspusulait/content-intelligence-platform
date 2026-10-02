package com.pompom.creative.rulemining;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface RuleCandidateRepository extends JpaRepository<RuleCandidate, UUID> {

  List<RuleCandidate> findByRuleType(RuleCandidate.RuleType ruleType);

  List<RuleCandidate> findByRuleCategory(RuleCandidate.RuleCategory category);

  List<RuleCandidate> findByValidationStatus(RuleCandidate.ValidationStatus status);

  @Query(
      "SELECT r FROM RuleCandidate r WHERE r.confidence >= :minConfidence "
          + "ORDER BY r.confidence DESC")
  List<RuleCandidate> findHighConfidenceRules(@Param("minConfidence") BigDecimal minConfidence);

  @Query(
      "SELECT r FROM RuleCandidate r WHERE r.isActionable = true "
          + "AND r.validationStatus IN ('CANDIDATE', 'VALIDATED', 'IN_USE') "
          + "ORDER BY r.confidence DESC")
  List<RuleCandidate> findActionableRules();

  @Query(
      "SELECT r FROM RuleCandidate r WHERE r.miningRunId = :runId " + "ORDER BY r.confidence DESC")
  List<RuleCandidate> findByMiningRunId(@Param("runId") UUID runId);

  @Query(
      "SELECT r FROM RuleCandidate r WHERE r.supportCount >= :minSupport "
          + "AND r.confidence >= :minConfidence "
          + "ORDER BY r.confidence DESC, r.supportCount DESC")
  List<RuleCandidate> findReliableRules(
      @Param("minSupport") int minSupport, @Param("minConfidence") BigDecimal minConfidence);
}
