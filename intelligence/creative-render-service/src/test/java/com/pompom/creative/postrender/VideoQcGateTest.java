package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

public class VideoQcGateTest {
  public static PostRenderEvaluation evaluation(String recommendation, boolean ownerApproved, String technical) {
    var asset = RenderAsset.builder().id(UUID.randomUUID()).sha256("checksum").mediaVerified(true)
        .assetType(RenderAsset.AssetType.VIDEO).build();
    var qc = Map.of("assetHash", "checksum", "technicalStatus", technical, "creativeRecommendation", recommendation,
        "creativeStatus", "NOT_EVALUATED".equals(recommendation) ? "CREATIVE_REVIEW_NOT_EVALUATED" : "CREATIVE_REVIEW_EVALUATED");
    try {
      return PostRenderEvaluation.builder().renderAsset(asset).evidenceSnapshot(new ObjectMapper().writeValueAsString(Map.of("videoQc", qc)))
          .overallDecision(PostRenderDecision.HUMAN_REVIEW).humanDecision(ownerApproved ? "APPROVED" : null)
          .humanReviewedAt(ownerApproved ? Instant.now() : null).build();
    } catch (Exception error) { throw new IllegalStateException(error); }
  }

  @ParameterizedTest @ValueSource(strings={"PUBLISH", "REVIEW", "REJECT", "NOT_EVALUATED"})
  void explicitOwnerMayPublishRegardlessOfCreativeAdvice(String recommendation) {
    assertThatCode(() -> VideoQcGate.requirePass(evaluation(recommendation, true, "TECHNICAL_QC_PASS"))).doesNotThrowAnyException();
  }

  @Test void publishRecommendationNeverAuthorizesAutomaticPublication() {
    assertThatThrownBy(() -> VideoQcGate.requirePass(evaluation("PUBLISH", false, "TECHNICAL_QC_PASS"))).isInstanceOf(IllegalStateException.class);
  }

  @Test void unavailableCreativeReviewDoesNotBlockRecordingOwnerDecision() {
    assertThatCode(() -> VideoQcGate.requireTechnicalIntegrity(evaluation("NOT_EVALUATED", false, "TECHNICAL_QC_PASS"))).doesNotThrowAnyException();
  }

  @Test void ownerCannotOverrideActualTechnicalCorruption() {
    assertThatThrownBy(() -> VideoQcGate.requirePass(evaluation("PUBLISH", true, "TECHNICAL_QC_FAIL"))).isInstanceOf(IllegalStateException.class);
  }

  @Test void quarantineAndUnverifiedBytesRemainMandatoryRestrictions() {
    var e = evaluation("PUBLISH", true, "TECHNICAL_QC_PASS");
    e.getRenderAsset().setQuarantined(true);
    assertThatThrownBy(() -> VideoQcGate.requirePass(e)).isInstanceOf(IllegalStateException.class);
    e.getRenderAsset().setQuarantined(false);
    e.getRenderAsset().setMediaVerified(false);
    assertThatThrownBy(() -> VideoQcGate.requirePass(e)).isInstanceOf(IllegalStateException.class);
  }

  @Test void differentVideoBytesCannotReuseOwnerApproval() {
    var e = evaluation("PUBLISH", true, "TECHNICAL_QC_PASS");
    var changed = PostRenderEvaluation.builder().renderAsset(e.getRenderAsset()).humanDecision("APPROVED").humanReviewedAt(Instant.now())
        .evidenceSnapshot(e.getEvidenceSnapshot().replace("checksum", "other-bytes")).build();
    assertThatThrownBy(() -> VideoQcGate.requirePass(changed)).isInstanceOf(IllegalStateException.class);
  }
  @Test void optionalPaidHelperAbsenceDoesNotAbandonVerifiedVideo() {
    var r = new PostRenderRuleResult("TECH_QA_EVIDENCE_SERVICE", "1", "rules", "POST_RENDER", "TECHNICAL_INTEGRITY",
        PostRenderSeverity.BLOCKER, PostRenderOutcome.SERVICE_ERROR, "Optional helper unavailable", null, Map.of(), Map.of(), "test", false, Instant.now());
    var advice = PostRenderEvaluationService.audiencePolicy(r);
    assertThat(advice.outcome()).isEqualTo(PostRenderOutcome.NOT_APPLICABLE);
    assertThat(advice.severity()).isEqualTo(PostRenderSeverity.INFO);
  }

}
