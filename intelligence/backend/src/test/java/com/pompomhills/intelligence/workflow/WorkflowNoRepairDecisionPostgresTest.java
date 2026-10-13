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
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
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

  private org.springframework.transaction.PlatformTransactionManager attemptManager;
  private JdbcClient jdbc;
  private WorkflowService service;
  private QualityMlClient ml;
  private ContentPromptQueryService prompts;
  private UUID analysisId;
  private String analysisBinding;

  @BeforeEach
  void setUp() {
    var dataSource =
        new DriverManagerDataSource(DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
    jdbc = JdbcClient.create(dataSource);
    attemptManager=new org.springframework.jdbc.datasource.DataSourceTransactionManager(dataSource);
    jdbc.sql("DROP TABLE IF EXISTS post_family_workflow_events").update();
    jdbc.sql("DROP TABLE IF EXISTS prompt_versions").update();
    jdbc.sql("CREATE TABLE prompt_versions (content_id bigint NOT NULL, id bigint NOT NULL, raw_text text NOT NULL, PRIMARY KEY(content_id,id))").update();
    jdbc.sql("INSERT INTO prompt_versions(content_id,id,raw_text) VALUES(10,10,:prompt)")
        .param("prompt", PROMPT).update();
    jdbc.sql(
            "CREATE TABLE post_family_workflow_events (id uuid PRIMARY KEY, kind varchar(80) NOT NULL,"
                + " binding_sha256 varchar(128), payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now())")
        .update();
    prompts = mock(ContentPromptQueryService.class);
    ml = mock(QualityMlClient.class);
    when(prompts.load(10L, 10L))
        .thenReturn(new ContentPromptSnapshot("v1", 10, "Mimi", "REEL", "DRAFT", 10, 1,
            PROMPT, "{}", "a".repeat(64)));
    service = new WorkflowService(prompts, ml,
        mock(MediaContentService.class), mock(VideoService.class),
        new ObjectMapper().findAndRegisterModules(), jdbc, null);
    org.springframework.test.util.ReflectionTestUtils.setField(service,"attemptTransactions",attemptManager);
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

  @Test
  void creativeOptimizationRequiresExplicitAuthorizationAndCannotUseGenericRoleEndpoint() {
    assertThatThrownBy(() -> service.generateCreativeOptimization(
        analysisId, Map.of("contentId", 10, "promptVersionId", 10, "maxCostUsd", .25), Map.of()))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Explicit creative optimization authorization");
    assertThatThrownBy(() -> service.creativeRole(Map.of(
        "role", "PROMPT_OPTIMIZATION",
        "generationAuthorized", true,
        "maxCostUsd", .25,
        "text", PROMPT,
        "context", Map.of("analysisRunId", analysisId.toString(), "promptVersionId", 10, "essentialEvents", List.of("event")))))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("source-bound Step 6 workflow");
    verifyNoInteractions(ml);
  }

  @Test
  void previewsTwoCandidatesLocallyAgainstSameRulesetWithoutPersistingReviewsOrVersions() throws Exception {
    String firstEvent = "Mimi attaches a note to the cabinet.";
    String secondEvent = "Every pull doubles the notes.";
    String finalEvent = "Mimi sneezes and notes land on the cabinet.";
    var events = List.of(
        Map.of("id", "beat_01", "action", firstEvent),
        Map.of("id", "beat_02", "action", secondEvent),
        Map.of("id", "beat_03", "action", finalEvent));
    String sourcePrompt = String.join(" ", List.of(PROMPT, firstEvent, secondEvent, finalEvent));
    when(prompts.load(10L, 10L))
        .thenReturn(new ContentPromptSnapshot("v1", 10, "Mimi", "REEL", "DRAFT", 10, 1,
            sourcePrompt, "{}", "unused"));
    var bound = Map.<String, Object>of(
        "prompt", sourcePrompt,
        "profile", "post-family-v1",
        "contentProfile", "ABSURD_PHYSICS",
        "generator", "SEEDANCE_2_0_MINI",
        "desiredDuration", 15,
        "settings", Map.of("aspectRatio", "9:16"),
        "structuredPlan", Map.of("beats", events),
        "references", List.of(),
        "acceptedStartFrame", true,
        "authorizationEvidence", Map.of("renderAuthorization", "AUTHORIZED"));
    var source = Map.of(
        "sha256", HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(sourcePrompt.getBytes(StandardCharsets.UTF_8))));
    var baseline = new LinkedHashMap<String, Object>();
    service.saveProductionSettings(Map.of("contentId",10,"promptVersionId",10,"contentProfile","ABSURD_PHYSICS"));
    baseline.put("boundRequest", bound);
    baseline.put("productionEvidence", Map.of("source", source));
    baseline.put("canonicalRuleEvaluation", Map.of("rulesetVersion", "1.7", "score", 85, "grade", "B"));
    baseline.put("contentId", 10);
    baseline.put("promptVersionId", 10);
    jdbc.sql("UPDATE post_family_workflow_events SET payload=payload || CAST(:payload AS jsonb) WHERE id=:id")
        .param("id", analysisId)
        .param("payload", new ObjectMapper().writeValueAsString(baseline))
        .update();
    var candidates = List.of(
        Map.of("candidateId", "candidate-a", "title", "Opening", "hypothesis", "Clarify the opening frame.", "prompt", sourcePrompt + "\nA"),
        Map.of("candidateId", "candidate-b", "title", "Pacing", "hypothesis", "Spread out the escalation.", "prompt", sourcePrompt + "\nB"));
    when(ml.workflow(eq("creative-role"), anyMap()))
        .thenThrow(new com.pompomhills.intelligence.quality.MlWorkflowException(409,Map.of(
            "detail","Source-plan validation failed before dispatch","category","SOURCE_PLAN_VALIDATION_FAILED","providerDispatched",false,"retrySafe",true)))
        .thenReturn(Map.of("role", "PROMPT_OPTIMIZATION", "provider", "openai", "model", "fixture",
            "result", Map.of("candidates", candidates), "attemptState", "SAVED"));
    when(ml.workflow(eq("source-plan"), anyMap()))
        .thenAnswer(invocation -> {
          var request = invocation.getArgument(1, Map.class);
          return Map.of("videoPlanIR", Map.of("beats", List.of(Map.of(
              "sourceQuote", request.get("prompt"), "sourceAction", "Mimi attaches a note"))));
        });
    when(ml.workflow(eq("review"), anyMap()))
        .thenReturn(Map.of(
            "canonicalRuleEvaluation", Map.of("status", "EVALUATED", "rulesetVersion", "1.7", "score", 86, "grade", "B",
                "failedRules", List.of(), "unknownRules", List.of()),
            "executionReview", Map.of("status", "PASS", "findings", List.of()),
            "planQuality", Map.of("status", "RISKY", "findings", List.of()),
            "generation", Map.of("capabilityStatus", "SUPPORTED"),
            "family8", Map.of("renderAuthorization", Map.of("status", "BLOCKED_PENDING_EVIDENCE")),
            "actualRenderQuality", Map.of("status", "UNKNOWN"),
            "audienceOutcome", Map.of("status", "UNKNOWN")));
    var generationRequest =
        Map.<String, Object>of(
            "contentId", 10, "promptVersionId", 10, "operatorAuthorized", true, "maxCostUsd", .25);
    var provenance =
        Map.<String, Object>of(
            "approvedStoryText", "Approved Mimi story",
            "approvalRecordId", "approval-1",
            "storyRevisionId", "revision-1");
    var failedAttempt = service.generateCreativeOptimization(analysisId, generationRequest, provenance);
    assertThat(failedAttempt)
        .containsEntry("optimizationFailed", true)
        .containsEntry("attemptState", "PRE_DISPATCH_REJECTED")
        .containsEntry("providerCallOccurred", false);
    assertThat(jdbc.sql(
            "SELECT payload->>'attemptState' FROM post_family_workflow_events "
                + "WHERE kind='CREATIVE_ROLE' AND payload->>'role'='PROMPT_OPTIMIZATION' ORDER BY created_at DESC,id DESC LIMIT 1")
        .query(String.class).single()).isEqualTo("PRE_DISPATCH_REJECTED");

    jdbc.sql("ALTER TABLE post_family_workflow_events ADD CONSTRAINT reject_comparison CHECK (kind <> 'CREATIVE_OPTIMIZATION')").update();
    var transaction=new org.springframework.transaction.support.TransactionTemplate(attemptManager);
    assertThatThrownBy(() -> transaction.execute(status -> service.generateCreativeOptimization(analysisId,generationRequest,provenance)))
        .isInstanceOf(IllegalStateException.class).hasMessageContaining("CANDIDATE_PERSISTENCE_FAILED");
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='CREATIVE_ROLE' AND payload->>'attemptState'='SAVED'").query(Long.class).single()).isEqualTo(1L);
    jdbc.sql("ALTER TABLE post_family_workflow_events DROP CONSTRAINT reject_comparison").update();
    var comparison = service.generateCreativeOptimization(analysisId, generationRequest, provenance);
    assertThat(comparison.get("rulesetVersion")).isEqualTo("1.7");
    assertThat((List<?>) comparison.get("candidates")).hasSize(2);
    assertThat(String.valueOf(((Map<?, ?>) ((List<?>) comparison.get("candidates")).get(0)).get("diff"))).contains("candidate-a");
    assertThat(String.valueOf(service.latestCreativeOptimization(analysisId).get("comparison"))).contains("candidate-a");
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='REVIEW'")
        .query(Long.class).single()).isEqualTo(1L);
    assertThat(jdbc.sql("SELECT count(*) FROM prompt_versions").query(Long.class).single()).isEqualTo(1L);
    var roleCalls=org.mockito.ArgumentCaptor.forClass(Map.class);
    verify(ml, times(2)).workflow(eq("creative-role"), roleCalls.capture());
    assertThat(roleCalls.getAllValues()).allSatisfy(call -> assertThat((Map<String,Object>)call.get("context")).containsEntry("optimizationGenerationContractVersion","profile-ownership-v1"));
    var reviewCalls = org.mockito.ArgumentCaptor.forClass(Map.class);
    verify(ml, times(4)).workflow(eq("review"), reviewCalls.capture());
    assertThat(reviewCalls.getAllValues())
        .allSatisfy(call -> assertThat(call.get("acceptedStartFrame")).isEqualTo(false))
        .allSatisfy(call -> assertThat(call.get("authorizationEvidence")).isNull());
  }

  @Test
  @org.junit.jupiter.api.condition.EnabledIfSystemProperty(named="optimization.liveMock", matches="true")
  void actualSavedSettingsThroughDeployedMlAndComparisonPersistenceWithZeroPaidCalls() throws Exception {
    var mapper = new ObjectMapper().findAndRegisterModules();
    var fixture = mapper.readValue(getClass().getResourceAsStream("/optimization-c7-profile.json"), Map.class);
    var baseline = (Map<String,Object>) fixture.get("baseline");
    var bound = (Map<String,Object>) baseline.get("boundRequest");
    String sourcePrompt = String.valueOf(bound.get("prompt"));
    jdbc.sql("UPDATE prompt_versions SET raw_text=:text WHERE id=10").param("text",sourcePrompt).update();
    jdbc.sql("UPDATE post_family_workflow_events SET payload=CAST(:payload AS jsonb) WHERE id=:id")
        .param("payload",mapper.writeValueAsString(baseline)).param("id",analysisId).update();
    when(prompts.load(10L,10L)).thenReturn(new ContentPromptSnapshot("v1",10,"Mimi","REEL","DRAFT",10,1,sourcePrompt,"{}","unused"));
    service.saveProductionSettings((Map<String,Object>)fixture.get("productionSettings"));
    var providerValues = List.of(
        Map.of("candidateId","candidate-a","title","Opening clarity","hypothesis","Extreme close-up of existing contact anomaly", "prompt",sourcePrompt.replace("[close-up on", "[extreme close-up on")),
        Map.of("candidateId","candidate-b","title","Escalation timing","hypothesis","More time on separation before multiplication", "prompt",sourcePrompt.replace("2-5s:","2-6s:").replace("5-10s:","6-10s:")));
    var http = java.net.http.HttpClient.newBuilder().version(java.net.http.HttpClient.Version.HTTP_1_1).build();
    when(ml.workflow(anyString(),anyMap())).thenAnswer(invocation -> {
      String endpoint=invocation.getArgument(0); Map<String,Object> body=invocation.getArgument(1);
      if (endpoint.equals("creative-role")) {
        assertThat((Map<String,Object>)body.get("context")).containsEntry("optimizationGenerationContractVersion","profile-ownership-v1");
        body=Map.of("text",body.get("text"),"context",body.get("context"),"providerResult",Map.of("candidates",providerValues),"diagnostics",Map.of("model","mock-saved-response"));
        endpoint="optimization-recovery";
      }
      var response=http.send(java.net.http.HttpRequest.newBuilder(java.net.URI.create("http://localhost:8000/api/v1/workflow/"+endpoint))
          .header("Content-Type","application/json").POST(java.net.http.HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build(),java.net.http.HttpResponse.BodyHandlers.ofString());
      assertThat(response.statusCode()).as(response.body()).isEqualTo(200);
      return mapper.readValue(response.body(),Map.class);
    });
    var request=Map.<String,Object>of("contentId",10,"promptVersionId",10,"operatorAuthorized",true,"maxCostUsd",.2);
    var attempt=(Map<String,Object>)((Map<String,Object>)fixture.get("attempt")).get("payload");
    var ctx=(Map<String,Object>)((Map<String,Object>)attempt.get("sourceRequest")).get("context");
    var provenance=Map.<String,Object>of("approvedStoryText",ctx.get("approvedStoryText"),"approvalRecordId",ctx.get("storyApprovalRecordId"),"storyRevisionId",ctx.get("storyRevisionId"));
    var comparison=service.generateCreativeOptimization(analysisId,request,provenance);
    assertThat(comparison).doesNotContainKey("optimizationFailed");
    var candidates=(List<Map<String,Object>>)comparison.get("candidates");
    assertThat(candidates).hasSize(2);
    for(var candidate:candidates) {
      assertThat((Map<String,Object>)candidate.get("sourcePlan")).containsEntry("contentProfile","ABSURD_PHYSICS");
      var review=(Map<String,Object>)candidate.get("review");
      assertThat((Map<String,Object>)review.get("canonicalRuleEvaluation")).containsEntry("status","EVALUATED").containsEntry("rulesetVersion","1.7");
      assertThat(String.valueOf(review.get("family8"))).contains("BLOCKED");
      assertThat(String.valueOf(candidate.get("fidelity"))).contains("SEMANTIC_FIDELITY_UNKNOWN");
    }
    var replay=service.generateCreativeOptimization(analysisId,request,provenance);
    assertThat(String.valueOf(replay.get("recordId"))).isEqualTo(String.valueOf(comparison.get("recordId")));
    verify(ml,times(1)).workflow(eq("creative-role"),anyMap());
    assertThat(jdbc.sql("SELECT count(*) FROM prompt_versions").query(Long.class).single()).isEqualTo(1L);
    assertThat(jdbc.sql("SELECT raw_text FROM prompt_versions WHERE id=10").query(String.class).single()).isEqualTo(sourcePrompt);
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='CREATIVE_OPTIMIZATION'").query(Long.class).single()).isEqualTo(1L);
    // Recover a mocked rejected response through the real zero-provider path.
    var stored = mapper.convertValue(attempt, new com.fasterxml.jackson.core.type.TypeReference<Map<String,Object>>(){});
    var savedRequest=(Map<String,Object>)stored.get("sourceRequest");
    ((Map<String,Object>)savedRequest.get("context")).put("analysisRunId",analysisId.toString());
    var diagnostic=(Map<String,Object>)stored.get("attemptDiagnostics");
    diagnostic.put("providerResultForRecovery",Map.of("candidates",providerValues));
    UUID recoveryId=UUID.randomUUID();
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES(:id,'CREATIVE_ROLE',CAST(:payload AS jsonb))")
        .param("id",recoveryId).param("payload",mapper.writeValueAsString(stored)).update();
    var recoveryRequest=new LinkedHashMap<String,Object>(request);recoveryRequest.put("recoverAttemptRecordId",recoveryId.toString());
    var recovered=service.generateCreativeOptimization(analysisId,recoveryRequest,provenance);
    assertThat(recovered).doesNotContainKey("optimizationFailed");
    var recoveredReplay=service.generateCreativeOptimization(analysisId,recoveryRequest,provenance);
    assertThat(String.valueOf(recoveredReplay.get("recordId"))).isEqualTo(String.valueOf(recovered.get("recordId")));
    verify(ml,times(1)).workflow(eq("optimization-recovery"),anyMap());
    verify(ml,times(1)).workflow(eq("creative-role"),anyMap());
    // Missing budget evidence and stale prompt association fail before local recovery.
    diagnostic.remove("actualCostUsd");
    jdbc.sql("UPDATE post_family_workflow_events SET payload=CAST(:payload AS jsonb) WHERE id=:id")
        .param("id",recoveryId).param("payload",mapper.writeValueAsString(stored)).update();
    assertThatThrownBy(()->service.generateCreativeOptimization(analysisId,recoveryRequest,provenance)).hasMessageContaining("budget and usage evidence");
    ((Map<String,Object>)savedRequest.get("context")).put("promptVersionId",11);
    jdbc.sql("UPDATE post_family_workflow_events SET payload=CAST(:payload AS jsonb) WHERE id=:id")
        .param("id",recoveryId).param("payload",mapper.writeValueAsString(stored)).update();
    assertThatThrownBy(()->service.generateCreativeOptimization(analysisId,recoveryRequest,provenance)).hasMessageContaining("stale promptVersionId");
    verify(ml,times(1)).workflow(eq("optimization-recovery"),anyMap());
    var envelope=service.latestCreativeOptimization(analysisId);
    java.nio.file.Files.writeString(java.nio.file.Path.of("/tmp/c7-e2e-comparison.json"),mapper.writeValueAsString(envelope));
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
