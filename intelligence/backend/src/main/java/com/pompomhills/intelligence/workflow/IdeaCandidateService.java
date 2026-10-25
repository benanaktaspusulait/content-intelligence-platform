package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

/** Native IDEA lineage. Receipts survive a failed all-or-nothing materialization transaction. */
@Service
public class IdeaCandidateService {
  private final JdbcClient jdbc;
  private final ObjectMapper json;
  private final IdeaDraftService drafts;
  private final PlatformTransactionManager transactions;
  private final com.pompomhills.intelligence.quality.QualityMlClient evaluator;

  public IdeaCandidateService(
      JdbcClient jdbc,
      ObjectMapper json,
      @org.springframework.context.annotation.Lazy IdeaDraftService drafts,
      PlatformTransactionManager transactions,
      com.pompomhills.intelligence.quality.QualityMlClient evaluator) {
    this.jdbc = jdbc;
    this.json = json;
    this.drafts = drafts;
    this.transactions = transactions;
    this.evaluator = evaluator;
  }

  private <T> T atomic(java.util.function.Supplier<T> work) {
    var tx = new TransactionTemplate(transactions);
    tx.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    return tx.execute(s -> work.get());
  }

  private void lock(String identity) {
    jdbc.sql("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))")
        .param("key", "idea-batch:" + identity)
        .query((rs, n) -> rs.getObject(1))
        .list();
  }

  @SuppressWarnings("unchecked")
  static Map<String, Object> map(Object o) {
    return o instanceof Map<?, ?> ? (Map<String, Object>) o : Map.of();
  }

  static String text(Map<String, Object> m, String k) {
    return Objects.toString(m.get(k), "");
  }

  private Map<String, Object> read(String raw) {
    try {
      return json.readValue(raw, new TypeReference<>() {});
    } catch (Exception e) {
      throw new IllegalStateException("Invalid saved IDEA event", e);
    }
  }

  private String encode(Object o) {
    try {
      return json.writeValueAsString(o);
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid IDEA payload", e);
    }
  }

