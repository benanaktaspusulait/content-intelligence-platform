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
  @Autowired com.pompomhills.intelligence.workflow.WorkflowService workflow;
  @Autowired com.pompomhills.intelligence.content.ContentWorkspaceController workspace;
  @Autowired com.pompomhills.intelligence.workflow.WorkflowRepairSessionService repairs;
  @org.springframework.test.context.bean.override.mockito.MockitoBean com.pompomhills.intelligence.quality.QualityMlClient workflowMl;

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
    UUID qa = UUID.randomUUID(); UUID lesson = UUID.randomUUID(); UUID approved = UUID.randomUUID();
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES (:id,'ACTUAL_RENDER_QA','{\"viewerFacingUsability\":\"USABLE\"}')").param("id", qa).update();
    String payload = "{\"parentRecordId\":\"" + lesson + "\",\"reviewStatus\":\"APPROVED\",\"contentProfile\":\"EDUCATIONAL\",\"targetModelVersion\":\"model-v1\",\"durationRange\":[10,20],\"sampleSize\":1,\"evidenceBasis\":[\"" + qa + "\"]}";
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES (:id,'LEARNING_REVIEW',CAST(:payload AS jsonb))").param("id", approved).param("payload", payload).update();
    assertThat(workflow.retrieveLessons("EDUCATIONAL", "model-v1", 15)).hasSize(1);
    assertThat(workflow.retrieveLessons("EDUCATIONAL", "model-v1", 30)).isEmpty();
    assertThat(workflow.retrieveLessons("CURIOSITY_ADVENTURE", "model-v1", 15)).isEmpty();
    workflow.reviewLearning(approved, java.util.Map.of("decision", "REVOKED", "reason", "Evidence no longer reliable"));
    assertThat(workflow.retrieveLessons("EDUCATIONAL", "model-v1", 15)).isEmpty();
  }

  @Test
  void promotionCannotChangeRegistryWithoutActiveArtifactInference() throws Exception {
    UUID challenger = UUID.randomUUID(); UUID champion = UUID.randomUUID();
    String platform = "test-" + challenger;
    for (UUID id : java.util.List.of(challenger, champion)) {
      jdbc.sql("INSERT INTO model_versions(id,version,model_type,platform,training_dataset_version,feature_version,knowledge_cutoff,metrics,status,trained_at) VALUES (:id,:version,'prediction',:platform,'fixture','fixture',now(),'{}',:status,now())")
          .param("id", id).param("version", id.toString()).param("platform", platform)
          .param("status", id.equals(champion) ? "CHAMPION" : "CHALLENGER").update();
    }
    var controller = new com.pompomhills.intelligence.modelregistry.api.ModelRegistryController(jdbc, new tools.jackson.databind.ObjectMapper());
    var mvc = org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup(controller).build();
    mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/api/v1/models/" + challenger + "/promote"))
        .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isNotImplemented());
    assertThat(jdbc.sql("SELECT status FROM model_versions WHERE id=:id").param("id", challenger).query(String.class).single()).isEqualTo("CHALLENGER");
    assertThat(jdbc.sql("SELECT status FROM model_versions WHERE id=:id").param("id", champion).query(String.class).single()).isEqualTo("CHAMPION");
  }

  @Test
  void savedRevisionPreservesExactParentSourceAndRejectsCrossContentParent() {
    Long content = jdbc.sql("INSERT INTO contents(title,type) VALUES ('revision fixture','REEL') RETURNING id").query(Long.class).single();
    Long parent = jdbc.sql("INSERT INTO prompt_versions(content_id,version_number,raw_text,source_path) VALUES (:content,1,'Original','library/fixture/prompt.txt') RETURNING id")
        .param("content", content).query(Long.class).single();
    var revision = workspace.createPrompt(content, new com.pompomhills.intelligence.content.ContentWorkspaceController.CreatePromptRequest("Edited", "{}", parent));
    assertThat(revision.sourcePath()).isEqualTo("library/fixture/prompt.txt");
    assertThat(jdbc.sql("SELECT parent_prompt_version_id FROM prompt_versions WHERE id=:id").param("id", revision.id()).query(Long.class).single()).isEqualTo(parent);
    Long other = jdbc.sql("INSERT INTO contents(title,type) VALUES ('other','REEL') RETURNING id").query(Long.class).single();
    assertThatThrownBy(() -> workspace.createPrompt(other, new com.pompomhills.intelligence.content.ContentWorkspaceController.CreatePromptRequest("Wrong parent", "{}", parent))).isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void sourceScopedRestoreFindsSavedReviewEvenBehindMoreThanTwoHundredUnrelatedRecords() {
    UUID saved = UUID.randomUUID();
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload,created_at) VALUES (:id,'REVIEW','{\"contentId\":888,\"promptVersionId\":999}',now()-interval '1 day')").param("id", saved).update();
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload) SELECT gen_random_uuid(),'REVIEW','{\"contentId\":1,\"promptVersionId\":2}'::jsonb FROM generate_series(1,201)").update();
    assertThat(workflow.list("REVIEW", "888", "999", null)).hasSize(1);
    assertThat(workflow.list("REVIEW", "888", "999", null).getFirst().get("recordId")).isEqualTo(saved.toString());
  }

  @Test
  void boundedRepairCreatesIndependentVersionAndReplayCannotMakeMoreCalls() throws Exception {
    Long content = jdbc.sql("INSERT INTO contents(title,type) VALUES ('repair fixture','REEL') RETURNING id").query(Long.class).single();
    Long parent = jdbc.sql("INSERT INTO prompt_versions(content_id,version_number,raw_text) VALUES (:content,1,'Luca pushes. CUT') RETURNING id").param("content", content).query(Long.class).single();
    UUID review = UUID.randomUUID();
    var bound = java.util.Map.of("profile","post-family-v1","prompt","Luca pushes. CUT","sourceId","fixture","sourceVersion",parent.toString(),"protectedIntent",java.util.List.of("Luca pushes."));
    var original = new java.util.LinkedHashMap<String,Object>();
    original.put("contentId",content); original.put("promptVersionId",parent); original.put("decisionPolicyVersion","impact-review-v1"); original.put("boundRequest",bound);
    original.put("planQuality",java.util.Map.of("status","PASS")); original.put("executionRisk",java.util.Map.of("status","PASS"));
    original.put("executionReview",java.util.Map.of("findings",java.util.List.of(java.util.Map.of("confidence","HIGH","evidenceBasis","MODEL_DOCUMENTED"))));
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES (:id,'REVIEW',CAST(:payload AS jsonb))").param("id",review).param("payload",new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(original)).update();
    org.mockito.Mockito.when(workflowMl.workflow(org.mockito.ArgumentMatchers.eq("creative-role"),org.mockito.ArgumentMatchers.anyMap())).thenReturn(java.util.Map.of("role","MINIMAL_REPAIR","provider","openai","model","fixture-model","result",java.util.Map.of("patches",java.util.List.of(java.util.Map.of("start",13,"end",16,"sourceQuote","CUT","replacement","Hold."))),"costUpperBoundUsd",0.01));
    org.mockito.Mockito.when(workflowMl.workflow(org.mockito.ArgumentMatchers.eq("repair"),org.mockito.ArgumentMatchers.anyMap())).thenReturn(java.util.Map.of("finalPrompt","Luca pushes. Hold.","bindingHash","repair","diff","CUT -> Hold."));
    org.mockito.Mockito.when(workflowMl.workflow(org.mockito.ArgumentMatchers.eq("review"),org.mockito.ArgumentMatchers.anyMap())).thenReturn(java.util.Map.of("bindingHash","independent","decisionPolicyVersion","impact-review-v1","originalPrompt","Luca pushes. Hold.","planQuality",java.util.Map.of("status","PASS"),"executionRisk",java.util.Map.of("status","PASS"),"executionReview",java.util.Map.of("findings",java.util.List.of())));
    var started = repairs.start(review,"single-call",2,1);
    UUID session = UUID.fromString(String.valueOf(started.get("sessionId")));
    assertThat(repairs.start(review,"single-call",2,1).get("sessionId")).isEqualTo(session.toString());
    var finished = repairs.step(session);
    assertThat(finished.get("state")).isEqualTo("STOPPED");
    assertThat(((Number)finished.get("bestPromptVersionId")).longValue()).isNotEqualTo(parent.longValue());
    assertThat(finished.get("stopReason")).isEqualTo("INDEPENDENT_REVIEW_CLEAR");
    repairs.step(session); repairs.decide(session,"ACCEPTED");
    org.mockito.Mockito.verify(workflowMl,org.mockito.Mockito.times(1)).workflow(org.mockito.ArgumentMatchers.eq("creative-role"),org.mockito.ArgumentMatchers.anyMap());
    assertThat(jdbc.sql("SELECT raw_text FROM prompt_versions WHERE id=:id").param("id",parent).query(String.class).single()).isEqualTo("Luca pushes. CUT");
  }

}
