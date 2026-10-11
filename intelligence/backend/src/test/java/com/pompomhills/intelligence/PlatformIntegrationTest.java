package com.pompomhills.intelligence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pompomhills.intelligence.character.CharacterService;
import com.pompomhills.intelligence.workflow.WorkflowService;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.performance.DiscoveryProfileService;
import com.pompomhills.intelligence.performance.InterventionService;
import com.pompomhills.intelligence.performance.PerformanceImportService;
import com.pompomhills.intelligence.performance.PlatformGrowthProfileService;
import com.pompomhills.intelligence.platformstate.PlatformStateService;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.times;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
@Import(PlatformIntegrationTest.WorkflowMlMockConfiguration.class)
class PlatformIntegrationTest {
  @org.springframework.boot.test.context.TestConfiguration
  static class WorkflowMlMockConfiguration {
    @Bean
    @Primary
    QualityMlClient workflowMlMock() {
      return org.mockito.Mockito.mock(QualityMlClient.class);
    }
  }
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

  @Autowired JdbcTemplate jdbc;
  @Autowired PerformanceImportService imports;
  @Autowired PlatformStateService platformStates;
  @Autowired PlatformGrowthProfileService growthProfiles;
  @Autowired InterventionService interventions;
  @Autowired DiscoveryProfileService discoveryProfiles;
  @Autowired CharacterService characters;
  @Autowired WorkflowService workflow;
  @Autowired QualityMlClient workflowMl;

  private UUID videoId;