  private Optional<Map<String, Object>> event(String kind, String binding) {
    return jdbc.sql(
            "SELECT payload::text FROM post_family_workflow_events WHERE kind=:kind AND binding_sha256=:binding ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("kind", kind)
        .param("binding", binding)
        .query(String.class)
        .optional()
        .map(this::read);
  }

  private Map<String, Object> append(String kind, String binding, Map<String, Object> body) {
    var value = new LinkedHashMap<>(body);
    UUID id = UUID.randomUUID();
    value.put("recordId", id.toString());
    value.putIfAbsent("createdAt", Instant.now().toString());
    jdbc.sql(
            "INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES(:id,:kind,:binding,CAST(:payload AS jsonb))")
        .param("id", id)
        .param("kind", kind)
        .param("binding", binding)
        .param("payload", encode(value))
        .update();
    return value;
  }

  public void validateSource(Map<String, Object> request) {
    var context = map(request.get("context"));
    var draft =
        drafts.get(
            UUID.fromString(text(context, "sourceIdeaDraftId")), text(context, "workspacePath"));
    if (!"IDEA".equals(map(draft.get("state")).get("inputMode"))
        || !"IDEA".equals(draft.get("checkpoint")))
      throw new IllegalArgumentException("An IDEA stage draft is required");
    if (!Objects.equals(draft.get("revision"), context.get("sourceIdeaRevision")))
      throw new IllegalStateException("Reopen the current IDEA draft revision before generation");
    if (!IdeaDraftService.sourceText(map(draft.get("state")))
        .trim()
        .equals(text(request, "text").trim()))
      throw new IllegalArgumentException("Save the exact IDEA brief before generation");
    Object count = context.getOrDefault("requestedAlternativeCount", 1);
    if (!(count instanceof Number n)
        || n.intValue() != n.doubleValue()
        || n.intValue() < 1
        || n.intValue() > 3) throw new IllegalArgumentException("IDEA count must be 1 to 3");
  }

  /** Returns false on every replay, including an interrupted/unknown dispatch. */
  public boolean reserve(String key, Map<String, Object> request) {
    return atomic(
        () -> {
          lock(key);
          if (event("IDEA_REQUEST", key).isPresent()) return false;
          append(
              "IDEA_REQUEST",
              key,
              Map.of(
                  "requestId",
                  key,
                  "sourceRequest",
                  request,
                  "status",
                  "PROVIDER_OUTCOME_UNKNOWN"));
          return true;
        });
  }

  public Map<String, Object> receipt(String key, Map<String, Object> response) {
    return atomic(
        () -> {
          lock(key);
          return event("IDEA_RECEIPT", key)
              .orElseGet(
                  () ->
                      append("IDEA_RECEIPT", key, Map.of("requestId", key, "response", response)));
        });
  }

  public List<Map<String, Object>> batches(UUID draft, String workspace) {
    drafts.get(draft, workspace);
    return jdbc.sql(
            "SELECT payload::text FROM post_family_workflow_events WHERE kind='IDEA_REQUEST' AND payload->'sourceRequest'->'context'->>'sourceIdeaDraftId'=:draft ORDER BY created_at,id")
        .param("draft", draft.toString())
        .query(
            (rs, n) -> {
              var request = read(rs.getString(1));
              String key = text(request, "requestId");
              var receipt = event("IDEA_RECEIPT", key);
              long count =
                  jdbc.sql(
                          "SELECT count(*) FROM post_family_workflow_events WHERE kind='IDEA_CANDIDATE' AND payload->>'requestId'=:key")
                      .param("key", key)
                      .query(Long.class)
                      .single();
              var row = new LinkedHashMap<String, Object>();
              row.put("requestId", key);
              row.put("candidateCount", count);
              row.put("recoverable", receipt.isPresent());
              row.put("status", receipt.isPresent() ? "RECEIPT_SAVED" : "PROVIDER_OUTCOME_UNKNOWN");
              if (receipt.isPresent()) {
                row.put("receiptId", receipt.get().get("recordId"));
                try {
                  int expected =
                      ((Number)
                              map(map(request.get("sourceRequest")).get("context"))
                                  .getOrDefault("requestedAlternativeCount", 1))
                          .intValue();
                  payloads(map(receipt.get().get("response")), expected);
                  row.put(
                      "status", count == expected ? "PERSISTED" : "PERSISTENCE_RECOVERY_REQUIRED");
                  row.put("recoverable", count != expected);
                } catch (RuntimeException e) {
                  row.put("status", "PROVIDER_RESULT_REJECTED");
                  row.put("recoverable", false);
                  row.put("error", e.getMessage());
                }
              }
              return (Map<String, Object>) row;
            })
        .list();
  }

  public Map<String, Object> recoverForDraft(UUID draft, Map<String, Object> request) {
    drafts.get(draft, text(request, "workspacePath"));
    String key = text(request, "requestId");
    var source = map(event("IDEA_REQUEST", key).orElseThrow().get("sourceRequest"));
    if (!draft.toString().equals(text(map(source.get("context")), "sourceIdeaDraftId")))
      throw new IllegalArgumentException("Request belongs to another draft");
    return recover(key);
  }

  public Map<String, Object> recover(String key) {
    var receipt =
        event("IDEA_RECEIPT", key)
            .orElseThrow(
                () ->
                    new IllegalStateException(
                        "IDEA dispatch outcome unknown. Do not regenerate; reconcile the original request "
                            + key));
    var reservation = event("IDEA_REQUEST", key).orElseThrow();
    var result = materialize(key, map(reservation.get("sourceRequest")), receipt);
    result.put("calls", 0);
    result.put("reused", true);
    return result;
  }

  private List<Map<String, Object>> payloads(Map<String, Object> response, int count) {
    if (!"IDEA".equals(response.get("role"))
        || List.of("PROVIDER_RESULT_REJECTED", "PROVIDER_OUTCOME_UNKNOWN")
            .contains(text(response, "attemptState")))
      throw new IllegalStateException(
          "Original IDEA response rejected; receipt preserved. Inspect receipt; no provider retry.");
    var result = map(response.get("result"));
    Object raw =
        count == 1 && !result.containsKey("candidates")
            ? List.of(result)
            : result.get("candidates");
    if (!(raw instanceof List<?> list) || list.size() != count)
      throw new IllegalStateException(
          "Incomplete IDEA batch; original receipt preserved. Recover persistence without regenerating.");
    var candidates = new ArrayList<Map<String, Object>>();
    for (Object value : list) {
      var p = map(value);
      for (String field :
          List.of(
              "title",
              "concept",
              "firstStaticFrame",
              "viewerQuestion",
              "discovery",
              "payoff",
              "productionRisk"))
        if (!(p.get(field) instanceof String s) || s.isBlank())
          throw new IllegalStateException(
              "Malformed IDEA candidate: " + field + "; original receipt preserved, no retry.");
      if (count > 1)
        for (String field :
            List.of("everydayGoal", "frameZeroProblem", "impossibleRule", "proposedProgression")) {
          if (!(p.get(field) instanceof String valueText) || valueText.isBlank())
            throw new IllegalStateException(
                "Incomplete IDEA batch field: "
                    + field
                    + "; original receipt preserved, no retry.");
        }
      candidates.add(p);
    }
    return candidates;
  }

  public Map<String, Object> materialize(
      String key, Map<String, Object> request, Map<String, Object> receipt) {
    try {
      return materializeAtomic(key, request, receipt);
    } catch (RuntimeException error) {
      throw new IllegalStateException(
          "IDEA batch not saved completely. Original receipt "
              + receipt.get("recordId")
              + " is preserved. Use Recover saved response for request "
              + key
              + "; never regenerate to repair persistence. "
              + error.getMessage(),
          error);
    }
  }

  private Map<String, Object> materializeAtomic(
      String key, Map<String, Object> request, Map<String, Object> receipt) {
    return atomic(
        () -> {
          lock(key);
          var response = map(receipt.get("response"));
          var context = map(request.get("context"));
          int count = ((Number) context.getOrDefault("requestedAlternativeCount", 1)).intValue();
          var payloads = payloads(response, count);
          String draft = text(context, "sourceIdeaDraftId");
          for (int i = 0; i < count; i++) {
            String binding =
                UUID.nameUUIDFromBytes(
                        (key + ":" + i).getBytes(java.nio.charset.StandardCharsets.UTF_8))
                    .toString();
            if (event("IDEA_CANDIDATE", binding).isPresent()) continue;
            String id =
                UUID.nameUUIDFromBytes(
                        ("idea:" + binding).getBytes(java.nio.charset.StandardCharsets.UTF_8))
                    .toString();
            var candidate = new LinkedHashMap<String, Object>();
            candidate.put("candidateId", id);
            candidate.put("draftId", draft);
            candidate.put("sourceIdeaRevision", context.get("sourceIdeaRevision"));
            candidate.put("requestId", key);
            candidate.put(
                "providerRequestId",
                map(response.get("providerResponseMetadata"))
                    .getOrDefault("requestId", context.getOrDefault("attemptId", key)));
            candidate.put("receiptId", receipt.get("recordId"));
            candidate.put("candidateIndex", i);
            candidate.put("payload", payloads.get(i));
            candidate.put("revision", 1);
            candidate.put("state", "UNDECIDED");
            candidate = new LinkedHashMap<>(append("IDEA_CANDIDATE", binding, candidate));
            append("IDEA_EVALUATION", id, evaluate(candidate, payloads, context));
          }
          var result = new LinkedHashMap<>(response);
          result.put("recordId", receipt.get("recordId"));
          result.put("requestId", key);
          result.put(
              "ideaCandidates", list(UUID.fromString(draft), text(context, "workspacePath")));
          result.put("batchStatus", "PERSISTED");
          return result;
        });
  }

  /** Read immutable original fields/context; never accept evaluator evidence from the browser. */
  private Map<String, Object> evaluate(
      Map<String, Object> candidate, List<Map<String, Object>> batch, Map<String, Object> context) {
    var result =
        new LinkedHashMap<>(
            evaluator.workflow(
                "idea-evaluation",
                Map.of("candidate", candidate, "batch", batch, "context", context)));
    try {
      String hash =
          HexFormat.of()
              .formatHex(
                  java.security.MessageDigest.getInstance("SHA-256")
                      .digest(
                          json.writer()
                              .with(
                                  com.fasterxml.jackson.databind.SerializationFeature
                                      .ORDER_MAP_ENTRIES_BY_KEYS)
                              .writeValueAsBytes(candidate.get("payload"))));
      if (!Objects.equals(candidate.get("candidateId"), result.get("candidateId"))
          || !hash.equals(result.get("sourcePayloadSha256")))
        throw new IllegalStateException(
            "IDEA evaluation source binding mismatch; prior evaluation preserved");
      if (!(result.get("gates") instanceof List<?> gates)
          || gates.size() != 10
          || gates.stream()
                  .map(IdeaCandidateService::map)
                  .map(g -> g.get("gate"))
                  .distinct()
                  .count()
              != 10)
        throw new IllegalStateException(
            "IDEA evaluator must return ten distinct source-bound gate results");
      if (!(result.get("providerCalls") instanceof Number calls)
          || calls.doubleValue() != 0
          || !(result.get("additionalCostUsd") instanceof Number cost)
          || cost.doubleValue() != 0)
        throw new IllegalStateException("IDEA evaluation must be provider-free");
    } catch (java.security.NoSuchAlgorithmException
        | com.fasterxml.jackson.core.JsonProcessingException error) {
      throw new IllegalStateException("IDEA evaluation source identity unavailable", error);
    }
    result.putIfAbsent("revision", 1);
    return result;
  }

  static boolean gateSatisfied(Map<String, Object> gate) {
    return "PASS".equals(gate.get("status"))
        || ("NOT_APPLICABLE".equals(gate.get("status"))
            && Boolean.TRUE.equals(map(gate.get("applicability")).get("policyExcluded")));
  }

  public List<Map<String, Object>> list(UUID draft, String workspace) {
    drafts.get(draft, workspace);
    return jdbc.sql(
            "SELECT payload::text FROM post_family_workflow_events WHERE kind='IDEA_CANDIDATE' AND payload->>'draftId'=:draft ORDER BY created_at,(payload->>'candidateIndex')::int,id")
        .param("draft", draft.toString())
        .query(
            (rs, n) -> {
              var c = new LinkedHashMap<>(read(rs.getString(1)));
              String id = text(c, "candidateId");
              c.put(
                  "evaluation",
                  event("IDEA_EVALUATION", id)
                      .orElse(Map.of("status", "NOT_EVALUATED", "eligible", false)));
              event("IDEA_DECISION", id)
                  .ifPresent(
                      d -> {
                        c.put("state", d.get("state"));
                        c.put("decisionRevision", d.get("revision"));
                      });
              event("IDEA_SEMANTIC_REVIEW", id)
                  .ifPresent(
                      r -> {
                        var review = new LinkedHashMap<>(r);
                        review.put(
                            "stale",
                            !Objects.equals(
                                r.get("sourcePayloadSha256"), digest(c.get("payload"))));
                        c.put("semanticReview", review);
                      });
              if (reviewFixturesEnabled)
                event("IDEA_REVIEW_FIXTURE", id).ifPresent(r -> c.put("fixtureSemanticReview", r));
              return (Map<String, Object>) c;
            })
        .list();
  }

  public Map<String, Object> decide(UUID draft, UUID candidate, Map<String, Object> request) {
    return atomic(
        () -> {
          lock("draft:" + draft);
          var candidates = list(draft, text(request, "workspacePath"));
          var c =
              candidates.stream()
                  .filter(x -> candidate.toString().equals(x.get("candidateId")))
                  .findFirst()
                  .orElseThrow(
                      () -> new IllegalArgumentException("IDEA candidate not found in this draft"));
          String state = text(request, "state");
          if (!List.of("SELECTED", "REJECTED").contains(state))
            throw new IllegalArgumentException("Select or reject an IDEA candidate");
          if (state.equals("SELECTED")
              && !Objects.equals(
                  c.get("sourceIdeaRevision"),
                  drafts.get(draft, text(request, "workspacePath")).get("revision")))
            throw new IllegalStateException(
                "IDEA source revision changed; reopen the current draft before selection");
          if (state.equals("SELECTED")
              && (!Boolean.TRUE.equals(map(c.get("evaluation")).get("eligible"))
                  || !"EVALUATED".equals(map(c.get("evaluation")).get("status"))
                  || ((List<?>) map(c.get("evaluation")).getOrDefault("gates", List.of())).isEmpty()
                  || ((List<?>) map(c.get("evaluation")).get("gates"))
                      .stream()
                          .map(IdeaCandidateService::map)
                          .anyMatch(
                              g -> Boolean.TRUE.equals(g.get("mandatory")) && !gateSatisfied(g))))
            throw new IllegalStateException(
                "NO_IDEA_APPROVED: mandatory IDEA evidence is unresolved");
          int revision = ((Number) c.getOrDefault("decisionRevision", 0)).intValue();
          if (state.equals(c.get("state"))) return c;
          if (!Objects.equals(request.get("expectedRevision"), revision))
            throw new IllegalStateException("Candidate changed; reload before deciding");
          if (state.equals("SELECTED"))
            for (var other : candidates)
              if ("SELECTED".equals(other.get("state")))
                append(
                    "IDEA_DECISION",
                    text(other, "candidateId"),
                    Map.of(
                        "state",
                        "UNDECIDED",
                        "revision",
                        ((Number) other.getOrDefault("decisionRevision", 0)).intValue() + 1));
          append(
              "IDEA_DECISION",
              candidate.toString(),
              Map.of(
                  "candidateId", candidate.toString(), "state", state, "revision", revision + 1));
          return list(draft, text(request, "workspacePath")).stream()
              .filter(x -> candidate.toString().equals(x.get("candidateId")))
              .findFirst()
              .orElseThrow();
        });
  }

  public Map<String, Object> reevaluate(UUID draft, UUID candidate, Map<String, Object> request) {
    return atomic(
        () -> {
          lock("draft:" + draft);
          var all = list(draft, text(request, "workspacePath"));
          var c =
              all.stream()
                  .filter(x -> candidate.toString().equals(x.get("candidateId")))
                  .findFirst()
                  .orElseThrow();
          var evaluation =
              new LinkedHashMap<>(
                  evaluate(
                      c,
                      all.stream()
                          .filter(x -> x.get("requestId").equals(c.get("requestId")))
                          .map(x -> map(x.get("payload")))
                          .toList(),
                      map(
                          map(event("IDEA_REQUEST", text(c, "requestId"))
                                  .orElseThrow()
                                  .get("sourceRequest"))
                              .get("context"))));
          evaluation.put(
              "revision",
              ((Number) map(c.get("evaluation")).getOrDefault("revision", 0)).intValue() + 1);
          var saved = append("IDEA_EVALUATION", candidate.toString(), evaluation);
          if ("SELECTED".equals(c.get("state")))
            append(
                "IDEA_DECISION",
                candidate.toString(),
                Map.of(
                    "state",
                    "UNDECIDED",
                    "revision",
                    ((Number) c.getOrDefault("decisionRevision", 0)).intValue() + 1));
          return saved;
        });
  }

  @org.springframework.beans.factory.annotation.Value(
      "${workflow.idea-review-fixtures-enabled:false}")
  private boolean reviewFixturesEnabled;

  private String digest(Object value) {
    try {
      return HexFormat.of()
          .formatHex(
              java.security.MessageDigest.getInstance("SHA-256")
                  .digest(
                      json.writer()
                          .with(
                              com.fasterxml.jackson.databind.SerializationFeature
                                  .ORDER_MAP_ENTRIES_BY_KEYS)
                          .writeValueAsBytes(value)));
    } catch (Exception e) {
      throw new IllegalStateException("Cannot bind IDEA source", e);
    }
  }

  private List<Map<String, Object>> reviewSources(UUID draft, String workspace) {
    var saved = drafts.get(draft, workspace);
    if (!"IDEA".equals(saved.get("checkpoint")))
      throw new IllegalStateException("IDEA checkpoint required");
    var all = list(draft, workspace);
    if (all.size() != 3)
      throw new IllegalStateException("Exactly three existing IDEA candidates required");
    return all.stream()
        .map(
            c -> {
              if (!Objects.equals(c.get("sourceIdeaRevision"), saved.get("revision")))
                throw new IllegalStateException("Stale IDEA draft revision");
              return Map.<String, Object>of(
                  "candidateId",
                  c.get("candidateId"),
                  "payload",
                  c.get("payload"),
                  "sourcePayloadSha256",
                  digest(c.get("payload")),
                  "originalEvaluationRevision",
                  map(c.get("evaluation")).get("revision"));
            })
        .toList();
  }

  private Map<String, Object> reviewQuote(
      UUID draft, String workspace, List<Map<String, Object>> sources) {
    var first = list(draft, workspace).get(0);
    var original =
        map(
            map(event("IDEA_REQUEST", text(first, "requestId")).orElseThrow().get("sourceRequest"))
                .get("context"));
    var context =
        Map.<String, Object>of(
            "targetConfiguration",
            map(original.get("targetConfiguration")),
            "mainCharacter",
            Objects.toString(original.get("mainCharacter"), ""));
    var quote =
        new LinkedHashMap<>(
            evaluator.workflow(
                "idea-semantic-review",
                Map.of("action", "PREVIEW", "candidates", sources, "context", context)));
    if (!"gpt-6-sol".equals(quote.get("model"))
        || !"openai".equals(quote.get("provider"))
        || !Integer.valueOf(1).equals(quote.get("maximumProviderCalls")))
      throw new IllegalStateException("Unexpected reviewer capability");
    if (Boolean.TRUE.equals(quote.get("fixture")) && !reviewFixturesEnabled)
      throw new IllegalStateException("Fixture transport forbidden in production");
    quote.put(
        "quoteId", digest(Map.of("draftId", draft.toString(), "sources", sources, "quote", quote)));
    quote.put("context", context);
    return quote;
  }

  public Map<String, Object> semanticReviewPreview(UUID draft, Map<String, Object> request) {
    String workspace = text(request, "workspacePath");
    return reviewQuote(draft, workspace, reviewSources(draft, workspace));
  }

  public List<Map<String, Object>> semanticReviewHistory(UUID draft, String workspace) {
    drafts.get(draft, workspace);
    return jdbc.sql(
            "SELECT payload::text FROM post_family_workflow_events WHERE kind IN ('IDEA_SEMANTIC_REVIEW','IDEA_REVIEW_FIXTURE','IDEA_REVIEW_RECEIPT') AND payload->>'draftId'=:draft ORDER BY created_at,id")
        .param("draft", draft.toString())
        .query((rs, n) -> read(rs.getString(1)))
        .list();
  }

  @SuppressWarnings("unchecked")
  private List<Map<String, Object>> rows(Object value) {
    if (!(value instanceof List<?> list) || list.stream().anyMatch(x -> !(x instanceof Map)))
      throw new IllegalStateException("Malformed reviewer result");
    return (List<Map<String, Object>>) (List<?>) list;
  }

  private void validateReview(
      Map<String, Object> response, List<Map<String, Object>> sources, boolean fixture) {
    if (fixture) {
      if (!reviewFixturesEnabled
          || !"ISOLATED_FIXTURE".equals(response.get("provider"))
          || !Integer.valueOf(0).equals(response.get("calls"))
          || !Boolean.FALSE.equals(response.get("providerDispatched")))
        throw new IllegalStateException("Invalid isolated fixture receipt");
    } else if (!"gpt-6-sol".equals(response.get("model"))
        || !"gpt-6-sol".equals(response.get("returnedModel"))
        || !Integer.valueOf(1).equals(response.get("calls"))
        || !Boolean.TRUE.equals(response.get("providerDispatched"))) {
      throw new IllegalStateException("Reviewer receipt/model mismatch");
    }
    var value = map(response.get("result"));
    if (!"idea-semantic-review-v1".equals(value.get("policyVersion"))
        || !Objects.equals(response.get("model"), value.get("reviewerModel"))
        || !Objects.equals(value.get("reviewerModel"), value.get("reviewerVersion"))
        || text(response, "rawProviderResponse").isBlank())
      throw new IllegalStateException("Missing reviewer version/raw receipt");
    var reviews = rows(value.get("candidateReviews"));
    if (reviews.size() != 3
        || reviews.stream().map(r -> r.get("candidateId")).distinct().count() != 3)
      throw new IllegalStateException("Three independent results required");
    var dimensions =
        Map.ofEntries(
            Map.entry("EVERYDAY_GOAL", "GOAL_001"),
            Map.entry("IMMEDIATE_CONFLICT", "HOOK_004"),
            Map.entry("TEXTUAL_OPENING_CAUSALITY", "HOOK_004"),
            Map.entry("SINGLE_RULE", "CONCEPT_007"),
            Map.entry("RULE_CONSISTENCY", "CONCEPT_007"),
            Map.entry("CHARACTER_MOTIVATION", "GOAL_001"),
            Map.entry("CAUSAL_PROGRESSION", "PROGRESSION_006"),
            Map.entry("POTENTIAL_VISUAL_BEATS", "PROGRESSION_006"),
            Map.entry("PAYOFF_SALIENCE", "PAYOFF_004"),
            Map.entry("REPLAY_POTENTIAL", "PAYOFF_006"),
            Map.entry("ORIGINALITY_RISK", "ENGINE_SILHOUETTE_DUPLICATE"),
            Map.entry("PRODUCTION_FEASIBILITY", "PRODUCIBILITY_003"));
    for (var review : reviews) {
      var source =
          sources.stream()
              .filter(c -> Objects.equals(c.get("candidateId"), review.get("candidateId")))
              .findFirst()
              .orElseThrow();
      if (!Objects.equals(source.get("sourcePayloadSha256"), review.get("sourcePayloadSha256"))
          || !Objects.equals(
              source.get("originalEvaluationRevision"), review.get("originalEvaluationRevision")))
        throw new IllegalStateException("Stale reviewer source hash/revision");
      var judgments = rows(review.get("judgments"));
      if (judgments.size() != 12
          || !new HashSet<>(judgments.stream().map(j -> text(j, "dimension")).toList())
              .equals(dimensions.keySet()))
        throw new IllegalStateException("Incomplete semantic dimensions");
      for (var j : judgments) {
        if (!Objects.equals(dimensions.get(text(j, "dimension")), j.get("ruleId"))
            || !Set.of(
                    "SEMANTIC_PASS",
                    "SEMANTIC_FAIL",
                    "SEMANTIC_UNKNOWN",
                    "VISUAL_EVIDENCE_REQUIRED",
                    "LATER_STAGE_EVIDENCE")
                .contains(text(j, "verdict"))
            || text(j, "reason").isBlank())
          throw new IllegalStateException("Invalid semantic judgment");
        if (!(j.get("confidence") instanceof Number confidence)
            || !Double.isFinite(confidence.doubleValue())
            || confidence.doubleValue() < 0
            || confidence.doubleValue() > 1)
          throw new IllegalStateException("Missing judgment uncertainty");
        var quotes = rows(j.get("evidence"));
        if (Set.of("SEMANTIC_PASS", "SEMANTIC_FAIL").contains(text(j, "verdict"))
            && quotes.isEmpty()) throw new IllegalStateException("Ungrounded semantic verdict");
        for (var q : quotes) {
          Object field = map(source.get("payload")).get(text(q, "field"));
          if ((q.containsKey("candidateId")
                  && !Objects.equals(q.get("candidateId"), source.get("candidateId")))
              || !(field instanceof String raw)
              || text(q, "quote").isBlank()
              || !raw.contains(text(q, "quote")))
            throw new IllegalStateException("Unsupported source quotation");
        }
      }
    }
  }

  public Map<String, Object> semanticReview(UUID draft, Map<String, Object> request) {
    String workspace = text(request, "workspacePath");
    // Reject before even preparing transport when explicit consent is absent.
    if (!Boolean.TRUE.equals(request.get("ownerAuthorized"))
        || !(request.get("maxCostUsd") instanceof Number budget)
        || !Double.isFinite(budget.doubleValue())
        || budget.doubleValue() <= 0
        || !"gpt-6-sol".equals(request.get("model"))
        || !Integer.valueOf(1).equals(request.get("maximumProviderCalls")))
      throw new IllegalArgumentException(
          "Explicit owner authorization, disclosed model, positive budget and one call required");
    var reservation =
        atomic(
            () -> {
              lock("draft:" + draft);
              var sources = reviewSources(draft, workspace);
              var quote = reviewQuote(draft, workspace, sources);
              if (!Objects.equals(request.get("quoteId"), quote.get("quoteId")))
                throw new IllegalStateException(
                    "Stale IDEA source hash/revision or quote; preview again");
              if (budget.doubleValue()
                  < ((Number) quote.get("estimatedUpperBoundUsd")).doubleValue())
                throw new IllegalArgumentException("Budget below displayed maximum estimate");
              String key = text(quote, "quoteId");
              if (event("IDEA_REVIEW_REQUEST", key).isPresent())
                throw new IllegalStateException(
                    "This review was already attempted; no retry. Inspect saved receipt/history.");
              append(
                  "IDEA_REVIEW_REQUEST",
                  key,
                  Map.of(
                      "draftId",
                      draft.toString(),
                      "sources",
                      sources,
                      "quote",
                      quote,
                      "maxCostUsd",
                      budget,
                      "ownerAuthorized",
                      true,
                      "status",
                      "RESERVED_NO_RETRY"));
              return Map.<String, Object>of("sources", sources, "quote", quote);
            });
    var quote = map(reservation.get("quote"));
    Map<String, Object> response;
    try {
      response =
          evaluator.workflow(
              "idea-semantic-review",
              Map.of(
                  "action",
                  "REVIEW",
                  "candidates",
                  reservation.get("sources"),
                  "context",
                  quote.get("context"),
                  "ownerAuthorized",
                  true,
                  "maxCostUsd",
                  budget,
                  "maximumProviderCalls",
                  1,
                  "model",
                  "gpt-6-sol"));
    } catch (Exception error) {
      return atomic(
          () ->
              append(
                  "IDEA_REVIEW_RECEIPT",
                  text(quote, "quoteId"),
                  Map.of(
                      "draftId",
                      draft.toString(),
                      "status",
                      "TRANSPORT_OUTCOME_UNKNOWN",
                      "retrySafe",
                      false,
                      "error",
                      "Transport failed; do not retry automatically")));
    }
    var receipt =
        atomic(
            () ->
                append(
                    "IDEA_REVIEW_RECEIPT",
                    text(quote, "quoteId"),
                    Map.of(
                        "draftId",
                        draft.toString(),
                        "response",
                        response,
                        "status",
                        "RECEIVED_NOT_YET_VALIDATED",
                        "retrySafe",
                        false)));
    try {
      return atomic(
          () -> {
            lock("draft:" + draft);
            var current = reviewSources(draft, workspace);
            if (!digest(current).equals(digest(reservation.get("sources"))))
              throw new IllegalStateException("Source/evaluation changed while review was running");
            boolean fixture = Boolean.TRUE.equals(quote.get("fixture"));
            validateReview(response, current, fixture);
            var saved = new ArrayList<Map<String, Object>>();
            for (var review : rows(map(response.get("result")).get("candidateReviews"))) {
              var record = new LinkedHashMap<>(review);
              record.putAll(
                  Map.of(
                      "draftId",
                      draft.toString(),
                      "receiptId",
                      receipt.get("recordId"),
                      "fixture",
                      fixture,
                      "reviewerModel",
                      response.get("model"),
                      "reviewerVersion",
                      map(response.get("result")).get("reviewerVersion"),
                      "policyVersion",
                      "idea-semantic-review-v1"));
              for (var j : rows(record.get("judgments")))
                j.put("receiptId", receipt.get("recordId"));
              saved.add(
                  append(
                      fixture ? "IDEA_REVIEW_FIXTURE" : "IDEA_SEMANTIC_REVIEW",
                      text(review, "candidateId"),
                      record));
              if (!fixture) applySemanticReview(draft, workspace, record);
            }
            return Map.<String, Object>of(
                "status",
                fixture ? "ISOLATED_FIXTURE_ONLY" : "COMPLETED",
                "fixture",
                fixture,
                "receiptId",
                receipt.get("recordId"),
                "candidateReviews",
                saved,
                "providerCalls",
                response.get("calls"));
          });
    } catch (Exception invalid) {
      return Map.of(
          "status",
          "REVIEW_REJECTED",
          "receiptId",
          receipt.get("recordId"),
          "error",
          Objects.toString(invalid.getMessage(), "Invalid review"),
          "retrySafe",
          false);
    }
  }

  private void applySemanticReview(UUID draft, String workspace, Map<String, Object> review) {
    var candidate =
        list(draft, workspace).stream()
            .filter(c -> Objects.equals(c.get("candidateId"), review.get("candidateId")))
            .findFirst()
            .orElseThrow();
    var evaluation = new LinkedHashMap<>(map(candidate.get("evaluation")));
    // Reparse to avoid modifying any historical object; no original field/decision is written.
    evaluation = new LinkedHashMap<>(read(encode(evaluation)));
    for (var gate : rows(evaluation.get("gates"))) {
      if ("NOT_APPLICABLE".equals(gate.get("status"))) continue;
      var judgments =
          rows(review.get("judgments")).stream()
              .filter(j -> Objects.equals(j.get("ruleId"), gate.get("policy")))
              .toList();
      boolean visual =
          Set.of(
                  "FRAME_ZERO_CAUSAL_LEGIBILITY",
                  "PRODUCTION_FEASIBILITY",
                  "ORIGINALITY_DUPLICATE_ENGINE")
              .contains(text(gate, "gate"));
      if (judgments.stream().anyMatch(j -> "SEMANTIC_FAIL".equals(j.get("verdict"))))
        gate.put("status", "FAIL");
      else if (!visual
          && !judgments.isEmpty()
          && judgments.stream().allMatch(j -> "SEMANTIC_PASS".equals(j.get("verdict"))))
        gate.put("status", "PASS");
      else gate.put("status", "UNKNOWN");
      gate.put("semanticJudgments", judgments);
      gate.put(
          "reasonCode",
          visual && !"FAIL".equals(gate.get("status"))
              ? "VISUAL_EVIDENCE_STILL_REQUIRED"
              : "SOURCE_BOUND_SEMANTIC_REVIEW");
      gate.put(
          "reason",
          visual
              ? "Independent text judgment attached; actual visual legibility, comparison or execution remains unverified. See semantic findings."
              : "Independent source-bound semantic judgment attached; see quotations and reasoning.");
    }
    var gates = rows(evaluation.get("gates"));
    boolean failed = gates.stream().anyMatch(g -> "FAIL".equals(g.get("status")));
    boolean eligible = gates.stream().allMatch(IdeaCandidateService::gateSatisfied);
    evaluation.put("revision", ((Number) evaluation.get("revision")).intValue() + 1);
    evaluation.put("status", failed ? "REJECTED" : eligible ? "EVALUATED" : "PENDING_EVIDENCE");
    evaluation.put("eligible", eligible);
    evaluation.put("semanticReceiptId", review.get("receiptId"));
    evaluation.put("semanticReviewPolicyVersion", "idea-semantic-review-v1");
    evaluation.put(
        "rejectionReasons",
        gates.stream()
            .filter(g -> "FAIL".equals(g.get("status")))
            .map(g -> g.get("semanticJudgments"))
            .toList());
    evaluation.put(
        "evidenceGaps",
        gates.stream()
            .filter(g -> "UNKNOWN".equals(g.get("status")))
            .map(g -> g.get("reason"))
            .toList());
    var summary = new LinkedHashMap<>(map(evaluation.get("summary")));
    var counts = new LinkedHashMap<String, Object>();
    for (String status : List.of("PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"))
      counts.put(status, gates.stream().filter(g -> status.equals(g.get("status"))).count());
    summary.put("creativeOutcomes", counts);
    evaluation.put("summary", summary);
    append("IDEA_EVALUATION", text(candidate, "candidateId"), evaluation);
  }
}
