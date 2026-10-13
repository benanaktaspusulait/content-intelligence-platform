package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.content.ContentPromptSnapshot;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@Testcontainers(disabledWithoutDocker = true)
class WorkflowNoRepairDecisionPostgresTest {
  private static final String PROMPT = "A saved immutable prompt with a source-backed goal.";
  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  private JdbcClient jdbc;
  private WorkflowService service;
  private UUID analysisId;
  private String analysisBinding;

  @BeforeEach
  void setUp() {
    var dataSource =
        new DriverManagerDataSource(DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
    jdbc = JdbcClient.create(dataSource);
    jdbc.sql("DROP TABLE IF EXISTS post_family_workflow_events").update();
    jdbc.sql("DROP TABLE IF EXISTS prompt_versions").update();
    jdbc.sql("CREATE TABLE prompt_versions (content_id bigint NOT NULL, id bigint NOT NULL, raw_text text NOT NULL, PRIMARY KEY(content_id,id))").update();
    jdbc.sql("INSERT INTO prompt_versions(content_id,id,raw_text) VALUES(10,10,:prompt)")
        .param("prompt", PROMPT).update();
    jdbc.sql(
            "CREATE TABLE post_family_workflow_events (id uuid PRIMARY KEY, kind varchar(80) NOT NULL,"
                + " binding_sha256 varchar(128), payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now())")
        .update();
    var prompts = mock(ContentPromptQueryService.class);
    when(prompts.load(10L, 10L))
        .thenReturn(new ContentPromptSnapshot("v1", 10, "Mimi", "REEL", "DRAFT", 10, 1,
            PROMPT, "{}", "a".repeat(64)));
    service = new WorkflowService(prompts, mock(QualityMlClient.class),
        mock(MediaContentService.class), mock(VideoService.class),
        new ObjectMapper().findAndRegisterModules(), jdbc, null);
    analysisId = UUID.randomUUID();
    analysisBinding = "analysis-binding";
    insertReview(analysisId, analysisBinding, "85", "EVALUATED", List.of(), "HYPOTHESIS", "now()");
  }

  @Test
  void persistsAnExplicitVersionAndAnalysisBoundDecisionIdempotentlyAndMarksItStale() {
    var first = service.saveProductionReviewDecision(request(analysisId, analysisBinding));
    var repeated = service.saveProductionReviewDecision(request(analysisId, analysisBinding));

    assertThat(first).containsEntry("decisionType", "NO_TEXT_REPAIR_JUSTIFIED")
        .containsEntry("decision", "NO_TEXT_REPAIR_JUSTIFIED")
        .containsEntry("provenance", "OPERATOR_CONFIRMED")
        .containsEntry("stale", false)
        .containsEntry("analysisRunId", analysisId.toString())
        .containsKeys("savedAt", "recordId");
    assertThat(String.valueOf(repeated.get("recordId"))).isEqualTo(String.valueOf(first.get("recordId")));
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='PRODUCTION_REVIEW_DECISION'")
        .query(Long.class).single()).isEqualTo(1L);
    var activeDecisions = (List<?>) service.getProductionReviewDecisions(10L, 10L).get("decisions");
    var activeDecision = (Map<?, ?>) activeDecisions.get(0);
    assertThat(activeDecision.get("stale")).isEqualTo(false);
    assertThat(String.valueOf(activeDecision.get("analysisRunId"))).isEqualTo(analysisId.toString());
    assertThat(activeDecision.containsKey("evidenceResolved")).isFalse();
    assertThat(jdbc.sql("SELECT payload->'family8'->'renderAuthorization'->>'status' "
            + "FROM post_family_workflow_events WHERE id=:id")
        .param("id", analysisId)
        .query(String.class).single()).isEqualTo("BLOCKED_PENDING_EVIDENCE");

    UUID newer = UUID.randomUUID();
    insertReview(newer, "new-analysis-binding", "86", "EVALUATED", List.of(), "HYPOTHESIS",
        "now() + interval '1 second'");
    var staleDecisions = (List<?>) service.getProductionReviewDecisions(10L, 10L).get("decisions");
    assertThat(((Map<?, ?>) staleDecisions.get(0)).get("stale")).isEqualTo(true);
    assertThatThrownBy(() -> service.saveProductionReviewDecision(request(analysisId, analysisBinding)))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("analysis is stale");
  }

