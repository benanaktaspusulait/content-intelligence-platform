package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.character.CanonicalCharacterIdentity;
import com.pompomhills.intelligence.quality.QualityMlClient;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

/** Isolated IDEA assets in the existing append-only event store; never production evidence. */
@Service
public class IdeaExplorationService {
  static final String LABEL = "EXPLORATORY — NOT PRODUCTION APPROVED";
  private final IdeaDraftService drafts;
  private final JdbcClient jdbc;
  private final ObjectMapper json;
  private final QualityMlClient ml;
  private final Path root;
  private final TransactionTemplate tx;

  public IdeaExplorationService(IdeaDraftService drafts, JdbcClient jdbc, ObjectMapper json,
      QualityMlClient ml, PlatformTransactionManager manager,
      @Value("${POMPOM_DATA_ROOT:/data}") String root) {
    this.drafts=drafts; this.jdbc=jdbc; this.json=json; this.ml=ml;
    this.root=Path.of(root).toAbsolutePath().normalize();
    tx=new TransactionTemplate(manager);
    tx.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
  }

  static String opening(Map<String,Object> state, ObjectMapper json) {
    if (state.get("firstFrameDescription") instanceof String s && !s.isBlank()) return s.strip();
    try {
      var value=json.readTree(String.valueOf(state.get("idea")));
      if (value.has("rawProviderConcept")) value=value.get("rawProviderConcept");
      for (var key:List.of("firstStaticFrame","staticFirstFrame","firstFrame"))
        if (value.has(key) && value.get(key).isTextual() && !value.get(key).asText().isBlank())
          return value.get(key).asText();
    } catch (Exception ignored) { /* Free text needs an explicitly saved opening description. */ }
    throw new IllegalArgumentException("Save a first-frame description in this IDEA before exploring");
  }

  public List<Map<String,Object>> list(UUID draft, String workspace) {
    drafts.get(draft,workspace);
    return jdbc.sql("SELECT DISTINCT ON (payload->>'explorationId') payload::text FROM post_family_workflow_events WHERE kind='IDEA_VISUAL_EXPLORATION' AND binding_sha256=:draft ORDER BY payload->>'explorationId',created_at DESC,id DESC")
        .param("draft",draft.toString()).query((rs,i)->read(rs.getString(1))).list().stream()
        .<Map<String,Object>>map(row->{ var out=new LinkedHashMap<>(row); out.put("editorialDecision",latestDecision(String.valueOf(row.get("explorationId")))); return out; }).toList();
  }

