package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.pompomhills.intelligence.quality.QualityMlClient;
import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

/** CPQ previews and authenticated immutable fidelity/calibration evidence. */
@Service
public class CreativePromptQualityService {
  public static final String RUBRIC = "creative-prompt-quality-v1";
  private static final List<String> DIMENSIONS = List.of("SCROLL_STOP_VISUAL_PROMISE", "CAUSAL_PROGRESSION", "VISUAL_STORYTELLING", "PRODUCTION_EXECUTABILITY", "ENDING_REPLAY", "DISTINCTIVE_CREATIVE_VALUE");
  private final JdbcClient jdbc;
  private final ObjectMapper json;
  private final QualityMlClient ml;
  private final WorkflowService workflow;
  @org.springframework.beans.factory.annotation.Value("${pompom.library-root:${pompom.data-root:/tmp/pompom-data}/library}")
  private String libraryRoot;
  private static final String ORIGINAL_CONTRACT = "original-fidelity-v2";
  private static final List<String> STORY_ANCHORS = List.of("CHARACTER_IDENTITY", "APPROVED_EVENTS", "EVENT_ORDER", "PHYSICAL_RULE", "TEMPORAL_CONSTRAINTS", "REQUIRED_ENDING");

  public CreativePromptQualityService(JdbcClient jdbc, ObjectMapper json, QualityMlClient ml, WorkflowService workflow) {
    this.jdbc=jdbc; this.json=json; this.ml=ml; this.workflow=workflow;
  }

