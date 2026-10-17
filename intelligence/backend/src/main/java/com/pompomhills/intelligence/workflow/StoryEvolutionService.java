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
  static final String PILOT="REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1";
  static final String ASSESSMENT="ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1";
  @Value("${pompom.cpq-story-assessment.evidence-root:}") String assessmentEvidenceRoot="";
  @org.springframework.beans.factory.annotation.Autowired(required=false)
  org.springframework.transaction.PlatformTransactionManager transactionManager;
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
    if(ASSESSMENT.equals(body.get("assessmentOnlyPolicy")))return startAssessment(body,req);
    if(body.containsKey("assessmentOnlyPolicy"))throw new ResponseStatusException(BAD_REQUEST,"Unsupported assessment policy");
    if(PILOT.equals(body.get("experimentVersion")))return startPilot(body,req);
    if(body.containsKey("experimentVersion"))throw new ResponseStatusException(BAD_REQUEST,"Unsupported experiment contract");
    String owner=util.owner(req); if(!realEnabled)throw new ResponseStatusException(FORBIDDEN,"Story evolution real dispatch remains disabled; no run authorized");
    UUID source=uuid(body.get("sourceStoryRecordId")); var story=workflow.getByKind(source,"CREATIVE_ROLE");
    if(!"STORY".equals(story.get("role")))throw new ResponseStatusException(BAD_REQUEST,"Exact STORY record required");
    UUID sourceApproval = body.get("approvalRecordId") != null ? uuid(body.get("approvalRecordId")) :
        db.sql("SELECT id FROM post_family_workflow_events WHERE kind='STORY_APPROVAL' AND payload->>'storyRecordId'=:story ORDER BY created_at DESC,id DESC LIMIT 1")
          .param("story",source.toString()).query(UUID.class).optional().orElseThrow(() -> new ResponseStatusException(CONFLICT,"Current approved source story required"));
    var approvedSource=workflow.approvedStoryForCpq(source,sourceApproval);
    String text=String.valueOf(approvedSource.get("text")); if(text.isBlank())throw new ResponseStatusException(BAD_REQUEST,"Source story text required");
    int rounds=integer(body,"maxRounds",1,3), requests=integer(body,"maxRequests",2,9); double budget=amount(body.get("maxTotalUsd")); if(requests<rounds*2)throw new ResponseStatusException(BAD_REQUEST,"Each story round requires generation plus independent review");
    if(!Boolean.TRUE.equals(body.get("authorizePaidInference"))||!Boolean.TRUE.equals(body.get("confirmSourceAuthority"))||!Boolean.FALSE.equals(body.get("automaticRetries")))throw new ResponseStatusException(BAD_REQUEST,"Bounded story authorization and retries-disabled confirmation required");
    String key=String.valueOf(body.getOrDefault("idempotencyKey",""));if(key.length()<8)throw new ResponseStatusException(BAD_REQUEST,"Stable idempotency key required");
    var prior=db.sql("SELECT id FROM story_evolution_runs WHERE owner_principal=:o AND idempotency_key=:k").param("o",owner).param("k",key).query(UUID.class).optional();if(prior.isPresent())return view(prior.get(),req);
    var scope=new LinkedHashMap<String,Object>();scope.put("sourceStoryRecordId",source.toString());scope.put("sourceStory",text);scope.put("sourceApprovalRecordId",sourceApproval.toString());scope.put("sourceRevisionId",approvedSource.get("revision"));scope.put("sourceStorySha256",hash(text));scope.put("objective",body.getOrDefault("objective","Improve visual hook, causal progression, escalation and payoff"));scope.put("profile",body.getOrDefault("profile",Map.of()));scope.put("contractVersion","STORY_EVOLUTION_V1");
    if(body.get("baselineAnalysisId")!=null){
      UUID analysis=uuid(body.get("baselineAnalysisId"));
      scope.put("baselineAnalysisId",analysis.toString());
      scope.put("canonicalStoryFeasibilityContext",canonicalStoryFeasibilityContext(source,sourceApproval,approvedSource,text,analysis));
      scope.put("contractVersion","CANONICAL_A_AWARE_STORY_EVOLUTION_V1");
    }
    UUID id=UUID.randomUUID();var progress=new LinkedHashMap<String,Object>();progress.put("phase","DIAGNOSIS");progress.put("round",0);progress.put("bestDraftId","");progress.put("acceptedChanges",List.of());progress.put("rejectedCandidates",List.of());
    db.sql("INSERT INTO story_evolution_runs(id,owner_principal,idempotency_key,source_story_record_id,source_story_sha256,authorization_payload,scope,state,progress,deadline) VALUES(:id,:o,:k,:s,:h,CAST(:a AS jsonb),CAST(:scope AS jsonb),'READY',CAST(:p AS jsonb),now()+make_interval(secs=>:sec))").param("id",id).param("o",owner).param("k",key).param("s",source).param("h",hash(text)).param("a",util.encode(body)).param("scope",util.encode(scope)).param("p",util.encode(progress)).param("sec",Math.max(60,Math.min(1800,((Number)body.getOrDefault("maxRunSeconds",600)).intValue()))).update();event(id,Map.of("state","AUTHORIZED","providerCalls",0));return view(id,req);
  }
  @Scheduled(fixedDelayString="${pompom.story-evolution.poll-delay-ms:2000}") public void processNext(){var id=db.sql("SELECT id FROM story_evolution_runs WHERE state='READY' AND cancel_requested=false AND deadline>now() ORDER BY created_at LIMIT 1").query(UUID.class).optional();id.ifPresent(x->{try{step(x);}catch(Exception e){stop(x,"PROVIDER_FAILED_OR_AMBIGUOUS",e.getMessage());}});}
  @Transactional void step(UUID id){
    var row=load(id); var scope=map(row.get("scope")); var p=new LinkedHashMap<>(map(row.get("progress")));
    if(ASSESSMENT.equals(scope.get("assessmentOnlyPolicy"))){stepAssessment(id,row,scope,p);return;}
    if(PILOT.equals(scope.get("experimentVersion"))){stepPilot(id,row,scope,p);return;}
    if(Boolean.TRUE.equals(row.get("cancel"))){stop(id,"CANCELLED","");return;}
    int round=((Number)p.get("round")).intValue()+1; int max=((Number)map(row.get("authorization")).getOrDefault("maxRounds",1)).intValue();
    if(round>max){stop(id,"ROUND_LIMIT_REACHED","");return;}
    p.put("round",round); p.put("phase","GENERATING"); setRunning(id,p);
    var context=new LinkedHashMap<String,Object>();
    context.put("inputMode","DETAILED_STORY"); context.put("storyGenerationMode","IMPROVE_EXISTING_STORY");
    context.put("approvedStoryText",scope.get("sourceStory")); context.put("sourceStoryRecordId",scope.get("sourceStoryRecordId")); context.put("sourceFingerprint",scope.get("sourceStorySha256"));
    context.put("lockedRequirements",scope.containsKey("canonicalStoryFeasibilityContext")?List.of("PRESERVE_CORE_PREMISE","PRESERVE_CHARACTER_IDENTITY","PRESERVE_PHYSICAL_RULE","PRESERVE_ENDING"):List.of("PRESERVE_CORE_PREMISE","PRESERVE_KEY_EVENTS","PRESERVE_ENDING")); context.put("objective",scope.get("objective"));
    context.put("roundNumber",round); context.put("previousRevision",p.get("bestDraftId")); context.put("bestCandidate",p.getOrDefault("bestCandidate",Map.of())); context.put("rejectedCandidates",p.getOrDefault("rejectedCandidates",List.of()));
    context.put("acceptedChanges",p.getOrDefault("acceptedChanges",List.of())); context.put("previousAssessment",p.getOrDefault("lastAssessment",Map.of())); context.put("requestedAlternativeCount",2);
    if(scope.containsKey("canonicalStoryFeasibilityContext"))context.put("canonicalStoryFeasibilityContext",scope.get("canonicalStoryFeasibilityContext"));
    var request=new LinkedHashMap<String,Object>(); request.put("role","STORY"); request.put("text",scope.get("sourceStory")); request.put("maxCostUsd",((Number)map(row.get("authorization")).get("maxTotalUsd")).doubleValue()); request.put("context",context);
    var generated=dispatch(id,request,p,map(row.get("authorization"))); var alternatives=rows(roleResult(generated).get("alternatives"));
    if(alternatives.isEmpty()){stop(id,"STORY_VALIDATION_FAILED","No complete story candidate returned");return;}
    var rejected=new ArrayList<Map<String,Object>>(rows(p.getOrDefault("rejectedCandidates",List.of()))); var valid=new ArrayList<Map<String,Object>>();
    String baseline=String.valueOf(scope.get("sourceStory")); String parent=String.valueOf(map(p.getOrDefault("bestCandidate",Map.of())).getOrDefault("text",baseline));
    for(var candidate:alternatives){String text=String.valueOf(candidate.getOrDefault("text",""));String cid=String.valueOf(candidate.getOrDefault("candidateId","candidate-"+(valid.size()+1)));
      if(text.isBlank()||text.equals(baseline)||text.equals(parent)){rejected.add(Map.of("candidateId",cid,"reason","EQUIVALENT_OR_MEANINGLESS"));continue;} valid.add(candidate);}
    if(valid.isEmpty()){p.put("rejectedCandidates",rejected);saveProgress(id,p,"NO_JUSTIFIED_IMPROVEMENT");return;}
    var reviewContext=new LinkedHashMap<String,Object>();reviewContext.put("sourceRequestId",id.toString());reviewContext.put("sourceFingerprint",scope.get("sourceStorySha256"));reviewContext.put("approvedStoryText",baseline);reviewContext.put("candidates",valid);reviewContext.put("reviewPolicyVersion",scope.containsKey("canonicalStoryFeasibilityContext")?"canonical-a-aware-story-review-v1":"story-evolution-v1");reviewContext.put("roundNumber",round);reviewContext.put("objective",scope.get("objective"));reviewContext.put("previousAssessment",p.getOrDefault("lastAssessment",Map.of()));reviewContext.put("bestCandidate",p.getOrDefault("bestCandidate",Map.of()));
    if(scope.containsKey("canonicalStoryFeasibilityContext"))reviewContext.put("canonicalStoryFeasibilityContext",scope.get("canonicalStoryFeasibilityContext"));
    var reviewRequest=new LinkedHashMap<String,Object>();reviewRequest.put("role","STORY_REVIEW");reviewRequest.put("text",baseline);reviewRequest.put("maxCostUsd",((Number)map(row.get("authorization")).get("maxTotalUsd")).doubleValue());reviewRequest.put("context",reviewContext);
    var reviewEnvelope=dispatch(id,reviewRequest,p,map(row.get("authorization")));var review=roleResult(reviewEnvelope); p.put("lastAssessment",review); p.put("lastReviewTransport",reviewEnvelope);p.put("rejectedCandidates",rejected);p.put("reviewedCandidates",valid);
    String recommended=String.valueOf(review.getOrDefault("recommendedCandidateId","")); Map<String,Object> chosen=valid.stream().filter(c->recommended.equals(String.valueOf(c.get("candidateId")))).findFirst().orElse(null);
    if(!"COMPLETED".equals(review.get("reviewStatus"))||chosen==null){p.put("rejectedCandidates",rejected);saveProgress(id,p,scope.containsKey("canonicalStoryFeasibilityContext")?"NO_ELIGIBLE_STORY_CANDIDATE":"NO_REVIEW_SUPPORTED_IMPROVEMENT");return;}
    var reviewProvenance=map(reviewEnvelope.getOrDefault("evidenceProvenance",Map.of("origin","UNKNOWN_ORIGIN")));
    reviewProvenance.put("reviewerIndependent",independentProviders(map(generated.get("evidenceProvenance")),reviewProvenance));
    if(scope.containsKey("canonicalStoryFeasibilityContext")&&!eligibleCanonicalStoryCandidate(review,recommended,reviewProvenance)){
      rejected.add(Map.of("candidateId",recommended,"reason","CANONICAL_A_STRUCTURAL_FEASIBILITY_NOT_ESTABLISHED"));
      p.put("rejectedCandidates",rejected);saveProgress(id,p,"NO_ELIGIBLE_STORY_CANDIDATE");return;
    }
    String chosenText=String.valueOf(chosen.get("text")); String cid=String.valueOf(chosen.getOrDefault("candidateId","candidate-"+round));
    UUID draft=UUID.randomUUID(); var payload=new LinkedHashMap<>(chosen); payload.put("parentStoryRecordId",scope.get("sourceStoryRecordId")); payload.put("parentDraftId",p.get("bestDraftId")); payload.put("sourceFingerprint",scope.get("sourceStorySha256")); payload.put("round",round); payload.put("changes",List.of("Provider-authored story change assessed by STORY_REVIEW")); payload.put("review",review);payload.put("reviewProvenance",reviewProvenance);
    payload.put("reviewQualification","DETERMINISTIC_FIXTURE".equals(reviewProvenance.get("origin"))?"STRUCTURAL_INTEGRATION_FIXTURE_ONLY":"PROVISIONAL_INDEPENDENT_REVIEW_SUPPORTED");
    db.sql("INSERT INTO story_evolution_drafts(id,run_id,round_number,parent_draft_id,candidate_id,prompt_payload,candidate_sha256,assessment) VALUES(:id,:run,:r,CAST(NULLIF(:parent,'') AS uuid),:cid,CAST(:payload AS jsonb),:hash,CAST(:assessment AS jsonb))").param("id",draft).param("run",id).param("r",round).param("parent",String.valueOf(p.get("bestDraftId"))).param("cid",cid).param("payload",util.encode(payload)).param("hash",hash(chosenText)).param("assessment",util.encode(review)).update();
    p.put("bestDraftId",draft.toString()); p.put("bestCandidate",payload); p.put("acceptedChanges",List.of("round "+round+": "+String.valueOf(review.getOrDefault("recommendationReason","independent review supported candidate"))));
    int used=((Number)p.getOrDefault("requestCount",0)).intValue();
    if(round<max){p.put("phase","GENERATING");db.sql("UPDATE story_evolution_runs SET state='READY',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","ROUND_RETAINED","round",round,"draftId",draft.toString(),"providerCalls",used));}
    else {p.put("phase","AWAITING_OWNER_STORY_APPROVAL");p.put("reason","AWAITING_OWNER_STORY_APPROVAL");db.sql("UPDATE story_evolution_runs SET state='AWAITING_OWNER_STORY_APPROVAL',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","AWAITING_OWNER_STORY_APPROVAL","round",round,"draftId",draft.toString(),"providerCalls",used));}
  }
  @Transactional public Map<String,Object> approve(UUID id,Map<String,Object> body,HttpServletRequest req){owner(id,req);var row=load(id);if(ASSESSMENT.equals(map(row.get("scope")).get("assessmentOnlyPolicy")))throw new ResponseStatusException(CONFLICT,"Research assessment cannot approve a story");if(!"AWAITING_OWNER_STORY_APPROVAL".equals(row.get("state")))throw new ResponseStatusException(CONFLICT,"No story candidate awaits approval");var p=map(row.get("progress"));UUID draft=uuid(body.get("draftId"));if(!draft.toString().equals(p.get("bestDraftId")))throw new ResponseStatusException(CONFLICT,"Exact current story draft required");var d=db.sql("SELECT candidate_id,prompt_payload::text,candidate_sha256 FROM story_evolution_drafts WHERE id=:id AND run_id=:run").param("id",draft).param("run",id).query((rs,n)->Map.of("candidateId",rs.getString(1),"payload",util.read(rs.getString(2)),"sha256",rs.getString(3))).single();if(!Objects.equals(d.get("sha256"),body.get("candidateSha256")))throw new ResponseStatusException(CONFLICT,"Stale story fingerprint");String text=String.valueOf(map(d.get("payload")).get("text"));var newStory=workflow.persistStoryEvolutionDraft(uuid(row.get("sourceStoryRecordId")),text,map(d.get("payload")));String cid=String.valueOf(map(newStory.get("result")).get("alternatives") instanceof List<?> l && !l.isEmpty()?map(l.getFirst()).get("candidateId"):"candidate-1");String revision=cid+"-revision-"+workflow.storyFingerprint(text);var approval=workflow.approveStory(uuid(String.valueOf(newStory.get("recordId"))),Map.of("approvedText",text,"candidateId",cid,"revisionId",revision,"contentFingerprint",workflow.storyFingerprint(text),"sourceType","AUTONOMOUS_STORY_EVOLUTION"));p.put("approval",approval);p.put("phase","APPROVED_NEW_SOURCE");db.sql("UPDATE story_evolution_runs SET state='APPROVED_NEW_SOURCE',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(p)).param("id",id).update();event(id,Map.of("state","OWNER_STORY_APPROVED","newStoryRecordId",newStory.get("recordId")));return view(id,req);
  }
  public Map<String,Object> view(UUID id,HttpServletRequest req){owner(id,req);var r=load(id);var out=new LinkedHashMap<>(r);out.put("runId",id.toString());out.put("drafts",db.sql("SELECT id,round_number,candidate_id,prompt_payload::text, candidate_sha256 FROM story_evolution_drafts WHERE run_id=:id ORDER BY round_number").param("id",id).query((rs,n)->Map.of("draftId",rs.getString(1),"round",rs.getInt(2),"candidateId",rs.getString(3),"payload",util.read(rs.getString(4)),"candidateSha256",rs.getString(5))).list());out.put("events",db.sql("SELECT payload::text FROM story_evolution_events WHERE run_id=:id ORDER BY created_at,id").param("id",id).query((rs,n)->util.read(rs.getString(1))).list());out.remove("owner");return out;}
  @Transactional
  public Map<String,Object> handoff(UUID id, Map<String,Object> body, HttpServletRequest req) {
    owner(id, req);
    var row = load(id);
    if(ASSESSMENT.equals(map(row.get("scope")).get("assessmentOnlyPolicy")))throw new ResponseStatusException(CONFLICT,"Assessment cannot authorize BUILD_PROMPT");
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
    context.put("targetConfiguration",Map.of("contentProfile",context.get("contentProfile"),"selectedGenerator",context.get("generator"),"duration",context.get("desiredDuration"),"aspectRatio",map(context.get("settings")).get("aspectRatio"),"mainCharacter",body.getOrDefault("mainCharacter","UNKNOWN")));
    var request = new LinkedHashMap<String,Object>();
    request.put("role", "BUILD_PROMPT");
    request.put("text", storyText);
    request.put("maxCostUsd", amount(body.get("maxCostUsd")));
    request.put("context", context);
    var built = new LinkedHashMap<>(workflow.creativeRole(request));
    String prompt = String.valueOf(roleResult(built).getOrDefault("prompt", ""));
    if (prompt.isBlank()) throw new ResponseStatusException(CONFLICT, "BUILD_PROMPT returned no complete prompt");
    var evaluationContext=new LinkedHashMap<String,Object>();
    for(String key:List.of("contentProfile","generator","desiredDuration","openingStrategy","settings"))evaluationContext.put(key,context.get(key));
    evaluationContext.put("profile","post-family-v1");evaluationContext.put("sourceId","story:"+newStory);evaluationContext.put("sourceVersion",approval.get("revisionId"));evaluationContext.put("canonicalRulesetVersion","1.11");
    var evaluation = ml.validatePromptForWorkflow(prompt, "1.11", null, evaluationContext);
    if (evaluation == null) throw new ResponseStatusException(CONFLICT, "Ruleset 1.11 evaluation returned no report");
    var canonical = canonical(evaluation);
    built.put("prompt",prompt);
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
      var reviewOptions = new LinkedHashMap<String,Object>();
      for(String key:List.of("contentProfile","generator","desiredDuration","openingStrategy","settings"))reviewOptions.put(key,context.get(key));
      reviewOptions.put("canonicalRulesetVersion","1.11");
      reviewOptions.put("profile", "post-family-v1");
      workflow.saveStudioSession(Map.of("contentId",contentId,"promptVersionId",promptId,"sourceStoryRecordId",newStory.toString(),"approvalRecordId",approval.get("recordId"),"storyRevisionId",approval.get("revisionId"),"approvedStoryText",storyText));
      var savedSettings=new LinkedHashMap<String,Object>(reviewOptions);savedSettings.remove("profile");savedSettings.remove("canonicalRulesetVersion");savedSettings.put("contentId",contentId);savedSettings.put("promptVersionId",promptId);savedSettings.put("aspectRatio",map(context.get("settings")).get("aspectRatio"));workflow.saveProductionSettings(savedSettings);
      var review = workflow.runReview(new WorkflowService.ReviewRequest(contentId, promptId, prompt, null, reviewOptions), true);
      UUID analysisId = uuid(review.get("recordId"));
      var persisted = validation.validateWorkflowProfile(review);
      var preflight = workflow.adaptiveOptimizationPreflight(analysisId);
      // The profile-admission projection is a separate persisted report. Expose the
      // saved REVIEW's actual canonical result under the canonical label.
      built.put("qualityProfileAdmissionEvaluation", canonical(persisted.report()));
      canonical.clear();
      canonical.putAll(map(review.get("canonicalRuleEvaluation")));
      built.put("newPromptId", promptId);
      built.put("newPromptVersion", created.versionNumber());
      built.put("analysisId", analysisId.toString());
      built.put("qualityValidationId", persisted.validationRecordId());
      built.put("optimizationPreflightState", preflight);
      built.put("review", review);
      built.put("step7PreparationPath", "/render-preparation?contentId=" + contentId
          + "&promptVersionId=" + promptId + "&workflowReviewId=" + analysisId);
      built.put("step7State", "RENDER_PREPARATION_BLOCKED_UNTIL_CHARACTER_AND_FIRST_FRAME");
    } else {
      built.put("persistenceStatus", "REQUIRES_CONTENT_AND_PARENT_PROMPT_BINDING");
    }
    var reviewTransport=map(progress.getOrDefault("lastReviewTransport",Map.of()));
    var validityContext=new LinkedHashMap<String,Object>();
    var creativeProvenance=new LinkedHashMap<String,Object>(map(reviewTransport.getOrDefault("evidenceProvenance",Map.of("origin","UNKNOWN_ORIGIN"))));
    creativeProvenance.put("storySourceId",newStory.toString());creativeProvenance.put("promptSourceId",built.getOrDefault("newPromptId",built.get("promptFingerprint")));
    creativeProvenance.put("generatorProfile",context.get("generator"));creativeProvenance.put("evaluatorVersion","1.11");
    validityContext.put("provenance",creativeProvenance);
    validityContext.put("reviewer",map(map(progress.getOrDefault("lastAssessment",Map.of())).getOrDefault("creativeQualityAssessment",Map.of())));
    built.put("creativeValidityAssessment",ml.workflow("adaptive-optimization-policy",Map.of(
      "action","CREATIVE_VALIDITY","canonical",canonical,"source",prompt,"context",validityContext)));
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
  Map<String,Object> canonicalStoryFeasibilityContext(UUID source,UUID sourceApproval,Map<String,Object> approvedSource,String text,UUID analysis) {
    var subject=util.context(analysis,null,null);
    var approved=map(subject.get("approvedStory"));
    if(!Objects.equals(String.valueOf(approved.get("storyId")),source.toString())
        || !Objects.equals(String.valueOf(approved.get("approvalRecordId")),sourceApproval.toString())
        || !Objects.equals(String.valueOf(approved.get("text")),text))
      throw new ResponseStatusException(CONFLICT,"Baseline analysis is not bound to the exact approved source story");
    var canonical=map(subject.get("canonical"));
    if(!"1.11".equals(String.valueOf(canonical.get("rulesetVersion")))||!"EVALUATED".equals(String.valueOf(canonical.get("status"))))
      throw new ResponseStatusException(CONFLICT,"Canonical-A-aware story evolution requires an evaluated Ruleset 1.11 baseline");
    // Reuse the authoritative adaptive policy projection without requiring the
    // baseline prompt to remain the latest mutable prompt version. The exact
    // analysis/story/settings subject binding above already fails closed.
    var policyContext=new LinkedHashMap<String,Object>();policyContext.put("creativeQualityTargetActive",false);
    var policyRequest=new LinkedHashMap<String,Object>();policyRequest.put("action","PREFLIGHT");policyRequest.put("canonical",canonical);policyRequest.put("source",subject.get("originalPrompt"));policyRequest.put("context",policyContext);
    var preflight=new LinkedHashMap<String,Object>(ml.workflow("adaptive-optimization-policy",policyRequest));
    preflight.put("sourceAnalysisId",analysis.toString());
    var findings=new ArrayList<Map<String,Object>>();
    var preflightLosses=new HashMap<String,Map<String,Object>>();
    for(var loss:rows(preflight.get("losses")))preflightLosses.put(String.valueOf(loss.get("ruleId")),loss);
    for(String bucket:List.of("failedRules","unknownRules"))for(var rule:rows(canonical.get(bucket))){
      var row=new LinkedHashMap<String,Object>();
      for(String key:List.of("ruleId","outcome","severity","family","message","details"))if(rule.containsKey(key))row.put(key,rule.get(key));
      var loss=preflightLosses.get(String.valueOf(rule.get("ruleId")));
      String classification=loss==null?("unknownRules".equals(bucket)?"EVIDENCE_ONLY":"PROMPT_OR_EXECUTION_LEVEL"):switch(String.valueOf(loss.get("classification"))){
        case "PROTECTED_STORY_CONFLICT" -> "STORY_LEVEL_CHANGE_REQUIRES_OWNER_APPROVAL";
        case "EVIDENCE_REQUIRED" -> "EVIDENCE_ONLY";
        default -> "PROMPT_OR_EXECUTION_LEVEL";
      };
      row.put("repairClassification",classification);
      if(loss!=null){row.put("reason",loss.get("reason"));row.put("overallLoss",loss.get("overallLoss"));}
      findings.add(row);
    }
    var target=new LinkedHashMap<String,Object>();target.put("name","CANONICAL_A");target.put("minimumScore",92);target.put("rulesetVersion","1.11");target.put("scoreIsPrediction",false);
    var context=new LinkedHashMap<String,Object>();
    context.put("version","canonical-story-feasibility-context-v1");
    context.put("creativeReviewVersion","creative-story-merit-v1");
    context.put("sourceStoryId",source.toString());context.put("sourceApprovalRecordId",sourceApproval.toString());context.put("sourceRevisionId",approvedSource.get("revision"));context.put("sourceStorySha256",hash(text));
    context.put("baselineAnalysisId",analysis.toString());context.put("rulesetVersion","1.11");context.put("target",target);
    context.put("baseline",Map.of("score",canonical.get("score"),"grade",canonical.get("grade"),"status",canonical.get("status")));
    var snapshot=new LinkedHashMap<String,Object>();for(String key:List.of("version","state","generationAllowed","researchGenerationEligibility","currentScore","fixedEvidenceOptimisticCeiling","canonicalATargetStatus","reasons","losses","missingEvidence","genuineSourceAttemptCount","renderAuthorized"))if(preflight.containsKey(key))snapshot.put(key,preflight.get(key));context.put("targetAwarePreflight",snapshot);
    context.put("canonicalFindings",findings);
    context.put("mandatoryEvidenceContracts",List.of("SOURCE_BOUND_BEATS","EXACT_STORY_QUOTES_WHEN_CLAIMED","UNKNOWN_WHEN_UNSUPPORTED","INDEPENDENT_VISUAL_EVIDENCE_FOR_VISUAL_GATES"));
    context.put("creativeRequirements",List.of("IMMEDIATE_VISUALLY_UNDERSTANDABLE_OPENING","CLEAR_PHYSICAL_CAUSALITY","MEANINGFUL_VISUAL_PROGRESSION","ACTIVE_MAIN_CHARACTER","GENUINELY_DISTINCT_PROBLEM_SOLVING_WHEN_NARRATIVELY_JUSTIFIED","ESCALATING_CONSEQUENCES","MEANINGFUL_REALIZATION_OR_REVERSAL_OR_PAYOFF","GENERATOR_FEASIBLE_MOVEMENT","ORIGINALITY_WITHOUT_COPYING_PRIOR_SILHOUETTES"));
    context.put("prohibitedShortcuts",List.of("INVENT_PASS_EVIDENCE","TREAT_UNKNOWN_AS_PASS","ADD_MEANINGLESS_SCORE_ACTIONS","RENAME_REPEATED_ACTIONS_AS_STRATEGIES","COUNT_CAMERA_CHANGES_AS_STORY_STRATEGIES","CLAIM_UNSEEN_EFFECTS_VISIBLE","ADD_UNRELATED_PROTAGONISTS_OR_ANIMALS","COPY_PRIOR_WINNING_SILHOUETTES","CHANGE_PROTECTED_SOURCE_WITHOUT_OWNER_APPROVAL"));
    context.put("assessmentScope","TEXTUAL_STORY_FEASIBILITY_PREDICTION_ONLY; CANONICAL OUTCOMES REQUIRE BUILD_PROMPT_AND_RULESET_1_11");
    context.put("contextSha256",hash(util.encode(context)));
    return context;
  }
  static boolean eligibleCanonicalStoryCandidate(Map<String,Object> review,String candidateId,Map<String,Object> provenance) {
    var creative=rows(map(review.get("creativeQualityAssessment")).get("candidateAssessments")).stream()
        .filter(x->candidateId.equals(String.valueOf(x.get("candidateId")))).findFirst().orElse(Map.of());
    var structural=rows(map(review.get("structuralFeasibilityAssessment")).get("candidateAssessments")).stream()
        .filter(x->candidateId.equals(String.valueOf(x.get("candidateId")))).findFirst().orElse(Map.of());
    if(!"STRUCTURALLY_PROMISING".equals(structural.get("status")))return false;
    boolean fixture="DETERMINISTIC_FIXTURE".equals(provenance.get("origin"));
    if(!fixture&&(!"CREATIVELY_STRONG".equals(creative.get("status"))||!Boolean.TRUE.equals(provenance.get("reviewerIndependent"))))return false;
    var required=Set.of("ATTEMPT_001","ATTEMPT_002","CHAR_002","REPETITION_004","MINI_STORY_LOCK");
    var rules=rows(structural.get("ruleAssessments"));
    if(!rules.stream().map(x->String.valueOf(x.get("ruleId"))).collect(java.util.stream.Collectors.toSet()).containsAll(required))return false;
    return rules.stream().filter(x->required.contains(String.valueOf(x.get("ruleId"))))
        .noneMatch(x->Set.of("NOT_SUPPORTED","UNKNOWN").contains(String.valueOf(x.get("status"))));
  }
  static Map<String,Object> roleResult(Map<String,Object> envelope) {
    return envelope.get("result") instanceof Map<?,?> ? map(envelope.get("result")) : envelope;
  }
  /** Read-only owner preflight for the existing, strictly scoped two-call pilot. */
  public Map<String,Object> inspectPilot(Map<String,Object> body,HttpServletRequest request) {
    util.owner(request);
    if(transactionManager==null)throw new ResponseStatusException(CONFLICT,"Durable story ledger transaction manager unavailable");
    var scope=pilotScope(body);var story=pilotContext(scope,false,null,null);
    var review=pilotContext(scope,true,null,null);
    var operations=new ArrayList<Map<String,Object>>();
    for(var input:List.of(Map.of("role","STORY","context",story),Map.of("role","STORY_REVIEW","context",review))) {
      var checked=new LinkedHashMap<>(ml.workflow("story-experiment/preflight",Map.of("role",input.get("role"),"text",scope.get("sourceStory"),"context",input.get("context"),"maxCostUsd",20)));
      operations.add(checked);
    }
    double maximum=operations.stream().mapToDouble(x->((Number)x.get("maximumCalculatedUsd")).doubleValue()).max().orElseThrow();
    double cap=Math.ceil((maximum+1e-12)*1e6)/1e6;
    operations.forEach(x->x.put("maxCostUsd",cap));
    return Map.of("experimentVersion",PILOT,"scope",scope,"sourceScopeSha256",scope.get("sourceScopeSha256"),
        "operations",operations,"maxRequests",2,"maxRounds",1,"maxTotalUsd",cap*2,"providerCalls",0,"persisted",false);
  }
  Map<String,Object> pilotScope(Map<String,Object> body) {
    UUID source=uuid(body.get("sourceStoryRecordId")), approval=uuid(body.get("approvalRecordId")),analysis=uuid(body.get("baselineAnalysisId"));
    var approved=workflow.approvedStoryForCpq(source,approval);
    String text=String.valueOf(approved.get("text"));
    var scope=new LinkedHashMap<String,Object>();
    scope.put("experimentVersion",PILOT);scope.put("sourceStoryRecordId",source.toString());scope.put("sourceApprovalRecordId",approval.toString());
    scope.put("sourceRevisionId",approved.get("revision"));scope.put("sourceStory",text);scope.put("sourceStorySha256",hash(text));
    scope.put("baselineAnalysisId",analysis.toString());scope.put("objective",body.getOrDefault("objective","Improve creative quality, not canonical points"));
    scope.put("protectedAnchors",body.getOrDefault("protectedAnchors",List.of()));scope.put("requestedAlternativeCount",2);
    scope.put("canonicalStoryFeasibilityContext",canonicalStoryFeasibilityContext(source,approval,approved,text,analysis));
    // The canonical context validates analysis/source lineage. Include the
    // current saved production settings too; a source-only hash is insufficient.
    scope.put("productionSettings",util.context(analysis,null,null).getOrDefault("productionSettings",Map.of()));
    scope.put("sourceScopeSha256",hash(util.encode(scope)));
    return scope;
  }
  Map<String,Object> pilotContext(Map<String,Object> scope,boolean review,Object candidates,String runId) {
    var context=new LinkedHashMap<String,Object>();
    context.put("canonicalStoryFeasibilityContext",scope.get("canonicalStoryFeasibilityContext"));
    context.put("approvedStoryText",scope.get("sourceStory"));context.put("sourceFingerprint",scope.get("sourceStorySha256"));
    context.put("objective",scope.get("objective"));context.put("roundNumber",1);
    context.put("storyExperiment",Map.of("version",PILOT,"requestedAlternativeCount",2,
        "sourceStorySha256",scope.get("sourceStorySha256"),"sourceScopeSha256",scope.get("sourceScopeSha256"),"protectedAnchors",scope.get("protectedAnchors")));
    if(review){
      context.put("reviewPolicyVersion","creative-story-merit-v1");
      if(candidates!=null)context.put("candidates",candidates);
      if(runId!=null)context.put("sourceRequestId",runId);
    } else {
      context.put("inputMode","DETAILED_STORY");context.put("storyGenerationMode","IMPROVE_EXISTING_STORY");context.put("requestedAlternativeCount",2);
      context.put("lockedRequirements",List.of("PRESERVE_CORE_PREMISE","PRESERVE_CHARACTER_IDENTITY","PRESERVE_PHYSICAL_RULE","PRESERVE_ENDING"));
    }
    return context;
  }
  Map<String,Object> pilotBody(Map<String,Object> scope) {
    return Map.of("sourceStoryRecordId",scope.get("sourceStoryRecordId"),"approvalRecordId",scope.get("sourceApprovalRecordId"),
        "baselineAnalysisId",scope.get("baselineAnalysisId"),"protectedAnchors",scope.get("protectedAnchors"),"objective",scope.get("objective"));
  }
  Map<String,Object> startPilot(Map<String,Object> body,HttpServletRequest request) {
    String owner=util.owner(request);var inspected=inspectPilot(body,request);
    if(!Boolean.TRUE.equals(body.get("authorizePaidInference"))||!Boolean.TRUE.equals(body.get("confirmSourceAuthority"))
        ||!Boolean.FALSE.equals(body.get("automaticRetries"))||!Boolean.FALSE.equals(body.get("fallback")))
      throw new ResponseStatusException(BAD_REQUEST,"Fresh exact owner authorization; retries/fallback disabled required");
    if(integer(body,"maxRequests",2,2)!=2||integer(body,"maxRounds",1,1)!=1||integer(body,"maxRunSeconds",1,600)>600)
      throw new ResponseStatusException(BAD_REQUEST,"Exact one-round two-call limits required");
    if(!Objects.equals(body.get("sourceScopeSha256"),inspected.get("sourceScopeSha256"))
        ||!util.encode(body.get("operations")).equals(util.encode(inspected.get("operations")))
        ||Double.compare(amount(body.get("maxTotalUsd")),((Number)inspected.get("maxTotalUsd")).doubleValue())!=0)
      throw new ResponseStatusException(CONFLICT,"SCOPE_OR_INSTRUCTION_MISMATCH");
    if(!realEnabled)throw new ResponseStatusException(FORBIDDEN,"Real dispatch disabled; no run created");
    String key=String.valueOf(body.getOrDefault("idempotencyKey",""));if(key.length()<8||key.length()>100)throw new ResponseStatusException(BAD_REQUEST,"Stable idempotency key required");
    db.sql("SELECT pg_advisory_xact_lock(hashtext(:key))").param("key","story-pilot:"+owner+":"+key).query((rs,n)->rs.getObject(1)).list();
    var prior=db.sql("SELECT id,authorization_payload::text FROM story_evolution_runs WHERE owner_principal=:o AND idempotency_key=:k")
      .param("o",owner).param("k",key).query((rs,n)->Map.of("id",rs.getObject(1,UUID.class),"grant",util.read(rs.getString(2)))).optional();
    if(prior.isPresent()){
      if(!util.encode(prior.get().get("grant")).equals(util.encode(body)))throw new ResponseStatusException(CONFLICT,"Idempotency key cannot rebind authorization");
      return view((UUID)prior.get().get("id"),request);
    }
    UUID id=UUID.randomUUID();var scope=map(inspected.get("scope"));
    db.sql("INSERT INTO story_evolution_runs(id,owner_principal,idempotency_key,source_story_record_id,source_story_sha256,authorization_payload,scope,state,progress,deadline) VALUES(:id,:owner,:key,:source,:sha,CAST(:grant AS jsonb),CAST(:scope AS jsonb),'READY','{\"phase\":\"STORY\",\"round\":1,\"requestCount\":0}',now()+make_interval(secs=>:seconds))")
      .param("id",id).param("owner",owner).param("key",key).param("source",uuid(scope.get("sourceStoryRecordId"))).param("sha",scope.get("sourceStorySha256"))
      .param("grant",util.encode(body)).param("scope",util.encode(scope)).param("seconds",body.get("maxRunSeconds")).update();
    event(id,Map.of("state","AUTHORIZED","experimentVersion",PILOT,"sourceScopeSha256",scope.get("sourceScopeSha256"),"providerCalls",0));
    return view(id,request);
  }
  void stepPilot(UUID id,Map<String,Object> row,Map<String,Object> scope,Map<String,Object> progress) {
    // Only a never-started READY run can enter. A restart never replays either
    // paid request after uncertain dispatch or durable receipt.
    int claimed=db.sql("UPDATE story_evolution_runs SET state='RUNNING' WHERE id=:id AND state='READY' AND cancel_requested=false AND deadline>now()")
      .param("id",id).update();if(claimed!=1)return;
    var generation=pilotDispatch(id,"STORY",scope,progress,pilotContext(scope,false,null,null));
    afterPilotReceipt(id,"STORY");
    if(!"CANDIDATES_ACCEPTED".equals(generation.get("processingStatus"))){stop(id,"STORY_RESULT_REJECTED_OR_UNCERTAIN","");return;}
    // Reload the exact durable receipt. Never review caller/local alternatives.
    var persisted=pilotReceipt(id,"STORY");
    var candidates=map(persisted.get("result")).get("alternatives");
    var reviewContext=pilotContext(scope,true,candidates,id.toString());
    var gate=ml.workflow("story-experiment/validate",Map.of("text",scope.get("sourceStory"),"context",reviewContext,"result",map(persisted.get("result"))));
    if(!Boolean.TRUE.equals(gate.get("eligible"))){stop(id,"STORY_RESULT_INSUFFICIENT",util.encode(gate));return;}
    var review=pilotDispatch(id,"STORY_REVIEW",scope,progress,reviewContext);
    afterPilotReceipt(id,"STORY_REVIEW");
    if(!"INDEPENDENT_REVIEW_COMPLETED".equals(review.get("processingStatus"))){stop(id,"REVIEW_FAILED_OR_UNCERTAIN","");return;}
    progress.put("reviewedCandidates",candidates);progress.put("lastAssessment",review.get("result"));
    progress.put("ownerStoryApproval","PENDING");progress.put("phase","RESEARCH_COMPLETE_OWNER_REVIEW_REQUIRED");
    progress.put("reviewerIndependent",independentProviders(map(generation.get("evidenceProvenance")),map(review.get("evidenceProvenance"))));
    if(!Boolean.TRUE.equals(progress.get("reviewerIndependent"))){stop(id,"REVIEWER_INDEPENDENCE_UNSUPPORTED","");return;}
    db.sql("UPDATE story_evolution_runs SET state='RESEARCH_COMPLETE_OWNER_REVIEW_REQUIRED',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id")
      .param("p",util.encode(progress)).param("id",id).update();
    event(id,Map.of("state","RESEARCH_COMPLETE_OWNER_REVIEW_REQUIRED","ownerStoryApproval","PENDING","canonicalPromptScore","NOT_EVALUATED"));
  }
  /** Read authentic archived receipts; HTTP callers cannot supply replacement stories. */
  Map<String,Object> assessmentScope() {
    if(assessmentEvidenceRoot==null||assessmentEvidenceRoot.isBlank())throw new ResponseStatusException(CONFLICT,"Assessment evidence root is not configured");
    try {
      var root=java.nio.file.Path.of(assessmentEvidenceRoot).toRealPath();
      String catalogText=java.nio.file.Files.readString(root.resolve("AUTHENTIC_STORY_ASSESSMENT_SOURCE_CATALOG.json"));
      var catalog=util.read(catalogText);
      if(!ASSESSMENT.equals(catalog.get("policy"))||!Boolean.TRUE.equals(catalog.get("ownerPolicyApproval")))throw new IllegalStateException("Approved assessment-only catalog required");
      var source=map(catalog.get("sourceScope"));var current=pilotScope(pilotBody(source));
      if(!util.encode(source).equals(util.encode(current)))throw new IllegalStateException("Assessment approved source/settings changed");
      var candidates=new ArrayList<Map<String,Object>>();
      for(var entry:rows(catalog.get("candidates"))) {
        var file=root.resolve(String.valueOf(entry.get("receiptFile"))).toRealPath();
        if(!file.startsWith(root))throw new IllegalStateException("Receipt path escapes evidence root");
        String saved=java.nio.file.Files.readString(file);
        if(!hash(saved).equals(entry.get("receiptFileSha256")))throw new IllegalStateException("Immutable provider receipt fingerprint changed");
        var receipt=util.read(saved);String raw=String.valueOf(receipt.get("rawProviderResponse"));
        if(!hash(raw).equals(entry.get("rawResponseSha256")))throw new IllegalStateException("Authentic raw response fingerprint changed");
        var candidate=rows(util.read(raw).get("alternatives")).stream().filter(c->Objects.equals(c.get("candidateId"),entry.get("candidateId"))).findFirst().orElseThrow();
        if(!hash(String.valueOf(candidate.get("text"))).equals(entry.get("candidateSha256")))throw new IllegalStateException("Immutable candidate SHA changed");
        var bound=new LinkedHashMap<>(entry);bound.put("receipt",receipt);bound.put("originalCandidate",candidate);candidates.add(bound);
      }
      var result=new LinkedHashMap<String,Object>();result.put("experimentVersion",PILOT);result.put("assessmentOnlyPolicy",ASSESSMENT);
      var authority=new TreeMap<String,String>();
      for(Class<?> type:List.of(StoryEvolutionService.class,QualityMlClient.class,CpqOwnerPilotService.class)) {
        try(var bytes=type.getResourceAsStream("/"+type.getName().replace('.','/')+".class")) {
          if(bytes==null)throw new IllegalStateException("Assessment authority implementation unavailable");
          authority.put(type.getName(),HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes.readAllBytes())));
        } catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException(impossible);}
      }
      result.put("transportPolicy",QualityMlClient.assessmentTransportPolicy());
      result.put("authorityImplementationSha256",hash(util.encode(authority)));
      result.put("catalogSha256",hash(catalogText));result.put("sourceScope",current);result.put("candidates",candidates);
      result.put("sourceStoryRecordId",current.get("sourceStoryRecordId"));result.put("sourceStorySha256",current.get("sourceStorySha256"));
      result.put("sourceStory",current.get("sourceStory"));result.put("ownerPolicyApproval",true);return result;
    } catch(java.io.IOException error){throw new ResponseStatusException(CONFLICT,"Authentic assessment evidence unavailable",error);}
  }
  Map<String,Object> assessmentContext(Map<String,Object> scope) {return new LinkedHashMap<>(Map.of("assessmentOnlyPolicy",ASSESSMENT,"assessmentScope",scope));}
  public Map<String,Object> inspectAssessment(Map<String,Object> body,HttpServletRequest request) {
    util.owner(request);if(transactionManager==null)throw new ResponseStatusException(CONFLICT,"Durable ledger unavailable");
    var scope=assessmentScope();var operation=new LinkedHashMap<>(ml.workflow("story-experiment/assessment-preflight",Map.of("role","STORY_REVIEW","text",scope.get("sourceStory"),"context",assessmentContext(scope),"maxCostUsd",20)));
    double cap=Math.ceil((((Number)operation.get("maximumCalculatedUsd")).doubleValue()+1e-12)*1e6)/1e6;
    operation.put("maxCostUsd",cap);
    return Map.of("assessmentOnlyPolicy",ASSESSMENT,"scope",scope,"scopeSha256",hash(util.encode(scope)),"operations",List.of(operation),"maxRequests",1,"maxTotalUsd",cap,"persisted",false,"providerCalls",0);
  }
  Map<String,Object> startAssessment(Map<String,Object> body,HttpServletRequest request) {
    String actor=util.owner(request);var checked=inspectAssessment(body,request);
    if(!Boolean.TRUE.equals(body.get("authorizePaidInference"))||!Boolean.TRUE.equals(body.get("confirmAssessmentOnly"))
        ||!Boolean.FALSE.equals(body.get("automaticRetries"))||!Boolean.FALSE.equals(body.get("fallback")))
      throw new ResponseStatusException(BAD_REQUEST,"Separate exact owner spending authorization required; assessment-only, no retry/fallback");
    if(integer(body,"maxRequests",1,1)!=1||integer(body,"maxRounds",1,1)!=1)throw new ResponseStatusException(BAD_REQUEST,"Exactly one review; no generation");
    int seconds=integer(body,"maxRunSeconds",1,600);
    if(!Objects.equals(body.get("scopeSha256"),checked.get("scopeSha256"))||!util.encode(body.get("operations")).equals(util.encode(checked.get("operations")))
        ||Double.compare(amount(body.get("maxTotalUsd")),((Number)checked.get("maxTotalUsd")).doubleValue())!=0)
      throw new ResponseStatusException(CONFLICT,"Assessment source/model/instruction/budget binding changed");
    if(!realEnabled)throw new ResponseStatusException(FORBIDDEN,"Paid review dispatch disabled");
    String key=String.valueOf(body.getOrDefault("idempotencyKey",""));if(key.length()<8||key.length()>100)throw new ResponseStatusException(BAD_REQUEST,"Stable bounded idempotency key required");
    db.sql("SELECT pg_advisory_xact_lock(hashtext(:key))").param("key","assessment:"+actor+":"+key).query((rs,n)->rs.getObject(1)).list();
    var prior=db.sql("SELECT id,authorization_payload::text FROM story_evolution_runs WHERE owner_principal=:o AND idempotency_key=:k").param("o",actor).param("k",key).query((rs,n)->Map.of("id",rs.getObject(1,UUID.class),"grant",util.read(rs.getString(2)))).optional();
    if(prior.isPresent()){
      if(!util.encode(prior.get().get("grant")).equals(util.encode(body)))throw new ResponseStatusException(CONFLICT,"Idempotency cannot rebind assessment grant");
      return view((UUID)prior.get().get("id"),request);
    }
    UUID id=UUID.randomUUID();var scope=map(checked.get("scope"));
    db.sql("INSERT INTO story_evolution_runs(id,owner_principal,idempotency_key,source_story_record_id,source_story_sha256,authorization_payload,scope,state,progress,deadline) VALUES(:id,:owner,:key,:source,:sha,CAST(:grant AS jsonb),CAST(:scope AS jsonb),'READY','{\"phase\":\"ASSESSMENT_ONLY_REVIEW\",\"requestCount\":0}',now()+make_interval(secs=>:seconds))")
      .param("id",id).param("owner",actor).param("key",key).param("source",uuid(scope.get("sourceStoryRecordId"))).param("sha",scope.get("sourceStorySha256"))
      .param("grant",util.encode(body)).param("scope",util.encode(scope)).param("seconds",seconds).update();
    event(id,Map.of("state","AUTHORIZED","experimentVersion",PILOT,"assessmentOnlyPolicy",ASSESSMENT,"scopeSha256",checked.get("scopeSha256"),"providerCalls",0));return view(id,request);
  }
  void stepAssessment(UUID id,Map<String,Object> row,Map<String,Object> scope,Map<String,Object> progress) {
    if(!"READY".equals(row.get("state"))||Boolean.TRUE.equals(row.get("cancel"))||!((Instant)row.get("deadline")).isAfter(Instant.now()))throw new IllegalStateException("Assessment already started/cancelled/expired; no paid resume");
    if(db.sql("UPDATE story_evolution_runs SET state='RUNNING',updated_at=now() WHERE id=:id AND state='READY' AND cancel_requested=false AND deadline>now()").param("id",id).update()!=1)throw new IllegalStateException("Assessment already claimed");
    if(!realEnabled||!util.encode(scope).equals(util.encode(assessmentScope())))throw new IllegalStateException("Assessment disabled or immutable source changed before dispatch");
    var grant=map(row.get("authorization"));var authorized=rows(grant.get("operations")).getFirst();var context=assessmentContext(scope);
    var current=ml.workflow("story-experiment/assessment-preflight",Map.of("role","STORY_REVIEW","text",scope.get("sourceStory"),"context",context,"maxCostUsd",authorized.get("maxCostUsd")));
    for(var entry:current.entrySet())if(!util.encode(entry.getValue()).equals(util.encode(authorized.get(entry.getKey()))))throw new IllegalStateException("Assessment dispatch binding changed: "+entry.getKey());
    double cap=((Number)authorized.get("maxCostUsd")).doubleValue();
    if(((Number)progress.getOrDefault("requestCount",0)).intValue()!=0||cap>((Number)grant.get("maxTotalUsd")).doubleValue()||cap<((Number)current.get("maximumCalculatedUsd")).doubleValue())throw new IllegalStateException("Exactly one reserved assessment request required");
    UUID requestId=UUID.nameUUIDFromBytes((id+":ASSESSMENT_STORY_REVIEW").getBytes(java.nio.charset.StandardCharsets.UTF_8));
    context.put("assessmentDispatch",authorized);context.put("assessmentSpendingAuthorized",true);context.put("storyRequestId",requestId.toString());
    var input=Map.<String,Object>of("role","STORY_REVIEW","text",scope.get("sourceStory"),"context",context,"maxCostUsd",cap);
    progress.put("requestCount",1);progress.put("reservedUsd",cap);
    durablePilot(id,progress,Map.of("state","REQUEST_RESERVED","experimentVersion",PILOT,"assessmentOnlyPolicy",ASSESSMENT,"role","STORY_REVIEW","requestId",requestId.toString(),"binding",current,"maxCostUsd",cap));
    Map<String,Object> receipt;
    long dispatchStarted=System.nanoTime();
    try{receipt=new LinkedHashMap<>(ml.workflow("creative-role",input));}
    catch(Exception error){
      receipt=new LinkedHashMap<>();receipt.put("processingStatus","DISPATCH_UNCERTAIN");receipt.put("billingStatus","USAGE_UNKNOWN");receipt.put("providerDispatched","UNKNOWN");
      receipt.put("requestId",requestId.toString());receipt.put("clientRequestId",requestId.toString());
      Throwable cause=error;var chain=new ArrayList<String>();boolean timedOut=false,interrupted=false;
      for(int depth=0;cause!=null&&depth<8;depth++,cause=cause.getCause()){
        chain.add(cause.getClass().getSimpleName());timedOut|=cause instanceof java.net.http.HttpTimeoutException;interrupted|=cause instanceof InterruptedException;
      }
      receipt.put("error",Map.of("category",error.getClass().getSimpleName(),"causeChainTypes",chain,
          "failureClass",timedOut?"BACKEND_HTTP_TIMEOUT":interrupted?"BACKEND_INTERRUPTED":"BACKEND_TRANSPORT_FAILURE",
          "detail","Backend-to-ML transport did not return a complete receipt; provider outcome and billing remain unknown; no retry",
          "elapsedSeconds",(System.nanoTime()-dispatchStarted)/1e9));
    }
    if(!"DISPATCH_UNCERTAIN".equals(receipt.get("processingStatus"))&&(!Objects.equals(receipt.get("provider"),"openai")||!Objects.equals(receipt.get("model"),authorized.get("model"))||!Boolean.TRUE.equals(receipt.get("providerDispatched"))
        ||!Objects.equals(receipt.get("requestId"),requestId.toString())||!util.encode(receipt.get("binding")).equals(util.encode(current))))receipt.put("processingStatus","UNEXPECTED_TRANSPORT_OR_MODEL");
    receipt.put("requestFingerprint",hash(util.encode(input)));receipt.put("runId",id.toString());
    progress.put("assessmentReceipt",receipt);progress.put("phase","ASSESSMENT_RECEIPT_SAVED");
    if(receipt.get("actualCostUsd") instanceof Number cost)progress.put("knownActualCostUsd",cost.doubleValue());else progress.put("unresolvedBilling",true);
    durablePilot(id,progress,Map.of("state","PROVIDER_RECEIPT","experimentVersion",PILOT,"assessmentOnlyPolicy",ASSESSMENT,"role","STORY_REVIEW","requestId",requestId.toString(),"envelope",receipt));
    if(!"INDEPENDENT_REVIEW_COMPLETED".equals(receipt.get("processingStatus"))){stop(id,"ASSESSMENT_REJECTED_OR_UNCERTAIN","Receipt preserved; no retry");return;}
    progress.put("researchAssessment",receipt.get("result"));progress.put("ownerStoryApproval","PENDING");progress.put("productionSourceAdmission","NOT_SATISFIED_BY_RESEARCH");progress.put("renderAuthorized",false);progress.put("officialAPlus","INACTIVE");
    db.sql("UPDATE story_evolution_runs SET state='ASSESSMENT_COMPLETE_OWNER_DECISION_PENDING',progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id").param("p",util.encode(progress)).param("id",id).update();
    event(id,Map.of("state","ASSESSMENT_COMPLETE_OWNER_DECISION_PENDING","experimentVersion",PILOT,"assessmentOnlyPolicy",ASSESSMENT,"storyApproval",false,"renderAuthorized",false));
  }

  /** Test seam for a worker dying after durable receipt, never a retry hook. */
  void afterPilotReceipt(UUID id,String role) {}
  Map<String,Object> pilotDispatch(UUID id,String role,Map<String,Object> scope,Map<String,Object> progress,Map<String,Object> context) {
    var row=load(id);var grant=map(row.get("authorization"));
    if(!realEnabled||!"RUNNING".equals(row.get("state"))||Boolean.TRUE.equals(row.get("cancel"))||!((Instant)row.get("deadline")).isAfter(Instant.now()))throw new IllegalStateException("Pilot disabled/cancelled/expired before dispatch");
    if(!util.encode(scope).equals(util.encode(pilotScope(pilotBody(scope)))))throw new IllegalStateException("SCOPE_OR_INSTRUCTION_MISMATCH: current source");
    int index=((Number)progress.getOrDefault("requestCount",0)).intValue();
    if(index>=2||!(index==0?"STORY":"STORY_REVIEW").equals(role))throw new IllegalStateException("Exact role sequence/request limit reached");
    var authorized=rows(grant.get("operations")).get(index);
    var current=ml.workflow("story-experiment/preflight",Map.of("role",role,"text",scope.get("sourceStory"),"context",context,"maxCostUsd",authorized.get("maxCostUsd")));
    var compare=new LinkedHashMap<>(current);
    if("STORY_REVIEW".equals(role)){compare.remove("effectiveRequestSha256");compare.remove("payloadBytes");}
    for(var entry:compare.entrySet())if(!util.encode(entry.getValue()).equals(util.encode(authorized.get(entry.getKey()))))throw new IllegalStateException("SCOPE_OR_INSTRUCTION_MISMATCH: "+entry.getKey());
    double cap=((Number)authorized.get("maxCostUsd")).doubleValue(),reserved=((Number)progress.getOrDefault("reservedUsd",0)).doubleValue();
    if(cap<((Number)current.get("maximumCalculatedUsd")).doubleValue()||reserved+cap>((Number)grant.get("maxTotalUsd")).doubleValue()+1e-12)throw new IllegalStateException("Budget ceiling exceeded before reservation");
    if("STORY_REVIEW".equals(role)){
      var saved=pilotReceipt(id,"STORY");
      if(!util.encode(context.get("candidates")).equals(util.encode(map(saved.get("result")).get("alternatives"))))throw new IllegalStateException("SCOPE_OR_INSTRUCTION_MISMATCH: persisted candidates");
      context.put("reviewPayloadSha256",current.get("effectiveRequestSha256"));
    }
    UUID requestId=UUID.nameUUIDFromBytes((id+":"+role).getBytes(java.nio.charset.StandardCharsets.UTF_8));
    context.put("storyRequestId",requestId.toString());context.put("storyExperimentDispatch",authorized);
    var request=Map.<String,Object>of("role",role,"text",scope.get("sourceStory"),"context",context,"maxCostUsd",cap);
    progress.put("requestCount",index+1);progress.put("reservedUsd",reserved+cap);progress.put("phase",role+"_RESERVED");
    durablePilot(id,progress,Map.of("state","REQUEST_RESERVED","experimentVersion",PILOT,"requestId",requestId.toString(),"role",role,"binding",current,"maxCostUsd",cap));
    Map<String,Object> receipt;
    try {receipt=new LinkedHashMap<>(ml.workflow("creative-role",request));}
    catch(Exception failure){receipt=new LinkedHashMap<>();receipt.put("requestId",requestId.toString());receipt.put("role",role);receipt.put("processingStatus","DISPATCH_UNCERTAIN");receipt.put("billingStatus","USAGE_UNKNOWN");receipt.put("providerDispatched","UNKNOWN");receipt.put("error",Map.of("category",failure.getClass().getSimpleName(),"detail","Transport did not return a durable response; retry forbidden"));}
    if(!"DISPATCH_UNCERTAIN".equals(receipt.get("processingStatus"))&&(!Objects.equals(receipt.get("provider"),authorized.get("provider"))||!Objects.equals(receipt.get("model"),authorized.get("model"))
        ||!Boolean.TRUE.equals(receipt.get("providerDispatched"))||!requestId.toString().equals(receipt.get("requestId"))
        ||!util.encode(current).equals(util.encode(receipt.get("binding")))))receipt.put("processingStatus","UNEXPECTED_TRANSPORT_OR_MODEL");
    receipt.put("requestFingerprint",hash(util.encode(request)));receipt.put("runId",id.toString());receipt.put("evidenceProvenance",evidenceProvenance(request,receipt));
    progress.put(role+"Receipt",receipt);progress.put("phase",role+"_RECEIVED");
    if(receipt.get("actualCostUsd") instanceof Number cost&&Double.isFinite(cost.doubleValue())&&cost.doubleValue()>=0)
      progress.put("knownActualCostUsd",((Number)progress.getOrDefault("knownActualCostUsd",0)).doubleValue()+cost.doubleValue());
    else if(!Boolean.FALSE.equals(receipt.get("providerDispatched")))progress.put("unresolvedBilling",true);
    durablePilot(id,progress,Map.of("state","PROVIDER_RECEIPT","experimentVersion",PILOT,"requestId",requestId.toString(),"role",role,"envelope",receipt));
    return receipt;
  }
  Map<String,Object> pilotReceipt(UUID id,String role) {
    var durable=db.sql("SELECT payload::text FROM story_evolution_events WHERE run_id=:id AND payload->>'state'='PROVIDER_RECEIPT' AND payload->>'role'=:role ORDER BY created_at,id")
      .param("id",id).param("role",role).query((rs,n)->util.read(rs.getString(1))).list();
    if(durable.size()!=1)throw new IllegalStateException("Exact one durable role receipt required; replay forbidden");
    var receipt=map(durable.getFirst().get("envelope"));
    if(!util.encode(receipt).equals(util.encode(map(load(id).get("progress")).get(role+"Receipt"))))throw new IllegalStateException("SCOPE_OR_INSTRUCTION_MISMATCH: persisted receipt changed");
    return receipt;
  }
  void durablePilot(UUID id,Map<String,Object> progress,Map<String,Object> evidence) {
    Runnable write=()->{
      event(id,evidence);
      db.sql("UPDATE story_evolution_runs SET progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id")
        .param("p",util.encode(progress)).param("id",id).update();
    };
    if(transactionManager==null)throw new IllegalStateException("Durable story ledger transaction manager unavailable");
    var transaction=new org.springframework.transaction.support.TransactionTemplate(transactionManager);
    transaction.setPropagationBehavior(org.springframework.transaction.TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    transaction.executeWithoutResult(status->write.run());
  }
  static boolean independentProviders(Map<String,Object> generation,Map<String,Object> review) {
    return "REAL_AI_PROVIDER".equals(generation.get("origin"))
        && "REAL_AI_PROVIDER".equals(review.get("origin"))
        && generation.get("provider") instanceof String gp && !gp.isBlank()
        && review.get("provider") instanceof String rp && !rp.isBlank()
        && !"UNKNOWN".equalsIgnoreCase(gp) && !"UNKNOWN".equalsIgnoreCase(rp)
        && !gp.equalsIgnoreCase(rp)
        && generation.get("model") instanceof String gm && !gm.isBlank()
        && review.get("model") instanceof String rm && !rm.isBlank();
  }
  Map<String,Object> dispatch(UUID id,Map<String,Object> request,Map<String,Object> progress,Map<String,Object> grant) {
    int index=((Number)progress.getOrDefault("requestCount",0)).intValue()+1;
    int max=((Number)grant.get("maxRequests")).intValue();
    if(index>max)throw new IllegalStateException("Story request limit reached; no retry");
    double total=((Number)grant.get("maxTotalUsd")).doubleValue();
    double reserved=((Number)progress.getOrDefault("reservedUsd",0)).doubleValue();
    double cap=Math.min(total/max,total-reserved);
    if(cap<=0)throw new IllegalStateException("Story budget exhausted before dispatch");
    request.put("maxCostUsd",cap);progress.put("requestCount",index);progress.put("reservedUsd",reserved+cap);
    db.sql("UPDATE story_evolution_runs SET progress=CAST(:p AS jsonb),updated_at=now() WHERE id=:id AND state='RUNNING'")
      .param("p",util.encode(progress)).param("id",id).update();
    event(id,Map.of("state","REQUEST_RESERVED","role",request.get("role"),"requestIndex",index,"maxCostUsd",cap));
    var result=new LinkedHashMap<String,Object>(ml.workflow("creative-role",request));
    double spent=result.get("actualCostUsd") instanceof Number n?n.doubleValue():cap;
    if(!Double.isFinite(spent)||spent<0||spent>cap)throw new IllegalStateException("Provider cost exceeds reserved story request budget");
    progress.put("actualCostUsd",((Number)progress.getOrDefault("actualCostUsd",0)).doubleValue()+spent);
    int calls=result.get("calls") instanceof Number n?n.intValue():1;
    progress.put("providerCalls",((Number)progress.getOrDefault("providerCalls",0)).intValue()+calls);
    var provenance=evidenceProvenance(request,result);
    result.put("evidenceProvenance",provenance);
    event(id,Map.of("state","REQUEST_COMPLETED","role",request.get("role"),"requestIndex",index,
      "actualCostUsd",spent,"provider",result.getOrDefault("provider","UNKNOWN"),"providerDispatched",result.getOrDefault("providerDispatched",true),"evidenceOrigin",provenance.get("origin")));
    return result;
  }
  Map<String,Object> evidenceProvenance(Map<String,Object> request,Map<String,Object> result) {
    String provider=String.valueOf(result.getOrDefault("provider","UNKNOWN"));
    boolean dispatched=Boolean.TRUE.equals(result.get("providerDispatched"));
    String origin="UNKNOWN".equals(result.get("providerDispatched"))?"UNKNOWN_ORIGIN":!dispatched||provider.toUpperCase().matches(".*(FIXTURE|MOCK|ISOLATED).*")?"DETERMINISTIC_FIXTURE":
      !"UNKNOWN".equals(provider)?"REAL_AI_PROVIDER":"UNKNOWN_ORIGIN";
    var out=new LinkedHashMap<String,Object>();out.put("version","creative-evidence-provenance-v1");out.put("origin",origin);
    out.put("provider",provider);out.put("model",result.get("model"));out.put("requestFingerprint",hash(util.encode(request)));
    out.put("responseFingerprint",hash(util.encode(result.getOrDefault("result",Map.of()))));out.put("timestamp",Instant.now().toString());
    out.put("reviewerOrigin",origin);out.put("reviewerIndependent",false);out.put("realCapabilityStatisticsEligible","REAL_AI_PROVIDER".equals(origin));
    out.put("officialCalibrationEligible",false);return out;
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
