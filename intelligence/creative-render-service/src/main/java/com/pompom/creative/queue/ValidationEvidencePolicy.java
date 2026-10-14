package com.pompom.creative.queue;

import com.pompom.creative.evidence.ValidationEvidenceDto;
import java.time.Instant;
import java.math.BigDecimal;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Enforces every hard precondition from the design doc (Slice B item 5, "Enforce immutable
 * validation evidence") before a render job may be queued. {@link #validate} returns normally only
 * when every predicate passes; otherwise it throws {@link ValidationEvidenceRejectedException} with
 * a stable {@code errorCode}. The caller ({@code RenderJobQueueService}) must create zero rows when
 * this method throws.
 *
 * <p>Order matters only for which single error code is reported first when multiple predicates
 * fail; every predicate is still independently enforced and tested.
 */
@Component
public class ValidationEvidencePolicy {

  @Value("${pompom.openart.cost.first-frame-usd:0}")
  private BigDecimal firstFrameCostUsd = BigDecimal.ZERO;

  public void validate(QueueRenderJobRequest request, ValidationEvidenceDto evidence, Instant now) {
    boolean firstFrame =
        request.jobType() == com.pompom.creative.domain.RenderJob.JobType.FIRST_FRAME;
    if (!firstFrame && !"RENDER_READY".equals(evidence.status())) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_NOT_RENDER_READY",
          "Validation record %d has status %s, not RENDER_READY"
              .formatted(evidence.validationRecordId(), evidence.status()));
    }
    if (firstFrame && !evidence.firstFrameEligible()) {
      throw new ValidationEvidenceRejectedException(
          "FIRST_FRAME_NOT_ELIGIBLE",
          "Validation record %d has no eligible prompt-stage first-frame decision"
              .formatted(evidence.validationRecordId()));
    }
    if (firstFrame) {
      Object params = request.openartParams() == null ? null : request.openartParams().get("paidCallAuthorization");
      Object ceilingValue = request.openartParams() == null ? null : request.openartParams().get("maxCostUsd");
      BigDecimal ceiling = decimal(ceilingValue);
      if (!Boolean.TRUE.equals(params) || ceiling == null || ceiling.signum() <= 0) {
        throw new ValidationEvidenceRejectedException(
            "FIRST_FRAME_PAID_CALL_NOT_AUTHORIZED",
            "First-frame generation requires explicit paid-call authorization and a positive USD ceiling");
      }
      if (firstFrameCostUsd == null || firstFrameCostUsd.signum() <= 0) {
        throw new ValidationEvidenceRejectedException(
            "FIRST_FRAME_USD_ESTIMATE_UNAVAILABLE",
            "First-frame provider cost cannot be compared with the USD ceiling; generation is disabled");
      }
      if (ceiling.compareTo(firstFrameCostUsd) < 0) {
        throw new ValidationEvidenceRejectedException(
            "FIRST_FRAME_COST_EXCEEDS_CEILING",
            "The configured first-frame estimate exceeds the authorized USD ceiling");
      }
    }
    boolean governed = !firstFrame && hasCompleteGovernedAdmission(evidence);
    if (!firstFrame && evidence.blockerCount() > 0 && !governed) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_HAS_BLOCKERS",
          "Validation record %d has %d blocker(s)"
              .formatted(evidence.validationRecordId(), evidence.blockerCount()));
    }
    if (!firstFrame && evidence.criticalCount() > 0 && !governed) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_HAS_CRITICALS",
          "Validation record %d has %d critical(s)"
              .formatted(evidence.validationRecordId(), evidence.criticalCount()));
    }
    if (!firstFrame
        && (evidence.independentRevalidationId() == null
            || evidence.independentlyRevalidatedAt() == null)) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_NOT_INDEPENDENTLY_REVALIDATED",
          "Validation record %d has no independent revalidation"
              .formatted(evidence.validationRecordId()));
    }
    if (evidence.contentId() != request.contentId()
        || evidence.promptVersionId() != request.promptVersionId()) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_IDENTITY_MISMATCH",
          "Validation record %d is linked to content %d/prompt version %d, not the requested %d/%d"
              .formatted(
                  evidence.validationRecordId(),
                  evidence.contentId(),
                  evidence.promptVersionId(),
                  request.contentId(),
                  request.promptVersionId()));
    }
    if (evidence.promptSha256() == null || !evidence.promptSha256().matches("^[0-9a-f]{64}$")) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_PROMPT_HASH_INVALID",
          "Validation record %d has a missing or malformed prompt hash"
              .formatted(evidence.validationRecordId()));
    }
    if (request.requestPromptSha256() != null
        && !request.requestPromptSha256().equals(evidence.promptSha256())) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_PROMPT_HASH_MISMATCH",
          "Validation record %d's prompt hash does not match the request's expected hash"
              .formatted(evidence.validationRecordId()));
    }
    // producibilityValidatorVersion is deliberately NOT checked here: AI producibility
    // validation (PRODUCIBILITY_001/002/003) is a family of ordinary deterministic rules in
    // the versioned ruleset, already fully identified by deterministicRulesetVersion above -
    // there is no independent "producibility validator" runtime with its own version axis.
    // Requiring this field would mean either rejecting every otherwise-complete evidence
    // record (since nothing can honestly populate it) or inventing a fabricated value just to
    // pass this check - both are worse than not checking it at all.
    if (evidence.deterministicRulesetVersion() == null
        || evidence.semanticProvider() == null
        || evidence.semanticModelVersion() == null) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_VERSIONS_INCOMPLETE",
          "Validation record %d is missing a required ruleset/semantic version identity"
              .formatted(evidence.validationRecordId()));
    }
    if (evidence.expiresAt() == null || !evidence.expiresAt().isAfter(now)) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_EXPIRED",
          "Validation record %d evidence has no expiry or has expired"
              .formatted(evidence.validationRecordId()));
    }
    if (!firstFrame && !hasVerifiedVisualGates(evidence)) {
      throw new ValidationEvidenceRejectedException(
          "VISUAL_EVIDENCE_PENDING",
          "Validation record %d does not have two matching verified visual gates"
              .formatted(evidence.validationRecordId()));
    }
    if (!firstFrame && !"AUTHORIZED".equals(evidence.renderAuthorization())) {
      throw new ValidationEvidenceRejectedException(
          "EVIDENCE_NOT_RENDER_AUTHORIZED",
          "Validation record %d has no exact AUTHORIZED Family 8 render authorization"
              .formatted(evidence.validationRecordId()));
    }
  }

  /** The proof is fetched from the intelligence service, never from queue request parameters. */
  private boolean hasCompleteGovernedAdmission(ValidationEvidenceDto evidence) {
    if(!(evidence.visualEvidence().get("governedAdmission") instanceof java.util.Map<?,?> proof)
        || !"STEP6_RESOLUTION_V2".equals(proof.get("policyVersion"))
        || !Boolean.TRUE.equals(proof.get("eligible"))
        || !Boolean.TRUE.equals(proof.get("evidenceComplete"))
        || !Boolean.TRUE.equals(proof.get("scoreEligible"))
        || !java.util.Objects.equals(evidence.promptSha256(),proof.get("promptSha256"))
        || !java.util.Objects.equals(evidence.deterministicRulesetVersion(),proof.get("rulesetVersion"))
        || !(proof.get("validationRecordId") instanceof Number id) || id.longValue()!=evidence.validationRecordId()
        || !(proof.get("originalBlockerCount") instanceof Number blockers) || blockers.intValue()!=evidence.blockerCount()
        || !(proof.get("originalCriticalCount") instanceof Number criticals) || criticals.intValue()!=evidence.criticalCount()
        || !(proof.get("canonicalFailures") instanceof java.util.List<?> failures)) return false;
    int countedBlockers=0,countedCriticals=0;
    var seen=new java.util.HashSet<String>();
    for(Object item:failures) {
      if(!(item instanceof java.util.Map<?,?> row) || !(row.get("ruleId") instanceof String rule)
          || !seen.add(rule) || !"FAIL".equals(row.get("outcome"))) return false;
      String severity=String.valueOf(row.get("severity"));
      if("BLOCKER".equals(severity)) countedBlockers++;
      if("CRITICAL".equals(severity)) countedCriticals++;
      if(!"BLOCKER".equals(severity) && !"CRITICAL".equals(severity)) continue;
      if(!(row.get("governanceRecordId") instanceof String record) || record.isBlank()) return false;
      boolean attempt="ATTEMPT_001".equals(rule) && "ATTEMPT_COUNT_EXCEPTION_V1".equals(row.get("disposition")) && "BLOCKER".equals(severity);
      boolean risk="PRODUCIBILITY_003".equals(rule) && "PRODUCTION_RISK_ACKNOWLEDGED".equals(row.get("disposition")) && "CRITICAL".equals(severity);
      if(!attempt && !risk) return false;
    }
    return countedBlockers==evidence.blockerCount() && countedCriticals==evidence.criticalCount();
  }

  private BigDecimal decimal(Object value) {
    if (value instanceof Number number) return new BigDecimal(number.toString());
    if (value instanceof String text) {
      try { return new BigDecimal(text.trim()); } catch (NumberFormatException ignored) { return null; }
    }
    return null;
  }

  private boolean hasVerifiedVisualGates(ValidationEvidenceDto evidence) {
    if (!evidence.finalVideoEligible()) return false;
    if (!(evidence.visualEvidence().get("firstFrame") instanceof java.util.Map<?, ?> first)
        || !(evidence.visualEvidence().get("silhouette")
            instanceof java.util.Map<?, ?> silhouette)) {
      return false;
    }
    return "PASS".equals(first.get("status"))
        && "PASS".equals(silhouette.get("status"))
        && java.util.Objects.equals(first.get("evidenceSetId"), silhouette.get("evidenceSetId"))
        && java.util.Objects.equals(first.get("assetId"), silhouette.get("assetId"))
        && java.util.Objects.equals(first.get("assetSha256"), silhouette.get("assetSha256"));
  }
}
