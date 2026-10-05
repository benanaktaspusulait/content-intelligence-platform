package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RuleGovernanceService {
  private final RuleCandidateRepository candidates;
  private final RuleEvidenceRepository evidence;
  private final RuleConflictRepository conflicts;
  private final RuleReviewRepository reviews;
  private final RulesetChangesetRepository changesets;
  private final RulesetVersionRepository versions;
  private final RuleHealthRepository health;

  public RuleGovernanceService(
      RuleCandidateRepository candidates,
      RuleEvidenceRepository evidence,
      RuleConflictRepository conflicts,
      RuleReviewRepository reviews,
      RulesetChangesetRepository changesets,
      RulesetVersionRepository versions,
      RuleHealthRepository health) {
    this.candidates = candidates;
    this.evidence = evidence;
    this.conflicts = conflicts;
    this.reviews = reviews;
    this.changesets = changesets;
    this.versions = versions;
    this.health = health;
  }

  public List<RuleHealthEntity> health(String tenantId) {
    return health.findByTenantIdOrderByLastEvaluatedAtDesc(tenantId);
  }

  public List<RuleCandidateEntity> listCandidates(String tenantId, CandidateStatus status) {
    return status == null
        ? candidates.findByTenantIdOrderByCreatedAtDesc(tenantId)
        : candidates.findByTenantIdAndStatusOrderByCreatedAtDesc(tenantId, status);
  }

  public RuleCandidateEntity getCandidate(String tenantId, UUID id) {
    return candidates
        .findById(id)
        .filter(candidate -> candidate.getTenantId().equals(tenantId))
        .orElseThrow(() -> new IllegalArgumentException("Rule candidate not found"));
  }

  public List<RuleEvidenceEntity> evidence(String tenantId, UUID candidateId) {
    getCandidate(tenantId, candidateId);
    return evidence.findByCandidateIdOrderByCreatedAtAsc(candidateId);
  }

  @Transactional
  public RuleEvidenceEntity addEvidence(String tenantId, UUID candidateId, RuleEvidenceEntity newEvidence) {
    RuleCandidateEntity candidate = getCandidate(tenantId, candidateId);
    if (newEvidence.getEvidenceType() == EvidenceType.OBSERVATIONAL
        && (newEvidence.getEvidenceLevel() == EvidenceLevel.CONTROLLED_EXPERIMENT
            || newEvidence.getEvidenceLevel() == EvidenceLevel.CAUSAL_EVIDENCE)) {
      throw new IllegalArgumentException("Observational evidence cannot be labelled experimental or causal");
    }
    RuleEvidenceEntity saved = evidence.save(newEvidence);
    List<UUID> ids = new java.util.ArrayList<>(candidate.getSupportingEvidenceIds());
    ids.add(saved.getId());
    candidate.setSupportingEvidenceIds(ids);
    candidate.setSupportingObservationCount(candidate.getSupportingObservationCount() + saved.getSampleSize());
    if (candidate.getStatus() == CandidateStatus.NEEDS_MORE_EVIDENCE) {
      candidate.setStatus(CandidateStatus.PROPOSED);
    }
    candidates.save(candidate);
    return saved;
  }

  public List<RuleConflictEntity> conflicts(String tenantId, UUID candidateId) {
    getCandidate(tenantId, candidateId);
    return conflicts.findByCandidateIdOrderByCreatedAtAsc(candidateId);
  }

  @Transactional
  public RuleConflictEntity registerConflict(
      String tenantId, UUID candidateId, String ruleKey, String conflictType, OverridePolicy policy) {
    RuleCandidateEntity candidate = getCandidate(tenantId, candidateId);
    return conflicts.save(new RuleConflictEntity(candidate, tenantId, ruleKey, conflictType, policy));
  }

  @Transactional
  public RuleConflictEntity resolveConflict(
      String tenantId, UUID candidateId, UUID conflictId, String reviewer, String note) {
    getCandidate(tenantId, candidateId);
    RuleConflictEntity conflict =
        conflicts.findById(conflictId)
            .filter(item -> item.getCandidate().getId().equals(candidateId))
            .orElseThrow(() -> new IllegalArgumentException("Rule conflict not found"));
    conflict.resolve(reviewer, note);
    return conflicts.save(conflict);
  }

  public List<RuleReviewEntity> reviews(String tenantId, UUID candidateId) {
    getCandidate(tenantId, candidateId);
    return reviews.findByCandidateIdOrderByCreatedAtAsc(candidateId);
  }

  @Transactional
  public RuleCandidateEntity createCandidate(RuleCandidateEntity candidate) {
    if (candidate.getSupportingEvidenceIds() == null || candidate.getSupportingEvidenceIds().isEmpty()) {
      candidate.setStatus(CandidateStatus.NEEDS_MORE_EVIDENCE);
    }
    return candidates.save(candidate);
  }

  @Transactional
  public RuleCandidateEntity qualify(UUID id, String tenantId) {
    RuleCandidateEntity candidate = getCandidate(tenantId, id);
    if (candidate.getSupportingEvidenceIds() == null || candidate.getSupportingEvidenceIds().isEmpty()) {
      throw new IllegalStateException("A candidate without evidence cannot be ready for review");
    }
    if (candidate.getEvidenceLevel() == EvidenceLevel.OBSERVED_ASSOCIATION
        && candidate.getRiskTier() == RiskTier.CRITICAL) {
      throw new IllegalStateException("Critical policy changes require stronger evidence or an experiment");
    }
    if (conflicts.countByCandidateIdAndResolutionStatus(id, "OPEN") > 0) {
      throw new IllegalStateException("Resolve candidate conflicts before review");
    }
    candidate.setStatus(CandidateStatus.READY_FOR_REVIEW);
    return candidates.save(candidate);
  }

  @Transactional
  public RuleReviewEntity review(
      UUID id,
      String tenantId,
      ReviewDecision decision,
      String reviewer,
      String reason,
      List<UUID> conflictsReviewed) {
    RuleCandidateEntity candidate = getCandidate(tenantId, id);
    if (candidate.getStatus() != CandidateStatus.READY_FOR_REVIEW) {
      throw new IllegalStateException("Only READY_FOR_REVIEW candidates can be reviewed");
    }
    if (decision == ReviewDecision.APPROVE || decision == ReviewDecision.SUPERSEDE_EXISTING_RULE) {
      candidate.setStatus(CandidateStatus.APPROVED);
    } else if (decision == ReviewDecision.REJECT) {
      candidate.setStatus(CandidateStatus.REJECTED);
    } else if (decision == ReviewDecision.REQUIRE_EXPERIMENT) {
      candidate.setStatus(CandidateStatus.EXPERIMENT_REQUIRED);
    } else {
      candidate.setStatus(CandidateStatus.NEEDS_MORE_EVIDENCE);
    }
    candidate.setReviewer(reviewer);
    candidate.setReviewedAt(Instant.now());
    candidate.setReviewComment(reason);
    candidates.save(candidate);
    return reviews.save(
        new RuleReviewEntity(
            candidate,
            tenantId,
            decision,
            reviewer,
            reason,
            Map.of("candidateStatus", candidate.getStatus().name()),
            conflictsReviewed,
            decision.name()));
  }

  @Transactional
  public RulesetVersionEntity activate(
      String tenantId, UUID candidateId, String parentVersion, String newVersion, String reviewer) {
    RuleCandidateEntity candidate = getCandidate(tenantId, candidateId);
    if (candidate.getStatus() != CandidateStatus.APPROVED) {
      throw new IllegalStateException("Only approved candidates can create an active ruleset");
    }
    if (conflicts.countByCandidateIdAndResolutionStatus(candidateId, "OPEN") > 0) {
      throw new IllegalStateException("Resolve candidate conflicts before activation");
    }
    if (versions.findByTenantIdAndRulesetVersion(tenantId, newVersion).isPresent()) {
      throw new IllegalStateException("Ruleset version already exists");
    }
    RulesetChangesetEntity changeset =
        changesets.save(new RulesetChangesetEntity(tenantId, parentVersion, newVersion, List.of(candidateId)));
    changeset.setStatus(ChangesetStatus.VALIDATED);
    changeset.setStatus(ChangesetStatus.APPROVED);
    changesets.save(changeset);
    RulesetVersionEntity version =
        versions.save(
            new RulesetVersionEntity(
                tenantId,
                newVersion,
                parentVersion,
                changeset,
                Map.of("candidateId", candidateId.toString(), "parentVersion", parentVersion)));
    version.activate(reviewer);
    changeset.setStatus(ChangesetStatus.ACTIVATED);
    changeset.setActivatedAt(Instant.now());
    changeset.setActivatedBy(reviewer);
    changesets.save(changeset);
    candidate.setStatus(CandidateStatus.SUPERSEDED);
    candidates.save(candidate);
    return versions.save(version);
  }
}
