package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** Offline operation dispatch only; no models, persistence or render execution. */
class ConceptRankingControllerTest {
  @Test
  void forwardsSuppliedBatchWithoutScoringOrMutation() {
    var client = mock(QualityMlClient.class);
    var request = Map.<String, Object>of("candidates", List.of(Map.of("id", "a", "title", "Supplied")));
    var expected = Map.<String, Object>of("workflow", "CONCEPT_CANDIDATE_RANKING", "firstRenderCandidate", "a");
    when(client.workflow("concepts/rank", request)).thenReturn(expected);
    assertThat(new ConceptRankingController(client).rank(request)).isEqualTo(expected);
    verify(client).workflow("concepts/rank", request);
    verifyNoMoreInteractions(client);
    assertThat(request).containsOnlyKeys("candidates");
  }

  @Test
  void singleValidationUsesTheSameMlRankingBoundary() {
    var client = mock(QualityMlClient.class);
    var request = Map.<String, Object>of("id", "incomplete");
    var expected = Map.<String, Object>of("revisionCandidates", List.of(Map.of("candidateId", "incomplete")));
    when(client.workflow("concepts/validate", request)).thenReturn(expected);
    assertThat(new ConceptRankingController(client).validate(request)).isEqualTo(expected);
    verify(client).workflow("concepts/validate", request);
    verifyNoMoreInteractions(client);
  }
}
