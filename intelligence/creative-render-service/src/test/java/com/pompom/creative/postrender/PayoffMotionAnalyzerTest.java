package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class PayoffMotionAnalyzerTest {
  private final PayoffMotionAnalyzer analyzer = new PayoffMotionAnalyzer();

  @Test
  void highLowHighProducesReductionContrastAndHoldCandidate() {
    Map<String, Object> result =
        analyzer.analyze(
            profile(0.9, 0.4, 0.9),
            new PayoffWindow(PayoffWindowStatus.RESOLVED, 1.0, 2.0, "test", "test"));

    assertThat(result.get("contrastDirection")).isEqualTo("REDUCTION");
    assertThat(result.get("intentionalHold")).isEqualTo(true);
    assertThat(result.get("holdDurationSeconds")).isEqualTo(1.0);
  }

  @Test
  void lowHighLowProducesIncreaseWithoutCallingItBad() {
    Map<String, Object> result =
        analyzer.analyze(
            profile(0.3, 0.9, 0.3),
            new PayoffWindow(PayoffWindowStatus.RESOLVED, 1.0, 2.0, "test", "test"));

    assertThat(result.get("contrastDirection")).isEqualTo("INCREASE");
    assertThat(result.get("contrastStatus")).isEqualTo("AVAILABLE");
  }

  @Test
  void unresolvedPayoffDoesNotGuessAWindow() {
    Map<String, Object> result =
        analyzer.analyze(
            profile(0.8, 0.8, 0.8),
            new PayoffWindow(PayoffWindowStatus.NOT_AVAILABLE, null, null, "test", "missing"));

    assertThat(result.get("contrastStatus")).isEqualTo("NOT_EVALUATED");
    assertThat(result.get("prePayoffMotion")).isNull();
  }

  private Map<String, Object> profile(double pre, double during, double post) {
    return Map.of(
        "segments",
        List.of(
            Map.of("startSeconds", 0.0, "endSeconds", 1.0, "averageMotion", pre),
            Map.of("startSeconds", 1.0, "endSeconds", 2.0, "averageMotion", during),
            Map.of("startSeconds", 2.0, "endSeconds", 3.0, "averageMotion", post)));
  }
}