  @BeforeEach
  void createVideo() {
    jdbc.update("TRUNCATE videos, import_batches CASCADE");
    videoId = UUID.randomUUID();
    jdbc.update(
        """
        INSERT INTO videos
          (id,content_hash,original_filename,relative_path,duration_ms,width,height,fps,
           aspect_ratio,codec,audio_present,status,ingested_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        videoId,
        "a".repeat(64),
        "pilot.mp4",
        "videos/original/pilot.mp4",
        15104,
        1080,
        1920,
        30.0,
        0.5625,
        "h264",
        true,
        "ANALYSED",
        OffsetDateTime.now(ZoneOffset.UTC));
  }

  @Test
  void savedStoryApprovalRequiresExactCandidateAndRestoreKeepsApprovedState() throws Exception {
    UUID storyId = UUID.randomUUID();
    String text = "Mimi finds a blue note and follows it.";
    String fingerprint = storyFingerprintForTest(text);
    String payload = """
        {"role":"STORY","sourceRequest":{"text":"Mimi idea","context":{"title":"Mimi's Note"}},
         "result":{"role":"STORY","alternatives":[{"candidateId":"candidate-1","title":"Blue note","text":"%s"}]}}
        """.formatted(text);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", storyId, payload);

    assertThatThrownBy(() -> workflow.approveStory(storyId, java.util.Map.of(
        "approvedText", text, "candidateId", "candidate-2",
        "revisionId", "candidate-2-revision-" + fingerprint, "contentFingerprint", fingerprint)))
        .hasMessageContaining("does not match");

    workflow.approveStory(storyId, java.util.Map.of(
        "approvedText", text, "candidateId", "candidate-1",
        "revisionId", "candidate-1-revision-" + fingerprint, "contentFingerprint", fingerprint));
    assertThatThrownBy(() -> workflow.changeLifecycle(storyId, java.util.Map.of("status", "DELETED")))
        .hasMessageContaining("Archive it instead");
    var duplicate = workflow.duplicateCreativeRole(storyId);
    assertThat(duplicate.get("lifecycleStatus")).isEqualTo("DRAFT");
    assertThat(workflow.list("STORY_APPROVAL").stream()
        .noneMatch(row -> duplicate.get("recordId").equals(row.get("storyRecordId")))).isTrue();
    var archived = workflow.changeLifecycle(storyId, java.util.Map.of("status", "ARCHIVED"));
    assertThat(archived.get("status")).isEqualTo("ARCHIVED");
    var restored = workflow.changeLifecycle(storyId, java.util.Map.of("status", "DRAFT"));
    assertThat(restored.get("status")).isEqualTo("APPROVED");
  }

  @Test
  void productionPromptRequiresExactSavedStoryApprovalBeforeProviderDispatch() {
    UUID storyId = UUID.randomUUID();
    String text = "Mimi places a note on the cabinet, but it sticks to her paw.";
    String fingerprint = storyFingerprintForTest(text);
    String payload = """
        {"role":"STORY","sourceRequest":{"text":"Mimi note idea"},
         "result":{"role":"STORY","alternatives":[{"candidateId":"candidate-1","title":"Note","text":"%s"}]}}
        """.formatted(text);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", storyId, payload);
    var request = java.util.Map.<String, Object>of(
        "role", "BUILD_PROMPT", "text", text, "maxCostUsd", 0.05,
        "context", java.util.Map.of("sourceStoryRecordId", storyId.toString(), "candidateId", "candidate-1",
            "storyRevisionId", "candidate-1-revision-" + fingerprint, "approvalRecordId", "missing-approval"));
    assertThatThrownBy(() -> workflow.creativeRole(request))
        .hasMessageContaining("exact approved story candidate and revision");
  }

  @Test
  void legacyPromptMigrationRecoversExactLineageIsIdempotentAndPreservesOriginalRecord() {
    UUID storyId = UUID.randomUUID();
    UUID promptId = UUID.randomUUID();
    String text = "Mimi stands by a messy cabinet. A sticky note sticks to her paw. She hides behind it.";
    String fingerprint = storyFingerprintForTest(text);
    String storyPayload = """
        {"role":"STORY","result":{"alternatives":[{"candidateId":"candidate-1","title":"The Note","text":"%s"}]}}
        """.formatted(text);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", storyId, storyPayload);
    var approval = workflow.approveStory(storyId, java.util.Map.of("approvedText", text,
        "candidateId", "candidate-1", "revisionId", "candidate-1-revision-" + fingerprint,
        "contentFingerprint", fingerprint));
    workflow.saveStudioSession(java.util.Map.of("sessionId", UUID.randomUUID().toString(),
        "storyRecordId", storyId.toString(), "title", "Mimi Note Project",
        "workspacePath", "library/pompom/mimi"));
    String prompt = "TIMED SHOT PLAN: 0-3s: Mimi stands by the cabinet. 3-6s: A sticky note sticks to her paw. 6-8s: Mimi hides behind the cabinet.";
    String buildPayload = """
        {"role":"BUILD_PROMPT","calls":1,"provider":"openai","sourceRequest":{"role":"BUILD_PROMPT","text":"%s","context":{"sourceStoryRecordId":"%s","candidateId":"candidate-1","storyRevisionId":"candidate-1-revision-%s","targetConfiguration":{"duration":8,"aspectRatio":"9:16","selectedGenerator":"SEEDANCE_2_0_MINI","contentProfile":"ABSURD_PHYSICS","mainCharacter":"Mimi"},"characterRecord":{"id":"00000000-0000-0000-0000-000000000003","name":"Mimi"}}},"result":{"prompt":"%s","productionPlan":{"legacy":"preserved"}}}
        """.formatted(text, storyId, fingerprint, prompt);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", promptId, buildPayload);
    var projection = java.util.Map.<String, Object>of("prompt", prompt, "providerCalls", 0,
        "validationStatus", "NOT_VALIDATED", "productionPlan", java.util.Map.of("builderContractVersion", "openart-production-prompt-v2"));
    doReturn(projection).when(workflowMl).workflow(org.mockito.ArgumentMatchers.eq("creative-role/revalidate-production-spec"), org.mockito.ArgumentMatchers.anyMap());

    var first = workflow.revalidateProductionSpec(promptId);
    var second = workflow.revalidateProductionSpec(promptId);
    assertThat(String.valueOf(first.get("recordId"))).isEqualTo(String.valueOf(second.get("recordId")));
    assertThat(first.get("providerCalls")).isEqualTo(0);
    assertThat(((java.util.Map<?, ?>) first.get("sourceLineage")).get("storyRecordId")).isEqualTo(storyId.toString());
    assertThat(((java.util.Map<?, ?>) first.get("sourceLineage")).get("approvalRecordId")).isEqualTo(String.valueOf(approval.get("recordId")));
    assertThat(((java.util.Map<?, ?>) first.get("sourceLineage")).get("projectTitle")).isEqualTo("Mimi Note Project");
    assertThat(jdbc.queryForObject("SELECT payload->'result'->>'prompt' FROM post_family_workflow_events WHERE id=?", String.class, promptId)).isEqualTo(prompt);
    assertThat(jdbc.queryForObject("SELECT payload->'result'->'productionPlan'->>'legacy' FROM post_family_workflow_events WHERE id=?", String.class, promptId)).isEqualTo("preserved");
    assertThat(jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events WHERE kind='PRODUCTION_SPEC_MIGRATION' AND payload->>'sourceRecordId'=?", Integer.class, promptId.toString())).isEqualTo(1);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM prompt_versions", Integer.class)).isZero();
    verify(workflowMl, times(1)).workflow(org.mockito.ArgumentMatchers.eq("creative-role/revalidate-production-spec"), org.mockito.ArgumentMatchers.anyMap());
  }

  @Test
  void legacyMigrationDoesNotGuessMissingApprovalOrTreatBuildTextAsApprovedSource() {
    UUID storyId = UUID.randomUUID();
    UUID promptId = UUID.randomUUID();
    String text = "Mimi finds a note and follows it.";
    String fingerprint = storyFingerprintForTest(text);
    String storyPayload = """
        {"role":"STORY","result":{"alternatives":[{"candidateId":"candidate-1","title":"Note","text":"%s"}]}}
        """.formatted(text);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", storyId, storyPayload);
    String prompt = "0-3s: Mimi finds a note.";
    String buildPayload = """
        {"role":"BUILD_PROMPT","sourceRequest":{"role":"BUILD_PROMPT","text":"%s","context":{"sourceStoryRecordId":"%s","candidateId":"candidate-1","storyRevisionId":"candidate-1-revision-%s","targetConfiguration":{"duration":3,"aspectRatio":"9:16"}}},"result":{"prompt":"%s"}}
        """.formatted(text, storyId, fingerprint, prompt);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", promptId, buildPayload);
    var projection = java.util.Map.<String, Object>of("prompt", prompt, "providerCalls", 0, "productionPlan", java.util.Map.of());
    doReturn(projection).when(workflowMl).workflow(org.mockito.ArgumentMatchers.eq("creative-role/revalidate-production-spec"), org.mockito.ArgumentMatchers.anyMap());

    org.mockito.Mockito.clearInvocations(workflowMl);
    var migrated = workflow.revalidateProductionSpec(promptId);
    org.mockito.ArgumentCaptor<java.util.Map<String, Object>> request = org.mockito.ArgumentCaptor.forClass(java.util.Map.class);
    verify(workflowMl).workflow(org.mockito.ArgumentMatchers.eq("creative-role/revalidate-production-spec"), request.capture());
    assertThat(request.getValue().get("approvedStory")).isEqualTo("");
    var lineage = (java.util.Map<?, ?>) migrated.get("sourceLineage");
    assertThat(lineage.get("storyRecordId")).isEqualTo(storyId.toString());
    assertThat(lineage.get("approvalRecordId")).isEqualTo("UNKNOWN");
    assertThat(lineage.get("sourceLineageStatus")).isEqualTo("EXACT_STORY_POINTER_NO_EXACT_APPROVAL");
  }

  @Test
  void independentDraftCanBeSafelySoftDeleted() {
    UUID storyId = UUID.randomUUID();
    String payload = """
        {"role":"STORY","sourceRequest":{"text":"An independent draft"},
         "result":{"role":"STORY","alternatives":[{"candidateId":"candidate-1","text":"A standalone saved draft."}]}}
        """;
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", storyId, payload);
    var deleted = workflow.changeLifecycle(storyId, java.util.Map.of("status", "DELETED", "reason", "Operator confirmed"));
    assertThat(deleted.get("status")).isEqualTo("DELETED");
    assertThat(workflow.get(storyId)).containsEntry("role", "STORY");
  }

  @Test
  void operatorStoryEditCreatesNewDraftWithExactParentLineage() {
    UUID storyId = UUID.randomUUID();
    String original = "Mimi finds a blue note.";
    String revised = "Mimi finds a blue note and follows it to a tiny stage.";
    String fingerprint = storyFingerprintForTest(original);
    String payload = """
        {"role":"STORY","title":"Mimi's Note","sourceRequest":{"text":"Mimi idea","context":{"title":"Mimi's Note"}},
         "result":{"role":"STORY","alternatives":[{"candidateId":"candidate-1","text":"%s"}]}}
        """.formatted(original);
    jdbc.update("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES (?,'CREATIVE_ROLE',null,CAST(? AS jsonb))", storyId, payload);

    var revision = workflow.saveStoryRevision(storyId, java.util.Map.of(
        "candidateId", "candidate-1", "revisionId", "candidate-1-revision-" + fingerprint,
        "text", revised, "title", "Mimi's Note"));
    assertThat(revision.get("revisionType")).isEqualTo("OPERATOR_EDIT");
    assertThat(revision.get("sourceRecordId")).isEqualTo(storyId.toString());
    assertThat(((java.util.Map<?, ?>) revision.get("sourceRequest")).get("context").toString())
        .contains(storyId.toString(), "candidate-1-revision-" + fingerprint);
    assertThat(workflow.list("STORY_APPROVAL").stream()
        .noneMatch(row -> storyId.toString().equals(row.get("storyRecordId")))).isTrue();
  }

  private String storyFingerprintForTest(String value) {
    int hash = 0x811c9dc5;
    for (int i = 0; i < value.length(); i++) hash = (hash ^ value.charAt(i)) * 0x01000193;
    return String.format("%08x", hash);
  }

  @Test
  void lockedPredictionPayloadCannotBeChangedButCanBeMarkedEvaluated() {
    UUID predictionId = UUID.randomUUID();
    jdbc.update(
        """
        INSERT INTO predictions
          (id,video_id,platform,prediction_type,status,model_version,dataset_version,
           feature_version,knowledge_cutoff,payload,confidence,comparable_sample_size)
        VALUES (?,?,'instagram','PRE_PUBLISH','DRAFT','cold-start-v1','none','fingerprint-v1',
                ?,CAST(? AS jsonb),'LOW',0)
        """,
        predictionId,
        videoId,
        OffsetDateTime.now(ZoneOffset.UTC),
        "{\"expectedValue\":null}");
    jdbc.update("UPDATE predictions SET status='LOCKED',locked_at=now() WHERE id=?", predictionId);

    assertThatThrownBy(
            () ->
                jdbc.update(
                    "UPDATE predictions SET payload=CAST(? AS jsonb) WHERE id=?",
                    "{\"expectedValue\":999999}",
                    predictionId))
        .isInstanceOf(DataAccessException.class)
        .hasMessageContaining("immutable");

    assertThat(jdbc.update("UPDATE predictions SET status='EVALUATED' WHERE id=?", predictionId))
        .isEqualTo(1);
  }

  @Test
  void csvPreviewAndCommitPreserveRawRowAndCreateNullableObservation() {
    String csv =
        "video_id,views,likes,comments,measurement_timestamp,metric_semantics\n"
            + videoId
            + ",60000,151,13,2026-09-28T07:05:00Z,SNAPSHOT\n";
    var upload =
        new MockMultipartFile(
            "file", "meta-export.csv", "text/csv", csv.getBytes(StandardCharsets.UTF_8));

    var preview = imports.preview(upload, "facebook", "Europe/London");
    assertThat(preview.matchedRows()).isEqualTo(1);
    assertThat(preview.unresolvedRows()).isZero();

    var committed = imports.commit(preview.batchId());
    assertThat(committed.status()).isEqualTo("COMMITTED");
    assertThat(
            jdbc.queryForObject(
                "SELECT views FROM performance_observations WHERE video_id=?", Long.class, videoId))
        .isEqualTo(60000L);
    assertThat(
            jdbc.queryForObject(
                "SELECT raw_data->>'comments' FROM import_rows WHERE import_batch_id=?",
                String.class,
                preview.batchId()))
        .isEqualTo("13");
  }

  @Test
  void discoveryProfileUsesReportedNonFollowerAndUsAudienceShares() {
    String csv =
        "video_id,views,follows,measurement_timestamp,metric_semantics,non_follower_share,us_audience_share\n"
            + videoId
            + ",60000,30,2026-09-29T08:00:00Z,SNAPSHOT,99,19.8\n";
    var upload =
        new MockMultipartFile(
            "file", "dev-corap-discovery.csv", "text/csv", csv.getBytes(StandardCharsets.UTF_8));

    var preview = imports.preview(upload, "facebook", "Europe/London");
    imports.commit(preview.batchId());

    var profile =
        discoveryProfiles.profile(
            videoId, "facebook", Instant.parse("2026-09-29T09:00:00Z"), null);
    assertThat(profile.nonFollowerShare()).isEqualTo(99.0);
    assertThat(profile.usAudienceShare()).isEqualTo(19.8);
    assertThat(profile.estimatedUsAudience()).isEqualTo(11880L);
    assertThat(profile.followsPerThousandViews()).isEqualTo(0.5);
    assertThat(profile.newAudienceQualityScore()).isEqualTo(99.0);
    assertThat(profile.algorithmVersion()).isEqualTo("new-audience-quality-v1");
    assertThat(
            jdbc.queryForObject(
                "SELECT metric_value FROM derived_performance_metrics WHERE metric_name='new_audience_quality_score'",
                Double.class))
        .isEqualTo(99.0);

    var live =
        platformStates.liveFeatures(
            videoId, "facebook", Instant.parse("2026-09-29T09:00:00Z"), "LIVE");
    assertThat(live.features())
        .containsEntry("nonFollowerShare", 99.0)
        .containsEntry("usAudienceShare", 19.8)
        .containsEntry("newAudienceQualityScore", 99.0)
        .containsEntry("newAudienceQualityAlgorithm", "new-audience-quality-v1");
  }

  @Test
  void unresolvedImportCanBeManuallyMatchedAndAuditedBeforeCommit() {
    String csv = "filename,views,measurement_timestamp\nunknown.mp4,42,2026-09-28T07:05:00Z\n";
    var upload =
        new MockMultipartFile(
            "file", "manual-match.csv", "text/csv", csv.getBytes(StandardCharsets.UTF_8));

    var preview = imports.preview(upload, "instagram", "UTC");
    assertThat(preview.unresolvedRows()).isEqualTo(1);
    UUID rowId = imports.rows(preview.batchId()).getFirst().id();

    var resolved = imports.resolve(preview.batchId(), rowId, videoId, "Selected in import review");
    assertThat(resolved.matchedRows()).isEqualTo(1);
    assertThat(resolved.unresolvedRows()).isZero();
    assertThat(imports.rows(preview.batchId()).getFirst().matchStatus()).isEqualTo("MANUAL");
    assertThat(
            jdbc.queryForObject(
                "SELECT count(*) FROM audit_events WHERE entity_id=? AND action='MANUAL_IMPORT_MATCH'",
                Integer.class,
                rowId))
        .isEqualTo(1);
    assertThat(imports.commit(preview.batchId()).status()).isEqualTo("COMMITTED");
  }

  @Test
  void reachFurtherTracksFirstLastAgeAndPerformanceWindowsWithoutCausalClaims() {
    Instant published = Instant.parse("2026-09-28T20:00:00Z");
    Instant first = Instant.parse("2026-09-28T22:00:00Z");
    platformStates.recordPublication(
        videoId,
        new PlatformStateService.PublicationRequest(
            null, "facebook", null, null, published, "Europe/London", true, "MANUAL", "Late slot"),
        "test-user");
    addReachFurther("ACTIVE", first, null);
    addReachFurther("ACTIVE", first.plusSeconds(3600), null);
    insertPerformance(published, first.minusSeconds(1800), 100L, 90L);
    insertPerformance(published, first, 150L, 120L);
    insertPerformance(published, first.plusSeconds(3600), 350L, 280L);
    insertPerformance(published, first.plusSeconds(3 * 3600), 900L, 700L);

    var summary = platformStates.reachFurtherSummary(videoId, "facebook");
    assertThat(summary.firstObservedAt()).isEqualTo(first);
    assertThat(summary.lastObservedAt()).isEqualTo(first.plusSeconds(3600));
    assertThat(summary.observationCount()).isEqualTo(2);
    assertThat(summary.videoAgeAtFirstObservationSeconds()).isEqualTo(7200);
    assertThat(summary.cohort()).isEqualTo("REACH_FURTHER_EARLY");
    assertThat(summary.offPeakPublish()).isTrue();
    assertThat(summary.publicationContextLabel()).isEqualTo("LOW-SIGNAL / OFF-PEAK TEST");
    assertThat(summary.performanceWindows().get("1h").deltaViews()).isEqualTo(200);
    assertThat(summary.causalDisclaimer()).contains("not treated as a cause");

    assertThatThrownBy(() -> addReachFurther("ACTIVE", first, null))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("Duplicate");
  }

  @Test
  void unknownTimingStaysUnknownAndPrePublishCannotReadLiveState() {
    addReachFurther("ACTIVE", null, null);

    var summary = platformStates.reachFurtherSummary(videoId, "facebook");
    assertThat(summary.firstObservedAt()).isNull();
    assertThat(summary.cohort()).isEqualTo("UNKNOWN_TIMING");
    var guarded =
        platformStates.liveFeatures(
            videoId, "facebook", Instant.parse("2026-09-29T08:00:00Z"), "PRE_PUBLISH");
    assertThat(guarded.allowed()).isFalse();
    assertThat(guarded.features()).isEmpty();
    assertThat(guarded.reason()).isEqualTo("PRE_PUBLISH_LEAKAGE_GUARD");
  }

  @Test
  void correctionIsAppendOnlyAndAuditTrailPreservesTheOriginal() {
    Instant observed = Instant.parse("2026-09-28T23:32:00Z");
    var original = addReachFurther("ACTIVE", observed, null);
    var correction =
        platformStates.observe(
            videoId,
            new PlatformStateService.ObservationRequest(
                null,
                "facebook",
                PlatformStateService.REACH_FURTHER,
                "INACTIVE",
                observed.plusSeconds(60),
                "MANUAL",
                null,
                1.0,
                "Corrected after dashboard review",
                null,
                null,
                true,
                original.id()),
            "test-user");

    assertThat(platformStates.observations(videoId, "facebook")).hasSize(2);
    assertThat(platformStates.reachFurtherSummary(videoId, "facebook").active()).isFalse();
    assertThat(correction.correctionOfObservationId()).isEqualTo(original.id());
    assertThat(
            jdbc.queryForObject(
                "SELECT count(*) FROM audit_events WHERE action='OBSERVATION_CORRECTED' AND entity_id=?",
                Integer.class,
                correction.id()))
        .isEqualTo(1);
    assertThatThrownBy(
            () ->
                jdbc.update(
                    "UPDATE platform_content_state_observations SET notes='silent edit' WHERE id=?",
                    original.id()))
        .isInstanceOf(DataAccessException.class)
        .hasMessageContaining("append-only");
  }

  @Test
  void screenshotEvidenceIsStoredButOcrDoesNotImplyVerification() throws Exception {
    Instant observed = Instant.parse("2026-09-28T23:32:00Z");
    var result =
        platformStates.observeScreenshot(
            videoId,
            "facebook",
            "ACTIVE",
            observed,
            "Reach Further visible in Meta dashboard",
            "Reach Further",
            false,
            "evidence.png",
            "image/png",
            new ByteArrayInputStream(new byte[] {1, 2, 3}),
            "test-user");

    assertThat(result.source()).isEqualTo("SCREENSHOT");
    assertThat(result.manuallyVerified()).isFalse();
    assertThat(result.confidence()).isEqualTo(0.6);
    Path evidence =
        Path.of(System.getProperty("java.io.tmpdir"), "pompom-creative-intelligence-tests")
            .resolve(result.evidenceRelativePath());
    assertThat(Files.exists(evidence)).isTrue();
  }

  @Test
  void csvCreatesStateOnlyFromAnExplicitReachFurtherField() {
    String csv =
        "video_id,views,reach_further,reach_further_observed_at\n"
            + videoId
            + ",17929,ACTIVE,2026-09-28T23:32:00Z\n";
    var upload =
        new MockMultipartFile(
            "file", "explicit-state.csv", "text/csv", csv.getBytes(StandardCharsets.UTF_8));
    var preview = imports.preview(upload, "facebook", "Europe/London");
    imports.commit(preview.batchId());

    var observations = platformStates.observations(videoId, "facebook");
    assertThat(observations).hasSize(1);
    assertThat(observations.getFirst().source()).isEqualTo("CSV");
    assertThat(observations.getFirst().observedAt())
        .isEqualTo(Instant.parse("2026-09-28T23:32:00Z"));
    assertThat(observations.getFirst().manuallyVerified()).isFalse();
  }

  @Test
  void platformGrowthProfilesSeparateInstagramBurstFromFacebookTail() {
    Instant published = Instant.parse("2026-09-20T07:00:00Z");
    insertPerformance("instagram", published, published.plusSeconds(6 * 3600), 600L, 500L);
    insertPerformance("instagram", published, published.plusSeconds(24 * 3600), 1000L, 800L);
    insertPerformance("facebook", published, published.plusSeconds(24 * 3600), 1000L, 800L);
    insertPerformance("facebook", published, published.plusSeconds(48 * 3600), 1400L, 1100L);
    insertPerformance("facebook", published, published.plusSeconds(7 * 24 * 3600), 2200L, 1800L);

    var instagram =
        growthProfiles.profile(videoId, "instagram", published.plusSeconds(8 * 24 * 3600), null);
    var facebook =
        growthProfiles.profile(videoId, "facebook", published.plusSeconds(8 * 24 * 3600), null);

    assertThat(instagram.instagramBurstRatio()).isEqualTo(0.6);
    assertThat(instagram.primarySignal()).isEqualTo("EARLY_BURST");
    assertThat(facebook.viewsAfter24h()).isEqualTo(1200);
    assertThat(facebook.facebookTailRatio()).isEqualTo(1.2);
    assertThat(facebook.primarySignal()).isEqualTo("LONG_TAIL");
  }

  @Test
  void manualEngagementInterventionIsAppendOnlyAuditedAndCutoffSafe() {
    Instant interventionAt = Instant.parse("2026-09-29T01:30:00Z");
    var event =
        interventions.record(
            videoId,
            new InterventionService.InterventionRequest(
                "facebook", interventionAt, "Personal accounts joined after stall", 329L, 376L),
            "test-user");

    assertThat(interventions.list(videoId, "facebook")).containsExactly(event);
    assertThat(
            jdbc.queryForObject(
                "SELECT count(*) FROM audit_events WHERE entity_id=? AND action='MANUAL_ENGAGEMENT_INTERVENTION_RECORDED'",
                Integer.class,
                event.id()))
        .isEqualTo(1);
    assertThatThrownBy(
            () ->
                jdbc.update(
                    "UPDATE intervention_events SET event_time=now() WHERE id=?", event.id()))
        .isInstanceOf(DataAccessException.class)
        .hasMessageContaining("append-only");

    var before =
        platformStates.liveFeatures(videoId, "facebook", interventionAt.minusSeconds(1), "LIVE");
    var after =
        platformStates.liveFeatures(videoId, "facebook", interventionAt.plusSeconds(1), "LIVE");
    assertThat(before.features()).containsEntry("manualEngagementIntervention", false);
    assertThat(after.features()).containsEntry("manualEngagementIntervention", true);
  }

  @Test
  void canonicalCharactersExistWithoutInventedCoverage() {
    var coverage = characters.coverage();

    assertThat(coverage)
        .extracting(CharacterService.CharacterCoverageView::name)
        .containsExactlyInAnyOrder("Opa", "Kiko", "Mimi", "Arda", "Luca", "Noah");
    assertThat(coverage)
        .allSatisfy(
            item -> {
              assertThat(item.observations()).isZero();
              assertThat(item.formatObservations()).isEmpty();
              assertThat(item.confidence()).isEqualTo("NO_DATA");
            });
  }

  private PlatformStateService.ObservationView addReachFurther(
      String value, Instant observedAt, UUID correction) {
    return platformStates.observe(
        videoId,
        new PlatformStateService.ObservationRequest(
            null,
            "facebook",
            PlatformStateService.REACH_FURTHER,
            value,
            observedAt,
            observedAt == null ? "API" : "MANUAL",
            null,
            observedAt == null ? 0.5 : 1.0,
            "Observed in Meta UI",
            null,
            null,
            observedAt != null,
            correction),
        "test-user");
  }

  private void insertPerformance(Instant published, Instant measured, Long views, Long reach) {
    insertPerformance("facebook", published, measured, views, reach);
  }

  private void insertPerformance(
      String platform, Instant published, Instant measured, Long views, Long reach) {
    UUID batchId = UUID.randomUUID();
    UUID rowId = UUID.randomUUID();
    jdbc.update(
        """
        INSERT INTO import_batches
          (id,source_filename,source_hash,platform,parser_version,timezone_assumption,column_mapping,quality_report,status)
        VALUES (?, ?, ?, ?, 'test', 'UTC', '{}'::jsonb, '{}'::jsonb, 'COMMITTED')
        """,
        batchId,
        batchId + ".csv",
        batchId.toString().replace("-", "").repeat(2),
        platform);
    jdbc.update(
        """
        INSERT INTO import_rows(id,import_batch_id,sheet_name,source_row_number,raw_data,matched_video_id,match_status,match_confidence)
        VALUES (?,?,'Sheet1',1,'{}'::jsonb,?,'EXACT',1.0)
        """,
        rowId,
        batchId,
        videoId);
    jdbc.update(
        """
        INSERT INTO performance_observations
          (import_row_id,video_id,platform,publication_timestamp,measurement_timestamp,
           metric_semantics,views,reach,paid)
        VALUES (?,?,?, ?,?,'CUMULATIVE',?,?,false)
        """,
        rowId,
        videoId,
        platform,
        OffsetDateTime.ofInstant(published, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(measured, ZoneOffset.UTC),
        views,
        reach);
  }
}
