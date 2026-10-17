package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.pompomhills.intelligence.quality.QualityMlClient;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.mock.web.MockHttpServletRequest;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static com.pompomhills.intelligence.workflow.CpqOwnerPilotService.*;

/** Disposable PostgreSQL + real owner/service/ML HTTP contracts, SDK mocked only. */
@Testcontainers(disabledWithoutDocker=true)
class StoryExperimentContractTest {
  @Container static PostgreSQLContainer<?> pg=new PostgreSQLContainer<>("postgres:17-alpine");
  static final Path ROOT=Path.of(System.getProperty("user.dir")).getParent().getParent();
  static final ObjectMapper json=new ObjectMapper().findAndRegisterModules();
  static Process bridgeProcess;static java.io.BufferedWriter bridgeInput;static java.io.BufferedReader bridgeOutput;
  @BeforeAll static void warmBridge() throws Exception {
    var builder=new ProcessBuilder(ROOT.resolve("intelligence/ml-service/.venv/bin/python").toString(),"-u",ROOT.resolve("intelligence/ml-service/tests/story_experiment_bridge_server.py").toString());
    builder.environment().put("POMPOM_DATA_ROOT",ROOT.resolve("intelligence/data").toString());builder.environment().put("PYTHONPATH",ROOT.resolve("intelligence/ml-service").toString());
    builder.redirectError(ProcessBuilder.Redirect.INHERIT);bridgeProcess=builder.start();
    bridgeInput=new java.io.BufferedWriter(new java.io.OutputStreamWriter(bridgeProcess.getOutputStream()));
    bridgeOutput=new java.io.BufferedReader(new java.io.InputStreamReader(bridgeProcess.getInputStream()));
  }
  @AfterAll static void closeBridge() {if(bridgeProcess!=null)bridgeProcess.destroy();}
  JdbcTemplate sql;JdbcClient db;QualityMlClient ml;StoryEvolutionService service;CpqOwnerPilotService util;
  Map<String,Object> fixture,manifest,body;MockHttpServletRequest owner;String mode="valid",drift="";int transports;
  boolean crashAfterStory,cancelAfterStory,tamperAfterStory;UUID run;

