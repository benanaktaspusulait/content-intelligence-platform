package com.pompomhills.intelligence.rulegovernance;

import static com.pompomhills.intelligence.rulegovernance.RuleGovernanceEnums.*;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/rule-governance")
public class RuleGovernanceController {
  private final RuleGovernanceService service;
  private final String governanceToken;

  public RuleGovernanceController(
      RuleGovernanceService service,
      @Value("${pompom.rule-governance.token:}") String governanceToken) {
    this.service = service;
    this.governanceToken = governanceToken;
  }

  @GetMapping("/candidates")
  public List<RuleCandidateEntity> candidates(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @RequestParam(required = false) CandidateStatus status) {
    requireAccess(token);
    return service.listCandidates(tenantId, status);
  }

  @GetMapping("/health")
  public List<RuleHealthEntity> health(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token) {
    requireAccess(token);
    return service.health(tenantId);
  }

  @GetMapping("/candidates/{id}")
  public RuleCandidateEntity candidate(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id) {
    requireAccess(token);
    return service.getCandidate(tenantId, id);
  }

  @PostMapping("/candidates")
  @ResponseStatus(HttpStatus.CREATED)
  public RuleCandidateEntity create(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @RequestBody CandidateRequest request) {
    requireAccess(token);
    RuleCandidateEntity candidate =
        new RuleCandidateEntity(
            tenantId,
            request.proposedRuleKey(),
            request.proposedRuleName(),
            request.proposedDefinition(),
            request.hypothesis(),
            request.scopeType(),
            request.scopeId(),
            request.evidenceLevel(),
            request.riskTier(),
            request.analysisMethod(),
            request.analysisVersion());
    candidate.setKnownConfounders(request.knownConfounders() == null ? List.of() : request.knownConfounders());
    candidate.setSupportingEvidenceIds(request.supportingEvidenceIds() == null ? List.of() : request.supportingEvidenceIds());
    return service.createCandidate(candidate);
  }

  @PostMapping("/candidates/{id}/qualify")
  public RuleCandidateEntity qualify(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id) {
    requireAccess(token);
    return service.qualify(id, tenantId);
  }

  @GetMapping("/candidates/{id}/evidence")
  public List<EvidenceResponse> evidence(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id) {
    requireAccess(token);
    return service.evidence(tenantId, id).stream()
        .map(e -> new EvidenceResponse(e.getId(), e.getEvidenceType(), e.getEvidenceLevel(), e.getMetric(), e.getSampleSize(), e.getObservedEffect(), e.getAnalysisMethod(), e.getAnalysisVersion()))
        .toList();
  }

  @PostMapping("/candidates/{id}/evidence")
  @ResponseStatus(HttpStatus.CREATED)
  public EvidenceResponse addEvidence(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id,
      @RequestBody EvidenceRequest request) {
    requireAccess(token);
    RuleCandidateEntity candidate = service.getCandidate(tenantId, id);
    RuleEvidenceEntity saved =
        service.addEvidence(
            tenantId,
            id,
            new RuleEvidenceEntity(
                candidate,
                tenantId,
                request.evidenceType(),
                request.evidenceLevel(),
                request.scopeType(),
                request.scopeId(),
                request.metric(),
                request.sampleSize(),
                request.analysisMethod(),
                request.analysisVersion()));
    return new EvidenceResponse(saved.getId(), saved.getEvidenceType(), saved.getEvidenceLevel(), saved.getMetric(), saved.getSampleSize(), saved.getObservedEffect(), saved.getAnalysisMethod(), saved.getAnalysisVersion());
  }

  @GetMapping("/candidates/{id}/conflicts")
  public List<RuleConflictEntity> conflicts(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id) {
    requireAccess(token);
    return service.conflicts(tenantId, id);
  }

  @PostMapping("/candidates/{id}/conflicts")
  @ResponseStatus(HttpStatus.CREATED)
  public RuleConflictEntity addConflict(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id,
      @RequestBody ConflictRequest request) {
    requireAccess(token);
    return service.registerConflict(tenantId, id, request.ruleKey(), request.conflictType(), request.overridePolicy());
  }

  @PostMapping("/candidates/{id}/conflicts/{conflictId}/resolve")
  public RuleConflictEntity resolveConflict(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id,
      @PathVariable UUID conflictId,
      @RequestBody ConflictResolutionRequest request) {
    requireAccess(token);
    return service.resolveConflict(tenantId, id, conflictId, request.reviewer(), request.note());
  }

  @GetMapping("/candidates/{id}/reviews")
  public List<RuleReviewEntity> reviews(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id) {
    requireAccess(token);
    return service.reviews(tenantId, id);
  }

  @PostMapping("/candidates/{id}/review")
  public RuleReviewEntity review(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id,
      @RequestBody ReviewRequest request) {
    requireAccess(token);
    return service.review(id, tenantId, request.decision(), request.reviewer(), request.reason(), request.conflictsReviewed());
  }

  @PostMapping("/candidates/{id}/activate")
  public ResponseEntity<RulesetVersionEntity> activate(
      @RequestHeader("X-Tenant-Id") String tenantId,
      @RequestHeader(value = "X-Rule-Governance-Token", required = false) String token,
      @PathVariable UUID id,
      @RequestBody ActivationRequest request) {
    requireAccess(token);
    return ResponseEntity.ok(service.activate(tenantId, id, request.parentVersion(), request.newVersion(), request.reviewer()));
  }

  private void requireAccess(String token) {
    if (governanceToken.isBlank()
        || token == null
        || !MessageDigest.isEqual(token.getBytes(StandardCharsets.UTF_8), governanceToken.getBytes(StandardCharsets.UTF_8))) {
      throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Rule governance authorization is not configured or invalid");
    }
  }

  public record CandidateRequest(String proposedRuleKey, String proposedRuleName, String proposedDefinition, String hypothesis, ScopeType scopeType, String scopeId, EvidenceLevel evidenceLevel, RiskTier riskTier, String analysisMethod, String analysisVersion, List<String> knownConfounders, List<UUID> supportingEvidenceIds) {}
  public record ReviewRequest(ReviewDecision decision, String reviewer, String reason, List<UUID> conflictsReviewed) {}
  public record ActivationRequest(String parentVersion, String newVersion, String reviewer) {}
  public record EvidenceRequest(EvidenceType evidenceType, EvidenceLevel evidenceLevel, ScopeType scopeType, String scopeId, String metric, int sampleSize, String analysisMethod, String analysisVersion) {}
  public record ConflictRequest(String ruleKey, String conflictType, OverridePolicy overridePolicy) {}
  public record ConflictResolutionRequest(String reviewer, String note) {}
  public record EvidenceResponse(UUID id, EvidenceType evidenceType, EvidenceLevel evidenceLevel, String metric, int sampleSize, Double observedEffect, String analysisMethod, String analysisVersion) {}
}
