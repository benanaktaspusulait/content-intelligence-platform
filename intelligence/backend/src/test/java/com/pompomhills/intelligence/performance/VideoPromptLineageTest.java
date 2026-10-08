package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pompomhills.intelligence.video.context.VideoCreativeContextService;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoPromptLineageTest {
  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired PerformanceImportService importService;

  protected UUID insertVideo(String filename) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,:name,:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("name", filename)
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  @Autowired VideoCreativeContextService contexts;
  @Autowired com.pompomhills.intelligence.common.config.PompomProperties configuration;
  @Autowired com.pompomhills.intelligence.workflow.WorkflowService workflow;
  @Autowired com.pompomhills.intelligence.content.ContentWorkspaceController workspace;
  @Autowired com.pompomhills.intelligence.workflow.WorkflowRepairSessionService repairs;

  @org.springframework.test.context.bean.override.mockito.MockitoBean
  com.pompomhills.intelligence.quality.QualityMlClient workflowMl;

  @org.springframework.test.context.bean.override.mockito.MockitoSpyBean
  com.pompomhills.intelligence.modelregistry.StatisticalTrainingService training;

  @Autowired com.pompomhills.intelligence.modelregistry.api.ModelRegistryController modelRegistry;
  @Autowired com.pompomhills.intelligence.prediction.PredictionService predictions;

  @org.springframework.test.context.bean.override.mockito.MockitoBean
  com.pompomhills.intelligence.creative.CreativeFingerprintRepository fingerprints;

  @org.springframework.test.context.bean.override.mockito.MockitoBean
  com.pompomhills.intelligence.prediction.ml.MlPredictionClient predictionMl;

  @Test
  void creativeDraftRetainsExactStoryProviderAndModelAfterEditedVersionReopens() {
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("creative-role"),
                org.mockito.ArgumentMatchers.anyMap()))
        .thenAnswer(
            invocation -> {
              java.util.Map<String, Object> input = invocation.getArgument(1);
              boolean story = "STORY".equals(input.get("role"));
              return new java.util.LinkedHashMap<>(
                  java.util.Map.of(
                      "role",
                      input.get("role"),
                      "provider",
                      "LOCAL_MOCK",
                      "model",
                      "fixture-model",
                      "result",
                      story
                          ? java.util.Map.of("alternatives", java.util.List.of("fixture-story"))
                          : java.util.Map.of("prompt", "fixture-draft")));
            });
    var story =
        workflow.creativeRole(
            java.util.Map.of("role", "STORY", "text", "fixture", "maxCostUsd", 1));
    var draft =
        workflow.creativeRole(
            java.util.Map.of(
                "role",
                "BUILD_PROMPT",
                "text",
                "edited fixture story",
                "maxCostUsd",
                1,
                "context",
                java.util.Map.of("sourceStoryRecordId", String.valueOf(story.get("recordId")))));
    Long content =
        jdbc.sql("INSERT INTO contents(title,type) VALUES ('creative fixture','REEL') RETURNING id")
            .query(Long.class)
            .single();
    var saved =
        workspace.createPrompt(
            content,
            new com.pompomhills.intelligence.content.ContentWorkspaceController.CreatePromptRequest(
                "fixture-draft edited", "{}", null, String.valueOf(draft.get("recordId"))));
    assertThat(workspace.creativeProvenance(content, saved.id()))
        .containsEntry("sourceStoryRecordId", String.valueOf(story.get("recordId")))
        .containsEntry("provider", "LOCAL_MOCK")
        .containsEntry("model", "fixture-model")
        .containsEntry("operatorEdited", true)
        .containsEntry("validationStatus", "NOT_VALIDATED");
    assertThatThrownBy(
            () ->
                workspace.createPrompt(
                    content,
                    new com.pompomhills.intelligence.content.ContentWorkspaceController
                        .CreatePromptRequest(
                        "wrong", "{}", null, String.valueOf(story.get("recordId")))))
        .isInstanceOf(IllegalArgumentException.class);
    assertThat(
            jdbc.sql("SELECT count(*) FROM prompt_versions WHERE content_id=:id")
                .param("id", content)
                .query(Integer.class)
                .single())
        .isEqualTo(1);
    assertThatThrownBy(() -> workspace.creativeProvenance(-1L, saved.id()))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void savedEditLineageReopensFromBothParentAndArtifactWithoutNewAnalysis() {
    UUID parent = insertVideo("parent.mp4"),
        artifact = insertVideo("edited.mp4"),
        unrelated = insertVideo("other.mp4"),
        record = UUID.randomUUID();
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'EDIT_HANDOFF',jsonb_build_object('videoId',CAST(:parent AS"
                + " text),'artifactVideoId',CAST(:artifact AS text),'reason','TEST_FIXTURE'))")
        .param("id", record)
        .param("parent", parent)
        .param("artifact", artifact)
        .update();
    assertThat(workflow.editedHandoffs(parent).getFirst().get("recordId"))
        .isEqualTo(record.toString());
    assertThat(workflow.editedHandoffs(artifact).getFirst().get("videoId"))
        .isEqualTo(parent.toString());
    assertThat(workflow.editedHandoffs(unrelated)).isEmpty();
  }

  @Test
  void
      folderVersionsStayAmbiguousUntilExactOperatorSelectionAndReconstructionNeverBecomesOriginal() {
    UUID video = insertVideo("source.mp4");
    String folder = "test";
    Long content =
        jdbc.sql(
                "INSERT INTO contents(title,type,source_path) VALUES ('lineage','REEL',:path)"
                    + " RETURNING id")
            .param("path", folder + "/prompt-" + video + ".txt")
            .query(Long.class)
            .single();
    Long first =
        jdbc.sql(
                "INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES"
                    + " (:content,1,'Original text') RETURNING id")
            .param("content", content)
            .query(Long.class)
            .single();
    jdbc.sql(
            "INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES"
                + " (:content,2,'Newer text')")
        .param("content", content)
        .update();
    var ambiguous = contexts.get(video);
    assertThat(ambiguous.prompt()).isNull();
    assertThat(ambiguous.evidenceStatus()).isEqualTo("PROMPT_AMBIGUOUS");
    contexts.link(video, first, "ORIGINAL", "Operator checked original generation record");
    assertThat(contexts.get(video).prompt().promptVersionId()).isEqualTo(first);
    assertThat(contexts.get(video).prompt().rawText()).isEqualTo("Original text");
    contexts.link(video, first, "RECONSTRUCTED", "Candidate reconstructed from clip");
    assertThat(contexts.get(video).prompt()).isNull();
    assertThatThrownBy(() -> contexts.link(video, first, "ORIGINAL", " "))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void retrievalExcludesWrongScopeAndLatestRevocation() {
    UUID qa = UUID.randomUUID();
    UUID lesson = UUID.randomUUID();
    UUID approved = UUID.randomUUID();
    UUID sourceReview = UUID.randomUUID();
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'REVIEW',CAST(:payload AS jsonb))")
        .param("id", sourceReview)
        .param(
            "payload",
            "{\"bindingHash\":\"fixture-binding\",\"routing\":{\"contentProfile\":\"EDUCATIONAL\"},\"generation\":{\"profileVersion\":\"model-v1\",\"selectedGenerator\":\"fixture-generator\",\"settings\":{\"aspectRatio\":\"9:16\"}},\"boundRequest\":{\"desiredDuration\":15}}")
        .update();
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'ACTUAL_RENDER_QA',CAST(:payload AS jsonb))")
        .param("id", qa)
        .param(
            "payload",
            "{\"viewerFacingUsability\":\"USABLE\",\"lineageStatus\":\"SOURCE_BOUND\",\"bindingHash\":\"fixture-binding\",\"duration\":15,\"videoId\":\"fixture-video\",\"reviewId\":\""
                + sourceReview
                + "\"}")
        .update();
    String payload =
        "{\"parentRecordId\":\""
            + lesson
            + "\",\"reviewStatus\":\"APPROVED\",\"lessonScope\":\"ACTUAL_EXECUTION\",\"contentProfile\":\"EDUCATIONAL\",\"targetModelVersion\":\"model-v1\",\"durationRange\":[10,20],\"settings\":{\"aspectRatio\":\"9:16\"},\"sampleSize\":1,\"evidenceBasis\":[\""
            + qa
            + "\"]}";
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'LEARNING_REVIEW',CAST(:payload AS jsonb))")
        .param("id", approved)
        .param("payload", payload)
        .update();
    assertThat(workflow.retrieveLessons("EDUCATIONAL", "model-v1", 15)).hasSize(1);
    assertThat(
            workflow.retrieveLessons(
                "EDUCATIONAL",
                "model-v1",
                15,
                java.util.Map.of("settings", java.util.Map.of("aspectRatio", "16:9"))))
        .isEmpty();
    assertThat(
            workflow.retrieveLessons(
                "EDUCATIONAL", "model-v1", 15, java.util.Map.of("generator", "wrong-generator")))
        .isEmpty();
    assertThat(workflow.retrieveLessons("EDUCATIONAL", "model-v1", 30)).isEmpty();
    assertThat(workflow.retrieveLessons("CURIOSITY_ADVENTURE", "model-v1", 15)).isEmpty();
    workflow.reviewLearning(
        approved, java.util.Map.of("decision", "REVOKED", "reason", "Evidence no longer reliable"));
    assertThat(workflow.retrieveLessons("EDUCATIONAL", "model-v1", 15)).isEmpty();
  }

  @Test
  void promotionCannotChangeRegistryWithoutActiveArtifactInference() throws Exception {
    UUID challenger = UUID.randomUUID();
    UUID champion = UUID.randomUUID();
    String platform = "test-" + challenger;
    for (UUID id : java.util.List.of(challenger, champion)) {
      jdbc.sql(
              "INSERT INTO"
                  + " model_versions(id,version,model_type,platform,training_dataset_version,feature_version,knowledge_cutoff,metrics,status,trained_at)"
                  + " VALUES"
                  + " (:id,:version,'prediction',:platform,'fixture','fixture',now(),'{}',:status,now())")
          .param("id", id)
          .param("version", id.toString())
          .param("platform", platform)
          .param("status", id.equals(champion) ? "CHAMPION" : "CHALLENGER")
          .update();
    }
    var controller =
        new com.pompomhills.intelligence.modelregistry.api.ModelRegistryController(
            jdbc, new tools.jackson.databind.ObjectMapper());
    var mvc =
        org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup(controller)
            .build();
    mvc.perform(
            org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post(
                "/api/v1/models/" + challenger + "/promote"))
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.status()
                .isNotImplemented());
    assertThat(
            jdbc.sql("SELECT status FROM model_versions WHERE id=:id")
                .param("id", challenger)
                .query(String.class)
                .single())
        .isEqualTo("CHALLENGER");
    assertThat(
            jdbc.sql("SELECT status FROM model_versions WHERE id=:id")
                .param("id", champion)
                .query(String.class)
                .single())
        .isEqualTo("CHAMPION");
  }

  @Test
  void savedRevisionPreservesExactParentSourceAndRejectsCrossContentParent() {
    Long content =
        jdbc.sql("INSERT INTO contents(title,type) VALUES ('revision fixture','REEL') RETURNING id")
            .query(Long.class)
            .single();
    Long parent =
        jdbc.sql(
                "INSERT INTO prompt_versions(content_id,version_number,raw_text,source_path) VALUES"
                    + " (:content,1,'Original','library/fixture/prompt.txt') RETURNING id")
            .param("content", content)
            .query(Long.class)
            .single();
    var revision =
        workspace.createPrompt(
            content,
            new com.pompomhills.intelligence.content.ContentWorkspaceController.CreatePromptRequest(
                "Edited", "{}", parent));
    assertThat(revision.sourcePath()).isEqualTo("library/fixture/prompt.txt");
    assertThat(
            jdbc.sql("SELECT parent_prompt_version_id FROM prompt_versions WHERE id=:id")
                .param("id", revision.id())
                .query(Long.class)
                .single())
        .isEqualTo(parent);
    Long other =
        jdbc.sql("INSERT INTO contents(title,type) VALUES ('other','REEL') RETURNING id")
            .query(Long.class)
            .single();
    assertThatThrownBy(
            () ->
                workspace.createPrompt(
                    other,
                    new com.pompomhills.intelligence.content.ContentWorkspaceController
                        .CreatePromptRequest("Wrong parent", "{}", parent)))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void sourceScopedRestoreFindsSavedReviewEvenBehindMoreThanTwoHundredUnrelatedRecords() {
    UUID saved = UUID.randomUUID();
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload,created_at) VALUES"
                + " (:id,'REVIEW','{\"contentId\":888,\"promptVersionId\":999}',now()-interval '1"
                + " day')")
        .param("id", saved)
        .update();
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) SELECT"
                + " gen_random_uuid(),'REVIEW','{\"contentId\":1,\"promptVersionId\":2}'::jsonb"
                + " FROM generate_series(1,201)")
        .update();
    assertThat(workflow.list("REVIEW", "888", "999", null)).hasSize(1);
    assertThat(workflow.list("REVIEW", "888", "999", null).getFirst().get("recordId"))
        .isEqualTo(saved.toString());
  }

  @Test
  void boundedRepairCreatesIndependentVersionAndReplayCannotMakeMoreCalls() throws Exception {
    Long content =
        jdbc.sql("INSERT INTO contents(title,type) VALUES ('repair fixture','REEL') RETURNING id")
            .query(Long.class)
            .single();
    Long parent =
        jdbc.sql(
                "INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES"
                    + " (:content,1,'Luca pushes. CUT') RETURNING id")
            .param("content", content)
            .query(Long.class)
            .single();
    UUID review = UUID.randomUUID();
    var bound =
        java.util.Map.of(
            "profile",
            "post-family-v1",
            "prompt",
            "Luca pushes. CUT",
            "sourceId",
            "fixture",
            "sourceVersion",
            parent.toString(),
            "protectedIntent",
            java.util.List.of("Luca pushes."));
    var original = new java.util.LinkedHashMap<String, Object>();
    original.put("contentId", content);
    original.put("promptVersionId", parent);
    original.put("decisionPolicyVersion", "impact-review-v1");
    original.put("boundRequest", bound);
    original.put("planQuality", java.util.Map.of("status", "PASS"));
    original.put("executionRisk", java.util.Map.of("status", "PASS"));
    original.put(
        "executionReview",
        java.util.Map.of(
            "findings",
            java.util.List.of(
                java.util.Map.of("confidence", "HIGH", "evidenceBasis", "MODEL_DOCUMENTED"))));
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'REVIEW',CAST(:payload AS jsonb))")
        .param("id", review)
        .param(
            "payload",
            new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(original))
        .update();
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("creative-role"),
                org.mockito.ArgumentMatchers.anyMap()))
        .thenReturn(
            java.util.Map.of(
                "role",
                "MINIMAL_REPAIR",
                "provider",
                "openai",
                "model",
                "fixture-model",
                "result",
                java.util.Map.of(
                    "patches",
                    java.util.List.of(
                        java.util.Map.of(
                            "start", 13, "end", 16, "sourceQuote", "CUT", "replacement", "Hold."))),
                "costUpperBoundUsd",
                0.01));
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("repair"), org.mockito.ArgumentMatchers.anyMap()))
        .thenReturn(
            java.util.Map.of(
                "finalPrompt",
                "Luca pushes. Hold.",
                "bindingHash",
                "repair",
                "diff",
                "CUT -> Hold."));
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("review"), org.mockito.ArgumentMatchers.anyMap()))
        .thenReturn(
            java.util.Map.of(
                "bindingHash",
                "independent",
                "decisionPolicyVersion",
                "impact-review-v1",
                "originalPrompt",
                "Luca pushes. Hold.",
                "planQuality",
                java.util.Map.of("status", "PASS"),
                "executionRisk",
                java.util.Map.of("status", "PASS"),
                "executionReview",
                java.util.Map.of("findings", java.util.List.of())));
    var started = repairs.start(review, "single-call", 2, 1);
    UUID session = UUID.fromString(String.valueOf(started.get("sessionId")));
    assertThat(repairs.start(review, "single-call", 2, 1).get("sessionId"))
        .isEqualTo(session.toString());
    var finished = repairs.step(session);
    assertThat(finished.get("state")).isEqualTo("STOPPED");
    assertThat(((Number) finished.get("bestPromptVersionId")).longValue())
        .isNotEqualTo(parent.longValue());
    assertThat(finished.get("stopReason")).isEqualTo("INDEPENDENT_REVIEW_CLEAR");
    repairs.step(session);
    repairs.decide(session, "ACCEPTED");
    org.mockito.Mockito.verify(workflowMl, org.mockito.Mockito.times(1))
        .workflow(
            org.mockito.ArgumentMatchers.eq("creative-role"),
            org.mockito.ArgumentMatchers.anyMap());
    assertThat(
            jdbc.sql("SELECT raw_text FROM prompt_versions WHERE id=:id")
                .param("id", parent)
                .query(String.class)
                .single())
        .isEqualTo("Luca pushes. CUT");
  }

  @Test
  void regenerationPreservesExactParentAndReplayThenRejectsChangedBytes() throws Exception {
    UUID video = insertVideo("regeneration-parent.mp4");
    String path = "test/" + video + ".mp4";
    var file = configuration.dataRoot().resolve(path);
    java.nio.file.Files.createDirectories(file.getParent());
    byte[] bytes = ("controlled lineage fixture " + video).getBytes();
    java.nio.file.Files.write(file, bytes);
    String hash =
        java.util.HexFormat.of()
            .formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes));
    jdbc.sql("UPDATE videos SET content_hash=:hash WHERE id=:id")
        .param("hash", hash)
        .param("id", video)
        .update();
    Long content =
        jdbc.sql(
                "INSERT INTO contents(title,type) VALUES ('regeneration fixture','REEL') RETURNING"
                    + " id")
            .query(Long.class)
            .single();
    Long parent =
        jdbc.sql(
                "INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES"
                    + " (:content,1,'Original') RETURNING id")
            .param("content", content)
            .query(Long.class)
            .single();
    var revision =
        workspace.createPrompt(
            content,
            new com.pompomhills.intelligence.content.ContentWorkspaceController.CreatePromptRequest(
                "Repaired", "{}", parent));
    UUID originalReview = UUID.randomUUID(), nextReview = UUID.randomUUID(), qa = UUID.randomUUID();
    var mapper = new com.fasterxml.jackson.databind.ObjectMapper();
    for (var entry :
        java.util.List.of(
            java.util.Map.entry(originalReview, parent),
            java.util.Map.entry(nextReview, revision.id()))) {
      var payload =
          java.util.Map.of(
              "contentId",
              content,
              "promptVersionId",
              entry.getValue(),
              "bindingHash",
              "a".repeat(64),
              "generation",
              java.util.Map.of("apiModelId", "fixture-model"));
      jdbc.sql(
              "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                  + " (:id,'REVIEW',CAST(:payload AS jsonb))")
          .param("id", entry.getKey())
          .param("payload", mapper.writeValueAsString(payload))
          .update();
    }
    var qaPayload =
        java.util.Map.of(
            "videoId",
            video.toString(),
            "relativePath",
            path,
            "assetHash",
            hash,
            "reviewId",
            originalReview.toString(),
            "repairEconomics",
            java.util.Map.of("fullRerenderJustified", true));
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'ACTUAL_RENDER_QA',CAST(:payload AS jsonb))")
        .param("id", qa)
        .param("payload", mapper.writeValueAsString(qaPayload))
        .update();
    var request =
        java.util.Map.<String, Object>of(
            "parentVideoId",
            video.toString(),
            "qaRecordId",
            qa.toString(),
            "reviewId",
            nextReview.toString(),
            "reason",
            "Controlled mock QA justifies a full attempt");
    var handoff = workflow.regenerationHandoff(request);
    assertThat(handoff.get("parentAssetHash")).isEqualTo(hash);
    assertThat(handoff.get("executionScope")).isEqualTo("FULL_VIDEO_ONLY");
    assertThat(String.valueOf(workflow.regenerationHandoff(request).get("recordId")))
        .isEqualTo(String.valueOf(handoff.get("recordId")));
    java.nio.file.Files.writeString(file, "changed bytes");
    assertThatThrownBy(() -> workflow.regenerationHandoff(request))
        .isInstanceOf(IllegalArgumentException.class);
    org.mockito.Mockito.verifyNoInteractions(workflowMl);
  }

  private UUID repairReviewFixture(int findingCount) throws Exception {
    Long content =
        jdbc.sql(
                "INSERT INTO contents(title,type) VALUES ('session stop fixture','REEL') RETURNING"
                    + " id")
            .query(Long.class)
            .single();
    Long prompt =
        jdbc.sql(
                "INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES"
                    + " (:content,1,'Luca pushes. CUT') RETURNING id")
            .param("content", content)
            .query(Long.class)
            .single();
    UUID id = UUID.randomUUID();
    var findings = new java.util.ArrayList<java.util.Map<String, Object>>();
    for (int n = 0; n < findingCount; n++)
      findings.add(java.util.Map.of("confidence", "HIGH", "evidenceBasis", "MODEL_DOCUMENTED"));
    var payload =
        java.util.Map.of(
            "contentId",
            content,
            "promptVersionId",
            prompt,
            "decisionPolicyVersion",
            "impact-review-v1",
            "boundRequest",
            java.util.Map.of("profile", "post-family-v1", "prompt", "Luca pushes. CUT"),
            "planQuality",
            java.util.Map.of("status", "PASS"),
            "executionRisk",
            java.util.Map.of("status", "PASS"),
            "executionReview",
            java.util.Map.of("findings", findings));
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,payload) VALUES"
                + " (:id,'REVIEW',CAST(:payload AS jsonb))")
        .param("id", id)
        .param(
            "payload",
            new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(payload))
        .update();
    return id;
  }

  @Test
  void cancelledSessionAndEvidenceOnlySourceMakeZeroProviderCalls() throws Exception {
    var started = repairs.start(repairReviewFixture(1), "cancel", 2, 1);
    UUID id = UUID.fromString(String.valueOf(started.get("sessionId")));
    repairs.decide(id, "CANCELLED");
    assertThat(repairs.step(id).get("state")).isEqualTo("CANCELLED");
    var evidence = repairs.start(repairReviewFixture(0), "evidence", 2, 1);
    var stopped = repairs.step(UUID.fromString(String.valueOf(evidence.get("sessionId"))));
    assertThat(stopped.get("stopReason")).isEqualTo("TOLERANT_ONLY_OR_EVIDENCE_NEEDED");
    assertThat(stopped.get("reservedCostUsd")).isEqualTo(0.0);
    org.mockito.Mockito.verifyNoInteractions(workflowMl);
  }

  @Test
  void timedOutSessionReservesCeilingAndCannotRunAgain() throws Exception {
    var started = repairs.start(repairReviewFixture(1), "expired", 2, 1);
    UUID id = UUID.fromString(String.valueOf(started.get("sessionId")));
    jdbc.sql(
            "UPDATE workflow_repair_sessions SET"
                + " state='RUNNING',attempts=1,updated_at=now()-interval '16 minutes' WHERE id=:id")
        .param("id", id)
        .update();
    var stopped = repairs.get(id);
    assertThat(stopped.get("stopReason")).isEqualTo("PROVIDER_OUTCOME_UNKNOWN");
    assertThat(stopped.get("reservedCostUsd")).isEqualTo(1.0);
    assertThat(repairs.step(id).get("state")).isEqualTo("STOPPED");
    org.mockito.Mockito.verifyNoInteractions(workflowMl);
  }

  @Test
  void cancellationDuringProviderRetainsCostAndProposalWithoutCreatingVersion() throws Exception {
    var started = repairs.start(repairReviewFixture(1), "during-call", 2, 1);
    UUID id = UUID.fromString(String.valueOf(started.get("sessionId")));
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("creative-role"),
                org.mockito.ArgumentMatchers.anyMap()))
        .thenAnswer(
            invocation -> {
              repairs.decide(id, "CANCELLED");
              return java.util.Map.of(
                  "role",
                  "MINIMAL_REPAIR",
                  "provider",
                  "openai",
                  "model",
                  "fixture",
                  "result",
                  java.util.Map.of("patches", java.util.List.of()),
                  "costUpperBoundUsd",
                  0.01);
            });
    var stopped = repairs.step(id);
    assertThat(stopped.get("state")).isEqualTo("CANCELLED");
    assertThat(stopped.get("reservedCostUsd")).isEqualTo(0.01);
    assertThat((java.util.List<?>) stopped.get("history")).hasSize(1);
    assertThat(stopped.get("bestPromptVersionId"))
        .isEqualTo(started.get("originalPromptVersionId"));
    org.mockito.Mockito.verify(workflowMl, org.mockito.Mockito.never())
        .workflow(org.mockito.ArgumentMatchers.eq("repair"), org.mockito.ArgumentMatchers.anyMap());
  }

  @Test
  void movedPromptKeepsContentIdentityAndHistoricalSnapshotWhileMismatchedBytesReject()
      throws Exception {
    String root = "test/moved-" + UUID.randomUUID();
    var old = configuration.dataRoot().resolve(root + "/old/prompt.txt");
    var moved = configuration.dataRoot().resolve(root + "/新しい/prompt.yaml");
    java.nio.file.Files.createDirectories(old.getParent());
    java.nio.file.Files.createDirectories(moved.getParent());
    java.nio.file.Files.writeString(old, "Authoritative source text");
    workspace.importFolder(
        new com.pompomhills.intelligence.content.ContentWorkspaceController.ImportFolderRequest(
            root));
    long content =
        jdbc.sql("SELECT id FROM contents WHERE source_path=:path")
            .param("path", root + "/old/prompt.txt")
            .query(Long.class)
            .single();
    var version = workspace.prompts(content).getFirst();
    java.nio.file.Files.move(old, moved);
    workspace.reconcileSourcePath(
        content,
        new com.pompomhills.intelligence.content.ContentWorkspaceController.SourceAliasRequest(
            version.id(), root + "/新しい/prompt.yaml", "Operator moved the same file"));
    workspace.importFolder(
        new com.pompomhills.intelligence.content.ContentWorkspaceController.ImportFolderRequest(
            root));
    assertThat(
            jdbc.sql("SELECT count(*) FROM contents WHERE source_path LIKE :root")
                .param("root", root + "/%")
                .query(Long.class)
                .single())
        .isEqualTo(1);
    assertThat(
            workspace.prompts(content).stream()
                .anyMatch(
                    v ->
                        v.id().equals(version.id())
                            && v.sourcePath().equals(root + "/old/prompt.txt")))
        .isTrue();
    java.nio.file.Files.writeString(moved, "Different source");
    assertThatThrownBy(
            () ->
                workspace.reconcileSourcePath(
                    content,
                    new com.pompomhills.intelligence.content.ContentWorkspaceController
                        .SourceAliasRequest(version.id(), root + "/新しい/prompt.yaml", "Bad bytes")))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void exactRenderKeepsOldVersionAndConflictingAssetLineageStaysAmbiguous() {
    UUID video = insertVideo("rendered.mp4");
    long content =
        jdbc.sql("INSERT INTO contents(title,type) VALUES ('render source','REEL') RETURNING id")
            .query(Long.class)
            .single();
    long first =
        jdbc.sql(
                "INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES"
                    + " (:content,1,'Exact original') RETURNING id")
            .param("content", content)
            .query(Long.class)
            .single();
    long newer =
        workspace
            .createPrompt(
                content,
                new com.pompomhills.intelligence.content.ContentWorkspaceController
                    .CreatePromptRequest("Newer text", "{}", first))
            .id();
    for (long prompt : java.util.List.of(first, newer)) {
      UUID job =
          jdbc.sql(
                  "INSERT INTO"
                      + " render_jobs(content_id,prompt_version_id,job_type,openart_model,status)"
                      + " VALUES (:content,:prompt,'VIDEO','fixture','COMPLETE') RETURNING id")
              .param("content", content)
              .param("prompt", prompt)
              .query(UUID.class)
              .single();
      jdbc.sql(
              "INSERT INTO"
                  + " render_assets(render_job_id,content_id,asset_type,relative_path,file_size_bytes,width,height)"
                  + " VALUES (:job,:content,'VIDEO',:path,1,640,360)")
          .param("job", job)
          .param("content", content)
          .param("path", "test/" + video + ".mp4")
          .update();
      if (prompt == first)
        assertThat(contexts.get(video).prompt().promptVersionId()).isEqualTo(first);
    }
    assertThat(contexts.get(video).prompt()).isNull();
    assertThat(contexts.get(video).evidenceStatus()).isEqualTo("PROMPT_AMBIGUOUS");
    assertThat(contexts.get(video).candidates()).hasSize(2);
    assertThatThrownBy(
            () ->
                contexts.link(
                    video, first, "ORIGINAL", "Cannot overwrite conflicting render records"))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void secondAttemptPlateauKeepsBestIndependentVersionInsteadOfLatest() throws Exception {
    var started = repairs.start(repairReviewFixture(3), "two-attempts", 2, 1);
    UUID id = UUID.fromString(String.valueOf(started.get("sessionId")));
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("creative-role"),
                org.mockito.ArgumentMatchers.anyMap()))
        .thenReturn(
            java.util.Map.of(
                "role",
                "MINIMAL_REPAIR",
                "provider",
                "openai",
                "model",
                "fixture",
                "result",
                java.util.Map.of(
                    "patches",
                    java.util.List.of(
                        java.util.Map.of(
                            "sourceQuote", "CUT", "start", 13, "end", 16, "replacement", "Hold"))),
                "costUpperBoundUsd",
                0.01));
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("repair"), org.mockito.ArgumentMatchers.anyMap()))
        .thenReturn(
            java.util.Map.of("finalPrompt", "Luca pushes. Hold", "diff", "first"),
            java.util.Map.of("finalPrompt", "Luca pushes. Wait", "diff", "second"));
    var improved =
        java.util.Map.<String, Object>of(
            "bindingHash",
            "first-independent",
            "planQuality",
            java.util.Map.of("status", "PASS"),
            "executionRisk",
            java.util.Map.of("status", "PASS"),
            "executionReview",
            java.util.Map.of(
                "findings",
                java.util.List.of(
                    java.util.Map.of("confidence", "HIGH"),
                    java.util.Map.of("confidence", "HIGH"))));
    var plateau =
        java.util.Map.<String, Object>of(
            "bindingHash",
            "second-independent",
            "planQuality",
            java.util.Map.of("status", "PASS"),
            "executionRisk",
            java.util.Map.of("status", "PASS"),
            "executionReview",
            java.util.Map.of(
                "findings",
                java.util.List.of(
                    java.util.Map.of("confidence", "HIGH"),
                    java.util.Map.of("confidence", "HIGH"))));
    org.mockito.Mockito.when(
            workflowMl.workflow(
                org.mockito.ArgumentMatchers.eq("review"), org.mockito.ArgumentMatchers.anyMap()))
        .thenReturn(improved, plateau);
    var first = repairs.step(id);
    assertThat(first.get("state")).isEqualTo("READY");
    var second = repairs.step(id);
    assertThat(second.get("stopReason")).isEqualTo("NO_IMPROVEMENT");
    assertThat(second.get("bestPromptVersionId")).isEqualTo(first.get("bestPromptVersionId"));
    assertThat(second.get("attempts")).isEqualTo(2);
    assertThat((java.util.List<?>) second.get("history")).hasSize(2);
    assertThat(repairs.decide(id, "ACCEPTED").get("bestReviewId"))
        .isEqualTo(first.get("bestReviewId"));
    repairs.step(id);
    org.mockito.Mockito.verify(workflowMl, org.mockito.Mockito.times(2))
        .workflow(
            org.mockito.ArgumentMatchers.eq("creative-role"),
            org.mockito.ArgumentMatchers.anyMap());
  }

  @Test
  void verifiedPromotionChangesActualInferenceSelectionAndRollbackRestoresPreviousArtifact()
      throws Exception {
    String platform = "model-fixture-" + UUID.randomUUID();
    UUID first = UUID.randomUUID(), second = UUID.randomUUID();
    for (UUID id : java.util.List.of(first, second))
      jdbc.sql(
              "INSERT INTO"
                  + " model_versions(id,version,model_type,platform,training_dataset_version,feature_version,knowledge_cutoff,metrics,artifact_path,status,trained_at)"
                  + " VALUES"
                  + " (:id,:version,'prediction',:platform,'fixture','prerender-v5-motion-intensity-v1','2025-01-01T00:00:00Z',CAST(:metrics"
                  + " AS jsonb),:path,:status,now())")
          .param("id", id)
          .param("version", id.toString())
          .param("platform", platform)
          .param("path", "models/statistical/" + id + ".json")
          .param("status", id.equals(first) ? "CHAMPION" : "CHALLENGER")
          .param(
              "metrics",
              "{\"pipelineVersion\":\"grouped-ridge-72h-v1\",\"artifactSha256\":\""
                  + "a".repeat(64)
                  + "\"}")
          .update();
    org.mockito.Mockito.doAnswer(
            invocation -> {
              String path = invocation.getArgument(1);
              return java.util.Map.of(
                  "verified",
                  true,
                  "promotionEligible",
                  true,
                  "featureVersion",
                  "prerender-v5-motion-intensity-v1",
                  "knowledgeCutoff",
                  "2025-01-01T00:00:00Z",
                  "datasetVersion",
                  "fixture",
                  "modelVersion",
                  path.substring(path.lastIndexOf('/') + 1, path.length() - 5));
            })
        .when(training)
        .verify(
            org.mockito.ArgumentMatchers.eq(platform),
            org.mockito.ArgumentMatchers.anyString(),
            org.mockito.ArgumentMatchers.anyMap());
    var mvc =
        org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup(modelRegistry)
            .build();
    mvc.perform(
            org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post(
                    "/api/v1/models/" + second + "/promote")
                .contentType("application/json")
                .content("{\"reason\":\"Verified fixture holdout\"}"))
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk());
    UUID video = insertVideo("model-selection.mp4");
    var fingerprint =
        org.mockito.Mockito.mock(
            com.pompomhills.intelligence.creative.CreativeFingerprintEntity.class);
    var analysis =
        org.mockito.Mockito.mock(
            com.pompomhills.intelligence.creative.CreativeAnalysisEntity.class);
    org.mockito.Mockito.when(fingerprint.getAnalysis()).thenReturn(analysis);
    org.mockito.Mockito.when(analysis.getSemanticVideoEvidence()).thenReturn(java.util.Map.of());
    org.mockito.Mockito.when(analysis.getAnalysisVersion()).thenReturn("fixture-v1");
    org.mockito.Mockito.when(fingerprint.getFeatures())
        .thenReturn(java.util.Map.of("overallMotionIntensity", java.util.Map.of("value", 0.5)));
    org.mockito.Mockito.when(fingerprints.findFirstByVideoIdOrderByCreatedAtDesc(video))
        .thenReturn(java.util.Optional.of(fingerprint));
    org.mockito.Mockito.when(
            predictionMl.prepublish(
                org.mockito.ArgumentMatchers.eq(platform),
                org.mockito.ArgumentMatchers.anyMap(),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.anyMap()))
        .thenAnswer(
            invocation -> {
              java.util.Map<String, Object> reference = invocation.getArgument(3);
              return new com.pompomhills.intelligence.prediction.ml.MlPredictionClient
                  .PredictionResponse(
                  "v1",
                  String.valueOf(reference.get("modelVersion")),
                  "fixture",
                  "prerender-v5-motion-intensity-v1",
                  "LOW",
                  30,
                  java.util.Map.of());
            });
    assertThat(predictions.generate(video, platform).modelVersion()).isEqualTo(second.toString());
    mvc.perform(
            org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post(
                    "/api/v1/models/" + first + "/rollback")
                .contentType("application/json")
                .content("{\"reason\":\"Restore prior verified artifact\"}"))
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk());
    assertThat(predictions.generate(video, platform).modelVersion()).isEqualTo(first.toString());
    assertThat(predictions.history(video)).hasSize(2);
  }

  @Test
  void trainingWithoutVerifiedMatureSnapshotsCannotCreateArtifact() {
    assertThatThrownBy(() -> training.train("instagram", "Eligibility fixture"))
        .isInstanceOf(org.springframework.web.server.ResponseStatusException.class)
        .hasMessageContaining("30 verified mature");
  }
}