  Map<String,Object> bridge(String operation,Map<String,Object> input) throws Exception {
    bridgeInput.write(json.writeValueAsString(Map.of("operation",operation,"input",input,"mode",mode)));bridgeInput.newLine();bridgeInput.flush();
    String line=bridgeOutput.readLine();assertThat(line).as("ML bridge process must be alive").isNotNull();
    var reply=json.readValue(line,new TypeReference<Map<String,Object>>(){});assertThat(reply.get("error")).as("ML bridge error: %s",reply).isNull();
    return json.readValue(String.valueOf(reply.get("output")),new TypeReference<>(){});
  }
  @BeforeEach void setup() throws Exception {
    var datasource=new DriverManagerDataSource(pg.getJdbcUrl(),pg.getUsername(),pg.getPassword());sql=new JdbcTemplate(datasource);db=JdbcClient.create(datasource);
    sql.execute("DROP SCHEMA public CASCADE;CREATE SCHEMA public");
    sql.execute(Files.readString(ROOT.resolve("intelligence/backend/src/main/resources/db/migration/V69__autonomous_story_evolution.sql")));
    sql.execute(Files.readString(ROOT.resolve("intelligence/backend/src/main/resources/db/migration/V71__story_pilot_immutable_receipts.sql")));
    fixture=bridge("fixture",Map.of());manifest=json.readValue(Files.readString(ROOT.resolve("intelligence/docs/CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json")),new TypeReference<>(){});
    var source=map(manifest.get("sourceSnapshot"));var workflow=mock(WorkflowService.class);ml=mock(QualityMlClient.class);
    when(workflow.approvedStoryForCpq(uuid(source.get("storyId")),uuid(source.get("approvalRecordId")))).thenReturn(Map.of("text",fixture.get("text"),"revision",source.get("revision")));
    var canonical=json.readValue(Files.readString(ROOT.resolve("intelligence/docs/p2-canonical-aware-story-evidence/canonical-evaluation.json")),new TypeReference<Map<String,Object>>(){});
    util=new CpqOwnerPilotService(db,json,null,ml){@Override public Map<String,Object> context(UUID a,UUID b,String c){return Map.of("approvedStory",source,"canonical",canonical,"originalPrompt",readPrompt(),"productionSettings",Map.of("contentProfile","ABSURD_PHYSICS","generator","SEEDANCE_2_0_MINI","desiredDuration",15.0,"openingStrategy","AUTO","settings",Map.of("mode","image2video","resolution","480p","aspectRatio","9:16")));}};
    service=new StoryEvolutionService(db,util,workflow,ml){@Override void afterPilotReceipt(UUID id,String role){
      if("STORY".equals(role)&&cancelAfterStory)sql.update("UPDATE story_evolution_runs SET cancel_requested=true WHERE id=?",id);
      if("STORY".equals(role)&&crashAfterStory)throw new IllegalStateException("Offline crash after durable receipt");
      if("STORY".equals(role)&&tamperAfterStory)sql.update("UPDATE story_evolution_runs SET progress=jsonb_set(progress,'{STORYReceipt,result,alternatives,0,text}',to_jsonb('Changed after durable receipt'::text)) WHERE id=?",id);
    }};service.realEnabled=true;service.transactionManager=new DataSourceTransactionManager(datasource);
    owner=new MockHttpServletRequest();owner.setUserPrincipal(()->"disposable-test-owner");owner.addUserRole("OWNER");
    when(ml.workflow(anyString(),anyMap())).thenAnswer(inv->{
      String operation=inv.getArgument(0);Map<String,Object> input=inv.getArgument(1);
      if(operation.equals("creative-role"))transports++;
      var output=new LinkedHashMap<>(bridge(operation,input));
      if(operation.equals("story-experiment/preflight")&&!drift.isBlank())output.put(drift,"changed-after-authorization");
      if(operation.equals("creative-role")&&mode.equals("fixture-fallback"))output.put("provider","ISOLATED_FIXTURE");
      return output;
    });
    body=new LinkedHashMap<>();body.put("experimentVersion",StoryEvolutionService.PILOT);body.put("sourceStoryRecordId",source.get("storyId"));body.put("approvalRecordId",source.get("approvalRecordId"));
    body.put("baselineAnalysisId",map(manifest.get("authorizationTemplate")).get("baselineAnalysisId"));body.put("objective",map(manifest.get("authorizationTemplate")).get("objective"));
    body.put("protectedAnchors",map(map(fixture.get("context")).get("storyExperiment")).get("protectedAnchors"));
  }
  String readPrompt(){try{return Files.readString(ROOT.resolve("intelligence/docs/p2-canonical-aware-story-evidence/generated-prompt.txt")).strip();}catch(Exception e){throw new RuntimeException(e);}}
  Map<String,Object> grant(){var g=new LinkedHashMap<>(body);var inspected=service.inspectPilot(g,owner);g.put("sourceScopeSha256",inspected.get("sourceScopeSha256"));g.put("operations",inspected.get("operations"));g.put("maxTotalUsd",inspected.get("maxTotalUsd"));g.put("maxRounds",1);g.put("maxRequests",2);g.put("maxRunSeconds",600);g.put("automaticRetries",false);g.put("fallback",false);g.put("authorizePaidInference",true);g.put("confirmSourceAuthority",true);g.put("idempotencyKey",UUID.randomUUID().toString());return g;}
  Map<String,Object> start(){var g=grant();var first=service.start(g,owner);run=uuid(first.get("runId"));assertThat(service.start(g,owner).get("runId")).isEqualTo(run.toString());return first;}
  Map<String,Object> view(){return service.view(run,owner);}
  List<Map<String,Object>> receipts(){return rows(view().get("events")).stream().filter(e->"PROVIDER_RECEIPT".equals(e.get("state"))).map(e->map(e.get("envelope"))).toList();}

