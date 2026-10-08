package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.openpdf.text.pdf.PdfReader;
import org.openpdf.text.pdf.parser.PdfTextExtractor;

class QualityReportPdfServiceTest {

  @Test
  void treatsTimelineSharesAsZeroToOneHundredPercentValues() {
    assertThat(QualityReportPdfService.formatStateShare(5.33)).isEqualTo("5%");
    assertThat(QualityReportPdfService.formatStateShare(20.0)).isEqualTo("20%");
    assertThat(QualityReportPdfService.isDominantStateShare(30.0)).isFalse();
    assertThat(QualityReportPdfService.isDominantStateShare(30.01)).isTrue();
  }

  @Test
  void rendersDistinctOutcomeCategoriesAndCanonicalConfidence() throws Exception {
    RuleEvaluationDto passed = evaluation("PASS_RULE", "PASS");
    RuleEvaluationDto failed = evaluation("FAIL_RULE", "FAIL");
    RuleEvaluationDto unknown = evaluation("UNKNOWN_RULE", "UNKNOWN");
    RuleEvaluationDto notApplicable = evaluation("NA_RULE", "NOT_APPLICABLE");
    RuleEvaluationDto serviceError = evaluation("ERROR_RULE", "SERVICE_ERROR");
    QualityReportDto report =
        new QualityReportDto(
            70.0,
            "NEEDS_REVISION",
            "1.7",
            0,
            0,
            1,
            Map.of("progression", 70.0),
            List.of(passed),
            List.of(failed),
            List.of(unknown),
            List.of(notApplicable),
            List.of(serviceError),
            List.of(),
            new ScoreCardDto(70.0, "Acceptable", "yellow"),
            new TimelineDataDto(
                List.of(new BeatDto(0.0, 15.0, "action", "result", 5, true)),
                List.of(),
                List.of(
                    new StateSegmentDto("short", 0.0, 0.8, 5.33),
                    new StateSegmentDto("long", 0.8, 3.8, 20.0))),
            1.0,
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            Map.of(),
            new QualityProvenanceDto("parser", "rules", "provider", "model", null, "PRE_RENDER"),
            Map.of(
                "specialized_applicability",
                Map.of(
                    "STUBBORN_RETURN_LOOP",
                    Map.of(
                        "status", "APPLICABLE",
                        "confidence", "HIGH",
                        "reason", "Box reclaim",
                        "evidenceReferences", List.of("beat_03", "beat_05")),
                    "STUBBORN_RETURN_HOOK",
                    Map.of(
                        "status", "UNKNOWN",
                        "confidence", "MEDIUM",
                        "reason", "Threat boundary unresolved",
                        "evidenceReferences", List.of("beat_04")),
                    "STUBBORN_RETURN_PAYOFF",
                    Map.of(
                        "status", "APPLICABLE",
                        "confidence", "MEDIUM",
                        "reason", "Same-rule stalemate",
                        "evidence", "legacy_ref")),
                "family8",
                Map.of(
                    "creativeQuality", Map.of("creativeScore", 70.0, "creativeGrade", "A"),
                    "evidenceCompleteness", Map.of("status", "PARTIAL", "evaluationCoverage", 0.75),
                    "renderAuthorization", Map.of(
                        "status", "BLOCKED_PENDING_EVIDENCE",
                        "reasons", List.of(Map.of(
                            "code", "REQUIRED_EVIDENCE_MISSING",
                            "message", "Visual evidence pending"))),
                    "legacy", Map.of("readiness", "READY_TO_RENDER")),
                "aggregation",
                Map.ofEntries(
                    Map.entry("score", 70.0),
                    Map.entry("scoredCount", 2),
                    Map.entry("denominator", 2),
                    Map.entry("passCount", 1),
                    Map.entry("failCount", 1),
                    Map.entry("unknownCount", 1),
                    Map.entry("notEvaluatedCount", 1),
                    Map.entry("notApplicableCount", 1),
                    Map.entry("serviceErrorCount", 0),
                    Map.entry("evaluationCoverage", 0.75),
                    Map.entry("aggregationState", "PARTIAL"))),
            Map.of(),
            Map.of(),
            0.95);

    byte[] pdf =
        new QualityReportPdfService()
            .render(new QualityReportExportRequest(report, "Luca", null, null));
    PdfReader reader = new PdfReader(pdf);
    PdfTextExtractor extractor = new PdfTextExtractor(reader);
    StringBuilder text = new StringBuilder();
    for (int page = 1; page <= reader.getNumberOfPages(); page++) {
      text.append(extractor.getTextFromPage(page));
    }

    assertThat(text).contains("Rule outcome coverage");
    assertThat(text).contains("PASS", "FAIL", "UNKNOWN", "NOT APPLICABLE", "SERVICE ERROR");
    assertThat(text).contains("Rule", "Applicability", "Confidence", "Reason", "Evidence");
    assertThat(text).contains("STUBBORN_RETURN_LOOP", "APPLICABLE", "HIGH", "Box reclaim");
    assertThat(text).contains("beat_03", "beat_05");
    assertThat(text)
        .contains("STUBBORN_RETURN_HOOK", "UNKNOWN", "MEDIUM", "Threat boundary unresolved");
    assertThat(text).contains("beat_04");
    assertThat(text)
        .contains("STUBBORN_RETURN_PAYOFF", "APPLICABLE", "MEDIUM", "Same-rule stalemate");
    assertThat(text).contains("legacy_ref");
    assertThat(text).contains("Canonical evidence confidence");
    assertThat(text).contains("Evaluation aggregation", "Scored", "Evaluation coverage", "PARTIAL");
    assertThat(text).contains("Creative quality", "Evidence completeness", "Render authorization");
    assertThat(text).contains("REQUIRED_EVIDENCE_MISSING", "Visual evidence pending");
    assertThat(text).contains("NOT EVALUATED", "NOT APPLICABLE", "SERVICE ERRORS");
    assertThat(text).contains("5%", "20%");
    assertThat(text).doesNotContain("533%", "2000%");
  }

