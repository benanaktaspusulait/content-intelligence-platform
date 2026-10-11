package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.QualityMlClient;
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

  @BeforeEach
  void setUp() {
    var dataSource =
        new DriverManagerDataSource(DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
    jdbc = JdbcClient.create(dataSource);
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
