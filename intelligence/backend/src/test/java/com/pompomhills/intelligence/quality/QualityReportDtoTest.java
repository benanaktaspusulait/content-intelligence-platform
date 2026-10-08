package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class QualityReportDtoTest {

  @Test
  void deserializesOutcomeAndNewRuleListsFromPythonSnakeCaseResponse() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    // There is no global Spring Jackson snake_case configuration in this module (no
    // spring.jackson.property-naming-strategy, no Jackson2ObjectMapperBuilder customizer, no
    // @JsonNaming/@JsonProperty on these DTOs) - confirmed by reading application.yml,
    // application-local.yml, and the full quality/ package. QualityMlClient's RestClient relies
    // on Spring Boot's autoconfigured ObjectMapper, which defaults to camelCase. So this test
    // configures SNAKE_CASE explicitly to match what would need to be true for the production
    // path to work at all.
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    String json =
        """
        {
          "overall_score": 70.0,
          "status": "NEEDS_REVISION",
          "ruleset_version": "1.3",
          "blocker_count": 0,
          "critical_count": 0,
          "warning_count": 1,
          "family_scores": {"progression": 70.0},
          "passed_rules": [
            {"rule_id": "HOOK_001", "rule_name": "Hook", "family": "hook_strength", "severity": "PASS", "outcome": "PASS", "message": "Opening is clear", "actual_value": null, "threshold_value": null}
          ],
          "failed_rules": [],
          "unknown_rules": [
            {"rule_id": "CONSISTENCY_002", "rule_name": "Character Continuity Lock",
             "family": "consistency", "severity": "CRITICAL", "outcome": "UNKNOWN",
             "message": "No rendered video available yet.", "actual_value": null,
             "threshold_value": null}
          ],
          "not_applicable_rules": [],
          "service_errors": [],
          "priority_fixes": [],
          "score_card": {"score": 70.0, "label": "Acceptable", "color": "yellow"},
          "timeline_data": {"beats": [], "consequence_markers": [], "state_segments": []},
          "parser_confidence": 0.9,
          "canonical_evidence_confidence": 0.95,
          "parser_warnings": [],
          "parser_assumptions": [],
          "top_strengths": [],
          "top_weaknesses": [],
          "evidence_missing": []
        }
        """;

    QualityReportDto dto = mapper.readValue(json, QualityReportDto.class);

    assertThat(dto.passedRules()).hasSize(1);
    assertThat(dto.passedRules().get(0).outcome()).isEqualTo("PASS");
    assertThat(dto.unknownRules()).hasSize(1);
    assertThat(dto.unknownRules().get(0).outcome()).isEqualTo("UNKNOWN");
    assertThat(dto.unknownRules().get(0).ruleId()).isEqualTo("CONSISTENCY_002");
    assertThat(dto.notApplicableRules()).isEmpty();
    assertThat(dto.serviceErrors()).isEmpty();
    assertThat(dto.parserConfidence()).isEqualTo(0.9);
    assertThat(dto.canonicalEvidenceConfidence()).isEqualTo(0.95);
    assertThat(dto.evidenceMissing()).isEmpty();
  }

  @SuppressWarnings("unchecked")
  @Test
  void preservesSpecializedApplicabilityThroughJsonRoundTrip() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    QualityReportDto original =
        mapper.readValue(
            """
            {
              "overall_score": 70.0,
              "status": "NEEDS_REVISION",
              "ruleset_version": "1.7",
              "pre_render_assessment": {
                "specialized_applicability": {
                  "STUBBORN_RETURN_LOOP": {
                    "status": "APPLICABLE",
                    "confidence": "HIGH",
                    "reason": "Box reclaim"
                  },
                  "STUBBORN_RETURN_HOOK": {
                    "status": "UNKNOWN",
                    "confidence": "MEDIUM",
                    "reason": "Threat boundary unresolved"
                  },
                  "STUBBORN_RETURN_PAYOFF": {
                    "status": "APPLICABLE",
                    "confidence": "MEDIUM",
                    "reason": "Same-rule stalemate"
                  }
                }
              }
            }
            """,
            QualityReportDto.class);

    QualityReportDto roundTripped =
        mapper.readValue(mapper.writeValueAsString(original), QualityReportDto.class);
    Map<String, Object> applicability =
        (Map<String, Object>) roundTripped.preRenderAssessment().get("specialized_applicability");

    assertThat(applicability).containsKeys(
        "STUBBORN_RETURN_LOOP", "STUBBORN_RETURN_HOOK", "STUBBORN_RETURN_PAYOFF");
    assertThat((Map<String, Object>) applicability.get("STUBBORN_RETURN_LOOP"))
        .containsEntry("status", "APPLICABLE")
        .containsEntry("confidence", "HIGH")
        .containsEntry("reason", "Box reclaim");
    assertThat((Map<String, Object>) applicability.get("STUBBORN_RETURN_HOOK"))
        .containsEntry("status", "UNKNOWN")
        .containsEntry("confidence", "MEDIUM")
        .containsEntry("reason", "Threat boundary unresolved");
    assertThat((Map<String, Object>) applicability.get("STUBBORN_RETURN_PAYOFF"))
        .containsEntry("status", "APPLICABLE")
        .containsEntry("confidence", "MEDIUM")
        .containsEntry("reason", "Same-rule stalemate");
  }

  @Test
  void normalizesMissingLegacyCollectionsForStoredReports() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    QualityReportDto dto =
        mapper.readValue(
            """
            {"overall_score": 70.0, "status": "NEEDS_REVISION", "ruleset_version": "1.0"}
            """,
            QualityReportDto.class);

    assertThat(dto.passedRules()).isEmpty();
    assertThat(dto.failedRules()).isEmpty();
    assertThat(dto.unknownRules()).isEmpty();
    assertThat(dto.notApplicableRules()).isEmpty();
    assertThat(dto.serviceErrors()).isEmpty();
    assertThat(dto.parserWarnings()).isEmpty();
    assertThat(dto.evidenceMissing()).isEmpty();
    assertThat(dto.scoreCard()).isNotNull();
    assertThat(dto.timelineData()).isNotNull();
    assertThat(dto.provenance()).isNotNull();
  }

  @SuppressWarnings("unchecked")
  @Test
  void preservesFamily7AggregationThroughJsonRoundTrip() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    QualityReportDto dto =
        mapper.readValue(
            """
            {
              "overall_score": null,
              "status": "NEEDS_REVISION",
              "ruleset_version": "1.7",
              "pre_render_assessment": {
                "aggregation": {
                  "score": null,
                  "scoredCount": 0,
                  "denominator": 0,
                  "passCount": 0,
                  "failCount": 0,
                  "unknownCount": 1,
                  "notEvaluatedCount": 0,
                  "notApplicableCount": 0,
                  "serviceErrorCount": 0,
                  "evaluationCoverage": 1.0,
                  "aggregationState": "NO_SCORED_ITEMS"
                }
              }
            }
            """,
            QualityReportDto.class);

    QualityReportDto roundTripped =
        mapper.readValue(mapper.writeValueAsString(dto), QualityReportDto.class);
    Map<String, Object> aggregation =
        (Map<String, Object>) roundTripped.preRenderAssessment().get("aggregation");

    assertThat(aggregation)
        .containsEntry("scoredCount", 0)
        .containsEntry("unknownCount", 1)
        .containsEntry("evaluationCoverage", 1.0)
        .containsEntry("aggregationState", "NO_SCORED_ITEMS");
    assertThat(aggregation.get("score")).isNull();
  }

  @SuppressWarnings("unchecked")
  @Test
  void preservesFamily8OrthogonalAxesAndAuthorizationReasons() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    QualityReportDto dto =
        mapper.readValue(
            """
            {
              "overall_score": null,
              "status": "NEEDS_REVISION",
              "ruleset_version": "1.7",
              "pre_render_assessment": {
                "family8": {
                  "creativeQuality": {"creativeScore": null, "creativeGrade": "A", "familyScores": {"producibility": null}},
                  "evidenceCompleteness": {"status": "PARTIAL", "evaluationCoverage": 0.5, "aggregation": {"aggregationState": "NO_SCORED_ITEMS"}},
                  "renderAuthorization": {
                    "status": "BLOCKED_PENDING_EVIDENCE",
                    "reasons": [{"code": "REQUIRED_EVIDENCE_MISSING", "source": "EVIDENCE", "message": "Visual evidence pending", "references": ["first-frame"]}]
                  },
                  "legacy": {"readiness": "READY_TO_RENDER"}
                }
              }
            }
            """,
            QualityReportDto.class);

    QualityReportDto roundTripped =
        mapper.readValue(mapper.writeValueAsString(dto), QualityReportDto.class);
    Map<String, Object> family8 =
        (Map<String, Object>) roundTripped.preRenderAssessment().get("family8");
    Map<String, Object> creative = (Map<String, Object>) family8.get("creativeQuality");
    Map<String, Object> authorization = (Map<String, Object>) family8.get("renderAuthorization");

    assertThat(creative.get("creativeScore")).isNull();
    assertThat(creative.get("creativeGrade")).isEqualTo("A");
    assertThat(((Map<String, Object>) creative.get("familyScores")).get("producibility")).isNull();
    assertThat(((Map<String, Object>) family8.get("evidenceCompleteness")).get("status"))
        .isEqualTo("PARTIAL");
    assertThat(authorization.get("status")).isEqualTo("BLOCKED_PENDING_EVIDENCE");
    assertThat(((java.util.List<Map<String, Object>>) authorization.get("reasons")).get(0))
        .containsEntry("code", "REQUIRED_EVIDENCE_MISSING")
        .containsEntry("message", "Visual evidence pending");
  }


  @SuppressWarnings("unchecked")
  @Test
  void preservesNullableScoresAggregationAndFamily8AxesThroughJsonRoundTrip() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    QualityReportDto original =
        mapper.readValue(
            """
            {
              "overall_score": null,
              "status": "NEEDS_REVISION",
              "ruleset_version": "1.7",
              "family_scores": {"scored_family": 82.5, "unscored_family": null},
              "score_card": {"score": null, "label": "Not evaluated", "color": "gray"},
              "pre_render_assessment": {
                "aggregation": {
                  "score": null,
                  "scoredCount": 2,
                  "denominator": 2,
                  "passCount": 1,
                  "failCount": 1,
                  "unknownCount": 1,
                  "notEvaluatedCount": 1,
                  "notApplicableCount": 1,
                  "serviceErrorCount": 1,
                  "evaluationCoverage": 0.75,
                  "aggregationState": "PARTIAL"
                },
                "family8": {
                  "creativeQuality": {
                    "creativeScore": null,
                    "creativeGrade": "A",
                    "familyScores": {"unscored_family": null}
                  },
                  "evidenceCompleteness": {
                    "status": "PARTIAL",
                    "evaluationCoverage": 0.75,
                    "aggregation": {"notEvaluatedCount": 1}
                  },
                  "renderAuthorization": {
                    "status": "BLOCKED_PENDING_EVIDENCE",
                    "reasons": [
                      {
                        "code": "REQUIRED_EVIDENCE_MISSING",
                        "source": "EVIDENCE_COMPLETENESS",
                        "message": "Visual evidence pending",
                        "references": ["first-frame", "silhouette"]
                      },
                      {
                        "code": "ASSESSMENT_TECHNICAL_FAILURE",
                        "source": "ASSESSMENT",
                        "message": "Independent validation pending",
                        "references": ["validation-record"]
                      }
                    ]
                  },
                  "legacy": {"readiness": "READY_TO_RENDER"}
                }
              }
            }
            """,
            QualityReportDto.class);

    QualityReportDto roundTripped =
        mapper.readValue(mapper.writeValueAsString(original), QualityReportDto.class);
    var json = mapper.readTree(mapper.writeValueAsString(roundTripped));
    Map<String, Object> preRender = roundTripped.preRenderAssessment();
    Map<String, Object> aggregation = (Map<String, Object>) preRender.get("aggregation");
    Map<String, Object> family8 = (Map<String, Object>) preRender.get("family8");
    Map<String, Object> creative = (Map<String, Object>) family8.get("creativeQuality");
    Map<String, Object> evidence = (Map<String, Object>) family8.get("evidenceCompleteness");
    Map<String, Object> authorization = (Map<String, Object>) family8.get("renderAuthorization");

    assertThat(json.has("overall_score")).isTrue();
    assertThat(json.get("overall_score").isNull()).isTrue();
    assertThat(json.get("score_card").has("score")).isTrue();
    assertThat(json.get("score_card").get("score").isNull()).isTrue();
    assertThat(json.get("family_scores").get("unscored_family").isNull()).isTrue();
    assertThat(json.get("pre_render_assessment").get("family8").get("creativeQuality")
        .get("creativeScore").isNull()).isTrue();

    assertThat(aggregation)
        .containsEntry("scoredCount", 2)
        .containsEntry("denominator", 2)
        .containsEntry("passCount", 1)
        .containsEntry("failCount", 1)
        .containsEntry("unknownCount", 1)
        .containsEntry("notEvaluatedCount", 1)
        .containsEntry("notApplicableCount", 1)
        .containsEntry("serviceErrorCount", 1)
        .containsEntry("evaluationCoverage", 0.75)
        .containsEntry("aggregationState", "PARTIAL");
    assertThat(creative.get("creativeScore")).isNull();
    assertThat(creative.get("creativeGrade")).isEqualTo("A");
    assertThat(((Map<String, Object>) creative.get("familyScores")).get("unscored_family"))
        .isNull();
    assertThat(evidence.get("status")).isEqualTo("PARTIAL");
    assertThat(evidence.get("evaluationCoverage")).isEqualTo(0.75);
    assertThat(authorization.get("status")).isEqualTo("BLOCKED_PENDING_EVIDENCE");
    var reasons = (java.util.List<Map<String, Object>>) authorization.get("reasons");
    assertThat(reasons).hasSize(2);
    assertThat(reasons.get(0))
        .containsEntry("code", "REQUIRED_EVIDENCE_MISSING")
        .containsEntry("source", "EVIDENCE_COMPLETENESS")
        .containsEntry("message", "Visual evidence pending")
        .containsEntry("references", java.util.List.of("first-frame", "silhouette"));
    assertThat(reasons.get(1))
        .containsEntry("code", "ASSESSMENT_TECHNICAL_FAILURE")
        .containsEntry("source", "ASSESSMENT")
        .containsEntry("message", "Independent validation pending")
        .containsEntry("references", java.util.List.of("validation-record"));
  }

  @Test
  void preservesNullableScoresInStoredSnapshotRoundTrip() {
    java.util.Map<String, Double> familyScores = new java.util.LinkedHashMap<>();
    familyScores.put("unscored_family", null);
    QualityReportDto original =
        new QualityReportDto(
            null,
            "NEEDS_REVISION",
            "1.7",
            0,
            0,
            0,
            familyScores,
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            new ScoreCardDto(null, "Not evaluated", "gray"),
            new TimelineDataDto(List.of(), List.of(), List.of()),
            1.0,
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            Map.of(),
            new QualityProvenanceDto("parser", "rules", "provider", "model", null, "PRE_RENDER"));

    String stored = QualityReportSnapshots.toJson(original);
    QualityReportDto restored = QualityReportSnapshots.fromJson(stored);

    assertThat(stored).contains("\"overallScore\":null", "\"score\":null");
    assertThat(restored.overallScore()).isNull();
    assertThat(restored.scoreCard().score()).isNull();
    assertThat(restored.familyScores().get("unscored_family")).isNull();
  }

}