  @Test void completeTwoCallContractUsesDurableCandidatesAndNoAutomaticApproval() throws Exception {
    start();service.processNext();var result=view();
    assertThat(transports).as("Run state: %s",result).isEqualTo(2);assertThat(result.get("state")).isEqualTo("RESEARCH_COMPLETE_OWNER_REVIEW_REQUIRED");
    assertThat(receipts()).hasSize(2).allSatisfy(r->{assertThat(r.get("rawProviderResponse")).isNotNull();assertThat(r.get("usage")).isNotNull();assertThat(r.get("billingStatus")).isEqualTo("KNOWN_INCURRED");});
    assertThat(map(result.get("progress"))).containsEntry("ownerStoryApproval","PENDING").containsEntry("reviewerIndependent",true);
    assertThat(map(map(result.get("progress")).get("lastAssessment")).get("recommendationReason")).isEqualTo("NO_CREATIVE_WINNER");
    assertThat(rows(result.get("drafts"))).isEmpty();service.processNext();assertThat(transports).isEqualTo(2);
    Path trace=ROOT.resolve("intelligence/backend/target/story-root-cause-positive-dry-run.json");Files.writeString(trace,json.writerWithDefaultPrettyPrinter().writeValueAsString(Map.of("evidenceOrigin","DETERMINISTIC_MOCK_ADAPTER_CONTRACT_TEST_ONLY","realProviderCalls",0,"productionDbWrites",0,"trace",result)));
  }
  @ParameterizedTest @ValueSource(strings={"zero","one","three","duplicate-id","duplicate-text","incomplete","source","unknown","proposal","malformed","missing-usage","over-budget","fixture-fallback","rule-mutation","bad-offsets"})
  void invalidFirstResultIsDurableAndNeverReservesReview(String failure){mode=failure;start();service.processNext();assertThat(transports).isEqualTo(1);assertThat(receipts()).hasSize(1);
    assertThat(receipts().getFirst().get("rawProviderResponse")).isNotNull();assertThat(view().get("state")).isEqualTo("STOPPED");
    assertThat(rows(view().get("events")).stream().filter(e->"REQUEST_RESERVED".equals(e.get("state"))).count()).isEqualTo(1);
    service.processNext();assertThat(transports).isEqualTo(1);
  }
  @ParameterizedTest @ValueSource(strings={"unknown-model","missing-model"})
  void modelMismatchKeepsFullReceiptButDoesNotClaimVerifiedCostOrReserveReview(String failure){
    mode=failure;start();service.processNext();assertThat(transports).isEqualTo(1);assertThat(receipts()).hasSize(1);
    var receipt=receipts().getFirst();assertThat(receipt.get("billingStatus")).isEqualTo("MODEL_IDENTITY_UNVERIFIED");
    assertThat(receipt.get("actualCostUsd")).isNull();assertThat(receipt.get("configuredRateCostUsd")).isEqualTo(.00027);
    assertThat(receipt.get("rawProviderResponse")).isNotNull();assertThat(view().get("state")).isEqualTo("STOPPED");
    assertThat(map(view().get("progress")).get("unresolvedBilling")).isEqualTo(true);
    service.processNext();assertThat(transports).isEqualTo(1);
  }
  @ParameterizedTest @ValueSource(strings={"saved-first","saved-followup"})
  void authenticSavedNarrativesGetSeparateOfflineEvidenceWithoutChangingPaidGate(String savedMode) throws Exception {
    mode=savedMode;start();service.processNext();assertThat(transports).isEqualTo(1);
    assertThat(view().get("state")).isEqualTo("STOPPED");assertThat(receipts()).hasSize(1);
    var receipt=receipts().getFirst();var values=rows(map(receipt.get("parsedProviderResponse")).get("alternatives"));
    assertThat(values).hasSize(2);var reports=new ArrayList<Map<String,Object>>();
    var scope=map(view().get("scope"));var context=service.pilotContext(scope,false,null,null);
    for(var candidate:values){
      var report=bridge("offline-evidence-audit",Map.of("text",scope.get("sourceStory"),"context",context,"candidate",candidate));
      assertThat(report.get("status")).isEqualTo("SEMANTIC_FIDELITY_REVIEW_REQUIRED");
      assertThat(report.get("paidReviewEligible")).isEqualTo(false);assertThat(report.get("sourceApproved")).isEqualTo(false);
      assertThat(report.get("narrativeSha256")).isEqualTo(hash(String.valueOf(candidate.get("text"))));reports.add(report);
    }
    service.processNext();assertThat(transports).isEqualTo(1);
    assertThat(rows(view().get("events")).stream().filter(e->"REQUEST_RESERVED".equals(e.get("state"))).count()).isEqualTo(1);
    String folder=savedMode.equals("saved-first")?"first-real-story-evolution-evidence":"real-story-identity-fidelity-followup-evidence";
    assertThat(receipt.get("rawProviderResponse")).isEqualTo(Files.readString(ROOT.resolve("intelligence/docs/"+folder+"/raw-model-response.txt")));
    Files.writeString(ROOT.resolve("intelligence/backend/target/story-root-cause-"+savedMode+".json"),json.writerWithDefaultPrettyPrinter().writeValueAsString(Map.of("evidenceOrigin","OFFLINE_SAVED_RESPONSE_REPLAY_MOCKED_TRANSPORT","newProviderCalls",0,"sourcePaidGateUnchanged",true,"auditReports",reports,"trace",view())));
  }
  @ParameterizedTest @ValueSource(strings={"review-timeout","review-transport","review-malformed"})
  void failedSecondCallPreservesFirstResponseAndKnownBilling(String failure){mode=failure;start();service.processNext();assertThat(transports).isEqualTo(2);assertThat(receipts()).hasSize(2);assertThat(receipts().getFirst().get("billingStatus")).isEqualTo("KNOWN_INCURRED");assertThat(receipts().getFirst().get("rawProviderResponse")).isNotNull();
    assertThat(map(view().get("progress")).get("knownActualCostUsd")).isNotNull();service.processNext();assertThat(transports).isEqualTo(2);
  }
  @Test void crashAndRestartRetainReceiptWithoutPaidReplay(){crashAfterStory=true;start();service.processNext();assertThat(receipts()).hasSize(1);assertThat(map(view().get("progress")).get("knownActualCostUsd")).isEqualTo(.00027);crashAfterStory=false;service.processNext();assertThat(transports).isEqualTo(1);}
  @Test void actualWorkerExitLeavesRunningReceiptAndRestartCannotReplay(){crashAfterStory=true;start();assertThatThrownBy(()->service.step(run)).hasMessageContaining("Offline crash");assertThat(view().get("state")).isEqualTo("RUNNING");assertThat(receipts()).hasSize(1);crashAfterStory=false;service.processNext();assertThat(transports).isEqualTo(1);}
  @Test void uncertainFirstDispatchCannotRetryOrReserveReview(){mode="story-timeout";start();service.processNext();assertThat(transports).isEqualTo(1);assertThat(receipts().getFirst().get("billingStatus")).isEqualTo("USAGE_UNKNOWN");assertThat(receipts().getFirst().get("actualCostUsd")).isNull();service.processNext();assertThat(transports).isEqualTo(1);}
  @Test void cancellationAfterReceiptStopsBeforeSecondReservation(){cancelAfterStory=true;start();service.processNext();assertThat(receipts()).hasSize(1);assertThat(transports).isEqualTo(1);}
  @Test void persistedCandidatesCannotBeChangedBetweenCalls(){tamperAfterStory=true;start();service.processNext();assertThat(transports).isEqualTo(1);assertThat(receipts()).hasSize(1);assertThat(view().toString()).contains("persisted receipt changed");}
  @Test void receiptsAndGrantAreImmutableAndThirdCallIsImpossible(){start();service.processNext();
    assertThatThrownBy(()->sql.update("UPDATE story_evolution_events SET payload='{}'::jsonb WHERE run_id=? AND payload->>'state'='PROVIDER_RECEIPT'",run)).hasMessageContaining("Immutable story pilot evidence");
    assertThatThrownBy(()->sql.update("UPDATE story_evolution_runs SET authorization_payload='{}'::jsonb WHERE id=?",run)).hasMessageContaining("Immutable story pilot authorization");
    var row=service.load(run);var progress=new LinkedHashMap<>(map(row.get("progress")));var scope=map(row.get("scope"));
    assertThatThrownBy(()->service.pilotDispatch(run,"STORY",scope,progress,service.pilotContext(scope,false,null,null))).hasMessageContaining("before dispatch");
    assertThat(transports).isEqualTo(2);
  }
  @ParameterizedTest @ValueSource(strings={"systemSha256","model"})
  void changedAuthorizedInstructionOrModelStopsBeforeReservation(String field){start();drift=field;service.processNext();assertThat(transports).isZero();assertThat(rows(view().get("events")).stream().noneMatch(e->"REQUEST_RESERVED".equals(e.get("state")))).isTrue();}
  @Test void ownerAndExactGrantLimitsAreRequired(){assertThatThrownBy(()->service.inspectPilot(body,new MockHttpServletRequest())).hasMessageContaining("Authenticated owner");var g=grant();g.put("maxRequests",3);assertThatThrownBy(()->service.start(g,owner)).hasMessageContaining("Invalid limit");assertThat(transports).isZero();}
  @Test void budgetAndSourceBindingCannotBeAlteredAfterPreflight(){var g=grant();g.put("maxTotalUsd",.00001);assertThatThrownBy(()->service.start(g,owner)).hasMessageContaining("SCOPE_OR_INSTRUCTION_MISMATCH");var stale=grant();stale.put("sourceScopeSha256","different");assertThatThrownBy(()->service.start(stale,owner)).hasMessageContaining("SCOPE_OR_INSTRUCTION_MISMATCH");assertThat(transports).isZero();}
}