  private Map<String,Object> read(String text) {
    try { return json.readValue(text,new TypeReference<Map<String,Object>>(){}); }
    catch(Exception error) { throw new IllegalStateException("Saved CPQ evidence is invalid",error); }
  }
  @SuppressWarnings("unchecked") private static Map<String,Object> map(Object value) {return value instanceof Map<?,?>?(Map<String,Object>)value:Map.of();}
  @SuppressWarnings("unchecked") private static List<Map<String,Object>> maps(Object value) {return value instanceof List<?>?(List<Map<String,Object>>)value:List.of();}
  private String encode(Object value) {try{return json.copy().enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS).writeValueAsString(value);}catch(Exception e){throw new IllegalStateException(e);}}
  private static String hash(String value) {try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
  private static String principal(HttpServletRequest request, String role) {
    if(request.getUserPrincipal()==null || request.getUserPrincipal().getName()==null || request.getUserPrincipal().getName().isBlank() || !request.isUserInRole(role))
      throw new ResponseStatusException(FORBIDDEN,"Authenticated "+role+" authority is required");
    return request.getUserPrincipal().getName();
  }
  private Map<String,Object> event(UUID id,String kind) {
    return jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id AND kind=:kind")
      .param("id",id).param("kind",kind).query(String.class).optional().map(this::read)
      .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Bound workflow evidence not found"));
  }
  private Map<String,Object> baseline(UUID analysisId) {return event(analysisId,"REVIEW");}
  private Map<String,Object> comparison(UUID analysisId) {
    return jdbc.sql("SELECT id,payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_OPTIMIZATION' AND payload->>'sourceAnalysisId'=:analysis ORDER BY created_at DESC,id DESC LIMIT 1")
      .param("analysis",analysisId.toString()).query((rs,n)->{var x=read(rs.getString(2));x.put("recordId",rs.getString(1));return x;}).optional()
      .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"No persisted optimization comparison is available"));
  }
  private Map<String,Object> comparison(UUID analysisId, UUID comparisonId) {
    var value=jdbc.sql("SELECT id,payload::text FROM post_family_workflow_events WHERE id=:id AND kind='CREATIVE_OPTIMIZATION' AND payload->>'sourceAnalysisId'=:analysis")
      .param("id",comparisonId).param("analysis",analysisId.toString())
      .query((rs,n)->{var x=read(rs.getString(2));x.put("recordId",rs.getString(1));return x;}).optional()
      .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Comparison is not bound to this analysis"));
    return value;
  }
  private Map<String,Object> candidate(Map<String,Object> comparison,String candidateId) {
    return maps(comparison.get("candidates")).stream().filter(c->candidateId.equals(c.get("candidateId"))).findFirst()
      .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Candidate is not part of the immutable saved comparison"));
  }
  private Map<String,Object> sourceStory(Map<String,Object> baseline,Map<String,Object> candidate,Map<String,Object> comparison) {
    var roleId=String.valueOf(comparison.getOrDefault("roleRecordId",""));
    if("null".equals(roleId)) roleId="";
    Map<String,Object> role=Map.of();
    if(!roleId.isBlank()) role=event(UUID.fromString(roleId),"CREATIVE_ROLE");
    var sourceRequest=map(role.get("sourceRequest"));var context=map(sourceRequest.get("context"));
    long content=((Number)baseline.get("contentId")).longValue(), prompt=((Number)baseline.get("promptVersionId")).longValue();
    var session=jdbc.sql("SELECT id,payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1")
      .param("content",String.valueOf(content)).param("prompt",String.valueOf(prompt)).query((rs,n)->Map.entry(rs.getString(1),read(rs.getString(2)))).optional()
      .orElseThrow(()->new ResponseStatusException(CONFLICT,"Approved story provenance is unavailable"));
    var sessionPayload=session.getValue();
    Object approvalId=sessionPayload.get("approvalRecordId");
    if(approvalId==null) throw new ResponseStatusException(CONFLICT,"Approved story revision is unavailable");
    var approval=event(UUID.fromString(String.valueOf(approvalId)),"STORY_APPROVAL");
    var verified=verifiedStory(sessionPayload,context);
    String story=text(verified.get("text"));
    var out=new LinkedHashMap<String,Object>();out.put("text",story);out.put("approval",approval);out.put("session",sessionPayload);out.put("roleContext",context);out.put("approvalRecordId",String.valueOf(approvalId));
    out.put("verified",verified);
    return out;
  }
  private Map<String,Object> verifiedStory(Map<String,Object> session,Map<String,Object> context) {
    String id=text(session.getOrDefault("sourceStoryRecordId",session.get("storyRecordId")));
    if(session.get("sourceStoryRecordId")!=null && session.get("storyRecordId")!=null && !text(session.get("sourceStoryRecordId")).equals(text(session.get("storyRecordId"))))
      throw new ResponseStatusException(CONFLICT,"SOURCE_APPROVAL_CONFLICT: story identifiers disagree");
    String approval=text(session.get("approvalRecordId"));
    var verified=workflow.approvedStoryForCpq(uuid(id,"SOURCE_APPROVAL_REQUIRED"),uuid(approval,"SOURCE_APPROVAL_REQUIRED"));
    for(var pair:Map.of("storyId","storyId","sourceStoryRecordId","storyId","storyApprovalRecordId","approvalRecordId","approvalRecordId","approvalRecordId","storyRevisionId","revision","approvedStoryText","text").entrySet())
      if(context.get(pair.getKey())!=null && !text(context.get(pair.getKey())).equals(text(verified.get(pair.getValue()))))
        throw new ResponseStatusException(CONFLICT,"SOURCE_APPROVAL_CONFLICT: "+pair.getKey());
    if(session.get("storyRevisionId")!=null && !text(session.get("storyRevisionId")).equals(verified.get("revision")))throw new ResponseStatusException(CONFLICT,"SOURCE_APPROVAL_CONFLICT: stale revision");
    return verified;
  }
  private Map<String,Object> savedProduction(long content,long promptId,String prompt,Map<String,Object> event,Map<String,Object> authority) {
    var merged=new LinkedHashMap<String,Object>(event);
    var execution=new LinkedHashMap<String,Object>(map(event.get("settings")));
    if(event.get("aspectRatio")!=null) {
      if(execution.get("aspectRatio")!=null && !execution.get("aspectRatio").equals(event.get("aspectRatio")))throw new ResponseStatusException(CONFLICT,"PRODUCTION_SETTINGS_CONFLICT: aspectRatio");
      execution.put("aspectRatio",event.get("aspectRatio"));
    }
    var rows=jdbc.sql("SELECT id::text,payload::text FROM post_family_workflow_events WHERE kind='REVIEW' AND payload->>'contentId'=:c AND payload->>'promptVersionId'=:p ORDER BY created_at DESC,id DESC LIMIT 1")
      .param("c",String.valueOf(content)).param("p",String.valueOf(promptId)).query((rs,n)->Map.entry(rs.getString(1),read(rs.getString(2)))).list();
    if(!rows.isEmpty()) {
      var row=rows.getFirst();var bound=map(row.getValue().get("boundRequest"));
      if(!prompt.equals(bound.get("prompt")))throw new ResponseStatusException(CONFLICT,"PRODUCTION_SETTINGS_CONFLICT: analysis source prompt");
      for(String key:List.of("contentProfile","generator","desiredDuration","openingStrategy"))
        if(event.get(key)!=null && bound.get(key)!=null && !text(event.get(key)).equals(text(bound.get(key))))throw new ResponseStatusException(CONFLICT,"PRODUCTION_SETTINGS_CONFLICT: "+key);
      for(var entry:map(bound.get("settings")).entrySet()) {
        if(execution.containsKey(entry.getKey()) && !execution.get(entry.getKey()).equals(entry.getValue()))throw new ResponseStatusException(CONFLICT,"PRODUCTION_SETTINGS_CONFLICT: "+entry.getKey());
        execution.put(entry.getKey(),entry.getValue());
      }
      authority.put("executionAnalysisId",row.getKey());
    }
    merged.put("settings",execution);
    return normalizedSettings(merged);
  }
  private String savedPrompt(long contentId,long promptVersionId) {
    return jdbc.sql("SELECT raw_text FROM prompt_versions WHERE content_id=:content AND id=:prompt")
      .param("content",contentId).param("prompt",promptVersionId).query(String.class).optional()
      .orElseThrow(()->new ResponseStatusException(CONFLICT,"Immutable source prompt is unavailable"));
  }
  private Map<String,Object> currentFidelity(UUID analysisId,UUID comparisonId,String candidateId,String storyHash,String sourceHash,String candidateHash,String interventionHash,String settingsHash,String ruleset) {
    var matches=jdbc.sql("SELECT evidence_id,decision,reviewer_principal,review_method_version,citations,rationale,valid_until,created_at FROM cpq_fidelity_reviews f WHERE subject_type='OPTIMIZATION_CANDIDATE' AND NOT EXISTS(SELECT 1 FROM cpq_fidelity_reviews s WHERE s.supersedes_evidence_id=f.evidence_id) AND analysis_id=:analysis AND comparison_id=:comparison AND candidate_prompt_fingerprint=:candidate AND approved_story_fingerprint=:story AND original_prompt_fingerprint=:source AND intervention_fingerprint=:intervention AND production_settings_fingerprint=:settings AND ruleset_version=:ruleset AND (valid_until IS NULL OR valid_until>now()) ORDER BY created_at DESC")
      .param("analysis",analysisId).param("comparison",comparisonId).param("candidate",candidateHash).param("story",storyHash).param("source",sourceHash).param("intervention",interventionHash).param("settings",settingsHash).param("ruleset",ruleset)
      .query((rs,n)->{var x=new LinkedHashMap<String,Object>();x.put("evidenceId",rs.getString("evidence_id"));x.put("decision",rs.getString("decision"));x.put("reviewerPrincipal",rs.getString("reviewer_principal"));x.put("reviewMethodVersion",rs.getString("review_method_version"));x.put("citations",readJsonList(rs.getString("citations")));x.put("rationale",rs.getString("rationale"));x.put("validUntil",rs.getTimestamp("valid_until")==null?"":rs.getTimestamp("valid_until").toInstant().toString());x.put("createdAt",rs.getTimestamp("created_at").toInstant().toString());return x;}).list();
    if(matches.isEmpty()){var x=new LinkedHashMap<String,Object>();x.put("evidenceId",null);x.put("decision","UNKNOWN");x.put("reason","No current immutable independent review matches every binding.");return x;}
    var decisions=matches.stream().map(review->String.valueOf(review.get("decision"))).collect(java.util.stream.Collectors.toSet());
    if(decisions.size()>1){var conflict=new LinkedHashMap<String,Object>();conflict.put("evidenceId",null);conflict.put("decision","UNKNOWN");conflict.put("reason","Conflicting current independent reviews require adjudication.");conflict.put("conflictingEvidenceIds",matches.stream().map(review->review.get("evidenceId")).toList());return conflict;}
    return matches.getFirst();
  }
  private Object readJsonList(String value) {try{return json.readValue(value,Object.class);}catch(Exception e){return List.of();}}

  private Map<String,Object> candidateBinding(UUID analysisId,Map<String,Object> baseline,Map<String,Object> comparison,Map<String,Object> candidate) {
    var reasons=new ArrayList<String>();
    long content=((Number)baseline.get("contentId")).longValue(), promptId=((Number)baseline.get("promptVersionId")).longValue();
    String original=savedPrompt(content,promptId), candidatePrompt=String.valueOf(candidate.getOrDefault("prompt",""));
    String sourceHash=hash(original), candidateHash=hash(candidatePrompt);
    var bound=map(baseline.get("boundRequest"));var canonical=map(baseline.get("canonicalRuleEvaluation"));
    String ruleset=String.valueOf(canonical.getOrDefault("rulesetVersion","UNKNOWN"));
    if(!original.equals(bound.get("prompt")) || !sourceHash.equals(comparison.get("sourcePromptSha256"))) reasons.add("SOURCE_PROMPT_FINGERPRINT_MISMATCH");
    if(!String.valueOf(promptId).equals(String.valueOf(comparison.get("sourcePromptVersionId")))) reasons.add("SOURCE_PROMPT_VERSION_MISMATCH");
    if(!ruleset.equals(String.valueOf(comparison.get("rulesetVersion")))) reasons.add("RULESET_MISMATCH");
    String roleId=String.valueOf(comparison.getOrDefault("roleRecordId",""));
    Map<String,Object> role=Map.of();
    try { if(!roleId.isBlank() && !"null".equals(roleId)) role=event(UUID.fromString(roleId),"CREATIVE_ROLE"); }
    catch(Exception ignored) { reasons.add("PROVIDER_ROLE_EVIDENCE_MISSING"); }
    var context=map(map(role.get("sourceRequest")).get("context"));
    if(!String.valueOf(content).equals(String.valueOf(context.get("contentId")))) reasons.add("CONTENT_BINDING_MISMATCH");
    if(!String.valueOf(promptId).equals(String.valueOf(context.get("promptVersionId")))) reasons.add("ROLE_PROMPT_BINDING_MISMATCH");
    if(!sourceHash.equals(hash(String.valueOf(map(role.get("sourceRequest")).getOrDefault("text",""))))) reasons.add("ROLE_SOURCE_FINGERPRINT_MISMATCH");
    var candidateReview=map(candidate.get("review"));
    var candidateCanonical=map(candidateReview.get("canonicalRuleEvaluation"));
    if(!"EVALUATED".equals(candidateCanonical.get("status"))) reasons.add("CANDIDATE_CANONICAL_EVALUATION_NOT_VERIFIED");
    if(!String.valueOf(ruleset).equals(String.valueOf(candidateCanonical.get("rulesetVersion")))) reasons.add("CANDIDATE_CANONICAL_RULESET_MISMATCH");
    var evaluation=map(candidateReview.get("boundRequest"));
    for(String key:List.of("contentProfile","generator","desiredDuration","settings"))
      if(!Objects.equals(bound.get(key),evaluation.get(key))) reasons.add("CANDIDATE_PRODUCTION_BINDING_MISMATCH:"+key);
    if(candidatePrompt.isBlank() || maps(map(role.get("result")).get("candidates")).stream().filter(c->Objects.equals(c.get("candidateId"),candidate.get("candidateId")) && Objects.equals(c.get("prompt"),candidatePrompt)).count()!=1)
      reasons.add("CANDIDATE_IDENTITY_OR_FINGERPRINT_UNVERIFIED");
    try {
      var story=sourceStory(baseline,candidate,comparison);
      String storyHash=hash(String.valueOf(story.get("text")));
      var approval=map(story.get("approval"));
      if(!storyHash.equals(hash(String.valueOf(approval.getOrDefault("approvedText",""))))) reasons.add("APPROVED_STORY_FINGERPRINT_MISMATCH");
      var approvedId=String.valueOf(story.get("approvalRecordId"));
      if(context.get("storyApprovalRecordId")!=null && !approvedId.equals(String.valueOf(context.get("storyApprovalRecordId")))) reasons.add("APPROVED_STORY_REVISION_MISMATCH");
    } catch(RuntimeException missing) { reasons.add("APPROVED_STORY_BINDING_UNAVAILABLE"); }
    UUID latest=jdbc.sql("SELECT id FROM post_family_workflow_events WHERE kind='REVIEW' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1")
      .param("content",String.valueOf(content)).param("prompt",String.valueOf(promptId)).query(UUID.class).optional().orElse(null);
    if(!analysisId.equals(latest)) reasons.add("ANALYSIS_IS_NOT_CURRENT_FOR_SOURCE_PROMPT");
    Long latestPrompt=jdbc.sql("SELECT max(id) FROM prompt_versions WHERE content_id=:content").param("content",content).query(Long.class).single();
    if(!Objects.equals(promptId,latestPrompt)) reasons.add("PROMPT_VERSION_IS_NOT_CURRENT");
    var currentSettings=jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='PRODUCTION_SETTINGS' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC LIMIT 1")
      .param("content",String.valueOf(content)).param("prompt",String.valueOf(promptId)).query(String.class).optional().map(this::read).orElse(Map.of());
    var target=map(context.get("targetConfiguration"));var boundSettings=map(bound.get("settings"));
    String targetDuration=String.valueOf(target.get("duration")), boundDuration=String.valueOf(bound.get("desiredDuration"));
    if(!Objects.equals(currentSettings.get("contentProfile"),target.get("contentProfile"))
        || !Objects.equals(bound.get("contentProfile"),target.get("contentProfile"))
        || !Objects.equals(currentSettings.get("generator"),target.get("generator"))
        || !Objects.equals(bound.get("generator"),target.get("generator"))
        || !Objects.equals(String.valueOf(currentSettings.get("desiredDuration")),boundDuration)
        || !Objects.equals(boundDuration,targetDuration)
        || !Objects.equals(boundSettings,target.get("settings"))
        || currentSettings.get("aspectRatio")!=null && !Objects.equals(currentSettings.get("aspectRatio"),boundSettings.get("aspectRatio"))
        || currentSettings.get("openingStrategy")!=null && !Objects.equals(currentSettings.get("openingStrategy"),bound.get("openingStrategy"))) reasons.add("PRODUCTION_SETTINGS_BINDING_MISMATCH");
    boolean providerRunMatches=Objects.equals(String.valueOf(context.get("analysisRunId")),analysisId.toString());
    if(!providerRunMatches) {
      var originalId=comparison.get("revalidatedFromComparisonId");
      if(originalId==null) reasons.add("PROVIDER_RESULT_BELONGS_TO_DIFFERENT_ANALYSIS");
      else try {
        var originalComparison=event(UUID.fromString(String.valueOf(originalId)),"CREATIVE_OPTIMIZATION");
        var originalRoleId=String.valueOf(originalComparison.get("roleRecordId"));
        boolean preserved=Objects.equals(originalRoleId,roleId)
          && Objects.equals(String.valueOf(originalComparison.get("sourceAnalysisId")),String.valueOf(context.get("analysisRunId")))
          && Objects.equals(originalComparison.get("sourcePromptVersionId"),comparison.get("sourcePromptVersionId"))
          && Objects.equals(originalComparison.get("sourcePromptSha256"),comparison.get("sourcePromptSha256"))
          && maps(originalComparison.get("candidates")).stream().anyMatch(old->Objects.equals(old.get("candidateId"),candidate.get("candidateId")) && Objects.equals(old.get("prompt"),candidatePrompt));
        if(!preserved) reasons.add("REVALIDATION_CHAIN_BINDING_MISMATCH");
      } catch(RuntimeException invalid) { reasons.add("REVALIDATION_SOURCE_UNAVAILABLE"); }
    }
    var result=new LinkedHashMap<String,Object>();result.put("status",reasons.isEmpty()?"COMPATIBLE":"READ_ONLY");result.put("assessmentAllowed",reasons.isEmpty());result.put("reasons",reasons);
    result.put("analysisId",analysisId.toString());result.put("comparisonId",comparison.get("recordId"));result.put("candidateId",candidate.get("candidateId"));
    result.put("contentId",content);result.put("promptVersionId",promptId);result.put("sourcePromptSha256",sourceHash);result.put("candidatePromptSha256",candidateHash);
    result.put("approvedStoryRevisionId",context.getOrDefault("storyApprovalRecordId","UNKNOWN"));result.put("approvedStorySha256",hash(String.valueOf(context.getOrDefault("approvedStoryText",""))));
    result.put("rulesetVersion",ruleset);var settingsOut=new LinkedHashMap<String,Object>();for(String key:List.of("contentProfile","generator","desiredDuration","settings"))settingsOut.put(key,bound.getOrDefault(key,"UNKNOWN"));result.put("productionSettings",settingsOut);
    return result;
  }

  public Map<String,Object> comparisonBindings(UUID analysisId, UUID comparisonId) {
    var baseline=baseline(analysisId);var comparison=comparison(analysisId,comparisonId);
    var rows=new ArrayList<Map<String,Object>>();for(var item:maps(comparison.get("candidates"))) {
      try { rows.add(candidateBinding(analysisId,baseline,comparison,item)); }
      catch(RuntimeException unavailable) {
        var denied=new LinkedHashMap<String,Object>();denied.put("status","READ_ONLY");denied.put("assessmentAllowed",false);denied.put("analysisId",analysisId.toString());denied.put("comparisonId",comparisonId.toString());denied.put("candidateId",item.get("candidateId"));denied.put("reasons",List.of("BINDING_EVIDENCE_UNAVAILABLE"));rows.add(denied);
      }
    }
    return Map.of("analysisId",analysisId.toString(),"comparisonId",comparisonId.toString(),"candidateBindings",rows);
  }

  public Map<String,Object> assess(UUID analysisId, UUID comparisonId, String candidateId, HttpServletRequest servlet) {
    String assessor=principal(servlet,"PRODUCTION_OPERATOR");
    var baseline=baseline(analysisId);var comparison=comparison(analysisId,comparisonId);var candidate=candidate(comparison,candidateId);
    var binding=candidateBinding(analysisId,baseline,comparison,candidate);
    if(!Boolean.TRUE.equals(binding.get("assessmentAllowed"))) throw new ResponseStatusException(CONFLICT,"Historical candidate is read-only: "+String.join(",",(List<String>)binding.get("reasons")));
    long content=((Number)baseline.get("contentId")).longValue(), promptId=((Number)baseline.get("promptVersionId")).longValue();
    UUID latest=jdbc.sql("SELECT id FROM post_family_workflow_events WHERE kind='REVIEW' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1").param("content",String.valueOf(content)).param("prompt",String.valueOf(promptId)).query(UUID.class).optional().orElse(null);
    if(!analysisId.equals(latest))throw new ResponseStatusException(CONFLICT,"CPQ assessment requires the current saved analysis for this prompt version");
    String original=savedPrompt(content,promptId),candidatePrompt=String.valueOf(candidate.get("prompt"));
    var bound=map(baseline.get("boundRequest"));var creative=map(map(candidate.get("currentAssessment")).get("creativeAssessment"));
    if(creative.isEmpty()) creative=map(candidate.get("creativeAssessment"));
    var review=map(candidate.get("review"));var canonical=map(review.get("canonicalRuleEvaluation"));var critic=map(review.get("executionReview"));
    var intervention=creative.getOrDefault("changeContract",List.of());String interventionHash=hash(encode(intervention));
    var run=jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_OPTIMIZATION_RUN' AND payload->'binding'->>'analysisId'=:analysis ORDER BY created_at DESC,id DESC LIMIT 1")
      .param("analysis",analysisId.toString()).query(String.class).optional().map(this::read).orElse(Map.of());
    var runBinding=map(run.get("binding"));var productionSettings=new LinkedHashMap<String,Object>();
    for(String key:List.of("contentProfile","generator","desiredDuration","settings","openingStrategy"))productionSettings.put(key,bound.get(key));
    var settingsHash=hash(encode(productionSettings));
    var story=sourceStory(baseline,candidate,comparison);String storyText=String.valueOf(story.get("text"));String storyHash=hash(storyText);
    String originalHash=hash(original),candidateHash=hash(candidatePrompt),ruleset=String.valueOf(canonical.getOrDefault("rulesetVersion",map(baseline.get("canonicalRuleEvaluation")).get("rulesetVersion")));
    var fidelity=currentFidelity(analysisId,comparisonId,candidateId,storyHash,originalHash,candidateHash,interventionHash,settingsHash,ruleset);
    var diagnosis=new LinkedHashMap<String,Object>();diagnosis.put("opportunities",maps(map(creative.get("diagnosis")).get("opportunities")));diagnosis.put("validatedMaterialChanges",intervention);diagnosis.put("canonicalFindings",canonical.getOrDefault("failedRules",List.of()));
    var assessRequest=new LinkedHashMap<String,Object>();assessRequest.put("originalPrompt",original);assessRequest.put("candidatePrompt",candidatePrompt);assessRequest.put("contentProfile",bound.getOrDefault("contentProfile","UNKNOWN"));assessRequest.put("generator",bound.getOrDefault("generator","UNKNOWN"));assessRequest.put("durationSeconds",bound.getOrDefault("desiredDuration",null));assessRequest.put("diagnosis",diagnosis);assessRequest.put("canonicalFindings",Map.of("rulesetVersion",ruleset,"score",canonical.getOrDefault("score",0),"grade",canonical.getOrDefault("grade","UNKNOWN"),"status",canonical.getOrDefault("status","UNKNOWN")));assessRequest.put("executionCritic",critic);
    var result=ml.workflow("creative-prompt-quality/assess",assessRequest);
    var fidelityOut=new LinkedHashMap<String,Object>();fidelityOut.put("decision",fidelity.getOrDefault("decision","UNKNOWN"));fidelityOut.put("evidenceId",fidelity.get("evidenceId"));fidelityOut.put("requiredForQualifiedGrade",true);
    result.put("sourceFidelity",fidelityOut);result.put("canonicalValidation",Map.of("rulesetVersion",ruleset,"score",canonical.get("score"),"grade",canonical.get("grade"),"status",canonical.get("status")));
    result.put("renderReadiness",Map.of("state","SEPARATE_F8_POLICY","authorized",false));result.put("analysisId",analysisId.toString());result.put("candidateId",candidateId);
    String bindingHash=hash(encode(List.of(analysisId.toString(),candidateId,originalHash,candidateHash,ruleset,RUBRIC,Objects.toString(fidelity.get("evidenceId"),"UNKNOWN"))));
    result.put("bindingSha256",bindingHash);result.put("calibrationActivation",jdbc.sql("SELECT activated FROM cpq_policy_state WHERE singleton=TRUE").query(Boolean.class).single());
    result.put("comparisonId",comparisonId.toString());result.put("assessedBy",assessor);result.put("sourceBinding",binding);
    jdbc.sql("INSERT INTO cpq_assessments(analysis_id,comparison_id,content_id,prompt_version_id,candidate_id,original_prompt_fingerprint,candidate_prompt_fingerprint,ruleset_version,rubric_version,calibration_corpus_version,fidelity_evidence_id,result) VALUES(:analysis,:comparison,:content,:prompt,:candidate,:original,:candidateHash,:ruleset,:rubric,NULL,:fidelity,CAST(:result AS jsonb))")
      .param("analysis",analysisId).param("comparison",comparisonId).param("content",content).param("prompt",promptId).param("candidate",candidateId).param("original",originalHash).param("candidateHash",candidateHash).param("ruleset",ruleset).param("rubric",RUBRIC).param("fidelity",fidelity.get("evidenceId"),java.sql.Types.OTHER).param("result",encode(result)).update();
    return result;
  }

  public Map<String,Object> savedAssessments(UUID analysisId) {
    var rows=jdbc.sql("SELECT assessment_id,comparison_id,candidate_id,result::text,created_at FROM cpq_assessments WHERE analysis_id=:analysis ORDER BY created_at DESC")
      .param("analysis",analysisId).query((rs,n)->{var x=read(rs.getString(4));x.put("assessmentId",rs.getString(1));x.put("comparisonId",rs.getString(2));x.put("candidateId",rs.getString(3));x.put("createdAt",rs.getTimestamp(5).toInstant().toString());return x;}).list();
    return Map.of("rubricVersion",RUBRIC,"gradingStatus","CALIBRATION_INCOMPLETE","candidateAssessments",rows,"activationState","INACTIVE","renderAuthorized",false);
  }

  @Transactional
  public Map<String,Object> reviewFidelity(UUID analysisId,UUID comparisonId,String candidateId,Map<String,Object> request,HttpServletRequest servlet) {
    String reviewer=principal(servlet,"EVIDENCE_REVIEWER");
    String decision=String.valueOf(request.get("decision"));if(!Set.of("PASS","FAIL","UNKNOWN").contains(decision)) throw new ResponseStatusException(BAD_REQUEST,"Decision must be PASS, FAIL or UNKNOWN");
    String rationale=String.valueOf(request.getOrDefault("rationale",""));if(rationale.trim().length()<20) throw new ResponseStatusException(BAD_REQUEST,"A concrete review rationale of at least 20 characters is required");
    String method=String.valueOf(request.getOrDefault("reviewMethodVersion","human-source-fidelity-v1"));if(!"human-source-fidelity-v1".equals(method))throw new ResponseStatusException(BAD_REQUEST,"Unsupported independent review method");
    var baseline=baseline(analysisId);long boundContent=((Number)baseline.get("contentId")).longValue(),boundPrompt=((Number)baseline.get("promptVersionId")).longValue();UUID latest=jdbc.sql("SELECT id FROM post_family_workflow_events WHERE kind='REVIEW' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1").param("content",String.valueOf(boundContent)).param("prompt",String.valueOf(boundPrompt)).query(UUID.class).optional().orElse(null);if(!analysisId.equals(latest))throw new ResponseStatusException(CONFLICT,"Fidelity review requires the current saved analysis for this prompt version");
    var comparison=comparison(analysisId,comparisonId);var candidate=candidate(comparison,candidateId);
    if(!Boolean.TRUE.equals(candidateBinding(analysisId,baseline,comparison,candidate).get("assessmentAllowed"))) throw new ResponseStatusException(CONFLICT,"Historical candidate is read-only until every source binding is verified");
    var story=sourceStory(baseline,candidate,comparison);
    String source=savedPrompt(((Number)baseline.get("contentId")).longValue(),((Number)baseline.get("promptVersionId")).longValue());String prompt=String.valueOf(candidate.get("prompt"));String approved=String.valueOf(story.get("text"));
    var citations=maps(request.get("citations"));if(citations.isEmpty())throw new ResponseStatusException(BAD_REQUEST,"At least one exact source or candidate quote is required");
    for(var citation:citations){String quote=String.valueOf(citation.getOrDefault("quote",""));String side=String.valueOf(citation.getOrDefault("side",""));if(quote.isBlank()||!("APPROVED_STORY".equals(side)?approved.contains(quote):"CANDIDATE_PROMPT".equals(side)&&prompt.contains(quote)))throw new ResponseStatusException(BAD_REQUEST,"Evidence citation must exactly match the bound approved story or candidate prompt");}
    var mappings=maps(request.get("sourceEventMapping"));
    for(var mapping:mappings){String from=String.valueOf(mapping.getOrDefault("sourceQuote","")),to=String.valueOf(mapping.getOrDefault("candidateQuote",""));if(from.isBlank()||to.isBlank()||!approved.contains(from)||!prompt.contains(to))throw new ResponseStatusException(BAD_REQUEST,"Source-event mappings must quote both bound source and candidate text");}
    if("PASS".equals(decision)&&mappings.isEmpty())throw new ResponseStatusException(BAD_REQUEST,"A fidelity PASS requires cited source-event mappings");
    Instant expiry;try{expiry=Instant.parse(String.valueOf(request.get("validUntil")));}catch(Exception e){throw new ResponseStatusException(BAD_REQUEST,"An explicit ISO-8601 validity expiry is required");}
    if(!expiry.isAfter(Instant.now())||expiry.isAfter(Instant.now().plusSeconds(180L*24*60*60)))throw new ResponseStatusException(BAD_REQUEST,"Review expiry must be within 180 days");
    long content=((Number)baseline.get("contentId")).longValue(),promptId=((Number)baseline.get("promptVersionId")).longValue();var canonical=map(baseline.get("canonicalRuleEvaluation"));
    var roleContext=map(story.get("roleContext"));var settings=map(map(baseline.get("boundRequest")).get("settings"));
    var creative=map(map(candidate.get("currentAssessment")).get("creativeAssessment"));if(creative.isEmpty())creative=map(candidate.get("creativeAssessment"));Object intervention=creative.getOrDefault("changeContract",List.of());
    var changedBeatIds=maps(intervention).stream().map(x->String.valueOf(x.getOrDefault("beatId","UNKNOWN"))).distinct().toList();
    if("PASS".equals(decision)) {
      var mappedBeatIds=mappings.stream().map(x->String.valueOf(x.getOrDefault("beatId",""))).collect(java.util.stream.Collectors.toSet());
      if(changedBeatIds.stream().anyMatch(id->!mappedBeatIds.contains(id)))throw new ResponseStatusException(BAD_REQUEST,"A PASS must map every changed beat to exact source and candidate quotes");
    }
    var settingsHash=hash(encode(settings));var sourceHash=hash(source);var candidateHash=hash(prompt);var storyHash=hash(approved);var interventionHash=hash(encode(intervention));
    String storyId=text(map(story.get("verified")).get("storyId"));
    String revision=text(map(story.get("verified")).get("revision"));
    if("UNKNOWN".equals(storyId)||"UNKNOWN".equals(revision))throw new ResponseStatusException(CONFLICT,"Approved story ID and revision binding are required for fidelity evidence");
    UUID evidenceId=UUID.randomUUID();
    var reviewSettings=new LinkedHashMap<String,Object>();for(String key:List.of("contentProfile","generator","desiredDuration","settings","openingStrategy"))reviewSettings.put(key,map(baseline.get("boundRequest")).get(key));
    UUID supersedes=null;
    if(request.get("supersedesEvidenceId")!=null) {
      supersedes=uuid(request.get("supersedesEvidenceId"),"Invalid candidate supersession");
      boolean same=jdbc.sql("SELECT EXISTS(SELECT 1 FROM cpq_fidelity_reviews WHERE evidence_id=:id AND subject_type='OPTIMIZATION_CANDIDATE' AND analysis_id=:analysis AND comparison_id=:comparison AND candidate_prompt_fingerprint=:candidate AND approved_story_fingerprint=:story AND original_prompt_fingerprint=:source)")
          .param("id",supersedes).param("analysis",analysisId).param("comparison",comparisonId).param("candidate",candidateHash).param("story",storyHash).param("source",sourceHash).query(Boolean.class).single();
      if(!same) throw new ResponseStatusException(CONFLICT,"Candidate supersession must preserve the exact immutable scope");
    }
    jdbc.sql("INSERT INTO cpq_fidelity_reviews(evidence_id,supersedes_evidence_id,content_id,prompt_version_id,approved_story_id,approved_revision,approved_story_fingerprint,original_prompt_fingerprint,candidate_prompt_fingerprint,intervention_fingerprint,changed_beat_ids,source_event_mapping,analysis_id,comparison_id,ruleset_version,cpq_rubric_version,production_settings_fingerprint,reviewer_principal,reviewer_authority,review_method_version,citations,rationale,decision,valid_until) VALUES(:id,:supersedes,:content,:promptId,:storyId,:revision,:story,:source,:candidate,:intervention,CAST(:beats AS jsonb),CAST(:mapping AS jsonb),:analysis,:comparison,:ruleset,:rubric,:settings,:reviewer,'EVIDENCE_REVIEWER',:method,CAST(:citations AS jsonb),:rationale,:decision,:expiry)")
      .param("id",evidenceId).param("supersedes",supersedes,java.sql.Types.OTHER).param("content",content).param("promptId",promptId).param("storyId",storyId).param("revision",revision).param("story",storyHash).param("source",sourceHash).param("candidate",candidateHash).param("intervention",interventionHash).param("beats",encode(changedBeatIds)).param("mapping",encode(mappings)).param("analysis",analysisId).param("comparison",comparisonId).param("ruleset",String.valueOf(canonical.get("rulesetVersion"))).param("rubric",RUBRIC).param("settings",hash(encode(reviewSettings))).param("reviewer",reviewer).param("method",method).param("citations",encode(citations)).param("rationale",rationale.trim()).param("decision",decision).param("expiry",java.sql.Timestamp.from(expiry)).update();
    return Map.of("evidenceId",evidenceId.toString(),"decision",decision,"reviewerPrincipal",reviewer,"reviewerAuthority","EVIDENCE_REVIEWER","candidateFingerprint",candidateHash,"validUntil",expiry.toString(),"immutable",true,"renderAuthorized",false);
  }

  private static String text(Object value) { return value == null ? "" : String.valueOf(value); }
  private static UUID uuid(Object value, String reason) {
    try { return UUID.fromString(text(value)); }
    catch (Exception error) { throw new ResponseStatusException(CONFLICT, reason); }
  }
  private String repositoryText(String relative, String expectedHash) {
    try {
      Path root = Path.of(libraryRoot).toRealPath();
      if (relative.isBlank() || Path.of(relative).isAbsolute()) throw new IllegalArgumentException();
      Path file = root.resolve(relative).normalize().toRealPath();
      if (!file.startsWith(root) || !Files.isRegularFile(file) || Files.size(file) > 500_000) throw new IllegalArgumentException();
      String value = Files.readString(file, StandardCharsets.UTF_8);
      if (expectedHash == null || !hash(value).equals(expectedHash))
        throw new ResponseStatusException(CONFLICT, "SOURCE_PROMPT_FINGERPRINT_MISMATCH");
      return value;
    } catch (ResponseStatusException error) { throw error; }
    catch (Exception error) { throw new ResponseStatusException(CONFLICT, "SOURCE_PROVENANCE_REQUIRED: inaccessible or unsafe repository path"); }
  }
  private Map<String,Object> normalizedSettings(Map<String,Object> source) {
    String profile = text(source.get("contentProfile")), generator = text(source.get("generator"));
    var config = map(source.get("settings")); String aspect = text(config.get("aspectRatio"));
    var executionKeys=Set.of("mode","resolution","aspectRatio","fps","frameRate","seed","quality","motionStrength","cameraMotion","guidanceScale","negativePrompt","continuationMode","duration","referenceStrength","styleStrength","numFrames","steps","format");
    if (!executionKeys.containsAll(config.keySet()) || config.values().stream().anyMatch(v->v instanceof Map<?,?> || v instanceof List<?>))
      throw new ResponseStatusException(CONFLICT,"PRODUCTION_SETTINGS_BINDING_REQUIRED: non-execution metadata is forbidden in reviewer settings");
    Object duration = source.getOrDefault("desiredDuration", source.get("durationSeconds"));
    if (profile.isBlank() || generator.isBlank() || Set.of("UNKNOWN", "AUTO").contains(profile)
        || Set.of("UNKNOWN", "AUTO").contains(generator) || !(duration instanceof Number n)
        || !Double.isFinite(n.doubleValue()) || n.doubleValue() <= 0 || !aspect.matches("[1-9][0-9]*:[1-9][0-9]*"))
      throw new ResponseStatusException(CONFLICT, "PRODUCTION_SETTINGS_BINDING_REQUIRED");
    if (source.get("desiredDuration") instanceof Number a && source.get("durationSeconds") instanceof Number b && Double.compare(a.doubleValue(),b.doubleValue())!=0)
      throw new ResponseStatusException(CONFLICT,"PRODUCTION_SETTINGS_BINDING_REQUIRED: conflicting duration fields");
    var out = new LinkedHashMap<String,Object>(); out.put("contentProfile", profile); out.put("generator", generator);
    out.put("desiredDuration", ((Number)duration).doubleValue()); out.put("settings", config);
    if (source.get("openingStrategy") != null) out.put("openingStrategy", source.get("openingStrategy"));
    return out;
  }
  private Map<String,Object> originalContext(Map<String,Object> request) {
    var source = new LinkedHashMap<String,Object>();
    for (String key : List.of("contentId", "promptVersionId", "repositoryRelativePath", "expectedPromptSha256", "storyId",
        "approvalRecordId", "productionSettingsRecordId", "productionSettingsSourcePath", "expectedSettingsSha256"))
      if (request.get(key) != null) source.put(key, request.get(key));
    var out = new LinkedHashMap<String,Object>(); var blockers = new ArrayList<String>();
    String prompt; String identity; Long content = null, promptId = null;
    if (source.get("promptVersionId") != null) {
      try { content = Long.valueOf(text(source.get("contentId"))); promptId = Long.valueOf(text(source.get("promptVersionId"))); }
      catch (Exception error) { throw new ResponseStatusException(BAD_REQUEST, "Exact contentId and promptVersionId are required"); }
      prompt = savedPrompt(content, promptId); identity = "saved-prompt:" + content + ":" + promptId;
      if (!hash(prompt).equals(source.get("expectedPromptSha256"))) throw new ResponseStatusException(CONFLICT, "SOURCE_PROMPT_FINGERPRINT_MISMATCH");
      Long current = jdbc.sql("SELECT max(id) FROM prompt_versions WHERE content_id=:content").param("content", content).query(Long.class).single();
      if (!promptId.equals(current)) blockers.add("PROMPT_VERSION_IS_NOT_CURRENT");
      var session = jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1")
          .param("content", content.toString()).param("prompt", promptId.toString()).query(String.class).optional().map(this::read).orElse(Map.of());
      for (var pair : Map.of("approvalRecordId", "approvalRecordId", "storyId", "sourceStoryRecordId").entrySet()) {
        Object authoritative = session.get(pair.getValue());
        if (authoritative==null && "storyId".equals(pair.getKey())) authoritative=session.get("storyRecordId");
        if (authoritative == null || source.get(pair.getKey()) != null && !text(source.get(pair.getKey())).equals(text(authoritative)))
          blockers.add("SOURCE_APPROVAL_REQUIRED");
        else source.put(pair.getKey(), authoritative);
      }
      try { verifiedStory(session,Map.of()); } catch(RuntimeException bad) { blockers.add("SOURCE_APPROVAL_REQUIRED"); }
      if (source.get("repositoryRelativePath") != null && !prompt.equals(repositoryText(text(source.get("repositoryRelativePath")), hash(prompt))))
        throw new ResponseStatusException(CONFLICT, "SOURCE_PROMPT_FINGERPRINT_MISMATCH");
    } else {
      String relative = text(source.get("repositoryRelativePath"));
      prompt = repositoryText(relative, text(source.get("expectedPromptSha256")));
      identity = "repository:" + Path.of(relative).normalize().toString();
    }
    if (prompt.isBlank() || prompt.length() > 50_000) throw new ResponseStatusException(BAD_REQUEST, "Complete bounded production prompt required");
    Map<String,Object> story = Map.of();
    try {
      story = workflow.approvedStoryForCpq(uuid(source.get("storyId"), "SOURCE_APPROVAL_REQUIRED"), uuid(source.get("approvalRecordId"), "SOURCE_APPROVAL_REQUIRED"));
      if (prompt.trim().equals(text(story.get("text")).trim())) blockers.add("INDEPENDENT_SOURCE_REQUIRED");
    } catch (RuntimeException error) { blockers.add("SOURCE_APPROVAL_REQUIRED"); }
    Map<String,Object> settings = Map.of(); var settingsAuthority = new LinkedHashMap<String,Object>();
    try {
      if (promptId != null) {
        var row = jdbc.sql("SELECT id::text,payload::text FROM post_family_workflow_events WHERE kind='PRODUCTION_SETTINGS' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1")
            .param("content", content.toString()).param("prompt", promptId.toString())
            .query((rs,n)->Map.entry(rs.getString(1), read(rs.getString(2)))).optional().orElseThrow();
        if (source.get("productionSettingsRecordId") != null && !row.getKey().equals(text(source.get("productionSettingsRecordId")))) throw new IllegalArgumentException();
        if (row.getValue().get("promptHash")!=null && !hash(prompt).equals(row.getValue().get("promptHash"))) throw new IllegalArgumentException();
        source.put("productionSettingsRecordId", row.getKey()); settings = savedProduction(content,promptId,prompt,row.getValue(),settingsAuthority);
        settingsAuthority.put("recordId", row.getKey());
      } else if (source.get("productionSettingsRecordId") != null) {
        var row = event(uuid(source.get("productionSettingsRecordId"), "PRODUCTION_SETTINGS_BINDING_REQUIRED"), "PRODUCTION_SETTINGS");
        if (!hash(prompt).equals(row.get("sourcePromptSha256")) || !identity.equals(row.get("sourceIdentity"))) throw new IllegalArgumentException();
        settings = normalizedSettings(row); settingsAuthority.put("recordId", source.get("productionSettingsRecordId"));
      } else {
        String relative = text(source.get("productionSettingsSourcePath"));
        var document = read(repositoryText(relative, text(source.get("expectedSettingsSha256"))));
        if (!hash(prompt).equals(document.get("sourcePromptSha256")) || !identity.equals(document.get("sourceIdentity"))) throw new IllegalArgumentException();
        settings = normalizedSettings(map(document.get("productionSettings")));
        settingsAuthority.put("repositoryRelativePath", relative); settingsAuthority.put("sha256", source.get("expectedSettingsSha256"));
      }
    } catch (RuntimeException error) { blockers.add("PRODUCTION_SETTINGS_BINDING_REQUIRED"); if(error.getMessage()!=null && error.getMessage().contains("PRODUCTION_SETTINGS_CONFLICT")) blockers.add(error.getMessage()); }
    out.put("subjectType", "ORIGINAL_PROMPT"); out.put("reviewContractVersion", ORIGINAL_CONTRACT);
    out.put("sourceIdentity", identity); out.put("sourceSelectors", source); out.put("promptText", prompt); out.put("promptSha256", hash(prompt));
    out.put("contentId", content); out.put("promptVersionId", promptId); out.put("approvedStory", story);
    out.put("productionSettings", settings); out.put("settingsAuthority", settingsAuthority);
    out.put("productionSettingsSha256", hash(encode(settings)));
    if (source.get("repositoryRelativePath") != null) out.put("repositoryProvenance", Map.of("repository", "pompom-production-library",
        "relativePath", source.get("repositoryRelativePath"), "sha256", hash(prompt), "identityOnlyNotStoryApproval", true));
    out.put("blockers", blockers.stream().distinct().toList());
    return out;
  }
  public Map<String,Object> pilotSubject(UUID analysis,UUID comparisonId,String candidateId) {
    var baseline=baseline(analysis); long content=((Number)baseline.get("contentId")).longValue(),promptId=((Number)baseline.get("promptVersionId")).longValue();
    String original=savedPrompt(content,promptId);
    var context=originalContext(Map.of("contentId",content,"promptVersionId",promptId,"expectedPromptSha256",hash(original)));
    if(!((List<?>)context.get("blockers")).isEmpty())throw new ResponseStatusException(CONFLICT,String.join(",",(List<String>)context.get("blockers")));
    var out=new LinkedHashMap<String,Object>(context);out.put("approvedStorySha256",hash(text(map(context.get("approvedStory")).get("text"))));out.put("analysisId",analysis.toString());out.put("canonical",baseline.get("canonicalRuleEvaluation"));out.put("originalPrompt",original);out.put("changedBeats",List.of());
    if(comparisonId!=null) {
      var comparison=comparison(analysis,comparisonId);var candidate=candidate(comparison,candidateId);
      if(!Boolean.TRUE.equals(candidateBinding(analysis,baseline,comparison,candidate).get("assessmentAllowed")))throw new ResponseStatusException(CONFLICT,"Candidate binding is not current");
      var story=sourceStory(baseline,candidate,comparison);
      if(!map(story.get("verified")).get("storyId").equals(map(context.get("approvedStory")).get("storyId")))throw new ResponseStatusException(CONFLICT,"Source story differs");
      var generatorRole=event(UUID.fromString(text(comparison.get("roleRecordId"))),"CREATIVE_ROLE");
      out.put("generationIdentity",Map.of("provider",text(generatorRole.get("provider")),"model",text(generatorRole.get("model"))));
      out.put("subjectType","OPTIMIZATION_CANDIDATE");out.put("comparisonId",comparisonId.toString());out.put("candidateId",candidateId);out.put("promptText",candidate.get("prompt"));out.put("promptSha256",hash(text(candidate.get("prompt"))));
      var creative=map(map(candidate.get("currentAssessment")).get("creativeAssessment"));if(creative.isEmpty())creative=map(candidate.get("creativeAssessment"));var changes=new ArrayList<Map<String,Object>>(maps(creative.get("changeContract")));
      if(changes.isEmpty()) {
        var originals=original.lines().filter(line->line.matches("^\\d+(?:\\.\\d+)?-\\d+(?:\\.\\d+)?s:.*")).toList();
        var revised=text(candidate.get("prompt")).lines().filter(line->line.matches("^\\d+(?:\\.\\d+)?-\\d+(?:\\.\\d+)?s:.*")).toList();
        if(originals.size()==revised.size())for(int i=0;i<originals.size();i++)if(!originals.get(i).equals(revised.get(i)))changes.add(Map.of("beatId",String.format("beat_%02d",i+1),"originalInstruction",originals.get(i),"revisedInstruction",revised.get(i),"evidence","EXACT_TEXT_DIFF_NOT_SEMANTIC_VERIFICATION"));
      }
      out.put("changedBeats",changes);
    }
    return out;
  }
  public Map<String,Object> originalPreflight(Map<String,Object> request, HttpServletRequest principal) {
    if (principal.isUserInRole("CREATIVE_QUALITY_ARCHITECTURE_APPROVER")) principal(principal, "CREATIVE_QUALITY_ARCHITECTURE_APPROVER");
    else principal(principal, "EVIDENCE_REVIEWER");
    var context = originalContext(request); var result = new LinkedHashMap<>(context);
    result.put("status", ((List<?>)context.get("blockers")).isEmpty() ? "READY_FOR_SOURCE_BINDING" : "BLOCKED");
    result.put("persisted", false); result.put("fidelityDecision", "UNKNOWN"); return result;
  }
  @Transactional
  public Map<String,Object> bindOriginal(Map<String,Object> request, HttpServletRequest principal) {
    String actor = principal(principal, "CREATIVE_QUALITY_ARCHITECTURE_APPROVER"); var context = originalContext(request);
    if (!((List<?>)context.get("blockers")).isEmpty()) throw new ResponseStatusException(CONFLICT, String.join(",", (List<String>)context.get("blockers")));
    String rationale = text(request.get("rationale")).trim();
    if (rationale.length() < 20) throw new ResponseStatusException(BAD_REQUEST, "Concrete source-binding rationale required");
    String scope = hash(encode(context)); UUID id = UUID.randomUUID(); var story = map(context.get("approvedStory"));
    var payload = new LinkedHashMap<>(context); payload.put("boundBy", actor); payload.put("bindingRationale", rationale); payload.put("bindingSha256", scope);
    jdbc.sql("INSERT INTO cpq_original_subjects(subject_id,binding_sha256,prompt_fingerprint,approved_story_fingerprint,approval_record_id,payload,bound_by) VALUES(:id,:scope,:prompt,:story,:approval,CAST(:payload AS jsonb),:actor)")
        .param("id",id).param("scope",scope).param("prompt",context.get("promptSha256")).param("story",hash(text(story.get("text"))))
        .param("approval",uuid(story.get("approvalRecordId"),"SOURCE_APPROVAL_REQUIRED")).param("payload",encode(payload)).param("actor",actor).update();
    return Map.of("subjectId",id.toString(),"subjectType","ORIGINAL_PROMPT","bindingSha256",scope,"status","READY_FOR_FIDELITY_REVIEW","fidelityDecision","UNKNOWN","renderAuthorized",false);
  }
  private Map<String,Object> originalSubject(UUID id) {
    var saved = jdbc.sql("SELECT payload::text FROM cpq_original_subjects WHERE subject_id=:id").param("id",id).query(String.class).optional().map(this::read)
        .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Original fidelity subject not found"));
    var current = originalContext(map(saved.get("sourceSelectors")));
    if (!((List<?>)current.get("blockers")).isEmpty() || !hash(encode(current)).equals(saved.get("bindingSha256")))
      throw new ResponseStatusException(CONFLICT,"ORIGINAL_BINDING_STALE: rebind current source approval/settings");
    saved.put("subjectId",id.toString()); return saved;
  }
  public Map<String,Object> originalReviewPacket(UUID id, HttpServletRequest principal) {
    principal(principal,"EVIDENCE_REVIEWER"); var packet=originalSubject(id); packet.put("requiredStoryAnchors",STORY_ANCHORS); return packet;
  }
  private Instant reviewExpiry(Map<String,Object> request) {
    Instant expiry;
    try { expiry=Instant.parse(text(request.get("validUntil"))); }
    catch (Exception error) { throw new ResponseStatusException(BAD_REQUEST,"Explicit ISO-8601 review expiry required"); }
    if (!expiry.isAfter(Instant.now()) || expiry.isAfter(Instant.now().plusSeconds(180L*24*60*60)))
      throw new ResponseStatusException(BAD_REQUEST,"Review expiry must be within 180 days");
    return expiry;
  }
  @Transactional
  public Map<String,Object> reviewOriginal(UUID id, Map<String,Object> request, HttpServletRequest principal) {
    String reviewer = principal(principal,"EVIDENCE_REVIEWER"); var subject = originalSubject(id); var story = map(subject.get("approvedStory"));
    if (reviewer.equals(subject.get("boundBy")) || reviewer.equals(story.get("approvedBy")))
      throw new ResponseStatusException(FORBIDDEN,"Independent reviewer cannot certify their own source binding/approval");
    String decision=text(request.get("decision")), rationale=text(request.get("rationale")).trim();
    if (!Set.of("PASS","FAIL","UNKNOWN").contains(decision) || rationale.length()<20)
      throw new ResponseStatusException(BAD_REQUEST,"Decision and concrete independent rationale required");
    if (request.get("reviewMethodVersion") != null && !"human-original-fidelity-v2".equals(request.get("reviewMethodVersion")))
      throw new ResponseStatusException(BAD_REQUEST,"Unsupported independent original review method");
    String prompt=text(subject.get("promptText")), approved=text(story.get("text")); var citations=maps(request.get("citations"));
    if (citations.isEmpty()) throw new ResponseStatusException(BAD_REQUEST,"Exact source/prompt citations required");
    for (var citation:citations) {
      String quote=text(citation.get("quote")), side=text(citation.get("side"));
      if (quote.isBlank() || !("APPROVED_STORY".equals(side) ? approved.contains(quote) : "ORIGINAL_PROMPT".equals(side) && prompt.contains(quote)))
        throw new ResponseStatusException(BAD_REQUEST,"Citation does not match bound original/story bytes");
    }
    var mappings=maps(request.get("sourceEventMapping")); var anchors=new HashSet<String>();
    for (var mapping:mappings) {
      String from=text(mapping.get("sourceQuote")), to=text(mapping.get("promptQuote")), anchor=text(mapping.get("anchor"));
      if (from.isBlank() || to.isBlank() || !approved.contains(from) || !prompt.contains(to) || !STORY_ANCHORS.contains(anchor))
        throw new ResponseStatusException(BAD_REQUEST,"Source mapping must cite bound text and a protected story anchor");
      anchors.add(anchor);
    }
    if ("PASS".equals(decision) && !anchors.containsAll(STORY_ANCHORS))
      throw new ResponseStatusException(BAD_REQUEST,"Fidelity PASS requires every protected story anchor mapping");
    Instant expiry=reviewExpiry(request); UUID evidenceId=UUID.randomUUID(); UUID supersedes=null;
    if (request.get("supersedesEvidenceId") != null) {
      supersedes=uuid(request.get("supersedesEvidenceId"),"Invalid supersession");
      Boolean same=jdbc.sql("SELECT EXISTS(SELECT 1 FROM cpq_fidelity_reviews WHERE evidence_id=:e AND subject_type='ORIGINAL_PROMPT' AND original_subject_id=:subject)")
          .param("e",supersedes).param("subject",id).query(Boolean.class).single();
      if (!same) throw new ResponseStatusException(CONFLICT,"Supersession must target the same immutable original subject");
    }
    jdbc.sql("INSERT INTO cpq_fidelity_reviews(evidence_id,subject_type,original_subject_id,review_contract_version,supersedes_evidence_id,content_id,prompt_version_id,approved_story_id,approved_revision,approved_story_fingerprint,original_prompt_fingerprint,candidate_prompt_fingerprint,intervention_fingerprint,changed_beat_ids,source_event_mapping,analysis_id,comparison_id,ruleset_version,cpq_rubric_version,production_settings_fingerprint,reviewer_principal,reviewer_authority,review_method_version,citations,rationale,decision,valid_until) VALUES(:id,'ORIGINAL_PROMPT',:subject,:contract,:supersedes,:content,:promptId,:storyId,:revision,:story,:prompt,:prompt,:intervention,'[]',CAST(:mapping AS jsonb),NULL,NULL,'NOT_APPLICABLE',:rubric,:settings,:reviewer,'EVIDENCE_REVIEWER','human-original-fidelity-v2',CAST(:citations AS jsonb),:rationale,:decision,:expiry)")
        .param("id",evidenceId).param("subject",id).param("contract",ORIGINAL_CONTRACT).param("supersedes",supersedes,java.sql.Types.OTHER)
        .param("content",subject.get("contentId"),java.sql.Types.BIGINT).param("promptId",subject.get("promptVersionId"),java.sql.Types.BIGINT)
        .param("storyId",story.get("storyId")).param("revision",story.get("revision")).param("story",hash(approved)).param("prompt",subject.get("promptSha256"))
        .param("intervention",hash("[]")).param("mapping",encode(mappings)).param("rubric",RUBRIC).param("settings",subject.get("productionSettingsSha256"))
        .param("reviewer",reviewer).param("citations",encode(citations)).param("rationale",rationale).param("decision",decision).param("expiry",java.sql.Timestamp.from(expiry)).update();
    return Map.of("evidenceId",evidenceId.toString(),"subjectId",id.toString(),"subjectType","ORIGINAL_PROMPT","decision",decision,
        "reviewerPrincipal",reviewer,"reviewContractVersion",ORIGINAL_CONTRACT,"validUntil",expiry.toString(),"renderAuthorized",false);
  }

  public Map<String,Object> calibrationState() {
    var counts=jdbc.sql("SELECT (SELECT count(*) FROM cpq_calibration_examples) examples,(SELECT count(*) FROM cpq_calibration_judgments) judgments,(SELECT count(*) FROM cpq_fidelity_reviews WHERE decision='PASS' AND valid_until>now()) fidelityPasses,(SELECT activated FROM cpq_policy_state WHERE singleton=TRUE) activated")
      .query((rs,n)->Map.<String,Object>of("examples",rs.getInt("examples"),"judgments",rs.getInt("judgments"),"currentFidelityPasses",rs.getInt("fidelityPasses"),"activated",rs.getBoolean("activated"))).single();
    var verifiedCounts=new LinkedHashMap<>(counts); int qualifiedPasses=0;
    var passIds=jdbc.sql("SELECT evidence_id FROM cpq_fidelity_reviews f WHERE decision='PASS' AND valid_until>now() AND NOT EXISTS(SELECT 1 FROM cpq_fidelity_reviews s WHERE s.supersedes_evidence_id=f.evidence_id)").query(UUID.class).list();
    for(UUID id:passIds) try { qualifiedImportEvidence(id); qualifiedPasses++; } catch(RuntimeException unqualified) { /* Explicitly not current qualified evidence. */ }
    verifiedCounts.put("currentFidelityPasses",qualifiedPasses);
    verifiedCounts.put("originalSubjects",jdbc.sql("SELECT count(*) FROM cpq_original_subjects").query(Long.class).single());
    verifiedCounts.put("fidelityReviews",jdbc.sql("SELECT count(*) FROM cpq_fidelity_reviews").query(Long.class).single());
    var corpora=jdbc.sql("SELECT corpus_version,state,corpus_sha256,created_by,created_at,approved_by FROM cpq_calibration_corpora ORDER BY created_at DESC")
      .query((rs,n)->Map.<String,Object>of("version",rs.getString("corpus_version"),"state",rs.getString("state"),"sha256",Objects.toString(rs.getString("corpus_sha256"),""),"createdBy",rs.getString("created_by"),"createdAt",rs.getTimestamp("created_at").toInstant().toString(),"approvedBy",Objects.toString(rs.getString("approved_by"),""))).list();
    return Map.of("rubricVersion",RUBRIC,"gradingStatus","CALIBRATION_INCOMPLETE","activated",counts.get("activated"),"counts",verifiedCounts,"corpora",corpora,"missingRequirements",List.of("Independent reviewed calibration examples","Held-out validation and false-positive/false-negative analysis","Reviewer agreement validation","Full-pipeline B-to-A golden acceptance","Authorized activation record"));
  }

  public Map<String,Object> reviewerCapabilities(HttpServletRequest request) {
    return Map.of("authenticated",request.getUserPrincipal()!=null,
      "principal",request.getUserPrincipal()==null?"":request.getUserPrincipal().getName(),
      "canAssessTextQuality",request.isUserInRole("PRODUCTION_OPERATOR"),
      "canReviewSourceFidelity",request.isUserInRole("EVIDENCE_REVIEWER"),
      "canReviewCalibration",request.isUserInRole("CREATIVE_QUALITY_REVIEWER"),
      "canManageCalibration",request.isUserInRole("CREATIVE_QUALITY_ARCHITECTURE_APPROVER"));
  }

  public Map<String,Object> createCorpus(String version,Map<String,Object> body,HttpServletRequest servlet) {
    String actor=principal(servlet,"CREATIVE_QUALITY_ARCHITECTURE_APPROVER");if(version==null||!version.matches("[a-z0-9][a-z0-9._-]{2,79}"))throw new ResponseStatusException(BAD_REQUEST,"Invalid immutable corpus version");
    jdbc.sql("INSERT INTO cpq_calibration_corpora(corpus_version,rubric_version,state,created_by,calibration_policy) VALUES(:version,:rubric,'DRAFT',:actor,CAST(:policy AS jsonb))")
      .param("version",version).param("rubric",RUBRIC).param("actor",actor).param("policy",encode(body.getOrDefault("policy",Map.of()))).update();
    return Map.of("corpusVersion",version,"state","DRAFT","createdBy",actor,"gradingActivated",false);
  }

  private Map<String,Object> qualifiedImportEvidence(UUID evidenceId) {
    var evidence = jdbc.sql("SELECT row_to_json(f)::text FROM cpq_fidelity_reviews f WHERE evidence_id=:id AND valid_until>now() AND NOT EXISTS(SELECT 1 FROM cpq_fidelity_reviews s WHERE s.supersedes_evidence_id=f.evidence_id)")
        .param("id",evidenceId).query(String.class).optional().map(this::read)
        .orElseThrow(()->new ResponseStatusException(CONFLICT,"Current unexpired independent fidelity evidence required"));
    if (!"PASS".equals(evidence.get("decision")) || !RUBRIC.equals(evidence.get("cpq_rubric_version")) || !"EVIDENCE_REVIEWER".equals(evidence.get("reviewer_authority")))
      throw new ResponseStatusException(CONFLICT,"Calibration import requires a qualified independent fidelity PASS; FAIL/UNKNOWN remain unqualified");
    var qualified = new LinkedHashMap<String,Object>(); qualified.put("evidence",evidence);
    if ("ORIGINAL_PROMPT".equals(evidence.get("subject_type"))) {
      if (!ORIGINAL_CONTRACT.equals(evidence.get("review_contract_version"))) throw new ResponseStatusException(CONFLICT,"Original fidelity contract mismatch");
      UUID subjectId=uuid(evidence.get("original_subject_id"),"Original subject binding missing"); var subject=originalSubject(subjectId);
      var decisions=jdbc.sql("SELECT DISTINCT decision FROM cpq_fidelity_reviews f WHERE original_subject_id=:subject AND subject_type='ORIGINAL_PROMPT' AND valid_until>now() AND NOT EXISTS(SELECT 1 FROM cpq_fidelity_reviews s WHERE s.supersedes_evidence_id=f.evidence_id)")
          .param("subject",subjectId).query(String.class).list();
      if (!decisions.equals(List.of("PASS"))) throw new ResponseStatusException(CONFLICT,"Conflicting original fidelity reviews require independent adjudication");
      var story=map(subject.get("approvedStory"));
      if (!subject.get("promptSha256").equals(evidence.get("original_prompt_fingerprint"))
          || !subject.get("promptSha256").equals(evidence.get("candidate_prompt_fingerprint"))
          || !hash(text(story.get("text"))).equals(evidence.get("approved_story_fingerprint"))
          || !story.get("storyId").equals(evidence.get("approved_story_id")) || !story.get("revision").equals(evidence.get("approved_revision"))
          || !subject.get("productionSettingsSha256").equals(evidence.get("production_settings_fingerprint")))
        throw new ResponseStatusException(CONFLICT,"Original fidelity scope mismatch");
      qualified.put("promptText",subject.get("promptText")); qualified.put("storyText",story.get("text"));
      qualified.put("productionSettings",subject.get("productionSettings")); qualified.put("promptVersionId",subject.get("promptVersionId"));
      qualified.put("provenance",Map.of("originalSubjectId",subjectId.toString(),"sourceIdentity",subject.get("sourceIdentity"),"bindingSha256",subject.get("bindingSha256")));
    } else {
      UUID analysis=uuid(evidence.get("analysis_id"),"Candidate analysis binding required"), comparisonId=uuid(evidence.get("comparison_id"),"Candidate comparison binding required");
      var baseline=baseline(analysis); var comparison=comparison(analysis,comparisonId);
      var matches=maps(comparison.get("candidates")).stream().filter(c->hash(text(c.get("prompt"))).equals(evidence.get("candidate_prompt_fingerprint"))).toList();
      if (matches.size()!=1) throw new ResponseStatusException(CONFLICT,"Exact candidate scope required");
      var candidate=matches.getFirst();
      if (!Boolean.TRUE.equals(candidateBinding(analysis,baseline,comparison,candidate).get("assessmentAllowed"))) throw new ResponseStatusException(CONFLICT,"Candidate source binding is stale");
      var story=sourceStory(baseline,candidate,comparison); String storyText=text(story.get("text"));
      var context=map(story.get("roleContext")); var session=map(story.get("session"));
      String storyId=text(map(story.get("verified")).get("storyId"));
      String revision=text(map(story.get("verified")).get("revision"));
      var bound=map(baseline.get("boundRequest")); var production=new LinkedHashMap<String,Object>();
      for (String key:List.of("contentProfile","generator","desiredDuration","settings","openingStrategy")) production.put(key,bound.get(key));
      var creative=map(map(candidate.get("currentAssessment")).get("creativeAssessment")); if(creative.isEmpty()) creative=map(candidate.get("creativeAssessment"));
      var current=currentFidelity(analysis,comparisonId,text(candidate.get("candidateId")),hash(storyText),hash(savedPrompt(((Number)baseline.get("contentId")).longValue(),((Number)baseline.get("promptVersionId")).longValue())),text(evidence.get("candidate_prompt_fingerprint")),hash(encode(creative.getOrDefault("changeContract",List.of()))),hash(encode(production)),text(map(baseline.get("canonicalRuleEvaluation")).get("rulesetVersion")));
      if (!"PASS".equals(current.get("decision")) || !storyId.equals(evidence.get("approved_story_id")) || !revision.equals(evidence.get("approved_revision")))
        throw new ResponseStatusException(CONFLICT,"Candidate fidelity is stale or conflicting");
      qualified.put("promptText",candidate.get("prompt")); qualified.put("storyText",storyText); qualified.put("productionSettings",normalizedSettings(bound));
      qualified.put("promptVersionId",evidence.get("prompt_version_id"));
      qualified.put("provenance",Map.of("analysisId",analysis.toString(),"comparisonId",comparisonId.toString(),"candidateId",candidate.get("candidateId")));
    }
    return qualified;
  }

  @Transactional
  public Map<String,Object> addCalibrationExample(String version,Map<String,Object> body,HttpServletRequest servlet) {
    String actor=principal(servlet,"CREATIVE_QUALITY_ARCHITECTURE_APPROVER");
    String state=jdbc.sql("SELECT state FROM cpq_calibration_corpora WHERE corpus_version=:version FOR UPDATE").param("version",version).query(String.class).optional()
        .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Calibration corpus not found"));
    if (!Set.of("DRAFT","REVIEWING").contains(state)) throw new ResponseStatusException(CONFLICT,"Corpus is not open for imports");
    UUID fidelityId=uuid(body.get("sourceFidelityEvidenceId"),"Existing independent source-fidelity evidence ID is required");
    if (body.get("subjectType")!=null) {
      String type=jdbc.sql("SELECT subject_type FROM cpq_fidelity_reviews WHERE evidence_id=:id").param("id",fidelityId).query(String.class).optional().orElse("");
      if (!type.isBlank() && !type.equals(body.get("subjectType"))) throw new ResponseStatusException(CONFLICT,"Fidelity subject type cannot be reused across original/candidate scopes");
    }
    var qualified=qualifiedImportEvidence(fidelityId); var evidence=map(qualified.get("evidence"));
    String prompt=text(body.get("promptText")), storyText=text(body.get("approvedStoryText"));
    if (prompt.isBlank() || !prompt.equals(qualified.get("promptText"))) throw new ResponseStatusException(CONFLICT,"Calibration prompt must match its independently reviewed candidate fingerprint or original bytes");
    if (storyText.isBlank() || !storyText.equals(qualified.get("storyText"))) throw new ResponseStatusException(CONFLICT,"Calibration approved story text must match its independent fidelity record");
    if (!text(body.get("sourceStoryId")).equals(evidence.get("approved_story_id")) || !text(body.get("sourceRevision")).equals(evidence.get("approved_revision")))
      throw new ResponseStatusException(CONFLICT,"Calibration source identity/revision must match independent fidelity evidence");
    if (body.get("subjectType")!=null && !body.get("subjectType").equals(evidence.get("subject_type"))) throw new ResponseStatusException(CONFLICT,"Fidelity subject type cannot be reused across original/candidate scopes");
    if (body.get("originalSubjectId")!=null && !text(body.get("originalSubjectId")).equals(text(evidence.get("original_subject_id")))) throw new ResponseStatusException(CONFLICT,"Original subject identity mismatch");
    if (body.get("promptVersionId")!=null && !text(body.get("promptVersionId")).equals(text(qualified.get("promptVersionId")))) throw new ResponseStatusException(CONFLICT,"Prompt version binding mismatch");
    var settings=normalizedSettings(body);
    if (!encode(settings).equals(encode(qualified.get("productionSettings")))) throw new ResponseStatusException(CONFLICT,"Production settings do not match independently bound evidence");
    String split=text(body.get("split")); if(!Set.of("CALIBRATION","HELD_OUT").contains(split)) throw new ResponseStatusException(BAD_REQUEST,"Split must be CALIBRATION or HELD_OUT");
    String label=text(body.get("promptVersionLabel")); if(label.isBlank()) throw new ResponseStatusException(BAD_REQUEST,"Prompt version label is required");
    String caseType=text(body.getOrDefault("caseType","GENERAL_PROMPT"));
    if (!Set.of("EXCELLENT_EXECUTION","STRONG_EXECUTION","ADEQUATE_IMPROVABLE","WEAK_EXECUTION","SOURCE_FAITHFUL_IMPROVEMENT","COSMETIC_REWRITE","PRODUCTION_REGRESSION","CONSTRAINED_UNIMPROVABLE","GENERAL_PROMPT").contains(caseType)) throw new ResponseStatusException(BAD_REQUEST,"Unsupported calibration case type");
    String mechanic=text(body.get("leakageGroup")).trim();
    if (mechanic.isBlank()) throw new ResponseStatusException(BAD_REQUEST,"Explicit related-story/central-mechanic leakageGroup required");
    String sourceGroup=hash(text(evidence.get("approved_story_id"))), promptHash=hash(prompt), settingsHash=hash(encode(settings));
    var existing=jdbc.sql("SELECT prompt_fingerprint,source_story_id,split,mechanic_group FROM cpq_calibration_examples WHERE corpus_version=:version")
        .param("version",version).query((rs,n)->{var x=new LinkedHashMap<String,Object>();x.put("prompt",rs.getString(1));x.put("story",rs.getString(2));x.put("split",rs.getString(3));x.put("mechanic",rs.getString(4));return x;}).list();
    for(var old:existing) {
      if(promptHash.equals(old.get("prompt"))) throw new ResponseStatusException(CONFLICT,"Duplicate prompt import in this corpus");
      if ((evidence.get("approved_story_id").equals(old.get("story")) || mechanic.equals(old.get("mechanic"))) && !split.equals(old.get("split")))
        throw new ResponseStatusException(CONFLICT,"Related story/variant/central-mechanic leakage across splits");
    }
    var provenance=new LinkedHashMap<>(map(body.get("provenance"))); provenance.put("verifiedBinding",qualified.get("provenance")); provenance.put("importedBy",actor);
    UUID id=UUID.randomUUID();
    jdbc.sql("INSERT INTO cpq_calibration_examples(example_id,corpus_version,source_story_id,source_revision,source_fingerprint,prompt_version_id,prompt_version_label,prompt_fingerprint,prompt_text,source_story_text,content_profile,generator,target_duration_seconds,source_fidelity_evidence_id,observed_render_evidence,audience_evidence,case_type,split,provenance,created_by,fidelity_subject_type,source_group,mechanic_group,production_settings_fingerprint,production_settings,import_contract_version) VALUES(:id,:corpus,:story,:revision,:sourceHash,:promptId,:label,:promptHash,:prompt,:storyText,:profile,:generator,:duration,:fidelity,CAST(:render AS jsonb),CAST(:audience AS jsonb),:caseType,:split,CAST(:provenance AS jsonb),:actor,:type,:sourceGroup,:mechanic,:settingsHash,CAST(:settings AS jsonb),'original-fidelity-v2')")
      .param("id",id).param("corpus",version).param("story",evidence.get("approved_story_id")).param("revision",evidence.get("approved_revision")).param("sourceHash",hash(storyText))
      .param("promptId",qualified.get("promptVersionId"),java.sql.Types.BIGINT).param("label",label).param("promptHash",promptHash).param("prompt",prompt).param("storyText",storyText)
      .param("profile",settings.get("contentProfile")).param("generator",settings.get("generator")).param("duration",settings.get("desiredDuration"))
      .param("fidelity",fidelityId).param("render",encode(body.getOrDefault("renderEvidence",Map.of()))).param("audience",encode(body.getOrDefault("audienceEvidence",Map.of())))
      .param("caseType",caseType).param("split",split).param("provenance",encode(provenance)).param("actor",actor).param("type",evidence.get("subject_type"))
      .param("sourceGroup",sourceGroup).param("mechanic",mechanic).param("settingsHash",settingsHash).param("settings",encode(settings)).update();
    return Map.of("exampleId",id.toString(),"corpusVersion",version,"promptSha256",promptHash,"split",split,"independentFidelityEvidenceId",fidelityId.toString(),"humanQualityGrade","NOT_YET_REVIEWED","activated",false);
  }

  public Map<String,Object> calibrationReviewPacket(UUID exampleId,HttpServletRequest servlet) {
    principal(servlet,"CREATIVE_QUALITY_REVIEWER");
    var row=jdbc.sql("SELECT prompt_text,content_profile,generator,target_duration_seconds,source_fidelity_evidence_id,production_settings::text FROM cpq_calibration_examples WHERE example_id=:id")
        .param("id",exampleId).query((rs,n)->{
          var x=new LinkedHashMap<String,Object>(); x.put("promptText",rs.getString(1)); x.put("contentProfile",rs.getString(2));
          x.put("generator",rs.getString(3)); x.put("durationSeconds",rs.getBigDecimal(4)); x.put("evidenceId",rs.getObject(5,UUID.class));
          x.put("productionSettings",rs.getString(6)==null?Map.of():read(rs.getString(6))); return x;
        }).optional().orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Calibration example not found"));
    UUID evidence=(UUID)row.remove("evidenceId");
    if(evidence==null) throw new ResponseStatusException(CONFLICT,"Current independent fidelity evidence required");
    qualifiedImportEvidence(evidence);
    row.put("exampleId",exampleId.toString()); row.put("blind",true); row.put("existingJudgmentsVisible",false);
    row.put("rubricVersion",RUBRIC); row.put("reviewMethodVersion","cpq-human-blind-review-v2");
    return row;
  }

  @Transactional
  public Map<String,Object> submitCalibrationJudgment(UUID exampleId,Map<String,Object> body,HttpServletRequest servlet) {
    String reviewer=principal(servlet,"CREATIVE_QUALITY_REVIEWER");var packet=calibrationReviewPacket(exampleId,servlet);
    var dims=map(body.get("dimensions"));if(!dims.keySet().equals(new HashSet<>(DIMENSIONS)))throw new ResponseStatusException(BAD_REQUEST,"Judgment must include exactly all six CPQ dimensions");
    String reviewedPrompt=String.valueOf(packet.get("promptText"));
    Set<String> levels=Set.of("EXCELLENT","STRONG","ADEQUATE","WEAK","UNKNOWN");
    for(String dim:DIMENSIONS){var item=map(dims.get(dim));var citations=maps(item.get("evidenceCitations"));if(!levels.contains(String.valueOf(item.get("level")))||String.valueOf(item.getOrDefault("rationale","")).trim().length()<20||citations.isEmpty())throw new ResponseStatusException(BAD_REQUEST,"Each dimension needs an allowed judgment, evidence citation and concrete rationale");
      if(text(item.get("strengthOrWeakness")).trim().length()<20 || text(item.get("productionConstraint")).trim().length()<20
          || "UNKNOWN".equals(item.get("level")) && text(item.get("uncertainty")).trim().length()<20)
        throw new ResponseStatusException(BAD_REQUEST,"Each dimension requires a specific strength/weakness, production constraint, and uncertainty for UNKNOWN");
      for(var citation:citations){String quote=String.valueOf(citation.getOrDefault("quote",""));if(quote.isBlank()||!reviewedPrompt.contains(quote))throw new ResponseStatusException(BAD_REQUEST,"Every blinded-review citation must quote the exact reviewed prompt text");}}
    var submittedCitations=maps(body.get("evidenceCitations"));
    if(submittedCitations.isEmpty()) submittedCitations=dims.values().stream().flatMap(value->maps(map(value).get("evidenceCitations")).stream()).toList();
    for(var citation:submittedCitations) if(text(citation.get("quote")).isBlank() || !reviewedPrompt.contains(text(citation.get("quote"))))
      throw new ResponseStatusException(BAD_REQUEST,"Summary evidence citations must quote the exact blinded prompt");
    String fidelity=String.valueOf(body.get("sourceFidelityDecision"));if(!Set.of("PASS","FAIL","UNKNOWN").contains(fidelity))throw new ResponseStatusException(BAD_REQUEST,"Invalid source-fidelity judgment");
    var evidence=jdbc.sql("SELECT source_fidelity_evidence_id FROM cpq_calibration_examples WHERE example_id=:id").param("id",exampleId).query(UUID.class).single();
    String existingReviewer=jdbc.sql("SELECT reviewer_principal FROM cpq_fidelity_reviews WHERE evidence_id=:id").param("id",evidence).query(String.class).single();
    if(reviewer.equals(existingReviewer))throw new ResponseStatusException(FORBIDDEN,"A fidelity evidence producer cannot be the sole independent calibration reviewer");
    if (jdbc.sql("SELECT EXISTS(SELECT 1 FROM cpq_calibration_judgments WHERE example_id=:id AND reviewer_principal=:reviewer AND rubric_version=:rubric)").param("id",exampleId).param("reviewer",reviewer).param("rubric",RUBRIC).query(Boolean.class).single())
      throw new ResponseStatusException(CONFLICT,"Reviewer already submitted an immutable judgment for this example");
    String method=String.valueOf(body.getOrDefault("reviewMethodVersion","cpq-human-blind-review-v2"));
    if(!"cpq-human-blind-review-v2".equals(method)) throw new ResponseStatusException(BAD_REQUEST,"Unsupported independent human review method");
    String anchor=String.valueOf(body.getOrDefault("overallQualityAnchor","UNKNOWN"));if(!Set.of("A+","A","B","C","F","UNKNOWN").contains(anchor))throw new ResponseStatusException(BAD_REQUEST,"Invalid blinded reviewer quality anchor");
    UUID id=UUID.randomUUID();jdbc.sql("INSERT INTO cpq_calibration_judgments(judgment_id,example_id,reviewer_principal,reviewer_role,rubric_version,review_method_version,dimension_judgments,source_fidelity_decision,overall_quality_anchor,evidence_citations,confidence) VALUES(:id,:example,:reviewer,'CREATIVE_QUALITY_REVIEWER',:rubric,:method,CAST(:dimensions AS jsonb),:fidelity,:anchor,CAST(:citations AS jsonb),CAST(:confidence AS jsonb))")
      .param("id",id).param("example",exampleId).param("reviewer",reviewer).param("rubric",RUBRIC).param("method",method).param("dimensions",encode(dims)).param("fidelity",fidelity).param("anchor",anchor).param("citations",encode(submittedCitations)).param("confidence",encode(body.getOrDefault("confidence",Map.of()))).update();
    return Map.of("judgmentId",id.toString(),"exampleId",exampleId.toString(),"reviewerPrincipal",reviewer,"blindReview",true,"gradeActivated",false);
  }

  public Map<String,Object> calibrationReadiness(String version) {
    jdbc.sql("SELECT corpus_version FROM cpq_calibration_corpora WHERE corpus_version=:version").param("version",version).query(String.class).optional()
      .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Calibration corpus not found"));
    var examples=jdbc.sql("SELECT example_id,split,case_type FROM cpq_calibration_examples WHERE corpus_version=:version ORDER BY example_id").param("version",version)
      .query((rs,n)->Map.<String,Object>of("id",rs.getString(1),"split",rs.getString(2),"caseType",rs.getString(3))).list();
    var judgments=jdbc.sql("SELECT example_id,reviewer_principal,dimension_judgments::text,overall_quality_anchor,source_fidelity_decision FROM cpq_calibration_judgments j JOIN cpq_calibration_examples e USING(example_id) WHERE e.corpus_version=:version ORDER BY example_id,reviewer_principal")
      .param("version",version).query((rs,n)->Map.<String,Object>of("exampleId",rs.getString(1),"reviewer",rs.getString(2),"dimensions",read(rs.getString(3)),"anchor",rs.getString(4),"fidelity",rs.getString(5))).list();
    var byExample=new LinkedHashMap<String,List<Map<String,Object>>>();for(var j:judgments)byExample.computeIfAbsent(String.valueOf(j.get("exampleId")),k->new ArrayList<>()).add(j);
    int examplesWithTwoReviewers=0;var pairResults=new ArrayList<Map<String,Object>>();var allPairs=new ArrayList<Boolean>();
    for(var ex:examples){var reviews=byExample.getOrDefault(String.valueOf(ex.get("id")),List.of());if(reviews.stream().map(x->x.get("reviewer")).distinct().count()>=2){examplesWithTwoReviewers++;for(int i=0;i<reviews.size();i++)for(int j=i+1;j<reviews.size();j++){
      var a=map(reviews.get(i).get("dimensions"));var b=map(reviews.get(j).get("dimensions"));var agrees=new LinkedHashMap<String,Boolean>();for(String d:DIMENSIONS){String av=String.valueOf(map(a.get(d)).get("level")),bv=String.valueOf(map(b.get(d)).get("level"));boolean same=av.equals(bv);agrees.put(d,same);allPairs.add(same);}boolean anchor=Objects.equals(reviews.get(i).get("anchor"),reviews.get(j).get("anchor"));agrees.put("OVERALL_ANCHOR",anchor);pairResults.add(Map.of("exampleId",ex.get("id"),"reviewerCount",reviews.size(),"exactAgreement",agrees));}}}
    long heldOut=examples.stream().filter(e->"HELD_OUT".equals(e.get("split"))).count();long calibration=examples.stream().filter(e->"CALIBRATION".equals(e.get("split"))).count();
    var evidenceProblems = new ArrayList<Map<String,Object>>();
    var evidenceRows=jdbc.sql("SELECT example_id,source_fidelity_evidence_id FROM cpq_calibration_examples WHERE corpus_version=:version").param("version",version)
        .query((rs,n)->new AbstractMap.SimpleImmutableEntry<>(rs.getObject(1,UUID.class),rs.getObject(2,UUID.class))).list();
    for(var row:evidenceRows) try { qualifiedImportEvidence(row.getValue()); }
      catch(RuntimeException invalid) { evidenceProblems.add(Map.of("exampleId",row.getKey().toString(),"reason",invalid instanceof ResponseStatusException status ? text(status.getReason()) : "FIDELITY_EVIDENCE_UNAVAILABLE")); }
    String corpusHash=hash(encode(Map.of("examples",examples,"judgments",judgments)));
    var report=new LinkedHashMap<String,Object>();report.put("rubricVersion",RUBRIC);report.put("corpusVersion",version);report.put("corpusFingerprint",corpusHash);report.put("exampleCount",examples.size());report.put("calibrationCount",calibration);report.put("heldOutCount",heldOut);report.put("judgmentCount",judgments.size());report.put("examplesWithAtLeastTwoReviewers",examplesWithTwoReviewers);report.put("pairwiseDimensionAgreementFraction",allPairs.isEmpty()?null:allPairs.stream().filter(Boolean::booleanValue).count()/(double)allPairs.size());report.put("reviewerPairResults",pairResults);report.put("currentFidelityPassCount",examples.size()-evidenceProblems.size());report.put("fidelityProblems",evidenceProblems);report.put("uniqueReviewerCount",judgments.stream().map(j->j.get("reviewer")).distinct().count());report.put("aggregateGradeThresholdsJustified",false);report.put("falsePositiveFalseNegativeAnalysis","NOT_RUN_NO_CALIBRATED_THRESHOLDS");report.put("activationEligible",false);report.put("gradingStatus","CALIBRATION_INCOMPLETE");
    var missing=new ArrayList<String>();if(!evidenceProblems.isEmpty())missing.add("Expired, stale or conflicting source-fidelity evidence requires revalidation.");if(examples.isEmpty())missing.add("No examples imported.");if(examples.stream().noneMatch(e->"HELD_OUT".equals(e.get("split"))))missing.add("No held-out examples.");if(examplesWithTwoReviewers<examples.size())missing.add("Every calibration example requires at least two distinct blind reviewers.");if(judgments.stream().anyMatch(j->"UNKNOWN".equals(j.get("anchor"))))missing.add("Resolve reviewer UNKNOWN quality anchors through independent adjudication.");missing.add("Statistical threshold selection and held-out false-positive/false-negative validation have not been approved or run.");missing.add("No legitimate full-pipeline B-to-A golden acceptance is recorded.");report.put("missingRequirements",missing);
    return report;
  }

  public Map<String,Object> calibrationPreview(String version,HttpServletRequest servlet) {
    String actor=principal(servlet,"CREATIVE_QUALITY_ARCHITECTURE_APPROVER");
    var examples=jdbc.sql("SELECT e.example_id,e.source_story_id,e.source_revision,e.source_fingerprint,e.prompt_version_label,e.prompt_fingerprint,e.prompt_text,e.source_story_text,e.content_profile,e.generator,e.target_duration_seconds,e.source_fidelity_evidence_id,e.split,e.case_type,e.provenance::text,f.decision,f.reviewer_principal FROM cpq_calibration_examples e JOIN cpq_fidelity_reviews f ON f.evidence_id=e.source_fidelity_evidence_id WHERE e.corpus_version=:version ORDER BY e.example_id")
      .param("version",version).query((rs,n)->{var x=new LinkedHashMap<String,Object>();x.put("exampleId",rs.getString("example_id"));x.put("sourceStoryId",rs.getString("source_story_id"));x.put("sourceRevision",rs.getString("source_revision"));x.put("sourceFingerprint",rs.getString("source_fingerprint"));x.put("promptVersion",rs.getString("prompt_version_label"));x.put("promptSha256",rs.getString("prompt_fingerprint"));x.put("promptText",rs.getString("prompt_text"));x.put("approvedStoryText",rs.getString("source_story_text"));x.put("contentProfile",rs.getString("content_profile"));x.put("generator",rs.getString("generator"));x.put("durationSeconds",rs.getBigDecimal("target_duration_seconds"));x.put("sourceFidelityEvidence",Map.of("evidenceId",rs.getString("source_fidelity_evidence_id"),"decision",rs.getString("decision"),"reviewerId",rs.getString("reviewer_principal")));x.put("split",rs.getString("split"));x.put("caseType",rs.getString("case_type"));x.put("provenance",read(rs.getString("provenance")));return x;}).list();
    var records=new ArrayList<Map<String,Object>>();
    for(var example:examples){qualifiedImportEvidence(UUID.fromString(text(map(example.get("sourceFidelityEvidence")).get("evidenceId"))));String id=String.valueOf(example.get("exampleId"));var reviews=jdbc.sql("SELECT reviewer_principal,dimension_judgments::text,source_fidelity_decision,overall_quality_anchor,evidence_citations::text,confidence::text,review_method_version,reviewed_at FROM cpq_calibration_judgments WHERE example_id=:id ORDER BY reviewer_principal")
        .param("id",UUID.fromString(id)).query((rs,n)->{var j=new LinkedHashMap<String,Object>();j.put("reviewerId",rs.getString(1));j.put("dimensions",read(rs.getString(2)));j.put("sourceFidelityDecision",rs.getString(3));j.put("overallQualityAnchor",rs.getString(4));j.put("evidenceCitations",readJsonList(rs.getString(5)));j.put("confidence",read(rs.getString(6)));j.put("reviewMethodVersion",rs.getString(7));j.put("reviewedAt",rs.getTimestamp(8).toInstant().toString());return j;}).list();
      var item=new LinkedHashMap<>(example);item.put("reviewerJudgments",reviews);item.put("reviewerProvenance",reviews.stream().map(j->Map.of("reviewerId",j.get("reviewerId"),"role","CREATIVE_QUALITY_REVIEWER","reviewMethodVersion",j.get("reviewMethodVersion"),"reviewedAt",j.get("reviewedAt"))).toList());item.put("reviewMethodVersion",reviews.isEmpty()?null:reviews.getFirst().get("reviewMethodVersion"));item.put("reviewedAt",reviews.isEmpty()?null:reviews.getFirst().get("reviewedAt"));records.add(item);
    }
    var preview=ml.workflow("creative-prompt-quality/calibration-preview",Map.of("records",records));
    var stored=new LinkedHashMap<String,Object>(preview);stored.put("corpusVersion",version);stored.put("persistedBy",actor);stored.put("reportingStatus","PROVISIONAL_ONLY");stored.put("activated",false);
    jdbc.sql("INSERT INTO cpq_calibration_reports(corpus_version,rubric_version,corpus_fingerprint,report,created_by) VALUES(:version,:rubric,:fingerprint,CAST(:report AS jsonb),:actor)")
      .param("version",version).param("rubric",RUBRIC).param("fingerprint",String.valueOf(preview.getOrDefault("corpusFingerprint",hash(encode(records))))).param("report",encode(stored)).param("actor",actor).update();
    return stored;
  }

}
