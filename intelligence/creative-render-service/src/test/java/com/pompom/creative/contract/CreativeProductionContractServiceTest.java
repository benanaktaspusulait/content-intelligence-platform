package com.pompom.creative.contract;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import org.junit.jupiter.api.Test;

class CreativeProductionContractServiceTest {
  private final CreativeProductionContractService service =
      new CreativeProductionContractService(new ObjectMapper(), new PromptConstraintCompiler());

  @Test
  void compilesCanonicalParsedPlanIntoVersionedContractAndGuidance() {
    ContentPromptSnapshot snapshot =
        snapshot(
            "{\"videoPlanIR\":{\"metadata\":{\"seriesType\":\"whats_wrong\",\"version\":2},"
                + "\"hook\":{\"anomaly\":\"water moves upward\"},"
                + "\"coreMechanic\":{\"primaryObject\":\"faucet\"},"
                + "\"characters\":[{\"name\":\"Kiko\"}],"
                + "\"beats\":[{\"start\":0,\"end\":2}],"
                + "\"finalPayoff\":{\"emphasisStrategy\":\"MOTION_REDUCTION\"}}}");

    CreativeProductionContractService.ContractCompilation result =
        service.compile(snapshot, "RULESET_1.5");

    assertThat(result.contract().status()).isEqualTo("READY");
    assertThat(result.contract().contractVersion()).isEqualTo("creative-production-contract-v1");
    assertThat(result.contract().activePreRenderRulesetVersion()).isEqualTo("RULESET_1.5");
    assertThat(result.constraints().constraints())
        .contains("At the payoff, reduce non-essential motion so the consequence and reaction remain readable.");
    assertThat(result.constraintsSha256()).hasSize(64);
  }

  @Test
  void legacyPromptIsExplicitlyUnavailableAndDoesNotGetInventedIntent() {
    CreativeProductionContractService.ContractCompilation result =
        service.compile(snapshot("{}"), "RULESET_1.5");

    assertThat(result.contract().status()).isEqualTo("CONTRACT_NOT_AVAILABLE_LEGACY");
    assertThat(result.constraints().constraints()).isEmpty();
  }

  private ContentPromptSnapshot snapshot(String parsedIr) {
    return new ContentPromptSnapshot("v1", 1L, "Test", "REEL", "RENDER_READY", 2L, 1,
        "A valid prompt with enough text", parsedIr, "a".repeat(64));
  }
}
