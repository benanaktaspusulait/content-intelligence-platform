package com.pompomhills.intelligence;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.workflow.CreativePromptQualityController;
import com.pompomhills.intelligence.workflow.WorkflowService;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;

/** Contract fixtures only: these principals/judgments never exist in production. */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
@Import(PlatformIntegrationTest.WorkflowMlMockConfiguration.class)
class OriginalCpqFidelityIntegrationTest {
  @Container static final PostgreSQLContainer<?> DB = new PostgreSQLContainer<>("postgres:17-alpine");
  static final Path LIBRARY = tempDirectory();
  @DynamicPropertySource static void config(DynamicPropertyRegistry r) {
    r.add("spring.datasource.url", DB::getJdbcUrl); r.add("spring.datasource.username", DB::getUsername);
    r.add("spring.datasource.password", DB::getPassword); r.add("pompom.library-root", LIBRARY::toString);
  }
  @Autowired CreativePromptQualityController api;
  @Autowired com.pompomhills.intelligence.workflow.CpqOwnerPilotService ownerPilot;
  @Autowired com.pompomhills.intelligence.workflow.CpqDraftReviewService draftReview;
  @Autowired WorkflowService workflow;
  @Autowired JdbcTemplate jdbc;
  @Autowired ObjectMapper json;
  @Autowired QualityMlClient ml;
  static final String STORY = "Mimi the bunny pulls a sticky note from her finger twice; each pull doubles two to four to eight within fifteen seconds; she sneezes and the notes land on the cabinet.";
  static final String PROMPT = "15 seconds, 9:16. Mimi the bunny stands beside the cabinet. A note clings to her finger. First pull: two notes become four. Second pull: four become eight. Keep the contact plane visible. She sneezes; all notes land on the cabinet. Locked camera.";
  static final List<String> DIMS = List.of("SCROLL_STOP_VISUAL_PROMISE","CAUSAL_PROGRESSION","VISUAL_STORYTELLING","PRODUCTION_EXECUTABILITY","ENDING_REPLAY","DISTINCTIVE_CREATIVE_VALUE");
  static final List<String> ANCHORS = List.of("CHARACTER_IDENTITY","APPROVED_EVENTS","EVENT_ORDER","PHYSICAL_RULE","TEMPORAL_CONSTRAINTS","REQUIRED_ENDING");
  UUID storyId, approvalId;
  Map<String,Object> request;
  MockHttpServletRequest manager = actor("fixture-source-manager","CREATIVE_QUALITY_ARCHITECTURE_APPROVER");
  MockHttpServletRequest evidenceReviewer = actor("fixture-source-reviewer","EVIDENCE_REVIEWER");

