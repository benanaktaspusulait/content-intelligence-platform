package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Registry read and local dispatch only; no database/provider/render execution. */
class ConceptGenerationControllerTest {
  @Test
  @SuppressWarnings("unchecked")
  void usesServerRegistryRatherThanClientSuppliedCharacterDescriptions() {
    var client = mock(QualityMlClient.class);
    var jdbc = mock(JdbcClient.class, RETURNS_DEEP_STUBS);
    var registry = List.<Map<String, Object>>of(Map.of("id", "registered-a", "name", "Kiko"));
    when(jdbc.sql(anyString()).query(org.mockito.ArgumentMatchers.<RowMapper<Map<String, Object>>>any()).list()).thenReturn(registry);
    var request = Map.<String, Object>of("count", 20, "seed", 42,
        "canonicalCast", List.of(Map.of("id", "fake", "name", "Unregistered")));
    var expectedPayload = Map.<String, Object>of("count", 20, "seed", 42, "canonicalCast", registry);
    var expected = Map.<String, Object>of("workflow", "GENERATE_AND_RANK_SHORT_CONCEPTS", "providerCalls", 0);
    when(client.workflow("concepts/generate", expectedPayload)).thenReturn(expected);
    assertThat(new ConceptGenerationController(client, jdbc).generate(request)).isEqualTo(expected);
    verify(client).workflow("concepts/generate", expectedPayload);
    verifyNoMoreInteractions(client);
    assertThat(request.get("canonicalCast")).isNotEqualTo(registry);
  }

  @Test
  void registryFailureDoesNotFallBackToUnverifiedCharactersOrInvokeGeneration() {
    var client = mock(QualityMlClient.class);
    var jdbc = mock(JdbcClient.class);
    when(jdbc.sql(anyString())).thenThrow(new IllegalStateException("Registry unavailable"));
    org.assertj.core.api.Assertions.assertThatThrownBy(
        () -> new ConceptGenerationController(client, jdbc).generate(Map.of("seed", 42)))
        .isInstanceOf(IllegalStateException.class).hasMessageContaining("Registry unavailable");
    verifyNoInteractions(client);
  }
}
