package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;

class PlanRenderFidelityAnalyzerTest {
  private final PlanRenderFidelityAnalyzer analyzer = new PlanRenderFidelityAnalyzer();

  @Test
  void plannedReductionWithObservedReductionMatches() {
    Map<String, Object> contract =
        Map.of("intent", Map.of("payoffIntent", Map.of("emphasisStrategy", "MOTION_REDUCTION")));
    Map<String, Object> result =
        analyzer.compare(contract, Map.of("contrastDirection", "REDUCTION"));
    assertThat(((Map<?, ?>) result.get("payoff")).get("fidelity")).isEqualTo("MATCH");
    assertThat(result.get("recommendedActionType")).isEqualTo("NO_ACTION");
  }

  @Test
  void plannedReductionWithFlatObservedMotionRequiresRegeneration() {
    Map<String, Object> contract =
        Map.of("intent", Map.of("payoffIntent", Map.of("emphasisStrategy", "MOTION_REDUCTION")));
    Map<String, Object> result = analyzer.compare(contract, Map.of("contrastDirection", "NONE"));
    assertThat(((Map<?, ?>) result.get("payoff")).get("fidelity")).isEqualTo("MISMATCH");
    assertThat(result.get("rootCause")).isEqualTo("RENDER_FIDELITY_ISSUE");
    assertThat(result.get("recommendedActionType")).isEqualTo("REGENERATE");
  }

  @Test
  void missingContractDoesNotFabricateMatch() {
    Map<String, Object> result =
        analyzer.compare(Map.of(), Map.of("contrastDirection", "REDUCTION"));
    assertThat(((Map<?, ?>) result.get("payoff")).get("fidelity")).isEqualTo("UNKNOWN");
    assertThat(result.get("status")).isEqualTo("CONTRACT_NOT_AVAILABLE_LEGACY");
  }
}
