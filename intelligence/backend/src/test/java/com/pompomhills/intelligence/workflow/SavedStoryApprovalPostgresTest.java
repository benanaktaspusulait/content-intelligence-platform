package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.MlWorkflowException;
import com.pompomhills.intelligence.quality.QualityMlClient;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.util.ReflectionTestUtils;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/** Isolated PostgreSQL regression for a real persisted in-review project and explicit approval. */
@Testcontainers(disabledWithoutDocker = true)
class SavedStoryApprovalPostgresTest {
  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  private JdbcClient jdbc;
  private WorkflowService service;
  private QualityMlClient ml;
  private org.springframework.transaction.support.TransactionTemplate tx;

  @BeforeEach
  void setUp() {
    var dataSource =
        new DriverManagerDataSource(DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
    jdbc = JdbcClient.create(dataSource);
    tx = new org.springframework.transaction.support.TransactionTemplate(new org.springframework.jdbc.datasource.DataSourceTransactionManager(dataSource));
    jdbc.sql("DROP TABLE IF EXISTS post_family_workflow_events").update();
    jdbc.sql(
            "CREATE TABLE post_family_workflow_events (id uuid PRIMARY KEY, kind varchar(80) NOT NULL,"
                + " binding_sha256 varchar(128), payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now())")
        .update();
    ml = mock(QualityMlClient.class);
    service =
        new WorkflowService(
            null,
            ml,
            null,
            null,
            new ObjectMapper().findAndRegisterModules(),
            jdbc,
            null);
    ReflectionTestUtils.setField(service, "attemptTransactions", new org.springframework.jdbc.datasource.DataSourceTransactionManager(dataSource));
  }

  @Test
  void rejectedStoryProviderResponseIsDurablySavedBeforeRequestFailureRollsBack() throws Exception {
    var diagnostics = Map.<String, Object>ofEntries(
        Map.entry("category", "PROVIDER_RESULT_REJECTED"),
        Map.entry("provider", "deepseek"),
        Map.entry("model", "deepseek-chat"),
        Map.entry("providerDispatched", true),
        Map.entry("providerResponseReturned", true),
        Map.entry("providerRequestId", "fixture-request-1"),
        Map.entry("finishReason", "stop"),
        Map.entry("usage", Map.of("prompt_tokens", 100, "completion_tokens", 40, "total_tokens", 140)),
        Map.entry("actualCostUsd", 0.001),
        Map.entry("approvedCostCeilingUsd", 0.02),
        Map.entry("rawProviderResponse", "{\"alternatives\":"),
        Map.entry("validationError", "Deepseek returned invalid JSON"));
    var envelope = new java.util.LinkedHashMap<String, Object>();
    envelope.put("detail", "Deepseek returned invalid JSON");
    envelope.putAll(diagnostics);
    when(ml.workflow(eq("creative-role"), anyMap()))
        .thenThrow(new MlWorkflowException(409, envelope));

    assertThatThrownBy(() -> tx.execute(status -> service.creativeRole(Map.of(
        "role", "STORY_REVIEW", "text", "Review this story.", "maxCostUsd", 0.02,
        "context", Map.of()))))
        .hasMessageContaining("Deepseek returned invalid JSON");

    var stored = jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_ROLE' ORDER BY created_at DESC LIMIT 1")
        .query(String.class).single();
    var payload = new ObjectMapper().readValue(stored, new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
    assertThat(payload).containsEntry("attemptState", "PROVIDER_RESULT_REJECTED");
    var savedDiagnostics = (Map<?, ?>) payload.get("attemptDiagnostics");
    assertThat(savedDiagnostics.get("rawProviderResponse")).isEqualTo("{\"alternatives\":");
    assertThat(savedDiagnostics.get("finishReason")).isEqualTo("stop");
    assertThat(savedDiagnostics.get("providerRequestId")).isEqualTo("fixture-request-1");
    assertThat(savedDiagnostics.get("usage")).isInstanceOf(Map.class);
    verify(ml, times(1)).workflow(eq("creative-role"), anyMap());
  }

  @Test
  void restoresInReviewCandidatesAndOnlyTheExplicitlyApprovedRevision() throws Exception {
    UUID storyId = UUID.randomUUID();
    String first = "Mimi follows a note to a blue cabinet.";
    String second = "Mimi hides from the notes beneath a table.";
    var story =
        Map.of(
            "role",
            "STORY",
            "title",
            "Mimi's Sticky Note Mystery",
            "lifecycleStatus",
            "IN_REVIEW",
            "result",
            Map.of(
                "role",
                "STORY",
                "alternatives",
                List.of(
                    Map.of("candidateId", "candidate-1", "text", first),
                    Map.of("candidateId", "candidate-2", "text", second))));
    insert(storyId, "CREATIVE_ROLE", story);

    UUID unrelatedStoryId = UUID.randomUUID();
    insert(
        unrelatedStoryId,
        "CREATIVE_ROLE",
        Map.of(
            "role",
            "STORY",
            "title",
            "A different project with the same display title",
            "result",
            Map.of("alternatives", List.of(Map.of("candidateId", "candidate-1", "text", "Unrelated.")))));

    service.saveStudioSession(
        Map.of(
            "sessionId",
            UUID.randomUUID().toString(),
            "storyRecordId",
            storyId.toString(),
            "title",
            "Mimi's Sticky Note Mystery",
            "selectedCandidateIdValue",
            "candidate-2",
            "profile",
            "ABSURD_PHYSICS",
            "duration",
            15,
            "aspectRatio",
            "9:16"));
    service.changeLifecycle(
        storyId,
        Map.of("status", "IN_REVIEW", "reason", "Isolated acceptance fixture"));

    var restoredStory = service.getByKind(storyId, "CREATIVE_ROLE");
    var restoredSession = service.list("CREATIVE_STUDIO_SESSION").getFirst();
    assertThat(restoredStory.get("lifecycleStatus")).isEqualTo("IN_REVIEW");
    assertThat(service.list("STORY_APPROVAL")).isEmpty();
    assertThat(((Map<?, ?>) restoredStory.get("result")).get("alternatives")).asList().hasSize(2);
    assertThat(restoredSession)
        .containsEntry("storyRecordId", storyId.toString())
        .containsEntry("selectedCandidateIdValue", "candidate-2");
    assertThat(service.list("CREATIVE_ROLE")).hasSize(2);

    String fingerprint = fingerprint(second);
    var approval =
        service.approveStory(
            storyId,
            Map.of(
                "approvedText",
                second,
                "candidateId",
                "candidate-2",
                "revisionId",
                "candidate-2-revision-" + fingerprint,
                "contentFingerprint",
                fingerprint));

    assertThat(approval)
        .containsEntry("storyRecordId", storyId.toString())
        .containsEntry("candidateId", "candidate-2")
        .containsEntry("approvedText", second);
    assertThat(service.list("STORY_APPROVAL")).singleElement().satisfies(saved -> {
      assertThat(saved).containsEntry("storyRecordId", storyId.toString());
      assertThat(saved).containsEntry("revisionId", "candidate-2-revision-" + fingerprint);
    });
    assertThat(service.list("CREATIVE_ROLE")).hasSize(2);
    assertThat(service.getByKind(unrelatedStoryId, "CREATIVE_ROLE").get("title"))
        .isEqualTo("A different project with the same display title");
    verifyNoInteractions(ml);
  }


  private Map<String, Object> approvedBuildRequest() throws Exception {
    UUID story = UUID.randomUUID();
    String text = "Mimi'nin notu çoğalır. Mimi hapşırır.";
    String revision = "candidate-2-revision-" + fingerprint(text);
    insert(story, "CREATIVE_ROLE", Map.of("role", "STORY", "result", Map.of("alternatives",
        List.of(Map.of("candidateId", "candidate-2", "text", text)))));
    var approval = service.approveStory(story, Map.of("approvedText", text, "candidateId", "candidate-2",
        "revisionId", revision, "contentFingerprint", fingerprint(text)));
    return Map.of("role", "BUILD_PROMPT", "text", text, "maxCostUsd", .15,
        "context", Map.of("sourceStoryRecordId", story.toString(), "candidateId", "candidate-2",
            "storyRevisionId", revision, "approvalRecordId", approval.get("recordId"),
            "targetConfiguration", Map.of("duration", 15, "aspectRatio", "9:16", "selectedGenerator", "SEEDANCE_2_0_MINI")));
  }

  @Test
  void rejectedProviderResponseCommitsAndIdenticalRetryNeverCallsMlAgain() throws Exception {
    var request = approvedBuildRequest();
    when(ml.workflow(eq("creative-role"), anyMap())).thenReturn(Map.of(
        "role", "BUILD_PROMPT", "attemptState", "PROVIDER_RESULT_REJECTED", "validationStatus", "REJECTED", "provider", "openai",
        "calls", 1, "rejectedProviderResponse", "{\"productionPlan\":{\"invalid\":true}}",
        "attemptDiagnostics", Map.of("error", "Beat 2: staging", "retryAutomatically", false)));
    var first = tx.execute(status -> service.creativeRole(request));
    assertThat(first).containsEntry("attemptState", "PROVIDER_RESULT_REJECTED").containsEntry("validationStatus", "REJECTED");
    assertThat(service.getByKind(UUID.fromString(String.valueOf(first.get("recordId"))), "CREATIVE_ROLE"))
        .containsEntry("rejectedProviderResponse", first.get("rejectedProviderResponse"));
    var retry = new java.util.LinkedHashMap<>(request);
    retry.put("maxCostUsd", .10);
    var replay = tx.execute(status -> service.creativeRole(retry));
    assertThat(replay).containsEntry("recordId", first.get("recordId").toString()).containsEntry("calls", 0)
        .containsEntry("reused", true).containsEntry("attemptState", "PROVIDER_RESULT_REJECTED");
    verify(ml, times(1)).workflow(eq("creative-role"), anyMap());
  }

  @Test
  void unknownProviderOutcomeCommitsAndReplayCannotChargeAgain() throws Exception {
    var request = approvedBuildRequest();
    when(ml.workflow(eq("creative-role"), anyMap())).thenReturn(Map.of("role", "BUILD_PROMPT",
        "provider", "openai", "attemptState", "PROVIDER_OUTCOME_UNKNOWN", "validationStatus", "UNKNOWN",
        "attemptDiagnostics", Map.of("exceptionType", "APITimeoutError", "providerOutcome", "UNKNOWN", "retryAutomatically", false)));
    var first = tx.execute(status -> service.creativeRole(request));
    assertThat(first).containsEntry("attemptState", "PROVIDER_OUTCOME_UNKNOWN").doesNotContainKey("calls");
    var replay = tx.execute(status -> service.creativeRole(request));
    assertThat(replay).containsEntry("recordId", first.get("recordId").toString())
        .containsEntry("calls", 0).containsEntry("attemptState", "PROVIDER_OUTCOME_UNKNOWN");
    verify(ml, times(1)).workflow(eq("creative-role"), anyMap());
  }

  @Test
  void completedRequestReplaysAndConcurrentIdenticalRequestsCallMlOnce() throws Exception {
    var request = approvedBuildRequest();
    var entered = new java.util.concurrent.CountDownLatch(1);
    var release = new java.util.concurrent.CountDownLatch(1);
    when(ml.workflow(eq("creative-role"), anyMap())).thenAnswer(call -> {
      entered.countDown();
      assertThat(release.await(5, java.util.concurrent.TimeUnit.SECONDS)).isTrue();
      return Map.of("role", "BUILD_PROMPT", "provider", "openai", "calls", 1, "result", Map.of("prompt", "Stored fixture draft"));
    });
    try (var pool = java.util.concurrent.Executors.newFixedThreadPool(2)) {
      var first = pool.submit(() -> tx.execute(status -> service.creativeRole(request)));
      assertThat(entered.await(5, java.util.concurrent.TimeUnit.SECONDS)).isTrue();
      var second = pool.submit(() -> tx.execute(status -> service.creativeRole(request)));
      release.countDown();
      var saved = first.get(10, java.util.concurrent.TimeUnit.SECONDS);
      var replay = second.get(10, java.util.concurrent.TimeUnit.SECONDS);
      assertThat(replay).containsEntry("recordId", saved.get("recordId").toString()).containsEntry("calls", 0)
          .containsEntry("attemptState", "REUSED_SAVED_RESULT");
      verify(ml, times(1)).workflow(eq("creative-role"), anyMap());
    }
  }

  @Test
  void wrongRevisionCandidateTextAndMissingApprovalStillFailBeforeMl() throws Exception {
    var valid = approvedBuildRequest();
    for (String field : List.of("candidateId", "storyRevisionId", "approvalRecordId")) {
      var context = new java.util.LinkedHashMap<>((Map<String, Object>) valid.get("context"));
      context.put(field, "wrong");
      var request = new java.util.LinkedHashMap<>(valid);
      request.put("context", context);
      assertThatThrownBy(() -> tx.execute(status -> service.creativeRole(request)))
          .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("exact approved story");
    }
    var edited = new java.util.LinkedHashMap<>(valid);
    edited.put("text", "A changed story");
    assertThatThrownBy(() -> tx.execute(status -> service.creativeRole(edited)))
        .isInstanceOf(IllegalArgumentException.class);
    UUID unapprovedStory = UUID.randomUUID();
    insert(unapprovedStory, "CREATIVE_ROLE", Map.of("role", "STORY", "result", Map.of("alternatives",
        List.of(Map.of("candidateId", "candidate-2", "text", valid.get("text"))))));
    var missingContext = new java.util.LinkedHashMap<>((Map<String, Object>) valid.get("context"));
    missingContext.put("sourceStoryRecordId", unapprovedStory.toString());
    missingContext.remove("approvalRecordId");
    var missing = new java.util.LinkedHashMap<>(valid);
    missing.put("context", missingContext);
    assertThatThrownBy(() -> tx.execute(status -> service.creativeRole(missing)))
        .isInstanceOf(IllegalArgumentException.class);
    verifyNoInteractions(ml);
  }

  private void insert(UUID id, String kind, Map<String, Object> payload) throws Exception {
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload)"
                + " VALUES(:id,:kind,:binding,CAST(:payload AS jsonb))")
        .param("id", id)
        .param("kind", kind)
        .param("binding", null)
        .param("payload", new ObjectMapper().writeValueAsString(payload))
        .update();
  }

  private String fingerprint(String value) {
    int hash = 0x811c9dc5;
    for (int i = 0; i < value.length(); i++) hash = (hash ^ value.charAt(i)) * 0x01000193;
    return String.format("%08x", hash);
  }
}
