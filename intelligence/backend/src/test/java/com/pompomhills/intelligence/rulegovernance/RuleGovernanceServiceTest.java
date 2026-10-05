package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RuleGovernanceServiceTest {
  @Mock private RuleCandidateRepository candidates;
  @Mock private RuleEvidenceRepository evidence;
  @Mock private RuleConflictRepository conflicts;
  @Mock private RuleReviewRepository reviews;
  @Mock private RulesetChangesetRepository changesets;
  @Mock private RulesetVersionRepository versions;
  @Mock private RuleHealthRepository health;
  private RuleGovernanceService service;
  private RuleCandidateEntity candidate;

  @BeforeEach
  void setUp() {
    service = new RuleGovernanceService(candidates, evidence, conflicts, reviews, changesets, versions, health);
    candidate = new RuleCandidateEntity("tenant-a", "HOOK_001", "Hook", "first frame is legible", "legibility improves retention", ScopeType.GLOBAL, null, EvidenceLevel.OBSERVED_ASSOCIATION, RiskTier.MEDIUM, "correlation", "1");
    when(candidates.findById(any())).thenReturn(Optional.of(candidate));
    when(conflicts.countByCandidateIdAndResolutionStatus(any(), eq("OPEN"))).thenReturn(0L);
    when(candidates.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
  }

  @Test
  void candidateWithoutEvidenceCannotBecomeReadyForReview() {
    assertThatThrownBy(() -> service.qualify(UUID.randomUUID(), "tenant-a"))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("without evidence");
  }

  @Test
  void observationalEvidenceCannotClaimCausalMaturity() {
    RuleEvidenceEntity causal = new RuleEvidenceEntity(candidate, "tenant-a", EvidenceType.OBSERVATIONAL, EvidenceLevel.CAUSAL_EVIDENCE, ScopeType.GLOBAL, null, "views_24h", 10, "correlation", "1");
    assertThatThrownBy(() -> service.addEvidence("tenant-a", UUID.randomUUID(), causal))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("cannot be labelled");
    verify(evidence, never()).save(any());
  }

  @Test
  void rejectedCandidateCannotBeActivated() {
    candidate.setStatus(CandidateStatus.REJECTED);
    assertThatThrownBy(() -> service.activate("tenant-a", UUID.randomUUID(), "1.3", "1.4", "reviewer"))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("approved");
    verify(changesets, never()).save(any());
  }
}
