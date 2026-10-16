package com.pompomhills.intelligence.workflow;

import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.quality.QualityReportDto;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import com.pompomhills.intelligence.quality.IntelligenceQualityValidationService;
import jakarta.servlet.http.HttpServletRequest;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import static com.pompomhills.intelligence.workflow.CpqOwnerPilotService.*;
import static org.springframework.http.HttpStatus.*;

/** Bounded, durable story evolution.  Prompt optimization remains a separate grant. */
@Service
public class StoryEvolutionService {
  final JdbcClient db; final CpqOwnerPilotService util; final WorkflowService workflow; final QualityMlClient ml;
  @org.springframework.beans.factory.annotation.Autowired(required=false) ContentWorkspaceController contentWorkspace;
  @org.springframework.beans.factory.annotation.Autowired(required=false) IntelligenceQualityValidationService validation;
  @Value("${pompom.cpq-pilot.real-enabled:false}") boolean realEnabled;
  public StoryEvolutionService(JdbcClient db,CpqOwnerPilotService util,WorkflowService workflow,QualityMlClient ml){this.db=db;this.util=util;this.workflow=workflow;this.ml=ml;}
  static int integer(Map<String,Object> b,String k,int min,int max){Object v=b.get(k);if(!(v instanceof Number n)||n.intValue()!=n.doubleValue()||n.intValue()<min||n.intValue()>max)throw new ResponseStatusException(BAD_REQUEST,"Invalid limit: "+k);return n.intValue();}
  static double amount(Object v){if(!(v instanceof Number n)||!Double.isFinite(n.doubleValue())||n.doubleValue()<=0||n.doubleValue()>20)throw new ResponseStatusException(BAD_REQUEST,"Positive story-evolution USD ceiling <=20 required");return n.doubleValue();}
  Map<String,Object> load(UUID id){return db.sql("SELECT owner_principal,source_story_record_id,source_story_sha256,authorization_payload::text,scope::text,state,progress::text,cancel_requested,deadline FROM story_evolution_runs WHERE id=:id").param("id",id).query((rs,n)->Map.<String,Object>of("owner",rs.getString(1),"sourceStoryRecordId",rs.getObject(2,UUID.class),"sourceStorySha256",rs.getString(3),"authorization",util.read(rs.getString(4)),"scope",util.read(rs.getString(5)),"state",rs.getString(6),"progress",util.read(rs.getString(7)),"cancel",rs.getBoolean(8),"deadline",rs.getTimestamp(9).toInstant())).single();}
  void owner(UUID id,HttpServletRequest req){if(!util.owner(req).equals(load(id).get("owner")))throw new ResponseStatusException(FORBIDDEN,"Run belongs to another owner");}
  @Transactional public Map<String,Object> start(Map<String,Object> body,HttpServletRequest req){
    String owner=util.owner(req); if(!realEnabled)throw new ResponseStatusException(FORBIDDEN,"Story evolution real dispatch remains disabled; no run authorized");
    UUID source=uuid(body.get("sourceStoryRecordId")); var story=workflow.getByKind(source,"CREATIVE_ROLE");
    if(!"STORY".equals(story.get("role")))throw new ResponseStatusException(BAD_REQUEST,"Exact STORY record required");
    String text=String.valueOf(map(story.get("sourceRequest")).getOrDefault("text","")); if(text.isBlank())throw new ResponseStatusException(BAD_REQUEST,"Source story text required");
    int rounds=integer(body,"maxRounds",1,3), requests=integer(body,"maxRequests",2,9); double budget=amount(body.get("maxTotalUsd"));
    if(!Boolean.TRUE.equals(body.get("authorizePaidInference"))||!Boolean.TRUE.equals(body.get("confirmSourceAuthority"))||!Boolean.FALSE.equals(body.get("automaticRetries")))throw new ResponseStatusException(BAD_REQUEST,"Bounded story authorization and retries-disabled confirmation required");
    String key=String.valueOf(body.getOrDefault("idempotencyKey",""));if(key.length()<8)throw new ResponseStatusException(BAD_REQUEST,"Stable idempotency key required");
    var prior=db.sql("SELECT id FROM story_evolution_runs WHERE owner_principal=:o AND idempotency_key=:k").param("o",owner).param("k",key).query(UUID.class).optional();if(prior.isPresent())return view(prior.get(),req);
    var scope=new LinkedHashMap<String,Object>();scope.put("sourceStoryRecordId",source.toString());scope.put("sourceStory",text);scope.put("sourceStorySha256",hash(text));scope.put("objective",body.getOrDefault("objective","Improve visual hook, causal progression, escalation and payoff"));scope.put("profile",body.getOrDefault("profile",Map.of()));scope.put("contractVersion","STORY_EVOLUTION_V1");
    UUID id=UUID.randomUUID();var progress=new LinkedHashMap<String,Object>();progress.put("phase","DIAGNOSIS");progress.put("round",0);progress.put("bestDraftId","");progress.put("acceptedChanges",List.of());progress.put("rejectedCandidates",List.of());
    db.sql("INSERT INTO story_evolution_runs(id,owner_principal,idempotency_key,source_story_record_id,source_story_sha256,authorization_payload,scope,state,progress,deadline) VALUES(:id,:o,:k,:s,:h,CAST(:a AS jsonb),CAST(:scope AS jsonb),'READY',CAST(:p AS jsonb),now()+make_interval(secs=>:sec))").param("id",id).param("o",owner).param("k",key).param("s",source).param("h",hash(text)).param("a",util.encode(body)).param("scope",util.encode(scope)).param("p",util.encode(progress)).param("sec",Math.max(60,Math.min(1800,((Number)body.getOrDefault("maxRunSeconds",600)).intValue()))).update();event(id,Map.of("state","AUTHORIZED","providerCalls",0));return view(id,req);
  }
  @Scheduled(fixedDelayString="${pompom.story-evolution.poll-delay-ms:2000}") public void processNext(){var id=db.sql("SELECT id FROM story_evolution_runs WHERE state='READY' AND cancel_requested=false AND deadline>now() ORDER BY created_at LIMIT 1").query(UUID.class).optional();id.ifPresent(x->{try{step(x);}catch(Exception e){stop(x,"PROVIDER_FAILED_OR_AMBIGUOUS",e.getMessage());}});}
  @Transactional void step(UUID id){
    var row=load(id); var scope=map(row.get("scope")); var p=new LinkedHashMap<>(map(row.get("progress")));
    if(Boolean.TRUE.equals(row.get("cancel"))){stop(id,"CANCELLED","");return;}
    int round=((Number)p.get("round")).intValue()+1; int max=((Number)map(row.get("authorization")).getOrDefault("maxRounds",1)).intValue();
    if(round>max){stop(id,"ROUND_LIMIT_REACHED","");return;}
    p.put("round",round); p.put("phase","GENERATING"); setRunning(id,p);
    var context=new LinkedHashMap<String,Object>();
    context.put("inputMode","DETAILED_STORY"); context.put("storyGenerationMode","IMPROVE_EXISTING_STORY");
    context.put("approvedStoryText",scope.get("sourceStory")); context.put("sourceStoryRecordId",scope.get("sourceStoryRecordId")); context.put("sourceFingerprint",scope.get("sourceStorySha256"));
    context.put("lockedRequirements",List.of("PRESERVE_CORE_PREMISE","PRESERVE_KEY_EVENTS","PRESERVE_ENDING")); context.put("objective",scope.get("objective"));
    context.put("previousRevision",p.get("bestDraftId")); context.put("bestCandidate",p.getOrDefault("bestCandidate",Map.of())); context.put("rejectedCandidates",p.getOrDefault("rejectedCandidates",List.of()));
    context.put("acceptedChanges",p.getOrDefault("acceptedChanges",List.of())); context.put("previousAssessment",p.getOrDefault("lastAssessment",Map.of())); context.put("requestedAlternativeCount",2);
    var request=new LinkedHashMap<String,Object>(); request.put("role","STORY"); request.put("text",scope.get("sourceStory")); request.put("maxCostUsd",((Number)map(row.get("authorization")).get("maxTotalUsd")).doubleValue()); request.put("context",context);
    var generated=ml.workflow("creative-role",request); var alternatives=rows(generated.get("alternatives"));
    if(alternatives.isEmpty()){stop(id,"STORY_VALIDATION_FAILED","No complete story candidate returned");return;}
    var rejected=new ArrayList<Map<String,Object>>(rows(p.getOrDefault("rejectedCandidates",List.of()))); var valid=new ArrayList<Map<String,Object>>();
    String baseline=String.valueOf(scope.get("sourceStory")); String parent=String.valueOf(map(p.getOrDefault("bestCandidate",Map.of())).getOrDefault("text",baseline));
    for(var candidate:alternatives){String text=String.valueOf(candidate.getOrDefault("text",""));String cid=String.valueOf(candidate.getOrDefault("candidateId","candidate-"+(valid.size()+1)));
      if(text.isBlank()||text.equals(baseline)||text.equals(parent)){rejected.add(Map.of("candidateId",cid,"reason","EQUIVALENT_OR_MEANINGLESS"));continue;} valid.add(candidate);}
    if(valid.isEmpty()){p.put("rejectedCandidates",rejected);saveProgress(id,p,"NO_JUSTIFIED_IMPROVEMENT");return;}
    var reviewContext=new LinkedHashMap<String,Object>();reviewContext.put("sourceRequestId",id.toString());reviewContext.put("sourceFingerprint",scope.get("sourceStorySha256"));reviewContext.put("approvedStoryText",baseline);reviewContext.put("candidates",valid);reviewContext.put("reviewPolicyVersion","story-evolution-v1");
    var reviewRequest=new LinkedHashMap<String,Object>();reviewRequest.put("role","STORY_REVIEW");reviewRequest.put("text",baseline);reviewRequest.put("maxCostUsd",((Number)map(row.get("authorization")).get("maxTotalUsd")).doubleValue());reviewRequest.put("context",reviewContext);
    var review=ml.workflow("creative-role",reviewRequest); p.put("lastAssessment",review); p.put("rejectedCandidates",rejected);
    String recommended=String.valueOf(review.getOrDefault("recommendedCandidateId","")); Map<String,Object> chosen=valid.stream().filter(c->recommended.equals(String.valueOf(c.get("candidateId")))).findFirst().orElse(valid.getFirst());
    String chosenText=String.valueOf(chosen.get("text")); String cid=String.valueOf(chosen.getOrDefault("candidateId","candidate-"+round));
    UUID draft=UUID.randomUUID(); var payload=new LinkedHashMap<>(chosen); payload.put("parentStoryRecordId",scope.get("sourceStoryRecordId")); payload.put("parentDraftId",p.get("bestDraftId")); payload.put("sourceFingerprint",scope.get("sourceStorySha256")); payload.put("round",round); payload.put("changes",List.of("Provider-authored story change assessed by independent STORY_REVIEW")); payload.put("review",review);
    db.sql("INSERT INTO story_evolution_drafts(id,run_id,round_number,parent_draft_id,candidate_id,prompt_payload,candidate_sha256,assessment) VALUES(:id,:run,:r,CAST(NULLIF(:parent,'') AS uuid),:cid,CAST(:payload AS jsonb),:hash,CAST(:assessment AS jsonb))").param("id",draft).param("run",id).param("r",round).param("parent",String.valueOf(p.get("bestDraftId"))).param("cid",cid).param("payload",util.encode(payload)).param("hash",hash(chosenText)).param("assessment",util.encode(review)).update();
    p.put("bestDraftId",draft.toString()); p.put("bestCandidate",payload); p.put("acceptedChanges",List.of("round "+round+": "+String.valueOf(review.getOrDefault("recommendationReason","independent review supported candidate"))));
    int used=((Number)p.getOrDefault("providerCalls",0)).intValue()+2; p.put("providerCalls",used);
    if(round<max){p.put("phase","GENERATING");db.sql("UPDATE story_evolution_runs SET state='READY',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","ROUND_RETAINED","round",round,"draftId",draft.toString(),"providerCalls",used));}
    else {p.put("phase","AWAITING_OWNER_STORY_APPROVAL");p.put("reason","AWAITING_OWNER_STORY_APPROVAL");db.sql("UPDATE story_evolution_runs SET state='AWAITING_OWNER_STORY_APPROVAL',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","AWAITING_OWNER_STORY_APPROVAL","round",round,"draftId",draft.toString(),"providerCalls",used));}
  }
  @Transactional public Map<String,Object> approve(UUID id,Map<String,Object> body,HttpServletRequest req){owner(id,req);var row=load(id);if(!"AWAITING_OWNER_STORY_APPROVAL".equals(row.get("state")))throw new ResponseStatusException(CONFLICT,"No story candidate awaits approval");var p=map(row.get("progress"));UUID draft=uuid(body.get("draftId"));if(!draft.toString().equals(p.get("bestDraftId")))throw new ResponseStatusException(CONFLICT,"Exact current story draft required");var d=db.sql("SELECT candidate_id,prompt_payload::text,candidate_sha256 FROM story_evolution_drafts WHERE id=:id AND run_id=:run").param("id",draft).param("run",id).query((rs,n)->Map.of("candidateId",rs.getString(1),"payload",util.read(rs.getString(2)),"sha256",rs.getString(3))).single();if(!Objects.equals(d.get("sha256"),body.get("candidateSha256")))throw new ResponseStatusException(CONFLICT,"Stale story fingerprint");String text=String.valueOf(map(d.get("payload")).get("text"));var newStory=workflow.persistStoryEvolutionDraft(uuid(row.get("sourceStoryRecordId")),text,map(d.get("payload")));String cid=String.valueOf(map(newStory.get("result")).get("alternatives") instanceof List<?> l && !l.isEmpty()?map(l.getFirst()).get("candidateId"):"candidate-1");String revision=cid+"-revision-"+hash(text);var approval=workflow.approveStory(uuid(String.valueOf(newStory.get("recordId"))),Map.of("approvedText",text,"candidateId",cid,"revisionId",revision,"contentFingerprint",hash(text),"sourceType","AUTONOMOUS_STORY_EVOLUTION"));p.put("approval",approval);p.put("phase","APPROVED_NEW_SOURCE");db.sql("UPDATE story_evolution_runs SET state='APPROVED_NEW_SOURCE',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","OWNER_STORY_APPROVED","newStoryRecordId",newStory.get("recordId")));return view(id,req);
  }
  public Map<String,Object> view(UUID id,HttpServletRequest req){owner(id,req);var r=load(id);var out=new LinkedHashMap<>(r);out.put("runId",id.toString());out.put("drafts",db.sql("SELECT id,round_number,candidate_id,prompt_payload::text, candidate_sha256 FROM story_evolution_drafts WHERE run_id=:id ORDER BY round_number").param("id",id).query((rs,n)->Map.of("draftId",rs.getString(1),"round",rs.getInt(2),"candidateId",rs.getString(3),"payload",util.read(rs.getString(4)),"candidateSha256",rs.getString(5))).list());out.put("events",db.sql("SELECT payload::text FROM story_evolution_events WHERE run_id=:id ORDER BY created_at,id").param("id",id).query((rs,n)->util.read(rs.getString(1))).list());out.remove("owner");return out;}
  @Transactional
  public Map<String,Object> handoff(UUID id, Map<String,Object> body, HttpServletRequest req) {
    owner(id, req);
    var row = load(id);
    if (!"APPROVED_NEW_SOURCE".equals(row.get("state")))
      throw new ResponseStatusException(CONFLICT, "Owner story approval is required before prompt handoff");
    if (!realEnabled)
      throw new ResponseStatusException(FORBIDDEN, "Prompt handoff provider dispatch remains disabled");
    if (!Boolean.TRUE.equals(body.get("authorizePromptGeneration"))
        || !Boolean.FALSE.equals(body.get("automaticRetries")))
      throw new ResponseStatusException(BAD_REQUEST, "Separate prompt-generation authorization and retries-disabled confirmation required");
    var progress = map(row.get("progress"));
    var approval = map(progress.get("approval"));
    UUID newStory = uuid(approval.get("storyRecordId"));
    String storyText = String.valueOf(approval.get("approvedText"));
    var context = new LinkedHashMap<String,Object>();
    context.put("sourceStoryRecordId", newStory.toString());
    context.put("candidateId", approval.get("candidateId"));
    context.put("storyRevisionId", approval.get("revisionId"));
    context.put("approvalRecordId", approval.get("recordId"));
    context.put("sourceFingerprint", approval.get("contentFingerprint"));
    context.put("contentProfile", body.getOrDefault("contentProfile", "ABSURD_PHYSICS"));
    context.put("generator", body.getOrDefault("generator", "SEEDANCE_2_0_MINI"));
    context.put("desiredDuration", body.getOrDefault("desiredDuration", 15));
    context.put("openingStrategy", body.getOrDefault("openingStrategy", "AUTO"));
    context.put("settings", body.getOrDefault("settings", Map.of("aspectRatio", "9:16", "mode", "image2video", "resolution", "480p")));
    var request = new LinkedHashMap<String,Object>();
    request.put("role", "BUILD_PROMPT");
    request.put("text", storyText);
    request.put("maxCostUsd", amount(body.get("maxCostUsd")));
    request.put("context", context);
    var built = new LinkedHashMap<>(workflow.creativeRole(request));
    String prompt = String.valueOf(built.getOrDefault("prompt", ""));
    if (prompt.isBlank()) throw new ResponseStatusException(CONFLICT, "BUILD_PROMPT returned no complete prompt");
    var evaluation = ml.validatePromptForWorkflow(prompt, "1.11", null, context);
    if (evaluation == null) throw new ResponseStatusException(CONFLICT, "Ruleset 1.11 evaluation returned no report");
    var canonical = canonical(evaluation);
    built.put("promptFingerprint", hash(prompt));
    built.put("sourceStoryRecordId", newStory.toString());
    built.put("sourceStoryFingerprint", approval.get("contentFingerprint"));
    built.put("canonicalEvaluation", canonical);

    // A real handoff must create the normal prompt-version and REVIEW records.
    // These fields are deliberately required for production handoff; omitting them
    // keeps the service-only test path from mutating application data.
    if (body.get("contentId") instanceof Number contentNumber
        && body.get("parentPromptVersionId") instanceof Number parentNumber) {
      if (contentWorkspace == null || validation == null)
        throw new ResponseStatusException(CONFLICT, "Prompt persistence services are unavailable");
      Long contentId = contentNumber.longValue();
      Long parentPrompt = parentNumber.longValue();
      var created = contentWorkspace.createPrompt(contentId,
          new ContentWorkspaceController.CreatePromptRequest(
              prompt, null, parentPrompt, String.valueOf(built.get("recordId"))));
      Long promptId = created.id();
      var bound = new LinkedHashMap<String,Object>(context);
      bound.put("prompt", prompt);
      bound.put("contentId", contentId);
      bound.put("promptVersionId", promptId);
      bound.put("settings", context.get("settings"));
      var reviewOptions = new LinkedHashMap<String,Object>(bound);
      reviewOptions.put("profile", "post-family-v1");
      var review = workflow.runReview(new WorkflowService.ReviewRequest(contentId, promptId, prompt, null, reviewOptions), true);
      UUID analysisId = uuid(review.get("recordId"));
      var persisted = validation.validateWorkflowProfile(Map.of(
          "contentId", contentId, "promptVersionId", promptId, "boundRequest", bound));
      var preflight = workflow.adaptiveOptimizationPreflight(analysisId);
      built.put("newPromptId", promptId);
      built.put("newPromptVersion", created.versionNumber());
      built.put("analysisId", analysisId.toString());
      built.put("qualityValidationId", persisted.validationRecordId());
      built.put("optimizationPreflightState", preflight);
      built.put("review", review);
    } else {
      built.put("persistenceStatus", "REQUIRES_CONTENT_AND_PARENT_PROMPT_BINDING");
    }
    progress.put("promptHandoff", built);
    progress.put("phase", "PROMPT_HANDOFF_COMPLETE");
    progress.put("newPromptFingerprint", hash(prompt));
    progress.put("canonicalEvaluation", canonical);
    db.sql("UPDATE story_evolution_runs SET state='PROMPT_HANDOFF_COMPLETE',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id")
        .param("p", util.encode(progress)).param("id", id).update();
    event(id, Map.of("state", "PROMPT_HANDOFF_COMPLETE", "newStoryRecordId", newStory.toString(),
        "promptFingerprint", hash(prompt), "rulesetVersion", evaluation.rulesetVersion()));
    return view(id, req);
  }
  Map<String,Object> canonical(QualityReportDto evaluation) {
    var out = new LinkedHashMap<String,Object>();
    out.put("overallScore", evaluation.overallScore()); out.put("status", evaluation.status());
    out.put("rulesetVersion", evaluation.rulesetVersion()); out.put("blockerCount", evaluation.blockerCount());
    out.put("criticalCount", evaluation.criticalCount()); out.put("warningCount", evaluation.warningCount());
    out.put("failedRules", evaluation.failedRules()); out.put("unknownRules", evaluation.unknownRules());
    out.put("parserConfidence", evaluation.parserConfidence()); out.put("parserWarnings", evaluation.parserWarnings());
    out.put("videoPlanIr", evaluation.videoPlanIr()); return out;
  }
  public Map<String,Object> latest(UUID source,HttpServletRequest req){String owner=util.owner(req);return db.sql("SELECT id FROM story_evolution_runs WHERE owner_principal=:o AND source_story_record_id=:s ORDER BY created_at DESC LIMIT 1").param("o",owner).param("s",source).query(UUID.class).optional().map(id->view(id,req)).orElse(Map.of());}
  public Map<String,Object> stop(UUID id,String reason,String detail){var p=map(load(id).get("progress"));p.put("reason",reason);if(detail!=null&&!detail.isBlank())p.put("detail",detail);db.sql("UPDATE story_evolution_runs SET state='STOPPED',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id AND state NOT IN ('APPROVED_NEW_SOURCE','STOPPED')").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","STOPPED","reason",reason));return p;}
  void setRunning(UUID id,Map<String,Object> p){db.sql("UPDATE story_evolution_runs SET state='RUNNING',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id AND state='READY'").param("p",util.encode(p)).param("id",id).update();}
  void saveProgress(UUID id,Map<String,Object> p,String reason){p.put("reason",reason);db.sql("UPDATE story_evolution_runs SET state='STOPPED',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","STOPPED","reason",reason));}
  void event(UUID id,Map<String,Object> p){db.sql("INSERT INTO story_evolution_events(id,run_id,payload) VALUES(:e,:r,CAST(:p AS jsonb))").param("e",UUID.randomUUID()).param("r",id).param("p",util.encode(p)).update();}
}
