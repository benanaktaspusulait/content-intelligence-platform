package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import com.pompomhills.intelligence.video.VideoService;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;

@Testcontainers(disabledWithoutDocker = true)
class IdeaDraftPostgresTest {
  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  JdbcClient jdbc;
  IdeaDraftService service;
  VideoService videos;
  ContentWorkspaceController contents;
  TransactionTemplate tx;

  @BeforeEach
  void setup() {
    var ds =
        new DriverManagerDataSource(
            DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
    jdbc = JdbcClient.create(ds);
    tx = new TransactionTemplate(new DataSourceTransactionManager(ds));
    videos = mock(VideoService.class);
    contents = mock(ContentWorkspaceController.class);
    jdbc.sql("DROP TABLE IF EXISTS post_family_workflow_events").update();
    jdbc.sql(
            "CREATE TABLE post_family_workflow_events(id uuid PRIMARY KEY,kind varchar(40),binding_sha256 varchar(128),payload jsonb,created_at timestamptz DEFAULT now())")
        .update();
    service = new IdeaDraftService(jdbc, new ObjectMapper(), videos, contents);
  }

  Map<String, Object> state(String mode, String text) {
    return Map.of(
        "inputMode",
        mode,
        "idea",
        text,
        "workspacePath",
        "library/work",
        "title",
        "Operator title",
        "profile",
        "AUTO",
        "duration",
        15,
        "aspectRatio",
        "9:16");
  }

  Map<String, Object> save(UUID id, int expected, Map<String, Object> state) {
    return tx.execute(
        s ->
            service.save(
                Map.of("draftId", id.toString(), "expectedRevision", expected, "state", state)));
  }

  long count() {
    return jdbc.sql("SELECT count(*) FROM post_family_workflow_events").query(Long.class).single();
  }

  @Test
  void savesExactIdeaAndRestoresSameIdentityWithoutAnyDownstreamWork() {
    UUID id = UUID.randomUUID();
    var first = save(id, 0, state("IDEA", "Mimi finds sticky notes that keep following her."));
    var restored = service.get(id, "library/work");
    assertThat(restored).isEqualTo(first);
    assertThat(service.list()).hasSize(1);
    assertThat(restored)
        .containsEntry("checkpoint", "IDEA")
        .containsEntry("revision", 1)
        .doesNotContainKeys(
            "approvalRecordId", "storyRecordId", "promptVersionId", "renderAuthorization");
    verifyNoInteractions(contents);
    assertThat(count()).isEqualTo(1);
  }

  @Test
  void unchangedDoubleSaveIsIdempotentAndStaleEditsCannotOverwrite() {
    UUID id = UUID.randomUUID();
    var initial = save(id, 0, state("IDEA", "First"));
    assertThat(save(id, 0, state("IDEA", "First"))).isEqualTo(initial);
    assertThat(count()).isEqualTo(1);
    var updated = save(id, 1, state("IDEA", "Second"));
    assertThat(updated).containsEntry("revision", 2);
    assertThatThrownBy(() -> save(id, 1, state("IDEA", "Stale")))
        .isInstanceOf(IllegalStateException.class);
    assertThat(service.get(id, "library/work")).isEqualTo(updated);
    assertThat(count()).isEqualTo(2);
  }

  @Test
  void workspaceCannotBeChangedOrCrossRestored() {
    UUID id = UUID.randomUUID();
    save(id, 0, state("IDEA", "Source"));
    assertThatThrownBy(() -> service.get(id, "other/work"))
        .isInstanceOf(IllegalArgumentException.class);
    var changed = new LinkedHashMap<>(state("IDEA", "Source"));
    changed.put("workspacePath", "other/work");
    assertThatThrownBy(() -> save(id, 1, changed)).isInstanceOf(IllegalArgumentException.class);
    assertThat(count()).isEqualTo(1);
  }

  @Test
  void detailedStoryIsTruthfulUnapprovedAndContinueIsIdempotent() {
    UUID id = UUID.randomUUID();
    String source = "A complete human story.\nAn unresolved ending.";
    save(id, 0, state("DETAILED_STORY", source));
    var request = Map.<String, Object>of("expectedRevision", 1, "workspacePath", "library/work");
    var continued = tx.execute(s -> service.continueDraft(id, request));
    assertThat(continued)
        .containsEntry("checkpoint", "STORY")
        .doesNotContainKeys("approvalRecordId", "promptVersionId");
    assertThat(
            jdbc.sql(
                    "SELECT payload->>'sourceType' FROM post_family_workflow_events WHERE kind='CREATIVE_ROLE'")
                .query(String.class)
                .single())
        .isEqualTo("OPERATOR");
    assertThat(
            jdbc.sql(
                    "SELECT payload->'result'->'alternatives'->0->>'text' FROM post_family_workflow_events WHERE kind='CREATIVE_ROLE'")
                .query(String.class)
                .single())
        .isEqualTo(source);
    assertThat(tx.<Map<String, Object>>execute(s -> service.continueDraft(id, request)))
        .isEqualTo(continued);
    assertThat(count()).isEqualTo(3);
    verifyNoInteractions(contents);
  }

  @Test
  void existingPromptUsesCanonicalVersionWithoutFakeStoryOrProvider() {
    UUID id = UUID.randomUUID();
    String prompt = "USER PROMPT\nKeep exact line breaks.";
    save(id, 0, state("EXISTING_PROMPT", prompt));
    when(contents.create(any()))
        .thenReturn(
            new ContentWorkspaceController.ContentSummary(
                9L, "Title", prompt, "REEL", "DRAFT", null, null, null, null));
    when(contents.createPrompt(eq(9L), any()))
        .thenReturn(
            new ContentWorkspaceController.PromptVersionSummary(
                12L, 9L, 1, prompt, null, null, null, null));
    var request = Map.<String, Object>of("expectedRevision", 1, "workspacePath", "library/work");
    var continued = tx.execute(s -> service.continueDraft(id, request));
    assertThat(continued)
        .containsEntry("checkpoint", "PRODUCTION_REVIEW")
        .containsEntry("promptVersionId", "12")
        .containsEntry("rawText", prompt)
        .containsEntry("promptSource", "USER_SUPPLIED")
        .doesNotContainKeys("storyRecordId", "approvalRecordId");
    verify(contents)
        .createPrompt(
            9L, new ContentWorkspaceController.CreatePromptRequest(prompt, null, null, null));
    assertThat(tx.<Map<String, Object>>execute(s -> service.continueDraft(id, request)))
        .isEqualTo(continued);
    verify(contents, times(1)).create(any());
    assertThat(
            jdbc.sql(
                    "SELECT count(*) FROM post_family_workflow_events WHERE kind!='CREATIVE_STUDIO_SESSION'")
                .query(Long.class)
                .single())
        .isZero();
  }

  @Test
  void ideaCannotUseFreeContinueToManufactureStory() {
    UUID id = UUID.randomUUID();
    save(id, 0, state("IDEA", "Source"));
    assertThatThrownBy(
            () ->
                tx.execute(
                    s ->
                        service.continueDraft(
                            id, Map.of("expectedRevision", 1, "workspacePath", "library/work"))))
        .isInstanceOf(IllegalArgumentException.class);
    assertThat(count()).isEqualTo(1);
  }

  @Test
  void failedPromptImportRollsBackSessionTransition() {
    UUID id = UUID.randomUUID();
    save(id, 0, state("EXISTING_PROMPT", "Prompt"));
    when(contents.create(any())).thenThrow(new IllegalStateException("Cannot save"));
    assertThatThrownBy(
            () ->
                tx.execute(
                    s ->
                        service.continueDraft(
                            id, Map.of("expectedRevision", 1, "workspacePath", "library/work"))))
        .isInstanceOf(IllegalStateException.class);
    assertThat(service.get(id, "library/work")).containsEntry("checkpoint", "IDEA");
    assertThat(count()).isEqualTo(1);
  }

  @Test
  void authorizedMockedStoryMakesOneOperationAndPersistsUnapprovedCandidates() {
    var ml = mock(com.pompomhills.intelligence.quality.QualityMlClient.class);
    when(ml.workflow(eq("creative-role"), anyMap()))
        .thenReturn(
            Map.of(
                "role",
                "STORY",
                "provider",
                "mock",
                "calls",
                1,
                "result",
                Map.of(
                    "alternatives",
                    List.of(Map.of("candidateId", "one", "text", "Mock candidate")))));
    var workflow = new WorkflowService(null, ml, null, videos, new ObjectMapper(), jdbc, null);
    var result =
        tx.execute(
            status ->
                workflow.creativeRole(
                    Map.of(
                        "role",
                        "STORY",
                        "generationAuthorized",
                        true,
                        "text",
                        "A short idea",
                        "maxCostUsd",
                        .1,
                        "context",
                        Map.of("workspacePath", "library/work"))));
    assertThat(result)
        .containsKey("recordId")
        .doesNotContainKeys("approvalRecordId", "promptVersionId");
    verify(videos).requirePromptWorkspace("library/work");
    verify(ml, times(1))
        .workflow(
            eq("creative-role"),
            argThat(
                request ->
                    !request.containsKey("generationAuthorized")
                        && request.get("maxCostUsd").equals(.1)));
    assertThat(
            jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='CREATIVE_ROLE'")
                .query(Long.class)
                .single())
        .isEqualTo(1);
    assertThat(
            jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='STORY_APPROVAL'")
                .query(Long.class)
                .single())
        .isZero();
    verifyNoInteractions(contents);
  }
}
