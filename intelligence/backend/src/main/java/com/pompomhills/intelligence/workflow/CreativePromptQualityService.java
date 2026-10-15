package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.pompomhills.intelligence.quality.QualityMlClient;
import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
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

  public CreativePromptQualityService(JdbcClient jdbc, ObjectMapper json, QualityMlClient ml) {
    this.jdbc=jdbc; this.json=json; this.ml=ml;
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
    String story=String.valueOf(approval.getOrDefault("approvedText",""));
    String contextStory=String.valueOf(context.getOrDefault("approvedStoryText",story));
    if(story.isBlank() || !hash(story).equals(hash(contextStory))) throw new ResponseStatusException(CONFLICT,"Candidate context does not match the current approved story");
    if(context.get("storyApprovalRecordId")!=null && !String.valueOf(context.get("storyApprovalRecordId")).equals(String.valueOf(approvalId)))
      throw new ResponseStatusException(CONFLICT,"Candidate is bound to a different story approval revision");
    var out=new LinkedHashMap<String,Object>();out.put("text",story);out.put("approval",approval);out.put("session",sessionPayload);out.put("roleContext",context);out.put("approvalRecordId",String.valueOf(approvalId));
    return out;
  }
  private String savedPrompt(long contentId,long promptVersionId) {
    return jdbc.sql("SELECT raw_text FROM prompt_versions WHERE content_id=:content AND id=:prompt")
      .param("content",contentId).param("prompt",promptVersionId).query(String.class).optional()
      .orElseThrow(()->new ResponseStatusException(CONFLICT,"Immutable source prompt is unavailable"));
  }
  private Map<String,Object> currentFidelity(UUID analysisId,UUID comparisonId,String candidateId,String storyHash,String sourceHash,String candidateHash,String interventionHash,String settingsHash,String ruleset) {
    var matches=jdbc.sql("SELECT evidence_id,decision,reviewer_principal,review_method_version,citations,rationale,valid_until,created_at FROM cpq_fidelity_reviews WHERE analysis_id=:analysis AND comparison_id=:comparison AND candidate_prompt_fingerprint=:candidate AND approved_story_fingerprint=:story AND original_prompt_fingerprint=:source AND intervention_fingerprint=:intervention AND production_settings_fingerprint=:settings AND ruleset_version=:ruleset AND (valid_until IS NULL OR valid_until>now()) ORDER BY created_at DESC")
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
    String storyId=String.valueOf(map(story.get("session")).getOrDefault("sourceStoryRecordId",roleContext.getOrDefault("storyId","UNKNOWN")));
    String revision=String.valueOf(roleContext.getOrDefault("storyRevisionId",map(story.get("session")).getOrDefault("storyRevisionId",map(story.get("approval")).getOrDefault("revisionId","UNKNOWN"))));
    if("UNKNOWN".equals(storyId)||"UNKNOWN".equals(revision))throw new ResponseStatusException(CONFLICT,"Approved story ID and revision binding are required for fidelity evidence");
    UUID evidenceId=UUID.randomUUID();
    var reviewSettings=new LinkedHashMap<String,Object>();for(String key:List.of("contentProfile","generator","desiredDuration","settings","openingStrategy"))reviewSettings.put(key,map(baseline.get("boundRequest")).get(key));
    jdbc.sql("INSERT INTO cpq_fidelity_reviews(evidence_id,content_id,prompt_version_id,approved_story_id,approved_revision,approved_story_fingerprint,original_prompt_fingerprint,candidate_prompt_fingerprint,intervention_fingerprint,changed_beat_ids,source_event_mapping,analysis_id,comparison_id,ruleset_version,cpq_rubric_version,production_settings_fingerprint,reviewer_principal,reviewer_authority,review_method_version,citations,rationale,decision,valid_until) VALUES(:id,:content,:promptId,:storyId,:revision,:story,:source,:candidate,:intervention,CAST(:beats AS jsonb),CAST(:mapping AS jsonb),:analysis,:comparison,:ruleset,:rubric,:settings,:reviewer,'EVIDENCE_REVIEWER',:method,CAST(:citations AS jsonb),:rationale,:decision,:expiry)")
      .param("id",evidenceId).param("content",content).param("promptId",promptId).param("storyId",storyId).param("revision",revision).param("story",storyHash).param("source",sourceHash).param("candidate",candidateHash).param("intervention",interventionHash).param("beats",encode(changedBeatIds)).param("mapping",encode(mappings)).param("analysis",analysisId).param("comparison",comparisonId).param("ruleset",String.valueOf(canonical.get("rulesetVersion"))).param("rubric",RUBRIC).param("settings",hash(encode(reviewSettings))).param("reviewer",reviewer).param("method",method).param("citations",encode(citations)).param("rationale",rationale.trim()).param("decision",decision).param("expiry",java.sql.Timestamp.from(expiry)).update();
    return Map.of("evidenceId",evidenceId.toString(),"decision",decision,"reviewerPrincipal",reviewer,"reviewerAuthority","EVIDENCE_REVIEWER","candidateFingerprint",candidateHash,"validUntil",expiry.toString(),"immutable",true,"renderAuthorized",false);
  }

  public Map<String,Object> calibrationState() {
    var counts=jdbc.sql("SELECT (SELECT count(*) FROM cpq_calibration_examples) examples,(SELECT count(*) FROM cpq_calibration_judgments) judgments,(SELECT count(*) FROM cpq_fidelity_reviews WHERE decision='PASS' AND valid_until>now()) fidelityPasses,(SELECT activated FROM cpq_policy_state WHERE singleton=TRUE) activated")
      .query((rs,n)->Map.<String,Object>of("examples",rs.getInt("examples"),"judgments",rs.getInt("judgments"),"currentFidelityPasses",rs.getInt("fidelityPasses"),"activated",rs.getBoolean("activated"))).single();
    var corpora=jdbc.sql("SELECT corpus_version,state,corpus_sha256,created_by,created_at,approved_by FROM cpq_calibration_corpora ORDER BY created_at DESC")
      .query((rs,n)->Map.<String,Object>of("version",rs.getString("corpus_version"),"state",rs.getString("state"),"sha256",Objects.toString(rs.getString("corpus_sha256"),""),"createdBy",rs.getString("created_by"),"createdAt",rs.getTimestamp("created_at").toInstant().toString(),"approvedBy",Objects.toString(rs.getString("approved_by"),""))).list();
    return Map.of("rubricVersion",RUBRIC,"gradingStatus","CALIBRATION_INCOMPLETE","activated",counts.get("activated"),"counts",counts,"corpora",corpora,"missingRequirements",List.of("Independent reviewed calibration examples","Held-out validation and false-positive/false-negative analysis","Reviewer agreement validation","Full-pipeline B-to-A golden acceptance","Authorized activation record"));
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

  public Map<String,Object> addCalibrationExample(String version,Map<String,Object> body,HttpServletRequest servlet) {
    String actor=principal(servlet,"CREATIVE_QUALITY_ARCHITECTURE_APPROVER");String prompt=String.valueOf(body.getOrDefault("promptText",""));if(prompt.isBlank())throw new ResponseStatusException(BAD_REQUEST,"Complete prompt text is required");
    UUID fidelityId;try{fidelityId=UUID.fromString(String.valueOf(body.get("sourceFidelityEvidenceId")));}catch(Exception e){throw new ResponseStatusException(BAD_REQUEST,"Existing independent source-fidelity evidence ID is required");}
    var evidence=jdbc.sql("SELECT decision,approved_story_id,approved_revision,candidate_prompt_fingerprint,approved_story_fingerprint FROM cpq_fidelity_reviews WHERE evidence_id=:id AND valid_until>now()")
      .param("id",fidelityId).query((rs,n)->Map.<String,Object>of("decision",rs.getString(1),"storyId",rs.getString(2),"revision",rs.getString(3),"candidateHash",rs.getString(4),"sourceHash",rs.getString(5))).optional().orElseThrow(()->new ResponseStatusException(CONFLICT,"Calibration import requires a current independent fidelity record"));
    if(!prompt.isBlank()&&!hash(prompt).equals(evidence.get("candidateHash")))throw new ResponseStatusException(CONFLICT,"Calibration prompt must match its independently reviewed candidate fingerprint");
    if(body.get("sourceStoryId")!=null&&!String.valueOf(body.get("sourceStoryId")).equals(evidence.get("storyId"))||body.get("sourceRevision")!=null&&!String.valueOf(body.get("sourceRevision")).equals(evidence.get("revision")))throw new ResponseStatusException(CONFLICT,"Calibration source identity must match the independent fidelity record");
    String split=String.valueOf(body.get("split"));if(!Set.of("CALIBRATION","HELD_OUT").contains(split))throw new ResponseStatusException(BAD_REQUEST,"Split must be CALIBRATION or HELD_OUT");
    UUID id=UUID.randomUUID();String promptHash=hash(prompt),storyText=String.valueOf(body.getOrDefault("approvedStoryText",""));String storyHash=hash(storyText);
    if(storyText.isBlank()||!storyHash.equals(evidence.get("sourceHash")))throw new ResponseStatusException(CONFLICT,"Calibration approved story text must match its independent fidelity record");
    String caseType=String.valueOf(body.getOrDefault("caseType","GENERAL_PROMPT"));
    if(!Set.of("EXCELLENT_EXECUTION","STRONG_EXECUTION","ADEQUATE_IMPROVABLE","WEAK_EXECUTION","SOURCE_FAITHFUL_IMPROVEMENT","COSMETIC_REWRITE","PRODUCTION_REGRESSION","CONSTRAINED_UNIMPROVABLE","GENERAL_PROMPT").contains(caseType))throw new ResponseStatusException(BAD_REQUEST,"Unsupported calibration case type");
    if(!(body.get("durationSeconds") instanceof Number duration)||!Double.isFinite(duration.doubleValue())||duration.doubleValue()<=0)throw new ResponseStatusException(BAD_REQUEST,"Positive target duration is required");
    String versionLabel=String.valueOf(body.getOrDefault("promptVersionLabel",""));if(versionLabel.isBlank())throw new ResponseStatusException(BAD_REQUEST,"Prompt version label is required");
    jdbc.sql("INSERT INTO cpq_calibration_examples(example_id,corpus_version,source_story_id,source_revision,source_fingerprint,prompt_version_id,prompt_version_label,prompt_fingerprint,prompt_text,source_story_text,content_profile,generator,target_duration_seconds,source_fidelity_evidence_id,observed_render_evidence,audience_evidence,case_type,split,provenance,created_by) VALUES(:id,:corpus,:story,:revision,:sourceHash,:promptId,:versionLabel,:promptHash,:prompt,:storyText,:profile,:generator,:duration,:fidelity,CAST(:render AS jsonb),CAST(:audience AS jsonb),:caseType,:split,CAST(:provenance AS jsonb),:actor)")
      .param("id",id).param("corpus",version).param("story",String.valueOf(body.getOrDefault("sourceStoryId",evidence.get("storyId")))).param("revision",String.valueOf(body.getOrDefault("sourceRevision",evidence.get("revision")))).param("sourceHash",storyHash).param("promptId",body.get("promptVersionId"),java.sql.Types.BIGINT).param("versionLabel",versionLabel).param("promptHash",promptHash).param("prompt",prompt).param("storyText",storyText).param("profile",String.valueOf(body.getOrDefault("contentProfile","UNKNOWN"))).param("generator",String.valueOf(body.getOrDefault("generator","UNKNOWN"))).param("duration",duration.doubleValue()).param("fidelity",fidelityId).param("render",encode(body.getOrDefault("renderEvidence",Map.of()))).param("audience",encode(body.getOrDefault("audienceEvidence",Map.of()))).param("caseType",caseType).param("split",split).param("provenance",encode(body.getOrDefault("provenance",Map.of()))).param("actor",actor).update();
    return Map.of("exampleId",id.toString(),"corpusVersion",version,"promptSha256",promptHash,"split",split,"independentFidelityEvidenceId",fidelityId.toString(),"humanQualityGrade", "NOT_YET_REVIEWED","activated",false);
  }

  public Map<String,Object> calibrationReviewPacket(UUID exampleId,HttpServletRequest servlet) {
    principal(servlet,"CREATIVE_QUALITY_REVIEWER");
    return jdbc.sql("SELECT example_id,corpus_version,prompt_text,content_profile,generator,target_duration_seconds FROM cpq_calibration_examples WHERE example_id=:id")
      .param("id",exampleId).query((rs,n)->Map.<String,Object>of("exampleId",rs.getString(1),"corpusVersion",rs.getString(2),"promptText",rs.getString(3),"contentProfile",rs.getString(4),"generator",rs.getString(5),"durationSeconds",rs.getBigDecimal(6),"blind",true,"existingJudgmentsVisible",false)).optional()
      .orElseThrow(()->new ResponseStatusException(NOT_FOUND,"Calibration example not found"));
  }

  @Transactional
  public Map<String,Object> submitCalibrationJudgment(UUID exampleId,Map<String,Object> body,HttpServletRequest servlet) {
    String reviewer=principal(servlet,"CREATIVE_QUALITY_REVIEWER");var packet=calibrationReviewPacket(exampleId,servlet);
    var dims=map(body.get("dimensions"));if(!dims.keySet().equals(new HashSet<>(DIMENSIONS)))throw new ResponseStatusException(BAD_REQUEST,"Judgment must include exactly all six CPQ dimensions");
    String reviewedPrompt=String.valueOf(packet.get("promptText"));
    Set<String> levels=Set.of("EXCELLENT","STRONG","ADEQUATE","WEAK","UNKNOWN");
    for(String dim:DIMENSIONS){var item=map(dims.get(dim));var citations=maps(item.get("evidenceCitations"));if(!levels.contains(String.valueOf(item.get("level")))||String.valueOf(item.getOrDefault("rationale","")).trim().length()<20||citations.isEmpty())throw new ResponseStatusException(BAD_REQUEST,"Each dimension needs an allowed judgment, evidence citation and concrete rationale");for(var citation:citations){String quote=String.valueOf(citation.getOrDefault("quote",""));if(quote.isBlank()||!reviewedPrompt.contains(quote))throw new ResponseStatusException(BAD_REQUEST,"Every blinded-review citation must quote the exact reviewed prompt text");}}
    String fidelity=String.valueOf(body.get("sourceFidelityDecision"));if(!Set.of("PASS","FAIL","UNKNOWN").contains(fidelity))throw new ResponseStatusException(BAD_REQUEST,"Invalid source-fidelity judgment");
    var evidence=jdbc.sql("SELECT source_fidelity_evidence_id FROM cpq_calibration_examples WHERE example_id=:id").param("id",exampleId).query(UUID.class).single();
    String existingReviewer=jdbc.sql("SELECT reviewer_principal FROM cpq_fidelity_reviews WHERE evidence_id=:id").param("id",evidence).query(String.class).single();
    if(reviewer.equals(existingReviewer))throw new ResponseStatusException(FORBIDDEN,"A fidelity evidence producer cannot be the sole independent calibration reviewer");
    String method=String.valueOf(body.getOrDefault("reviewMethodVersion","cpq-human-blind-review-v1"));
    String anchor=String.valueOf(body.getOrDefault("overallQualityAnchor","UNKNOWN"));if(!Set.of("A+","A","B","C","F","UNKNOWN").contains(anchor))throw new ResponseStatusException(BAD_REQUEST,"Invalid blinded reviewer quality anchor");
    UUID id=UUID.randomUUID();jdbc.sql("INSERT INTO cpq_calibration_judgments(judgment_id,example_id,reviewer_principal,reviewer_role,rubric_version,review_method_version,dimension_judgments,source_fidelity_decision,overall_quality_anchor,evidence_citations,confidence) VALUES(:id,:example,:reviewer,'CREATIVE_QUALITY_REVIEWER',:rubric,:method,CAST(:dimensions AS jsonb),:fidelity,:anchor,CAST(:citations AS jsonb),CAST(:confidence AS jsonb))")
      .param("id",id).param("example",exampleId).param("reviewer",reviewer).param("rubric",RUBRIC).param("method",method).param("dimensions",encode(dims)).param("fidelity",fidelity).param("anchor",anchor).param("citations",encode(body.getOrDefault("evidenceCitations",List.of()))).param("confidence",encode(body.getOrDefault("confidence",Map.of()))).update();
    return Map.of("judgmentId",id.toString(),"exampleId",exampleId.toString(),"reviewerPrincipal",reviewer,"blindReview",true,"gradeActivated",false,"corpusVersion",packet.get("corpusVersion"));
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
    String corpusHash=hash(encode(Map.of("examples",examples,"judgments",judgments)));
    var report=new LinkedHashMap<String,Object>();report.put("rubricVersion",RUBRIC);report.put("corpusVersion",version);report.put("corpusFingerprint",corpusHash);report.put("exampleCount",examples.size());report.put("calibrationCount",calibration);report.put("heldOutCount",heldOut);report.put("judgmentCount",judgments.size());report.put("examplesWithAtLeastTwoReviewers",examplesWithTwoReviewers);report.put("pairwiseDimensionAgreementFraction",allPairs.isEmpty()?null:allPairs.stream().filter(Boolean::booleanValue).count()/(double)allPairs.size());report.put("reviewerPairResults",pairResults);report.put("aggregateGradeThresholdsJustified",false);report.put("falsePositiveFalseNegativeAnalysis","NOT_RUN_NO_CALIBRATED_THRESHOLDS");report.put("activationEligible",false);report.put("gradingStatus","CALIBRATION_INCOMPLETE");
    var missing=new ArrayList<String>();if(examples.isEmpty())missing.add("No examples imported.");if(examples.stream().noneMatch(e->"HELD_OUT".equals(e.get("split"))))missing.add("No held-out examples.");if(examplesWithTwoReviewers<examples.size())missing.add("Every calibration example requires at least two distinct blind reviewers.");if(judgments.stream().anyMatch(j->"UNKNOWN".equals(j.get("anchor"))))missing.add("Resolve reviewer UNKNOWN quality anchors through independent adjudication.");missing.add("Statistical threshold selection and held-out false-positive/false-negative validation have not been approved or run.");missing.add("No legitimate full-pipeline B-to-A golden acceptance is recorded.");report.put("missingRequirements",missing);
    return report;
  }

  public Map<String,Object> calibrationPreview(String version,HttpServletRequest servlet) {
    String actor=principal(servlet,"CREATIVE_QUALITY_ARCHITECTURE_APPROVER");
    var examples=jdbc.sql("SELECT e.example_id,e.source_story_id,e.source_revision,e.source_fingerprint,e.prompt_version_label,e.prompt_fingerprint,e.prompt_text,e.source_story_text,e.content_profile,e.generator,e.target_duration_seconds,e.source_fidelity_evidence_id,e.split,e.case_type,e.provenance::text,f.decision,f.reviewer_principal FROM cpq_calibration_examples e JOIN cpq_fidelity_reviews f ON f.evidence_id=e.source_fidelity_evidence_id WHERE e.corpus_version=:version ORDER BY e.example_id")
      .param("version",version).query((rs,n)->{var x=new LinkedHashMap<String,Object>();x.put("exampleId",rs.getString("example_id"));x.put("sourceStoryId",rs.getString("source_story_id"));x.put("sourceRevision",rs.getString("source_revision"));x.put("sourceFingerprint",rs.getString("source_fingerprint"));x.put("promptVersion",rs.getString("prompt_version_label"));x.put("promptSha256",rs.getString("prompt_fingerprint"));x.put("promptText",rs.getString("prompt_text"));x.put("approvedStoryText",rs.getString("source_story_text"));x.put("contentProfile",rs.getString("content_profile"));x.put("generator",rs.getString("generator"));x.put("durationSeconds",rs.getBigDecimal("target_duration_seconds"));x.put("sourceFidelityEvidence",Map.of("evidenceId",rs.getString("source_fidelity_evidence_id"),"decision",rs.getString("decision"),"reviewerId",rs.getString("reviewer_principal")));x.put("split",rs.getString("split"));x.put("caseType",rs.getString("case_type"));x.put("provenance",read(rs.getString("provenance")));return x;}).list();
    var records=new ArrayList<Map<String,Object>>();
    for(var example:examples){String id=String.valueOf(example.get("exampleId"));var reviews=jdbc.sql("SELECT reviewer_principal,dimension_judgments::text,source_fidelity_decision,overall_quality_anchor,evidence_citations::text,confidence::text,review_method_version,reviewed_at FROM cpq_calibration_judgments WHERE example_id=:id ORDER BY reviewer_principal")
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
