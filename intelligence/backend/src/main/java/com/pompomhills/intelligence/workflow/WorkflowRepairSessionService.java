package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

/** Durable bounded operator repair sessions. A provider never validates or accepts its own patch. */
@Service
public class WorkflowRepairSessionService {
  private final JdbcClient jdbc;
  private final WorkflowService workflow;
  private final ContentWorkspaceController contents;
  private final ObjectMapper json = new ObjectMapper().findAndRegisterModules();
  public WorkflowRepairSessionService(JdbcClient jdbc, WorkflowService workflow, ContentWorkspaceController contents) {
    this.jdbc = jdbc; this.workflow = workflow; this.contents = contents;
  }

  public Map<String,Object> start(UUID reviewId, String key, int maxAttempts, double budget) {
    if (key == null || key.isBlank() || maxAttempts < 1 || maxAttempts > 2 || !Double.isFinite(budget) || budget <= 0 || budget > 20) throw new IllegalArgumentException("Explicit idempotency key, at most two attempts and bounded positive budget required");
    var review = workflow.getByKind(reviewId,"REVIEW");
    if (!(review.get("contentId") instanceof Number) || !(review.get("promptVersionId") instanceof Number)
        || !"impact-review-v1".equals(review.get("decisionPolicyVersion"))
        || Boolean.TRUE.equals(review.get("needsSavedPromptVersion"))) throw new IllegalArgumentException("Save and review the exact source version first");
    var previousSession = jdbc.sql("SELECT id FROM workflow_repair_sessions WHERE review_id=:review AND idempotency_key=:key").param("review", reviewId).param("key", key).query(UUID.class).optional();
    if (previousSession.isEmpty() && jdbc.sql("SELECT count(*) FROM post_family_workflow_events WHERE kind='REPAIR' AND payload->>'parentReviewId'=:review").param("review", reviewId.toString()).query(Long.class).single() > 0) throw new IllegalStateException("This source already has a repair; reopen its session or review a new saved source version");
    UUID id = UUID.randomUUID();
    var payload = new LinkedHashMap<String,Object>();
    payload.put("originalReviewId", reviewId.toString()); payload.put("originalPromptVersionId", review.get("promptVersionId")); payload.put("bestReviewId", reviewId.toString());
    payload.put("bestPromptVersionId", review.get("promptVersionId")); payload.put("contentId", review.get("contentId"));
    payload.put("bestScore", score(review)); payload.put("history", List.of()); payload.put("stopReason", "NOT_STARTED");
    jdbc.sql("INSERT INTO workflow_repair_sessions(id,review_id,idempotency_key,state,max_attempts,max_cost_usd,payload) VALUES (:id,:review,:key,'READY',:attempts,:budget,CAST(:payload AS jsonb)) ON CONFLICT(review_id,idempotency_key) DO NOTHING")
        .param("id", id).param("review", reviewId).param("key", key).param("attempts", maxAttempts).param("budget", budget).param("payload", write(payload)).update();
    UUID stored = jdbc.sql("SELECT id FROM workflow_repair_sessions WHERE review_id=:review AND idempotency_key=:key").param("review", reviewId).param("key", key).query(UUID.class).single();
    var session = get(stored);
    if (((Number) session.get("maxAttempts")).intValue() != maxAttempts || Double.compare(((Number) session.get("maxCostUsd")).doubleValue(), budget) != 0) throw new IllegalArgumentException("Replay must preserve original attempt and budget limits");
    return session;
  }

  public Map<String,Object> get(UUID id) {
    jdbc.sql("UPDATE workflow_repair_sessions SET state='STOPPED',payload=payload || '{\"stopReason\":\"PROVIDER_OUTCOME_UNKNOWN\"}'::jsonb WHERE id=:id AND state='RUNNING' AND updated_at<now()-interval '15 minutes'").param("id",id).update();
    return jdbc.sql("SELECT state,max_attempts,attempts,max_cost_usd,reserved_cost_usd,payload::text FROM workflow_repair_sessions WHERE id=:id")
        .param("id",id).query((rs, ignored) -> {
          var result = read(rs.getString("payload")); result.put("sessionId", id.toString()); result.put("state", rs.getString("state"));
          result.put("maxAttempts", rs.getInt("max_attempts")); result.put("attempts", rs.getInt("attempts"));
          result.put("maxCostUsd", rs.getDouble("max_cost_usd")); result.put("reservedCostUsd", rs.getDouble("reserved_cost_usd")); return result;
        }).optional().orElseThrow(() -> new IllegalArgumentException("Repair session not found"));
  }