  private static RuleEvaluationDto evaluation(String ruleId, String outcome) {
    return new RuleEvaluationDto(
        ruleId,
        ruleId,
        "test_family",
        "WARNING",
        outcome,
        outcome,
        null,
        null,
        Map.of());
  }

  @Test
  void rendersNullableFamilyScoresAndFamily8RepresentationWithoutCollapsingCoverage() throws Exception {
    java.util.Map<String, Double> familyScores = new java.util.LinkedHashMap<>();
    familyScores.put("unscored_family", null);
    familyScores.put("scored_family", 82.5);

    java.util.Map<String, Object> family8 = new java.util.LinkedHashMap<>();
    family8.put(
        "creativeQuality",
        java.util.Map.of(
            "creativeScore", 82.5,
            "creativeGrade", "A",
            "familyScores", familyScores));
    family8.put(
        "evidenceCompleteness",
        java.util.Map.of("status", "PARTIAL", "evaluationCoverage", 0.75));
    family8.put(
        "renderAuthorization",
        java.util.Map.of(
            "status", "BLOCKED_PENDING_EVIDENCE",
            "reasons",
                List.of(
                    java.util.Map.of(
                        "code", "REQUIRED_EVIDENCE_MISSING",
                        "source", "EVIDENCE_COMPLETENESS",
                        "message", "Visual evidence pending",
                        "references", List.of("first-frame", "silhouette")),
                    java.util.Map.of(
                        "code", "ASSESSMENT_TECHNICAL_FAILURE",
                        "source", "ASSESSMENT",
                        "message", "Independent validation pending",
                        "references", List.of("validation-record")))));
    family8.put("legacy", java.util.Map.of("readiness", "READY_TO_RENDER"));

    java.util.Map<String, Object> aggregation =
        java.util.Map.ofEntries(
            Map.entry("score", 70.0),
            Map.entry("scoredCount", 2),
            Map.entry("denominator", 2),
            Map.entry("passCount", 1),
            Map.entry("failCount", 1),
            Map.entry("unknownCount", 1),
            Map.entry("notEvaluatedCount", 1),
            Map.entry("notApplicableCount", 1),
            Map.entry("serviceErrorCount", 1),
            Map.entry("evaluationCoverage", 0.75),
            Map.entry("aggregationState", "PARTIAL"));
    java.util.Map<String, Object> preRender = new java.util.LinkedHashMap<>();
    preRender.put("grade", "A");
    preRender.put("readiness", "READY_TO_RENDER");
    preRender.put("assessment_coverage_percent", 75);
    preRender.put("strengths", List.of("Clear sticky-ball mechanic"));
    preRender.put("concerns", List.of("Visual evidence pending"));
    preRender.put("recommended_changes", List.of("Supply first-frame evidence"));
    preRender.put("verdict", "Evidence remains pending.");
    preRender.put("aggregation", aggregation);
    preRender.put("family8", family8);

    QualityReportDto report =
        new QualityReportDto(
            null,
            "NEEDS_REVISION",
            "1.7",
            0,
            0,
            1,
            familyScores,
            List.of(evaluation("PASS_RULE", "PASS")),
            List.of(evaluation("FAIL_RULE", "FAIL")),
            List.of(evaluation("UNKNOWN_RULE", "UNKNOWN")),
            List.of(evaluation("NA_RULE", "NOT_APPLICABLE")),
            List.of(evaluation("ERROR_RULE", "SERVICE_ERROR")),
            List.of(),
            new ScoreCardDto(null, "Not evaluated", "gray"),
            new TimelineDataDto(
                List.of(new BeatDto(0.0, 15.0, "action", "result", 5, true)),
                List.of(),
                List.of()),
            1.0,
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            Map.of(),
            new QualityProvenanceDto("parser", "rules", "provider", "model", null, "PRE_RENDER"),
            preRender,
            Map.of(),
            Map.of(),
            0.95);

    byte[] pdf =
        new QualityReportPdfService()
            .render(new QualityReportExportRequest(report, "Luca", null, null));
    PdfReader reader = new PdfReader(pdf);
    PdfTextExtractor extractor = new PdfTextExtractor(reader);
    StringBuilder text = new StringBuilder();
    for (int page = 1; page <= reader.getNumberOfPages(); page++) {
      text.append(extractor.getTextFromPage(page));
    }

    assertThat(text.toString()).contains("unscored_family", "N/A", "scored_family");
    assertThat(text.toString()).contains("Not evaluated");
    assertThat(text.toString()).contains("75% evidence coverage", "Evaluation coverage: 75%");
    assertThat(text.toString()).doesNotContain("Evaluation coverage: 0.75");
    assertThat(text.toString())
        .contains(
            "PASS: 1",
            "FAIL: 1",
            "UNKNOWN: 1",
            "NOT EVALUATED: 1",
            "NOT APPLICABLE: 1",
            "SERVICE ERRORS: 1");
    assertThat(text.toString())
        .contains(
            "Creative quality",
            "Evidence completeness",
            "Render authorization",
            "BLOCKED_PENDING_EVIDENCE");
    assertThat(text.toString())
        .contains(
            "EVIDENCE_COMPLETENESS",
            "first-frame",
            "silhouette",
            "ASSESSMENT",
            "validation-record");
  }

}