  @Test
  void rejectsMissingConfirmationCrossBoundRunsAndFailedCanonicalEvidence() {
    var noConsent = request(analysisId, analysisBinding);
    noConsent.put("operatorConfirmed", false);
    assertThatThrownBy(() -> service.saveProductionReviewDecision(noConsent))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Explicit Step 6");

    var wrongBinding = request(analysisId, "different");
    assertThatThrownBy(() -> service.saveProductionReviewDecision(wrongBinding))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("analysis binding");

    UUID failed = UUID.randomUUID();
    insertReview(failed, "failed-binding", "80", "EVALUATED",
        List.of(Map.of("ruleId", "BLOCKING_TEXT_RULE")), "HYPOTHESIS", "now() + interval '1 second'");
    assertThatThrownBy(() -> service.saveProductionReviewDecision(request(failed, "failed-binding")))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("failed or unavailable");
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='PRODUCTION_REVIEW_DECISION'")
        .query(Long.class).single()).isZero();
  }

  @Test
  void rejectsTechnicalFailuresAndRequiredPromptRepairWithoutResolvingOutstandingEvidence() {
    UUID technical = UUID.randomUUID();
    insertReview(technical, "technical-binding", "85", "EVALUATED", List.of(), "HYPOTHESIS",
        "BLOCKED_TECHNICAL_FAILURE", List.of(), "now() + interval '1 second'");
    assertThatThrownBy(() -> service.saveProductionReviewDecision(request(technical, "technical-binding")))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("failed or unavailable");

    UUID requiredRepair = UUID.randomUUID();
    insertReview(requiredRepair, "repair-binding", "85", "EVALUATED", List.of(), "HYPOTHESIS",
        "BLOCKED_PENDING_EVIDENCE",
        List.of(Map.of("scope", "PROMPT_TEXT", "repairable", true,
            "applicability", "APPLICABLE", "repairability", "REQUIRED")),
        "now() + interval '2 seconds'");
    assertThatThrownBy(() -> service.saveProductionReviewDecision(request(requiredRepair, "repair-binding")))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("failed or unavailable");
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='PRODUCTION_REVIEW_DECISION'")
        .query(Long.class).single()).isZero();
  }

  private Map<String, Object> request(UUID runId, String binding) {
    return new java.util.LinkedHashMap<>(Map.of(
        "contentId", 10,
        "promptVersionId", 10,
        "decisionType", "NO_TEXT_REPAIR_JUSTIFIED",
        "decisionId", "step6-no-text-repair",
        "decision", "NO_TEXT_REPAIR_JUSTIFIED",
        "operatorConfirmed", true,
        "analysisRunId", runId.toString(),
        "analysisBindingHash", binding));
  }

  private void insertReview(UUID id, String binding, String score, String status,
      List<Map<String, Object>> failed, String planStatus, String createdAtExpression) {
    insertReview(id, binding, score, status, failed, planStatus, "BLOCKED_PENDING_EVIDENCE",
        List.of(), createdAtExpression);
  }

  private void insertReview(UUID id, String binding, String score, String status,
      List<Map<String, Object>> failed, String planStatus, String authorizationStatus,
      List<Map<String, Object>> findings, String createdAtExpression) {
    var payload = Map.<String, Object>of(
        "recordId", id.toString(),
        "contentId", 10,
        "promptVersionId", 10,
        "bindingHash", binding,
        "reviewStatus", authorizationStatus.contains("TECHNICAL_FAILURE")
            ? "ASSESSMENT_TECHNICAL_FAILURE" : "COMPLETED",
        "canonicalRuleEvaluation", Map.of("score", score, "status", status, "failedRules", failed),
        "planQuality", Map.of("status", planStatus, "findings", findings),
        "family8", Map.of("renderAuthorization", Map.of("status", authorizationStatus,
            "reasons", List.of(Map.of("code", "REQUIRED_EVIDENCE_MISSING", "source", "EXECUTION_INPUTS")))));
    try {
      jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload,created_at) "
              + "VALUES(:id,'REVIEW',:binding,CAST(:payload AS jsonb)," + createdAtExpression + ")")
          .param("id", id)
          .param("binding", binding)
          .param("payload", new ObjectMapper().writeValueAsString(payload))
          .update();
    } catch (Exception error) {
      throw new IllegalStateException(error);
    }
  }
}
