package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;
import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Deterministic no-network fixture for the published-observation-to-new-ruleset contract. */
class RuleEvolutionIntegrationFixtureTest {
  @Test
  void publishedObservationBecomesEvidenceThenNewImmutableRuleset() {
    Map<String, Object> original =
        Map.of("version", "1.3", "rules", List.of(Map.of("id", "HOOK_001", "definition", "legacy")));
    UUID evidenceId = UUID.randomUUID();
    RuleCandidateEntity candidate =
        new RuleCandidateEntity(
            "tenant-a",
            "HOOK_001",
            "Opening problem legibility",
            "first frame contains a readable problem",
            "legible hooks improve measured 24h views",
            ScopeType.BRAND_OR_ACCOUNT,
            "pompom-hills",
            EvidenceLevel.SUPPORTED_PATTERN,
            RiskTier.MEDIUM,
            "normalized-performance-pattern",
            "v1");
    candidate.setSupportingEvidenceIds(List.of(evidenceId));
    candidate.setSupportingObservationCount(12);
    candidate.setStatus(CandidateStatus.READY_FOR_REVIEW);

    RuleReviewEntity review =
        new RuleReviewEntity(
            candidate,
            "tenant-a",
            ReviewDecision.APPROVE,
            "creative-lead",
            "Repeated across the locked dataset snapshot",
            Map.of("datasetSnapshotId", "snapshot-001"),
            List.of(),
            "CREATE_RULESET_CHANGESET");
    candidate.setStatus(CandidateStatus.APPROVED);

    RulesetChangesetEntity changeset =
        new RulesetChangesetEntity("tenant-a", "1.3", "1.4", List.of(evidenceId));
    RulesetVersionEntity next =
        new RulesetVersionEntity(
            "tenant-a",
            "1.4",
            "1.3",
            changeset,
            Map.of("version", "1.4", "parent", "1.3", "candidate", candidate.getProposedRuleKey()));
    next.activate(review.getReviewer());

    assertThat(original.get("version")).isEqualTo("1.3");
    assertThat(next.getRulesetVersion()).isEqualTo("1.4");
    assertThat(next.getParentRulesetVersion()).isEqualTo("1.3");
    assertThat(next.getStatus()).isEqualTo("ACTIVE");
    assertThat(candidate.getStatus()).isEqualTo(CandidateStatus.APPROVED);
  }
}
