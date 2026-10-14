package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/** Current immutable evidence + trusted container identity; request JSON never supplies authority. */
@Service
public class Step6GovernanceService {
  public static final String POLICY = "STEP6_RESOLUTION_V2";
  public static final String EXCEPTION = "ATTEMPT_COUNT_EXCEPTION_V1";
  private final JdbcClient jdbc;
  private final ObjectMapper json;
  private final Map<String,Object> metadata;
  private final String currentRuleset;
  public record Actor(String name, Set<String> roles) {
    public boolean has(String role) { return name != null && !name.isBlank() && roles.contains(role); }
    public static Actor from(HttpServletRequest request) {
      if (request.getUserPrincipal() == null) return new Actor("", Set.of());
      var roles = new HashSet<String>();
      for (String role : List.of("ARCHITECTURE_APPROVER", "EVIDENCE_REVIEWER", "PRODUCTION_OPERATOR"))
        if (request.isUserInRole(role)) roles.add(role);
      return new Actor(request.getUserPrincipal().getName(), Set.copyOf(roles));
    }
  }
  public Step6GovernanceService(JdbcClient jdbc, ObjectMapper json,
      @Value("${pompom.governance.current-ruleset:1.11}") String currentRuleset) {
    this.jdbc=jdbc; this.json=json; this.currentRuleset=currentRuleset;
    try (var input=getClass().getResourceAsStream("/governance/step6-policy.json")) {
      metadata=json.readValue(input,new TypeReference<Map<String,Object>>(){});
    } catch(Exception e) { throw new IllegalStateException("Governed resolution policy unavailable",e); }
  }
  @SuppressWarnings("unchecked") private static Map<String,Object> map(Object value) {
    return value instanceof Map<?,?> ? (Map<String,Object>)value : Map.of();
  }
  @SuppressWarnings("unchecked") private static List<Map<String,Object>> rows(Object value) {
    return value instanceof List<?> ? (List<Map<String,Object>>)value : List.of();
  }
  private String encode(Object value) {
    try { return json.writer().with(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS).writeValueAsString(value); }
    catch(Exception e) { throw new IllegalStateException(e); }
  }
  public static String sha(String value) {
    try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
    catch(Exception e) { throw new IllegalStateException(e); }
  }
  private Map<String,Object> read(String value) {
    try { return json.readValue(value,new TypeReference<Map<String,Object>>(){}); }
    catch(Exception e) { throw new IllegalStateException(e); }
  }
  private Map<String,Object> event(UUID id, String kind) {
    return jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id AND kind=:kind")
      .param("id",id).param("kind",kind).query(String.class).optional().map(this::read)
      .orElseThrow(()->new IllegalArgumentException("Required persisted "+kind+" evidence unavailable"));
  }
  private List<Map<String,Object>> events(String kind) {
    return jdbc.sql("SELECT id,payload::text FROM post_family_workflow_events WHERE kind=:kind ORDER BY created_at DESC,id DESC")
      .param("kind",kind).query((rs,n)->{var x=read(rs.getString(2));x.put("recordId",rs.getString(1));return x;}).list();
  }
  private Map<String,Object> context(UUID id) {
    var analysis=event(id,"REVIEW"); var canonical=map(analysis.get("canonicalRuleEvaluation"));
    String content=String.valueOf(analysis.get("contentId")), prompt=String.valueOf(analysis.get("promptVersionId"));
    var latest=events("REVIEW").stream().filter(x->content.equals(String.valueOf(x.get("contentId"))) && prompt.equals(String.valueOf(x.get("promptVersionId")))).findFirst();
    if (latest.isEmpty() || !id.toString().equals(latest.get().get("recordId"))) throw new IllegalStateException("STALE_ANALYSIS");
    if (!currentRuleset.equals(canonical.get("rulesetVersion"))) throw new IllegalStateException("STALE_RULESET");
    if (!"EVALUATED".equals(canonical.get("status"))) throw new IllegalStateException("CANONICAL_EVIDENCE_UNAVAILABLE");
    String text=jdbc.sql("SELECT raw_text FROM prompt_versions WHERE content_id=:content AND id=:prompt")
      .param("content",Long.valueOf(content)).param("prompt",Long.valueOf(prompt)).query(String.class).single();
    if (!text.equals(analysis.get("originalPrompt"))) throw new IllegalStateException("STALE_PROMPT");
    var bound=map(analysis.get("boundRequest")); var target=new LinkedHashMap<String,Object>();
    for(String key:List.of("contentProfile","generator","desiredDuration","settings","openingStrategy")) target.put(key,bound.get(key));
    var setting=events("PRODUCTION_SETTINGS").stream().filter(x->content.equals(String.valueOf(x.get("contentId"))) && prompt.equals(String.valueOf(x.get("promptVersionId")))).findFirst();
    if(setting.isPresent()) {
      for(String key:List.of("contentProfile","generator","desiredDuration","openingStrategy"))
        if(setting.get().containsKey(key) && !String.valueOf(setting.get().get(key)).equals(String.valueOf(bound.get(key)))) throw new IllegalStateException("STALE_SETTINGS");
      if(setting.get().containsKey("aspectRatio") && !Objects.equals(setting.get().get("aspectRatio"),map(bound.get("settings")).get("aspectRatio"))) throw new IllegalStateException("STALE_SETTINGS");
    }
    var result=new LinkedHashMap<String,Object>();
    result.put("analysisId",id.toString());result.put("rulesetVersion",currentRuleset);result.put("promptVersionId",prompt);
    result.put("contentId",content);result.put("promptSha256",sha(text));result.put("settingsSha256",sha(encode(target)));
    result.put("analysisBindingHash",analysis.get("bindingHash"));result.put("policyVersion",POLICY);
    var storySession=events("CREATIVE_STUDIO_SESSION").stream().filter(x->content.equals(String.valueOf(x.get("contentId"))) && prompt.equals(String.valueOf(x.get("promptVersionId")))).findFirst();
    result.put("storyApprovalId",storySession.map(x->String.valueOf(x.get("approvalRecordId"))).orElse("MISSING"));
    if(storySession.isPresent() && storySession.get().get("approvalRecordId") != null) {
      var approvedStory=event(UUID.fromString(String.valueOf(storySession.get().get("approvalRecordId"))),"STORY_APPROVAL");
      result.put("approvedStorySha256",sha(String.valueOf(approvedStory.getOrDefault("approvedText",""))));
    }
    result.put("analysis",analysis);result.put("canonical",canonical);return result;
  }
  private String binding(Map<String,Object> context) {
    var identity=new LinkedHashMap<>(context);identity.remove("analysis");identity.remove("canonical");return sha(encode(identity));
  }
  private List<Map<String,Object>> findings(Map<String,Object> ctx) {
    var result=new ArrayList<Map<String,Object>>();var canon=map(ctx.get("canonical"));
    for(String group:List.of("failedRules","unknownRules")) for(var rule:rows(canon.get(group))) {
      String id=String.valueOf(rule.get("ruleId")); var meta=map(map(metadata.get("rules")).get(id));
      if(meta.isEmpty()) meta=map(metadata.get("defaultFailure"));
      String type=String.valueOf(meta.get("resolutionType"));
      if(group.equals("unknownRules")) type=String.valueOf(meta.getOrDefault("unknownType","EVIDENCE_REQUIRED"));
      var details=map(rule.get("details"));
      if(meta.containsKey("verifiedFailureType") && !details.containsKey("missingEvidence")
          && !"EVIDENCE_INCOMPLETE_FAILURE".equals(details.get("failureBasis")) && details.containsKey("visualEvidence"))
        type=String.valueOf(meta.get("verifiedFailureType"));
      var item=new LinkedHashMap<String,Object>(rule);item.put("resolutionType",type);
      item.put("blocksText",group.equals("failedRules") && (Boolean.TRUE.equals(meta.get("blocksText")) || "CONFIRMED_HARD_BLOCKER".equals(type)));
      item.put("blocksRender",true);item.put("metadata",meta);result.add(item);
    }
    return result;
  }
  private Optional<Map<String,Object>> validEvent(String kind, Map<String,Object> ctx) {
    String hash=binding(ctx);var revoked=events("GOVERNANCE_REVOCATION").stream().map(x->String.valueOf(x.get("targetRecordId"))).toList();return events(kind).stream().filter(x->!revoked.contains(String.valueOf(x.get("recordId"))) && hash.equals(x.get("scopeSha256")) && POLICY.equals(x.get("policyVersion")) && Instant.parse(String.valueOf(x.get("expiresAt"))).isAfter(Instant.now())).findFirst();
  }
  private List<String> exceptionReasons(Map<String,Object> ctx, Actor actor) {
    var reasons=new ArrayList<String>();if(!actor.has("ARCHITECTURE_APPROVER")) reasons.add("AUTHENTICATED_ARCHITECTURE_APPROVER_REQUIRED");
    var canon=map(ctx.get("canonical"));var analysis=map(ctx.get("analysis"));var bound=map(analysis.get("boundRequest"));
    if(!(bound.get("desiredDuration") instanceof Number duration) || duration.doubleValue()>20 || duration.doubleValue()<=0) reasons.add("ELIGIBLE_SHORT_FORM_REQUIRED");
    boolean applicable=rows(canon.get("failedRules")).stream().anyMatch(x->"ATTEMPT_001".equals(x.get("ruleId")));
    if(!applicable) reasons.add("TARGET_RULE_MUST_BE_APPLICABLE_FAIL");
    long attempts=rows(map(canon.get("videoPlanIR")).get("beats")).stream().filter(b->Boolean.TRUE.equals(b.get("isAttempt")) && Boolean.TRUE.equals(map(b.get("attemptEvidence")).get("sourceBound")) && !Boolean.TRUE.equals(map(b.get("attemptEvidence")).get("duplicateSourceEvent"))).count();
    if(attempts<2) reasons.add("TWO_GENUINE_SOURCE_BOUND_ATTEMPTS_REQUIRED");
    var support=validEvent("GOVERNANCE_SUPPORT",ctx);
    if(support.isEmpty()) reasons.add("INDEPENDENT_STORY_PROGRESSION_PAYOFF_EVIDENCE_REQUIRED");
    else if(actor.name().equals(support.get().get("principal"))) reasons.add("INDEPENDENT_APPROVER_REQUIRED");
    return reasons;
  }
  private Optional<Map<String,Object>> effectiveException(Map<String,Object> ctx) {
    var approved=validEvent("GOVERNANCE_EXCEPTION",ctx);
    var support=validEvent("GOVERNANCE_SUPPORT",ctx);
    if(approved.isEmpty() || support.isEmpty()
        || !EXCEPTION.equals(approved.get().get("exceptionPolicy"))
        || !"ATTEMPT_001".equals(approved.get().get("ruleId"))
        || !"ARCHITECTURE_APPROVER".equals(approved.get().get("authenticatedRole"))
        || !"EVIDENCE_REVIEWER".equals(support.get().get("authenticatedRole"))
        || !Objects.equals(approved.get().get("supportRecordId"),support.get().get("recordId"))
        || Objects.equals(approved.get().get("principal"),support.get().get("principal"))) return Optional.empty();
    return approved;
  }
  public Map<String,Object> evaluate(UUID id, Actor actor) {
    var result=new LinkedHashMap<String,Object>();result.put("policyVersion",POLICY);
    try {
      var ctx=context(id);result.putAll(ctx);result.remove("analysis");result.remove("canonical");
      var fs=findings(ctx);result.put("findings",fs);
      var textReasons=new ArrayList<String>();if(!actor.has("PRODUCTION_OPERATOR")) textReasons.add("AUTHENTICATED_PRODUCTION_OPERATOR_REQUIRED");
      if(fs.stream().anyMatch(x->Boolean.TRUE.equals(x.get("blocksText")))) textReasons.add("SUPPORTED_TEXT_REPAIR_OR_HARD_FAILURE_REQUIRES_REVIEW");
      var actions=new LinkedHashMap<String,Object>();
      actions.put("TEXT_ACCEPTED_RENDER_BLOCKED",Map.of("allowed",textReasons.isEmpty(),"reasons",textReasons));
      actions.put("ATTEMPT_COUNT_EXCEPTION_V1",Map.of("allowed",exceptionReasons(ctx,actor).isEmpty(),"reasons",exceptionReasons(ctx,actor)));
      actions.put("INDEPENDENT_EVIDENCE_REVIEW",Map.of("allowed",actor.has("EVIDENCE_REVIEWER"),"reasons",actor.has("EVIDENCE_REVIEWER")?List.of():List.of("AUTHENTICATED_EVIDENCE_REVIEWER_REQUIRED")));
      actions.put("EVIDENCE_PREPARATION",Map.of("allowed",true,"reasons",List.of("NO_GENERATION_OR_RENDER_PERMISSION")));
      actions.put("PRODUCTION_RISK_ACKNOWLEDGEMENT",Map.of("allowed",actor.has("PRODUCTION_OPERATOR"),"reasons",actor.has("PRODUCTION_OPERATOR")?List.of():List.of("AUTHENTICATED_PRODUCTION_OPERATOR_REQUIRED")));
      result.put("allowedActions",actions);result.put("textAcceptance",validEvent("GOVERNANCE_TEXT_ACCEPTANCE",ctx).orElse(Map.of()));
      result.put("attemptException",effectiveException(ctx).orElse(Map.of()));result.put("renderPermission",false);
    } catch(IllegalStateException e) {result.put("blockedReason",e.getMessage());result.put("allowedActions",Map.of());}
    return result;
  }
  private void requireRole(Actor actor,String role) {
    if(!actor.has(role)) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"Authenticated "+role+" required");
  }
  @Transactional
  public Map<String,Object> command(UUID id,String action,Map<String,Object> request,Actor actor) {
    String role=action.equals("revoke")?"ARCHITECTURE_APPROVER":action.equals("support")?"EVIDENCE_REVIEWER":action.equals("exception")?"ARCHITECTURE_APPROVER":"PRODUCTION_OPERATOR";
    requireRole(actor,role);if(!Boolean.TRUE.equals(request.get("operatorConfirmed"))) throw new IllegalArgumentException("Explicit operator confirmation required");
    if(String.valueOf(request.getOrDefault("justification","")).trim().length()<20) throw new IllegalArgumentException("Concrete justification of at least 20 characters required");
    // Serialize commands with latest review/settings writers using the row lock as a scoped transaction boundary.
    jdbc.sql("SELECT id FROM prompt_versions WHERE content_id=(SELECT (payload->>'contentId')::bigint FROM post_family_workflow_events WHERE id=:id) AND id=(SELECT (payload->>'promptVersionId')::bigint FROM post_family_workflow_events WHERE id=:id) FOR UPDATE").param("id",id).query(Long.class).single();
    var ctx=context(id);var decision=evaluate(id,actor);var record=new LinkedHashMap<String,Object>();
    for(String key:List.of("analysisId","rulesetVersion","promptVersionId","contentId","promptSha256","settingsSha256","analysisBindingHash","policyVersion")) record.put(key,ctx.get(key));
    record.put("storyApprovalId",ctx.get("storyApprovalId"));record.put("approvedStorySha256",ctx.get("approvedStorySha256"));
    record.put("scopeSha256",binding(ctx));record.put("principal",actor.name());record.put("authenticatedRole",role);
    record.put("operatorConfirmed",true);record.put("justification",String.valueOf(request.get("justification")).trim());
    record.put("createdAt",Instant.now().toString());record.put("expiresAt",Instant.now().plusSeconds(86400).toString());
    record.put("provenance","AUTHENTICATED_OPERATOR");record.put("unresolvedFindings",findings(ctx));
    String kind;
    switch(action) {
      case "revoke" -> {
        UUID target=UUID.fromString(String.valueOf(request.get("targetRecordId")));
        var candidate=jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id AND kind IN ('GOVERNANCE_EXCEPTION','GOVERNANCE_SUPPORT','GOVERNANCE_RISK_ACCEPTANCE','GOVERNANCE_TEXT_ACCEPTANCE')").param("id",target).query(String.class).optional().map(this::read).orElseThrow(()->new IllegalArgumentException("Governance record unavailable"));
        if(!Objects.equals(candidate.get("scopeSha256"),binding(ctx))) throw new IllegalArgumentException("Revocation scope mismatch");
        record.put("targetRecordId",target.toString());kind="GOVERNANCE_REVOCATION";
      }
      case "support" -> {
        var sessions=events("CREATIVE_STUDIO_SESSION");
        var session=sessions.stream().filter(x->String.valueOf(ctx.get("contentId")).equals(String.valueOf(x.get("contentId"))) && String.valueOf(ctx.get("promptVersionId")).equals(String.valueOf(x.get("promptVersionId")))) .findFirst().orElseThrow(()->new IllegalStateException("APPROVED_STORY_BINDING_REQUIRED"));
        var story=event(UUID.fromString(String.valueOf(session.get("approvalRecordId"))),"STORY_APPROVAL");
        String approved=String.valueOf(story.getOrDefault("approvedText",""));if(approved.isBlank()) throw new IllegalStateException("APPROVED_STORY_REQUIRED");
        String prompt=String.valueOf(map(ctx.get("analysis")).get("originalPrompt"));var proofs=new LinkedHashMap<String,Object>();
        var quotes=new HashSet<String>();
        for(String dimension:List.of("miniStory","activeProgression","payoff")) {
          var proof=map(request.get(dimension));String quote=String.valueOf(proof.getOrDefault("sourceQuote",""));String storyQuote=String.valueOf(proof.getOrDefault("approvedStoryQuote",""));
          if(quote.length()<10 || !prompt.contains(quote) || storyQuote.length()<5 || !approved.contains(storyQuote) || String.valueOf(proof.getOrDefault("reason","")).length()<20) throw new IllegalArgumentException("Independent source/story evidence required for "+dimension);
          quotes.add(quote);proofs.put(dimension,Map.of("sourceQuote",quote,"approvedStoryQuote",storyQuote,"reason",proof.get("reason")));
        }
        if(quotes.size()<3 || !Boolean.TRUE.equals(request.get("approvedEventsPreserved"))) throw new IllegalArgumentException("Distinct independent proofs and approved-event preservation required");
        record.put("support",proofs);record.put("approvedStorySha256",sha(approved));record.put("storyApprovalId",session.get("approvalRecordId"));record.put("approvedEventsPreserved",true);kind="GOVERNANCE_SUPPORT";
      }
      case "exception" -> {
        if(!"ATTEMPT_001".equals(request.get("ruleId")) || !EXCEPTION.equals(request.get("exceptionPolicy"))) throw new IllegalArgumentException("Exception outside governed rule scope");
        var reasons=exceptionReasons(ctx,actor);if(!reasons.isEmpty()) throw new IllegalStateException(String.join(", ",reasons));
        var support=validEvent("GOVERNANCE_SUPPORT",ctx).orElseThrow();
        record.put("ruleId","ATTEMPT_001");record.put("exceptionPolicy",EXCEPTION);record.put("supportRecordId",support.get("recordId"));record.put("supportPrincipal",support.get("principal"));kind="GOVERNANCE_EXCEPTION";
      }
      case "text-acceptance" -> {
        if(!Boolean.TRUE.equals(map(map(decision.get("allowedActions")).get("TEXT_ACCEPTED_RENDER_BLOCKED")).get("allowed"))) throw new IllegalStateException("Text acceptance is not eligible");
        record.put("state","TEXT_ACCEPTED_RENDER_BLOCKED");record.put("acceptedRisks",events("GOVERNANCE_RISK_ACCEPTANCE").stream().filter(x->binding(ctx).equals(x.get("scopeSha256"))).toList());record.put("pendingEvidence",findings(ctx).stream().filter(x->"EVIDENCE_REQUIRED".equals(x.get("resolutionType"))).toList());kind="GOVERNANCE_TEXT_ACCEPTANCE";
      }
      case "risk-acknowledgement" -> {
        String ruleId=String.valueOf(request.get("ruleId"));var match=findings(ctx).stream().filter(x->ruleId.equals(x.get("ruleId")) && "PRODUCTION_RISK_REVIEW".equals(x.get("resolutionType")) && Boolean.TRUE.equals(map(x.get("metadata")).get("acknowledgeable"))).findFirst();
        if(match.isEmpty()) throw new IllegalArgumentException("Only governed production risks may be acknowledged");
        record.put("ruleId",ruleId);record.put("acceptedRisk",match.get());kind="GOVERNANCE_RISK_ACCEPTANCE";
      }
      default -> throw new IllegalArgumentException("Unsupported governance action");
    }
    UUID key=UUID.randomUUID();jdbc.sql("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES(:id,:kind,:binding,CAST(:payload AS jsonb))")
      .param("id",key).param("kind",kind).param("binding",binding(ctx)).param("payload",encode(record)).update();record.put("recordId",key.toString());return record;
  }
  /** Lossless proof for the internal validation-evidence boundary. Never changes canonical fields. */
  public Map<String,Object> validationAdmission(long validationId,long content,long prompt,String promptHash,
      String ruleset,String reportJson,int blockerCount,int criticalCount) {
    try {
      var latest=events("REVIEW").stream().filter(x->String.valueOf(content).equals(String.valueOf(x.get("contentId"))) && String.valueOf(prompt).equals(String.valueOf(x.get("promptVersionId")))).findFirst().orElseThrow();
      var ctx=context(UUID.fromString(String.valueOf(latest.get("recordId"))));
      if(!Objects.equals(ctx.get("promptSha256"),promptHash) || !Objects.equals(ctx.get("rulesetVersion"),ruleset.split("\\+",2)[0])) return Map.of();
      var report=read(reportJson);
      var profileBinding=map(map(report.get("preRenderAssessment")).get("canonicalProfileAdmission"));
      if(!"profile-admission-v1".equals(profileBinding.get("version")) || !Objects.equals(ctx.get("analysisBindingHash"),profileBinding.get("workflowBindingHash"))) return Map.of();
      var failures=rows(report.get("failedRules"));
      int actualBlockers=0,actualCriticals=0,remainingBlockers=0,remainingCriticals=0;
      var ledger=new ArrayList<Map<String,Object>>();var exception=effectiveException(ctx);
      String scope=binding(ctx);var risks=events("GOVERNANCE_RISK_ACCEPTANCE");
      var revoked=events("GOVERNANCE_REVOCATION").stream().map(x->x.get("targetRecordId")).toList();
      var unique=new HashSet<String>();
      for(var failure:failures) {
        String rule=String.valueOf(failure.get("ruleId")),severity=String.valueOf(failure.get("severity"));
        if(!unique.add(rule)) return Map.of();
        if("BLOCKER".equals(severity)) actualBlockers++;
        if("CRITICAL".equals(severity)) actualCriticals++;
        var entry=new LinkedHashMap<String,Object>(failure);String disposition="UNRESOLVED";
        if("ATTEMPT_001".equals(rule) && exception.isPresent()) {
          disposition="ATTEMPT_COUNT_EXCEPTION_V1";entry.put("governanceRecordId",exception.get().get("recordId"));
        } else if(Boolean.TRUE.equals(map(map(metadata.get("rules")).get(rule)).get("acknowledgeable"))) {
          var accepted=risks.stream().filter(x->scope.equals(x.get("scopeSha256")) && rule.equals(x.get("ruleId")) && "PRODUCTION_OPERATOR".equals(x.get("authenticatedRole")) && !revoked.contains(x.get("recordId")) && Instant.parse(String.valueOf(x.get("expiresAt"))).isAfter(Instant.now())).findFirst();
          if(accepted.isPresent()) {disposition="PRODUCTION_RISK_ACKNOWLEDGED";entry.put("governanceRecordId",accepted.get().get("recordId"));}
        }
        if("UNRESOLVED".equals(disposition)) {
          if("BLOCKER".equals(severity)) remainingBlockers++;
          if("CRITICAL".equals(severity)) remainingCriticals++;
        }
        entry.put("disposition",disposition);ledger.add(entry);
      }
      if(actualBlockers!=blockerCount || actualCriticals!=criticalCount) return Map.of();
      boolean evidenceComplete=rows(report.get("unknownRules")).isEmpty() && rows(report.get("serviceErrors")).isEmpty();
      boolean scoreEligible=report.get("overallScore") instanceof Number score && score.doubleValue()>=92;
      boolean textAccepted=validEvent("GOVERNANCE_TEXT_ACCEPTANCE",ctx).isPresent();
      var f8=map(map(map(ctx.get("analysis")).get("family8")).get("renderAuthorization"));
      var reasons=rows(f8.get("reasons"));
      var workflow=map(ctx.get("analysis"));var bound=map(workflow.get("boundRequest"));
      boolean referenceReady=rows(bound.get("references")).stream().anyMatch(r->"VERIFIED".equals(r.get("status")) && String.valueOf(r.getOrDefault("sha256","")).matches("[a-f0-9]{64}"));
      boolean frameReady=Boolean.TRUE.equals(bound.get("acceptedStartFrame"));
      boolean supported="SUPPORTED".equals(map(workflow.get("generation")).get("capabilityStatus"));
      // FINAL_VIDEO_INTEGRITY is independently enforced by ValidationEvidenceService
      // and the queue (visual gates, independent identity, expiry). Requiring that
      // derived status here as well would create a circular admission dependency.
      boolean noOtherReasons=reasons.stream().allMatch(r->"FINAL_VIDEO_INTEGRITY".equals(r.get("source")));
      boolean independentF8Ready=referenceReady && frameReady && supported && noOtherReasons
          && !"BLOCKED_TECHNICAL_FAILURE".equals(f8.get("status"));
      var proof=new LinkedHashMap<String,Object>();proof.put("policyVersion",POLICY);proof.put("validationRecordId",validationId);
      proof.put("promptSha256",promptHash);proof.put("rulesetVersion",ruleset);proof.put("analysisId",ctx.get("analysisId"));
      proof.put("originalBlockerCount",blockerCount);proof.put("originalCriticalCount",criticalCount);
      proof.put("remainingBlockerCount",remainingBlockers);proof.put("remainingCriticalCount",remainingCriticals);
      proof.put("canonicalFailures",ledger);proof.put("evidenceComplete",evidenceComplete);proof.put("scoreEligible",scoreEligible);
      proof.put("textAccepted",textAccepted);proof.put("independentF8Ready",independentF8Ready);
      proof.put("eligible",evidenceComplete && scoreEligible && textAccepted && independentF8Ready && remainingBlockers==0 && remainingCriticals==0);
      return proof;
    } catch(RuntimeException unavailable) {return Map.of();}
  }
}
