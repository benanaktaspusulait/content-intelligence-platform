package com.pompomhills.intelligence.workflow;

import com.pompomhills.intelligence.quality.QualityMlClient;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.time.Instant;
import java.util.*;

import static com.pompomhills.intelligence.workflow.CpqOwnerPilotService.*;
import static org.springframework.http.HttpStatus.*;

/** Existing database/scheduled-worker pattern, with no browser-owned execution. */
@Service
public class OptimizationLoopService {
  static final String TARGET="CANONICAL_RULESET_1_11_A";
  final JdbcClient db; final CpqOwnerPilotService util; final CreativePromptQualityService cpq;
  final WorkflowService workflow; final QualityMlClient ml;
  @Value("${pompom.cpq-pilot.real-enabled:false}") boolean realEnabled;
  public OptimizationLoopService(JdbcClient db,CpqOwnerPilotService util,CreativePromptQualityService cpq,WorkflowService workflow,QualityMlClient ml){this.db=db;this.util=util;this.cpq=cpq;this.workflow=workflow;this.ml=ml;}
  Instant now(){return Instant.now();}
  Map<String,Object> local(String action,Map<String,Object> data){var input=new LinkedHashMap<>(data);input.put("action",action);return ml.workflow("optimization-loop/local",input);}
  public Map<String,Object> capabilities(){var r=new LinkedHashMap<>(local("CAPABILITIES",Map.of()));r.put("realDispatchEnabled",realEnabled);return r;}
  Map<String,Object> scope(UUID analysis,String draft){
    var subject=cpq.pilotSubject(analysis,null,null);var saved=workflow.get(analysis);
    String original=String.valueOf(subject.get("originalPrompt"));String baseline=draft==null||draft.isBlank()?original:draft;
    if(baseline.length()>30000)throw new ResponseStatusException(BAD_REQUEST,"Baseline too large");
    var decisions=db.sql("SELECT evidence_id,payload::text FROM cpq_pilot_evidence WHERE evidence_type='OWNER_DECISION' AND payload::text LIKE :binding ORDER BY created_at,evidence_id")
        .param("binding","%"+subject.get("approvedStorySha256")+"%").query((rs,n)->Map.of("evidenceId",rs.getString(1),"payload",util.read(rs.getString(2)))).list();
    var r=new LinkedHashMap<String,Object>();r.put("analysisId",analysis.toString());r.put("contentId",subject.get("contentId"));r.put("promptVersionId",subject.get("promptVersionId"));r.put("originalPrompt",original);r.put("baselinePrompt",baseline);r.put("baselineSha256",hash(baseline));r.put("baselineKind",baseline.equals(original)?"IMMUTABLE_SAVED_PROMPT":"UNAPPROVED_RUN_BASELINE");
    r.put("approvedStory", subject.get("approvedStory"));
    r.put("approvedStorySha256", subject.get("approvedStorySha256"));
    r.put("settings", subject.get("productionSettings"));
    r.put("settingsSha256", subject.get("productionSettingsSha256"));
    r.put("ownerDecisions", decisions);
    r.put("request", saved.get("boundRequest"));
    r.put("contractVersion", "BOUNDED_OPTIMIZATION_LOOP_V1");
    r.put("evaluationPolicy", Map.of("ruleset", "1.11", "attemptEvidence", "ACTOR_SOURCE_BOUND_V2", "motionEvidence", "TOKEN_MOTION_V2", "stage", "PRE_RENDER"));
    r.put("providerConfiguration", capabilities().get("profiles"));
    r.put("target", TARGET);
    return r;
  }
  /**
   * The target-aware feasibility calculation is owned by the existing workflow
   * policy path.  Keeping this as a seam also makes the bounded-loop contract
   * testable with an eligible disposable fixture without duplicating policy.
   */
  Map<String,Object> targetAwarePreflight(UUID analysis){return workflow.adaptiveOptimizationPreflight(analysis);}
  Map<String,Object> targetAwareSnapshot(UUID analysis){
    var result=targetAwarePreflight(analysis);
    var snapshot=new LinkedHashMap<String,Object>();
    for(String key:List.of("state","generationAllowed","researchGenerationEligibility","currentScore","fixedEvidenceOptimisticCeiling","canonicalATargetStatus","reasons","losses","missingEvidence","genuineSourceAttemptCount","creativeQualityTarget","renderAuthorized","sourceAnalysisId","sourcePromptVersionId","sourcePromptSha256","productionSettingsRecordId"))
      if(result.containsKey(key)) snapshot.put(key,result.get(key));
    return snapshot;
  }
  Map<String,Object> boundScope(UUID analysis,String draft,Map<String,Object> feasibility){var s=new LinkedHashMap<>(scope(analysis,draft));s.put("targetAwarePreflight",feasibility);return s;}
  public Map<String,Object> preflight(Map<String,Object> body,HttpServletRequest request){
    util.owner(request); UUID analysis=uuid(body.get("analysisId"));
    var feasibility=targetAwareSnapshot(analysis);
    var s=boundScope(analysis,String.valueOf(body.getOrDefault("draftPrompt","")),feasibility);
    var out=new LinkedHashMap<String,Object>();out.put("scope",s);out.put("scopeSha256",hash(util.encode(s)));out.put("capabilities",capabilities());out.put("targetAwarePreflight",feasibility);out.put("persisted",false);
    out.put("generationAllowed",feasibility.getOrDefault("generationAllowed",false));out.put("state",feasibility.getOrDefault("state","CONTRACT_FAILURE"));
    out.put("researchGenerationEligibility",feasibility.getOrDefault("researchGenerationEligibility",Map.of()));
    if(Boolean.TRUE.equals(map(feasibility.get("researchGenerationEligibility")).get("allowed")))
      out.put("researchComparisonPlan",researchComparisonPlan(s));
    return out;
  }
  Map<String,Object> researchComparisonPlan(Map<String,Object> scope){
    var profiles=map(capabilities().get("profiles"));
    var runs=new ArrayList<Map<String,Object>>();double total=0;int totalInputBound=0;
    for(var pairing:List.of(List.of("deepseek-primary","openai-escalation"),List.of("openai-escalation","deepseek-primary"))){
      String generator=pairing.get(0),reviewer=pairing.get(1);var operations=new ArrayList<Map<String,Object>>();double runCost=0;
      for(String role:List.of("GENERATION","SOURCE_FIDELITY","CRITIC")){
        String profileId="GENERATION".equals(role)?generator:reviewer;var profile=map(profiles.get(profileId));
        var auth=new LinkedHashMap<String,Object>();auth.put("profileId",profileId);auth.put("role",role);
        for(String key:List.of("provider","model","reasoningEffort"))auth.put(key,profile.get(key));
        auth.put("maxOutputTokens",4000);auth.put("maxCostUsd",20.0);
        String prompt=String.valueOf(scope.get("baselinePrompt"));String assumption="EXACT_CURRENT_BASELINE";
        if(!"GENERATION".equals(role)){prompt=(prompt+"\n"+"X".repeat(30000)).substring(0,30000);assumption="MAXIMUM_ALLOWED_CANDIDATE_30000_CHARS";}
        var input=new LinkedHashMap<String,Object>();input.put("scope",scope);input.put("role",role);input.put("prompt",prompt);input.put("round",1);input.put("candidateId","PREVIEW:1");input.put("feedback",Map.of());input.put("authorization",auth);input.put("timeoutSeconds",120);
        var preview=local("PREVIEW_REQUEST",input);double estimate=((Number)preview.get("maxCalculatedCostUsd")).doubleValue();double cap=Math.ceil(estimate*1_000_000d)/1_000_000d;
        var operation=new LinkedHashMap<String,Object>();operation.putAll(auth);operation.put("maxCostUsd",cap);operation.put("inputBoundAssumption",assumption);
        for(String key:List.of("inputTokenUpperBound","maxCalculatedCostUsd","systemSha256","userPayloadSha256","responseSchemaSha256","instructionContextSha256","sourceScopeSha256","transportOrigin","providerAdapter","fixtureFallbackAllowed","providerDispatched"))operation.put(key,preview.get(key));
        operations.add(operation);runCost+=cap;totalInputBound+=((Number)preview.get("inputTokenUpperBound")).intValue();
      }
      var run=new LinkedHashMap<String,Object>();run.put("label",runs.isEmpty()?"RUN_A":"RUN_B");run.put("mode",generator.equals("deepseek-primary")?"DEEPSEEK_ONLY":"OPENAI_ONLY");run.put("generatorProfileId",generator);run.put("independentReviewerProfileId",reviewer);run.put("maxRounds",1);run.put("maxRequests",3);run.put("maxRunSeconds",600);run.put("maxTotalUsd",Math.ceil(runCost*1_000_000d)/1_000_000d);run.put("operations",operations);runs.add(run);total+=runCost;
    }
    var plan=new LinkedHashMap<String,Object>();plan.put("version","real-model-a-comparison-plan-v1");plan.put("purpose","REAL_MODEL_A_CAPABILITY_RESEARCH_V1");plan.put("runs",runs);plan.put("maximumRequests",6);plan.put("maximumOutputTokens",24000);plan.put("summedConservativeInputUnitBound",totalInputBound);plan.put("maximumTotalUsd",Math.ceil(total*1_000_000d)/1_000_000d);plan.put("timeoutSecondsPerRequest",120);plan.put("automaticRetries",false);plan.put("fallback",false);plan.put("promptApprovalAllowed",false);plan.put("imageGenerationAllowed",false);plan.put("renderAuthorized",false);plan.put("providerCalls",0);return plan;
  }
  static int integer(Map<String,Object> data,String key,int min,int max){var v=data.get(key);if(!(v instanceof Number n)||!Double.isFinite(n.doubleValue())||n.doubleValue()!=n.intValue()||n.intValue()<min||n.intValue()>max)throw new ResponseStatusException(BAD_REQUEST,"Invalid limit: "+key);return n.intValue();}
  static double amount(Object v){if(!(v instanceof Number n)||!Double.isFinite(n.doubleValue())||n.doubleValue()<=0||n.doubleValue()>20)throw new ResponseStatusException(BAD_REQUEST,"Explicit positive USD ceiling <=20 required");return n.doubleValue();}
  Map<String,Object> validateGrant(Map<String,Object> body){
    if(!TARGET.equals(body.get("target")))throw new ResponseStatusException(BAD_REQUEST,"Unsupported/inactive target; CPQ A/A+ unavailable");
    if(!Boolean.TRUE.equals(body.get("authorizePaidInference"))||!Boolean.TRUE.equals(body.get("confirmSourceAuthority"))||!Boolean.FALSE.equals(body.get("automaticRetries")))throw new ResponseStatusException(BAD_REQUEST,"One explicit bounded grant and source confirmation required; retries disabled");
    integer(body,"maxRounds",1,5);integer(body,"maxRequests",1,15);integer(body,"maxRunSeconds",30,1800);amount(body.get("maxTotalUsd"));
    String mode=String.valueOf(body.get("mode"));if(!Set.of("DEEPSEEK_ONLY","OPENAI_ONLY","ADAPTIVE").contains(mode))throw new ResponseStatusException(BAD_REQUEST,"Unsupported routing mode");
    var profiles=map(capabilities().get("profiles"));var rules=rows(body.get("operations"));if(rules.isEmpty()||rules.size()>6)throw new ResponseStatusException(BAD_REQUEST,"Explicit role/profile allowances required");
    var ids=new HashSet<String>();for(var r:rules){String role=String.valueOf(r.get("role")),id=String.valueOf(r.get("profileId"));if(!Set.of("GENERATION","SOURCE_FIDELITY","CRITIC").contains(role)||!ids.add(role+":"+id))throw new ResponseStatusException(BAD_REQUEST,"Invalid/duplicate role");var p=map(profiles.get(id));if(p.isEmpty())throw new ResponseStatusException(BAD_REQUEST,"Unlisted model");if(!Boolean.TRUE.equals(p.get("configured")))throw new ResponseStatusException(CONFLICT,"Provider profile is not configured on the server");for(String k:List.of("provider","model","reasoningEffort"))if(!Objects.equals(r.get(k),p.get(k)))throw new ResponseStatusException(CONFLICT,"Exact model/effort binding required");integer(r,"maxOutputTokens",1024,((Number)p.get("reviewMaxOutputTokens")).intValue());amount(r.get("maxCostUsd"));}
    var generators=rules.stream().filter(r->"GENERATION".equals(r.get("role"))).map(r->String.valueOf(r.get("profileId"))).toList();
    var expected=mode.equals("ADAPTIVE")?Set.of("deepseek-primary","openai-escalation"):Set.of(mode.equals("DEEPSEEK_ONLY")?"deepseek-primary":"openai-escalation");
    if(!new HashSet<>(generators).equals(expected))throw new ResponseStatusException(BAD_REQUEST,"Generation allowance must match chosen routing mode");
    for(String generator:generators)for(String role:List.of("SOURCE_FIDELITY","CRITIC"))if(rules.stream().noneMatch(r->role.equals(r.get("role"))&&!generator.equals(r.get("profileId"))))throw new ResponseStatusException(BAD_REQUEST,"Independent source/critic model allowance required for every generator");
    if(Boolean.TRUE.equals(body.get("researchOnly"))){
      if(!"REAL_MODEL_A_CAPABILITY_RESEARCH_V1".equals(body.get("purpose"))
          || !Boolean.TRUE.equals(body.get("confirmNoPromptApproval"))
          || !Boolean.TRUE.equals(body.get("confirmNoImageOrRender")))
        throw new ResponseStatusException(BAD_REQUEST,"Exact text-only research purpose and downstream prohibitions required");
      if(((Number)body.get("maxRounds")).intValue()!=1 || ((Number)body.get("maxRequests")).intValue()!=3)
        throw new ResponseStatusException(BAD_REQUEST,"Research comparison run is exactly one generation plus two independent reviews");
    }
    return new LinkedHashMap<>(body);
  }
  static boolean researchAllowed(Map<String,Object> feasibility,Map<String,Object> body){
    return Boolean.TRUE.equals(body.get("researchOnly"))
        && Boolean.TRUE.equals(map(feasibility.get("researchGenerationEligibility")).get("allowed"));
  }
  void validateResearchBindings(Map<String,Object> scope,Map<String,Object> grant){
    if(!Boolean.TRUE.equals(grant.get("researchOnly")))return;
    var plan=researchComparisonPlan(scope);
    String mode=String.valueOf(grant.get("mode"));
    var expectedRun=rows(plan.get("runs")).stream().filter(r->mode.equals(r.get("mode"))).findFirst()
        .orElseThrow(()->new ResponseStatusException(BAD_REQUEST,"Research routing mode is not in the current server plan"));
    if(((Number)grant.get("maxRounds")).intValue()!=((Number)expectedRun.get("maxRounds")).intValue()
        || ((Number)grant.get("maxRequests")).intValue()!=((Number)expectedRun.get("maxRequests")).intValue()
        || ((Number)grant.get("maxRunSeconds")).intValue()!=((Number)expectedRun.get("maxRunSeconds")).intValue()
        || Double.compare(((Number)grant.get("maxTotalUsd")).doubleValue(),((Number)expectedRun.get("maxTotalUsd")).doubleValue())!=0)
      throw new ResponseStatusException(CONFLICT,"Research limits/cost must match the fresh server preflight");
    var expected=rows(expectedRun.get("operations"));var actual=rows(grant.get("operations"));
    if(actual.size()!=expected.size())throw new ResponseStatusException(CONFLICT,"Research operations changed after preflight");
    var immutable=List.of("profileId","role","provider","model","reasoningEffort","maxOutputTokens","maxCostUsd",
        "inputTokenUpperBound","maxCalculatedCostUsd","systemSha256","userPayloadSha256","responseSchemaSha256",
        "instructionContextSha256","sourceScopeSha256","transportOrigin","providerAdapter","fixtureFallbackAllowed","providerDispatched");
    for(var wanted:expected){
      var supplied=actual.stream().filter(r->Objects.equals(r.get("profileId"),wanted.get("profileId"))&&Objects.equals(r.get("role"),wanted.get("role"))).findFirst()
          .orElseThrow(()->new ResponseStatusException(CONFLICT,"Research role/profile binding changed after preflight"));
      for(String key:immutable){Object a=supplied.get(key),b=wanted.get(key);boolean same=a instanceof Number an&&b instanceof Number bn?Double.compare(an.doubleValue(),bn.doubleValue())==0:Objects.equals(a,b);if(!same)throw new ResponseStatusException(CONFLICT,"Research "+key+" changed after preflight");}
      if(!"REAL_PROVIDER_ADAPTER".equals(supplied.get("transportOrigin"))||!"CreativeCapabilityProvider".equals(supplied.get("providerAdapter"))||!Boolean.FALSE.equals(supplied.get("fixtureFallbackAllowed"))||!Boolean.FALSE.equals(supplied.get("providerDispatched")))
        throw new ResponseStatusException(CONFLICT,"Research transport must be the non-fixture real-provider adapter");
    }
  }
  @Transactional public Map<String,Object> start(Map<String,Object> body,HttpServletRequest request){
    String owner=util.owner(request);
    UUID analysis=uuid(body.get("analysisId"));
    // Recompute the authoritative target gate before validating/recording a
    // paid grant.  A stale client preflight can therefore never reserve a
    // budget or create a job for a protected target such as Mimi.
    var feasibility=targetAwareSnapshot(analysis);
    if(!Boolean.TRUE.equals(feasibility.get("generationAllowed"))&&!researchAllowed(feasibility,body))
      throw new ResponseStatusException(CONFLICT,util.encode(Map.of("state",feasibility.getOrDefault("state","TARGET_BLOCKED"),"generationAllowed",false,"researchGenerationEligibility",feasibility.getOrDefault("researchGenerationEligibility",Map.of()),"feasibility",feasibility,"providerCalls",0,"nextAction","STORY_EVOLUTION_OR_UPDATED_SOURCE_EVIDENCE")));
    var grant=validateGrant(body);
    var s=boundScope(analysis,String.valueOf(body.getOrDefault("draftPrompt","")),feasibility);
    if(!hash(util.encode(s)).equals(body.get("scopeSha256")))throw new ResponseStatusException(CONFLICT,"Source/settings/baseline changed after inspection");
    validateResearchBindings(s,grant);
    if(!realEnabled)throw new ResponseStatusException(FORBIDDEN,"Real dispatch remains disabled; no run authorized");
    String key=String.valueOf(body.getOrDefault("idempotencyKey",""));if(key.length()<8||key.length()>100)throw new ResponseStatusException(BAD_REQUEST,"Stable idempotency key required");
    db.sql("SELECT pg_advisory_xact_lock(hashtext(:k))").param("k","optimization:"+owner+":"+key).query((rs,n)->rs.getObject(1)).list();
    var old=db.sql("SELECT id,grant_payload::text FROM optimization_runs WHERE owner_principal=:owner AND idempotency_key=:key").param("owner",owner).param("key",key).query((rs,n)->Map.of("id",rs.getObject(1,UUID.class),"grant",util.read(rs.getString(2)))).optional();
    if(old.isPresent()){if(!util.encode(old.get().get("grant")).equals(util.encode(grant)))throw new ResponseStatusException(CONFLICT,"Duplicate Start cannot rebind authorization");return view((UUID)old.get().get("id"),request);}
    UUID id=UUID.randomUUID();var progress=new LinkedHashMap<String,Object>();progress.put("phase","EVALUATE_BASELINE");progress.put("round",0);progress.put("bestPrompt",s.get("baselinePrompt"));progress.put("bestDraftId","");progress.put("equivalentRounds",0);progress.put("noProgressRounds",0);
    db.sql("INSERT INTO optimization_runs(id,owner_principal,idempotency_key,scope,scope_sha256,grant_payload,state,progress,deadline) VALUES(:id,:owner,:key,CAST(:scope AS jsonb),:hash,CAST(:grant AS jsonb),'READY',CAST(:progress AS jsonb),now()+make_interval(secs=>:seconds))").param("id",id).param("owner",owner).param("key",key).param("scope",util.encode(s)).param("hash",hash(util.encode(s))).param("grant",util.encode(grant)).param("progress",util.encode(progress)).param("seconds",((Number)grant.get("maxRunSeconds")).intValue()).update();event(id,Map.of("state","AUTHORIZED","authorizationOwner",owner,"noPromptApproval",true));return view(id,request);
  }
  @Transactional public Map<String,Object> accept(UUID id,Map<String,Object> body,HttpServletRequest request,com.pompomhills.intelligence.content.ContentWorkspaceController versions){
    owner(id,request);var run=load(id);var progress=map(run.get("progress"));var savedScope=map(run.get("scope"));
    if(Boolean.TRUE.equals(map(run.get("grant")).get("researchOnly")))
      throw new ResponseStatusException(FORBIDDEN,"Research-only runs cannot approve or create prompt versions");
    if(!Boolean.TRUE.equals(body.get("approveExactPromptVersion"))||!Boolean.TRUE.equals(body.get("confirmNoRenderOrGrade")))throw new ResponseStatusException(BAD_REQUEST,"Explicit final prompt approval and no-render confirmation required");
    db.sql("SELECT id FROM optimization_runs WHERE id=:id FOR UPDATE").param("id",id).query(UUID.class).single();
    var prior=db.sql("SELECT payload::text FROM optimization_run_events WHERE run_id=:id AND payload->>'state'='OWNER_ACCEPTED'").param("id",id).query((rs,n)->util.read(rs.getString(1))).optional();
    if(prior.isPresent())return prior.get();
    if(!"COMPLETED".equals(run.get("state"))||!"TARGET_REACHED_REVIEW_REQUIRED".equals(progress.get("reason")))throw new ResponseStatusException(CONFLICT,"Target unmet or run unresolved; no automatic acceptance");
    if(!hash(util.encode(scope(uuid(savedScope.get("analysisId")),String.valueOf(savedScope.get("baselinePrompt"))))).equals(run.get("scopeSha256")))throw new ResponseStatusException(CONFLICT,"Source/settings changed; acceptance requires current evidence");
    UUID draft=uuid(body.get("draftId"));if(!draft.toString().equals(progress.get("reviewCandidateId")))throw new ResponseStatusException(CONFLICT,"Exact final review candidate required");
    var candidate=db.sql("SELECT payload::text,prompt_sha256 FROM optimization_run_drafts WHERE id=:draft AND run_id=:id").param("draft",draft).param("id",id).query((rs,n)->Map.of("payload",util.read(rs.getString(1)),"sha256",rs.getString(2))).single();
    if(!candidate.get("sha256").equals(body.get("promptSha256")))throw new ResponseStatusException(CONFLICT,"Exact prompt fingerprint required");
    var assessment=map(progress.get("lastAssessment"));if(!Boolean.TRUE.equals(assessment.get("retained"))||!Boolean.TRUE.equals(assessment.get("independentSupport"))||!"PASS".equals(assessment.get("sourceFidelity"))||!Boolean.TRUE.equals(map(assessment.get("compilerAssessment")).get("approvalEligible")))throw new ResponseStatusException(CONFLICT,"Independent source/quality and compiler review remains unresolved");
    String prompt=String.valueOf(map(candidate.get("payload")).get("prompt"));
    var created=versions.createPrompt(((Number)savedScope.get("contentId")).longValue(),new com.pompomhills.intelligence.content.ContentWorkspaceController.CreatePromptRequest(prompt,util.encode(Map.of("boundedOptimizationProvenance",Map.of("runId",id.toString(),"draftId",draft.toString(),"promptSha256",candidate.get("sha256"),"owner",util.owner(request),"explicitApproval",true,"renderAuthorized",false))),((Number)savedScope.get("promptVersionId")).longValue()));
    var result=Map.<String,Object>of("state","OWNER_ACCEPTED","runId",id.toString(),"draftId",draft.toString(),"promptVersionId",created.id(),"renderAuthorized",false,"officialCpqGrading","INACTIVE");event(id,result);return result;
  }
  Map<String,Object> load(UUID id){return db.sql("SELECT owner_principal,scope::text,scope_sha256,grant_payload::text,state,progress::text,cancel_requested,deadline FROM optimization_runs WHERE id=:id").param("id",id).query((rs,n)->Map.<String,Object>of("owner",rs.getString(1),"scope",util.read(rs.getString(2)),"scopeSha256",rs.getString(3),"grant",util.read(rs.getString(4)),"state",rs.getString(5),"progress",util.read(rs.getString(6)),"cancel",rs.getBoolean(7),"deadline",rs.getTimestamp(8).toInstant())).optional().orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Run not found"));}
  void owner(UUID id,HttpServletRequest request){if(!util.owner(request).equals(load(id).get("owner")))throw new ResponseStatusException(FORBIDDEN,"Run belongs to another owner");}
  public Map<String,Object> latest(UUID analysis,HttpServletRequest request){String who=util.owner(request);return db.sql("SELECT id FROM optimization_runs WHERE owner_principal=:owner AND scope->>'analysisId'=:analysis ORDER BY created_at DESC LIMIT 1").param("owner",who).param("analysis",analysis.toString()).query(UUID.class).optional().map(id->view(id,request)).orElse(Map.of());}
  public Map<String,Object> view(UUID id,HttpServletRequest request){owner(id,request);var row=load(id);var out=new LinkedHashMap<>(row);out.remove("owner");out.put("runId",id.toString());out.put("deadline",row.get("deadline").toString());out.put("requests",requests(id));out.put("cost",cost(id));out.put("drafts",db.sql("SELECT id,payload::text FROM optimization_run_drafts WHERE run_id=:id ORDER BY round_number").param("id",id).query((rs,n)->Map.of("draftId",rs.getString(1),"payload",util.read(rs.getString(2)))).list());out.put("events",db.sql("SELECT payload::text FROM optimization_run_events WHERE run_id=:id ORDER BY created_at,id").param("id",id).query((rs,n)->util.read(rs.getString(1))).list());out.put("researchOnly",Boolean.TRUE.equals(map(row.get("grant")).get("researchOnly")));out.put("promptApprovalAllowed",!Boolean.TRUE.equals(map(row.get("grant")).get("researchOnly")));out.put("imageGenerationAllowed",false);out.put("renderAuthorized",false);out.put("officialCpqGrading","INACTIVE");return out;}
  public Map<String,Object> stop(UUID id,HttpServletRequest request){owner(id,request);db.sql("UPDATE optimization_runs SET cancel_requested=true WHERE id=:id AND state IN ('READY','RUNNING','PAUSED')").param("id",id).update();event(id,Map.of("state","CANCEL_REQUESTED","notice","In-flight inference remains potentially chargeable; outcome will be collected"));return view(id,request);}
  public Map<String,Object> resume(UUID id,HttpServletRequest request){owner(id,request);throw new ResponseStatusException(CONFLICT,"Terminal/ambiguous runs cannot resume or replay requests. Start a freshly authorized scope for new work.");}
  List<Map<String,Object>> requests(UUID id){return db.sql("SELECT id,round_number,role,state,reserved_usd,response::text FROM optimization_run_requests WHERE run_id=:id ORDER BY created_at,id").param("id",id).query((rs,n)->Map.<String,Object>of("requestId",rs.getString(1),"round",rs.getInt(2),"role",rs.getString(3),"state",rs.getString(4),"reservedUsd",rs.getDouble(5),"response",util.read(Objects.toString(rs.getString(6),"{}")))).list();}
  Map<String,Object> cost(UUID id){double spent=0,reserved=0,unknown=0;for(var r:requests(id)){var response=map(r.get("response"));if(response.get("costUsd") instanceof Number n)spent+=n.doubleValue();else if(Set.of("AUTHORIZED","DISPATCHING").contains(r.get("state")))reserved+=((Number)r.get("reservedUsd")).doubleValue();else unknown+=((Number)r.get("reservedUsd")).doubleValue();}return Map.of("spentUsd",spent,"reservedUsd",reserved,"unknownReservedUsd",unknown,"accountingComplete",unknown==0);}
  Map<String,Object> failure(Exception error,String layer){
    var f=new LinkedHashMap<String,Object>();f.put("layer",layer);f.put("exceptionCategory",error.getClass().getSimpleName());f.put("causeCategory",error.getCause()==null?"":error.getCause().getClass().getSimpleName());f.put("responseReceived",error instanceof com.pompomhills.intelligence.quality.MlWorkflowException);f.put("httpStatus",error instanceof com.pompomhills.intelligence.quality.MlWorkflowException m?m.statusCode():null);f.put("timeoutSeconds",130);f.put("retrySafe",false);return f;
  }
  void event(UUID id,Map<String,Object> payload){db.sql("INSERT INTO optimization_run_events(id,run_id,payload) VALUES(:event,:id,CAST(:payload AS jsonb))").param("event",UUID.randomUUID()).param("id",id).param("payload",util.encode(payload)).update();}
  void transition(UUID id,String state,Map<String,Object> progress,String reason){var next=new LinkedHashMap<>(progress);next.put("reason",reason);int changed=db.sql("UPDATE optimization_runs SET state=:state,progress=CAST(:p AS jsonb),lease_started=NULL WHERE id=:id AND state='RUNNING'").param("state",state).param("p",util.encode(next)).param("id",id).update();if(changed==1)event(id,Map.of("state",state,"phase",next.get("phase"),"round",next.get("round"),"reason",reason));}
  @Scheduled(fixedDelayString="${pompom.optimization.poll-delay-ms:2000}")
  public void processNext(){
    db.sql("UPDATE optimization_runs SET state='STOPPED',progress=progress || '{\"reason\":\"UNCERTAIN_WORKER_INTERRUPTION_NO_RETRY\"}'::jsonb WHERE state='RUNNING' AND lease_started<now()-interval '4 minutes'").update();
    var claimed=db.sql("WITH picked AS(SELECT id FROM optimization_runs WHERE state='READY' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) UPDATE optimization_runs r SET state='RUNNING',lease_started=now() FROM picked WHERE r.id=picked.id RETURNING r.id").query(UUID.class).optional();
    if(claimed.isEmpty())return;UUID id=claimed.get();var row=load(id);var progress=new LinkedHashMap<>(map(row.get("progress")));
    try{step(id,row,progress);}catch(Exception e){progress.put("failure",failure(e,"ORCHESTRATION_OR_ML_TRANSPORT"));transition(id,"STOPPED",progress,"SHARED_TECHNICAL_CONTRACT_FAILURE");}
  }
  void step(UUID id,Map<String,Object> row,Map<String,Object> progress){
    if(Boolean.TRUE.equals(row.get("cancel"))){transition(id,"STOPPED",progress,"OWNER_CANCELLED");return;}
    if(now().isAfter((Instant)row.get("deadline"))){transition(id,"STOPPED",progress,"TIME_LIMIT");return;}
    if(!realEnabled){transition(id,"STOPPED",progress,"DISPATCH_DISABLED");return;}
    var scope=map(row.get("scope"));
    // Durable worker boundary: eligibility is never carried forward from the
    // browser inspection or the original authorization.
    var currentFeasibility=targetAwareSnapshot(uuid(scope.get("analysisId")));
    var grant=map(row.get("grant"));
    if(!Boolean.TRUE.equals(currentFeasibility.get("generationAllowed"))&&!researchAllowed(currentFeasibility,grant)){
      progress.put("targetAwarePreflight",currentFeasibility);
      transition(id,"STOPPED",progress,String.valueOf(currentFeasibility.getOrDefault("state","TARGET_BLOCKED")));
      return;
    }
    var fresh=boundScope(uuid(scope.get("analysisId")),String.valueOf(scope.get("baselinePrompt")),currentFeasibility);
    if(!hash(util.encode(fresh)).equals(row.get("scopeSha256"))){transition(id,"STOPPED",progress,"SCOPE_CHANGED_FRESH_AUTHORIZATION_REQUIRED");return;}
    String phase=String.valueOf(progress.get("phase"));
    if(phase.equals("EVALUATE_BASELINE")){
      var evaluated=local("EVALUATE",Map.of("scope",scope,"prompt",progress.get("bestPrompt")));progress.put("baselineEvaluation",evaluated);progress.put("bestEvaluation",evaluated);
      if(!"NO_DETECTED_CONTRADICTION".equals(map(evaluated.get("integrity")).get("status"))){progress.put("evaluationIntegrity",evaluated.get("integrity"));transition(id,"STOPPED",progress,"EVALUATION_INTEGRITY_PROBLEM");return;}
      if(((Number)map(evaluated.get("canonical")).get("score")).doubleValue()>=92&&!Boolean.TRUE.equals(grant.get("researchOnly"))){transition(id,"COMPLETED",progress,"TARGET_REACHED_REVIEW_REQUIRED");return;}
      progress.put("phase","GENERATION");transition(id,"READY",progress,"");return;
    }
    int round=((Number)progress.get("round")).intValue();
    if(phase.equals("GENERATION")&&round>=((Number)grant.get("maxRounds")).intValue()){transition(id,"STOPPED",progress,"ROUND_LIMIT");return;}
    var cost=cost(id);if(!Boolean.TRUE.equals(cost.get("accountingComplete"))){transition(id,"STOPPED",progress,"UNCERTAIN_PROVIDER_ACCOUNTING");return;}
    if(requests(id).size()>=((Number)grant.get("maxRequests")).intValue()){transition(id,"STOPPED",progress,"REQUEST_LIMIT");return;}
    String generator=String.valueOf(progress.getOrDefault("generatorProfile", "OPENAI_ONLY".equals(grant.get("mode"))?"openai-escalation":"deepseek-primary"));
    if(phase.equals("GENERATION")){round++;progress.put("round",round);if("ADAPTIVE".equals(grant.get("mode"))&&round>1&&((Number)progress.get("noProgressRounds")).intValue()>0)generator="openai-escalation";progress.put("generatorProfile",generator);progress.put("parentPrompt",progress.get("bestPrompt"));progress.put("parentEvaluation",progress.get("bestEvaluation"));progress.put("parentDraftId",progress.get("bestDraftId"));}
    final String selectedGenerator=generator, selectedRole=phase;
    var op=rows(grant.get("operations")).stream().filter(o->selectedRole.equals(o.get("role")) && (selectedRole.equals("GENERATION")?selectedGenerator.equals(o.get("profileId")):!selectedGenerator.equals(o.get("profileId")))).findFirst().orElseThrow(()->new IllegalStateException("Role/model outside grant"));
    double cap=((Number)op.get("maxCostUsd")).doubleValue();double committed=((Number)cost.get("spentUsd")).doubleValue()+((Number)cost.get("reservedUsd")).doubleValue()+((Number)cost.get("unknownReservedUsd")).doubleValue();
    if(cap+committed>((Number)grant.get("maxTotalUsd")).doubleValue()+1e-9){transition(id,"STOPPED",progress,"BUDGET_LIMIT");return;}
    String prompt=String.valueOf(phase.equals("GENERATION")?progress.get("bestPrompt"):map(progress.get("pendingCandidate")).get("prompt"));
    var dispatchScope=new LinkedHashMap<>(scope);
    var input=new LinkedHashMap<String,Object>();input.put("scope",dispatchScope);input.put("role",phase);input.put("prompt",prompt);input.put("round",round);input.put("candidateId",id+":"+round);input.put("feedback",progress.getOrDefault("lastAssessment",Map.of()));input.put("authorization",op);input.put("timeoutSeconds",Math.max(1,Math.min(120,Duration.between(now(),(Instant)row.get("deadline")).toSeconds())));
    local("PREFLIGHT_REQUEST",input); // Capability, schema, token/cost bound checked before reservation.
    if(Boolean.TRUE.equals(load(id).get("cancel"))){transition(id,"STOPPED",progress,"OWNER_CANCELLED");return;}
    UUID requestId=UUID.randomUUID();input.put("requestId",requestId.toString());
    db.sql("INSERT INTO optimization_run_requests(id,run_id,round_number,role,input,input_sha256,authorization_payload,reserved_usd,state) VALUES(:req,:run,:round,:role,CAST(:input AS jsonb),:hash,CAST(:auth AS jsonb),:cap,'AUTHORIZED')").param("req",requestId).param("run",id).param("round",round).param("role",phase).param("input",util.encode(input)).param("hash",hash(util.encode(input))).param("auth",util.encode(op)).param("cap",cap).update();
    if(db.sql("UPDATE optimization_run_requests SET state='DISPATCHING' WHERE id=:req AND state='AUTHORIZED' AND EXISTS(SELECT 1 FROM optimization_runs r WHERE r.id=run_id AND r.state='RUNNING' AND NOT r.cancel_requested AND r.deadline>now())").param("req",requestId).update()!=1){transition(id,"STOPPED",progress,Boolean.TRUE.equals(load(id).get("cancel"))?"OWNER_CANCELLED":"TIME_LIMIT_OR_LEASE_EXPIRED");return;}
    event(id,Map.of("state","DISPATCHING","round",round,"role",phase,"requestId",requestId.toString(),"profileId",op.get("profileId")));
    Map<String,Object> response;
    try{response=ml.workflow("cpq-pilot/optimization-loop-execute",input);}catch(Exception e){response=new LinkedHashMap<>();response.put("executionStatus","FAILED_OR_AMBIGUOUS");response.put("usageAccountingStatus","INCOMPLETE");response.put("failure",failure(e,"BACKEND_ML_TRANSPORT"));}
    String state="COMPLETED".equals(response.get("executionStatus"))?"COMPLETED":"FAILED_OR_AMBIGUOUS";
    if(state.equals("COMPLETED")&&(!(response.get("costUsd") instanceof Number n)||!Double.isFinite(n.doubleValue())||n.doubleValue()<0||n.doubleValue()>cap||!"COMPLETE".equals(response.get("usageAccountingStatus"))||!Objects.equals(op.get("model"),response.get("model"))||!Objects.equals(op.get("provider"),response.get("provider"))))state="FAILED_OR_AMBIGUOUS";
    db.sql("UPDATE optimization_run_requests SET response=CAST(:response AS jsonb),state=:state,completed_at=now() WHERE id=:req AND state='DISPATCHING'").param("response",util.encode(response)).param("state",state).param("req",requestId).update();
    if(!state.equals("COMPLETED")){
      var failure=map(response.getOrDefault("failure",Map.of("layer","RESPONSE_CONTRACT","retrySafe",false)));
      progress.put("failure",failure);progress.put("providerOutcome",response.getOrDefault("providerOutcome","UNKNOWN"));
      progress.put("billingStatus",response.getOrDefault("billingStatus","UNKNOWN"));progress.put("processingOutcome",response.getOrDefault("processingOutcome","UNKNOWN"));
      boolean received="RESPONSE_RECEIVED".equals(response.get("providerOutcome"))&&"COMPLETE".equals(response.get("usageAccountingStatus"));
      transition(id,"STOPPED",progress,received?"LOCAL_POST_RESPONSE_VALIDATION_FAILED":"UNCERTAIN_PROVIDER_DISPATCH_OR_CONTRACT");return;
    }
    if(Boolean.TRUE.equals(load(id).get("cancel"))){transition(id,"STOPPED",progress,"OWNER_CANCELLED_AFTER_COLLECTING_INFLIGHT");return;}
    var result=map(response.get("result"));
    if(phase.equals("GENERATION")){
      var candidates=rows(result.get("candidates"));if(candidates.isEmpty()){
        var rejected=rows(result.get("rejectedProposals"));String reason=String.valueOf(result.getOrDefault("noImprovementReason",""));progress.put("lastAssessment",result);
        if(rejected.stream().anyMatch(r->String.valueOf(r.get("classification")).contains("CONTRACT"))){transition(id,"STOPPED",progress,"SHARED_TECHNICAL_CONTRACT_FAILURE");return;}
        if(!reason.isBlank()&&!reason.equals("null")){transition(id,"STOPPED",progress,"NO_JUSTIFIED_IMPROVEMENT");return;}
        if(rejected.stream().anyMatch(r->"STORY_CHANGE_REQUIRES_APPROVAL".equals(r.get("classification")))){transition(id,"STOPPED",progress,"BLOCKED_BY_PROTECTED_CONSTRAINT");return;}
        int repeats=((Number)progress.get("equivalentRounds")).intValue()+1;progress.put("equivalentRounds",repeats);progress.put("noProgressRounds",((Number)progress.get("noProgressRounds")).intValue()+1);transition(id,repeats>=2?"STOPPED":"READY",progress,repeats>=2?"REPEATED_EQUIVALENT_CANDIDATES":"");return;
      }
      if(candidates.size()!=1)throw new IllegalStateException("One generated candidate per round");var candidate=candidates.getFirst();String text=String.valueOf(candidate.get("prompt"));var evaluation=local("EVALUATE",Map.of("scope",scope,"prompt",text));
      UUID draft=UUID.randomUUID();var payload=new LinkedHashMap<>(candidate);payload.put("evaluation",evaluation);payload.put("generationRequestId",requestId.toString());payload.put("parentDraftId",progress.get("parentDraftId"));payload.put("round",round);
      db.sql("INSERT INTO optimization_run_drafts(id,run_id,parent_id,round_number,prompt_sha256,payload) VALUES(:draft,:run,CAST(NULLIF(:parent,'') AS uuid),:round,:hash,CAST(:payload AS jsonb))").param("draft",draft).param("run",id).param("parent",String.valueOf(progress.get("parentDraftId"))).param("round",round).param("hash",hash(text)).param("payload",util.encode(payload)).update();progress.put("pendingDraftId",draft.toString());progress.put("pendingCandidate",candidate);progress.put("pendingEvaluation",evaluation);
      if(!"NO_DETECTED_CONTRADICTION".equals(map(evaluation.get("integrity")).get("status"))){progress.put("evaluationIntegrity",evaluation.get("integrity"));transition(id,"STOPPED",progress,"EVALUATION_INTEGRITY_PROBLEM");return;}
      progress.put("phase","SOURCE_FIDELITY");transition(id,"READY",progress,"");return;
    }
    if(phase.equals("SOURCE_FIDELITY")){progress.put("sourceReview",result);progress.put("phase","CRITIC");transition(id,"READY",progress,"");return;}
    var assessment=local("COMPARE",Map.of("scope",scope,"candidate",progress.get("pendingCandidate"),"parentPrompt",progress.get("parentPrompt"),"parentEvaluation",progress.get("parentEvaluation"),"baselineEvaluation",progress.get("baselineEvaluation"),"sourceReview",progress.get("sourceReview"),"criticReview",result));
    assessment.put("draftId",progress.get("pendingDraftId"));event(id,Map.of("state","ROUND_EVALUATED","round",round,"assessment",assessment));progress.put("lastAssessment",assessment);
    if(Boolean.TRUE.equals(assessment.get("retained"))){progress.put("bestPrompt",map(progress.get("pendingCandidate")).get("prompt"));progress.put("bestDraftId",progress.get("pendingDraftId"));progress.put("bestEvaluation",assessment.get("evaluation"));progress.put("noProgressRounds",0);}else progress.put("noProgressRounds",((Number)progress.get("noProgressRounds")).intValue()+1);
    if("TARGET_REACHED_REVIEW_REQUIRED".equals(assessment.get("targetState"))){progress.put("reviewCandidateId",progress.get("pendingDraftId"));transition(id,"COMPLETED",progress,"TARGET_REACHED_REVIEW_REQUIRED");return;}
    progress.put("phase","GENERATION");transition(id,((Number)progress.get("noProgressRounds")).intValue()>=2?"STOPPED":"READY",progress,((Number)progress.get("noProgressRounds")).intValue()>=2?"NO_DEFENSIBLE_PROGRESS":"");
  }
}
