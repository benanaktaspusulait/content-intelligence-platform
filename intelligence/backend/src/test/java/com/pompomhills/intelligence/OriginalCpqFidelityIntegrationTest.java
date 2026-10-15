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
    jdbc.execute("TRUNCATE cpq_original_subjects,cpq_calibration_corpora,contents,post_family_workflow_events CASCADE");
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
  @Test void realSavedMimiPilotIdentifiesActualSettingsAndCandidateStoryBindingBlockers() throws Exception {
    // Only this disposable Testcontainers DB receives fixture identities/reviews. Never real human evidence.
    Path projection=Path.of("../docs/cpq-v1-mimi-pilot-2026-10-15/supervisor-only/persisted-cpq-test-projection.json");
    if(!Files.exists(projection)) projection=Path.of("intelligence/docs/cpq-v1-mimi-pilot-2026-10-15/supervisor-only/persisted-cpq-test-projection.json");
    var data=json.readValue(Files.readString(projection),Map.class);
    jdbc.execute("TRUNCATE cpq_original_subjects,cpq_calibration_corpora,contents,post_family_workflow_events CASCADE");
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
    assertThat(preflight).containsEntry("status","BLOCKED");
    assertThat((List<String>)preflight.get("blockers")).containsExactly("PRODUCTION_SETTINGS_BINDING_REQUIRED");
    assertThatThrownBy(()->bind(selectors)).hasMessageContaining("PRODUCTION_SETTINGS_BINDING_REQUIRED");
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
      assertThatThrownBy(()->api.fidelityReview(analysis,comparison,candidateId,review,evidenceReviewer)).hasMessageContaining("Approved story ID and revision binding are required");
      assertThat(((Number)((Map<String,Object>)((Map<String,Object>)candidate.get("review")).get("canonicalRuleEvaluation")).get("score")).doubleValue()).isCloseTo(88.40625,within(0.000001));
    }
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_fidelity_reviews",Integer.class)).isZero();
    assertThat(jdbc.queryForObject("SELECT count(*) FROM cpq_original_subjects",Integer.class)).isZero();
    assertThat(jdbc.queryForObject("SELECT activated FROM cpq_policy_state",Boolean.class)).isFalse();
    assertThat(jdbc.queryForObject("SELECT encode(digest(string_agg(id::text||kind||payload::text,'' ORDER BY id),'sha256'),'hex') FROM post_family_workflow_events",String.class)).isEqualTo(historyDigest);
    assertThat(jdbc.queryForObject("SELECT raw_text FROM prompt_versions WHERE id=10",String.class)).isEqualTo(original);
    verifyNoInteractions(ml);
  }
}
