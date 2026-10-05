package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TemporalBeatAlignmentServiceTest {
  private final TemporalBeatAlignmentService service = new TemporalBeatAlignmentService();

  @Test
  void alignsDropToOverlappingPlanBeatAndKeepsUnmappedCandidatesExplicit() {
    Map<String, Object> profile = Map.of("activityDrops", List.of(
        Map.of("startSeconds", 2.0, "endSeconds", 3.0, "classification", "UNMAPPED_DROP"),
        Map.of("startSeconds", 6.0, "endSeconds", 7.0, "classification", "UNMAPPED_DROP")));
    Map<String, Object> contract = Map.of("intent", Map.of("timingIntent", List.of(
        Map.of("id", "reaction-1", "type", "REACTION", "start", 1.5, "end", 3.5))));

    Map<String, Object> result = service.align(profile, contract);

    List<Map<String, Object>> drops = (List<Map<String, Object>>) result.get("activityDrops");
    assertThat(drops.get(0).get("classification")).isEqualTo("PLANNED_REACTION");
    assertThat(drops.get(0).get("alignedBeatId")).isEqualTo("reaction-1");
    assertThat(result.get("unmappedActivityDrops")).asList().hasSize(1);
  }
}
