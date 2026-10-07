package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
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
}
