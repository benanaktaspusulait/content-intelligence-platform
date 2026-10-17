package com.pompomhills.intelligence.workflow;

import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class StoryReviewIndependenceTest {
  Map<String,Object> evidence(String origin,String provider,String model) {
    return Map.of("origin",origin,"provider",provider,"model",model);
  }
  @Test void crossProviderRealReviewHasIndependentProvenance() {
    assertThat(StoryEvolutionService.independentProviders(
        evidence("REAL_AI_PROVIDER","deepseek","deepseek-chat"),
        evidence("REAL_AI_PROVIDER","openai","gpt-4o-mini-2024-07-18"))).isTrue();
  }
  @Test void sameProviderFixtureAndMissingIdentityCannotEstablishIndependence() {
    var generator=evidence("REAL_AI_PROVIDER","deepseek","deepseek-chat");
    assertThat(StoryEvolutionService.independentProviders(generator,
        evidence("REAL_AI_PROVIDER","deepseek","different-model"))).isFalse();
    assertThat(StoryEvolutionService.independentProviders(generator,
        evidence("DETERMINISTIC_FIXTURE","openai","mock"))).isFalse();
    assertThat(StoryEvolutionService.independentProviders(generator,Map.of())).isFalse();
  }
}
