package com.pompomhills.intelligence.workflow;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.pompomhills.intelligence.quality.QualityMlClient;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.mock.web.MockHttpServletRequest;
import org.testcontainers.junit.jupiter.*;
import org.testcontainers.containers.PostgreSQLContainer;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/** Disposable SQL ledger with real Python evaluator/compiler. Transport fixtures only. */
@Testcontainers(disabledWithoutDocker=true)
class OptimizationLoopTest {
 @Container static PostgreSQLContainer<?> pg=new PostgreSQLContainer<>("postgres:17-alpine");
 static final Path ROOT=Path.of(System.getProperty("user.dir")).getParent().getParent();
 static final ObjectMapper json=new ObjectMapper();
 JdbcTemplate jdbc;JdbcClient db;QualityMlClient ml;OptimizationLoopService service;boolean targetBlocked,visualBlocked;
 Map<String,Object> fixture;String mode="material";int submitted;Runnable inFlight=()->{};UUID runId;
 MockHttpServletRequest owner=new MockHttpServletRequest();long clockOffset=0;
 Map<String,Object> bridge(String operation,Map<String,Object> input) throws Exception {
  var builder=new ProcessBuilder(ROOT.resolve("intelligence/ml-service/.venv/bin/python").toString(),ROOT.resolve("intelligence/ml-service/tests/optimization_loop_bridge.py").toString());
  builder.environment().put("POMPOM_DATA_ROOT",ROOT.resolve("intelligence/data").toString());builder.environment().put("PYTHONPATH",ROOT.resolve("intelligence/ml-service/tests").toString());builder.environment().put("DEEPSEEK_API_KEY","isolated-test-only");builder.environment().put("OPENAI_API_KEY","isolated-test-only");builder.redirectError(ProcessBuilder.Redirect.INHERIT);
  var process=builder.start();process.getOutputStream().write(json.writeValueAsBytes(Map.of("operation",operation,"input",input)));process.getOutputStream().close();String out=new String(process.getInputStream().readAllBytes());assertThat(process.waitFor()).isZero();return json.readValue(out,new TypeReference<>(){});
 }
 @BeforeEach void setup() throws Exception {
  var ds=new DriverManagerDataSource(pg.getJdbcUrl(),pg.getUsername(),pg.getPassword());jdbc=new JdbcTemplate(ds);db=JdbcClient.create(ds);
  jdbc.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public; CREATE FUNCTION prevent_cpq_evidence_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable'; END $$;");
  jdbc.execute(Files.readString(ROOT.resolve("intelligence/backend/src/main/resources/db/migration/V68__bounded_optimization_runs.sql")));
  ml=mock(QualityMlClient.class);fixture=bridge("scope",Map.of());
  when(ml.workflow(anyString(),anyMap())).thenAnswer(inv->{String op=inv.getArgument(0);Map<String,Object> in=inv.getArgument(1);if(op.equals("cpq-pilot/optimization-loop-execute")){submitted++;inFlight.run();if(mode.equals("ambiguous"))return Map.of("executionStatus","FAILED_OR_AMBIGUOUS","usageAccountingStatus","INCOMPLETE","failure",Map.of("layer","PROVIDER_TRANSPORT","exceptionCategory","TimeoutError","retrySafe",false));var copy=new LinkedHashMap<>(in);copy.put("_testMode",mode);return bridge(op,copy);}return bridge(op,in);});
  var util=new CpqOwnerPilotService(db,json,mock(CreativePromptQualityService.class),ml);
  service=new OptimizationLoopService(db,util,mock(CreativePromptQualityService.class),mock(WorkflowService.class),ml){
   @Override Map<String,Object> scope(UUID id,String draft){var copy=new LinkedHashMap<>(fixture);if(draft!=null&&!draft.isBlank()){copy.put("baselinePrompt",draft);copy.put("baselineSha256",CpqOwnerPilotService.hash(draft));}return copy;}
   @Override Map<String,Object> targetAwarePreflight(UUID id){return targetBlocked?Map.of("state","TARGET_BLOCKED_BY_STORY_CONSTRAINT","generationAllowed",false,"researchGenerationEligibility",Map.of("version","canonical-a-text-research-eligibility-v1","allowed",false,"state","BLOCKED_BY_PROTECTED_STORY_CONSTRAINT"),"currentScore",88.40625,"fixedEvidenceOptimisticCeiling",89.3125,"canonicalATargetStatus","CANONICAL_A_UNATTAINABLE_WITH_CURRENT_EVIDENCE","reasons",List.of("Protected ATTEMPT_001 story constraint"),"renderAuthorized",false):visualBlocked?Map.of("state","TARGET_BLOCKED_BY_EVIDENCE","generationAllowed",false,"researchGenerationEligibility",Map.of("version","canonical-a-text-research-eligibility-v1","allowed",true,"state","ELIGIBLE_FOR_EXPLICIT_OWNER_AUTHORIZATION","promptApprovalAllowed",false,"imageGenerationAllowed",false,"renderAuthorized",false),"currentScore",93.42708333333334,"fixedEvidenceOptimisticCeiling",94.26041666666667,"canonicalATargetStatus","CANONICAL_A_POTENTIALLY_ATTAINABLE","renderAuthorized",false):Map.of("state","DIAGNOSING","generationAllowed",true,"researchGenerationEligibility",Map.of("version","canonical-a-text-research-eligibility-v1","allowed",true,"state","ELIGIBLE_FOR_EXPLICIT_OWNER_AUTHORIZATION"),"currentScore",88.40625,"fixedEvidenceOptimisticCeiling",100,"canonicalATargetStatus","CANONICAL_A_POTENTIALLY_ATTAINABLE","renderAuthorized",false);}
   @Override Instant now(){return Instant.now().plusSeconds(clockOffset);}
  };service.realEnabled=true;owner.setUserPrincipal(()->"isolated-owner");owner.addUserRole("OWNER");
 }
 Map<String,Object> grant() {
  var g=new LinkedHashMap<String,Object>();g.put("analysisId",fixture.get("analysisId"));g.put("scopeSha256",CpqOwnerPilotService.hash(new CpqOwnerPilotService(db,json,null,ml).encode(fixture)));g.put("idempotencyKey",UUID.randomUUID().toString());g.put("target",OptimizationLoopService.TARGET);g.put("mode","ADAPTIVE");g.put("maxRounds",3);g.put("maxRequests",9);g.put("maxRunSeconds",600);g.put("maxTotalUsd",10.);g.put("authorizePaidInference",true);g.put("confirmSourceAuthority",true);g.put("automaticRetries",false);
  var profiles=CpqOwnerPilotService.map(service.capabilities().get("profiles"));var ops=new ArrayList<Map<String,Object>>();
  for(String id:profiles.keySet())for(String role:List.of("GENERATION","SOURCE_FIDELITY","CRITIC")){var p=CpqOwnerPilotService.map(profiles.get(id));ops.add(new LinkedHashMap<>(Map.of("profileId",id,"role",role,"provider",p.get("provider"),"model",p.get("model"),"reasoningEffort",p.get("reasoningEffort"),"maxOutputTokens",p.get("reviewMaxOutputTokens"),"maxCostUsd",1.)));}g.put("operations",ops);return g;
 }
 Map<String,Object> researchGrant(){var g=grant();g.put("mode","DEEPSEEK_ONLY");g.put("maxRounds",1);g.put("maxRequests",3);g.put("researchOnly",true);g.put("purpose","REAL_MODEL_A_CAPABILITY_RESEARCH_V1");g.put("confirmNoPromptApproval",true);g.put("confirmNoImageOrRender",true);g.put("operations",CpqOwnerPilotService.rows(g.get("operations")).stream().filter(r->("GENERATION".equals(r.get("role"))&&"deepseek-primary".equals(r.get("profileId")))||(!"GENERATION".equals(r.get("role"))&&"openai-escalation".equals(r.get("profileId")))).toList());return g;}
 Map<String,Object> start(Map<String,Object> g){var v=service.start(g,owner);runId=UUID.fromString(String.valueOf(v.get("runId")));return v;}
 Map<String,Object> advance(int n){for(int i=0;i<n;i++)service.processNext();return service.view(runId,owner);}
 Map<String,Object> progress(Map<String,Object> v){return CpqOwnerPilotService.map(v.get("progress"));}
 @Test void twoActualRoundsRetainUsefulDraftThenRejectProductionRegression(){
  start(grant());var v=advance(12);assertThat(v.get("state")).isEqualTo("STOPPED");assertThat(progress(v).get("reason")).isEqualTo("ROUND_LIMIT");
  var drafts=CpqOwnerPilotService.rows(v.get("drafts"));assertThat(drafts).hasSize(2);assertThat(submitted).isEqualTo(7);
  for(var d:drafts)assertThat(((Number)CpqOwnerPilotService.map(CpqOwnerPilotService.map(CpqOwnerPilotService.map(d.get("payload")).get("evaluation")).get("canonical")).get("score")).doubleValue()).isCloseTo(88.40625,within(1e-9));
  assertThat(progress(v).get("bestDraftId")).isNotEqualTo("");assertThat(v.get("renderAuthorized")).isEqualTo(false);assertThat(String.valueOf(v.get("events"))).contains("ROUND_EVALUATED","retained=true");
 }
 @Test void duplicateStartAndReconnectDoNotDispatchAgain(){var g=grant();var v=start(g);assertThat(service.start(g,owner).get("runId")).isEqualTo(v.get("runId"));assertThat(jdbc.queryForObject("SELECT count(*) FROM optimization_runs",Integer.class)).isEqualTo(1);assertThat(service.latest(UUID.fromString(String.valueOf(fixture.get("analysisId"))),owner).get("runId")).isEqualTo(v.get("runId"));assertThat(submitted).isZero();}
 @Test void unauthorizedAndInactiveTargetsRefused(){assertThatThrownBy(()->service.start(grant(),new MockHttpServletRequest())).hasMessageContaining("Authenticated owner");var g=grant();g.put("target","CPQ_A_PLUS");assertThatThrownBy(()->service.start(g,owner)).hasMessageContaining("Unsupported/inactive");assertThat(submitted).isZero();}
 @Test void targetAwareStoryBlockStopsBeforeGrantOrProvider(){targetBlocked=true;var g=grant();assertThatThrownBy(()->service.start(g,owner)).hasMessageContaining("TARGET_BLOCKED_BY_STORY_CONSTRAINT");assertThat(jdbc.queryForObject("SELECT count(*) FROM optimization_runs",Integer.class)).isZero();assertThat(submitted).isZero();}
 @Test void protectedStoryBlockAlsoDeniesResearchGrant(){targetBlocked=true;assertThatThrownBy(()->service.start(researchGrant(),owner)).hasMessageContaining("BLOCKED_BY_PROTECTED_STORY_CONSTRAINT");assertThat(jdbc.queryForObject("SELECT count(*) FROM optimization_runs",Integer.class)).isZero();assertThat(submitted).isZero();}
 @Test void visualEvidenceBlockAllowsOnlyAuditedResearchAndNeverApproval() throws Exception {visualBlocked=true;assertThatThrownBy(()->service.start(grant(),owner)).hasMessageContaining("TARGET_BLOCKED_BY_EVIDENCE");var g=researchGrant();var first=start(g);assertThat(service.start(g,owner).get("runId")).isEqualTo(first.get("runId"));var v=advance(8);assertThat(submitted).isEqualTo(3);assertThat(v).containsEntry("researchOnly",true).containsEntry("promptApprovalAllowed",false).containsEntry("imageGenerationAllowed",false).containsEntry("renderAuthorized",false);assertThatThrownBy(()->service.accept(runId,Map.of(),owner,mock(com.pompomhills.intelligence.content.ContentWorkspaceController.class))).hasMessageContaining("cannot approve");}
 @Test void incompleteResearchGrantFailsBeforeReservationOrDispatch(){visualBlocked=true;var g=researchGrant();g.remove("confirmNoImageOrRender");assertThatThrownBy(()->service.start(g,owner)).hasMessageContaining("downstream prohibitions");assertThat(jdbc.queryForObject("SELECT count(*) FROM optimization_runs",Integer.class)).isZero();assertThat(submitted).isZero();}
 @Test void unlistedModelAndMissingIndependentRoleRefused(){var g=grant();CpqOwnerPilotService.rows(g.get("operations")).getFirst().put("model","unlisted");assertThatThrownBy(()->service.start(g,owner)).hasMessageContaining("model/effort");var h=grant();h.put("operations",CpqOwnerPilotService.rows(h.get("operations")).stream().filter(r->!"SOURCE_FIDELITY".equals(r.get("role"))).toList());assertThatThrownBy(()->service.start(h,owner)).hasMessageContaining("Independent");}
 @Test void cancellationCollectsInflightButNeverStartsReview(){start(grant());advance(1);inFlight=()->service.stop(runId,owner);var v=advance(2);assertThat(submitted).isEqualTo(1);assertThat(progress(v).get("reason")).isEqualTo("OWNER_CANCELLED_AFTER_COLLECTING_INFLIGHT");assertThat(CpqOwnerPilotService.rows(v.get("requests"))).hasSize(1);}
 @Test void unknownAccountingStopsWithoutReplay(){mode="ambiguous";start(grant());var v=advance(6);assertThat(submitted).isEqualTo(1);assertThat(progress(v).get("reason")).isEqualTo("UNCERTAIN_PROVIDER_DISPATCH_OR_CONTRACT");assertThat(CpqOwnerPilotService.map(v.get("cost")).get("unknownReservedUsd")).isEqualTo(1.);assertThatThrownBy(()->service.resume(runId,owner)).hasMessageContaining("cannot resume");}
 @Test void requestLimitIsServerEnforced(){var g=grant();g.put("maxRequests",1);start(g);var v=advance(5);assertThat(submitted).isEqualTo(1);assertThat(progress(v).get("reason")).isEqualTo("REQUEST_LIMIT");}
 @Test void budgetStopsBeforeDispatch(){var g=grant();g.put("maxTotalUsd",.1);start(g);var v=advance(3);assertThat(progress(v).get("reason")).isEqualTo("BUDGET_LIMIT");assertThat(submitted).isZero();}
 @Test void durationStopsBeforeDispatch(){start(grant());clockOffset=1000;var v=advance(1);assertThat(progress(v).get("reason")).isEqualTo("TIME_LIMIT");assertThat(submitted).isZero();}
 @Test void repeatedEquivalentPlansStop(){mode="equivalent";start(grant());var v=advance(6);assertThat(submitted).isEqualTo(2);assertThat(progress(v).get("reason")).isEqualTo("REPEATED_EQUIVALENT_CANDIDATES");assertThat(progress(v).get("bestDraftId")).isEqualTo("");}
 @Test void authorizationAndDraftsAreImmutable(){start(grant());advance(3);assertThatThrownBy(()->jdbc.update("UPDATE optimization_runs SET grant_payload='{}'::jsonb WHERE id=?",runId)).hasMessageContaining("Immutable optimization authorization");assertThatThrownBy(()->jdbc.update("UPDATE optimization_run_drafts SET payload='{}'::jsonb WHERE run_id=?",runId)).hasMessageContaining("immutable");}
}
