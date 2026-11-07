package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import java.util.Map;
import org.junit.jupiter.api.Test;

class AutonomousProductionControllerTest {
  @Test
  void startsExistingEligibleFirstWithIdempotencyAndFixedSafeDefaults() {
    var client = mock(QualityMlClient.class);
    var response = Map.<String, Object>of("runId", "00000000-0000-0000-0000-000000000001", "providerRequests", 0);
    when(client.workflow("autonomous-production/runs", Map.of("mode", "EXISTING_ELIGIBLE_FIRST", "idempotencyKey", "key-1"))).thenReturn(response);

    assertThat(new AutonomousProductionController(client).start("key-1", Map.of())).isEqualTo(response);

    verify(client).workflow("autonomous-production/runs", Map.of("mode", "EXISTING_ELIGIBLE_FIRST", "idempotencyKey", "key-1"));
    verifyNoMoreInteractions(client);
  }

  @Test
  void readsOnlyAValidatedRunId() {
    var client = mock(QualityMlClient.class);
    var response = Map.<String, Object>of("runId", "00000000-0000-0000-0000-000000000001");
    when(client.workflowRead("autonomous-production/runs/00000000-0000-0000-0000-000000000001")).thenReturn(response);

    assertThat(new AutonomousProductionController(client).status("00000000-0000-0000-0000-000000000001")).isEqualTo(response);
    verify(client).workflowRead("autonomous-production/runs/00000000-0000-0000-0000-000000000001");
    verifyNoMoreInteractions(client);
  }
}
