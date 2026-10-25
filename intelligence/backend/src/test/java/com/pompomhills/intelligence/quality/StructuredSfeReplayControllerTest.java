package com.pompomhills.intelligence.quality;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
class StructuredSfeReplayControllerTest {
  @Test void dispatchesOnlyStoredReplayWithoutRegistryOrGeneration() {
    var client=mock(QualityMlClient.class); var jdbc=mock(JdbcClient.class);
    var request=Map.<String,Object>of("shortFormEvidenceSourceVersion","structured-canonical-v1","allowExternalGeneration",false);
    var expected=Map.<String,Object>of("workflow","STRUCTURED_SFE_OFFLINE_REPLAY","providerCalls",0);
    when(client.workflow("concepts/semantic/short-form-replay",request)).thenReturn(expected);
    assertThat(new ConceptGenerationController(client,jdbc).replayStructuredShortForm(request)).isEqualTo(expected);
    verify(client).workflow("concepts/semantic/short-form-replay",request);verifyNoMoreInteractions(client);verifyNoInteractions(jdbc);
  }
}
