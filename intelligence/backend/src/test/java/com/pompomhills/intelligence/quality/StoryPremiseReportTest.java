package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** Validate PDF text projection without rendering any document or media. */
class StoryPremiseReportTest {
  @Test
  void historicalReportsRemainUnchanged() {
    assertThat(QualityReportPdfService.storyPremiseLines(null)).isEmpty();
    assertThat(QualityReportPdfService.storyPremiseLines(Map.of())).isEmpty();
  }

  @Test
  void preservesRevisionReasonEvidenceAndDurationSuitability() {
    Map<String, Object> engine = Map.of(
        "status", "STORY_REVISION_REQUIRED", "score", 12,
        "humanReadableReport", "Passive misunderstanding has no meaningful choice or cost.",
        "storyEngineSummary", Map.of("drivingGoal", "Not established"),
        "checks", List.of(Map.of("checkId", "MORAL_CHOICE_GATE", "outcome", "UNKNOWN",
            "reason", "No deliberate rejection of the original goal.",
            "evidence", List.of(Map.of("quote", "Arda looks scary.")))),
        "durationSuitability", Map.of("10_20_SECONDS", Map.of("status", "SUITABLE", "reason", "One reveal."),
            "45_75_SECONDS", Map.of("status", "REVISION_REQUIRED", "reason", "Needs an active arc.")),
        "findings", List.of(Map.of("severity", "WARN", "message", "Too few meaning changes.")));
    String text = String.join("\n", QualityReportPdfService.storyPremiseLines(engine));
    assertThat(text).contains("STORY_REVISION_REQUIRED", "separate from canonical scoring",
        "Passive misunderstanding", "MORAL_CHOICE_GATE", "Source: Arda looks scary.",
        "10_20_SECONDS: SUITABLE", "45_75_SECONDS: REVISION_REQUIRED",
        "Visual execution and audience response remain unverified");
  }
}
