package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;

@Testcontainers(disabledWithoutDocker=true)
class Step6GovernancePostgresTest {
  @Container static PostgreSQLContainer<?> db=new PostgreSQLContainer<>("postgres:17-alpine");
  JdbcClient jdbc;ObjectMapper json=new ObjectMapper();Step6GovernanceService service;UUID id;Map<String,Object> analysis;
  final Step6GovernanceService.Actor approver=new Step6GovernanceService.Actor("architect",Set.of("ARCHITECTURE_APPROVER"));
  final Step6GovernanceService.Actor reviewer=new Step6GovernanceService.Actor("independent-reviewer",Set.of("EVIDENCE_REVIEWER"));
  final Step6GovernanceService.Actor operator=new Step6GovernanceService.Actor("operator",Set.of("PRODUCTION_OPERATOR"));
  @BeforeEach void setup() throws Exception {
    jdbc=JdbcClient.create(new DriverManagerDataSource(db.getJdbcUrl(),db.getUsername(),db.getPassword()));
    jdbc.sql("DROP TABLE IF EXISTS post_family_workflow_events").update();jdbc.sql("DROP TABLE IF EXISTS prompt_versions").update();
    jdbc.sql("CREATE TABLE prompt_versions(content_id bigint,id bigint,raw_text text,PRIMARY KEY(content_id,id))").update();
    jdbc.sql("CREATE TABLE post_family_workflow_events(id uuid PRIMARY KEY,kind text,binding_sha256 text,payload jsonb,created_at timestamptz DEFAULT now())").update();
    analysis=json.readValue(getClass().getResourceAsStream("/governance-analysis-1.11.json"),Map.class);
    jdbc.sql("INSERT INTO prompt_versions VALUES(10,10,:text)").param("text",analysis.get("originalPrompt")).update();
    id=insert("REVIEW",analysis);
    var story=insert("STORY_APPROVAL",Map.of("approvedText",analysis.get("originalPrompt")));
    insert("CREATIVE_STUDIO_SESSION",Map.of("contentId",10,"promptVersionId",10,"approvalRecordId",story.toString()));
    service=new Step6GovernanceService(jdbc,json,"1.11");
  }
  UUID insert(String kind,Map<String,Object> data) throws Exception {
    UUID key=UUID.randomUUID();jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES(:id,:kind,CAST(:data AS jsonb))")
      .param("id",key).param("kind",kind).param("data",json.writeValueAsString(data)).update();return key;
  }
  Map<String,Object> request() {return new LinkedHashMap<>(Map.of("justification","The approved narrative has two evidenced strategies and a complete payoff.","operatorConfirmed",true));}
  Map<String,Object> exception() {var r=request();r.put("ruleId","ATTEMPT_001");r.put("exceptionPolicy",Step6GovernanceService.EXCEPTION);return r;}
  Map<String,Object> support() {
    var r=request();r.put("approvedEventsPreserved",true);
    var qs=List.of("Mimi tries to peel the stuck note away with her other hand", "each pull doubles the number of sticky notes", "Mimi sneezes and the sticky notes fly off");
    int i=0;for(String key:List.of("miniStory","activeProgression","payoff")) {String q=qs.get(i++);r.put(key,Map.of("sourceQuote",q,"approvedStoryQuote",q,"reason","Independent reviewer verified this event against the approved narrative and current plan."));}return r;
  }
  void provideSupport() {service.command(id,"support",support(),reviewer);}
  @Test void authenticatedScopedApprovalRetainsCanonicalFailureAndHistory() {
    String before=jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id").param("id",id).query(String.class).single();
    provideSupport();var result=service.command(id,"exception",exception(),approver);
    assertThat(result).containsEntry("ruleId","ATTEMPT_001").containsEntry("exceptionPolicy",Step6GovernanceService.EXCEPTION).containsEntry("principal","architect");
    assertThat((Map<String,Object>)service.evaluate(id,operator).get("attemptException")).containsKey("recordId");
    assertThat(jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id").param("id",id).query(String.class).single()).isEqualTo(before);
  }
  @Test void noRoleNoJustificationNoConfirmationNoScopeNoIndependentSupport() {
    assertThatThrownBy(()->service.command(id,"exception",exception(),operator)).hasMessageContaining("ARCHITECTURE_APPROVER");
    var noJustification=exception();noJustification.put("justification","");assertThatThrownBy(()->service.command(id,"exception",noJustification,approver)).hasMessageContaining("justification");
    var noConfirmation=exception();noConfirmation.put("operatorConfirmed",false);assertThatThrownBy(()->service.command(id,"exception",noConfirmation,approver)).hasMessageContaining("confirmation");
    var wrong=exception();wrong.put("ruleId","OTHER_BLOCKER");assertThatThrownBy(()->service.command(id,"exception",wrong,approver)).hasMessageContaining("scope");
    assertThatThrownBy(()->service.command(id,"exception",exception(),approver)).hasMessageContaining("INDEPENDENT_STORY");
  }
  @Test void samePersonCannotReviewAndApproveAndClaimsCannotSupplyAuthority() {
    provideSupport();assertThatThrownBy(()->service.command(id,"exception",exception(),new Step6GovernanceService.Actor("independent-reviewer",Set.of("ARCHITECTURE_APPROVER")))).hasMessageContaining("INDEPENDENT_APPROVER");
    var req=new org.springframework.mock.web.MockHttpServletRequest();req.addHeader("X-Role","ARCHITECTURE_APPROVER");
    var forged=exception();forged.put("roles",List.of("ARCHITECTURE_APPROVER"));
    assertThatThrownBy(()->service.command(id,"exception",forged,Step6GovernanceService.Actor.from(req))).hasMessageContaining("ARCHITECTURE_APPROVER");
  }
  @Test void separateTextAcceptanceDoesNotWaiveRulesOrAuthorizeRender() {
    var r=service.command(id,"text-acceptance",request(),operator);
    assertThat(r).containsEntry("state","TEXT_ACCEPTED_RENDER_BLOCKED").containsKey("unresolvedFindings");
    var state=service.evaluate(id,operator);assertThat(state).containsEntry("renderPermission",false);
    assertThat((Map<String,Object>)state.get("attemptException")).isEmpty();
    assertThat((Map<String,Object>)state.get("textAcceptance")).containsKey("recordId");
  }
  @Test void staleAnalysisRulesetPromptAndSettingsAreRejected() throws Exception {
    var oldRules=new Step6GovernanceService(jdbc,json,"1.12");assertThat(oldRules.evaluate(id,operator)).containsEntry("blockedReason","STALE_RULESET");
    jdbc.sql("UPDATE prompt_versions SET raw_text='changed' WHERE id=10").update();assertThat(service.evaluate(id,operator)).containsEntry("blockedReason","STALE_PROMPT");
    jdbc.sql("UPDATE prompt_versions SET raw_text=:text WHERE id=10").param("text",analysis.get("originalPrompt")).update();
    insert("PRODUCTION_SETTINGS",Map.of("contentId",10,"promptVersionId",10,"generator","OTHER"));assertThat(service.evaluate(id,operator)).containsEntry("blockedReason","STALE_SETTINGS");
    jdbc.sql("DELETE FROM post_family_workflow_events WHERE kind='PRODUCTION_SETTINGS'").update();
    insert("REVIEW",analysis);assertThat(service.evaluate(id,operator)).containsEntry("blockedReason","STALE_ANALYSIS");
  }
  @Test void riskAcknowledgementIsScopedAndDoesNotPassCanonicalRules() {
    var req=request();req.put("ruleId","PRODUCIBILITY_003");var accepted=service.command(id,"risk-acknowledgement",req,operator);
    assertThat(accepted).containsEntry("ruleId","PRODUCIBILITY_003").containsKey("acceptedRisk");
    var invalid=request();invalid.put("ruleId","INSTANT_VISUAL_ABSURDITY_GATE");assertThatThrownBy(()->service.command(id,"risk-acknowledgement",invalid,operator)).hasMessageContaining("Only governed");
  }
  @Test void revocationImmediatelyInvalidatesException() {
    provideSupport();var approved=service.command(id,"exception",exception(),approver);var revoke=request();revoke.put("targetRecordId",approved.get("recordId"));service.command(id,"revoke",revoke,approver);
    assertThat((Map<String,Object>)service.evaluate(id,operator).get("attemptException")).isEmpty();
  }
  @Test void incompleteEvidenceOrUnacceptedRiskNeverGainsEffectiveAdmission() throws Exception {
    provideSupport();service.command(id,"exception",exception(),approver);
    var report=new LinkedHashMap<>((Map<String,Object>)analysis.get("canonicalRuleEvaluation"));
    report.put("overallScore",95); // synthetic admission fixture only; never persisted as analysis or a production score
    var proof=service.validationAdmission(1,10,10,Step6GovernanceService.sha(String.valueOf(analysis.get("originalPrompt"))),"1.11",json.writeValueAsString(report),3,1);
    assertThat(proof).containsEntry("eligible",false);
    assertThat((List<?>)proof.get("canonicalFailures")).hasSize(4);
  }
  @Test void completeIndependentAdmissionKeepsOriginalCountsAndOnlyResolvesTarget() throws Exception {
    provideSupport();service.command(id,"exception",exception(),approver);
    var risk=request();risk.put("ruleId","PRODUCIBILITY_003");service.command(id,"risk-acknowledgement",risk,operator);
    var canonical=(Map<String,Object>)analysis.get("canonicalRuleEvaluation");
    var report=new LinkedHashMap<>(canonical);
    report.put("overallScore",95); // separate synthetic complete-evidence fixture, never a saved score
    report.put("unknownRules",List.of());report.put("serviceErrors",List.of());
    var failures=((List<Map<String,Object>>)report.get("failedRules")).stream().filter(x->List.of("ATTEMPT_001","PRODUCIBILITY_003").contains(x.get("ruleId"))).toList();report.put("failedRules",failures);
    var proof=service.validationAdmission(77,10,10,Step6GovernanceService.sha(String.valueOf(analysis.get("originalPrompt"))),"1.11",json.writeValueAsString(report),1,1);
    assertThat(proof).containsEntry("eligible",true).containsEntry("originalBlockerCount",1).containsEntry("originalCriticalCount",1).containsEntry("remainingBlockerCount",0);
    assertThat(((List<Map<String,Object>>)proof.get("canonicalFailures")).get(0)).containsEntry("outcome","FAIL");
    var nonWaivable=new LinkedHashMap<String,Object>(failures.get(0));nonWaivable.put("ruleId","OTHER_HARD_BLOCKER");report.put("failedRules",List.of(nonWaivable));
    assertThat(service.validationAdmission(77,10,10,Step6GovernanceService.sha(String.valueOf(analysis.get("originalPrompt"))),"1.11",json.writeValueAsString(report),1,0)).containsEntry("eligible",false);
  }
}