  public Map<String,Object> step(UUID id) {
    if (jdbc.sql("UPDATE workflow_repair_sessions SET state='RUNNING',attempts=attempts+1,updated_at=now() WHERE id=:id AND state='READY' AND attempts<max_attempts RETURNING id").param("id",id).query(UUID.class).optional().isEmpty()) return get(id);
    var session = get(id);
    var best = workflow.get(UUID.fromString(String.valueOf(session.get("bestReviewId"))));
    var bound = map(best.get("boundRequest"));
    var history = new ArrayList<Map<String,Object>>(maps(session.get("history")));
    var attempt = new LinkedHashMap<String,Object>(); attempt.put("number",session.get("attempts")); attempt.put("sourceReviewId", best.get("recordId"));
    try {
      var actionable = maps(map(best.get("executionReview")).get("findings"));
      if (actionable.isEmpty() || actionable.stream().allMatch(finding -> "LOW".equals(finding.get("confidence")) && "GENERAL_HEURISTIC".equals(finding.get("evidenceBasis")))) {
        session.put("stopReason", "TOLERANT_ONLY_OR_EVIDENCE_NEEDED");
        attempt.put("providerCalls", 0); history.add(attempt); session.put("history", history);
        save(id, session, "STOPPED"); return get(id);
      }
      if (maps(bound.get("intentRequirements")).stream().anyMatch(requirement -> "ESSENTIAL".equals(requirement.get("level")) && !"SOURCE_SUPPORTED".equals(requirement.get("status")))) {
        // Intent declarations are verified by the source-bound review, not by the fixer.
        if (maps(best.get("intentRequirements")).stream().anyMatch(requirement -> "ESSENTIAL".equals(requirement.get("level")) && !"SOURCE_SUPPORTED".equals(requirement.get("status")))) throw new IllegalArgumentException("EVIDENCE_NEEDED");
      }
      double remaining = ((Number)session.get("maxCostUsd")).doubleValue() - ((Number)session.get("reservedCostUsd")).doubleValue();
      if (remaining <= 0) throw new IllegalArgumentException("COST_LIMIT");
      var proposal = workflow.creativeRole(Map.of("role","MINIMAL_REPAIR", "text",bound.get("prompt"), "context",Map.of("protectedIntent",bound.getOrDefault("protectedIntent",List.of()), "intentRequirements",best.getOrDefault("intentRequirements",List.of()), "findings", map(best.get("executionReview")).getOrDefault("findings",List.of()), "retrievedLessons",bound.getOrDefault("retrievedLessons",List.of())), "maxCostUsd",remaining));
      attempt.put("providerProposal",proposal);
      if (!"MINIMAL_REPAIR".equals(proposal.get("role")) || !"openai".equals(proposal.get("provider")) || !(proposal.get("model") instanceof String model) || model.isBlank()) throw new IllegalStateException("Configured repair role identity mismatch");
      double reserved = proposal.get("costUpperBoundUsd") instanceof Number cost ? cost.doubleValue() : remaining;
      jdbc.sql("UPDATE workflow_repair_sessions SET reserved_cost_usd=reserved_cost_usd+:cost WHERE id=:id").param("id",id).param("cost",reserved).update();
      if ("CANCELLED".equals(get(id).get("state"))) return get(id);
      var patches = maps(map(proposal.get("result")).get("patches"));
      if (patches.isEmpty()) throw new IllegalArgumentException("NO_PROPOSED_CHANGE");
      var repaired = workflow.repair(UUID.fromString(String.valueOf(best.get("recordId"))),patches);
      if (!(repaired.get("finalPrompt") instanceof String) || String.valueOf(repaired.get("finalPrompt")).isBlank()) throw new IllegalArgumentException("INVALID_REPAIR_RESULT");
      String finalText = String.valueOf(repaired.get("finalPrompt"));
      if (finalText.equals(bound.get("prompt"))) throw new IllegalArgumentException("NO_IMPROVEMENT");
      long content = ((Number)session.get("contentId")).longValue();
      var version = contents.createPrompt(content,new ContentWorkspaceController.CreatePromptRequest(finalText,"{}",((Number)session.get("bestPromptVersionId")).longValue()));
      attempt.put("promptVersionId", version.id()); attempt.put("stage", "VERSION_SAVED_REVALIDATION_PENDING");
      history.add(attempt); session.put("history", history); save(id, session, "RUNNING");
      var reviewed = workflow.runReview(new WorkflowService.ReviewRequest(content,version.id(),finalText,version.sourcePath(),bound),true);
      attempt.put("promptVersionId",version.id()); attempt.put("reviewId",reviewed.get("recordId")); attempt.put("diff",repaired.get("diff"));
      int nextScore = score(reviewed); attempt.put("score",nextScore);
      boolean improved = nextScore < ((Number)session.get("bestScore")).intValue();
      if (improved) {
        session.put("bestScore",nextScore); session.put("bestReviewId",reviewed.get("recordId")); session.put("bestPromptVersionId",version.id());
      }
      session.put("stopReason", improved ? nextScore == 0 ? "INDEPENDENT_REVIEW_CLEAR" : ((Number)session.get("attempts")).intValue() >= ((Number)session.get("maxAttempts")).intValue() ? "ATTEMPT_LIMIT" : "NEXT_ATTEMPT_AVAILABLE" : "NO_IMPROVEMENT");
      attempt.put("stage", "INDEPENDENTLY_REVIEWED"); session.put("history",history);
      save(id,session,improved && nextScore > 0 && ((Number)session.get("attempts")).intValue() < ((Number)session.get("maxAttempts")).intValue() ? "READY" : "STOPPED");
    } catch (RuntimeException error) {
      attempt.put("failureType", error.getClass().getSimpleName());
      org.slf4j.LoggerFactory.getLogger(getClass()).debug("Repair session stopped", error);
      attempt.put("failure","Provider/repair/independent verification failed; no automatic retry");
      attempt.put("costStatus", "UNKNOWN_RESERVED_CEILING");
      jdbc.sql("UPDATE workflow_repair_sessions SET reserved_cost_usd=max_cost_usd WHERE id=:id").param("id", id).update();
      if (!history.contains(attempt)) history.add(attempt);
      session.put("history",history); session.put("stopReason","FAILED_OR_OUTCOME_UNKNOWN");
      save(id,session,"STOPPED");
    }
    return get(id);
  }

