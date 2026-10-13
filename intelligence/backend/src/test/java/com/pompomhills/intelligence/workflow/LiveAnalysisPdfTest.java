package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.QualityReportPdfService;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.openpdf.text.pdf.PdfReader;
import org.openpdf.text.pdf.parser.PdfTextExtractor;
import org.springframework.test.util.ReflectionTestUtils;

class LiveAnalysisPdfTest {
  @Test
  void actualBrowserExportRouteIncludesCompletePersistedAnalysisWithoutRerunning() throws Exception {
    var json = new ObjectMapper();
    Map<String,Object> snapshot;
    try (var input = getClass().getResourceAsStream("/step5-analysis-snapshot.json")) {
      snapshot = json.readValue(input, new TypeReference<>() {});
    }
    String unchanged = json.writeValueAsString(snapshot);
    var id = UUID.fromString(String.valueOf(snapshot.get("recordId")));
    var service = mock(WorkflowService.class);
    when(service.get(id)).thenReturn(snapshot);
    Map<String,Object> extraction;
    try (var input = getClass().getResourceAsStream("/step5-source-plan.json")) { extraction = json.readValue(input, new TypeReference<>() {}); }
    extraction.put("historicalRunId", id.toString());
    when(service.sourcePlan(id)).thenReturn(extraction);
    var controller = new WorkflowController(service);
    ReflectionTestUtils.setField(controller, "pdf", new QualityReportPdfService());
    var response = controller.report(id);
    assertThat(response.getHeaders().getFirst("Cache-Control")).isEqualTo("no-store");
    assertThat(response.getHeaders().getFirst("Content-Disposition")).contains(id.toString());
    try (var reader = new PdfReader(response.getBody())) {
      assertThat(reader.getNumberOfPages()).isGreaterThan(2);
      var extractor = new PdfTextExtractor(reader);
      StringBuilder text = new StringBuilder();
      for (int page=1;page<=reader.getNumberOfPages();page++) text.append(extractor.getTextFromPage(page));
      String readable = text.toString();
      String joined = readable.replaceAll("\\s+", "");
      assertThat(joined).contains(id.toString(), "MINI_STORY_LOCK", "GOAL_VISIBLE_EARLY", "TEMPORAL_COMPLEXITY_SPLIT_GATE", "BEAT_DENSITY_RULE", "STUBBORN_RETURN_LOOP", "CONTINUATION_LOCK", "STUBBORN_RETURN_HOOK", "STUBBORN_RETURN_PAYOFF", "ASSESSMENT_TECHNICAL_FAILURE", "REFERENCE_ASSOCIATION", "EXECUTION_INPUTS");
      assertThat(readable).contains("85.0", "Grade: B", "ABSURD PHYSICS", "SEEDANCE 2 0 MINI", "1.7", "Video Plan IR", "Timed Beats (5)", "goal evidence", "F8 Render Authorization", "Findings Resolution", "Evidence & Source Traceability", "input-contract mismatch", "UNKNOWN", "480p", "Mimi", "sticky note", "Read-only source extraction", "NOT_PERFORMED");
      assertThat(readable).doesNotContain("All 9 approved story events are represented", "{status=", "[object Object]");
    }
    assertThat(json.writeValueAsString(snapshot)).isEqualTo(unchanged);
    verify(service).get(id);
    verify(service).sourcePlan(id);
    verifyNoMoreInteractions(service);
  }
}
