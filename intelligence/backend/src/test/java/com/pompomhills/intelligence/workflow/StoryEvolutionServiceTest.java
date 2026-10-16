package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.QualityMlClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.*;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.mock.web.MockHttpServletRequest;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@Testcontainers(disabledWithoutDocker=true)
class StoryEvolutionServiceTest {
  @Container static PostgreSQLContainer<?> pg=new PostgreSQLContainer<>("postgres:17-alpine");
  JdbcClient db; JdbcTemplate jdbc; CpqOwnerPilotService util; WorkflowService workflow; QualityMlClient ml; StoryEvolutionService service; MockHttpServletRequest owner; UUID source=UUID.randomUUID(),sourceApproval=UUID.randomUUID();
  static final Path ROOT=Path.of(System.getProperty("user.dir")).getParent().getParent();
  @BeforeEach void setup() throws Exception {
    var ds=new DriverManagerDataSource(pg.getJdbcUrl(),pg.getUsername(),pg.getPassword()); db=JdbcClient.create(ds); jdbc=new JdbcTemplate(ds);
    jdbc.execute(Files.readString(ROOT.resolve("intelligence/backend/src/main/resources/db/migration/V69__autonomous_story_evolution.sql")));
    jdbc.execute("TRUNCATE story_evolution_runs CASCADE");
    workflow=mock(WorkflowService.class);when(workflow.storyFingerprint(anyString())).thenCallRealMethod();ml=mock(QualityMlClient.class);var json=new ObjectMapper();util=new CpqOwnerPilotService(db,json,null,ml);service=new StoryEvolutionService(db,util,workflow,ml);service.realEnabled=true;
    owner=new MockHttpServletRequest();owner.setUserPrincipal(()->"test-owner");owner.addUserRole("OWNER");
    String original="Mimi sees a sticky note on her finger. She pulls and it splits into two. The notes double until she is covered, then she sneezes them onto the cabinet.";
    when(workflow.getByKind(source,"CREATIVE_ROLE")).thenReturn(Map.of("role","STORY","sourceRequest",Map.of("text",original)));
    when(workflow.approvedStoryForCpq(source,sourceApproval)).thenReturn(Map.of("text",original,"revision","original-revision"));
    Map<String,Object> first=new LinkedHashMap<>();first.put("alternatives",List.of(Map.of("candidateId","candidate-1","title","same","text",original),Map.of("candidateId","candidate-2","title","clear escalation","text",original+" The mirror reveals the mess before the sneeze.")));
    Map<String,Object> second=new LinkedHashMap<>();second.put("alternatives",List.of(Map.of("candidateId","candidate-3","title","payoff","text",original+" The mirror reveal becomes a visual loop before the sneeze.")));
    Map<String,Object> review=new LinkedHashMap<>();review.put("reviewId","review-1");review.put("sourceRequestId","ignored");review.put("sourceFingerprint","ignored");review.put("recommendedCandidateId","candidate-2");review.put("recommendationReason","Material opening and consequence progression");review.put("reviewStatus","COMPLETED");
    var review2=new LinkedHashMap<String,Object>(review);review2.put("recommendedCandidateId","candidate-3");
    when(ml.workflow(eq("creative-role"),anyMap())).thenReturn(envelope(first),envelope(review),envelope(second),envelope(review2));
  }
  Map<String,Object> grant(){var g=new LinkedHashMap<String,Object>(Map.of("sourceStoryRecordId",source.toString(),"idempotencyKey",UUID.randomUUID().toString(),"objective","Improve opening causality and escalation","maxRounds",2,"maxRequests",6,"maxTotalUsd",1.0,"maxRunSeconds",300,"authorizePaidInference",true,"confirmSourceAuthority",true,"automaticRetries",false));g.put("approvalRecordId",sourceApproval.toString());return g;}
  Map<String,Object> envelope(Map<String,Object> result){return Map.of("provider","ISOLATED_FIXTURE","calls",0,"actualCostUsd",0.0,"providerDispatched",false,"result",result);}
  @Test void rejectsInsufficientRequestBudgetBeforeStart(){var g=grant();g.put("maxRequests",2);assertThatThrownBy(()->service.start(g,owner)).isInstanceOf(org.springframework.web.server.ResponseStatusException.class);verifyNoInteractions(ml);}
  @Test void doesNotAcceptUnrecommendedFirstCandidate(){var g=grant();var run=service.start(g,owner);reset(ml);
    var candidate=Map.<String,Object>of("alternatives",List.of(Map.of("candidateId","candidate-1","text","A different source-faithful staging candidate")));
    var review=new LinkedHashMap<String,Object>();review.put("reviewStatus","COMPLETED");review.put("recommendedCandidateId",null);
    when(ml.workflow(eq("creative-role"),anyMap())).thenReturn(envelope(candidate),envelope(review));service.processNext();
    var view=service.view(UUID.fromString(String.valueOf(run.get("runId"))),owner);assertThat(view.get("state")).isEqualTo("STOPPED");assertThat(view.toString()).contains("NO_REVIEW_SUPPORTED_IMPROVEMENT");assertThat(CpqOwnerPilotService.rows(view.get("drafts"))).isEmpty();}
  @Test void runsTwoRoundsAutomaticallyAndPassesBestContext(){var run=service.start(grant(),owner);UUID id=UUID.fromString(String.valueOf(run.get("runId")));service.processNext();var afterOne=service.view(id,owner);assertThat(afterOne.get("state")).isEqualTo("READY");assertThat(CpqOwnerPilotService.map(afterOne.get("progress")).get("round")).isEqualTo(1);service.processNext();var done=service.view(id,owner);assertThat(done.get("state")).isEqualTo("AWAITING_OWNER_STORY_APPROVAL");assertThat(CpqOwnerPilotService.rows(done.get("drafts"))).hasSize(2);var calls=ArgumentCaptor.forClass(Map.class);verify(ml,atLeast(3)).workflow(eq("creative-role"),calls.capture());assertThat(calls.getAllValues().get(2).get("context").toString()).contains("bestCandidate","previousAssessment","rejectedCandidates");assertThat(done.get("events").toString()).contains("ROUND_RETAINED","AWAITING_OWNER_STORY_APPROVAL");}
  @Test void duplicateStartReusesRunAndEquivalentCandidateIsRejected(){var g=grant();var first=service.start(g,owner);assertThat(service.start(g,owner).get("runId")).isEqualTo(first.get("runId"));service.processNext();var view=service.view(UUID.fromString(String.valueOf(first.get("runId"))),owner);assertThat(view.get("progress").toString()).contains("EQUIVALENT_OR_MEANINGLESS");}
  @Test void ownerApprovalBindsNewSourceAndSeparatePromptHandoff(){var g=grant();var run=service.start(g,owner);UUID id=UUID.fromString(String.valueOf(run.get("runId")));service.processNext();service.processNext();var before=service.view(id,owner);var draft=CpqOwnerPilotService.rows(before.get("drafts")).getLast();var payload=CpqOwnerPilotService.map(draft.get("payload"));UUID newStory=UUID.randomUUID();when(workflow.persistStoryEvolutionDraft(eq(source),anyString(),anyMap())).thenReturn(Map.of("recordId",newStory.toString(),"result",Map.of("alternatives",List.of(Map.of("candidateId","candidate-1")))));when(workflow.approveStory(eq(newStory),anyMap())).thenReturn(Map.of("storyRecordId",newStory.toString(),"recordId",UUID.randomUUID().toString(),"candidateId","candidate-1","revisionId","candidate-1-revision-x","approvedText",payload.get("text"),"contentFingerprint",payload.get("sourceFingerprint")));var approved=service.approve(id,Map.of("draftId",draft.get("draftId"),"candidateSha256",draft.get("candidateSha256")),owner);assertThat(approved.get("state")).isEqualTo("APPROVED_NEW_SOURCE");assertThat(workflow.getByKind(source,"CREATIVE_ROLE")).isNotNull();when(workflow.creativeRole(anyMap())).thenReturn(Map.of("prompt","new prompt","promptSha256","new"));var report=mock(com.pompomhills.intelligence.quality.QualityReportDto.class);when(report.overallScore()).thenReturn(81.0);when(report.status()).thenReturn("NEEDS_REVISION");when(report.rulesetVersion()).thenReturn("1.11");when(ml.validatePromptForWorkflow(anyString(),eq("1.11"),isNull(),anyMap())).thenReturn(report);var handed=service.handoff(id,Map.of("authorizePromptGeneration",true,"automaticRetries",false,"maxCostUsd",.2),owner);assertThat(handed.get("state")).isEqualTo("PROMPT_HANDOFF_COMPLETE");assertThat(handed.toString()).contains("canonicalEvaluation","promptFingerprint");verify(workflow).creativeRole(anyMap());}
}
