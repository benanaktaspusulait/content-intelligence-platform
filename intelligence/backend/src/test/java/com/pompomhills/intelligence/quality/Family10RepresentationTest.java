package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.openpdf.text.pdf.PdfReader;
import org.openpdf.text.pdf.parser.PdfTextExtractor;

class Family10RepresentationTest {
  @ParameterizedTest
  @ValueSource(strings = {"PRODUCIBLE", "RISKY", "NOT_PRODUCIBLE", "UNKNOWN", "NOT_APPLICABLE"})
  void preservesCanonicalEvidenceAcrossMlDtoSnapshotAndPdf(String status) throws Exception {
    Map<String, Object> projection = new LinkedHashMap<>();
    projection.put("status", status);
    projection.put("durationSeconds", null);
    projection.put("durationSource", "UNAVAILABLE");
    projection.put(
        "dimensions",
        Map.of(
            "FINE_MOTOR_PRECISION",
                Map.of(
                    "level",
                    "HIGH",
                    "reason",
                    "Exact thread contact required",
                    "evidenceReferences",
                    List.of("beat_02.fineMotorRequirement"),
                    "material",
                    true,
                    "requiresRedesign",
                    false),
            "TEXT_LIP_SYNC_SYMBOL",
                Map.of(
                    "level",
                    "UNKNOWN",
                    "reason",
                    "Text dependency not supplied",
                    "evidenceReferences",
                    List.of()),
            "SEGMENT_CONTINUITY",
                Map.of(
                    "level",
                    "NOT_APPLICABLE",
                    "reason",
                    "Single generation",
                    "evidenceReferences",
                    List.of())));
    projection.put("reasons", List.of("Exact thread contact required"));
    projection.put("durationLoad", Map.of("level", "UNKNOWN", "reason", "Duration unavailable"));
    projection.put(
        "provenance",
        Map.of(
            "evaluatorVersion", "general-producibility-v1", "source", "STRUCTURED_VIDEO_PLAN_IR"));
    ObjectMapper mapper =
        new ObjectMapper().setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    Map<String, Object> assessment =
        Map.of(
            "general_producibility",
            projection,
            "creative_grade",
            "A",
            "creative_score",
            98,
            "family8",
            Map.of(
                "creativeQuality",
                Map.of("creativeScore", 98, "creativeGrade", "A"),
                "evidenceCompleteness",
                Map.of("status", "COMPLETE", "evaluationCoverage", 1),
                "renderAuthorization",
                Map.of("status", "AUTHORIZED", "reasons", List.of())));
    QualityReportDto dto =
        mapper.readValue(
            mapper.writeValueAsString(
                Map.of(
                    "overall_score",
                    98,
                    "status",
                    "RENDER_READY",
                    "ruleset_version",
                    "1.7",
                    "pre_render_assessment",
                    assessment)),
            QualityReportDto.class);
    QualityReportDto restored = QualityReportSnapshots.fromJson(QualityReportSnapshots.toJson(dto));
    assertThat(restored).isNotNull();
    assertThat(restored.preRenderAssessment()).isEqualTo(dto.preRenderAssessment());
    Map<?, ?> recovered = (Map<?, ?>) restored.preRenderAssessment().get("general_producibility");
    assertThat(recovered.get("status")).isEqualTo(status);
    assertThat(recovered.containsKey("durationSeconds")).isTrue();
    assertThat(recovered.get("durationSeconds")).isNull();
    assertThat(
            QualityReportSnapshots.renderAuthorizationStatus(
                QualityReportSnapshots.toJson(restored)))
        .isEqualTo("AUTHORIZED");
    byte[] bytes =
        new QualityReportPdfService()
            .render(new QualityReportExportRequest(restored, "Family 10", null, null));
    PdfReader reader = new PdfReader(bytes);
    StringBuilder text = new StringBuilder();
    PdfTextExtractor extractor = new PdfTextExtractor(reader);
    for (int page = 1; page <= reader.getNumberOfPages(); page++)
      text.append(extractor.getTextFromPage(page));
    reader.close();
    assertThat(text.toString())
        .contains(
            "General Producibility: " + status,
            "FINE_MOTOR_PRECISION",
            "HIGH",
            "Exact thread contact required",
            "beat_02.fineMotorRequirement",
            "TEXT_LIP_SYNC_SYMBOL",
            "UNKNOWN",
            "SEGMENT_CONTINUITY",
            "NOT_APPLICABLE",
            "Duration: UNKNOWN",
            "general-producibility-v1");
    assertThat(text.toString())
        .contains(
            "Creative quality: score 98",
            "grade A",
            "Evidence completeness: COMPLETE",
            "Render authorization: AUTHORIZED");
    Files.createDirectories(Path.of("target/family10-pdf"));
    Files.write(Path.of("target/family10-pdf/" + status + ".pdf"), bytes);
  }
}
