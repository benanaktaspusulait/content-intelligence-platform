package com.pompom.creative.qa;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderQaResult;
import com.pompom.creative.repository.RenderQaResultRepository;
import java.math.BigDecimal;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * QA decision engine that determines ACCEPT/RERENDER/ABANDON based on QA analysis.
 *
 * <p>Decision Rules: - Character mismatch: ABANDON immediately - Dead air (>2s) and attempts < 2:
 * RERENDER - Dead air persists after max attempts: ABANDON - Compliance score < 70: RERENDER - All
 * checks pass: ACCEPT
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class QaDecisionEngine {

  private final RenderQaResultRepository qaResultRepo;
  private final ObjectMapper objectMapper;

  private static final int COMPLIANCE_THRESHOLD = 70;
  private static final int MAX_RERENDER_ATTEMPTS = 2;

  /**
   * Make QA decision based on analysis results.
   *
   * @param asset Render asset being evaluated
   * @param qaResult QA analysis result from Python service
   * @return QA decision with reasoning
   */
  @Transactional
  public QaDecision makeDecision(RenderAsset asset, QaAnalysisResult qaResult) {
    log.info(
        "Making QA decision for asset: {} (attempt: {})",
        asset.getId(),
        asset.getRenderJob().getAttemptNumber());

    // Extract analysis results
    boolean hasDeadAir = qaResult.isHasDeadAir();
    boolean characterVerified = qaResult.isCharacterIdentityVerified();
    int complianceScore = qaResult.getComplianceScore();
    int attemptNumber = asset.getRenderJob().getAttemptNumber();

    // Determine decision
    RenderQaResult.QaDecision decision;
    String reason;
    boolean requiresHumanReview = false;

    if (!characterVerified) {
      // Character mismatch - abandon immediately
      decision = RenderQaResult.QaDecision.ABANDON;
      reason = "Character identity verification failed: " + qaResult.getCharacterIdentityIssues();
      requiresHumanReview = true;

    } else if (hasDeadAir && attemptNumber < MAX_RERENDER_ATTEMPTS) {
      // Dead air detected but we can retry
      decision = RenderQaResult.QaDecision.RERENDER;
      reason =
          String.format(
              "Dead air detected (%dms), retrying (attempt %d/%d)",
              qaResult.getDeadAirDurationMs(), attemptNumber, MAX_RERENDER_ATTEMPTS);

    } else if (hasDeadAir) {
      // Dead air persists after max attempts
      decision = RenderQaResult.QaDecision.ABANDON;
      reason =
          String.format(
              "Dead air persists after %d attempts (%dms total)",
              attemptNumber, qaResult.getDeadAirDurationMs());
      requiresHumanReview = true;

    } else if (complianceScore < COMPLIANCE_THRESHOLD && attemptNumber < MAX_RERENDER_ATTEMPTS) {
      // Low compliance score - retry
      decision = RenderQaResult.QaDecision.RERENDER;
      reason =
          String.format(
              "Compliance score below threshold: %d < %d (attempt %d/%d)",
              complianceScore, COMPLIANCE_THRESHOLD, attemptNumber, MAX_RERENDER_ATTEMPTS);

    } else if (complianceScore < COMPLIANCE_THRESHOLD) {
      // Low compliance persists
      decision = RenderQaResult.QaDecision.ABANDON;
      reason =
          String.format(
              "Compliance score remains low after %d attempts: %d", attemptNumber, complianceScore);
      requiresHumanReview = true;

    } else {
      // All checks pass
      decision = RenderQaResult.QaDecision.ACCEPT;
      reason =
          String.format(
              "All QA checks passed (compliance: %d, confidence: %.2f)",
              complianceScore, qaResult.getConfidence());
    }

    // Create QA result entity
    RenderQaResult qaResultEntity =
        createQaResultEntity(asset, qaResult, decision, reason, requiresHumanReview);

    qaResultRepo.save(qaResultEntity);

    log.info("QA decision for asset {}: {} - {}", asset.getId(), decision, reason);

    return new QaDecision(decision, reason, requiresHumanReview);
  }

  /** Create RenderQaResult entity from analysis. */
  private RenderQaResult createQaResultEntity(
      RenderAsset asset,
      QaAnalysisResult qaResult,
      RenderQaResult.QaDecision decision,
      String reason,
      boolean requiresHumanReview) {
    // Convert dead air segments to JSON
    String deadAirSegmentsJson = null;
    if (qaResult.isHasDeadAir() && qaResult.getDeadAirSegments() != null) {
      try {
        deadAirSegmentsJson = objectMapper.writeValueAsString(qaResult.getDeadAirSegments());
      } catch (JsonProcessingException e) {
        log.warn("Failed to serialize dead air segments", e);
      }
    }

    // Create compliance issues JSON (currently just a simple message)
    String complianceIssuesJson = null;
    if (qaResult.getComplianceScore() < 100) {
      try {
        complianceIssuesJson =
            objectMapper.writeValueAsString(
                java.util.Map.of(
                    "score", qaResult.getComplianceScore(),
                    "hasDeadAir", qaResult.isHasDeadAir(),
                    "characterVerified", qaResult.isCharacterIdentityVerified()));
      } catch (JsonProcessingException e) {
        log.warn("Failed to serialize compliance issues", e);
      }
    }

    return RenderQaResult.builder()
        .renderAsset(asset)
        .promptVersionId(asset.getRenderJob().getPromptVersionId())
        .decision(decision)
        .decisionReason(reason)
        .confidence(BigDecimal.valueOf(qaResult.getConfidence()))
        .complianceScore(qaResult.getComplianceScore())
        .complianceIssues(complianceIssuesJson)
        .hasDeadAir(qaResult.isHasDeadAir())
        .deadAirSegments(deadAirSegmentsJson)
        .characterIdentityVerified(qaResult.isCharacterIdentityVerified())
        .characterIdentityIssues(qaResult.getCharacterIdentityIssues())
        .physicsConsistent(null)
        .physicsViolations(null)
        .hasObjectDuplication(null)
        .duplicationDetails(null)
        .finalExecutionScore(null) // Placeholder - not implemented in Part 2
        .finalExecutionIssues(null)
        .requiresHumanReview(requiresHumanReview)
        .build();
  }

  /** QA decision result. */
  public record QaDecision(
      RenderQaResult.QaDecision decision, String reason, boolean requiresHumanReview) {}
}
