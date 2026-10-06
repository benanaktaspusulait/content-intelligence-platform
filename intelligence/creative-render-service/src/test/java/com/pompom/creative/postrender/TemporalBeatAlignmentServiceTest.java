package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TemporalBeatAlignmentServiceTest {
  private final TemporalBeatAlignmentService service = new TemporalBeatAlignmentService();

  @Test
  void alignsDropToOverlappingPlanBeatAndKeepsUnmappedCandidatesExplicit() {
    Map<String, Object> profile =
        Map.of(
            "activityDrops",
            List.of(
                Map.of("startSeconds", 2.0, "endSeconds", 3.0, "classification", "UNMAPPED_DROP"),
                Map.of("startSeconds", 6.0, "endSeconds", 7.0, "classification", "UNMAPPED_DROP")));
    Map<String, Object> contract =
        Map.of(
            "intent",
            Map.of(
                "timingIntent",
                List.of(Map.of("id", "reaction-1", "type", "REACTION", "start", 1.5, "end", 3.5))));

    Map<String, Object> result = service.align(profile, contract);

    List<Map<String, Object>> drops = (List<Map<String, Object>>) result.get("activityDrops");
    assertThat(drops.get(0).get("classification")).isEqualTo("PLANNED_REACTION");
    assertThat(drops.get(0).get("alignedBeatId")).isEqualTo("reaction-1");
    assertThat(result.get("unmappedActivityDrops")).asList().hasSize(1);
  }

  @Test
  void evaluatesDirectTimingIntentBeatsForActionNoveltyAndFidelity() {
    Map<String, Object> profile =
        Map.of(
            "segments",
                List.of(
                    Map.of(
                        "startSeconds",
                        0.0,
                        "endSeconds",
                        2.0,
                        "averageMotion",
                        0.2,
                        "motionVariability",
                        0.1),
                    Map.of(
                        "startSeconds",
                        2.0,
                        "endSeconds",
                        4.0,
                        "averageMotion",
                        0.7,
                        "motionVariability",
                        0.4),
                    Map.of(
                        "startSeconds",
                        4.0,
                        "endSeconds",
                        6.0,
                        "averageMotion",
                        0.3,
                        "motionVariability",
                        0.2)),
            "visualNovelty",
                Map.of(
                    "points",
                    List.of(
                        Map.of("timestamp", 1.0, "novelty", 0.2),
                        Map.of("timestamp", 3.0, "novelty", 0.8),
                        Map.of("timestamp", 5.0, "novelty", 0.6))));
    Map<String, Object> contract =
        Map.of(
            "intent",
            Map.of(
                "timingIntent",
                List.of(
                    Map.of(
                        "id",
                        "beat-1",
                        "type",
                        "OPENING",
                        "start",
                        0.0,
                        "end",
                        2.0,
                        "primaryAction",
                        "PUSH"),
                    Map.of(
                        "id",
                        "beat-2",
                        "type",
                        "ATTEMPT",
                        "start",
                        2.0,
                        "end",
                        4.0,
                        "primaryAction",
                        "BLOCK"),
                    Map.of(
                        "id",
                        "beat-3",
                        "type",
                        "PAYOFF",
                        "start",
                        4.0,
                        "end",
                        6.0,
                        "primaryAction",
                        "LIFT"))));

    Map<String, Object> result = service.align(profile, contract);

    Map<String, Object> planned = (Map<String, Object>) result.get("plannedActionNovelty");
    Map<String, Object> observed = (Map<String, Object>) result.get("observedVisualBeatNovelty");
    Map<String, Object> fidelity = (Map<String, Object>) result.get("planRenderFidelity");
    assertThat(planned.get("status")).isEqualTo("STRONG");
    assertThat(observed.get("status")).isNotEqualTo("UNKNOWN");
    assertThat(fidelity.get("status")).isNotEqualTo("PLAN_NOT_AVAILABLE");
  }

  @Test
  void explainsWhenAPlanIsUnavailableInsteadOfClaimingNovelty() {
    Map<String, Object> result = service.align(Map.of(), Map.of());

    Map<String, Object> action = (Map<String, Object>) result.get("actionBeatNovelty");
    Map<String, Object> fidelity = (Map<String, Object>) result.get("planRenderFidelity");
    assertThat(action.get("status")).isEqualTo("PLAN_NOT_AVAILABLE");
    assertThat(fidelity.get("status")).isEqualTo("PLAN_NOT_AVAILABLE");
  }
}
