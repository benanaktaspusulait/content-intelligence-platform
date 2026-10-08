package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.openpdf.text.pdf.PdfReader;
import org.openpdf.text.pdf.parser.PdfTextExtractor;

class Family10GoldenTransportTest {
  @ParameterizedTest
  @ValueSource(
      strings = {
        "sticky-ball-01",
        "ball-crocodile-01",
        "upside-chair-01",
        "lamp-01",
        "snack-box-01",
        "box-cat-01",
        "spot-cat-01",
        "sneaky-door-01",
        "island-journal-01"
      })
  void frozenMlApiEvidenceSurvivesActualDtoSnapshotAndPdf(String goldenId) throws Exception {
    Path fixture =
        Path.of(
            System.getProperty("basedir"),
            "../data/golden/pompom-golden-v1/frozen-semantic/family10/api-contract.json");
    ObjectMapper mapper =
        new ObjectMapper().setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    JsonNode assets = mapper.readTree(fixture.toFile()).get("assets");
    assertThat(assets.size()).isEqualTo(9);
    QualityReportDto dto = mapper.treeToValue(assets.get(goldenId), QualityReportDto.class);
    QualityReportDto restored = QualityReportSnapshots.fromJson(QualityReportSnapshots.toJson(dto));
    assertThat(restored).isNotNull();
    assertThat(restored.preRenderAssessment()).isEqualTo(dto.preRenderAssessment());
    assertThat(restored.overallScore()).isNull();
    assertThat(restored.preRenderAssessment().get("creative_score")).isNull();
    Map<?, ?> evidence = (Map<?, ?>) restored.preRenderAssessment().get("general_producibility");
    Map<?, ?> dimensions = (Map<?, ?>) evidence.get("dimensions");
    assertThat(dimensions.size()).isEqualTo(15);
    byte[] pdf =
        new QualityReportPdfService()
            .render(new QualityReportExportRequest(restored, goldenId, null, null));
    PdfReader reader = new PdfReader(pdf);
    PdfTextExtractor extractor = new PdfTextExtractor(reader);
    StringBuilder text = new StringBuilder();
    for (int page = 1; page <= reader.getNumberOfPages(); page++)
      text.append(extractor.getTextFromPage(page));
    reader.close();
    assertThat(text.toString())
        .contains(
            "General Producibility: " + evidence.get("status"),
            "general-producibility-v1",
            "FAMILY10_REVIEWED_FROZEN_PROMPT",
            "family10-reviewed-v1");
    for (Object key : dimensions.keySet()) assertThat(text.toString()).contains(key.toString());
    Map<?, ?> provenance = (Map<?, ?>) evidence.get("provenance");
    Map<?, ?> source = (Map<?, ?>) provenance.get("sourceEvidence");
    assertThat(text.toString()).contains(source.get("promptHash").toString());
    Files.createDirectories(Path.of("target/family10-pdf"));
    Files.write(Path.of("target/family10-pdf/" + goldenId + ".pdf"), pdf);
  }
}