  public Map<String,Object> generate(UUID draft, Map<String,Object> input) {
    if (!Boolean.TRUE.equals(input.get("generationAuthorized")))
      throw new IllegalArgumentException("Explicit authorization for one exploratory image is required");
    UUID operation=UUID.fromString(String.valueOf(input.get("explorationId")));
    String workspace=String.valueOf(input.getOrDefault("workspacePath",""));
    drafts.get(draft,workspace);
    String fingerprint=hash(encode(input).getBytes(java.nio.charset.StandardCharsets.UTF_8));
    var claimed=tx.execute(status->{
      jdbc.sql("SELECT pg_advisory_xact_lock(hashtextextended(:id,0))").param("id","idea-exploration:"+operation)
          .query(rs->{rs.next();return 0;});
      var prior=find(draft,operation);
      if (prior.isPresent()) {
        if (!fingerprint.equals(prior.get().get("requestFingerprint")))
          throw new IllegalArgumentException("Exploration identity already belongs to a different request");
        return Map.<String,Object>of("reused",true,"receipt",prior.get());
      }
      var fresh=drafts.get(draft,workspace);
      if (!(input.get("expectedRevision") instanceof Number revision)
          || revision.doubleValue()!=((Number)fresh.get("revision")).doubleValue())
        throw new IllegalStateException("IDEA changed. Reopen and explicitly authorize its saved revision");
      var state=map(fresh.get("state"));
      if (!"IDEA".equals(state.get("inputMode")) || !"IDEA".equals(fresh.get("checkpoint")))
        throw new IllegalArgumentException("Exploration requires a saved IDEA, not a STORY or prompt");
      String frame=opening(state,json);
      if (frame.length()>4000) throw new IllegalArgumentException("First-frame description must be at most 4000 characters");
      if (!(input.get("maxCostUsd") instanceof Number cap) || !Double.isFinite(cap.doubleValue()) || cap.doubleValue()<=0 || cap.doubleValue()>5)
        throw new IllegalArgumentException("A positive exploratory-image cost ceiling up to $5 is required");
      String characterId=String.valueOf(state.getOrDefault("mainCharacterId",""));
      var character=new CanonicalCharacterIdentity(jdbc).requireActive(characterId,null);
      String referenceId=String.valueOf(input.getOrDefault("referenceId",""));
      if (referenceId.isBlank()) throw new IllegalArgumentException("A verified canonical character reference is required");
      var reference=jdbc.sql("SELECT relative_path,sha256,approval_status FROM character_references WHERE id=:reference AND character_id=:character")
          .param("reference",UUID.fromString(referenceId)).param("character",UUID.fromString(characterId))
          .query((rs,i)->Map.of("path",rs.getString(1),"sha256",rs.getString(2),"status",rs.getString(3)))
          .optional().orElseThrow(()->new IllegalArgumentException("Character reference not found"));
      if (!Set.of("VERIFIED","APPROVED").contains(reference.get("status")))
        throw new IllegalArgumentException("Character reference must be verified or approved");
      var file=checkedFile(root.resolve(reference.get("path")),root);
      if (!hash(bytes(file)).equals(reference.get("sha256")))
        throw new IllegalArgumentException("Canonical reference bytes changed; verification is required");
      var request=new LinkedHashMap<String,Object>();
      request.put("draftId",draft.toString()); request.put("ideaRevision",fresh.get("revision"));
      request.put("explorationId",operation.toString());request.put("sourceFirstFrame",frame);
      request.put("contentProfile",state.getOrDefault("profile","AUTO"));
      request.put("characterId",characterId);request.put("characterName",character.get("name"));
      request.put("referenceId",referenceId);request.put("referenceImagePath",file.toString());
      request.put("referenceSha256",reference.get("sha256"));request.put("maxCostUsd",input.get("maxCostUsd"));
      var receipt=new LinkedHashMap<>(request);receipt.put("sourceRequest",request);
      receipt.put("sourceIdeaSha256",hash(String.valueOf(state.get("idea")).getBytes(java.nio.charset.StandardCharsets.UTF_8)));
      receipt.put("requestFingerprint",fingerprint);receipt.put("status","PROVIDER_OUTCOME_UNKNOWN");
      receipt.put("calculatedCostUsd",null);receipt.put("usage",null);isolate(receipt);
      append(receipt,"IDEA_VISUAL_EXPLORATION",draft.toString());
      return Map.<String,Object>of("reused",false,"receipt",receipt,"sourceRequest",request);
    });
    var receipt=new LinkedHashMap<>(map(claimed.get("receipt")));
    if (Boolean.TRUE.equals(claimed.get("reused"))) {receipt.put("reused",true);return receipt;}
    try { receipt.putAll(ml.workflow("idea-exploration/generate",map(claimed.get("sourceRequest")))); }
    catch (RuntimeException error) {
      receipt.put("status","PROVIDER_OUTCOME_UNKNOWN");receipt.put("calculatedCostUsd",null);
      receipt.put("usage",null);receipt.put("error","Image dispatch has no confirmed receipt; no automatic retry");
    }
    isolate(receipt);
    tx.executeWithoutResult(status->append(receipt,"IDEA_VISUAL_EXPLORATION",draft.toString()));
    return receipt;
  }

