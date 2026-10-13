package com.pompomhills.intelligence.workflow;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.QualityMlClient;
import java.util.*;
import org.junit.jupiter.api.Test;
class SourcePlanReadOnlyTest {
  @Test void extractionIsSeparateAndNeverPersistsOrRevalidates() throws Exception {
    var json=new ObjectMapper();
    Map<String,Object> saved=json.readValue(getClass().getResourceAsStream("/step5-analysis-snapshot.json"),new TypeReference<>(){});
    Map<String,Object> extraction=json.readValue(getClass().getResourceAsStream("/step5-source-plan.json"),new TypeReference<>(){});
    var before=json.writeValueAsString(saved);var id=UUID.fromString(saved.get("recordId").toString());
    var ml=mock(QualityMlClient.class);var service=spy(new WorkflowService(null,ml,null,null,json,null,null));
    doReturn(saved).when(service).getByKind(id,"REVIEW");when(ml.workflow(eq("source-plan"),anyMap())).thenReturn(extraction);
    var result=service.sourcePlan(id);assertThat(result.get("historicalRunId")).isEqualTo(id.toString());
    assertThat(result.get("resultId")).isNotEqualTo(id.toString());assertThat(result.get("authorizationStatus")).isEqualTo("NOT_EVALUATED");
    assertThat(json.writeValueAsString(saved)).isEqualTo(before);verify(ml).workflow(eq("source-plan"),anyMap());verifyNoMoreInteractions(ml);
    saved.put("originalPrompt","different prompt");assertThatThrownBy(()->service.sourcePlan(id)).isInstanceOf(IllegalArgumentException.class);verifyNoMoreInteractions(ml);
  }
}