  @BeforeEach void setup() throws Exception {
    jdbc.execute("TRUNCATE cpq_owner_pilots,cpq_original_subjects,cpq_calibration_corpora,contents,post_family_workflow_events CASCADE");
    reset(ml);
    storyId=event("CREATIVE_ROLE",Map.of("role","STORY","sourceRequest",Map.of("text",STORY)));
    approvalId=approve(storyId,STORY);
    request=repositoryRequest("original.txt",PROMPT,storyId,approvalId);
  }
  static Path tempDirectory() { try { return Files.createTempDirectory("cpq-original-isolated-"); } catch(Exception e) { throw new RuntimeException(e); } }
  static MockHttpServletRequest actor(String name,String role) {
    var r=new MockHttpServletRequest(); r.setUserPrincipal(()->name); r.addUserRole(role); return r;
  }
  static String sha(String v) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(v.getBytes(java.nio.charset.StandardCharsets.UTF_8))); }
  static String storyRevisionHash(String v) { int h=0x811c9dc5; for(char c:v.toCharArray()) {h^=c;h*=0x01000193;} return String.format(Locale.ROOT,"%08x",h); }
  UUID event(String kind,Map<String,Object> payload) throws Exception {
    UUID id=UUID.randomUUID(); jdbc.update("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES(?,?,CAST(? AS jsonb))",id,kind,json.writeValueAsString(payload)); return id;
  }
  UUID approve(UUID id,String text) {
    var approval=workflow.approveStory(id,Map.of("candidateId","ORIGINAL_SOURCE","approvedText",text,"contentFingerprint",storyRevisionHash(text),"revisionId","ORIGINAL_SOURCE-revision-"+storyRevisionHash(text)));
    return UUID.fromString(String.valueOf(approval.get("recordId")));
  }
  Map<String,Object> settings() { return Map.of("contentProfile","ABSURD_PHYSICS","generator","SEEDANCE_2_0_MINI","desiredDuration",15,"settings",Map.of("aspectRatio","9:16","mode","image2video","resolution","480p")); }
  Map<String,Object> repositoryRequest(String path,String text,UUID story,UUID approval) throws Exception {
    Files.writeString(LIBRARY.resolve(path),text);
    String settingsPath=path+".settings.json";
    String settingsDoc=json.writeValueAsString(Map.of("sourceIdentity","repository:"+path,"sourcePromptSha256",sha(text),"productionSettings",settings()));
    Files.writeString(LIBRARY.resolve(settingsPath),settingsDoc);
    return new LinkedHashMap<>(Map.of("repositoryRelativePath",path,"expectedPromptSha256",sha(text),"storyId",story.toString(),"approvalRecordId",approval.toString(),
        "productionSettingsSourcePath",settingsPath,"expectedSettingsSha256",sha(settingsDoc),"rationale","Fixture source binding, never a real story approval or human judgment."));
  }
  UUID bind(Map<String,Object> body) { return UUID.fromString(String.valueOf(api.bindOriginal(body,manager).get("subjectId"))); }
  Map<String,Object> review(String decision,String prompt) {
    return new LinkedHashMap<>(Map.of("decision",decision,"rationale","Isolated authorization and persistence fixture; no actual creative judgment.","validUntil",Instant.now().plusSeconds(3600).toString(),
      "citations",List.of(Map.of("side","APPROVED_STORY","quote",STORY),Map.of("side","ORIGINAL_PROMPT","quote",prompt)),
      "sourceEventMapping",ANCHORS.stream().map(a->Map.of("anchor",a,"sourceQuote",STORY,"promptQuote",prompt)).toList()));
  }
  UUID fidelity(UUID subject,String decision) { return UUID.fromString(String.valueOf(api.originalFidelityReview(subject,review(decision,PROMPT),evidenceReviewer).get("evidenceId"))); }
  String corpus() {String version="fixture-"+UUID.randomUUID(); api.createCorpus(version,Map.of(),manager); return version;}
  Map<String,Object> example(UUID evidence) {
    var b=new LinkedHashMap<String,Object>(settings()); b.put("durationSeconds",15); b.put("sourceFidelityEvidenceId",evidence.toString());
    b.put("promptText",PROMPT);b.put("approvedStoryText",STORY);b.put("sourceStoryId",storyId.toString());b.put("sourceRevision","ORIGINAL_SOURCE-revision-"+storyRevisionHash(STORY));
    b.put("promptVersionLabel","fixture-original");b.put("split","CALIBRATION");b.put("caseType","GENERAL_PROMPT");b.put("subjectType","ORIGINAL_PROMPT");b.put("leakageGroup","fixture-sticky-mechanic");
    b.put("provenance",Map.of("provider","HIDDEN_PROVIDER","canonicalGrade","HIDDEN_GRADE","views",99999,"corpusRole","HIDDEN_LABEL"));return b;
  }
  Map<String,Object> judgment(String level) {
    var dimensions=new LinkedHashMap<String,Object>();
    for(String d:DIMS) dimensions.put(d,Map.of("level",level,"rationale","This is an isolated workflow fixture, not real human quality evidence.",
      "strengthOrWeakness","The contact plane is explicitly staged in the fixture text.","productionConstraint","Only fifteen seconds are available for the two sequential pulls.",
      "uncertainty","Rendered adherence and actual audience response remain unverified.","evidenceCitations",List.of(Map.of("quote","Keep the contact plane visible."))));
    return Map.of("dimensions",dimensions,"sourceFidelityDecision","PASS","overallQualityAnchor","UNKNOWN");
  }

  @Test void fullOriginalToBlindReviewAndPreviewRemainsInactive() throws Exception {
    int events=jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events",Integer.class);
    assertThat(api.originalPreflight(request,manager)).containsEntry("status","READY_FOR_SOURCE_BINDING").containsEntry("persisted",false);
    UUID subject=bind(request), evidence=fidelity(subject,"PASS"); String corpus=corpus();
    var imported=api.addExample(corpus,example(evidence),manager); UUID example=UUID.fromString(String.valueOf(imported.get("exampleId")));
    var reviewer1=actor("fixture-blind-1","CREATIVE_QUALITY_REVIEWER");var reviewer2=actor("fixture-blind-2","CREATIVE_QUALITY_REVIEWER");
    var packet=api.reviewPacket(example,reviewer1);
    assertThat(packet).containsEntry("promptText",PROMPT).containsEntry("blind",true).containsEntry("existingJudgmentsVisible",false);
    assertThat(packet.keySet()).containsExactlyInAnyOrder("promptText","contentProfile","generator","durationSeconds","productionSettings","exampleId","blind","existingJudgmentsVisible","rubricVersion","reviewMethodVersion");
    assertThat(json.writeValueAsString(packet)).doesNotContain("HIDDEN_","views","corpusVersion","ORIGINAL_PROMPT");
    api.judgment(example,judgment("STRONG"),reviewer1);api.judgment(example,judgment("WEAK"),reviewer2);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_calibration_judgments WHERE example_id=? AND jsonb_array_length(evidence_citations)>0 AND review_method_version='cpq-human-blind-review-v2'",Integer.class,example)).isEqualTo(2);
    var ready=api.readiness(corpus);
    assertThat(ready).containsEntry("judgmentCount",2).containsEntry("examplesWithAtLeastTwoReviewers",1).containsEntry("currentFidelityPassCount",1).containsEntry("activationEligible",false).containsEntry("aggregateGradeThresholdsJustified",false);
    assertThat(((Number)ready.get("pairwiseDimensionAgreementFraction")).doubleValue()).isZero();
    when(ml.workflow(eq("creative-prompt-quality/calibration-preview"),anyMap())).thenReturn(Map.of("gradingStatus","CALIBRATION_INCOMPLETE","corpusFingerprint","fixture-only","activated",false));
    assertThat(api.calibrationPreview(corpus,manager)).containsEntry("activated",false).containsEntry("reportingStatus","PROVISIONAL_ONLY");
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
    assertThat(jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events",Integer.class)).isEqualTo(events);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events WHERE kind='CREATIVE_OPTIMIZATION'",Integer.class)).isZero();
  }

  @Test void repositoryWithoutApprovalOrSettingsReturnsAllBlockers() {
    var missing=new LinkedHashMap<>(request);missing.remove("storyId");missing.remove("approvalRecordId");missing.remove("productionSettingsSourcePath");missing.remove("expectedSettingsSha256");
    var preflight=api.originalPreflight(missing,manager);
    assertThat((List<String>)preflight.get("blockers")).contains("SOURCE_APPROVAL_REQUIRED","PRODUCTION_SETTINGS_BINDING_REQUIRED");
    assertThatThrownBy(()->api.bindOriginal(missing,manager)).hasMessageContaining("SOURCE_APPROVAL_REQUIRED");
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_original_subjects",Integer.class)).isZero();
  }
  @Test void savedBaselineUsesItsOwnApprovalAndSettingsWithoutAnOptimizationCandidate() throws Exception {
    jdbc.update("INSERT INTO contents(id,title,type) VALUES(8101,'Isolated original','SHORT')");
    jdbc.update("INSERT INTO prompt_versions(id,content_id,version_number,raw_text) VALUES(8101,8101,1,?)",PROMPT);
    event("CREATIVE_STUDIO_SESSION",Map.of("contentId",8101,"promptVersionId",8101,"storyRecordId",storyId.toString(),"approvalRecordId",approvalId.toString()));
    var config=new LinkedHashMap<>(settings());config.put("contentId",8101);config.put("promptVersionId",8101);config.put("promptHash",sha(PROMPT));event("PRODUCTION_SETTINGS",config);
    var saved=Map.<String,Object>of("contentId",8101,"promptVersionId",8101,"expectedPromptSha256",sha(PROMPT),"rationale","Bind the independently approved story to this exact isolated saved original.");
    UUID subject=bind(saved), evidence=fidelity(subject,"PASS");
    var body=example(evidence);body.put("promptVersionId",8101);
    assertThat(api.addExample(corpus(),body,manager)).containsEntry("humanQualityGrade","NOT_YET_REVIEWED");
    assertThat(jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events WHERE kind='CREATIVE_OPTIMIZATION'",Integer.class)).isZero();
  }
  @Test void aDifferentStoryApprovalCannotBeReused() throws Exception {
    UUID other=event("CREATIVE_ROLE",Map.of("role","STORY","sourceRequest",Map.of("text","Another story.")));
    var wrong=new LinkedHashMap<>(request);wrong.put("storyId",other.toString());
    assertThat((List<String>)api.originalPreflight(wrong,manager).get("blockers")).contains("SOURCE_APPROVAL_REQUIRED");
  }
  @Test void providerOrQualityMetadataCannotLeakThroughProductionSettings() throws Exception {
    var config=new LinkedHashMap<>(settings());config.put("settings",Map.of("aspectRatio","9:16","provider","HIDDEN_PROVIDER","canonicalGrade","A+"));
    String doc=json.writeValueAsString(Map.of("sourceIdentity","repository:original.txt","sourcePromptSha256",sha(PROMPT),"productionSettings",config));
    Files.writeString(LIBRARY.resolve("original.txt.settings.json"),doc);request.put("expectedSettingsSha256",sha(doc));
    assertThat((List<String>)api.originalPreflight(request,manager).get("blockers")).contains("PRODUCTION_SETTINGS_BINDING_REQUIRED");
  }
  @Test void wrongFingerprintAndUnsafeRepositoryPathAreRejected() {
    var wrong=new LinkedHashMap<>(request);wrong.put("expectedPromptSha256","0".repeat(64));
    assertThatThrownBy(()->api.originalPreflight(wrong,manager)).hasMessageContaining("SOURCE_PROMPT_FINGERPRINT_MISMATCH");
    wrong.put("repositoryRelativePath","../escape.txt");assertThatThrownBy(()->api.originalPreflight(wrong,manager)).hasMessageContaining("SOURCE_PROVENANCE_REQUIRED");
  }
  @Test void sourceCannotServeAsItsOwnSoleStoryEvidence() throws Exception {
    var self=repositoryRequest("self.txt",STORY,storyId,approvalId);
    assertThat((List<String>)api.originalPreflight(self,manager).get("blockers")).contains("INDEPENDENT_SOURCE_REQUIRED");
    assertThatThrownBy(()->bind(self)).hasMessageContaining("INDEPENDENT_SOURCE_REQUIRED");
  }
  @Test void authenticationAndReviewerIndependenceCannotBeForgedInJson() {
    var anonymous=new MockHttpServletRequest(); var forged=new LinkedHashMap<>(request);forged.put("reviewerRole","CREATIVE_QUALITY_ARCHITECTURE_APPROVER");forged.put("reviewerPrincipal","fixture-source-manager");
    assertThatThrownBy(()->api.bindOriginal(forged,anonymous)).hasMessageContaining("Authenticated");
    UUID subject=bind(request);
    assertThatThrownBy(()->api.originalFidelityReview(subject,review("PASS",PROMPT),anonymous)).hasMessageContaining("EVIDENCE_REVIEWER");
    var same=actor("fixture-source-manager","EVIDENCE_REVIEWER");
    assertThatThrownBy(()->api.originalFidelityReview(subject,review("PASS",PROMPT),same)).hasMessageContaining("Independent reviewer");
    assertThatThrownBy(()->api.originalReviewPacket(subject,manager)).hasMessageContaining("EVIDENCE_REVIEWER");
  }
  @Test void passNeedsAllExactAnchorsAndConcreteRationaleAndExpiry() {
    UUID subject=bind(request);var incomplete=review("PASS",PROMPT);incomplete.put("sourceEventMapping",List.of());
    assertThatThrownBy(()->api.originalFidelityReview(subject,incomplete,evidenceReviewer)).hasMessageContaining("every protected story anchor");
    var wrong=review("PASS",PROMPT);wrong.put("citations",List.of(Map.of("side","APPROVED_STORY","quote","invented span")));
    assertThatThrownBy(()->api.originalFidelityReview(subject,wrong,evidenceReviewer)).hasMessageContaining("Citation");
    var empty=review("UNKNOWN",PROMPT);empty.put("rationale","");assertThatThrownBy(()->api.originalFidelityReview(subject,empty,evidenceReviewer)).hasMessageContaining("rationale");
    var expired=review("PASS",PROMPT);expired.put("validUntil",Instant.now().minusSeconds(1).toString());assertThatThrownBy(()->api.originalFidelityReview(subject,expired,evidenceReviewer)).hasMessageContaining("expiry");
  }
  @Test void unknownFailAndMissingEvidenceCannotQualifyCalibrationImport() {
    UUID subject=bind(request);String corpus=corpus();
    for(String decision:List.of("UNKNOWN","FAIL")) {UUID evidence=fidelity(subject,decision);assertThatThrownBy(()->api.addExample(corpus,example(evidence),manager)).hasMessageContaining("FAIL/UNKNOWN");}
    var body=example(UUID.randomUUID());assertThatThrownBy(()->api.addExample(corpus,body,manager)).hasMessageContaining("Current unexpired");
  }
  @Test void exactPromptStoryVersionAndProductionScopeAreEnforced() {
    UUID evidence=fidelity(bind(request),"PASS");String corpus=corpus();
    for(var change:List.of(Map.entry("promptText",PROMPT+" changed"),Map.entry("approvedStoryText",STORY+" changed"),Map.entry("sourceStoryId",UUID.randomUUID().toString()),Map.entry("sourceRevision","stale"),Map.entry("generator","OTHER"),Map.entry("subjectType","OPTIMIZATION_CANDIDATE"))) {
      var body=example(evidence);body.put(change.getKey(),change.getValue());assertThatThrownBy(()->api.addExample(corpus,body,manager)).isInstanceOf(org.springframework.web.server.ResponseStatusException.class);
    }
    var badVersion=example(evidence);badVersion.put("promptVersionId",99999L);assertThatThrownBy(()->api.addExample(corpus,badVersion,manager)).hasMessageContaining("Prompt version");
    var bad=example(evidence);bad.put("originalSubjectId",UUID.randomUUID().toString());
    assertThatThrownBy(()->api.addExample(corpus,bad,manager)).hasMessageContaining("subject identity");
  }
  @Test void candidateLedgerEvidenceCannotBePresentedAsOriginalEvidence() throws Exception {
    UUID original=fidelity(bind(request),"PASS");
    jdbc.update("INSERT INTO contents(id,title,type) VALUES(8101,'Isolated scope rejection','SHORT')");
    jdbc.update("INSERT INTO prompt_versions(id,content_id,version_number,raw_text) VALUES(8101,8101,1,?)",PROMPT);
    UUID analysis=event("REVIEW",Map.of("fixtureOnly",true)), candidateEvidence=UUID.randomUUID();
    jdbc.update("INSERT INTO cpq_fidelity_reviews SELECT (jsonb_populate_record(NULL::cpq_fidelity_reviews,to_jsonb(f)||jsonb_build_object('evidence_id',?::text,'subject_type','OPTIMIZATION_CANDIDATE','original_subject_id',NULL,'review_contract_version','candidate-fidelity-v1','content_id',8101,'prompt_version_id',8101,'analysis_id',?::text))).* FROM cpq_fidelity_reviews f WHERE evidence_id=?",candidateEvidence.toString(),analysis.toString(),original);
    assertThatThrownBy(()->api.addExample(corpus(),example(candidateEvidence),manager)).hasMessageContaining("subject type cannot be reused");
  }
  @Test void approvalAndSettingsChangesRequireNewBinding() throws Exception {
    UUID subject=bind(request);String corpus=corpus();UUID evidence=fidelity(subject,"PASS");
    Files.writeString(LIBRARY.resolve("original.txt.settings.json"),"{}");
    assertThatThrownBy(()->api.addExample(corpus,example(evidence),manager)).hasMessageContaining("ORIGINAL_BINDING_STALE");
    request=repositoryRequest("original.txt",PROMPT,storyId,approvalId);
    approve(storyId,STORY);
    assertThatThrownBy(()->api.originalReviewPacket(subject,evidenceReviewer)).hasMessageContaining("ORIGINAL_BINDING_STALE");
  }
  @Test void changedPromptBytesAndFrozenCorporaCannotBeReused() throws Exception {
    UUID subject=bind(request),evidence=fidelity(subject,"PASS");String corpus=corpus();
    jdbc.update("UPDATE cpq_calibration_corpora SET state='CALIBRATED' WHERE corpus_version=?",corpus);
    assertThatThrownBy(()->api.addExample(corpus,example(evidence),manager)).hasMessageContaining("not open");
    Files.writeString(LIBRARY.resolve("original.txt"),PROMPT+" changed");
    assertThatThrownBy(()->api.originalReviewPacket(subject,evidenceReviewer)).hasMessageContaining("SOURCE_PROMPT_FINGERPRINT_MISMATCH");
  }
  @Test void duplicateAndRelatedSplitLeakageAreRejected() throws Exception {
    UUID evidence=fidelity(bind(request),"PASS");String corpus=corpus();api.addExample(corpus,example(evidence),manager);
    assertThatThrownBy(()->api.addExample(corpus,example(evidence),manager)).hasMessageContaining("Duplicate prompt");
    String variant=PROMPT+" Keep the full cabinet visible.";UUID other=bind(repositoryRequest("variant.txt",variant,storyId,approvalId));
    UUID otherEvidence=UUID.fromString(String.valueOf(api.originalFidelityReview(other,review("PASS",variant),evidenceReviewer).get("evidenceId")));
    var b=example(otherEvidence);b.put("promptText",variant);b.put("split","HELD_OUT");b.put("leakageGroup","different-label-cannot-bypass-story-group");
    assertThatThrownBy(()->api.addExample(corpus,b,manager)).hasMessageContaining("leakage");
  }
  @Test void originalEvidenceIsAppendOnlyAndSupersessionIsScoped() throws Exception {
    UUID subject=bind(request),first=fidelity(subject,"UNKNOWN");
    var pass=review("PASS",PROMPT);pass.put("supersedesEvidenceId",first.toString());
    UUID second=UUID.fromString(String.valueOf(api.originalFidelityReview(subject,pass,evidenceReviewer).get("evidenceId")));
    String corpus=corpus();assertThatThrownBy(()->api.addExample(corpus,example(first),manager)).hasMessageContaining("Current unexpired");
    api.addExample(corpus,example(second),manager);
    UUID other=bind(repositoryRequest("other.txt",PROMPT+" Another composition.",storyId,approvalId));
    var otherReview=review("PASS",PROMPT+" Another composition.");otherReview.put("supersedesEvidenceId",first.toString());
    assertThatThrownBy(()->api.originalFidelityReview(other,otherReview,evidenceReviewer)).hasMessageContaining("same immutable original subject");
    assertThatThrownBy(()->jdbc.update("UPDATE cpq_fidelity_reviews SET decision='PASS' WHERE evidence_id=?",first)).hasMessageContaining("immutable");
    assertThatThrownBy(()->jdbc.update("DELETE FROM cpq_original_subjects WHERE subject_id=?",subject)).hasMessageContaining("immutable");
  }
  @Test void conflictExpiredEvidenceAndDuplicateReviewerRemainBlocked() throws Exception {
    UUID subject=bind(request),pass=fidelity(subject,"PASS");String corpus=corpus();
    UUID fail=fidelity(subject,"FAIL");assertThatThrownBy(()->api.addExample(corpus,example(pass),manager)).hasMessageContaining("Conflicting");
    var resolve=review("PASS",PROMPT);resolve.put("supersedesEvidenceId",fail.toString());UUID current=UUID.fromString(String.valueOf(api.originalFidelityReview(subject,resolve,evidenceReviewer).get("evidenceId")));
    UUID id=UUID.fromString(String.valueOf(api.addExample(corpus,example(current),manager).get("exampleId")));
    var r=actor("fixture-quality-1","CREATIVE_QUALITY_REVIEWER");api.judgment(id,judgment("STRONG"),r);
    assertThatThrownBy(()->api.judgment(id,judgment("WEAK"),r)).hasMessageContaining("already submitted");
    var self=actor("fixture-source-reviewer","CREATIVE_QUALITY_REVIEWER");assertThatThrownBy(()->api.judgment(id,judgment("STRONG"),self)).hasMessageContaining("sole independent");
    UUID expired=UUID.randomUUID();
    jdbc.update("INSERT INTO cpq_fidelity_reviews SELECT (jsonb_populate_record(NULL::cpq_fidelity_reviews,to_jsonb(f)||jsonb_build_object('evidence_id',?::text,'valid_until',now()-interval '1 second','supersedes_evidence_id',NULL))).* FROM cpq_fidelity_reviews f WHERE evidence_id=?",expired.toString(),current);
    assertThatThrownBy(()->api.addExample(corpus,example(expired),manager)).hasMessageContaining("Current unexpired");
  }
  @Test void realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence() throws Exception {
    // Only this disposable Testcontainers DB receives fixture identities/reviews. Never real human evidence.
    Path projection=Path.of("../docs/cpq-v1-mimi-pilot-2026-10-15/supervisor-only/persisted-cpq-test-projection.json");
    if(!Files.exists(projection)) projection=Path.of("intelligence/docs/cpq-v1-mimi-pilot-2026-10-15/supervisor-only/persisted-cpq-test-projection.json");
    var data=json.readValue(Files.readString(projection),Map.class);
    jdbc.execute("TRUNCATE cpq_owner_pilots,cpq_original_subjects,cpq_calibration_corpora,contents,post_family_workflow_events CASCADE");
    String original=(String)data.get("originalPrompt");
    assertThat(sha(original)).isEqualTo("0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98");
    jdbc.update("INSERT INTO contents(id,title,type) VALUES(10,'Isolated saved Mimi pilot','SHORT')");
    jdbc.update("INSERT INTO prompt_versions(id,content_id,version_number,raw_text) VALUES(10,10,1,?)",original);
    for(var raw:(List<Map<String,Object>>)data.get("events"))
      jdbc.update("INSERT INTO post_family_workflow_events(id,kind,payload,created_at) VALUES(?,?,CAST(? AS jsonb),CAST(? AS timestamptz))",UUID.fromString((String)raw.get("id")),raw.get("kind"),json.writeValueAsString(raw.get("payload")),raw.get("createdAt"));
    UUID analysis=UUID.fromString("f0d36feb-ee0f-4da8-ae21-2071a3ddea18");
    UUID source=UUID.fromString("bc1cf798-d20b-4b98-8b73-56e1581c3afc"), approval=UUID.fromString("20b77d13-848d-46d0-ab4b-bb9b6efb0836");
    String approved=(String)workflow.approvedStoryForCpq(source,approval).get("text");
    assertThat(sha(approved)).isEqualTo("df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b");
    String historyDigest=jdbc.queryForObject("SELECT encode(digest(string_agg(id::text||kind||payload::text,'' ORDER BY id),'sha256'),'hex') FROM post_family_workflow_events",String.class);
    var selectors=Map.<String,Object>of("contentId",10,"promptVersionId",10,"expectedPromptSha256",sha(original),"rationale","Disposable saved-input pilot binding; never a production or human approval.");
    var preflight=api.originalPreflight(selectors,manager);
    assertThat(preflight).containsEntry("status","READY_FOR_SOURCE_BINDING");
    assertThat((Map<String,Object>)preflight.get("productionSettings")).containsEntry("contentProfile","ABSURD_PHYSICS").containsEntry("generator","SEEDANCE_2_0_MINI");
    UUID originalSubject=bind(selectors);
    api.originalFidelityReview(originalSubject,Map.of("decision","UNKNOWN","rationale","Real-input disposable contract check; semantic assessment remains unknown.","validUntil",Instant.now().plusSeconds(3600).toString(),"citations",List.of(Map.of("side","APPROVED_STORY","quote",approved)),"sourceEventMapping",List.of()),evidenceReviewer);
    var comparisonIds=List.of("e651eb75-b894-477d-ae77-0fe6e05236da","9275c94b-fc35-4207-8648-dfd8d166e502","9275c94b-fc35-4207-8648-dfd8d166e502");
    var candidateIds=List.of("candidate-a","candidate-a","candidate-b");
    var expectedHashes=List.of("90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495","218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749","2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746");
    for(int n=0;n<3;n++) {
      UUID comparison=UUID.fromString(comparisonIds.get(n));String candidateId=candidateIds.get(n);
      assertThat((List<Map<String,Object>>)api.comparisonBinding(analysis,comparison).get("candidateBindings")).allSatisfy(b->assertThat(b).containsEntry("status","COMPATIBLE"));
      var event=(Map<String,Object>)((List<Map<String,Object>>)data.get("events")).stream().filter(e->comparison.toString().equals(e.get("id"))).findFirst().orElseThrow().get("payload");
      var candidate=((List<Map<String,Object>>)event.get("candidates")).stream().filter(c->candidateId.equals(c.get("candidateId"))).findFirst().orElseThrow();
      String prompt=(String)candidate.get("prompt");assertThat(sha(prompt)).isEqualTo(expectedHashes.get(n));
      var review=Map.<String,Object>of("decision","UNKNOWN","rationale","Disposable real-input diagnostic only, never a human source-fidelity decision.","validUntil",Instant.now().plusSeconds(3600).toString(),"citations",List.of(Map.of("side","APPROVED_STORY","quote",approved),Map.of("side","CANDIDATE_PROMPT","quote",prompt)),"sourceEventMapping",List.of());
      assertThat(api.fidelityReview(analysis,comparison,candidateId,review,evidenceReviewer)).containsEntry("decision","UNKNOWN");
      assertThat(api.originalReviewPacket(originalSubject,evidenceReviewer).get("approvedStory")).isInstanceOf(Map.class);
      assertThat(((Number)((Map<String,Object>)((Map<String,Object>)candidate.get("review")).get("canonicalRuleEvaluation")).get("score")).doubleValue()).isCloseTo(88.40625,within(0.000001));
    }
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_fidelity_reviews WHERE decision='UNKNOWN'",Integer.class)).isEqualTo(4);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_original_subjects",Integer.class)).isEqualTo(1);
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
    assertThat(jdbc.queryForObject("SELECT encode(digest(string_agg(id::text||kind||payload::text,'' ORDER BY id),'sha256'),'hex') FROM post_family_workflow_events",String.class)).isEqualTo(historyDigest);
    assertThat(jdbc.queryForObject("SELECT raw_text FROM prompt_versions WHERE id=10",String.class)).isEqualTo(original);
    verifyNoInteractions(ml);
  }
  Map<String,Object> legacyOwnerPilot(Map<String,Object> create,MockHttpServletRequest owner) throws Exception {
    // TEST_FIXTURE simulates an immutable pre-V66 pilot; production create always uses SINGLE_SUBJECT_V1.
    var legacy=new LinkedHashMap<String,Object>(create);legacy.put("subjects",List.of());
    Map<String,Object> snapshot=org.springframework.test.util.ReflectionTestUtils.invokeMethod(ownerPilot,"snapshot",legacy);
    String encoded=org.springframework.test.util.ReflectionTestUtils.invokeMethod(ownerPilot,"encode",snapshot);
    UUID id=UUID.randomUUID();jdbc.update("INSERT INTO cpq_owner_pilots(pilot_id,owner_principal,policy_version,scope_sha256,snapshot,total_budget_usd) VALUES(?,?, 'OWNER_MACHINE_PILOT_V1',?,CAST(? AS jsonb),?)",id,owner.getUserPrincipal().getName(),sha(encoded),encoded,create.get("maxTotalUsd"));
    return ownerPilot.view(id,owner);
  }
  @Test void ownerMachinePilotUsesRealMimiInputsWithThreeDistinctMockedExecutions() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();
    var catalog=Path.of("../data");if(!Files.exists(catalog.resolve("workflow/cpq-pilot-blind-manifests-v1.json")))catalog=Path.of("intelligence/data");
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"dataRoot",catalog.toAbsolutePath().toString());
    var owner=actor("fixture-owner","OWNER");
    var selectors=List.of(Map.of("comparisonId","e651eb75-b894-477d-ae77-0fe6e05236da","candidateId","candidate-a"),Map.of("comparisonId","9275c94b-fc35-4207-8648-dfd8d166e502","candidateId","candidate-a"),Map.of("comparisonId","9275c94b-fc35-4207-8648-dfd8d166e502","candidateId","candidate-b"));
    var create=Map.<String,Object>of("analysisId","f0d36feb-ee0f-4da8-ae21-2071a3ddea18","candidates",selectors,"maxTotalUsd",0.5,"confirmSourceAuthority",true);
    assertThatThrownBy(()->ownerPilot.create(create,manager)).hasMessageContaining("Authenticated owner");
    UUID pilot=UUID.fromString((String)legacyOwnerPilot(create,owner).get("pilotId"));
    var profile=Map.of("provider","openai","model","fixture-separate-source-model","configured",true,"inputUsdPerMillion",0.01,"outputUsdPerMillion",0.01);
    when(ml.workflow(eq("cpq-pilot/capabilities"),anyMap())).thenReturn(Map.of("profiles",Map.of("fixture-review",profile),"sourceFidelityConfiguration",Map.of("fixture-review",Map.of("reasoningEffort","low","supportedReasoningEfforts",List.of("low","medium","high","xhigh","max")))));
    assertThatThrownBy(()->ownerPilot.decision(pilot,Map.of("decision","ACCEPT_TEXT_FOR_PREPARATION","rationale","Fixture-only acceptance without the required independent stage evidence.","confirmUngradedNoRender",true),owner)).hasMessageContaining("All three independent stage results");
    var dispatched=new ArrayList<Map<String,Object>>();
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenAnswer(invocation->{
      Map<String,Object> request=invocation.getArgument(1);dispatched.add(request);var input=(Map<String,Object>)request.get("input");var results=new ArrayList<Map<String,Object>>();
      for(var packet:(List<Map<String,Object>>)input.get("packets")) {
        var result=new LinkedHashMap<String,Object>();result.put("neutralId",packet.get("neutralId"));result.put("fixtureLabel","TEST_FIXTURE");
        if("SOURCE_FIDELITY".equals(input.get("purpose")))result.put("decision","UNKNOWN");
        else {var dimensions=new LinkedHashMap<String,Object>();for(String d:DIMS)dimensions.put(d,Map.of("level",dispatched.size()==2?"STRONG":"WEAK","uncertainty","TEST_FIXTURE no creative claim"));result.put("dimensions",dimensions);assertThat(packet.keySet()).containsExactlyInAnyOrder("neutralId","prompt","promptSha256","productionSettings");}
        results.add(result);
      }
      return Map.of("requestId",request.get("requestId"),"provider","openai","model","fixture-separate-source-model","costUsd",0.0001,"usage",Map.of("prompt_tokens",10,"completion_tokens",10),"results",results,"evidenceType","MACHINE_REVIEW","executionStatus","COMPLETED","fixtureLabel","TEST_FIXTURE");
    });
    for(String slot:List.of("SOURCE_FIDELITY","CRITIC_A","CRITIC_B")) {
      var authorization=Map.<String,Object>of("slot",slot,"profileId","fixture-review","provider","openai","model","fixture-separate-source-model","maxOutputTokens",4000,"maxCostUsd",0.1,"authorizePaidInference",true,"automaticRetries",false,"idempotencyKey","fixture-key-"+slot+"-unique");
      var denied=new LinkedHashMap<String,Object>(authorization);denied.put("authorizePaidInference",false);
      assertThatThrownBy(()->ownerPilot.authorize(pilot,denied,owner)).hasMessageContaining("Explicit single paid dispatch");
      var authorized=ownerPilot.authorize(pilot,authorization,owner);
      ownerPilot.authorize(pilot,authorization,owner); // Same durable key returns the existing reservation.
      var wrongKey=new LinkedHashMap<String,Object>(authorization);wrongKey.put("idempotencyKey","different-fixture-key-"+slot);
      assertThatThrownBy(()->ownerPilot.authorize(pilot,wrongKey,owner)).hasMessageContaining("already has an immutable authorization");var requests=(List<Map<String,Object>>)authorized.get("requests");UUID request=UUID.fromString((String)requests.stream().filter(r->slot.equals(r.get("slot"))).findFirst().orElseThrow().get("requestId"));
      assertThatThrownBy(()->ownerPilot.execute(pilot,request,owner)).hasMessageContaining("Real dispatch disabled");
      org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",true);
      try {ownerPilot.execute(pilot,request,owner);ownerPilot.execute(pilot,request,owner);} finally {org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",false);}
    }
    assertThat(((List<Map<String,Object>>)((Map<String,Object>)dispatched.get(1).get("input")).get("packets")).stream().map(packet->packet.get("neutralId"))).containsExactly("Q04","Q01","Q02","Q03");
    assertThat(((List<Map<String,Object>>)((Map<String,Object>)dispatched.get(2).get("input")).get("packets")).stream().map(packet->packet.get("neutralId"))).containsExactly("Q02","Q03","Q01","Q04");
    assertThat(dispatched).hasSize(3);assertThat(dispatched.stream().map(r->r.get("requestId")).distinct()).hasSize(3);
    assertThat((Map<String,Object>)dispatched.getFirst().get("authorization")).containsEntry("reasoningEffort","low");
    assertThat((Map<String,Object>)dispatched.get(1).get("authorization")).doesNotContainKey("reasoningEffort");
    assertThat((Map<String,Object>)dispatched.get(2).get("authorization")).doesNotContainKey("reasoningEffort");
    var view=ownerPilot.view(pilot,owner);assertThat((List<?>)((Map<?,?>)view.get("comparison")).get("disagreements")).hasSize(24);
    assertThat(view).containsEntry("humanReviewCount",0).containsEntry("officialGrading","INACTIVE").containsEntry("renderAuthorized",false);
    assertThat(ownerPilot.decision(pilot,Map.of("decision","KEEP_ORIGINAL","rationale","Fixture owner decision; no real approval or creative inference.","confirmUngradedNoRender",true),owner).get("evidence")).isInstanceOf(List.class);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence WHERE evidence_type='MACHINE_REVIEW'",Integer.class)).isEqualTo(3);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_calibration_judgments",Integer.class)).isZero();
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_calibration_examples",Integer.class)).isZero();
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
  }

  @Test void realSavedMimiContradictorySettingsAreRejectedWithExplicitDiagnostics() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();
    var conflicting=new LinkedHashMap<String,Object>(settings());conflicting.put("contentId",10);conflicting.put("promptVersionId",10);conflicting.put("aspectRatio","16:9");event("PRODUCTION_SETTINGS",conflicting);
    var preflight=api.originalPreflight(Map.of("contentId",10,"promptVersionId",10,"expectedPromptSha256","0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98"),manager);
    assertThat((List<String>)preflight.get("blockers")).anyMatch(message->message.contains("PRODUCTION_SETTINGS_CONFLICT"));
  }

  @Test void sourceReasoningAuthorizationAndFailedRequestCannotBeReplayed() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();
    var owner=actor("fixture-owner","OWNER");
    var selectors=List.of(Map.of("comparisonId","e651eb75-b894-477d-ae77-0fe6e05236da","candidateId","candidate-a"),Map.of("comparisonId","9275c94b-fc35-4207-8648-dfd8d166e502","candidateId","candidate-a"),Map.of("comparisonId","9275c94b-fc35-4207-8648-dfd8d166e502","candidateId","candidate-b"));
    var create=Map.<String,Object>of("analysisId","f0d36feb-ee0f-4da8-ae21-2071a3ddea18","candidates",selectors,"maxTotalUsd",0.3,"confirmSourceAuthority",true);
    UUID pilot=UUID.fromString((String)legacyOwnerPilot(create,owner).get("pilotId"));
    var profile=Map.of("provider","openai","model","gpt-6.1-sol","configured",true,"inputUsdPerMillion",2.5,"outputUsdPerMillion",10.0);
    var caps=Map.<String,Object>of("profiles",Map.of("openai-escalation",profile),"sourceFidelityConfiguration",Map.of("openai-escalation",Map.of("reasoningEffort","low","supportedReasoningEfforts",List.of("low","medium","high","xhigh","max"))));
    when(ml.workflow(eq("cpq-pilot/capabilities"),anyMap())).thenReturn(caps);
    var auth=Map.<String,Object>of("slot","SOURCE_FIDELITY","profileId","openai-escalation","provider","openai","model","gpt-6.1-sol","maxOutputTokens",4000,"maxCostUsd",0.3,"authorizePaidInference",true,"automaticRetries",false,"idempotencyKey","fresh-source-fixture-authorization");
    var wrongEffort=new LinkedHashMap<String,Object>(auth);wrongEffort.put("reasoningEffort","none");
    assertThatThrownBy(()->ownerPilot.authorize(pilot,wrongEffort,owner)).hasMessageContaining("reasoning effort differs");
    var noConsent=new LinkedHashMap<String,Object>(auth);noConsent.put("authorizePaidInference",false);
    assertThatThrownBy(()->ownerPilot.authorize(pilot,noConsent,owner)).hasMessageContaining("Explicit single paid dispatch");
    var authorized=ownerPilot.authorize(pilot,auth,owner);
    ownerPilot.authorize(pilot,auth,owner); // Canonicalized effort remains idempotent.
    var requests=(List<Map<String,Object>>)authorized.get("requests");
    UUID requestId=UUID.fromString((String)requests.getFirst().get("requestId"));
    assertThat((Map<String,Object>)requests.getFirst().get("authorization")).containsEntry("reasoningEffort","low");
    long historicalCount=jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events",Long.class);
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenReturn(Map.of("executionStatus","FAILED_OR_AMBIGUOUS","failureCategory","REASONING_BUDGET_EXHAUSTED","rawResponse","","usage",Map.of("prompt_tokens",6161,"completion_tokens",4000),"costUsd",0.0554025));
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",true);
    try {
      ownerPilot.execute(pilot,requestId,owner);
      ownerPilot.execute(pilot,requestId,owner); // Inspection only, never a second ML dispatch.
    } finally {org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",false);}
    verify(ml,times(1)).workflow(eq("cpq-pilot/execute"),anyMap());
    assertThat(jdbc.queryForObject("SELECT state FROM cpq_machine_requests WHERE request_id=?",String.class,requestId)).isEqualTo("FAILED_OR_AMBIGUOUS");
    assertThat(jdbc.queryForObject("SELECT response->>'failureCategory' FROM cpq_machine_requests WHERE request_id=?",String.class,requestId)).isEqualTo("REASONING_BUDGET_EXHAUSTED");
    var newKey=new LinkedHashMap<String,Object>(auth);newKey.put("idempotencyKey","another-source-fixture-authorization");
    assertThatThrownBy(()->ownerPilot.authorize(pilot,newKey,owner)).hasMessageContaining("already has an immutable authorization");
    // A fresh pilot is allowed only with its own explicit, bounded authorization.
    UUID freshPilot=UUID.fromString((String)legacyOwnerPilot(create,owner).get("pilotId"));
    var fresh=ownerPilot.authorize(freshPilot,newKey,owner);
    var freshRequests=(List<Map<String,Object>>)fresh.get("requests");
    assertThat(freshRequests.getFirst().get("requestId")).isNotEqualTo(requestId.toString());
    assertThat(jdbc.queryForObject("SELECT count(*) FROM post_family_workflow_events",Long.class)).isEqualTo(historicalCount);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence",Integer.class)).isZero();
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
    assertThat(fresh).containsEntry("renderAuthorized",false).containsEntry("officialGrading","INACTIVE");
  }

  Map<String,Object> singleCreate() {return Map.of("analysisId","f0d36feb-ee0f-4da8-ae21-2071a3ddea18","candidates",List.of(Map.of("comparisonId","e651eb75-b894-477d-ae77-0fe6e05236da","candidateId","candidate-a"),Map.of("comparisonId","9275c94b-fc35-4207-8648-dfd8d166e502","candidateId","candidate-a"),Map.of("comparisonId","9275c94b-fc35-4207-8648-dfd8d166e502","candidateId","candidate-b")),"maxTotalUsd",2.0,"confirmSourceAuthority",true);}
  void singleCapabilities() {
    var profile=Map.of("provider","openai","model","gpt-6.1-sol","configured",true,"inputUsdPerMillion",2.5,"outputUsdPerMillion",10.0);
    when(ml.workflow(eq("cpq-pilot/capabilities"),anyMap())).thenReturn(Map.of("profiles",Map.of("openai-escalation",profile),"sourceFidelityConfiguration",Map.of("openai-escalation",Map.of("reasoningEffort","low","supportedReasoningEfforts",List.of("low")))));
  }
  Map<String,Object> singleAuth(String sha) {var a=new LinkedHashMap<String,Object>();a.put("slot","SOURCE_FIDELITY");a.put("subjectPromptSha256",sha);a.put("profileId","openai-escalation");a.put("provider","openai");a.put("model","gpt-6.1-sol");a.put("maxOutputTokens",4000);a.put("maxCostUsd",0.30);a.put("authorizePaidInference",true);a.put("automaticRetries",false);a.put("idempotencyKey","TEST_FIXTURE_"+sha);return a;}
  Path singleEvidence(String file){var p=Path.of("../docs/cpq-single-subject-source-fidelity-evidence",file);return Files.exists(p)?p:Path.of("intelligence/docs/cpq-single-subject-source-fidelity-evidence",file);}
  Map<String,Object> mockedSingle(Map<String,Object> request, boolean pass) throws Exception {
    var input=(Map<String,Object>)request.get("input");var packet=((List<Map<String,Object>>)input.get("packets")).getFirst();String neutral=String.valueOf(packet.get("neutralId"));
    assertThat(input).isEqualTo(json.readValue(Files.readString(singleEvidence(neutral+"-prototype-input.json")),Map.class));
    Map<String,Object> f=json.readValue(Files.readString(singleEvidence(neutral+"-single-subject-response.TEST_FIXTURE.json")),Map.class);
    var result=((List<Map<String,Object>>)f.get("results")).getFirst();result.put("sourceBinding",packet.get("sourceBinding"));
    if(pass){result.put("decision","PASS");result.put("omissions",List.of());for(var m:(List<Map<String,Object>>)result.get("mappings"))m.put("consistency","PASS");}
    var response=new LinkedHashMap<String,Object>(f);response.put("requestId",request.get("requestId"));response.put("provider","openai");response.put("model","gpt-6.1-sol");response.put("costUsd",.001);response.put("evidenceType","MACHINE_REVIEW");response.put("executionStatus","COMPLETED");response.put("fixtureLabel","TEST_FIXTURE");response.put("rawResponse",json.writeValueAsString(f));response.put("usageAccountingStatus","COMPLETE");response.put("providerMetadata",Map.of("finishReason","stop"));response.put("usage",Map.of("prompt_tokens",100,"completion_tokens",100));return response;
  }
  @Test void singleSubjectRequestsKeepUnknownEvidenceAndIsolateFailedCandidate() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();singleCapabilities();var owner=actor("fixture-owner","OWNER");
    var data=Path.of("../data");if(!Files.exists(data))data=Path.of("intelligence/data");
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"dataRoot",data.toAbsolutePath().toString());
    var created=ownerPilot.create(singleCreate(),owner);UUID pilot=UUID.fromString((String)created.get("pilotId"));
    assertThat(((Map<?,?>)created.get("snapshot")).get("sourceReviewUnit")).isEqualTo("SINGLE_SUBJECT_V1");
    assertThat((Map<String,Object>)created.get("sourceReview")).containsEntry("validatedSubjects",0).containsEntry("criticGateSatisfied",false);
    var subjects=(List<Map<String,Object>>)((Map<String,Object>)created.get("snapshot")).get("subjects");
    var ids=new ArrayList<UUID>();for(var subject:subjects){var authorization=singleAuth((String)subject.get("promptSha256"));var view=ownerPilot.authorize(pilot,authorization,owner);ownerPilot.authorize(pilot,authorization,owner);
      var requests=(List<Map<String,Object>>)view.get("requests");var req=requests.getLast();ids.add(UUID.fromString((String)req.get("requestId")));
      var changed=new LinkedHashMap<String,Object>(authorization);changed.put("maxCostUsd",.31);var changedCost=changed;assertThatThrownBy(()->ownerPilot.authorize(pilot,changedCost,owner)).hasMessageContaining("Idempotency key reused");
      changed=new LinkedHashMap<String,Object>(authorization);changed.put("idempotencyKey",UUID.randomUUID().toString());var duplicate=changed;assertThatThrownBy(()->ownerPilot.authorize(pilot,duplicate,owner)).hasMessageContaining("immutable authorization");
    }
    assertThat(ids.stream().distinct()).hasSize(4);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_machine_requests WHERE pilot_id=? AND subject_prompt_sha256 IS NOT NULL",Integer.class,pilot)).isEqualTo(4);
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenAnswer(inv->{Map<String,Object> request=inv.getArgument(1);if(request.get("requestId").equals(ids.get(1).toString()))return Map.of("executionStatus","FAILED_OR_AMBIGUOUS","failureCategory","REASONING_BUDGET_EXHAUSTED","rawResponse","");return mockedSingle(request,false);});
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",true);
    try {for(var id:ids){ownerPilot.execute(pilot,id,owner);ownerPilot.execute(pilot,id,owner);}}finally{org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",false);}
    verify(ml,times(4)).workflow(eq("cpq-pilot/execute"),anyMap());var view=ownerPilot.view(pilot,owner);var aggregate=(Map<String,Object>)view.get("sourceReview");
    assertThat(aggregate).containsEntry("validatedSubjects",3).containsEntry("complete",false).containsEntry("criticGateSatisfied",false).containsEntry("manualAdjudicationSubjects",3);
    assertThat((List<?>)aggregate.get("missingSubjectIds")).hasSize(1);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence WHERE pilot_id=?",Integer.class,pilot)).isEqualTo(3);
    var snapshots=json.writeValueAsString(view.get("snapshot"));assertThat(snapshots).contains("88.40625");assertThat(view).containsEntry("renderAuthorized",false).containsEntry("officialGrading","INACTIVE").containsEntry("humanReviewCount",0);
    var critic=new LinkedHashMap<String,Object>(singleAuth("ignored"));critic.remove("subjectPromptSha256");critic.put("slot","CRITIC_A");critic.put("idempotencyKey",UUID.randomUUID().toString());
    var authorized=ownerPilot.authorize(pilot,critic,owner);var reqs=(List<Map<String,Object>>)authorized.get("requests");UUID criticId=UUID.fromString((String)reqs.getLast().get("requestId"));
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",true);try{assertThatThrownBy(()->ownerPilot.execute(pilot,criticId,owner)).hasMessageContaining("source stage must complete");}finally{org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",false);}
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
  }
  @Test void allFourExactSourceReviewsRequiredForCriticGate() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();singleCapabilities();var owner=actor("fixture-owner","OWNER");
    var data=Path.of("../data");if(!Files.exists(data))data=Path.of("intelligence/data");org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"dataRoot",data.toAbsolutePath().toString());
    var created=ownerPilot.create(singleCreate(),owner);UUID pilot=UUID.fromString((String)created.get("pilotId"));
    var subjects=(List<Map<String,Object>>)((Map<String,Object>)created.get("snapshot")).get("subjects");
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenAnswer(inv->mockedSingle(inv.getArgument(1),true));
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",true);
    try{int count=0;for(var subject:subjects){var view=ownerPilot.authorize(pilot,singleAuth((String)subject.get("promptSha256")),owner);var reqs=(List<Map<String,Object>>)view.get("requests");UUID id=UUID.fromString((String)reqs.getLast().get("requestId"));var executed=ownerPilot.execute(pilot,id,owner);count++;assertThat((Map<String,Object>)executed.get("sourceReview")).containsEntry("validatedSubjects",count).containsEntry("criticGateSatisfied",count==4);}}
    finally{org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",false);}
    // TEST_FIXTURE PASS is a mechanics test only, never a real Mimi semantic finding.
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_machine_requests WHERE pilot_id=?",Integer.class,pilot)).isEqualTo(4);
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
  }

  @Test void completeUnknownSourceEvidenceRequiresReviewAndWrongSubjectCannotAuthorize() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();singleCapabilities();var owner=actor("fixture-owner","OWNER");
    var data=Path.of("../data");if(!Files.exists(data))data=Path.of("intelligence/data");org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"dataRoot",data.toAbsolutePath().toString());
    var created=ownerPilot.create(singleCreate(),owner);UUID pilot=UUID.fromString((String)created.get("pilotId"));
    assertThatThrownBy(()->ownerPilot.authorize(pilot,singleAuth("f".repeat(64)),owner)).hasMessageContaining("Exact pilot subjectPromptSha256");
    var missing=new LinkedHashMap<String,Object>(singleAuth("f".repeat(64)));missing.remove("subjectPromptSha256");assertThatThrownBy(()->ownerPilot.authorize(pilot,missing,owner)).hasMessageContaining("Exact pilot subjectPromptSha256");
    var subjects=(List<Map<String,Object>>)((Map<String,Object>)created.get("snapshot")).get("subjects");
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenAnswer(inv->mockedSingle(inv.getArgument(1),false));
    org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",true);
    try{for(var subject:subjects){var view=ownerPilot.authorize(pilot,singleAuth((String)subject.get("promptSha256")),owner);var reqs=(List<Map<String,Object>>)view.get("requests");ownerPilot.execute(pilot,UUID.fromString((String)reqs.getLast().get("requestId")),owner);}}
    finally{org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"realEnabled",false);}
    assertThat((Map<String,Object>)ownerPilot.view(pilot,owner).get("sourceReview")).containsEntry("validatedSubjects",4).containsEntry("complete",true).containsEntry("manualAdjudicationSubjects",4).containsEntry("criticGateSatisfied",false);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence WHERE evidence_type='MACHINE_REVIEW'",Integer.class)).isEqualTo(4);
  }

  @Test void offlineCitationRevalidationCannotPromoteSavedFailedExecutionOrOpenCriticGate() throws Exception {
    realSavedMimiPilotResolvesFourSubjectsWithUnknownSemanticEvidence();
    var docs=Path.of("../docs/cpq-single-subject-delivery-evidence");if(!Files.exists(docs))docs=Path.of("intelligence/docs/cpq-single-subject-delivery-evidence");
    Map<String,Object> row=json.readValue(Files.readString(docs.resolve("real-original-only-durable-result.json")),Map.class);
    Map<String,Object> saved=json.readValue(Files.readString(docs.resolve("real-original-only-prepared-pilot.json")),Map.class);
    UUID pilot=UUID.fromString((String)row.get("pilot_id")),requestId=UUID.fromString((String)row.get("request_id"));
    jdbc.update("INSERT INTO cpq_owner_pilots(pilot_id,owner_principal,policy_version,scope_sha256,snapshot,total_budget_usd) VALUES(?,'fixture-owner','OWNER_MACHINE_PILOT_V1',?,CAST(? AS jsonb),.70)",pilot,"a".repeat(64),json.writeValueAsString(saved.get("snapshot")));
    jdbc.update("INSERT INTO cpq_machine_requests(request_id,pilot_id,slot,idempotency_key,authorized_by,authorization_payload,input_sha256,state,reserved_usd,input,response,failure,subject_prompt_sha256) VALUES(?,?,'SOURCE_FIDELITY',?,'fixture-owner',CAST(? AS jsonb),?,'FAILED_OR_AMBIGUOUS',.10,CAST(? AS jsonb),CAST(? AS jsonb),?,?)",requestId,pilot,row.get("idempotency_key"),json.writeValueAsString(row.get("authorization_payload")),row.get("input_sha256"),json.writeValueAsString(row.get("input")),json.writeValueAsString(row.get("response")),row.get("failure"),row.get("subject_prompt_sha256"));
    String before=jdbc.queryForObject("SELECT row_to_json(r)::text FROM cpq_machine_requests r WHERE request_id=?",String.class,requestId);
    var response=new LinkedHashMap<String,Object>((Map<String,Object>)row.get("response"));var raw=json.readValue((String)response.get("rawResponse"),Map.class);response.put("results",raw.get("results"));
    org.springframework.test.util.ReflectionTestUtils.invokeMethod(ownerPilot,"validateSingleSource",(Map<String,Object>)row.get("input"),response);
    assertThat(response.get("executionStatus")).isEqualTo("FAILED_OR_AMBIGUOUS");
    assertThat(jdbc.queryForObject("SELECT row_to_json(r)::text FROM cpq_machine_requests r WHERE request_id=?",String.class,requestId)).isEqualTo(before);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence WHERE pilot_id=?",Integer.class,pilot)).isZero();
    var view=ownerPilot.view(pilot,actor("fixture-owner","OWNER"));assertThat((Map<String,Object>)view.get("sourceReview")).containsEntry("validatedSubjects",0).containsEntry("criticGateSatisfied",false);
    assertThat(view).containsEntry("officialGrading","INACTIVE").containsEntry("renderAuthorized",false).containsEntry("humanReviewCount",0);
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();verifyNoInteractions(ml);
  }

  @Test void ownerAuthorizedOfflineRecoveryIsAppendOnlyIdempotentAndKeepsFail() throws Exception {
    offlineCitationRevalidationCannotPromoteSavedFailedExecutionOrOpenCriticGate();
    var data=Path.of("../data");if(!Files.exists(data))data=Path.of("intelligence/data");org.springframework.test.util.ReflectionTestUtils.setField(ownerPilot,"dataRoot",data.toAbsolutePath().toString());
    UUID pilot=UUID.fromString("770e8477-f352-499e-aabd-b7418435e70b"),requestId=UUID.fromString("6f078994-3385-4910-8423-47a46ad9999a");var owner=actor("fixture-owner","OWNER");
    String before=jdbc.queryForObject("SELECT row_to_json(r)::text FROM cpq_machine_requests r WHERE request_id=?",String.class,requestId);
    var file=Path.of("../docs/cpq-source-fidelity-closure-evidence/offline-revalidated-response.json");if(!Files.exists(file))file=Path.of("intelligence/docs/cpq-source-fidelity-closure-evidence/offline-revalidated-response.json");
    Map<String,Object> validated=json.readValue(Files.readString(file),Map.class);
    when(ml.workflow(eq("cpq-pilot/revalidate-source"),anyMap())).thenReturn(validated);
    assertThatThrownBy(()->ownerPilot.recoveryPreview(pilot,requestId,actor("other","OWNER"))).hasMessageContaining("owner differs");
    assertThatThrownBy(()->ownerPilot.recoverSource(pilot,requestId,Map.of(),owner)).hasMessageContaining("Explicit offline");
    var preview=ownerPilot.recoveryPreview(pilot,requestId,owner);assertThat(preview).containsEntry("eligible",true).containsEntry("persisted",false).containsEntry("newInference",false);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence",Integer.class)).isZero();
    var authorization=new LinkedHashMap<String,Object>((Map<String,Object>)preview.get("expectedAuthorization"));authorization.put("authorizeOfflineRevalidation",true);authorization.put("confirmNoInferenceNoApproval",true);
    for(String field:List.of("rawResponseSha256","inputSha256","originalResponseSha256","providerResponseId","citationContractVersion","sourceBinding")){
      var wrong=new LinkedHashMap<String,Object>(authorization);wrong.put(field,"incorrect");assertThatThrownBy(()->ownerPilot.recoverSource(pilot,requestId,wrong,owner)).hasMessageContaining("authorization binding differs");
    }
    var altered=json.readValue(json.writeValueAsString(validated),Map.class);((Map<String,Object>)((List<?>)altered.get("results")).getFirst()).put("uncertainty","Changed model finding is forbidden.");
    when(ml.workflow(eq("cpq-pilot/revalidate-source"),anyMap())).thenReturn(altered);
    assertThatThrownBy(()->ownerPilot.recoverSource(pilot,requestId,authorization,owner)).hasMessageContaining("findings must remain unchanged");
    when(ml.workflow(eq("cpq-pilot/revalidate-source"),anyMap())).thenReturn(validated);
    var view=ownerPilot.recoverSource(pilot,requestId,authorization,owner);ownerPilot.recoverSource(pilot,requestId,authorization,owner);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_pilot_evidence WHERE pilot_id=?",Integer.class,pilot)).isEqualTo(1);
    assertThat(jdbc.queryForObject("SELECT row_to_json(r)::text FROM cpq_machine_requests r WHERE request_id=?",String.class,requestId)).isEqualTo(before);
    var aggregate=(Map<String,Object>)view.get("sourceReview");assertThat(aggregate).containsEntry("validatedSubjects",1).containsEntry("requiredSubjects",4).containsEntry("manualAdjudicationSubjects",1).containsEntry("criticGateSatisfied",false).containsEntry("complete",false);
    var subjects=(List<Map<String,Object>>)aggregate.get("subjects");assertThat(subjects.stream().filter(x->Boolean.TRUE.equals(x.get("hasValidatedEvidence"))).findFirst().orElseThrow()).containsEntry("neutralId","Q04").containsEntry("semanticVerdict","FAIL").containsEntry("status","REVIEW_REQUIRED");
    assertThat(subjects.stream().filter(x->"NOT_EXECUTED".equals(x.get("status")))).hasSize(3);
    var evidence=((List<Map<String,Object>>)view.get("evidence")).getFirst();assertThat(evidence).containsKey("evidenceId");assertThat((Map<String,Object>)evidence.get("payload")).containsEntry("evidenceProvenance","RECOVERED_MACHINE_EVIDENCE");
    assertThat(view).containsEntry("officialGrading","INACTIVE").containsEntry("humanReviewCount",0).containsEntry("renderAuthorized",false);
    assertThat(json.writeValueAsString(view.get("snapshot"))).contains("88.40625");assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
    verify(ml,never()).workflow(eq("cpq-pilot/execute"),anyMap());
  }

  Map<String,Object> diagnosticSetup() throws Exception {
    offlineCitationRevalidationCannotPromoteSavedFailedExecutionOrOpenCriticGate();
    var fixture=Path.of("../docs/cpq-draft-comparison-evidence");if(!Files.exists(fixture))fixture=Path.of("intelligence/docs/cpq-draft-comparison-evidence");
    Map<String,Object> estimates=json.readValue(Files.readString(fixture.resolve("preflight.TEST_FIXTURE.json")),Map.class);
    when(ml.workflow(eq("cpq-pilot/draft-preflight"),anyMap())).thenAnswer(inv->{var body=(Map<String,Object>)inv.getArgument(1);return estimates.get("deepseek-primary".equals(body.get("profileId"))?"CRITIC_A":"CRITIC_B");});
    when(ml.workflow(eq("cpq-pilot/capabilities"),anyMap())).thenReturn(Map.of("profiles",Map.of("deepseek-primary",Map.of("configured",true),"openai-escalation",Map.of("configured",true))));
    return draftReview.preflight(actor("fixture-owner","OWNER"));
  }
  Map<String,Object> diagnosticAuth(Map<String,Object> pre,String stage) {
    var cfg=(Map<String,Object>)((Map<String,Object>)pre.get("reviewers")).get(stage);var auth=new LinkedHashMap<String,Object>();for(String key:List.of("provider","model","reasoningEffort","maxOutputTokens"))auth.put(key,cfg.get(key));
    auth.put("slot",stage);auth.put("profileId",stage.equals("CRITIC_A")?"deepseek-primary":"openai-escalation");auth.put("scopeSha256",pre.get("scopeSha256"));auth.put("authorizePaidInference",true);auth.put("automaticRetries",false);auth.put("confirmDiagnosticOnly",true);auth.put("maxCostUsd",stage.equals("CRITIC_A")?.06:.14);auth.put("idempotencyKey","TEST_FIXTURE_DIAGNOSTIC_"+stage);return auth;
  }
  Map<String,Object> diagnosticResponse(Map<String,Object> body) throws Exception {
    var file=Path.of("../docs/cpq-draft-comparison-evidence/pairwise-response.TEST_FIXTURE.json");if(!Files.exists(file))file=Path.of("intelligence/docs/cpq-draft-comparison-evidence/pairwise-response.TEST_FIXTURE.json");Map<String,Object> comparison=json.readValue(Files.readString(file),Map.class);var auth=(Map<String,Object>)body.get("authorization");
    var out=new LinkedHashMap<String,Object>();out.put("reviewPurpose","DRAFT_COMPARATIVE_REVIEW_V1");out.put("policyVersion","DRAFT_COMPARATIVE_REVIEW_V1");out.put("evidenceType","MACHINE_REVIEW");out.put("diagnosticOnly",true);out.put("requestId",body.get("requestId"));out.put("provider",auth.get("provider"));out.put("model",auth.get("model"));out.put("executionStatus","COMPLETED");out.put("effectiveRequestConfiguration",Map.of("provider",auth.get("provider"),"model",auth.get("model"),"reasoningEffort",auth.get("reasoningEffort"),"maxOutputTokens",auth.get("maxOutputTokens")));out.put("rawResponse",json.writeValueAsString(comparison));out.put("comparison",comparison);out.put("fixtureLabel","TEST_FIXTURE");out.put("costUsd",.001);out.put("usageAccountingStatus","COMPLETE");out.put("usage",Map.of("prompt_tokens",1000,"completion_tokens",1000));out.put("providerMetadata",Map.of("finishReason","stop","model",auth.get("model"),"requestId","TEST_FIXTURE_RESPONSE","apiStatus","COMPLETED"));return out;
  }
  Map<String,Object> diagnosticCreate(Map<String,Object> pre,MockHttpServletRequest owner){return draftReview.create(Map.of("scopeSha256",pre.get("scopeSha256"),"authorizeDiagnosticRecordCreation",true,"confirmDiagnosticOnly",true,"maxTotalUsd",.20),owner);}
  @Test void diagnosticPairIsExactBlindUngradedAndCannotBypassProductionPilot() throws Exception {
    var pre=diagnosticSetup();var owner=actor("fixture-owner","OWNER");assertThat(pre).containsEntry("persisted",false);
    assertThatThrownBy(()->draftReview.preflight(new MockHttpServletRequest())).hasMessageContaining("Authenticated owner required");
    assertThatThrownBy(()->draftReview.create(Map.of(),owner)).hasMessageContaining("Explicit creation consent");
    assertThatThrownBy(()->draftReview.create(Map.of("authorizeDiagnosticRecordCreation",true,"confirmDiagnosticOnly",true,"scopeSha256","wrong"),owner)).hasMessageContaining("exact scope");
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_owner_pilots",Integer.class)).isEqualTo(1);
    var scope=(Map<String,Object>)pre.get("snapshot");var inputs=(Map<String,Object>)scope.get("inputs");var first=(Map<String,Object>)inputs.get("CRITIC_A");var second=(Map<String,Object>)inputs.get("CRITIC_B");
    var a=(List<Map<String,Object>>)first.get("packets");var b=(List<Map<String,Object>>)second.get("packets");assertThat(a.getFirst().get("label")).isEqualTo("A");assertThat(b.getFirst().get("label")).isEqualTo("B");assertThat(a.getFirst()).isEqualTo(b.getLast());assertThat(a.getLast()).isEqualTo(b.getFirst());
    assertThat(sha((String)a.getFirst().get("prompt"))).isEqualTo("82a2d896798076cb3fd3cf88482c5709167d88034a8b6702149f000bc690abef");assertThat(sha((String)a.getLast().get("prompt"))).isEqualTo("0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98");
    assertThat(json.writeValueAsString(inputs)).doesNotContain("supervisorMapping","88.40625","OWNER_DECISION","DRAFT_ONLY","promptSha256");
    int prompts=jdbc.queryForObject("SELECT count(*) FROM prompt_versions",Integer.class);var created=diagnosticCreate(pre,owner);UUID id=UUID.fromString((String)created.get("reviewId"));assertThat(created).containsEntry("diagnosticOnly",true).containsEntry("renderAuthorized",false).containsEntry("officialGrading","INACTIVE");
    assertThatThrownBy(()->ownerPilot.view(id,owner)).hasMessageContaining("Pilot not found");assertThatThrownBy(()->draftReview.view(UUID.fromString("770e8477-f352-499e-aabd-b7418435e70b"),owner)).hasMessageContaining("Diagnostic review not found");assertThatThrownBy(()->draftReview.view(id,actor("different-owner","OWNER"))).hasMessageContaining("owner differs");
    for(String stage:List.of("CRITIC_A","CRITIC_B")){var auth=diagnosticAuth(pre,stage);draftReview.authorize(id,auth,owner);draftReview.authorize(id,auth,owner);}
    var view=draftReview.view(id,owner);var requests=(List<Map<String,Object>>)view.get("requests");assertThat(requests).hasSize(2);
    assertThatThrownBy(()->draftReview.execute(id,UUID.fromString((String)requests.getFirst().get("requestId")),owner)).hasMessageContaining("disabled");
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenAnswer(inv->diagnosticResponse(inv.getArgument(1)));org.springframework.test.util.ReflectionTestUtils.setField(draftReview,"realEnabled",true);
    try{for(var req:requests){UUID request=UUID.fromString((String)req.get("requestId"));draftReview.execute(id,request,owner);draftReview.execute(id,request,owner);}}finally{org.springframework.test.util.ReflectionTestUtils.setField(draftReview,"realEnabled",false);}
    verify(ml,times(2)).workflow(eq("cpq-pilot/execute"),anyMap());view=draftReview.view(id,owner);assertThat((List<?>)view.get("evidence")).hasSize(2);assertThat(view).containsEntry("sourceFidelity","UNRESOLVED_NOT_EVALUATED_BY_THIS_REVIEW").containsEntry("officialGrading","INACTIVE").containsEntry("renderAuthorized",false).containsEntry("humanReviewCount",0);
    var old=ownerPilot.view(UUID.fromString("770e8477-f352-499e-aabd-b7418435e70b"),owner);assertThat((Map<String,Object>)old.get("sourceReview")).containsEntry("validatedSubjects",0).containsEntry("criticGateSatisfied",false);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM prompt_versions",Integer.class)).isEqualTo(prompts);assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
  }
  @Test void diagnosticFailureRetainsFirstCriticAndDoesNotPermitRetry() throws Exception {
    var pre=diagnosticSetup();var owner=actor("fixture-owner","OWNER");UUID id=UUID.fromString((String)diagnosticCreate(pre,owner).get("reviewId"));
    for(String stage:List.of("CRITIC_A","CRITIC_B"))draftReview.authorize(id,diagnosticAuth(pre,stage),owner);
    var reqs=(List<Map<String,Object>>)draftReview.view(id,owner).get("requests");
    when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenAnswer(inv->{var body=(Map<String,Object>)inv.getArgument(1);var response=diagnosticResponse(body);if("openai".equals(response.get("provider"))){response.remove("comparison");response.put("executionStatus","FAILED_OR_AMBIGUOUS");response.put("rawResponse","{truncated");response.put("failureCategory","VISIBLE_OUTPUT_TRUNCATED");}return response;});
    org.springframework.test.util.ReflectionTestUtils.setField(draftReview,"realEnabled",true);
    try{assertThatThrownBy(()->draftReview.execute(id,UUID.fromString((String)reqs.getLast().get("requestId")),owner)).hasMessageContaining("First critic must complete");for(var req:reqs)draftReview.execute(id,UUID.fromString((String)req.get("requestId")),owner);draftReview.execute(id,UUID.fromString((String)reqs.getLast().get("requestId")),owner);}finally{org.springframework.test.util.ReflectionTestUtils.setField(draftReview,"realEnabled",false);}
    verify(ml,times(2)).workflow(eq("cpq-pilot/execute"),anyMap());var view=draftReview.view(id,owner);assertThat((List<?>)view.get("evidence")).hasSize(1);var requests=(List<Map<String,Object>>)view.get("requests");assertThat(requests.getLast()).containsEntry("state","FAILED_OR_AMBIGUOUS");assertThat((Map<String,Object>)requests.getLast().get("response")).containsEntry("rawResponse","{truncated");
  }
  @Test void firstDiagnosticFailureBlocksRemainingReviewer() throws Exception {
    var pre=diagnosticSetup();var owner=actor("fixture-owner","OWNER");UUID id=UUID.fromString((String)diagnosticCreate(pre,owner).get("reviewId"));for(String stage:List.of("CRITIC_A","CRITIC_B"))draftReview.authorize(id,diagnosticAuth(pre,stage),owner);
    var requests=(List<Map<String,Object>>)draftReview.view(id,owner).get("requests");when(ml.workflow(eq("cpq-pilot/execute"),anyMap())).thenReturn(Map.of("executionStatus","FAILED_OR_AMBIGUOUS","rawResponse","","fixtureLabel","TEST_FIXTURE"));org.springframework.test.util.ReflectionTestUtils.setField(draftReview,"realEnabled",true);
    try{draftReview.execute(id,UUID.fromString((String)requests.getFirst().get("requestId")),owner);assertThatThrownBy(()->draftReview.execute(id,UUID.fromString((String)requests.getLast().get("requestId")),owner)).hasMessageContaining("First critic must complete");}finally{org.springframework.test.util.ReflectionTestUtils.setField(draftReview,"realEnabled",false);}verify(ml,times(1)).workflow(eq("cpq-pilot/execute"),anyMap());assertThat((List<?>)draftReview.view(id,owner).get("evidence")).isEmpty();
  }

}
