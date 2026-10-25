package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;

class SemanticEvidenceReplayControllerTest {
  @Test
  void forwardsStoredReplayWithoutRegistryLookupOrGeneration() {
    var client = mock(QualityMlClient.class);
    var jdbc = mock(JdbcClient.class);
    var request = Map.<String, Object>of("experimentId", "semantic-live-v1-seed-42-count-40",
        "semanticEvidenceAdapterVersion", "v1", "allowExternalGeneration", false);
    var expected = Map.<String, Object>of("workflow", "SEMANTIC_EVIDENCE_REPLAY", "providerCalls", 0);
    when(client.workflow("concepts/semantic/replay", request)).thenReturn(expected);
    assertThat(new ConceptGenerationController(client, jdbc).replaySemanticEvidence(request)).isEqualTo(expected);
    verify(client).workflow("concepts/semantic/replay", request);
    verifyNoMoreInteractions(client);
    verifyNoInteractions(jdbc);
  }
}