  public Map<String,Object> decide(UUID draft,UUID exploration,Map<String,Object> input) {
    drafts.get(draft,String.valueOf(input.getOrDefault("workspacePath","")));
    var image=find(draft,exploration).orElseThrow(()->new IllegalArgumentException("Exploration not found"));
    if (!"GENERATED".equals(image.get("status"))) throw new IllegalArgumentException("Inspect a generated image before recording an editorial decision");
    String decision=String.valueOf(input.get("decision"));
    if (!Set.of("PROMISING_HOOK","WEAK_HOOK","NEEDS_VISUAL_REVISION").contains(decision))
      throw new IllegalArgumentException("Unsupported editorial visual decision");
    var row=new LinkedHashMap<String,Object>();row.put("explorationId",exploration.toString());row.put("draftId",draft.toString());
    row.put("ideaRevision",image.get("ideaRevision"));row.put("decision",decision);
    String note=String.valueOf(input.getOrDefault("note",""));if(note.length()>2000) throw new IllegalArgumentException("Editorial note is too long");
    row.put("note",note);isolate(row);tx.executeWithoutResult(status->append(row,"IDEA_VISUAL_DECISION",draft.toString()));return row;
  }

  public Resource image(UUID draft,UUID exploration,String workspace) {
    drafts.get(draft,workspace);
    var row=find(draft,exploration).orElseThrow(()->new IllegalArgumentException("Exploration not found"));
    if (!"GENERATED".equals(row.get("status"))) throw new IllegalArgumentException("No generated exploratory image");
    Path file=checkedFile(Path.of(String.valueOf(row.get("imagePath"))),root.resolve("exploratory-frames").resolve(draft.toString()).resolve(String.valueOf(row.get("ideaRevision"))).resolve(exploration.toString()));
    if (!hash(bytes(file)).equals(row.get("sha256"))) throw new IllegalArgumentException("Exploratory image integrity check failed");
    return new FileSystemResource(file);
  }

  private static void isolate(Map<String,Object> row) {
    row.put("label",LABEL);row.put("firstFrameEligible",false);row.put("renderAuthorized",false);row.put("publishAuthorized",false);
    row.remove("contentId");row.remove("promptVersionId");row.remove("approvalRecordId");
  }
  private Optional<Map<String,Object>> find(UUID draft,UUID exploration) {
    return jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='IDEA_VISUAL_EXPLORATION' AND binding_sha256=:draft AND payload->>'explorationId'=:operation ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("draft",draft.toString()).param("operation",exploration.toString()).query(String.class).optional().map(this::read);
  }
  private Map<String,Object> latestDecision(String exploration) {
    return jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='IDEA_VISUAL_DECISION' AND payload->>'explorationId'=:id ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("id",exploration).query(String.class).optional().map(this::read).orElse(Map.of());
  }
  private void append(Map<String,Object> row,String kind,String binding) {
    row.put("recordId",UUID.randomUUID().toString());row.put("updatedAt",Instant.now().toString());
    jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES(:id,:kind,:binding,CAST(:payload AS jsonb))")
        .param("id",UUID.fromString(String.valueOf(row.get("recordId")))).param("kind",kind).param("binding",binding).param("payload",encode(row)).update();
  }
  private String encode(Object value) {try{return json.writeValueAsString(value);}catch(Exception e){throw new IllegalArgumentException("Invalid exploration data",e);}}
  private Map<String,Object> read(String value) {try{return json.readValue(value,new TypeReference<>(){});}catch(Exception e){throw new IllegalStateException("Invalid exploration receipt",e);}}
  @SuppressWarnings("unchecked") private static Map<String,Object> map(Object value) {return value instanceof Map<?,?>?(Map<String,Object>)value:Map.of();}
  private static Path checkedFile(Path file,Path scope) {try{Path real=file.toRealPath();if(!real.startsWith(scope.toRealPath())||!Files.isRegularFile(real))throw new IllegalArgumentException("Asset outside its storage scope");return real;}catch(java.io.IOException e){throw new IllegalArgumentException("Reference or exploratory image file is missing",e);}}
  private static byte[] bytes(Path file) {try{return Files.readAllBytes(file);}catch(java.io.IOException e){throw new IllegalArgumentException("Cannot read asset",e);}}
  private static String hash(byte[] data) {try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));}catch(Exception e){throw new IllegalStateException(e);}}
}
