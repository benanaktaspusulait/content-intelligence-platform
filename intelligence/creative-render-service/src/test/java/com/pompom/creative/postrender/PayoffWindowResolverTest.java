package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.domain.RenderJob;
import org.junit.jupiter.api.Test;

class PayoffWindowResolverTest {
  private final PayoffWindowResolver resolver = new PayoffWindowResolver();

  @Test
  void resolvesOnlyAnExplicitTimestampedPayoffMarker() {
    RenderJob job = RenderJob.builder()
        .promptTextSnapshot("0.0-1.0 HOOK\n7.5-9.0 PAYOFF: Kiko laughs")
        .build();

    PayoffWindow window = resolver.resolve(job);

    assertThat(window.status()).isEqualTo(PayoffWindowStatus.RESOLVED);
    assertThat(window.startSeconds()).isEqualTo(7.5);
    assertThat(window.endSeconds()).isEqualTo(9.0);
  }

  @Test
  void doesNotInferPayoffFromAnUntimedPrompt() {
    RenderJob job = RenderJob.builder().promptTextSnapshot("Kiko reaches the payoff and smiles.").build();

    assertThat(resolver.resolve(job).status()).isEqualTo(PayoffWindowStatus.NOT_AVAILABLE);
  }

  @Test
  void marksMultipleExplicitPayoffsAmbiguous() {
    RenderJob job = RenderJob.builder()
        .promptTextSnapshot("2-3s PAYOFF one\\n8-9s REVEAL two")
        .build();

    assertThat(resolver.resolve(job).status()).isEqualTo(PayoffWindowStatus.AMBIGUOUS);
  }
}
