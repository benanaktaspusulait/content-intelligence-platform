package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.quality.QualityReportPdfService;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.openpdf.text.pdf.PdfReader;
import org.openpdf.text.pdf.parser.PdfTextExtractor;

class WorkflowImpactReportTest {
  @Test
  void rendersFourDimensionsWithEnglishDecisionDashboardInPdf() throws Exception {
    Map<String, Object> snapshot =
        Map.of(
            "decisionPolicyVersion",
            "impact-review-v1",
            "bindingHash",
            "binding",
            "operatorReport",
            List.of(
                Map.of("label", "KUSURUN ETKİSİ", "text", "Yerel sapma; temel olay okunabilir.")),
            "reviewDimensions",
            Map.of(
                "promptPlanQuality",
                Map.of("status", "HYPOTHESIS"),
                "generatorExecutionRisk",
                Map.of("status", "ADVISORY_RISK"),
                "actualRenderQuality",
                Map.of(
                    "planFidelity",
                    "PARTIAL",
                    "viewerFacingUsability",
                    "USABLE",
                    "editorialRecommendation",
                    "TEST_CANDIDATE"),
                "audienceDistributionOutcome",
                Map.of("status", "NOT_JOINED")));
    byte[] bytes = new QualityReportPdfService().renderWorkflow(snapshot);
    try (PdfReader reader = new PdfReader(bytes)) {
      String text = "";
      for (int i = 1; i <= reader.getNumberOfPages(); i++)
        text += new PdfTextExtractor(reader).getTextFromPage(i);
      assertThat(text)
          .contains(
              "Defect impact",
              "PARTIAL",
              "USABLE",
              "TEST_CANDIDATE",
              "NOT_JOINED",
              "Prompt plan quality",
              "Generator execution risk",
              "Actual render quality",
              "Audience distribution outcome",
              "Does not authorize publishing",
              "Analysis execution",
              "Evidence completeness");
    }
  }
}
