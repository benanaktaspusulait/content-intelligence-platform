package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** Pure projection and dispatch tests. No PDF, media, server or provider generation. */
class ShortFormReportTest {
  @Test
  void absentHistoricalReportsHaveNoAdditionalProjection() {
    assertThat(QualityReportPdfService.shortFormLines(null)).isEmpty();
    assertThat(QualityReportPdfService.shortFormLines(Map.of())).isEmpty();
  }

  @Test
  void projectsIndependentResultAndSourceEvidenceWithoutChangingIt() {
    Map<String, Object> engine = Map.of(
        "status", "REVISION_REQUIRED", "shortFormScore", 56,
        "humanReadableReport", "One causal beat in five blocks.",
        "progressDensityScore", 20,
        "duplicateEngineRisk", Map.of("status", "HIGH"),
        "findings", List.of(Map.of("code", "HIGH_ACTIVITY_LOW_PROGRESS", "message", "Motion is not progress.")),
        "beats", List.of(Map.of("id", "B1", "progressTypes", List.of("UNDERSTANDING"), "quote", "Kiko tries to sit.")),
        "sourceSha256", "source-sha", "evidenceLimitations", List.of("No video frames inspected."));
    String before = engine.toString();
    assertThat(String.join("\n", QualityReportPdfService.shortFormLines(engine))).contains(
        "56/100", "independent of canonical and long-form", "HIGH_ACTIVITY_LOW_PROGRESS",
        "progressDensityScore: 20", "Source: Kiko tries to sit.", "source-sha", "No video frames inspected.");
    assertThat(engine.toString()).isEqualTo(before);
  }

  @Test
  void explicitControllerDispatchUsesOnlyTheOfflineOperation() {
    var client = mock(QualityMlClient.class);
    var expected = Map.<String, Object>of("status", "PASS");
    when(client.workflow("short-form/evaluate", Map.of("text", "source", "desiredDuration", 15.0))).thenReturn(expected);
    var controller = new ShortFormController(client);
    assertThat(controller.evaluate(new ShortFormController.ShortFormRequest("source", 15.0))).isEqualTo(expected);
    verify(client).workflow("short-form/evaluate", Map.of("text", "source", "desiredDuration", 15.0));
    verifyNoMoreInteractions(client);
  }
}