  public Map<String,Object> decide(UUID id, String decision) {
    if (decision == null || !List.of("ACCEPTED","REJECTED","CANCELLED").contains(decision)) throw new IllegalArgumentException("Explicit accept, reject or cancel required");
    var session = get(id);
    if ("RUNNING".equals(session.get("state")) && !"CANCELLED".equals(decision)) throw new IllegalStateException("Cancel or await the active attempt");
    jdbc.sql("UPDATE workflow_repair_sessions SET state=:state,updated_at=now() WHERE id=:id AND state IN ('READY','RUNNING','STOPPED')").param("id",id).param("state",decision).update();
    return get(id);
  }

  private void save(UUID id,Map<String,Object> value,String state) {
    jdbc.sql("UPDATE workflow_repair_sessions SET payload=CAST(:payload AS jsonb),state=:state,updated_at=now() WHERE id=:id AND state='RUNNING'").param("id",id).param("payload",write(value)).param("state",state).update();
  }
  private static int score(Map<String,Object> review) {
    int result=maps(map(review.get("executionReview")).get("findings")).size();
    for (String key : List.of("planQuality","executionRisk")) {
      String status=String.valueOf(map(review.get(key)).get("status"));
      if ("FAIL".equals(status) || "BLOCK".equals(status)) result+=100;
      else if ("UNKNOWN".equals(status) || "null".equals(status)) result+=10;
    }
    return result;
  }
  @SuppressWarnings("unchecked") private static Map<String,Object> map(Object value) { return value instanceof Map<?,?> ? (Map<String,Object>)value : Map.of(); }
  @SuppressWarnings("unchecked") private static List<Map<String,Object>> maps(Object value) { return value instanceof List<?> ? (List<Map<String,Object>>)value : List.of(); }
  private String write(Object value) { try { return json.writeValueAsString(value); } catch(Exception e) { throw new IllegalArgumentException("Invalid session payload",e); } }
  @SuppressWarnings("unchecked") private Map<String,Object> read(String value) { try { return json.readValue(value,LinkedHashMap.class); } catch(Exception e) { throw new IllegalStateException("Invalid stored session",e); } }
}
