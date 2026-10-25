package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.video.VideoService;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;

@Testcontainers(disabledWithoutDocker = true)
class IdeaCandidatePostgresTest {
  @Container
  static final PostgreSQLContainer<?> DATABASE = new PostgreSQLContainer<>("postgres:17-alpine");

  JdbcClient jdbc;
  IdeaCandidateService service;
  IdeaDraftService drafts;
  QualityMlClient evaluationMl;
  DataSourceTransactionManager manager;
  UUID draft;
  String workspace = "test/isolated-idea-batch";
  ObjectMapper json = new ObjectMapper();

  @BeforeEach
  void setup() throws Exception {
    var ds =
        new DriverManagerDataSource(
            DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
    jdbc = JdbcClient.create(ds);
    manager = new DataSourceTransactionManager(ds);
    jdbc.sql("DROP TABLE IF EXISTS post_family_workflow_events CASCADE").update();
    jdbc.sql("DROP TABLE IF EXISTS characters").update();
    jdbc.sql(
            "CREATE TABLE post_family_workflow_events(id uuid PRIMARY KEY,kind varchar(40),binding_sha256 varchar(64),payload jsonb,created_at timestamptz DEFAULT clock_timestamp())")
        .update();
    for (String statement :
        Files.readString(Path.of("src/main/resources/db/migration/V73__native_idea_candidates.sql"))
            .split(";")) if (!statement.isBlank()) jdbc.sql(statement).update();
    jdbc.sql(
            "CREATE TABLE characters(id uuid PRIMARY KEY,name text,status text,notes text,active boolean)")
        .update();
    jdbc.sql(
            "INSERT INTO characters VALUES('00000000-0000-0000-0000-000000000003','Mimi','UNTESTED','test',true)")
        .update();
    drafts =
        new IdeaDraftService(
            jdbc, json, mock(VideoService.class), mock(ContentWorkspaceController.class));
    evaluationMl = mock(QualityMlClient.class);
    when(evaluationMl.workflow(eq("idea-evaluation"), anyMap()))
        .thenAnswer(
            call -> {
              var candidate =
                  IdeaCandidateService.map(((Map<?, ?>) call.getArgument(1)).get("candidate"));
              var result = new LinkedHashMap<String, Object>();
              result.put("candidateId", candidate.get("candidateId"));
              result.put(
                  "sourcePayloadSha256",
                  java.util.HexFormat.of()
                      .formatHex(
                          java.security.MessageDigest.getInstance("SHA-256")
                              .digest(
                                  json.writer()
                                      .with(
                                          com.fasterxml.jackson.databind.SerializationFeature
                                              .ORDER_MAP_ENTRIES_BY_KEYS)
                                      .writeValueAsBytes(candidate.get("payload")))));
              result.put("providerCalls", 0);
              result.put("additionalCostUsd", 0);
              result.put("status", "PENDING_EVIDENCE");
              result.put("eligible", false);
              result.put("policyVersion", "TEST_TRANSPORT_ONLY");
              result.put(
                  "gates",
                  java.util.stream.IntStream.range(0, 10)
                      .mapToObj(
                          i ->
                              Map.of(
                                  "gate",
                                  "test-transport-" + i,
                                  "status",
                                  "UNKNOWN",
                                  "mandatory",
                                  true))
                      .toList());
              return result;
            });
    service = new IdeaCandidateService(jdbc, json, drafts, manager, evaluationMl);
    draft = UUID.randomUUID();
    new TransactionTemplate(manager)
        .execute(
            s ->
                drafts.save(
                    Map.of(
                        "draftId",
                        draft.toString(),
                        "expectedRevision",
                        0,
                        "state",
                        Map.of(
                            "inputMode",
                            "IDEA",
                            "idea",
                            "Test brief",
                            "workspacePath",
                            workspace))));
  }

  Map<String, Object> request(int count) {
    return Map.of(
        "role",
        "IDEA",
        "text",
        "Test brief",
        "context",
        Map.of(
            "sourceIdeaDraftId",
            draft.toString(),
            "sourceIdeaRevision",
            1,
            "workspacePath",
            workspace,
            "requestedAlternativeCount",
            count,
            "mainCharacterId",
            "00000000-0000-0000-0000-000000000003"));
  }

  Map<String, Object> payload(int i) {
    var payload =
        new LinkedHashMap<String, Object>(
            Map.of(
                "title",
                "Fixture " + i,
                "concept",
                "Mimi tries to put away item " + i,
                "firstStaticFrame",
                "Mimi already struggles with item " + i,
                "viewerQuestion",
                "How will item " + i + " settle?",
                "discovery",
                "Changing one arrangement changes the consequence " + i,
                "payoff",
                "Item " + i + " finally settles in an unexpected visible position",
                "productionRisk",
                "Unverified object contact " + i,
                "everydayGoal",
                "Put away item " + i,
                "impossibleRule",
                "Rule " + i));
    payload.put("frameZeroProblem", "Mimi already struggles with item " + i);
    payload.put("proposedProgression", "Three distinct consequences of rule " + i);
    return payload;
  }

  Map<String, Object> response(int count) {
    return Map.of(
        "role",
        "IDEA",
        "provider",
        "fixture",
        "model",
        "fixture-no-provider",
        "calls",
        0,
        "rawProviderResponse",
        "ORIGINAL UNCHANGED RESPONSE",
        "providerResponseMetadata",
        Map.of("requestId", "fixture-provider-request"),
        "result",
        count == 1
            ? payload(1)
            : Map.of(
                "candidates",
                java.util.stream.IntStream.rangeClosed(1, count).mapToObj(this::payload).toList()));
  }

  Map<String, Object> persist(String key, int count) {
    service.reserve(key, request(count));
    var receipt = service.receipt(key, response(count));
    return service.materialize(key, request(count), receipt);
  }

  long count(String kind) {
    return jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind=:kind")
        .param("kind", kind)
        .query(Long.class)
        .single();
  }

  void fixtureEvaluation(Map<String, Object> c) throws Exception {
    // Test-only evidence adapter: not accessible from HTTP or production evaluation.
    var evidence =
        Map.of(
            "status",
            "EVALUATED",
            "eligible",
            true,
            "revision",
            2,
            "gates",
            List.of(
                Map.of(
                    "gate",
                    "TEST_POLICY",
                    "mandatory",
                    true,
                    "status",
                    "PASS",
                    "evidence",
                    "isolated test policy proof")));
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES(:id,'IDEA_EVALUATION',:candidate,CAST(:payload AS jsonb))")
        .param("id", UUID.randomUUID())
        .param("candidate", c.get("candidateId"))
        .param("payload", json.writeValueAsString(evidence))
        .update();
  }

  @Test
  void threeIndependentIdeasShareReceiptAndHaveStableIdentitiesAndIndependentEvaluations() {
    var response = response(3);
    persist("batch", 3);
    var all = service.list(draft, workspace);
    assertThat(all).hasSize(3);
    assertThat(all).extracting(c -> c.get("candidateId")).doesNotHaveDuplicates();
    assertThat(all).extracting(c -> c.get("receiptId")).containsOnly(all.get(0).get("receiptId"));
    assertThat(all)
        .extracting(c -> c.get("providerRequestId"))
        .containsOnly("fixture-provider-request");
    for (var c : all)
      assertThat(IdeaCandidateService.map(c.get("evaluation")))
          .containsEntry("eligible", false)
          .containsEntry("status", "PENDING_EVIDENCE");
    service.reevaluate(
        draft,
        UUID.fromString((String) all.get(0).get("candidateId")),
        Map.of("workspacePath", workspace));
    var reloaded = service.list(draft, workspace);
    assertThat(IdeaCandidateService.map(reloaded.get(0).get("evaluation")).get("revision"))
        .isEqualTo(2);
    assertThat(IdeaCandidateService.map(reloaded.get(1).get("evaluation")).get("revision"))
        .isEqualTo(1);
    var raw =
        jdbc.sql(
                "SELECT payload->'response'::text FROM post_family_workflow_events WHERE kind='IDEA_RECEIPT'")
            .query(String.class)
            .single();
    assertThat(IdeaCandidateService.map(read(raw))).isEqualTo(response);
    assertThat(count("CREATIVE_ROLE")).isZero();
  }

  Object read(String s) {
    try {
      return json.readValue(s, Map.class);
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
  }

  @Test
  void rejectionSelectionReloadAndMandatoryBlockers() throws Exception {
    persist("batch", 3);
    var all = service.list(draft, workspace);
    var first = all.get(0);
    var second = all.get(1);
    assertThatThrownBy(
            () ->
                service.decide(
                    draft,
                    UUID.fromString((String) first.get("candidateId")),
                    Map.of("workspacePath", workspace, "state", "SELECTED", "expectedRevision", 0)))
        .hasMessageContaining("NO_IDEA_APPROVED");
    service.decide(
        draft,
        UUID.fromString((String) first.get("candidateId")),
        Map.of("workspacePath", workspace, "state", "REJECTED", "expectedRevision", 0));
    fixtureEvaluation(second);
    service.decide(
        draft,
        UUID.fromString((String) second.get("candidateId")),
        Map.of("workspacePath", workspace, "state", "SELECTED", "expectedRevision", 0));
    var restored =
        new IdeaCandidateService(jdbc, json, drafts, manager, evaluationMl).list(draft, workspace);
    assertThat(restored.get(0).get("state")).isEqualTo("REJECTED");
    assertThat(restored.get(1).get("state")).isEqualTo("SELECTED");
    assertThatThrownBy(
            () ->
                service.decide(
                    draft,
                    UUID.fromString((String) second.get("candidateId")),
                    Map.of("workspacePath", workspace, "state", "REJECTED", "expectedRevision", 0)))
        .hasMessageContaining("reload");
  }

  @Test
  void repeatedAndConcurrentCallbacksAreIdempotent() throws Exception {
    persist("batch", 3);
    var pool = Executors.newFixedThreadPool(4);
    try {
      var tasks = new ArrayList<Callable<Map<String, Object>>>();
      for (int i = 0; i < 8; i++) tasks.add(() -> service.recover("batch"));
      for (var f : pool.invokeAll(tasks))
        assertThat(f.get()).containsEntry("batchStatus", "PERSISTED");
    } finally {
      pool.shutdownNow();
    }
    assertThat(count("IDEA_CANDIDATE")).isEqualTo(3);
    assertThat(count("IDEA_EVALUATION")).isEqualTo(3);
    assertThat(count("IDEA_RECEIPT")).isEqualTo(1);
    assertThat(service.reserve("batch", request(3))).isFalse();
  }

  @Test
  void partialWriteRollsBackAllCandidatesAndRecoveryUsesOriginalReceipt() {
    service.reserve("batch", request(3));
    var receipt = service.receipt("batch", response(3));
    jdbc.sql(
            "CREATE OR REPLACE FUNCTION fail_second_idea() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.kind='IDEA_CANDIDATE' AND NEW.payload->>'candidateIndex'='1' THEN RAISE EXCEPTION 'simulated interrupted write'; END IF; RETURN NEW; END $$")
        .update();
    jdbc.sql(
            "CREATE TRIGGER fail_idea BEFORE INSERT ON post_family_workflow_events FOR EACH ROW EXECUTE FUNCTION fail_second_idea()")
        .update();
    assertThatThrownBy(() -> service.materialize("batch", request(3), receipt))
        .isInstanceOf(RuntimeException.class);
    assertThat(count("IDEA_CANDIDATE")).isZero();
    assertThat(count("IDEA_RECEIPT")).isEqualTo(1);
    assertThat(service.batches(draft, workspace).get(0))
        .containsEntry("status", "PERSISTENCE_RECOVERY_REQUIRED");
    jdbc.sql("DROP TRIGGER fail_idea ON post_family_workflow_events").update();
    service.recover("batch");
    assertThat(count("IDEA_CANDIDATE")).isEqualTo(3);
  }

  @Test
  void missingMalformedIncompleteResponsesRemainPreservedAndNeverMaterialize() {
    var malformed = new LinkedHashMap<>(response(3));
    malformed.put(
        "result", Map.of("candidates", List.of(Map.of("title", "broken"), payload(2), payload(3))));
    var responses = List.of(Map.of("role", "IDEA", "result", Map.of()), response(2), malformed);
    int i = 0;
    for (var r : responses) {
      String key = "bad-" + i++;
      service.reserve(key, request(3));
      service.receipt(key, r);
      assertThatThrownBy(() -> service.recover(key)).isInstanceOf(IllegalStateException.class);
      assertThat(service.reserve(key, request(3))).isFalse();
    }
    assertThat(count("IDEA_CANDIDATE")).isZero();
    assertThat(count("IDEA_RECEIPT")).isEqualTo(3);
  }

  @Test
  void singleIdeaCompatibilityAndUnknownDispatchNeverRetries() {
    persist("single", 1);
    assertThat(service.list(draft, workspace)).hasSize(1);
    service.reserve("interrupted", request(3));
    assertThatThrownBy(() -> service.recover("interrupted"))
        .hasMessageContaining("Do not regenerate");
    assertThat(service.reserve("interrupted", request(3))).isFalse();
  }

  @Test
  void actualWorkflowDispatchIsIdeaOnceAndAuthorizationPreventsAnyCall() {
    var ml = mock(QualityMlClient.class);
    when(ml.workflow(eq("creative-role"), anyMap())).thenReturn(response(3));
    var workflow = new WorkflowService(null, ml, null, mock(VideoService.class), json, jdbc, null);
    workflow.ideaCandidates = service;
    var req = new LinkedHashMap<>(request(3));
    req.put("maxCostUsd", .1);
    assertThatThrownBy(
            () -> new TransactionTemplate(manager).execute(s -> workflow.creativeRole(req)))
        .hasMessageContaining("authorization");
    verifyNoInteractions(ml);
    req.put("generationAuthorized", true);
    req.put("maxCostUsd", 0);
    assertThatThrownBy(
            () -> new TransactionTemplate(manager).execute(s -> workflow.creativeRole(req)))
        .hasMessageContaining("cost ceiling");
    verifyNoInteractions(ml);
    req.put("maxCostUsd", .1);
    var first = new TransactionTemplate(manager).execute(s -> workflow.creativeRole(req));
    var second = new TransactionTemplate(manager).execute(s -> workflow.creativeRole(req));
    assertThat(first.get("ideaCandidates")).isEqualTo(second.get("ideaCandidates"));
    verify(ml, times(1)).workflow(eq("creative-role"), argThat(r -> "IDEA".equals(r.get("role"))));
    assertThat(count("CREATIVE_ROLE")).isZero();
  }

  @Test
  void reevaluationUsesPersistedSourceNotBrowserEvidenceAndAppendsHistory() {
    persist("batch", 3);
    var before = service.list(draft, workspace);
    var first = before.get(0);
    service.reevaluate(
        draft,
        UUID.fromString((String) first.get("candidateId")),
        Map.of(
            "workspacePath",
            workspace,
            "payload",
            Map.of("payoff", "forged"),
            "context",
            Map.of("profile", "EDUCATIONAL"),
            "eligible",
            true));
    var after = service.list(draft, workspace);
    assertThat(after.get(0).get("payload")).isEqualTo(first.get("payload"));
    assertThat(count("IDEA_EVALUATION")).isEqualTo(4);
    assertThat(count("IDEA_CANDIDATE")).isEqualTo(3);
    assertThat(count("IDEA_RECEIPT")).isEqualTo(1);
    verify(evaluationMl, atLeastOnce())
        .workflow(
            eq("idea-evaluation"),
            argThat(
                r ->
                    IdeaCandidateService.map(r.get("context")).equals(request(3).get("context"))
                        && !r.containsKey("eligible")));
  }

  @Test
  void mismatchedEvaluationBindingCannotReplacePriorResult() {
    persist("batch", 3);
    var first = service.list(draft, workspace).get(0);
    when(evaluationMl.workflow(eq("idea-evaluation"), anyMap()))
        .thenReturn(Map.of("candidateId", "wrong", "sourcePayloadSha256", "wrong"));
    assertThatThrownBy(
            () ->
                service.reevaluate(
                    draft,
                    UUID.fromString((String) first.get("candidateId")),
                    Map.of("workspacePath", workspace)))
        .hasMessageContaining("source binding mismatch");
    assertThat(count("IDEA_EVALUATION")).isEqualTo(3);
    assertThat(service.list(draft, workspace).get(0)).isEqualTo(first);
  }

  @Test
  void evaluationUnavailableDoesNotBecomeARejectionOrProviderRetry() {
    persist("batch", 3);
    var first = service.list(draft, workspace).get(0);
    when(evaluationMl.workflow(eq("idea-evaluation"), anyMap()))
        .thenThrow(new IllegalStateException("local evaluation unavailable"));
    assertThatThrownBy(
            () ->
                service.reevaluate(
                    draft,
                    UUID.fromString((String) first.get("candidateId")),
                    Map.of("workspacePath", workspace)))
        .hasMessageContaining("local evaluation unavailable");
    assertThat(service.list(draft, workspace).get(0)).isEqualTo(first);
    assertThat(count("IDEA_EVALUATION")).isEqualTo(3);
    verify(evaluationMl, never()).workflow(eq("creative-role"), anyMap());
  }

  @Test
  void onlyPolicyGroundedNotApplicableCanSatisfyAnExemptGate() {
    assertThat(IdeaCandidateService.gateSatisfied(Map.of("status", "NOT_APPLICABLE"))).isFalse();
    assertThat(
            IdeaCandidateService.gateSatisfied(
                Map.of(
                    "status", "NOT_APPLICABLE", "applicability", Map.of("policyExcluded", true))))
        .isTrue();
    assertThat(
            IdeaCandidateService.gateSatisfied(
                Map.of("status", "UNKNOWN", "sourceCheck", Map.of("status", "PASS"))))
        .isFalse();
  }

  void reviewTransport(boolean fixture, boolean malformed) {
    org.springframework.test.util.ReflectionTestUtils.setField(
        service, "reviewFixturesEnabled", fixture);
    when(evaluationMl.workflow(eq("idea-semantic-review"), anyMap()))
        .thenAnswer(
            call -> {
              Map<String, Object> req = call.getArgument(1);
              if ("PREVIEW".equals(req.get("action")))
                return new LinkedHashMap<>(
                    Map.of(
                        "model",
                        "gpt-6-sol",
                        "provider",
                        "openai",
                        "maximumProviderCalls",
                        1,
                        "estimatedUpperBoundUsd",
                        0.1,
                        "fixture",
                        fixture));
              var dimensions =
                  Map.ofEntries(
                      Map.entry("EVERYDAY_GOAL", "GOAL_001"),
                      Map.entry("IMMEDIATE_CONFLICT", "HOOK_004"),
                      Map.entry("TEXTUAL_OPENING_CAUSALITY", "HOOK_004"),
                      Map.entry("SINGLE_RULE", "CONCEPT_007"),
                      Map.entry("RULE_CONSISTENCY", "CONCEPT_007"),
                      Map.entry("CHARACTER_MOTIVATION", "GOAL_001"),
                      Map.entry("CAUSAL_PROGRESSION", "PROGRESSION_006"),
                      Map.entry("POTENTIAL_VISUAL_BEATS", "PROGRESSION_006"),
                      Map.entry("PAYOFF_SALIENCE", "PAYOFF_004"),
                      Map.entry("REPLAY_POTENTIAL", "PAYOFF_006"),
                      Map.entry("ORIGINALITY_RISK", "ENGINE_SILHOUETTE_DUPLICATE"),
                      Map.entry("PRODUCTION_FEASIBILITY", "PRODUCIBILITY_003"));
              @SuppressWarnings("unchecked")
              var sources = (List<Map<String, Object>>) req.get("candidates");
              var reviews =
                  sources.stream()
                      .map(
                          c -> {
                            var row = new LinkedHashMap<String, Object>(c);
                            row.remove("payload");
                            row.put(
                                "judgments",
                                dimensions.entrySet().stream()
                                    .map(
                                        d -> {
                                          var j =
                                              new LinkedHashMap<String, Object>(
                                                  Map.of(
                                                      "dimension",
                                                      d.getKey(),
                                                      "ruleId",
                                                      d.getValue(),
                                                      "verdict",
                                                      "SEMANTIC_PASS",
                                                      "confidence",
                                                      0.7,
                                                      "reason",
                                                      "TEST FIXTURE ONLY",
                                                      "evidence",
                                                      List.of(
                                                          Map.of(
                                                              "field",
                                                              "impossibleRule",
                                                              "quote",
                                                              IdeaCandidateService.map(
                                                                      c.get("payload"))
                                                                  .get("impossibleRule")))));
                                          if (malformed)
                                            j.put(
                                                "evidence",
                                                List.of(
                                                    Map.of(
                                                        "field",
                                                        "impossibleRule",
                                                        "quote",
                                                        "invented evidence")));
                                          return j;
                                        })
                                    .toList());
                            return row;
                          })
                      .toList();
              String model = fixture ? "fixture-transport-v1" : "gpt-6-sol";
              var response = new LinkedHashMap<String, Object>();
              response.putAll(
                  Map.of(
                      "model",
                      model,
                      "returnedModel",
                      model,
                      "provider",
                      fixture ? "ISOLATED_FIXTURE" : "openai",
                      "calls",
                      fixture ? 0 : 1,
                      "providerDispatched",
                      !fixture,
                      "rawProviderResponse",
                      "TEST RAW RECEIPT",
                      "result",
                      Map.of(
                          "policyVersion",
                          "idea-semantic-review-v1",
                          "reviewerModel",
                          model,
                          "reviewerVersion",
                          model,
                          "candidateReviews",
                          reviews)));
              return response;
            });
  }

  Map<String, Object> reviewRequest(Map<String, Object> quote) {
    return Map.of(
        "workspacePath",
        workspace,
        "quoteId",
        quote.get("quoteId"),
        "model",
        "gpt-6-sol",
        "ownerAuthorized",
        true,
        "maxCostUsd",
        1,
        "maximumProviderCalls",
        1);
  }

  @Test
  void reviewRequiresOwnerBudgetBeforeTransport() {
    persist("auth-review", 3);
    clearInvocations(evaluationMl);
    assertThatThrownBy(
            () ->
                service.semanticReview(
                    draft,
                    Map.of("workspacePath", workspace, "ownerAuthorized", false, "maxCostUsd", 1)))
        .isInstanceOf(IllegalArgumentException.class);
    verifyNoInteractions(evaluationMl);
    assertThat(count("IDEA_REVIEW_REQUEST")).isZero();
  }

  @Test
  void isolatedReviewsPersistSeparatelyAndNeverChangeRealEvaluationsOrDecisions() {
    persist("fixture-review", 3);
    reviewTransport(true, false);
    var before = service.list(draft, workspace);
    var quote = service.semanticReviewPreview(draft, Map.of("workspacePath", workspace));
    assertThat(service.semanticReview(draft, reviewRequest(quote)))
        .containsEntry("status", "ISOLATED_FIXTURE_ONLY");
    assertThat(count("IDEA_REVIEW_FIXTURE")).isEqualTo(3);
    assertThat(count("IDEA_SEMANTIC_REVIEW")).isZero();
    assertThat(count("IDEA_EVALUATION")).isEqualTo(3);
    var after = service.list(draft, workspace);
    for (int n = 0; n < 3; n++) {
      assertThat(after.get(n).get("evaluation")).isEqualTo(before.get(n).get("evaluation"));
      assertThat(after.get(n).get("state")).isEqualTo(before.get(n).get("state"));
      assertThat(after.get(n)).containsKey("fixtureSemanticReview");
    }
    assertThatThrownBy(() -> service.semanticReview(draft, reviewRequest(quote)))
        .hasMessageContaining("already attempted");
    verify(evaluationMl, times(1))
        .workflow(eq("idea-semantic-review"), argThat(r -> "REVIEW".equals(r.get("action"))));
  }

  @Test
  void staleQuoteCannotDispatchAfterEvaluationRevisionChanges() {
    persist("stale-review", 3);
    reviewTransport(true, false);
    var quote = service.semanticReviewPreview(draft, Map.of("workspacePath", workspace));
    var c = service.list(draft, workspace).get(0);
    service.reevaluate(
        draft,
        UUID.fromString(c.get("candidateId").toString()),
        Map.of("workspacePath", workspace));
    assertThatThrownBy(() -> service.semanticReview(draft, reviewRequest(quote)))
        .hasMessageContaining("Stale");
    verify(evaluationMl, never())
        .workflow(eq("idea-semantic-review"), argThat(r -> "REVIEW".equals(r.get("action"))));
  }

  @Test
  void invalidReviewKeepsRawReceiptAndNoPartialCandidateResults() {
    persist("invalid-review", 3);
    reviewTransport(true, true);
    var quote = service.semanticReviewPreview(draft, Map.of("workspacePath", workspace));
    assertThat(service.semanticReview(draft, reviewRequest(quote)))
        .containsEntry("status", "REVIEW_REJECTED");
    assertThat(count("IDEA_REVIEW_RECEIPT")).isEqualTo(1);
    assertThat(count("IDEA_REVIEW_FIXTURE")).isZero();
    assertThat(count("IDEA_EVALUATION")).isEqualTo(3);
    assertThat(service.semanticReviewHistory(draft, workspace).toString())
        .contains("TEST RAW RECEIPT");
  }

  @Test
  void productionRejectsFixtureTransportBeforeDispatch() {
    persist("bad-fixture-review", 3);
    reviewTransport(true, false);
    org.springframework.test.util.ReflectionTestUtils.setField(
        service, "reviewFixturesEnabled", false);
    assertThatThrownBy(
            () -> service.semanticReviewPreview(draft, Map.of("workspacePath", workspace)))
        .hasMessageContaining("forbidden");
    assertThat(count("IDEA_REVIEW_REQUEST")).isZero();
  }

  @Test
  void independentTextPassNeverCreatesVisualPassOrSelection() {
    persist("real-contract-mock", 3);
    reviewTransport(false, false);
    // These are isolated test records only; no SDK/provider is used by this test.
    for (var c : service.list(draft, workspace)) {
      var e = new LinkedHashMap<>(IdeaCandidateService.map(c.get("evaluation")));
      e.put(
          "gates",
          List.of(
              Map.of(
                  "gate",
                  "VISIBLE_EVERYDAY_GOAL",
                  "policy",
                  "GOAL_001",
                  "status",
                  "UNKNOWN",
                  "mandatory",
                  true),
              Map.of(
                  "gate",
                  "FRAME_ZERO_CAUSAL_LEGIBILITY",
                  "policy",
                  "HOOK_004",
                  "status",
                  "UNKNOWN",
                  "mandatory",
                  true),
              Map.of(
                  "gate",
                  "ORIGINALITY_DUPLICATE_ENGINE",
                  "policy",
                  "ENGINE_SILHOUETTE_DUPLICATE",
                  "status",
                  "UNKNOWN",
                  "mandatory",
                  true),
              Map.of(
                  "gate",
                  "PRODUCTION_FEASIBILITY",
                  "policy",
                  "PRODUCIBILITY_003",
                  "status",
                  "UNKNOWN",
                  "mandatory",
                  true)));
      jdbc.sql(
              "UPDATE post_family_workflow_events SET payload=CAST(:body AS jsonb) WHERE kind='IDEA_EVALUATION' AND binding_sha256=:id")
          .param("body", json.valueToTree(e).toString())
          .param("id", c.get("candidateId"))
          .update();
    }
    var quote = service.semanticReviewPreview(draft, Map.of("workspacePath", workspace));
    assertThat(service.semanticReview(draft, reviewRequest(quote)))
        .containsEntry("status", "COMPLETED");
    for (var c : service.list(draft, workspace)) {
      var e = IdeaCandidateService.map(c.get("evaluation"));
      assertThat(e).containsEntry("eligible", false).containsEntry("revision", 2);
      @SuppressWarnings("unchecked")
      var gates = (List<Map<String, Object>>) e.get("gates");
      assertThat(gates.get(0)).containsEntry("status", "PASS");
      assertThat(gates.subList(1, 4)).allMatch(g -> "UNKNOWN".equals(g.get("status")));
      assertThat(c.get("state")).isNotEqualTo("SELECTED");
    }
  }
}
