package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PostRenderRuleEngineTest {
  private final PostRenderRuleEngine engine = new PostRenderRuleEngine();
  private final PostRenderDecisionAggregator aggregator = new PostRenderDecisionAggregator();

  @Test
  void lowMotionEvidenceIsInformationalAndDoesNotFailQa() {
    RenderEvidenceIR evidence = evidence(true, true, 0.02, EvidenceStatus.AVAILABLE);

    List<PostRenderRuleResult> results = engine.evaluate(evidence);

    assertThat(aggregator.aggregate(results)).isEqualTo(PostRenderDecision.PASS);
    assertThat(results.stream().filter(result -> result.ruleId().equals("VISUAL_LOW_MOTION_INFO"))
        .findFirst().orElseThrow().outcome()).isEqualTo(PostRenderOutcome.PASS);
  }

  @Test
  void unreadableMediaFailsAsTechnicalBlocker() {
    RenderEvidenceIR evidence = evidence(false, true, 0.5, EvidenceStatus.AVAILABLE);

    assertThat(aggregator.aggregate(engine.evaluate(evidence))).isEqualTo(PostRenderDecision.FAIL);
  }

  @Test
  void unavailableRequiredQaServiceProducesSystemError() {
    RenderEvidenceIR evidence = evidence(true, true, null, EvidenceStatus.SERVICE_ERROR);

    assertThat(aggregator.aggregate(engine.evaluate(evidence))).isEqualTo(PostRenderDecision.SYSTEM_ERROR);
  }

  private RenderEvidenceIR evidence(boolean readable, boolean checksum, Double density, EvidenceStatus qaStatus) {
    Map<String, Object> technical = Map.of(
        "mediaReadable", readable, "mediaReadableStatus", EvidenceStatus.AVAILABLE.name(),
        "checksumVerified", checksum, "checksumVerifiedStatus", EvidenceStatus.AVAILABLE.name(),
        "durationMs", 15000, "durationMsStatus", EvidenceStatus.AVAILABLE.name(),
        "width", 1080, "widthStatus", EvidenceStatus.AVAILABLE.name());
    Map<String, Object> qa = Map.of(
        "evidenceAvailable", qaStatus == EvidenceStatus.AVAILABLE,
        "evidenceAvailableStatus", qaStatus.name(),
        "hasDeadAir", false, "hasDeadAirStatus", qaStatus.name(),
        "characterIdentityVerified", true, "characterIdentityVerifiedStatus", qaStatus.name());
    Map<String, Object> motion = density == null ? Map.of() : Map.of(
        "motionIntervalDensity", density, "motionIntervalDensityStatus", EvidenceStatus.AVAILABLE.name());
    return new RenderEvidenceIR(UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID(), null, null,
        "render-evidence-v1", Instant.now(), Map.of(), Map.of("technical", technical, "qa", qa, "motion", motion));
  }
}
