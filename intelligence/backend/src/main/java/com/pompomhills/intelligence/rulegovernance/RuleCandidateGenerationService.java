package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Converts already-normalized, tenant-scoped analysis output into governed evidence/candidates. */
@Service
public class RuleCandidateGenerationService {
  private final RuleCandidateRepository candidates;
  private final RuleEvidenceRepository evidence;

  public RuleCandidateGenerationService(RuleCandidateRepository candidates, RuleEvidenceRepository evidence) {
    this.candidates = candidates;
    this.evidence = evidence;
  }

  @Transactional
  public GenerationResult generate(GenerationRequest request) {
    if (request.observations() == null || request.observations().isEmpty()) {
      throw new IllegalArgumentException("Candidate generation requires normalized observations");
    }
    if (request.datasetSnapshotId() == null) {
      throw new IllegalArgumentException("Candidate generation requires a dataset snapshot");
    }
    RuleCandidateEntity candidate =
        candidates
            .findByTenantIdAndProposedRuleKeyAndScopeTypeAndScopeId(
                request.tenantId(), request.ruleKey(), request.scopeType(), request.scopeId())
            .orElseGet(
                () ->
                    new RuleCandidateEntity(
                        request.tenantId(),
                        request.ruleKey(),
                        request.ruleName(),
                        request.definition(),
                        request.hypothesis(),
                        request.scopeType(),
                        request.scopeId(),
                        request.evidenceLevel(),
                        request.riskTier(),
                        request.analysisMethod(),
                        request.analysisVersion()));
    candidate.setKnownConfounders(request.knownConfounders() == null ? List.of() : request.knownConfounders());
    candidate.setStatus(CandidateStatus.PROPOSED);
    candidate = candidates.save(candidate);
    List<UUID> evidenceIds = new ArrayList<>(candidate.getSupportingEvidenceIds());
    List<RuleEvidenceEntity> created = new ArrayList<>();
    for (Observation observation : request.observations()) {
      RuleEvidenceEntity item =
          new RuleEvidenceEntity(
              candidate,
              request.tenantId(),
              observation.evidenceType(),
              request.evidenceLevel(),
              request.scopeType(),
              request.scopeId(),
              observation.metric(),
              observation.sampleSize(),
              request.analysisMethod(),
              request.analysisVersion());
      item.setObservedEffect(observation.effect());
      item.setPlatform(observation.platform());
      item.setHorizon(observation.horizon());
      item.setProvenance(
          Map.of(
              "datasetSnapshotId", request.datasetSnapshotId().toString(),
              "sourceObservationKey", observation.sourceObservationKey(),
              "generatedAt", Instant.now().toString()));
      item.setConfounderControls(request.knownConfounders() == null ? List.of() : request.knownConfounders());
      RuleEvidenceEntity saved = evidence.save(item);
      evidenceIds.add(saved.getId());
      created.add(saved);
    }
    candidate.setSupportingEvidenceIds(evidenceIds);
    candidate.setSupportingObservationCount(
        created.stream().mapToInt(RuleEvidenceEntity::getSampleSize).sum());
    candidate.setStatus(CandidateStatus.PROPOSED);
    candidates.save(candidate);
    return new GenerationResult(candidate, created);
  }

  public record GenerationRequest(
      String tenantId,
      String ruleKey,
      String ruleName,
      String definition,
      String hypothesis,
      ScopeType scopeType,
      String scopeId,
      EvidenceLevel evidenceLevel,
      RiskTier riskTier,
      String analysisMethod,
      String analysisVersion,
      UUID datasetSnapshotId,
      List<String> knownConfounders,
      List<Observation> observations) {}

  public record Observation(
      String sourceObservationKey,
      EvidenceType evidenceType,
      String metric,
      int sampleSize,
      Double effect,
      String platform,
      String horizon) {}

  public record GenerationResult(RuleCandidateEntity candidate, List<RuleEvidenceEntity> evidence) {}
}
