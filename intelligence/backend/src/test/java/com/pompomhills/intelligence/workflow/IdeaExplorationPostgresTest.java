package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.video.VideoService;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;

@Testcontainers(disabledWithoutDocker = true)
class IdeaExplorationPostgresTest {
  @Container static final PostgreSQLContainer<?> DB=new PostgreSQLContainer<>("postgres:17-alpine");
  @TempDir Path root;
  static final String CHARACTER="00000000-0000-0000-0000-000000000004";
  static final UUID REFERENCE=UUID.fromString("10000000-0000-0000-0000-000000000001");
  JdbcClient jdbc; IdeaDraftService drafts; IdeaExplorationService service; QualityMlClient ml;
  TransactionTemplate tx; UUID draft;
  @BeforeEach void setup() throws Exception {
    var ds=new DriverManagerDataSource(DB.getJdbcUrl(),DB.getUsername(),DB.getPassword());
    jdbc=JdbcClient.create(ds);var manager=new DataSourceTransactionManager(ds);tx=new TransactionTemplate(manager);
    for(var table:List.of("post_family_workflow_events","character_references","characters")) jdbc.sql("DROP TABLE IF EXISTS "+table).update();
    jdbc.sql("CREATE TABLE post_family_workflow_events(id uuid PRIMARY KEY,kind varchar(40),binding_sha256 varchar(128),payload jsonb,created_at timestamptz DEFAULT now())").update();
    jdbc.sql("CREATE TABLE characters(id uuid PRIMARY KEY,name text,status text,notes text,active boolean)").update();
    jdbc.sql("CREATE TABLE character_references(id uuid PRIMARY KEY,character_id uuid,relative_path text,sha256 text,approval_status text)").update();
    jdbc.sql("INSERT INTO characters VALUES(:id,'Arda','UNTESTED','Test fixture',true)").param("id",UUID.fromString(CHARACTER)).update();
    Files.writeString(root.resolve("reference.png"),"TEST_REFERENCE_NOT_REAL");
    jdbc.sql("INSERT INTO character_references VALUES(:id,:character,'reference.png',:sha,'VERIFIED')")
        .param("id",REFERENCE).param("character",UUID.fromString(CHARACTER)).param("sha",sha(Files.readAllBytes(root.resolve("reference.png")))).update();
    drafts=new IdeaDraftService(jdbc,new ObjectMapper(),mock(VideoService.class),mock(ContentWorkspaceController.class));
    ml=mock(QualityMlClient.class);service=new IdeaExplorationService(drafts,jdbc,new ObjectMapper(),ml,manager,root.toString());
    draft=UUID.randomUUID();save(0,"Small Arda beside a huge prepared picnic blanket, one strawberry at its opposite end.");
  }
  void save(int revision,String opening) {
    tx.execute(status->drafts.save(Map.of("draftId",draft.toString(),"expectedRevision",revision,"state",Map.of(
        "inputMode","IDEA","idea","Original test IDEA","workspacePath","library/work","mainCharacterId",CHARACTER,
        "profile","CURIOSITY_ADVENTURE","firstFrameDescription",opening))));
  }
  Map<String,Object> request(){return new LinkedHashMap<>(Map.of("explorationId",UUID.randomUUID().toString(),"workspacePath","library/work","expectedRevision",1,"referenceId",REFERENCE.toString(),"generationAuthorized",true,"maxCostUsd",.1));}
  void generated() {
    when(ml.workflow(eq("idea-exploration/generate"),anyMap())).thenAnswer(call->{
      Map<String,Object> in=call.getArgument(1);Path dir=root.resolve("exploratory-frames").resolve(draft.toString()).resolve("1").resolve(String.valueOf(in.get("explorationId")));Files.createDirectories(dir);
      Path image=dir.resolve("TEST_GENERATED_ASSET.png");Files.writeString(image,"TEST_IMAGE_BYTES_NOT_REAL");
      return Map.of("status","GENERATED","imagePath",image.toString(),"sha256",sha(Files.readAllBytes(image)),"model","gpt-image-2","calculatedCostUsd",.053,"firstFrameEligible",true,"renderAuthorized",true);
    });
  }
  @Test void savedIdeaGeneratesAndRetrievesExactRevisionWithoutAnyStoryOrProductionIds() throws Exception {
    generated();var input=request();var result=service.generate(draft,input);
    assertThat(result).containsEntry("ideaRevision",1).containsEntry("label",IdeaExplorationService.LABEL)
        .containsEntry("firstFrameEligible",false).containsEntry("renderAuthorized",false).containsEntry("publishAuthorized",false)
        .doesNotContainKeys("contentId","promptVersionId","approvalRecordId");
    var rows=service.list(draft,"library/work");assertThat(rows).hasSize(1);
    assertThat(rows.getFirst().get("sourceFirstFrame")).isEqualTo("Small Arda beside a huge prepared picnic blanket, one strawberry at its opposite end.");
    assertThat(service.image(draft,UUID.fromString((String)input.get("explorationId")),"library/work").getContentAsByteArray()).isEqualTo("TEST_IMAGE_BYTES_NOT_REAL".getBytes());
    verify(ml,times(1)).workflow(eq("idea-exploration/generate"),anyMap());
  }
  @Test void duplicateOperationNeverRegeneratesEvenAfterSourceChanges() {
    generated();var input=request();service.generate(draft,input);save(1,"A revised opening");
    assertThat(service.generate(draft,input)).containsEntry("reused",true).containsEntry("ideaRevision",1);
    verify(ml,times(1)).workflow(anyString(),anyMap());
    var changed=new LinkedHashMap<>(input);changed.put("expectedRevision",2);
    assertThatThrownBy(()->service.generate(draft,changed)).hasMessageContaining("different request");
  }
  @Test void staleRevisionOrMissingConsentCannotDispatch() {
    var input=request();input.put("expectedRevision",2);
    assertThatThrownBy(()->service.generate(draft,input)).hasMessageContaining("IDEA changed");
    input.put("generationAuthorized",false);
    assertThatThrownBy(()->service.generate(draft,input)).hasMessageContaining("authorization");
    verifyNoInteractions(ml);
  }
  @Test void missingUnverifiedOrChangedReferenceFailsBeforeDispatch() throws Exception {
    var input=request();input.put("referenceId","");assertThatThrownBy(()->service.generate(draft,input)).hasMessageContaining("verified canonical");
    input.put("referenceId",REFERENCE.toString());jdbc.sql("UPDATE character_references SET approval_status='PENDING'").update();
    assertThatThrownBy(()->service.generate(draft,input)).hasMessageContaining("verified or approved");
    jdbc.sql("UPDATE character_references SET approval_status='VERIFIED'").update();Files.writeString(root.resolve("reference.png"),"CHANGED");
    assertThatThrownBy(()->service.generate(draft,input)).hasMessageContaining("bytes changed");verifyNoInteractions(ml);
  }
  @Test void providerTransportFailureIsDurableUnknownCostAndCannotAutomaticallyRetry() {
    when(ml.workflow(anyString(),anyMap())).thenThrow(new IllegalStateException("Connection lost"));var input=request();
    assertThat(service.generate(draft,input)).containsEntry("status","PROVIDER_OUTCOME_UNKNOWN").containsEntry("calculatedCostUsd",null);
    assertThat(service.generate(draft,input)).containsEntry("reused",true).containsEntry("calculatedCostUsd",null);
    verify(ml,times(1)).workflow(anyString(),anyMap());
  }
  @Test void promisingEditorialDecisionCannotChangeOfficialEvidenceOrSavedIdea() {
    generated();var before=drafts.get(draft,"library/work");var input=request();service.generate(draft,input);
    var decision=service.decide(draft,UUID.fromString((String)input.get("explorationId")),Map.of("workspacePath","library/work","decision","PROMISING_HOOK"));
    assertThat(decision).containsEntry("firstFrameEligible",false).containsEntry("renderAuthorized",false).containsEntry("publishAuthorized",false);
    assertThat(drafts.get(draft,"library/work")).isEqualTo(before);
    assertThat(service.list(draft,"library/work").getFirst().get("editorialDecision")).isNotNull();
    var official=new WorkflowService(null,null,null,null,new ObjectMapper(),null,null);
    assertThatThrownBy(()->official.generateStartFrame(Map.of("contentId",1,"promptVersionId",1,"prompt","Scene","maxCostUsd",.1,"firstFrameEligible",true)))
        .hasMessageContaining("Canonical story validation is unavailable");
    assertThat(jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind NOT IN ('CREATIVE_STUDIO_SESSION','IDEA_VISUAL_EXPLORATION','IDEA_VISUAL_DECISION')").query(Long.class).single()).isZero();
  }
  @Test void arbitraryApprovalDecisionsAndWrongWorkspaceAreRejected() {
    generated();var input=request();service.generate(draft,input);UUID op=UUID.fromString((String)input.get("explorationId"));
    assertThatThrownBy(()->service.decide(draft,op,Map.of("workspacePath","library/work","decision","APPROVED"))).hasMessageContaining("Unsupported editorial");
    assertThatThrownBy(()->service.list(draft,"other/work")).hasMessageContaining("different workspace");
  }
  static String sha(byte[] bytes)throws Exception{return HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes));}
}
