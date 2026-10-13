package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.quality.ValidationEvidenceService;
import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Append-only operational adapters over existing prompt, media and ML services. */
@Service
public class WorkflowService {
  private static final String BUILD_PROMPT_CONTRACT_VERSION = "openart-production-prompt-v2";
  @Value("${WORKFLOW_BUILD_PROMPT_MODEL:}") private String buildPromptModel;
  @Value("${pompom.data-root:/tmp/pompom-data}") private String workflowDataRoot;
  private final ContentPromptQueryService prompts;
  private final QualityMlClient ml;
  private final MediaContentService media;
  private final VideoService videos;
  private final ObjectMapper json;
  private final JdbcClient jdbc;
  private final MlVideoClient videoMl;
  @Autowired private ValidationEvidenceService authorization;
  @Autowired private com.pompomhills.intelligence.video.VideoVariantService variantService;

  @Autowired
  public WorkflowService(
      ContentPromptQueryService prompts,
      QualityMlClient ml,
      MediaContentService media,
      VideoService videos,
      JdbcClient jdbc,
      MlVideoClient videoMl) {
    this(prompts, ml, media, videos, new ObjectMapper().findAndRegisterModules(), jdbc, videoMl);
  }

  public WorkflowService(
      ContentPromptQueryService prompts,
      QualityMlClient ml,
      MediaContentService media,
      VideoService videos,
      ObjectMapper json,
      JdbcClient jdbc,
      MlVideoClient videoMl) {
    this.prompts = prompts;
    this.ml = ml;
    this.media = media;
    this.videos = videos;
    this.json = json;
    this.jdbc = jdbc;
    this.videoMl = videoMl;
  }

  public Map<String, Object> runReview(ReviewRequest request, boolean persist) {
    if (!"post-family-v1".equals(request.options().get("profile")))
      throw new IllegalArgumentException("Explicit post-family-v1 profile required");
    var input = new LinkedHashMap<String, Object>(request.options());
    // Resolve approved evidence again on every request; clients cannot inject revoked lessons.
    input.remove("retrievedLessons");
    if (input.get("lessonModelVersion") instanceof String model
        && input.get("desiredDuration") instanceof Number duration) {
      input.put(
          "retrievedLessons",
          retrieveLessons(
              String.valueOf(input.get("contentProfile")), model, duration.doubleValue(), input));
    }
    input.remove("authorizationEvidence");
    if (request.contentId() != null && request.promptVersionId() != null) {
      var snapshot = prompts.load(request.contentId(), request.promptVersionId());
      input.put("prompt", snapshot.promptText());
      input.put(
          "sourceId", "content:" + snapshot.contentId() + "/prompt:" + snapshot.promptVersionId());
      input.put("sourceVersion", String.valueOf(snapshot.promptVersionId()));
      if (jdbc != null && authorization != null) {
        Long latest =
            jdbc.sql(
                    "SELECT q.id FROM quality_validations q WHERE content_id=:content AND"
                        + " prompt_version_id=:prompt AND (:canonical IS NULL OR q.id=:canonical)"
                        + " ORDER BY EXISTS(SELECT 1 FROM quality_validation_visual_evidence ve"
                        + " WHERE ve.validation_record_id=q.id) DESC,q.id DESC LIMIT 1")
                .param("content", request.contentId())
                .param("prompt", request.promptVersionId())
                .param("canonical", input.get("canonicalValidationId"), java.sql.Types.BIGINT)
                .query(Long.class)
                .optional()
                .orElse(null);
        if (latest != null) {
          try {
            var facts = authorization.getEvidence(latest);
            var canonical = json.convertValue(facts, new TypeReference<Map<String, Object>>() {});
            canonical.put(
                "fresh", facts.expiresAt() != null && facts.expiresAt().isAfter(Instant.now()));
            canonical.put("deterministicRulesetVersion", facts.deterministicRulesetVersion());
            input.put("authorizationEvidence", canonical);
          } catch (RuntimeException incomplete) {
            input.put(
                "authorizationEvidence",
                Map.of("status", "UNKNOWN", "reason", "Canonical evidence incomplete"));
          }
        }
      }
    } else {
      if (request.prompt() == null || request.prompt().isBlank())
        throw new IllegalArgumentException("Prompt required");
      input.put("prompt", request.prompt());
      input.put("sourceId", "draft:" + request.sourcePath());
      input.put("sourceVersion", "DRAFT");
    }
    input.put("references", verifiedReferences(input.get("references")));
    // Pass accepted start-frame candidate to ML service so F8 can recognize it.
    if (request.contentId() != null && request.promptVersionId() != null) {
      input.put("acceptedStartFrame", hasAcceptedStartFrame(request.contentId(), request.promptVersionId()));
    }
    // Recommendation provenance belongs to the persisted workflow record, not to the
    // provider contract. Keep it in `boundRequest` while sending only schema-approved
    // fields to the ML service (its request model rejects unknown properties).
    var providerInput = new LinkedHashMap<String, Object>(input);
    providerInput.remove("contentProfileRecommendation");
    providerInput.remove("openingStrategyRecommendation");
    providerInput.remove("generatorRecommendation");
    var result = new LinkedHashMap<>(ml.workflow("review", providerInput));
    if (result.get("retrievedLessons") instanceof List<?> matchedLessons)
      input.put("retrievedLessons", matchedLessons);
    result.put("boundRequest", input);
    result.put("contentId", request.contentId());
    result.put("promptVersionId", request.promptVersionId());
    if (persist) {
      if (request.contentId() != null) {
        var previous =
            jdbc.sql(
                    "SELECT id,payload::text payload FROM post_family_workflow_events WHERE"
                        + " kind='REVIEW' AND payload->>'contentId'=:content ORDER BY created_at"
                        + " DESC LIMIT 1")
                .param("content", String.valueOf(request.contentId()))
                .query(
                    (rs, ignored) -> {
                      var row = read(rs.getString("payload"));
                      row.put("recordId", rs.getString("id"));
                      return row;
                    })
                .optional();
        if (previous.isPresent()
            && "impact-review-v1".equals(previous.get().get("decisionPolicyVersion"))
            && !essentialSignature(result).containsAll(essentialSignature(previous.get()))) {
          if (!(input.get("intentChangeReason") instanceof String reason) || reason.isBlank())
            throw new IllegalArgumentException(
                "Essential intent changed: explicit intentChangeReason required; historical review"
                    + " is preserved");
          result.put(
              "essentialIntentDecision",
              Map.of(
                  "previousReviewId",
                  previous.get().get("recordId"),
                  "reason",
                  reason,
                  "decision",
                  "EXPLICIT_NEW_SOURCE_REVIEW"));
        }
      }
      result.put("recordId", save("REVIEW", String.valueOf(result.get("bindingHash")), result));
    }
    return result;
  }

  @Transactional
  public Map<String, Object> generateCreativeOptimization(
      UUID analysisId, Map<String, Object> request, Map<String, Object> provenance) {
    if (!Boolean.TRUE.equals(request.get("operatorAuthorized")))
      throw new IllegalArgumentException("Explicit creative optimization authorization is required");
    if (!(request.get("maxCostUsd") instanceof Number budget)
        || !Double.isFinite(budget.doubleValue())
        || budget.doubleValue() <= 0
        || budget.doubleValue() > 20)
      throw new IllegalArgumentException("A positive budget no greater than $20 is required");

    var baseline = getByKind(analysisId, "REVIEW");
    if (!(baseline.get("contentId") instanceof Number content)
        || !(baseline.get("promptVersionId") instanceof Number version)
        || !String.valueOf(content.longValue()).equals(String.valueOf(request.get("contentId")))
        || !String.valueOf(version.longValue()).equals(String.valueOf(request.get("promptVersionId"))))
      throw new IllegalArgumentException("The analysis must match the selected content and prompt version");
    var latest =
        jdbc.sql(
                "SELECT id FROM post_family_workflow_events WHERE kind='REVIEW' AND"
                    + " payload->>'contentId'=:content ORDER BY created_at DESC,id DESC LIMIT 1")
            .param("content", String.valueOf(content.longValue()))
            .query(UUID.class)
            .optional()
            .orElseThrow(() -> new IllegalStateException("Current saved quality analysis is unavailable"));
    if (!analysisId.equals(latest))
      throw new IllegalStateException("Quality analysis is stale; reload Step 6 before optimizing");
    var source = prompts.load(content.longValue(), version.longValue());
    var bound = map(baseline.get("boundRequest"));
    var sourceEvidence = map(map(baseline.get("productionEvidence")).get("source"));
    if (!source.promptText().equals(bound.get("prompt"))
        || !sha256(source.promptText()).equals(String.valueOf(sourceEvidence.getOrDefault("sha256", ""))))
      throw new IllegalStateException("Saved prompt source no longer matches the selected analysis");
    if (String.valueOf(provenance.getOrDefault("approvedStoryText", "")).isBlank()
        || String.valueOf(provenance.getOrDefault("approvalRecordId", "")).isBlank())
      throw new IllegalStateException("Approved story provenance is unavailable for this prompt version");

    var beats = maps(map(bound.get("structuredPlan")).get("beats"));
    var essentialEvents = beats.stream()
        .map(beat -> String.valueOf(beat.getOrDefault("action", "")).trim())
        .filter(action -> !action.isBlank())
        .distinct()
        .toList();
    if (essentialEvents.isEmpty())
      throw new IllegalStateException("Source-bound essential event anchors are unavailable");
    var context = new LinkedHashMap<String, Object>();
    context.put("analysisRunId", analysisId.toString());
    context.put("contentId", content.longValue());
    context.put("promptVersionId", version.longValue());
    context.put("approvedStoryText", provenance.get("approvedStoryText"));
    context.put("storyRevisionId", provenance.get("storyRevisionId"));
    context.put("storyApprovalRecordId", provenance.get("approvalRecordId"));
    context.put("essentialEvents", essentialEvents);
    context.put("targetConfiguration", Map.of(
        "contentProfile", bound.getOrDefault("contentProfile", "UNKNOWN"),
        "generator", bound.getOrDefault("generator", "UNKNOWN"),
        "duration", bound.getOrDefault("desiredDuration", "UNKNOWN"),
        "settings", map(bound.get("settings"))));
    var roleRequest = new LinkedHashMap<String, Object>();
    roleRequest.put("role", "PROMPT_OPTIMIZATION");
    roleRequest.put("text", source.promptText());
    roleRequest.put("context", context);
    roleRequest.put("maxCostUsd", budget.doubleValue());
    roleRequest.put("generationAuthorized", true);
    var role = creativeRole(roleRequest, true);
    UUID roleRecordId = UUID.fromString(String.valueOf(role.get("recordId")));
    var previousComparison =
        jdbc.sql(
                "SELECT id,payload::text FROM post_family_workflow_events WHERE"
                    + " kind='CREATIVE_OPTIMIZATION' AND payload->>'roleRecordId'=:role"
                    + " ORDER BY created_at DESC,id DESC LIMIT 1")
            .param("role", roleRecordId.toString())
            .query((rs, ignored) -> {
              var value = read(rs.getString(2));
              value.put("recordId", rs.getString(1));
              return value;
            })
            .optional();
    if (previousComparison.isPresent()) return previousComparison.get();
    var generated = maps(map(role.get("result")).get("candidates"));
    if (generated.size() != 2)
      throw new IllegalStateException("The optimization role did not return exactly two candidates");

    var candidates = new ArrayList<Map<String, Object>>();
    String baselineRuleset = String.valueOf(map(baseline.get("canonicalRuleEvaluation")).get("rulesetVersion"));
    if (baselineRuleset.isBlank() || "null".equals(baselineRuleset))
      throw new IllegalStateException("Baseline canonical ruleset identity is unavailable");
    for (var candidate : generated) {
      String candidateId = String.valueOf(candidate.get("candidateId"));
      String text = String.valueOf(candidate.get("prompt"));
      var candidateReview = reviewCreativeCandidate(analysisId, candidateId, text, bound);
      String candidateRuleset =
          String.valueOf(map(candidateReview.get("canonicalRuleEvaluation")).get("rulesetVersion"));
      if (!baselineRuleset.equals(candidateRuleset))
        throw new IllegalStateException("Candidate review ruleset differs from baseline; comparison is unavailable");
      var summary = new LinkedHashMap<String, Object>(candidate);
      summary.put("review", candidateReview);
      summary.put("rulesetVersion", candidateRuleset);
      summary.put("fidelity", Map.of(
          "essentialEventsPreserved", true,
          "approvedStoryCoverage", "PROMPT_SOURCE_EVENTS_PRESERVED; APPROVED_STORY_SEMANTIC_FIDELITY_UNKNOWN",
          "storyRevisionId", provenance.getOrDefault("storyRevisionId", "UNKNOWN"),
          "endingPreservedBySourceEventAnchor", true));
      summary.put("productionRisks", Map.of(
          "localExecutionCritic", candidateReview.getOrDefault("executionReview", Map.of()),
          "productionComplexity", candidateReview.getOrDefault("planQuality", Map.of()),
          "generatorCapability", map(candidateReview.get("generation")).getOrDefault("capabilityStatus", "UNKNOWN"),
          "family8", map(candidateReview.get("family8")).getOrDefault("renderAuthorization", Map.of())));
      summary.put("unknowns", Map.of(
          "canonicalRules", map(candidateReview.get("canonicalRuleEvaluation")).getOrDefault("unknownRules", List.of()),
          "actualRenderQuality", candidateReview.getOrDefault("actualRenderQuality", Map.of()),
          "audienceOutcome", candidateReview.getOrDefault("audienceOutcome", Map.of())));
      summary.put("diff", lineDiff(source.promptText(), text, candidateId));
      candidates.add(summary);
    }
    var comparison = new LinkedHashMap<String, Object>();
    comparison.put("sourceAnalysisId", analysisId.toString());
    comparison.put("sourcePromptVersionId", version.longValue());
    comparison.put("sourcePromptSha256", sha256(source.promptText()));
    comparison.put("roleRecordId", roleRecordId.toString());
    comparison.put("rulesetVersion", baselineRuleset);
    comparison.put("candidates", candidates);
    comparison.put("selection", null);
    comparison.put("approval", null);
    comparison.put("recordId", save("CREATIVE_OPTIMIZATION", null, comparison));
    return comparison;
  }

  public Map<String, Object> latestCreativeOptimization(UUID analysisId) {
    getByKind(analysisId, "REVIEW");
    return jdbc.sql(
            "SELECT id,payload::text FROM post_family_workflow_events WHERE"
                + " kind='CREATIVE_OPTIMIZATION' AND payload->>'sourceAnalysisId'=:analysis"
                + " ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("analysis", analysisId.toString())
        .query((rs, ignored) -> {
          var value = read(rs.getString(2));
          value.put("recordId", rs.getString(1));
          return value;
        })
        .optional()
        .<Map<String, Object>>map(value -> Map.of("comparison", value))
        .orElseGet(() -> {
          var empty = new LinkedHashMap<String, Object>();
          empty.put("comparison", null);
          return empty;
        });
  }

  private Map<String, Object> reviewCreativeCandidate(
      UUID analysisId, String candidateId, String prompt, Map<String, Object> baselineRequest) {
    var sourcePlan =
        ml.workflow(
            "source-plan",
            Map.of(
                "prompt",
                prompt,
                "sourceId",
                "creative-optimization:" + analysisId + ":" + candidateId,
                "sourceVersion",
                "UNSAVED_CANDIDATE"));
    var planBeats = maps(map(sourcePlan.get("videoPlanIR")).get("beats"));
    var events = new ArrayList<Map<String, Object>>();
    for (var beat : planBeats) {
      String quote = String.valueOf(beat.getOrDefault("sourceQuote", ""));
      if (quote.isBlank()) continue;
      String action = String.valueOf(beat.getOrDefault("sourceAction", quote));
      if (!quote.contains(action)) action = quote;
      events.add(Map.of("sourceQuote", quote, "action", action));
    }
    var options = new LinkedHashMap<String, Object>();
    for (String key : List.of(
        "profile", "contentProfile", "openingStrategy", "desiredDuration",
        "plannedEditedDuration", "generator", "qualityJustification", "viewerQuestion",
        "settings", "references", "segments", "protectedIntent", "creativeEvidence",
        "intentChangeReason", "lessonModelVersion", "retrievedLessons", "canonicalValidationId")) {
      if (baselineRequest.containsKey(key)) options.put(key, baselineRequest.get(key));
    }
    options.put("structuredPlan", Map.of(
        "evidenceStatus", "DETERMINISTIC_SOURCE_EVENTS_ONLY",
        "sourceVersion", "UNSAVED_CANDIDATE",
        "events", events));
    options.put("acceptedStartFrame", false);
    options.put("authorizationEvidence", Map.of());
    return runReview(
        new ReviewRequest(
            null, null, prompt, "creative-optimization-" + candidateId, options),
        false);
  }

  private static String lineDiff(String original, String candidate, String id) {
    var before = original.lines().toList();
    var after = candidate.lines().toList();
    int[][] lcs = new int[before.size() + 1][after.size() + 1];
    for (int i = before.size() - 1; i >= 0; i--)
      for (int j = after.size() - 1; j >= 0; j--)
        lcs[i][j] =
            before.get(i).equals(after.get(j))
                ? lcs[i + 1][j + 1] + 1
                : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    var diff = new StringBuilder("--- original\n+++ ").append(id).append('\n');
    int i = 0, j = 0;
    while (i < before.size() || j < after.size()) {
      if (i < before.size() && j < after.size() && before.get(i).equals(after.get(j))) {
        diff.append(' ').append(before.get(i++)).append('\n');
        j++;
      } else if (i < before.size() && (j == after.size() || lcs[i + 1][j] >= lcs[i][j + 1])) {
        diff.append('-').append(before.get(i++)).append('\n');
      } else {
        diff.append('+').append(after.get(j++)).append('\n');
      }
    }
    return diff.toString();
  }

  static java.util.Set<String> essentialSignature(Map<String, Object> review) {
    var result = new java.util.TreeSet<String>();
    for (var requirement : maps(review.get("intentRequirements")))
      if ("ESSENTIAL".equals(requirement.get("level"))
          && "SOURCE_SUPPORTED".equals(requirement.get("status")))
        result.add(String.valueOf(requirement.get("sourceQuote")));
    return result;
  }

  public Map<String, Object> admission(UUID id, Map<String, Object> queued) {
    var stored = get(id);
    if (stored.get("contentId") == null
        || stored.get("promptVersionId") == null
        || !String.valueOf(stored.get("contentId")).equals(String.valueOf(queued.get("contentId")))
        || !String.valueOf(stored.get("promptVersionId"))
            .equals(String.valueOf(queued.get("promptVersionId"))))
      throw new IllegalStateException("Saved prompt version binding required");
    var admissionRequest = new LinkedHashMap<>(map(stored.get("boundRequest")));
    if (queued.get("validationRecordId") instanceof Number validationId)
      admissionRequest.put("canonicalValidationId", validationId.longValue());
    var fresh =
        runReview(
            new ReviewRequest(
                ((Number) stored.get("contentId")).longValue(),
                ((Number) stored.get("promptVersionId")).longValue(),
                null,
                null,
                admissionRequest),
            false);
    String binding = String.valueOf(queued.get("bindingHash"));
    requireAuthorized(stored, binding);
    requireAuthorized(fresh, binding);
    var generation = map(fresh.get("generation"));
    var params = map(queued.get("settings"));
    validateRegenerationHandoff(params, stored);
    var bound = map(generation.get("settings"));
    if (!"SUPPORTED".equals(generation.get("capabilityStatus"))
        || !"image2video".equals(generation.get("mode"))
        || !String.valueOf(generation.get("apiModelId")).equals(queued.get("model"))
        || !(params.get("durationSeconds") instanceof Number actual)
        || !(generation.get("supportedRenderDuration") instanceof Number desired)
        || Double.compare(actual.doubleValue(), desired.doubleValue()) != 0
        || !String.valueOf(bound.getOrDefault("aspectRatio", "16:9"))
            .equals(params.getOrDefault("aspectRatio", "16:9"))
        || !"480p".equals(bound.getOrDefault("resolution", "480p")))
      throw new IllegalStateException(
          "Queued generator, mode, duration or settings do not match reviewed adapter contract");
    Object frame = map(bound.get("startFrame")).get("id");
    var firstFrame =
        map(map(map(fresh.get("boundRequest")).get("authorizationEvidence")).get("visualEvidence"));
    Object validatedHash = map(firstFrame.get("firstFrame")).get("assetSha256");
    var frameRefs = maps(map(fresh.get("boundRequest")).get("references"));
    boolean matchedFrame =
        frameRefs.stream()
            .anyMatch(
                ref ->
                    "FIRST_FRAME".equals(ref.get("kind"))
                        && "VERIFIED".equals(ref.get("status"))
                        && frame != null
                        && frame.equals(ref.get("relativePath"))
                        && ref.get("sha256") != null
                        && ref.get("sha256").equals(validatedHash));
    if (!matchedFrame
        || !String.valueOf(frame).equals(String.valueOf(params.get("firstFrameImageId"))))
      throw new IllegalStateException(
          "Reviewed frame path/hash must match the canonical visual evidence");
    if (!maps(generation.get("segments")).isEmpty())
      throw new IllegalStateException("Multi-segment execution requires a verified adapter");
    return Map.of(
        "renderAuthorization",
        "AUTHORIZED",
        "bindingHash",
        binding,
        "existingEvidenceStillRequired",
        true);
  }

  public Map<String, Object> regenerationHandoff(Map<String, Object> input) {
    UUID parentVideo = UUID.fromString(String.valueOf(input.get("parentVideoId")));
    var qa =
        getByKind(UUID.fromString(String.valueOf(input.get("qaRecordId"))), "ACTUAL_RENDER_QA");
    var review = getByKind(UUID.fromString(String.valueOf(input.get("reviewId"))), "REVIEW");
    String reason = String.valueOf(input.getOrDefault("reason", ""));
    if (reason.isBlank()
        || !Boolean.TRUE.equals(map(qa.get("repairEconomics")).get("fullRerenderJustified")))
      throw new IllegalArgumentException("Evidence-bound full rerender justification is required");
    var parent = videos.get(parentVideo);
    UUID variantId =
        input.get("parentVariantId") == null
            ? null
            : UUID.fromString(String.valueOf(input.get("parentVariantId")));
    String path =
        variantId == null
            ? parent.relativePath()
            : variantService.get(parentVideo, variantId).generatedPath();
    if (!path.equals(qa.get("relativePath")))
      throw new IllegalArgumentException("QA is not bound to the selected exact parent file");
    UUID artifactVideo = UUID.fromString(String.valueOf(qa.get("videoId")));
    String hash =
        jdbc.sql("SELECT content_hash FROM videos WHERE id=:id")
            .param("id", artifactVideo)
            .query(String.class)
            .single();
    if (!hash.equals(qa.get("assetHash")) || !hash.equals(currentMediaHash(path)))
      throw new IllegalArgumentException("Parent actual-video hash changed");
    var sourceReview = getByKind(UUID.fromString(String.valueOf(qa.get("reviewId"))), "REVIEW");
    if (!java.util.Objects.equals(
        String.valueOf(sourceReview.get("contentId")), String.valueOf(review.get("contentId"))))
      throw new IllegalArgumentException("Regeneration source belongs to another content");
    boolean descendant =
        jdbc.sql(
                "WITH RECURSIVE ancestry AS (SELECT id,parent_prompt_version_id FROM"
                    + " prompt_versions WHERE id=:new UNION ALL SELECT"
                    + " pv.id,pv.parent_prompt_version_id FROM prompt_versions pv JOIN ancestry ON"
                    + " pv.id=ancestry.parent_prompt_version_id) SELECT EXISTS(SELECT 1 FROM"
                    + " ancestry WHERE id=:old)")
            .param("new", ((Number) review.get("promptVersionId")).longValue())
            .param("old", ((Number) sourceReview.get("promptVersionId")).longValue())
            .query(Boolean.class)
            .single();
    if (!descendant)
      throw new IllegalArgumentException(
          "Regeneration prompt must preserve exact parent source ancestry");
    var record = new LinkedHashMap<String, Object>();
    record.put("parentVideoId", parentVideo.toString());
    record.put("parentVariantId", variantId);
    record.put("parentAssetHash", hash);
    record.put("qaRecordId", qa.get("recordId"));
    record.put("reviewId", review.get("recordId"));
    record.put("bindingHash", review.get("bindingHash"));
    record.put("contentId", review.get("contentId"));
    record.put("promptVersionId", review.get("promptVersionId"));
    record.put("reason", reason);
    record.put("generation", review.get("generation"));
    record.put("executionScope", "FULL_VIDEO_ONLY");
    record.put("status", "HANDOFF_PENDING_CANONICAL_AUTHORIZATION");
    record.put("automaticExecution", false);
    String fingerprint;
    try {
      fingerprint =
          HexFormat.of()
              .formatHex(
                  MessageDigest.getInstance("SHA-256").digest(json.writeValueAsBytes(record)));
    } catch (Exception error) {
      throw new IllegalStateException("Regeneration fingerprint unavailable", error);
    }
    record.put("handoffFingerprint", fingerprint);
    var replay = regenerationReplay(fingerprint);
    if (replay.isPresent()) return replay.get();
    try {
      record.put(
          "recordId",
          save("REGENERATION_HANDOFF", String.valueOf(review.get("bindingHash")), record));
    } catch (org.springframework.dao.DataIntegrityViolationException concurrent) {
      return regenerationReplay(fingerprint).orElseThrow(() -> concurrent);
    }
    return record;
  }

  private java.util.Optional<Map<String, Object>> regenerationReplay(String fingerprint) {
    return jdbc.sql(
            "SELECT id FROM post_family_workflow_events WHERE kind='REGENERATION_HANDOFF' AND"
                + " payload->>'handoffFingerprint'=:fingerprint")
        .param("fingerprint", fingerprint)
        .query(UUID.class)
        .optional()
        .map(this::get);
  }

  private String currentMediaHash(String path) {
    try {
      var digest = MessageDigest.getInstance("SHA-256");
      try (var stream =
          new java.security.DigestInputStream(
              media.resolve(path).resource().getInputStream(), digest)) {
        stream.transferTo(java.io.OutputStream.nullOutputStream());
      }
      return HexFormat.of().formatHex(digest.digest());
    } catch (java.io.IOException | java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("Parent media hash could not be verified", error);
    }
  }

  private void validateRegenerationHandoff(Map<String, Object> params, Map<String, Object> review) {
    if (!params.containsKey("regenerationHandoffId")) return;
    var handoff =
        getByKind(
            UUID.fromString(String.valueOf(params.get("regenerationHandoffId"))),
            "REGENERATION_HANDOFF");
    if (!"FULL_VIDEO_ONLY".equals(handoff.get("executionScope"))
        || !java.util.Objects.equals(handoff.get("bindingHash"), review.get("bindingHash"))
        || !java.util.Objects.equals(handoff.get("reviewId"), review.get("recordId")))
      throw new IllegalStateException("Regeneration source binding is stale");
    var qa =
        getByKind(UUID.fromString(String.valueOf(handoff.get("qaRecordId"))), "ACTUAL_RENDER_QA");
    String hash =
        jdbc.sql("SELECT content_hash FROM videos WHERE id=:id")
            .param("id", UUID.fromString(String.valueOf(qa.get("videoId"))))
            .query(String.class)
            .single();
    if (!hash.equals(handoff.get("parentAssetHash"))
        || !hash.equals(currentMediaHash(String.valueOf(qa.get("relativePath"))))
        || !Boolean.TRUE.equals(map(qa.get("repairEconomics")).get("fullRerenderJustified")))
      throw new IllegalStateException("Regeneration parent evidence is stale");
    for (String key : List.of("parentVideoId", "parentVariantId", "parentAssetHash"))
      if (!java.util.Objects.equals(
          String.valueOf(handoff.get(key)), String.valueOf(params.get(key))))
        throw new IllegalStateException(
            "Regeneration lineage must match the reviewed immutable handoff");
  }

  public Map<String, Object> creativeRoleReadiness() {
    return ml.workflow("creative-role/readiness", Map.of());
  }

  /** Rebuilds a current read model from an immutable saved BUILD_PROMPT record, locally only. */
  @Transactional
  public Map<String, Object> revalidateProductionSpec(UUID sourceRecordId) {
    var source = getByKind(sourceRecordId, "CREATIVE_ROLE");
    if (!"BUILD_PROMPT".equals(source.get("role")))
      throw new IllegalArgumentException("Only a saved BUILD_PROMPT record can be migrated");
    var savedResult = map(source.get("result"));
    String prompt = String.valueOf(savedResult.getOrDefault("prompt", ""));
    if (prompt.isBlank()) throw new IllegalArgumentException("The saved prompt is empty; it cannot be revalidated");
    var sourceRequest = map(source.get("sourceRequest"));
    var context = map(sourceRequest.get("context"));
    var target = map(context.get("targetConfiguration"));
    String approvedStory = "";
    var identity = new LinkedHashMap<String, Object>();
    String migrationVersion = "openart-production-prompt-v2-legacy-migration-evidence-v7";
    identity.put("savedPromptRecordId", sourceRecordId.toString());
    identity.put("savedPromptVersion", "BUILD_PROMPT_RECORD");
    identity.put("storyRecordId", "UNKNOWN");
    identity.put("storyRevisionId", "UNKNOWN");
    identity.put("approvalRecordId", "UNKNOWN");
    identity.put("storyTitle", "UNKNOWN");
    identity.put("projectTitle", "UNKNOWN");
    identity.put("workspacePath", "UNKNOWN");

    String storyIdText = String.valueOf(context.getOrDefault("sourceStoryRecordId", "")).trim();
    String candidateId = String.valueOf(context.getOrDefault("candidateId", "")).trim();
    String revisionId = String.valueOf(context.getOrDefault("storyRevisionId", "")).trim();
    if (!storyIdText.isBlank() && !"MANUAL_STORY".equals(storyIdText)) {
      UUID storyId;
      try { storyId = UUID.fromString(storyIdText); }
      catch (IllegalArgumentException invalid) { throw new IllegalArgumentException("Saved story pointer is malformed", invalid); }
      var story = getByKind(storyId, "CREATIVE_ROLE");
      if (!"STORY".equals(story.get("role")))
        throw new IllegalArgumentException("Saved story pointer does not resolve to a STORY record");
      // Older BUILD_PROMPT requests omitted candidateId even though they stored
      // an immutable revision id. Recover it only when the revision hash
      // matches an actual candidate in the exact linked story record.
      if (candidateId.isBlank() && !revisionId.isBlank()) {
        int marker = revisionId.lastIndexOf("-revision-");
        if (marker > 0) {
          String revisionCandidate = revisionId.substring(0, marker);
          String revisionFingerprint = revisionId.substring(marker + "-revision-".length());
          String candidate = storyCandidateText(story, storyId, revisionCandidate);
          if (candidate != null && revisionFingerprint.equals(storyFingerprint(candidate.trim())))
            candidateId = revisionCandidate;
        }
      }
      Map<String, Object> session = latestStudioSessionForStory(storyId.toString());
      if (candidateId.isBlank()) {
        String sessionCandidate = String.valueOf(session.getOrDefault("selectedCandidateIdValue", "")).trim();
        Object rawFingerprints = session.get("reviewedStoryFingerprints");
        Map<String, Object> fingerprints = map(rawFingerprints);
        String sessionFingerprint = String.valueOf(fingerprints.getOrDefault(sessionCandidate, "")).trim();
        String candidate = storyCandidateText(story, storyId, sessionCandidate);
        if (candidate != null && !sessionCandidate.isBlank()
            && sessionFingerprint.equals(storyFingerprint(candidate.trim()))
            && revisionId.equals(sessionCandidate + "-revision-" + sessionFingerprint))
          candidateId = sessionCandidate;
      }
      String candidateText = storyCandidateText(story, storyId, candidateId);
      boolean exactRevision = candidateText != null
          && revisionId.equals(candidateId + "-revision-" + storyFingerprint(candidateText.trim()));
      identity.put("storyRecordId", storyId.toString());
      identity.put("storyRevisionId", revisionId.isBlank() ? "UNKNOWN" : revisionId);
      if (!candidateId.isBlank()) identity.put("candidateId", candidateId);
      if (!session.isEmpty()) {
        identity.put("workspaceSessionId", session.getOrDefault("sessionId", "UNKNOWN"));
        identity.put("projectTitle", session.getOrDefault("title", "UNKNOWN"));
        identity.put("workspacePath", session.getOrDefault("workspacePath", "UNKNOWN"));
        if (session.get("contentId") != null && !String.valueOf(session.get("contentId")).isBlank())
          identity.put("contentId", session.get("contentId"));
        if (session.get("promptVersionId") != null && !String.valueOf(session.get("promptVersionId")).isBlank())
          identity.put("promptVersionId", session.get("promptVersionId"));
        identity.put("workspaceProvenance", "EXACT_STORY_ID_SESSION_SNAPSHOT");
      }
      if (exactRevision) {
        var approval = findExactStoryApproval(storyId, candidateId, revisionId, candidateText.trim());
        identity.put("sourceLineageStatus", approval == null ? "EXACT_STORY_POINTER_NO_EXACT_APPROVAL" : "EXACT_APPROVED_STORY_LINEAGE");
        if (approval != null) {
          identity.put("approvalRecordId", approval.get("id"));
          approvedStory = candidateText.trim();
        }
        var alternative = storyAlternative(story, candidateId);
        identity.put("storyTitle", alternative.getOrDefault("title", "UNKNOWN"));
      } else {
        identity.put("sourceLineageStatus", "CANDIDATE_OR_REVISION_POINTER_UNVERIFIED");
      }
    } else {
      identity.put("sourceLineageStatus", "NO_CANONICAL_STORY_POINTER");
    }

    String characterName = String.valueOf(target.getOrDefault("mainCharacter", context.getOrDefault("mainCharacter", ""))).trim();
    var characterRecord = map(context.get("characterRecord"));
    if (!characterName.isBlank() && characterRecord.get("id") != null) {
      String characterId = String.valueOf(characterRecord.get("id"));
      var catalog = jdbc.sql("SELECT id,name,status,active FROM characters WHERE id=:id AND lower(name)=lower(:name)")
          .param("id", UUID.fromString(characterId)).param("name", characterName)
          .query((rs, row) -> Map.<String, Object>of("id", rs.getString("id"), "name", rs.getString("name"),
              "status", rs.getString("status"), "active", rs.getBoolean("active"))).optional().orElse(null);
      if (catalog != null) {
        var confirmed = new LinkedHashMap<String, Object>(catalog);
        confirmed.put("catalogVerified", true);
        context.put("characterRecord", confirmed);
        var refs = jdbc.sql("SELECT id,relative_path,description FROM character_references WHERE character_id=:id ORDER BY created_at")
            .param("id", UUID.fromString(characterId)).query((rs, row) -> Map.<String, Object>of(
                "id", rs.getString("id"), "relativePath", rs.getString("relative_path"),
                "description", rs.getString("description") == null ? "" : rs.getString("description"))).list();
        context.put("characterReferences", refs.stream().map(ref -> Map.<String, Object>of(
            "id", ref.get("id"), "relativePath", ref.get("relativePath"), "verified", false,
            "verificationStatus", "NOT_VERIFIED")).toList());
        identity.put("characterCatalogId", characterId);
        identity.put("characterCatalogStatus", catalog.get("status"));
      }
    }
    var mlContext = new LinkedHashMap<String, Object>();
    mlContext.put("sourceIdentity", identity);
    mlContext.put("targetConfiguration", target);
    mlContext.put("mainCharacter", characterName);
    mlContext.put("characterRecord", context.get("characterRecord"));
    mlContext.put("characterReferences", context.getOrDefault("characterReferences", List.of()));

    String sourcePromptSha256 = sha256(prompt);
    String fingerprint = sha256(sourceRecordId + "\n" + migrationVersion + "\n" + sourcePromptSha256);
    jdbc.sql("SELECT pg_advisory_xact_lock(hashtext(:fingerprint))").param("fingerprint", fingerprint).query((rs, row) -> rs.getObject(1)).list();
    var existing = jdbc.sql("SELECT id,payload::text payload,created_at FROM post_family_workflow_events WHERE kind='PRODUCTION_SPEC_MIGRATION' AND payload->>'idempotencyFingerprint'=:fingerprint ORDER BY created_at DESC LIMIT 1")
        .param("fingerprint", fingerprint).query((rs, row) -> {
          var value = read(rs.getString("payload"));
          value.put("recordId", rs.getString("id"));
          value.put("createdAt", rs.getObject("created_at", java.time.OffsetDateTime.class).toInstant().toString());
          return value;
        }).optional();
    if (existing.isPresent()) return existing.get();

    var request = new LinkedHashMap<String, Object>();
    request.put("prompt", prompt);
    request.put("approvedStory", approvedStory);
    request.put("context", mlContext);
    var projection = ml.workflow("creative-role/revalidate-production-spec", request);
    var migration = new LinkedHashMap<String, Object>();
    migration.put("migrationVersion", migrationVersion);
    migration.put("originRecordId", sourceRecordId.toString());
    migration.put("sourceRecordId", sourceRecordId.toString());
    migration.put("sourcePromptSha256", sourcePromptSha256);
    migration.put("idempotencyFingerprint", fingerprint);
    migration.put("createdAt", Instant.now().toString());
    migration.put("migrationMethod", "LOCAL_DETERMINISTIC_NO_PROVIDER_CALL");
    migration.put("sourceLineage", identity);
    migration.put("result", projection);
    migration.put("validationStatus", "NOT_VALIDATED");
    migration.put("providerCalls", 0);
    migration.put("recordId", save("PRODUCTION_SPEC_MIGRATION", fingerprint, migration));
    return migration;
  }

  private Map<String, Object> findExactStoryApproval(UUID storyId, String candidateId, String revisionId, String candidateText) {
    var rows = jdbc.sql("SELECT id,payload::text payload FROM post_family_workflow_events WHERE kind='STORY_APPROVAL' AND payload->>'storyRecordId'=:story ORDER BY created_at DESC")
        .param("story", storyId.toString()).query((rs, row) -> Map.of("id", rs.getString("id"), "payload", rs.getString("payload"))).list();
    for (var row : rows) {
      var approval = read(String.valueOf(row.get("payload")));
      if (candidateId.equals(String.valueOf(approval.getOrDefault("candidateId", "")))
          && revisionId.equals(String.valueOf(approval.getOrDefault("revisionId", "")))
          && candidateText.equals(String.valueOf(approval.getOrDefault("approvedText", "")).trim())
          && storyFingerprint(candidateText).equals(String.valueOf(approval.getOrDefault("contentFingerprint", ""))))
        return Map.of("id", row.get("id"), "payload", approval);
    }
    return null;
  }

  private Map<String, Object> storyAlternative(Map<String, Object> story, String candidateId) {
    Object raw = map(story.get("result")).get("alternatives");
    if (raw instanceof List<?> alternatives) for (Object item : alternatives) {
      if (item instanceof Map<?, ?> candidate && candidateId.equals(String.valueOf(candidate.get("candidateId")))) {
        var result = new LinkedHashMap<String, Object>();
        result.put("title", candidate.get("title") == null ? "UNKNOWN" : candidate.get("title"));
        Object candidateText = candidate.get("text") == null ? candidate.get("description") : candidate.get("text");
        result.put("text", candidateText == null ? "" : candidateText);
        return result;
      }
    }
    return Map.of();
  }

  private Map<String, Object> latestStudioSessionForStory(String storyId) {
    return jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'storyRecordId'=:story ORDER BY created_at DESC LIMIT 1")
        .param("story", storyId).query(String.class).optional().map(this::read).orElse(Map.of());
  }

  @Transactional
  public Map<String, Object> creativeRole(Map<String, Object> request) {
    return creativeRole(request, false);
  }

  @Transactional
  private Map<String, Object> creativeRole(Map<String, Object> request, boolean sourceBoundOptimization) {
    String role = String.valueOf(request.get("role"));
    if (!List.of("STORY", "STORY_REVIEW", "BUILD_PROMPT", "MINIMAL_REPAIR", "PROMPT_OPTIMIZATION").contains(role))
      throw new IllegalArgumentException("Unsupported creative role");
    if ("PROMPT_OPTIMIZATION".equals(role) && !sourceBoundOptimization)
      throw new IllegalArgumentException("Creative optimization must use the source-bound Step 6 workflow");
    if ("STORY".equals(role) || "PROMPT_OPTIMIZATION".equals(role)) {
      if (!Boolean.TRUE.equals(request.get("generationAuthorized")))
        throw new IllegalArgumentException("Explicit authorization for this paid creative operation is required");
      if (!(request.get("maxCostUsd") instanceof Number ceiling)
          || !Double.isFinite(ceiling.doubleValue()) || ceiling.doubleValue() <= 0 || ceiling.doubleValue() > 20)
        throw new IllegalArgumentException("A positive authorized cost ceiling is required");
      if (String.valueOf(request.getOrDefault("text", "")).isBlank())
        throw new IllegalArgumentException("Source text is required before requesting creative generation");
      if ("PROMPT_OPTIMIZATION".equals(role)) {
        var optimizationContext = map(request.get("context"));
        if (String.valueOf(optimizationContext.getOrDefault("analysisRunId", "")).isBlank()
            || String.valueOf(optimizationContext.getOrDefault("promptVersionId", "")).isBlank()
            || !(optimizationContext.get("essentialEvents") instanceof List<?> events)
            || events.isEmpty())
          throw new IllegalArgumentException("Source analysis and essential events are required");
      }
    }
    if ("STORY".equals(role)) {
      videos.requirePromptWorkspace(String.valueOf(map(request.get("context")).getOrDefault("workspacePath", "")));
    }
    if (map(request.get("context")).get("sourceStoryRecordId") instanceof String storyId
        && !storyId.isBlank() && !"MANUAL_STORY".equals(storyId)) {
      var story = getByKind(UUID.fromString(storyId), "CREATIVE_ROLE");
      if (!"STORY".equals(story.get("role")))
        throw new IllegalArgumentException("Story provenance requires an exact STORY record");
    }
    var verifiedRequest = new LinkedHashMap<>(request);
    // Authorization is enforced here; the strict provider contract accepts only role/text/context/budget.
    verifiedRequest.remove("generationAuthorized");
    var context = new LinkedHashMap<>(map(request.get("context")));
    if ("BUILD_PROMPT".equals(role)) {
      context.put("promptBuilderContractVersion", BUILD_PROMPT_CONTRACT_VERSION);
      Object storyId = context.get("sourceStoryRecordId");
      if (storyId != null && !"MANUAL_STORY".equals(String.valueOf(storyId))) {
        UUID sourceId = UUID.fromString(String.valueOf(storyId));
        var story = getByKind(sourceId, "CREATIVE_ROLE");
        String candidateId = String.valueOf(context.getOrDefault("candidateId", ""));
        String revisionId = String.valueOf(context.getOrDefault("storyRevisionId", ""));
        String candidate = storyCandidateText(story, sourceId, candidateId);
        if (candidate == null || !candidate.trim().equals(String.valueOf(request.getOrDefault("text", "")).trim())
            || !(candidateId + "-revision-" + storyFingerprint(candidate.trim())).equals(revisionId)
            || !hasStoryApproval(sourceId, candidateId, revisionId, String.valueOf(context.getOrDefault("approvalRecordId", ""))))
          throw new IllegalArgumentException("BUILD_PROMPT requires the exact approved story candidate and revision");
      }
      bindCanonicalCharacterReferences(context);
    }
    context.remove("retrievedLessons");
    var scope = map(context.remove("lessonContext"));
    var lessons =
        scope.get("duration") instanceof Number duration
            ? retrieveLessons(
                String.valueOf(scope.get("contentProfile")),
                String.valueOf(scope.get("modelVersion")),
                duration.doubleValue(),
                scope)
            : List.<Map<String, Object>>of();
    context.put("retrievedLessons", lessons);
    verifiedRequest.put("context", context);
    // BUILD_PROMPT is resumable. The exact approved story revision and target
    // configuration form the request identity; a changed budget must never
    // turn the same request into another paid provider call.
    String requestFingerprint = creativeRoleFingerprint(role, verifiedRequest);
    if ("BUILD_PROMPT".equals(role) || "PROMPT_OPTIMIZATION".equals(role)) {
      // Serialize identical requests across tabs/processes while the provider
      // call is in progress. The first transaction commits the durable result;
      // the next caller then replays it without another provider call.
      jdbc.sql("SELECT pg_advisory_xact_lock(hashtext(:fingerprint))")
          .param("fingerprint", requestFingerprint)
          .query((rs, rowNum) -> rs.getObject(1))
          .list();
      var saved = findCreativeRoleByFingerprint(requestFingerprint, role);
      if (saved.isPresent()) {
        if (!(saved.get().get("result") instanceof Map<?, ?>)
            || "PROVIDER_RESULT_REJECTED".equals(saved.get().get("attemptState"))) {
          if ("PROMPT_OPTIMIZATION".equals(role))
            throw new IllegalStateException("A prior optimization provider outcome is unresolved; do not automatically retry");
        } else {
          var replay = new LinkedHashMap<>(saved.get());
          replay.put("recordId", saved.get().get("recordId"));
          replay.put("reused", true);
          replay.put("calls", 0);
          replay.put("attemptState", "REUSED_SAVED_RESULT");
          replay.put("requestFingerprint", requestFingerprint);
          return replay;
        }
      }
    }
    Map<String, Object> workflowResponse;
    try {
      workflowResponse = ml.workflow("creative-role", verifiedRequest);
    } catch (RuntimeException error) {
      String detail = error.getMessage() == null ? "The ML service rejected the request" : error.getMessage();
      var failed = new LinkedHashMap<String, Object>();
      failed.put("role", role);
      failed.put("sourceStoryRecordId", context.get("sourceStoryRecordId"));
      failed.put("sourceRequest", verifiedRequest);
      failed.put("requestFingerprint", requestFingerprint);
      failed.put("attemptState", "FAILED");
      failed.put("validationStatus", "UNKNOWN");
      failed.put("attemptDiagnostics", Map.of(
          "provider", role.equals("STORY") ? "deepseek" : "openai",
          "error", detail,
          "persisted", true,
          "retryAutomatically", false));
      try {
        failed.put("recordId", save("CREATIVE_ROLE", null, failed));
      } catch (RuntimeException persistenceError) {
        // Preserve the provider error as the user-facing outcome even if the
        // diagnostic append itself cannot be written.
      }
      throw new IllegalStateException("Creative role request failed: " + detail, error);
    }
    var result = new LinkedHashMap<>(workflowResponse);
    result.put("retrievedLessons", lessons);
    result.put("sourceStoryRecordId", context.get("sourceStoryRecordId"));
    result.put("sourceRequest", verifiedRequest);
    result.put("requestFingerprint", requestFingerprint);
    boolean rejected = "PROVIDER_RESULT_REJECTED".equals(workflowResponse.get("attemptState"));
    boolean unknown = "PROVIDER_OUTCOME_UNKNOWN".equals(workflowResponse.get("attemptState"));
    result.put("attemptState", rejected ? "PROVIDER_RESULT_REJECTED" : unknown ? "PROVIDER_OUTCOME_UNKNOWN" : "SAVED");
    var diagnostics = new LinkedHashMap<>(map(workflowResponse.get("attemptDiagnostics")));
    diagnostics.put("provider", result.getOrDefault("provider", "unknown"));
    diagnostics.put("model", result.getOrDefault("model", "unknown"));
    if (!unknown) diagnostics.put("calls", result.getOrDefault("calls", 0));
    diagnostics.put("validationStatus", rejected ? "REJECTED" : unknown ? "UNKNOWN" : "NOT_VALIDATED");
    diagnostics.put("persisted", true);
    result.put("attemptDiagnostics", diagnostics);
    result.put("validationStatus", rejected ? "REJECTED" : unknown ? "UNKNOWN" : "NOT_VALIDATED");
    if ("PROMPT_OPTIMIZATION".equals(role))
      result.put("operatorAuthorization", Map.of(
          "operatorConfirmed", true,
          "maxCostUsd", request.get("maxCostUsd"),
          "authorizedAt", Instant.now().toString()));
    result.put("recordId", save("CREATIVE_ROLE", null, result));
    return result;
  }

  private String creativeRoleFingerprint(String role, Map<String, Object> request) {
    try {
      var canonical = new LinkedHashMap<String, Object>();
      canonical.put("role", role);
      canonical.put("text", request.get("text"));
      canonical.put("context", request.get("context"));
      if ("BUILD_PROMPT".equals(role)) {
        canonical.put("builderContractVersion", BUILD_PROMPT_CONTRACT_VERSION);
        canonical.put("builderModel", buildPromptModel == null ? "" : buildPromptModel);
      }
      if ("PROMPT_OPTIMIZATION".equals(role))
        canonical.put("optimizationModel", System.getenv().getOrDefault("WORKFLOW_PROMPT_OPTIMIZATION_MODEL", ""));
      return HexFormat.of().formatHex(
          MessageDigest.getInstance("SHA-256").digest(json.writeValueAsBytes(canonical)));
    } catch (Exception error) {
      throw new IllegalStateException("Creative role request identity unavailable", error);
    }
  }

  private void bindCanonicalCharacterReferences(Map<String, Object> context) {
    context.put("characterReferences", List.of());
    var target = map(context.get("targetConfiguration"));
    String characterName = String.valueOf(target.getOrDefault("mainCharacter", context.getOrDefault("mainCharacter", ""))).trim();
    if (characterName.isBlank() || jdbc == null) return;
    var provided = map(context.get("characterRecord"));
    String rawId = String.valueOf(provided.getOrDefault("id", "")).trim();
    Map<String, Object> canonical;
    if (!rawId.isBlank()) {
      UUID characterId;
      try { characterId = UUID.fromString(rawId); } catch (IllegalArgumentException error) { characterId = null; }
      canonical = characterId == null ? Map.of() : jdbc.sql("SELECT id::text id,name,status,notes,active FROM characters WHERE id=:id AND active=true")
          .param("id", characterId).query((rs, ignored) -> Map.<String, Object>of("id", rs.getString("id"), "name", rs.getString("name"), "status", rs.getString("status"), "notes", rs.getString("notes") == null ? "" : rs.getString("notes"), "active", rs.getBoolean("active"))).optional().orElse(Map.of());
    } else {
      canonical = jdbc.sql("SELECT id::text id,name,status,notes,active FROM characters WHERE lower(name)=lower(:name) AND active=true")
          .param("name", characterName).query((rs, ignored) -> Map.<String, Object>of("id", rs.getString("id"), "name", rs.getString("name"), "status", rs.getString("status"), "notes", rs.getString("notes") == null ? "" : rs.getString("notes"), "active", rs.getBoolean("active"))).optional().orElse(Map.of());
    }
    if (!canonical.isEmpty() && !characterName.equalsIgnoreCase(String.valueOf(canonical.get("name"))))
      throw new IllegalArgumentException("Selected character ID and name do not match the canonical character catalog");
    context.put("characterRecord", canonical);
    if (canonical.isEmpty()) { context.put("characterReferences", List.of()); return; }
    UUID characterId = UUID.fromString(String.valueOf(canonical.get("id")));
    String rootValue = System.getenv().getOrDefault("POMPOM_DATA_ROOT", "/data");
    java.nio.file.Path root = java.nio.file.Path.of(rootValue).toAbsolutePath().normalize();
    var references = jdbc.sql("SELECT id::text id,relative_path,description FROM character_references WHERE character_id=:id ORDER BY created_at,id")
        .param("id", characterId).query((rs, ignored) -> {
          String relative = rs.getString("relative_path");
          java.nio.file.Path resolved = root.resolve(relative).normalize();
          if (!resolved.startsWith(root) || !java.nio.file.Files.isRegularFile(resolved)) return null;
          try {
            byte[] bytes = java.nio.file.Files.readAllBytes(resolved);
            String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
            return Map.<String, Object>of("id", rs.getString("id"), "relativePath", relative,
                "description", rs.getString("description") == null ? "" : rs.getString("description"),
                "status", "VERIFIED", "sha256", sha);
          } catch (Exception error) { return null; }
        }).list().stream().filter(java.util.Objects::nonNull).toList();
    boolean openArtCatalogAvailable = Boolean.TRUE.equals(jdbc.sql(
            "SELECT to_regclass('public.openart_reference_assets') IS NOT NULL")
        .query(Boolean.class).single());
    if (openArtCatalogAvailable) {
      var openArtReferences = jdbc.sql("SELECT id::text id,canonical_key,display_name,source,media_type,provider_asset_id,local_path,sha256,status FROM openart_reference_assets WHERE status='AVAILABLE' AND lower(media_type) LIKE 'image%' AND (lower(canonical_key) IN (:name,'character/'||:name,'characters/'||:name) OR lower(display_name)=:name) ORDER BY source,canonical_key")
          .param("name", characterName.toLowerCase(java.util.Locale.ROOT))
          .query((rs, ignored) -> {
            String source = rs.getString("source");
            String assetId = rs.getString("provider_asset_id");
            String relative = rs.getString("local_path");
            String sha = rs.getString("sha256");
            if ("LOCAL".equals(source)) {
              if (relative == null) return null;
              java.nio.file.Path resolved = root.resolve(relative).normalize();
              if (!resolved.startsWith(root) || !java.nio.file.Files.isRegularFile(resolved)) return null;
              try {
                sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(java.nio.file.Files.readAllBytes(resolved)));
              } catch (Exception error) { return null; }
            } else if (assetId == null || sha == null || sha.isBlank()) return null;
            return Map.<String, Object>of("id", rs.getString("id"), "canonicalKey", rs.getString("canonical_key"),
                "displayName", rs.getString("display_name"), "source", source, "status", "VERIFIED", "sha256", sha);
          }).list().stream().filter(java.util.Objects::nonNull).toList();
      if (!openArtReferences.isEmpty()) references = openArtReferences;
    }
    context.put("characterReferences", references);
  }

  private java.util.Optional<Map<String, Object>> findCreativeRoleByFingerprint(
      String fingerprint, String role) {
    return jdbc.sql(
            "SELECT id,payload::text payload FROM post_family_workflow_events "
                + "WHERE kind='CREATIVE_ROLE' AND payload->>'role'=:role "
                + "AND payload->>'requestFingerprint'=:fingerprint "
                + "ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("role", role)
        .param("fingerprint", fingerprint)
        .query((rs, ignored) -> {
          var value = read(rs.getString("payload"));
          value.put("recordId", rs.getString("id"));
          return value;
        }).optional();
  }

  public Map<String, Object> approveStory(UUID storyRecordId, Map<String, Object> request) {
    var story = getByKind(storyRecordId, "CREATIVE_ROLE");
    if (!"STORY".equals(story.get("role")))
      throw new IllegalArgumentException("Only a STORY role record can be approved");
    String approvedText = String.valueOf(request.getOrDefault("approvedText", "")).trim();
    if (approvedText.isBlank()) throw new IllegalArgumentException("approvedText is required");
    String candidateId = String.valueOf(request.getOrDefault("candidateId", "")).trim();
    String revisionId = String.valueOf(request.getOrDefault("revisionId", "")).trim();
    String fingerprint = String.valueOf(request.getOrDefault("contentFingerprint", "")).trim();
    if (candidateId.isBlank() || revisionId.isBlank() || fingerprint.isBlank())
      throw new IllegalArgumentException("A candidate ID, exact revision ID and content fingerprint are required for approval");
    String candidateText = storyCandidateText(story, storyRecordId, candidateId);
    if (candidateText == null || !candidateText.trim().equals(approvedText))
      throw new IllegalArgumentException("The selected candidate does not match the saved story text");
    String expectedFingerprint = storyFingerprint(approvedText);
    if (!expectedFingerprint.equals(fingerprint)
        || !(candidateId + "-revision-" + expectedFingerprint).equals(revisionId))
      throw new IllegalArgumentException("The approval revision does not match the selected candidate content");
    var approval = new LinkedHashMap<String, Object>();
    approval.put("role", "STORY_APPROVAL");
    approval.put("storyRecordId", storyRecordId.toString());
    approval.put("approvedText", approvedText);
    approval.put("candidateId", request.get("candidateId"));
    approval.put("revisionId", request.get("revisionId"));
    approval.put("contentFingerprint", request.get("contentFingerprint"));
    approval.put("sourceType", request.getOrDefault("sourceType", "GENERATED_CANDIDATE"));
    approval.put("sourceRevisionId", request.get("sourceRevisionId"));
    approval.put("reviewRecordId", request.get("reviewRecordId"));
    approval.put("originalStory", story.get("result"));
    approval.put("approvedAt", java.time.Instant.now().toString());
    approval.put("recordId", save("STORY_APPROVAL", storyRecordId.toString(), approval));
    return approval;
  }

  @Transactional
  public Map<String, Object> saveStoryRevision(UUID storyRecordId, Map<String, Object> request) {
    var source = getByKind(storyRecordId, "CREATIVE_ROLE");
    if (!"STORY".equals(source.get("role")))
      throw new IllegalArgumentException("Only a saved STORY record can be revised");
    String parentCandidateId = String.valueOf(request.getOrDefault("candidateId", "")).trim();
    String parentRevisionId = String.valueOf(request.getOrDefault("revisionId", "")).trim();
    String revisedText = String.valueOf(request.getOrDefault("text", "")).trim();
    if (revisedText.isBlank()) throw new IllegalArgumentException("Revised story text is required");
    String parentText = storyCandidateText(source, storyRecordId, parentCandidateId);
    if (parentText == null || parentRevisionId.isBlank()
        || !(parentCandidateId + "-revision-" + storyFingerprint(parentText.trim())).equals(parentRevisionId))
      throw new IllegalArgumentException("The source candidate revision is missing or does not match the saved story");

    var context = new LinkedHashMap<String, Object>();
    Object rawRequest = source.get("sourceRequest");
    if (rawRequest instanceof Map<?, ?> requestMap && requestMap.get("context") instanceof Map<?, ?> contextMap)
      contextMap.forEach((key, value) -> context.put(String.valueOf(key), value));
    context.put("parentStoryRecordId", storyRecordId.toString());
    context.put("parentCandidateId", parentCandidateId);
    context.put("parentRevisionId", parentRevisionId);
    var sourceRequest = new LinkedHashMap<String, Object>();
    sourceRequest.put("role", "STORY_REVISION");
    Object sourceText = rawRequest instanceof Map<?, ?> requestMap ? requestMap.get("text") : null;
    sourceRequest.put("text", sourceText == null ? "" : String.valueOf(sourceText));
    sourceRequest.put("context", context);

    String candidateId = "candidate-1";
    String fingerprint = storyFingerprint(revisedText);
    var alternative = new LinkedHashMap<String, Object>();
    alternative.put("candidateId", candidateId);
    alternative.put("title", "Edited story");
    alternative.put("text", revisedText);
    var result = new LinkedHashMap<String, Object>();
    result.put("role", "STORY");
    result.put("alternatives", List.of(alternative));
    result.put("revisionId", candidateId + "-revision-" + fingerprint);
    result.put("parentStoryRecordId", storyRecordId.toString());
    var revision = new LinkedHashMap<String, Object>();
    revision.put("role", "STORY");
    revision.put("sourceRequest", sourceRequest);
    revision.put("sourceRecordId", storyRecordId.toString());
    revision.put("title", request.getOrDefault("title", source.getOrDefault("title", "Untitled story session")));
    revision.put("revisionType", "OPERATOR_EDIT");
    revision.put("result", result);
    revision.put("recordId", save("CREATIVE_ROLE", null, revision));
    return revision;
  }

  private String storyCandidateText(Map<String, Object> story, UUID storyRecordId, String candidateId) {
    if (candidateId == null || candidateId.isBlank()) return null;
    if ("ORIGINAL_SOURCE".equals(candidateId)) {
      Object sourceRequest = story.get("sourceRequest");
      if (sourceRequest instanceof Map<?, ?> source) {
        Object sourceText = source.get("text");
        return sourceText == null ? null : String.valueOf(sourceText);
      }
      Object sourceText = story.get("text");
      return sourceText == null ? null : String.valueOf(sourceText);
    }
    Object raw = map(story.get("result")).get("alternatives");
    if (!(raw instanceof List<?> alternatives)) return null;
    for (int i = 0; i < alternatives.size(); i++) {
      Object item = alternatives.get(i);
      String id;
      String text;
      if (item instanceof Map<?, ?> candidate) {
        id = String.valueOf(candidate.get("candidateId") == null ? "" : candidate.get("candidateId")).trim();
        Object candidateText = candidate.get("text") == null ? candidate.get("description") : candidate.get("text");
        text = candidateText == null ? "" : String.valueOf(candidateText);
      } else {
        id = storyRecordId + "-candidate-" + (i + 1);
        text = String.valueOf(item);
      }
      if (id.equals(candidateId)) return text;
    }
    return null;
  }

  private String storyFingerprint(String value) {
    int hash = 0x811c9dc5;
    for (int i = 0; i < value.length(); i++) {
      hash ^= value.charAt(i);
      hash *= 0x01000193;
    }
    return String.format(java.util.Locale.ROOT, "%08x", hash);
  }

  public Map<String, Object> saveStudioSession(Map<String, Object> request) {
    String sessionId = String.valueOf(request.getOrDefault("sessionId", "")).trim();
    if (sessionId.isBlank()) sessionId = UUID.randomUUID().toString();
    var payload = new LinkedHashMap<String, Object>(request);
    payload.put("sessionId", sessionId);
    payload.put("updatedAt", java.time.Instant.now().toString());
    payload.put("recordId", save("CREATIVE_STUDIO_SESSION", sessionId, payload));
    return payload;
  }

  public Map<String, Object> getStudioSession(UUID sessionId) {
    return jdbc.sql(
            "SELECT id,payload::text payload FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'sessionId'=:session ORDER BY created_at DESC LIMIT 1")
        .param("session", sessionId.toString())
        .query((rs, ignored) -> {
          var value = read(rs.getString("payload"));
          value.put("recordId", rs.getString("id"));
          return value;
        }).optional().orElseThrow(() -> new IllegalArgumentException("Creative studio session not found"));
  }

  public Map<String, Object> getStudioSessionForPrompt(Long contentId, Long promptVersionId) {
    return jdbc.sql(
            "SELECT id,payload::text payload FROM post_family_workflow_events "
                + "WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'contentId'=:content "
                + "AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC LIMIT 1")
        .param("content", String.valueOf(contentId))
        .param("prompt", String.valueOf(promptVersionId))
        .query((rs, ignored) -> {
          var value = read(rs.getString("payload"));
          value.put("recordId", rs.getString("id"));
          return value;
        }).optional().orElseThrow(() -> new IllegalArgumentException("Creative studio settings not found"));
  }

  public Map<String, Object> saveProductionSettings(Map<String, Object> request) {
    if (request.get("contentId") == null || request.get("promptVersionId") == null)
      throw new IllegalArgumentException("contentId and promptVersionId are required");
    long contentId = Long.parseLong(String.valueOf(request.get("contentId")));
    long promptVersionId = Long.parseLong(String.valueOf(request.get("promptVersionId")));
    var snapshot = prompts.load(contentId, promptVersionId);
    if (snapshot.contentId() != contentId || snapshot.promptVersionId() != promptVersionId)
      throw new IllegalArgumentException("Production settings require the exact content and immutable prompt version");
    var payload = new LinkedHashMap<String, Object>(request);
    payload.put("promptHash", snapshot.promptSha256());
    payload.put("savedAt", Instant.now().toString());
    payload.put("recordId", save("PRODUCTION_SETTINGS",
        String.valueOf(request.get("contentId")) + "/" + request.get("promptVersionId"), payload));
    return payload;
  }

  public Map<String, Object> getProductionSettings(Long contentId, Long promptVersionId) {
    return jdbc.sql(
            "SELECT id,payload::text payload FROM post_family_workflow_events WHERE kind='PRODUCTION_SETTINGS' "
                + "AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt "
                + "ORDER BY created_at DESC LIMIT 1")
        .param("content", String.valueOf(contentId)).param("prompt", String.valueOf(promptVersionId))
        .query((rs, ignored) -> { var value = read(rs.getString("payload")); value.put("recordId", rs.getString("id")); return value; })
        .optional().orElseThrow(() -> new IllegalArgumentException("Production settings not found"));
  }

  /** Read the existing schema snapshot without contacting a generation provider. */
  public Map<String, Object> getProviderCapabilities() {
    try {
      return json.readValue(java.nio.file.Files.readString(java.nio.file.Path.of(
          workflowDataRoot, "workflow", "provider-capabilities.json")), new TypeReference<>() {});
    } catch (java.io.IOException unavailable) {
      return Map.of("status", "UNKNOWN", "models", Map.of());
    }
  }

  /** Append operator-reviewed Step 4 interpretations without changing the immutable prompt. */
  @Transactional
  public Map<String, Object> saveProductionReviewDecision(Map<String, Object> request) {
    Object content = request.get("contentId");
    Object version = request.get("promptVersionId");
    String decisionType = String.valueOf(request.getOrDefault("decisionType", "")).trim();
    String decisionId = String.valueOf(request.getOrDefault("decisionId", "")).trim();
    String decision = String.valueOf(request.getOrDefault("decision", "")).trim();
    if (content == null || version == null || decisionType.isBlank() || decisionId.isBlank()
        || decision.isBlank())
      throw new IllegalArgumentException("contentId, promptVersionId, decisionType, decisionId and decision are required");
    if (!List.of("EVENT_CLASSIFICATION", "CREATIVE_CONFLICT", "CREATIVE_INTENT",
        "NO_TEXT_REPAIR_JUSTIFIED").contains(decisionType))
      throw new IllegalArgumentException("Unsupported production review decision type");
    String savedPrompt = jdbc.sql("SELECT raw_text FROM prompt_versions WHERE content_id=:content AND id=:version")
        .param("content", Long.valueOf(String.valueOf(content)))
        .param("version", Long.valueOf(String.valueOf(version)))
        .query(String.class).optional().orElseThrow(() -> new IllegalArgumentException("The selected immutable prompt version does not belong to this content"));
    String sourceEvidence = String.valueOf(request.getOrDefault("sourceQuote", request.getOrDefault("sourceEvidence", "")));
    Map<String, Object> analysis = null;
    if (decisionType.equals("NO_TEXT_REPAIR_JUSTIFIED")) {
      if (!decisionId.equals("step6-no-text-repair")
          || !decision.equals("NO_TEXT_REPAIR_JUSTIFIED")
          || !Boolean.TRUE.equals(request.get("operatorConfirmed")))
        throw new IllegalArgumentException("Explicit Step 6 no-repair confirmation is required");
      String analysisRunId = String.valueOf(request.getOrDefault("analysisRunId", "")).trim();
      UUID analysisId;
      try {
        analysisId = UUID.fromString(analysisRunId);
      } catch (IllegalArgumentException invalid) {
        throw new IllegalArgumentException("A valid saved analysisRunId is required", invalid);
      }
      analysis = jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id AND kind='REVIEW'")
          .param("id", analysisId)
          .query(String.class)
          .optional()
          .map(this::read)
          .orElseThrow(() -> new IllegalArgumentException("The selected analysis run does not exist"));
      if (!String.valueOf(content).equals(String.valueOf(analysis.get("contentId")))
          || !String.valueOf(version).equals(String.valueOf(analysis.get("promptVersionId"))))
        throw new IllegalArgumentException("The analysis run belongs to a different content or prompt version");
      var latest = getLatestReview(content, version);
      if (latest == null || !analysisRunId.equals(String.valueOf(latest.get("recordId"))))
        throw new IllegalStateException("The selected analysis is stale; load the latest saved quality evaluation");
      String bindingHash = String.valueOf(analysis.getOrDefault("bindingHash", ""));
      if (bindingHash.isBlank() || !bindingHash.equals(String.valueOf(request.get("analysisBindingHash"))))
        throw new IllegalArgumentException("The analysis binding does not match the saved quality evaluation");
      var canonical = map(analysis.get("canonicalRuleEvaluation"));
      String reviewStatus = String.valueOf(
          analysis.getOrDefault("reviewStatus", analysis.getOrDefault("status", ""))).toUpperCase();
      String authorizationStatus = String.valueOf(
          map(map(analysis.get("family8")).get("renderAuthorization")).getOrDefault("status", ""));
      if (!"EVALUATED".equals(canonical.get("status"))
          || !maps(canonical.get("failedRules")).isEmpty()
          || "FAIL".equalsIgnoreCase(String.valueOf(map(analysis.get("planQuality")).get("status")))
          || reviewStatus.contains("TECHNICAL_FAILURE")
          || authorizationStatus.contains("TECHNICAL_FAILURE")
          || hasActionableTextRepair(analysis))
        throw new IllegalStateException("A failed or unavailable evaluation cannot support a no-repair decision");
    }
    List<String> evidenceParts = decisionType.equals("CREATIVE_CONFLICT")
        ? sourceEvidence.lines().map(String::trim).filter(line -> !line.isBlank()).toList()
        : List.of(sourceEvidence.trim());
    if (!decisionType.equals("NO_TEXT_REPAIR_JUSTIFIED")
        && (evidenceParts.isEmpty() || evidenceParts.stream().anyMatch(part -> part.isBlank() || !savedPrompt.contains(part))))
      throw new IllegalArgumentException("The operator decision must cite exact text from the selected immutable prompt version");
    if (decisionType.equals("CREATIVE_INTENT")
        && (!decisionId.equals("creative-intent") || !decision.equals("CONFIRMED")
            || !sourceEvidence.equals(savedPrompt)))
      throw new IllegalArgumentException("Creative intent confirmation requires review of the complete saved prompt");
    var payload = new LinkedHashMap<String, Object>(request);
    payload.put("contentId", String.valueOf(content));
    payload.put("promptVersionId", String.valueOf(version));
    payload.put("provenance", "OPERATOR_CONFIRMED");
    payload.put("savedAt", Instant.now().toString());
    payload.put("sourceFingerprint", sha256(savedPrompt));
    if (decisionType.equals("NO_TEXT_REPAIR_JUSTIFIED")) {
      String analysisRunId = String.valueOf(request.get("analysisRunId"));
      String binding = sha256(String.join("\n", String.valueOf(content), String.valueOf(version), decisionType,
          decisionId, analysisRunId, String.valueOf(payload.get("sourceFingerprint"))));
      jdbc.sql("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))")
          .param("key", binding)
          .query((rs, rowNum) -> Boolean.TRUE)
          .single();
      var existing = jdbc.sql("SELECT id,payload::text FROM post_family_workflow_events "
              + "WHERE kind='PRODUCTION_REVIEW_DECISION' AND payload->>'contentId'=:content "
              + "AND payload->>'promptVersionId'=:prompt AND payload->>'decisionType'=:type "
              + "AND payload->>'decisionId'=:decisionId AND payload->>'analysisRunId'=:analysis "
              + "AND payload->>'sourceFingerprint'=:fingerprint ORDER BY created_at,id LIMIT 1")
          .param("content", String.valueOf(content))
          .param("prompt", String.valueOf(version))
          .param("type", decisionType)
          .param("decisionId", decisionId)
          .param("analysis", analysisRunId)
          .param("fingerprint", String.valueOf(payload.get("sourceFingerprint")))
          .query((rs, ignored) -> {
            var saved = read(rs.getString(2));
            saved.put("recordId", rs.getString(1));
            return saved;
          })
          .optional();
      if (existing.isPresent()) return existing.get();
      payload.put("analysisBindingHash", analysis.get("bindingHash"));
      payload.put("operatorDecision", "NO_TEXT_REPAIR_JUSTIFIED");
      payload.put("justification", "No applicable canonical prompt-text failure was recorded; outstanding evidence remains unresolved.");
      payload.put("stale", false);
      payload.put("recordId", save("PRODUCTION_REVIEW_DECISION", binding, payload));
      return payload;
    }
    String binding = sha256(String.join("\n", String.valueOf(content), String.valueOf(version), decisionType, decisionId));
    payload.put("recordId", save("PRODUCTION_REVIEW_DECISION", binding, payload));
    return payload;
  }

  public Map<String, Object> getProductionReviewDecisions(Long contentId, Long promptVersionId) {
    var snapshot = prompts.load(contentId, promptVersionId);
    var rows = jdbc.sql("SELECT id,payload::text payload FROM post_family_workflow_events "
            + "WHERE kind='PRODUCTION_REVIEW_DECISION' AND payload->>'contentId'=:content "
            + "AND payload->>'promptVersionId'=:prompt ORDER BY created_at,id")
        .param("content", String.valueOf(contentId)).param("prompt", String.valueOf(promptVersionId))
        .query((rs, ignored) -> { var value = read(rs.getString("payload")); value.put("recordId", rs.getString("id")); return value; }).list();
    var latest = new LinkedHashMap<String, Object>();
    var latestReview = getLatestReview(contentId, promptVersionId);
    for (var row : rows) {
      if (!sha256(snapshot.promptText()).equals(row.get("sourceFingerprint"))) continue;
      if ("NO_TEXT_REPAIR_JUSTIFIED".equals(row.get("decisionType"))) {
        boolean stale = latestReview == null
            || !String.valueOf(row.get("analysisRunId")).equals(String.valueOf(latestReview.get("recordId")))
            || !String.valueOf(row.get("analysisBindingHash")).equals(String.valueOf(latestReview.get("bindingHash")));
        row.put("stale", stale);
        if (stale) row.put("staleReason", "A newer or different saved quality evaluation is current.");
      }
      latest.put(String.valueOf(row.get("decisionType")) + ":" + row.get("decisionId"), row);
    }
    return Map.of("contentId", contentId, "promptVersionId", promptVersionId,
        "decisions", List.copyOf(latest.values()));
  }

  private boolean hasActionableTextRepair(Map<String, Object> analysis) {
    var findings = maps(map(analysis.get("planQuality")).get("findings"));
    return findings.stream().anyMatch(finding -> {
      String scope = String.valueOf(finding.getOrDefault("scope",
          finding.getOrDefault("category", finding.getOrDefault("type", finding.getOrDefault("domain", "")))))
          .toUpperCase();
      String applicability = String.valueOf(finding.getOrDefault("applicability", "")).toUpperCase();
      String repairability = String.valueOf(finding.getOrDefault("repairability", "")).toUpperCase();
      return (scope.contains("PROMPT") || scope.contains("TEXT"))
          && Boolean.TRUE.equals(finding.get("repairable"))
          && !List.of("UNKNOWN", "NOT_APPLICABLE").contains(applicability)
          && !List.of("OPTIONAL", "NOT_REPAIRABLE").contains(repairability);
    });
  }

  public Map<String, Object> saveProductionReferenceBinding(Map<String, Object> request) {
    long contentId = Long.parseLong(String.valueOf(request.get("contentId")));
    long promptVersionId = Long.parseLong(String.valueOf(request.get("promptVersionId")));
    UUID characterId = UUID.fromString(String.valueOf(request.get("characterId")));
    UUID referenceId = UUID.fromString(String.valueOf(request.get("referenceId")));
    var version = jdbc.sql("SELECT raw_text FROM prompt_versions WHERE content_id=:content AND id=:version")
        .param("content", contentId).param("version", promptVersionId).query(String.class).optional()
        .orElseThrow(() -> new IllegalArgumentException("The selected immutable prompt version does not belong to this content"));
    var character = jdbc.sql("SELECT name FROM characters WHERE id=:id AND active=true")
        .param("id", characterId).query(String.class).optional()
        .orElseThrow(() -> new IllegalArgumentException("Character is not in the active canonical registry"));
    if (!java.util.regex.Pattern.compile("\\b" + java.util.regex.Pattern.quote(character) + "\\b", java.util.regex.Pattern.CASE_INSENSITIVE).matcher(version).find())
      throw new IllegalArgumentException("The selected character does not match the source prompt version");
    var asset = jdbc.sql("SELECT relative_path,description,sha256,approval_status,version_number FROM character_references WHERE id=:id AND character_id=:character")
        .param("id", referenceId).param("character", characterId)
        .query((rs, row) -> Map.of("relativePath", rs.getString("relative_path"), "description", rs.getString("description") == null ? "" : rs.getString("description"), "sha256", rs.getString("sha256") == null ? "" : rs.getString("sha256"), "status", rs.getString("approval_status"), "version", rs.getInt("version_number")))
        .optional().orElseThrow(() -> new IllegalArgumentException("Reference does not belong to the selected character"));
    if (!"APPROVED".equals(asset.get("status")) || String.valueOf(asset.get("sha256")).isBlank())
      throw new IllegalArgumentException("Only an approved reference with a verified hash can be bound");
    java.nio.file.Path root = java.nio.file.Path.of(workflowDataRoot).toAbsolutePath().normalize();
    java.nio.file.Path image = root.resolve(String.valueOf(asset.get("relativePath"))).normalize();
    if (!image.startsWith(root) || !java.nio.file.Files.isRegularFile(image))
      throw new IllegalArgumentException("Approved reference image is missing from local storage");
    try {
      String currentHash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(java.nio.file.Files.readAllBytes(image)));
      if (!currentHash.equals(asset.get("sha256"))) throw new IllegalArgumentException("Approved reference image hash changed; review and upload the image again");
    } catch (java.io.IOException | java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("Unable to verify approved character reference", error);
    }
    var payload = new LinkedHashMap<String, Object>();
    payload.put("contentId", String.valueOf(contentId)); payload.put("promptVersionId", String.valueOf(promptVersionId));
    payload.put("characterId", characterId.toString()); payload.put("character", character);
    payload.put("referenceId", referenceId.toString()); payload.put("relativePath", asset.get("relativePath"));
    payload.put("sha256", asset.get("sha256")); payload.put("version", asset.get("version"));
    payload.put("description", asset.get("description")); payload.put("approvalStatus", "APPROVED");
    payload.put("provenance", "CANONICAL_CHARACTER_REFERENCE_APPROVAL"); payload.put("savedAt", Instant.now().toString());
    String binding = sha256(String.join("\n", String.valueOf(contentId), String.valueOf(promptVersionId), referenceId.toString(), String.valueOf(asset.get("sha256"))));
    payload.put("recordId", save("PRODUCTION_CHARACTER_REFERENCE_BINDING", binding, payload));
    return payload;
  }

  public Map<String, Object> getProductionReferenceBinding(Long contentId, Long promptVersionId) {
    return jdbc.sql("SELECT id,payload::text payload FROM post_family_workflow_events WHERE kind='PRODUCTION_CHARACTER_REFERENCE_BINDING' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("content", String.valueOf(contentId)).param("prompt", String.valueOf(promptVersionId))
        .query((rs, row) -> { var result = read(rs.getString("payload")); result.put("recordId", rs.getString("id")); return result; })
        .optional().orElse(Map.of("contentId", contentId, "promptVersionId", promptVersionId, "status", "MISSING"));
  }

  /** Persist the review-only visual preparation artifact without invoking an image provider. */
  public Map<String, Object> saveVisualPreparation(Map<String, Object> request) {
    if (request.get("contentId") == null || request.get("promptVersionId") == null)
      throw new IllegalArgumentException("contentId and promptVersionId are required");
    String specification = String.valueOf(request.getOrDefault("firstFrameSpecification", "")).trim();
    String imagePrompt = String.valueOf(request.getOrDefault("firstFrameImagePrompt", "")).trim();
    if (specification.isBlank() || imagePrompt.isBlank())
      throw new IllegalArgumentException("First-frame specification and image prompt are required");
    long contentId = Long.parseLong(String.valueOf(request.get("contentId")));
    long promptVersionId = Long.parseLong(String.valueOf(request.get("promptVersionId")));
    var snapshot = prompts.load(contentId, promptVersionId);
    if (snapshot.contentId() != contentId || snapshot.promptVersionId() != promptVersionId)
      throw new IllegalArgumentException("Visual specification source identity does not match");
    if (request.get("reviewId") == null) throw new IllegalArgumentException("An exact saved analysis review is required");
    var review = get(UUID.fromString(String.valueOf(request.get("reviewId"))));
    if (!String.valueOf(contentId).equals(String.valueOf(review.get("contentId"))) || !String.valueOf(promptVersionId).equals(String.valueOf(review.get("promptVersionId"))))
      throw new IllegalArgumentException("Visual specification analysis belongs to another project or prompt");
    var payload = new LinkedHashMap<String, Object>(request);
    payload.put("promptHash", snapshot.promptSha256());
    payload.put("promptVersionNumber", snapshot.promptVersionNumber());
    payload.put("status", String.valueOf(request.getOrDefault("status", "READY_FOR_REVIEW")));
    payload.put("providerCallPerformed", false);
    payload.put("savedAt", Instant.now().toString());
    String binding = sha256(String.join("\n", String.valueOf(request.get("contentId")), String.valueOf(request.get("promptVersionId")), specification, imagePrompt));
    payload.put("bindingHash", binding);
    payload.put("recordId", save("VISUAL_PREPARATION", binding, payload));
    return payload;
  }

  public Map<String, Object> getVisualPreparation(Long contentId, Long promptVersionId) {
    return jdbc.sql("SELECT id,payload::text payload FROM post_family_workflow_events WHERE kind='VISUAL_PREPARATION' AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt ORDER BY created_at DESC LIMIT 1")
        .param("content", String.valueOf(contentId)).param("prompt", String.valueOf(promptVersionId))
        .query((rs, ignored) -> { var value = read(rs.getString("payload")); value.put("recordId", rs.getString("id")); return value; })
        .optional().orElseThrow(() -> new IllegalArgumentException("Visual preparation not found"));
  }

  /** Proxy to ML service start-frame generation endpoint. Resolves character reference image path. */
  public Map<String, Object> generateStartFrame(Map<String, Object> request) {
    if (request.get("contentId") == null || request.get("promptVersionId") == null)
      throw new IllegalArgumentException("contentId and promptVersionId are required");
    if (request.get("prompt") == null || String.valueOf(request.get("prompt")).isBlank())
      throw new IllegalArgumentException("prompt text is required");
    Object maxCost = request.getOrDefault("maxCostUsd", 0);
    if (!(maxCost instanceof Number) || ((Number) maxCost).doubleValue() <= 0)
      throw new IllegalArgumentException("maxCostUsd must be positive");
    
    // Resolve character reference image path from verified reference
    String characterId = String.valueOf(request.getOrDefault("characterId", ""));
    String referenceId = String.valueOf(request.getOrDefault("referenceId", ""));
    if (characterId.isBlank() || referenceId.isBlank())
      throw new IllegalArgumentException("characterId and referenceId are required for start-frame generation");
    
    UUID charUuid = UUID.fromString(characterId);
    UUID refUuid = UUID.fromString(referenceId);
    
    // Verify the reference exists and is approved
    var refRecord = jdbc.sql("SELECT relative_path,sha256,approval_status FROM character_references WHERE id=:ref AND character_id=:char")
        .param("ref", refUuid).param("char", charUuid)
        .query((rs, ignored) -> Map.of(
            "path", rs.getString("relative_path"),
            "sha", rs.getString("sha256"),
            "status", rs.getString("approval_status")))
        .optional().orElseThrow(() -> new IllegalArgumentException("Character reference not found"));
    
    if (!"VERIFIED".equals(refRecord.get("status")) && !"APPROVED".equals(refRecord.get("status")))
      throw new IllegalArgumentException("Character reference must be verified before generating start frame");
    
    // Resolve absolute image path
    String relativePath = (String) refRecord.get("path");
    Path dataRootPath = Path.of(workflowDataRoot);
    Path imagePath = dataRootPath.resolve(relativePath).normalize();
    if (!imagePath.startsWith(dataRootPath) || !Files.isRegularFile(imagePath))
      throw new IllegalArgumentException("Character reference image file not found");
    
    // Add resolved image path to request
    request.put("referenceImagePath", imagePath.toString());
    request.put("referenceSha256", refRecord.get("sha"));
    
    var result = ml.workflow("start-frame/generate", request);
    
    // Persist generated candidate in database
    if ("GENERATED".equals(result.get("status"))) {
      String candidateId = String.valueOf(result.get("candidateId"));
      String charId = String.valueOf(result.getOrDefault("characterId", ""));
      String refId = String.valueOf(result.getOrDefault("referenceId", ""));
      String refSha = String.valueOf(result.getOrDefault("referenceSha256", ""));
      String imgPath = String.valueOf(result.getOrDefault("imagePath", ""));
      String imgSha = String.valueOf(result.getOrDefault("sha256", ""));
      int width = ((Number) result.getOrDefault("width", 0)).intValue();
      int height = ((Number) result.getOrDefault("height", 0)).intValue();
      String model = String.valueOf(result.getOrDefault("model", ""));
      String quality = String.valueOf(result.getOrDefault("quality", "medium"));
      double cost = ((Number) result.getOrDefault("cost", 0.053)).doubleValue();
      
      UUID dbId = UUID.randomUUID();
      jdbc.sql(
          "INSERT INTO start_frame_candidates(id,content_id,prompt_version_id,candidate_id,character_id,reference_id,reference_sha256,image_path,image_sha256,width,height,model,quality,cost_usd,status) VALUES (:id,:content,:prompt,:candidate,:char,:ref,:refsha,:imgpath,:imgsha,:width,:height,:model,:quality,:cost,'CANDIDATE')")
          .param("id", dbId)
          .param("content", Long.valueOf(String.valueOf(request.get("contentId"))))
          .param("prompt", Long.valueOf(String.valueOf(request.get("promptVersionId"))))
          .param("candidate", candidateId)
          .param("char", UUID.fromString(charId))
          .param("ref", UUID.fromString(refId))
          .param("refsha", refSha)
          .param("imgpath", imgPath)
          .param("imgsha", imgSha)
          .param("width", width)
          .param("height", height)
          .param("model", model)
          .param("quality", quality)
          .param("cost", cost)
          .update();
      
      result.put("databaseId", dbId.toString());
    }
    
    return result;
  }

  /** List start-frame candidates for a content/prompt version. */
  public Map<String, Object> listStartFrameCandidates(Long contentId, Long promptVersionId) {
    var candidates = jdbc.sql(
        "SELECT id::text,candidate_id,character_id::text,reference_id::text,reference_sha256,image_path,image_sha256,width,height,model,quality,cost_usd,status,rejected_at,rejected_by,rejected_reason,accepted_at,accepted_by,created_at FROM start_frame_candidates WHERE content_id=:content AND prompt_version_id=:prompt ORDER BY created_at DESC")
        .param("content", contentId).param("prompt", promptVersionId)
        .query((rs, ignored) -> Map.<String, Object>ofEntries(
            java.util.Map.entry("id", rs.getString("id")),
            java.util.Map.entry("candidateId", rs.getString("candidate_id")),
            java.util.Map.entry("characterId", rs.getString("character_id")),
            java.util.Map.entry("referenceId", rs.getString("reference_id")),
            java.util.Map.entry("referenceSha256", rs.getString("reference_sha256")),
            java.util.Map.entry("imagePath", rs.getString("image_path")),
            java.util.Map.entry("imageSha256", rs.getString("image_sha256")),
            java.util.Map.entry("width", rs.getInt("width")),
            java.util.Map.entry("height", rs.getInt("height")),
            java.util.Map.entry("model", rs.getString("model")),
            java.util.Map.entry("quality", rs.getString("quality")),
            java.util.Map.entry("costUsd", rs.getBigDecimal("cost_usd").doubleValue()),
            java.util.Map.entry("status", rs.getString("status")),
            java.util.Map.entry("createdAt", rs.getTimestamp("created_at").toInstant().toString())))
        .list();
    return Map.of("contentId", contentId, "promptVersionId", promptVersionId, "candidates", candidates);
  }

  /** Accept a start-frame candidate. */
  public Map<String, Object> acceptStartFrame(Map<String, Object> request) {
    String id = String.valueOf(request.get("candidateId"));
    Long contentId = Long.valueOf(String.valueOf(request.get("contentId")));
    Long promptVersionId = Long.valueOf(String.valueOf(request.get("promptVersionId")));
    if (id == null || id.isBlank())
      throw new IllegalArgumentException("candidateId is required");
    
    var existing = jdbc.sql(
        "SELECT id::text,status FROM start_frame_candidates WHERE id::text=:id AND content_id=:content AND prompt_version_id=:prompt")
        .param("id", id).param("content", contentId).param("prompt", promptVersionId)
        .query((rs, ignored) -> Map.of("id", rs.getString("id"), "status", rs.getString("status")))
        .optional().orElseThrow(() -> new IllegalArgumentException("Start-frame candidate not found"));
    
    if ("ACCEPTED".equals(existing.get("status")))
      throw new IllegalArgumentException("Candidate already accepted");
    if ("REJECTED".equals(existing.get("status")))
      throw new IllegalArgumentException("Cannot accept a rejected candidate; generate a new one");
    
    jdbc.sql("UPDATE start_frame_candidates SET status='ACCEPTED',accepted_at=now(),accepted_by=:who WHERE id::text=:id")
        .param("id", id).param("who", "operator").update();
    
    return Map.of("status", "ACCEPTED", "candidateId", id, "contentId", contentId, "promptVersionId", promptVersionId);
  }

  /** Reject a start-frame candidate. */
  public Map<String, Object> rejectStartFrame(Map<String, Object> request) {
    String id = String.valueOf(request.get("candidateId"));
    Long contentId = Long.valueOf(String.valueOf(request.get("contentId")));
    Long promptVersionId = Long.valueOf(String.valueOf(request.get("promptVersionId")));
    if (id == null || id.isBlank())
      throw new IllegalArgumentException("candidateId is required");
    
    var existing = jdbc.sql(
        "SELECT id::text,status FROM start_frame_candidates WHERE id::text=:id AND content_id=:content AND prompt_version_id=:prompt")
        .param("id", id).param("content", contentId).param("prompt", promptVersionId)
        .query((rs, ignored) -> Map.of("id", rs.getString("id"), "status", rs.getString("status")))
        .optional().orElseThrow(() -> new IllegalArgumentException("Start-frame candidate not found"));
    
    if ("REJECTED".equals(existing.get("status")))
      throw new IllegalArgumentException("Candidate already rejected");
    if ("ACCEPTED".equals(existing.get("status")))
      throw new IllegalArgumentException("Cannot reject an accepted candidate");
    
    String reason = String.valueOf(request.getOrDefault("reason", ""));
    jdbc.sql("UPDATE start_frame_candidates SET status='REJECTED',rejected_at=now(),rejected_by='operator',rejected_reason=:reason WHERE id::text=:id")
        .param("id", id).param("reason", reason).update();
    
    return Map.of("status", "REJECTED", "candidateId", id, "contentId", contentId, "promptVersionId", promptVersionId);
  }

  /** Check if there's an accepted start frame for the given content/prompt version. */
  public boolean hasAcceptedStartFrame(Long contentId, Long promptVersionId) {
    return jdbc.sql("SELECT COUNT(*) FROM start_frame_candidates WHERE content_id=:content AND prompt_version_id=:prompt AND status='ACCEPTED'")
        .param("content", contentId).param("prompt", promptVersionId)
        .query(Integer.class).single() > 0;
  }

  public Map<String, Object> secondOpinion(UUID id, Map<String, Object> options) {
    var review = get(id);
    var result =
        new LinkedHashMap<>(
            ml.workflow(
                "critic",
                Map.of(
                    "request",
                    review.get("boundRequest"),
                    "provider",
                    String.valueOf(options.getOrDefault("provider", "deepseek")).toLowerCase(),
                    "model",
                    options.getOrDefault("model", ""))));
    result.put("reviewId", id.toString());
    result.put("bindingHash", review.get("bindingHash"));
    result.put(
        "recordId", save("SECOND_OPINION", String.valueOf(review.get("bindingHash")), result));
    return result;
  }

  public Map<String, Object> reviewLearning(UUID id, Map<String, Object> input) {
    var record = get(id);
    if (!List.of("PENDING_HUMAN_REVIEW", "APPROVED", "REJECTED")
        .contains(record.get("reviewStatus")))
      throw new IllegalArgumentException("Only pending learning records can be reviewed");
    if (!List.of("APPROVED", "REJECTED", "REVOKED").contains(input.get("decision"))
        || !(input.get("reason") instanceof String reason)
        || reason.isBlank())
      throw new IllegalArgumentException("Explicit decision and review reason required");
    var review = new LinkedHashMap<>(record);
    review.remove("recordId");
    review.put("parentRecordId", record.getOrDefault("parentRecordId", id.toString()));
    review.put("reviewStatus", input.get("decision"));
    review.put("reviewReason", input.get("reason"));
    review.put("reviewedAt", Instant.now().toString());
    review.put("automaticallyApplied", false);
    review.put("recordId", save("LEARNING_REVIEW", null, review));
    return review;
  }

  public List<Map<String, Object>> retrieveLessons(String profile, String model, double duration) {
    return retrieveLessons(profile, model, duration, Map.of());
  }

  public List<Map<String, Object>> retrieveLessons(
      String profile, String model, double duration, Map<String, Object> target) {
    if (!Double.isFinite(duration) || duration <= 0 || profile == null || model == null)
      return List.of();
    if (!target.isEmpty()
        && (!(target.get("generator") instanceof String generator)
            || generator.isBlank()
            || "AUTO".equals(generator))) return List.of();
    return jdbc
        .sql(
            """
            SELECT id,payload::text payload FROM (
              SELECT DISTINCT ON (payload->>'parentRecordId') id,payload,created_at
              FROM post_family_workflow_events WHERE kind='LEARNING_REVIEW'
              ORDER BY payload->>'parentRecordId',created_at DESC,id DESC
            ) latest WHERE payload->>'reviewStatus'='APPROVED'
              AND payload->>'contentProfile'=:profile AND payload->>'targetModelVersion'=:model
            ORDER BY created_at DESC LIMIT 100
            """)
        .param("profile", profile)
        .param("model", model)
        .query(
            (rs, ignored) -> {
              var result = read(rs.getString("payload"));
              result.put("recordId", rs.getString("id"));
              return result;
            })
        .list()
        .stream()
        .filter(
            lesson -> {
              if (!List.of("ACTUAL_EXECUTION", "PROMPT_FIX")
                  .contains(String.valueOf(lesson.get("lessonScope")))) return false;
              var range = lesson.get("durationRange");
              if (!(range instanceof List<?> values)
                  || values.size() != 2
                  || !(values.get(0) instanceof Number low)
                  || !(values.get(1) instanceof Number high)
                  || !Double.isFinite(low.doubleValue())
                  || !Double.isFinite(high.doubleValue())
                  || low.doubleValue() <= 0
                  || high.doubleValue() < low.doubleValue()
                  || duration < low.doubleValue()
                  || duration > high.doubleValue()) return false;
              if (!(lesson.get("sampleSize") instanceof Number size)
                  || size.intValue() < 1
                  || size.doubleValue() != size.intValue()) return false;
              if (!(lesson.get("evidenceBasis") instanceof List<?> evidence) || evidence.isEmpty())
                return false;
              var sources = new java.util.HashSet<String>();
              var references = new java.util.HashSet<String>();
              for (Object reference : evidence) {
                if (!references.add(String.valueOf(reference))) continue;
                try {
                  boolean repair = "PROMPT_FIX".equals(lesson.get("lessonScope"));
                  var record =
                      getByKind(
                          UUID.fromString(String.valueOf(reference)),
                          repair ? "REPAIR" : "ACTUAL_RENDER_QA");
                  String sourceReview;
                  if (repair) {
                    if (!(record.get("verificationPasses") instanceof Number count)
                        || count.intValue() <= 0) return false;
                    sourceReview =
                        jdbc.sql(
                                "SELECT s.payload->>'bestReviewId' FROM workflow_repair_sessions s"
                                    + " CROSS JOIN LATERAL"
                                    + " jsonb_array_elements(s.payload->'history') attempt WHERE"
                                    + " s.state='ACCEPTED' AND attempt->>'repairRecordId'=:repair"
                                    + " AND attempt->>'reviewId'=s.payload->>'bestReviewId' ORDER"
                                    + " BY s.updated_at DESC LIMIT 1")
                            .param("repair", String.valueOf(reference))
                            .query(String.class)
                            .optional()
                            .orElse(null);
                  } else {
                    if (!"USABLE".equals(record.get("viewerFacingUsability"))
                        || !"SOURCE_BOUND".equals(record.get("lineageStatus"))) return false;
                    sourceReview = (String) record.get("reviewId");
                  }
                  if (sourceReview == null) return false;
                  var review = getByKind(UUID.fromString(sourceReview), "REVIEW");
                  var generation = map(review.get("generation"));
                  var bound = map(review.get("boundRequest"));
                  Object evidenceDuration =
                      repair ? bound.get("desiredDuration") : record.get("duration");
                  if (!profile.equals(map(review.get("routing")).get("contentProfile"))
                      || !model.equals(generation.get("profileVersion"))
                      || !map(lesson.get("settings")).equals(map(generation.get("settings")))
                      || !(evidenceDuration instanceof Number sourceDuration)
                      || sourceDuration.doubleValue() < low.doubleValue()
                      || sourceDuration.doubleValue() > high.doubleValue()) return false;
                  if (!repair
                      && !java.util.Objects.equals(
                          record.get("bindingHash"), review.get("bindingHash"))) return false;
                  if (target.get("settings") instanceof Map<?, ?>
                      && !lessonSettings(target.get("settings"))
                          .equals(lessonSettings(generation.get("settings")))) return false;
                  if (target.get("generator") instanceof String generator
                      && !List.of("", "AUTO").contains(generator)
                      && !generator.equals(generation.get("selectedGenerator"))) return false;
                  String source =
                      repair
                          ? String.valueOf(review.get("contentId"))
                          : String.valueOf(record.get("videoId"));
                  if (source.equals("null")) return false;
                  if (!repair) {
                    if (!(record.get("assetHash") instanceof String hash)
                        || !hash.matches("[a-f0-9]{64}")) return false;
                    if (!jdbc.sql(
                            "SELECT EXISTS(SELECT 1 FROM videos WHERE id=:video AND"
                                + " content_hash=:hash)")
                        .param("video", UUID.fromString(source))
                        .param("hash", hash)
                        .query(Boolean.class)
                        .single()) return false;
                  }
                  sources.add(source);
                } catch (IllegalArgumentException | ClassCastException unavailable) {
                  return false;
                }
              }
              return sources.size() >= size.intValue();
            })
        .limit(5)
        .map(
            lesson -> {
              lesson.put(
                  "retrievalReason",
                  "Approved, source-bound evidence matches profile, model, settings and duration;"
                      + " latest review retained");
              return lesson;
            })
        .toList();
  }

  private static Map<String, Object> lessonSettings(Object value) {
    var settings = new LinkedHashMap<>(map(value));
    settings.remove(
        "startFrame"); // Asset identity stays source-bound; it is not a generation capability
    // setting.
    return settings;
  }

  public List<Map<String, Object>> verifiedReferences(Object value) {
    if (!(value instanceof List<?> references)) return List.of();
    var result = new ArrayList<Map<String, Object>>();
    for (Object item : references) {
      if (!(item instanceof Map<?, ?> reference))
        throw new IllegalArgumentException("Invalid reference");
      var verified = new LinkedHashMap<String, Object>();
      verified.put("character", reference.get("character"));
      verified.put("kind", reference.get("kind"));
      verified.put("relativePath", reference.get("relativePath"));
      try {
        if (!(reference.get("relativePath") instanceof String path))
          throw new IllegalArgumentException("Reference path required");
        var resolved = media.resolve(path);
        try (var stream = resolved.resource().getInputStream()) {
          byte[] bytes = stream.readNBytes(20 * 1024 * 1024 + 1);
          if (bytes.length > 20 * 1024 * 1024)
            throw new IllegalArgumentException("Reference exceeds 20 MiB");
          verified.put(
              "sha256",
              HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
          verified.put("status", "VERIFIED");
          verified.put("method", "OPERATOR_ASSOCIATED_LOCAL_ASSET");
        }
      } catch (Exception unavailable) {
        verified.put("sha256", null);
        verified.put("status", "UNKNOWN");
        verified.put("reason", "Referans dosyası yerel medya kökünde doğrulanamadı.");
      }
      result.add(verified);
    }
    return result;
  }

  public Map<String, Object> repair(UUID id, List<Map<String, Object>> patches) {
    var previous = get(id);
    if (((Number) previous.getOrDefault("repairPasses", 0)).intValue() != 0
        || jdbc.sql(
                    "SELECT COUNT(*) FROM post_family_workflow_events WHERE kind='REPAIR' AND"
                        + " payload->>'parentReviewId'=:parent")
                .param("parent", id.toString())
                .query(Long.class)
                .single()
            > 0)
      throw new IllegalArgumentException(
          "Only one repair is allowed for this review; save the final revision before a new"
              + " review");
    var result =
        new LinkedHashMap<>(
            ml.workflow(
                "repair",
                Map.of(
                    "request",
                    previous.get("boundRequest"),
                    "patches",
                    patches,
                    "repairPasses",
                    previous.getOrDefault("repairPasses", 0))));
    var changed = new LinkedHashMap<>(map(previous.get("boundRequest")));
    changed.put("prompt", result.get("finalPrompt"));
    result.put("boundRequest", changed);
    result.put("parentReviewId", id.toString());
    result.put("contentId", previous.get("contentId"));
    result.put("promptVersionId", previous.get("promptVersionId"));
    result.put("recordId", save("REPAIR", String.valueOf(result.get("bindingHash")), result));
    return result;
  }

  public Map<String, Object> actualQa(UUID id, Map<String, Object> input) {
    var review = get(id);
    if (!"impact-review-v1".equals(review.get("decisionPolicyVersion"))
        || Boolean.TRUE.equals(review.get("needsSavedPromptVersion")))
      throw new IllegalArgumentException(
          "Current source-bound impact review required; save/review changed intent first");
    return actualQaBound(review, id, input);
  }

  @org.springframework.transaction.annotation.Transactional
  public Map<String, Object> importEditedVariant(UUID videoId, Map<String, Object> input) {
    var original = videos.get(videoId);
    String path = String.valueOf(input.get("relativePath"));
    String reason = String.valueOf(input.getOrDefault("reason", ""));
    if (reason.isBlank() || original.relativePath().equals(path))
      throw new IllegalArgumentException("Distinct edited file and review reason are required");
    UUID parentId =
        input.get("parentVariantId") == null
            ? null
            : UUID.fromString(String.valueOf(input.get("parentVariantId")));
    if (parentId != null) variantService.get(videoId, parentId);
    var artifact = videos.ingest(path, null);
    if (artifact.id().equals(videoId))
      throw new IllegalArgumentException(
          "Edited file has original bytes; no new edited result exists");
    var operations =
        input.get("editOperations") instanceof List<?> list
            ? new ArrayList<Object>(list)
            : List.<Object>of();
    var existing =
        variantService.list(videoId).stream()
            .filter(variant -> variant.generatedPath().equals(path))
            .findFirst();
    var variant =
        existing.orElseGet(
            () ->
                variantService.create(
                    videoId,
                    parentId,
                    com.pompomhills.intelligence.video.VideoVariantType.CUSTOM_EDIT,
                    path,
                    operations));
    if (!java.util.Objects.equals(variant.parentVariantId(), parentId)
        || !variant.editOperations().equals(operations))
      throw new IllegalArgumentException(
          "Existing variant has different parent or edit provenance");
    var record = new LinkedHashMap<String, Object>();
    record.put("videoId", videoId.toString());
    record.put("variantId", variant.id().toString());
    record.put("parentVariantId", parentId);
    record.put("artifactVideoId", artifact.id().toString());
    record.put("relativePath", path);
    record.put("durationMs", artifact.durationMs());
    record.put(
        "artifactHash",
        jdbc.sql("SELECT content_hash FROM videos WHERE id=:id")
            .param("id", artifact.id())
            .query(String.class)
            .single());
    record.put(
        "originalHash",
        jdbc.sql("SELECT content_hash FROM videos WHERE id=:id")
            .param("id", videoId)
            .query(String.class)
            .single());
    record.put("editOperations", operations);
    record.put("operationVerification", "OPERATOR_REPORTED");
    record.put("fileVerification", "HASH_AND_METADATA_VERIFIED");
    record.put("reason", reason);
    record.put("recordId", save("EDIT_HANDOFF", null, record));
    return record;
  }

  public List<Map<String, Object>> editedHandoffs(UUID videoId) {
    videos.get(videoId);
    return jdbc.sql(
            """
            SELECT id,payload::text payload FROM post_family_workflow_events
            WHERE kind='EDIT_HANDOFF' AND (payload->>'videoId'=:video OR payload->>'artifactVideoId'=:video)
            ORDER BY created_at DESC
            """)
        .param("video", videoId.toString())
        .query(
            (rs, index) -> {
              Map<String, Object> value = new LinkedHashMap<>(read(rs.getString("payload")));
              value.put("recordId", rs.getObject("id", UUID.class).toString());
              return value;
            })
        .list();
  }

  public List<Map<String, Object>> actualQaRecords(UUID videoId) {
    videos.get(videoId);
    return jdbc.sql(
            "SELECT id,payload::text payload FROM post_family_workflow_events WHERE"
                + " kind='ACTUAL_RENDER_QA' AND payload->>'videoId'=:video AND"
                + " payload->>'lineageStatus'='UNAVAILABLE' ORDER BY created_at DESC LIMIT 1")
        .param("video", videoId.toString())
        .query(
            (rs, ignored) -> {
              var result = read(rs.getString("payload"));
              result.put("recordId", rs.getString("id"));
              return result;
            })
        .list();
  }

  public Map<String, Object> actualQaWithoutPlan(UUID videoId, Map<String, Object> input) {
    var video = videos.get(videoId);
    var request = new LinkedHashMap<>(input);
    request.put("relativePath", video.relativePath());
    var plan = new LinkedHashMap<String, Object>();
    try {
      String identity = "actual-only:" + videoId + ":" + UUID.randomUUID();
      plan.put(
          "bindingHash",
          HexFormat.of()
              .formatHex(
                  MessageDigest.getInstance("SHA-256")
                      .digest(identity.getBytes(java.nio.charset.StandardCharsets.UTF_8))));
    } catch (java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("Actual-only binding could not be created", error);
    }
    plan.put("lineageStatus", "UNAVAILABLE");
    plan.put("decisionPolicyVersion", "impact-review-v1");
    return actualQaBound(plan, null, request);
  }

  private Map<String, Object> actualQaBound(
      Map<String, Object> review, UUID id, Map<String, Object> input) {
    String path = String.valueOf(input.get("relativePath"));
    var video = videos.ingest(path, null);
    var analysis = videoMl.analyse(path, VideoService.CURRENT_ANALYSIS_VERSION, Map.of(), false);
    var observed = new LinkedHashMap<>(map(input.get("observation")));
    observed.put("bindingHash", review.get("bindingHash"));
    observed.put("assetHash", analysis.metadata().sha256());
    observed.put("duration", analysis.metadata().durationMs() / 1000.0);
    observed.put(
        "technicalAnalysis",
        json.convertValue(analysis, new TypeReference<Map<String, Object>>() {}));
    double actualDuration = analysis.metadata().durationMs() / 1000.0;
    if (observed.get("coverage") instanceof List<?> coverage
        && coverage.size() == 2
        && coverage.get(0) instanceof Number start
        && coverage.get(1) instanceof Number end)
      observed.put(
          "coverage",
          List.of(Math.max(0, start.doubleValue()), Math.min(actualDuration, end.doubleValue())));
    boolean humanReviewed = Boolean.TRUE.equals(input.get("humanReviewed"));
    boolean stillsReviewed = Boolean.TRUE.equals(input.get("stillsReviewed"));
    observed.put(
        "events",
        maps(observed.get("events")).stream()
            .map(item -> checkedObservation(item, humanReviewed, stillsReviewed, path, video.id()))
            .toList());
    observed.put(
        "defects",
        maps(observed.get("defects")).stream()
            .map(item -> checkedObservation(item, humanReviewed, stillsReviewed, path, video.id()))
            .toList());
    var experience = new LinkedHashMap<String, Object>();
    for (var entry : map(observed.get("experience")).entrySet())
      experience.put(
          entry.getKey(),
          checkedObservation(
              map(entry.getValue()), humanReviewed, stillsReviewed, path, video.id()));
    observed.put("experience", experience);
    observed.put(
        "repairProposal",
        checkedObservation(
            map(observed.get("repairProposal")), humanReviewed, stillsReviewed, path, video.id()));
    // Intent comes only from the immutable pre-render review, never from observation input.
    var requirements = maps(review.get("intentRequirements"));
    List<Map<String, Object>> events = new ArrayList<>();
    for (var beat :
        maps(map(map(review.get("productionEvidence")).get("videoPlanIR")).get("beats"))) {
      String level = "UNCLASSIFIED";
      for (var requirement : requirements) {
        if ("SOURCE_SUPPORTED".equals(requirement.get("status"))
            && requirement.get("eventIds") instanceof List<?> ids
            && ids.contains(beat.get("id"))) {
          String candidate = String.valueOf(requirement.get("level"));
          if ("ESSENTIAL".equals(candidate)
              || "UNCLASSIFIED".equals(level)
              || "FLEXIBLE".equals(candidate) && !"ESSENTIAL".equals(level)) level = candidate;
        }
      }
      events.add(
          Map.of(
              "id",
              beat.get("id"),
              "start",
              beat.get("startTime"),
              "end",
              beat.get("endTime"),
              "description",
              beat.get("action"),
              "requiresMotion",
              true,
              "intentLevel",
              level));
    }
    var plan = new LinkedHashMap<String, Object>();
    plan.put("bindingHash", review.get("bindingHash"));
    plan.put("events", events);
    plan.put("intentRequirements", requirements);
    plan.put("planQuality", review.get("planQuality"));
    plan.put("executionRisk", review.get("executionRisk"));
    plan.put("decisionPolicyVersion", review.get("decisionPolicyVersion"));
    if (id == null) plan.put("lineageStatus", "UNAVAILABLE");
    var qa =
        ml.workflow(
            "feedback",
            Map.of(
                "kind",
                "ACTUAL_RENDER_QA",
                "payload",
                Map.of("plan", plan, "observation", observed)));
    qa.put("reviewId", id == null ? null : id.toString());
    qa.put("lineageStatus", id == null ? "UNAVAILABLE" : "SOURCE_BOUND");
    qa.put("videoId", video.id().toString());
    qa.put("duration", actualDuration);
    qa.put("relativePath", path);
    qa.put("recordId", save("ACTUAL_RENDER_QA", String.valueOf(review.get("bindingHash")), qa));
    return qa;
  }

  static Map<String, Object> checkedObservation(
      Map<String, Object> item,
      boolean reviewed,
      boolean stillsReviewed,
      String path,
      UUID videoId) {
    var bound = new LinkedHashMap<>(item);
    if (videoId.toString().equals(item.get("reference"))
        && item.get("start") instanceof Number start
        && item.get("end") instanceof Number end
        && Double.isFinite(start.doubleValue())
        && Double.isFinite(end.doubleValue())
        && start.doubleValue() >= 0
        && end.doubleValue() > start.doubleValue()) {
      bound.put("reference", path + "#t=" + start.doubleValue() + "-" + end.doubleValue());
    }
    return checkedObservation(bound, reviewed, stillsReviewed, path);
  }

  static Map<String, Object> checkedObservation(
      Map<String, Object> item, boolean reviewed, String path) {
    return checkedObservation(item, reviewed, false, path);
  }

  static Map<String, Object> checkedObservation(
      Map<String, Object> item, boolean reviewed, boolean stillsReviewed, String path) {
    var checked = new LinkedHashMap<>(item);
    boolean clip = reviewed && "HUMAN_REVIEWED_CLIP".equals(item.get("evidenceBasis"));
    boolean stills =
        stillsReviewed
            && "DENSE_LOCAL_FRAMES".equals(item.get("evidenceBasis"))
            && Boolean.FALSE.equals(item.get("requiresMotion"));
    boolean bound = item.get("reference") instanceof String ref && ref.startsWith(path + "#t=");
    if ((!clip && !stills) || !bound) {
      checked.put("evidenceBasis", "SAMPLED_STILLS");
      checked.put("state", "UNKNOWN");
      checked.put("value", "UNKNOWN");
      checked.put("confidence", "UNKNOWN");
    }
    checked.put("assetEvidenceBinding", path);
    checked.put(
        "reviewerMethod",
        clip
            ? "OPERATOR_CLIP_ATTESTATION"
            : stills && bound ? "OPERATOR_STATIC_FRAME_ATTESTATION" : "UNVERIFIED");
    return checked;
  }

  public Map<String, Object> feedback(String kind, Map<String, Object> payload) {
    if (!List.of("MEASUREMENT", "COHORT", "ASSOCIATION").contains(kind))
      throw new IllegalArgumentException("Unknown feedback kind");
    if ("ASSOCIATION".equals(kind)) {
      if (!(payload.get("platformContentId") instanceof String identifier) || identifier.isBlank())
        throw new IllegalArgumentException("Platform ID must be a lossless string");
      var candidates =
          jdbc.sql(
                  "SELECT id,payload::text payload FROM post_family_workflow_events WHERE"
                      + " kind='ASSOCIATION' AND payload->>'platform'=:platform AND"
                      + " payload->>'platformContentId'=:publication ORDER BY created_at")
              .param("platform", payload.get("platform"))
              .param("publication", identifier)
              .query(
                  (rs, ignored) -> {
                    var row = read(rs.getString("payload"));
                    row.put("recordId", rs.getString("id"));
                    return row;
                  })
              .list();
      if (payload.get("videoId") != null) {
        if (!(payload.get("reviewReason") instanceof String reason) || reason.isBlank())
          throw new IllegalArgumentException("Manual association requires a review reason");
        UUID videoId = UUID.fromString(String.valueOf(payload.get("videoId")));
        boolean exists =
            jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
                .param("id", videoId)
                .query(Boolean.class)
                .single();
        if (!exists) throw new IllegalArgumentException("Local video not found");
        if (payload.get("qaRecordId") != null) {
          var actual = get(UUID.fromString(String.valueOf(payload.get("qaRecordId"))));
          if (!"ACTUAL_RENDER_QA".equals(actual.get("stage"))
              || !videoId.toString().equals(String.valueOf(actual.get("videoId")))
              || (payload.get("reviewId") != null
                  && !payload.get("reviewId").equals(actual.get("reviewId"))))
            throw new IllegalArgumentException(
                "Publication lineage does not match the observed actual video");
        }
        var record = new LinkedHashMap<>(payload);
        boolean conflict =
            candidates.stream()
                .anyMatch(
                    candidate ->
                        !videoId.toString().equals(String.valueOf(candidate.get("videoId"))));
        record.put("status", conflict ? "AMBIGUOUS" : "MANUAL_REVIEWED");
        record.put("candidatesBefore", candidates);
        record.put("recordId", save("ASSOCIATION", null, record));
        return record;
      }
      return ml.workflow(
          "feedback",
          Map.of(
              "kind",
              kind,
              "payload",
              Map.of(
                  "platform",
                  payload.get("platform"),
                  "platformContentId",
                  identifier,
                  "associations",
                  candidates)));
    }
    var measured = new LinkedHashMap<>(payload);
    if ("MEASUREMENT".equals(kind)) {
      if (map(payload.get("observation")).get("associationRecordId") != null) {
        var association =
            get(
                UUID.fromString(
                    String.valueOf(map(payload.get("observation")).get("associationRecordId"))));
        if (!List.of("MANUAL_REVIEWED", "MATCHED").contains(association.get("status")))
          throw new IllegalArgumentException("Measurement association requires resolved lineage");
        measured.put("association", association);
      }
      measured.put("entryProvenance", "OPERATOR_ENTERED");
      var raw = new LinkedHashMap<>(map(measured.get("observation")));
      raw.put("sourceHashVerification", "UNVERIFIED_OPERATOR_SOURCE");
      raw.put("entryProvenance", "OPERATOR_ENTERED");
      measured.put("observation", raw);
    }
    var result =
        new LinkedHashMap<>(ml.workflow("feedback", Map.of("kind", kind, "payload", measured)));
    if ("MEASUREMENT".equals(kind)) {
      var dimensions = new LinkedHashMap<String, Object>();
      for (String key :
          List.of("promptPlanQuality", "generatorExecutionRisk", "actualRenderQuality"))
        dimensions.put(key, Map.of("status", "NOT_JOINED"));
      var association = map(measured.get("association"));
      if (association.get("qaRecordId") != null) {
        var fixed = get(UUID.fromString(String.valueOf(association.get("qaRecordId"))));
        dimensions.putAll(map(fixed.get("reviewDimensions")));
        result.put("fixedReviewRecordId", fixed.get("recordId"));
        result.put("reviewFixedBeforeOutcomeJoin", true);
      }
      dimensions.put("audienceDistributionOutcome", new LinkedHashMap<>(result));
      result.put("reviewDimensions", dimensions);
      result.put("association", association);
    }
    result.put("recordId", save(kind, null, result));
    return result;
  }

  public Map<String, Object> lesson(String kind, Map<String, Object> value) {
    if (!List.of("LESSON", "EXPERIMENT").contains(kind))
      throw new IllegalArgumentException("Unknown lesson kind");
    for (String field :
        List.of(
            "hypothesis",
            "evidenceBasis",
            "sampleSize",
            "targetModelVersion",
            "settings",
            "contentProfile",
            "durationRange",
            "observedResult",
            "counterexamples"))
      if (!value.containsKey(field)) throw new IllegalArgumentException("Required field: " + field);
    var record = new LinkedHashMap<>(value);
    record.putIfAbsent("lessonScope", "UNKNOWN");
    record.put("reviewStatus", "PENDING_HUMAN_REVIEW");
    record.put("automaticallyApplied", false);
    record.put("recordId", save(kind, null, record));
    return record;
  }

  public Map<String, Object> getByKind(UUID id, String kind) {
    if (!jdbc.sql(
            "SELECT EXISTS(SELECT 1 FROM post_family_workflow_events WHERE id=:id AND kind=:kind)")
        .param("id", id)
        .param("kind", kind)
        .query(Boolean.class)
        .single()) throw new IllegalArgumentException("Workflow record kind mismatch");
    return get(id);
  }

  /** Read-only parser projection of the exact saved review source, never a revalidation. */
  public Map<String, Object> sourcePlan(UUID id) {
    var review = getByKind(id, "REVIEW");
    var source = map(review.get("source"));
    String prompt = String.valueOf(review.getOrDefault("originalPrompt", ""));
    if (prompt.isBlank() || !sha256(prompt).equals(source.get("sha256")))
      throw new IllegalArgumentException("Saved review source hash does not match its prompt");
    var result = new LinkedHashMap<>(ml.workflow("source-plan", Map.of(
        "prompt", prompt, "sourceId", String.valueOf(source.get("artifact")),
        "sourceVersion", String.valueOf(source.get("version")))));
    if (!source.get("sha256").equals(map(result.get("source")).get("sha256"))
        || !"READ_ONLY_SOURCE_EXTRACTION".equals(result.get("kind")))
      throw new IllegalArgumentException("Source extraction is not bound to the saved prompt");
    result.put("historicalRunId", id.toString());
    return result;
  }

  public Map<String, Object> get(UUID id) {
    var text =
        jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE id=:id")
            .param("id", id)
            .query(String.class)
            .optional()
            .orElseThrow(() -> new IllegalArgumentException("Workflow record not found"));
    var result = read(text);
    result.put("recordId", id.toString());
    return result;
  }

  /** Load the latest REVIEW record for a given content/prompt version. */
  public Map<String, Object> getLatestReview(Object contentId, Object promptVersionId) {
    String content = String.valueOf(contentId);
    String prompt = String.valueOf(promptVersionId);
    var text = jdbc.sql(
            "SELECT id, payload::text FROM post_family_workflow_events WHERE kind='REVIEW'"
                + " AND payload->>'contentId'=:content AND payload->>'promptVersionId'=:prompt"
                + " ORDER BY created_at DESC, id DESC LIMIT 1")
        .param("content", content)
        .param("prompt", prompt)
        .query((rs, ignored) -> {
          var result = read(rs.getString("payload"));
          result.put("recordId", rs.getString("id"));
          return result;
        })
        .optional()
        .orElse(null);
    return text;
  }

  public List<Map<String, Object>> list(String kind) {
    return list(kind, null, null, null);
  }

  public List<Map<String, Object>> list(
      String kind, String contentId, String promptVersionId, String bindingHash) {
    return jdbc.sql(
            "SELECT id,created_at,payload::text payload FROM post_family_workflow_events WHERE kind=:kind"
                + " AND (CAST(:content AS text) IS NULL OR payload->>'contentId'=:content)"
                + " AND (CAST(:prompt AS text) IS NULL OR payload->>'promptVersionId'=:prompt)"
                + " AND (CAST(:binding AS text) IS NULL OR payload->>'bindingHash'=:binding)"
                + " ORDER BY created_at DESC LIMIT 200")
        .param("content", contentId, java.sql.Types.VARCHAR)
        .param("prompt", promptVersionId, java.sql.Types.VARCHAR)
        .param("binding", bindingHash, java.sql.Types.VARCHAR)
        .param("kind", kind)
        .query(
            (rs, ignored) -> {
              var result = read(rs.getString("payload"));
              result.put("recordId", rs.getString("id"));
              result.put("createdAt", rs.getObject("created_at", java.time.OffsetDateTime.class).toInstant().toString());
              var lifecycle = latestLifecycle(UUID.fromString(rs.getString("id")));
              result.put("lifecycleStatus", lifecycle.getOrDefault("status", inferredLifecycle(result)));
              if (lifecycle.containsKey("reason")) result.put("lifecycleReason", lifecycle.get("reason"));
              if (lifecycle.containsKey("title")) result.put("title", lifecycle.get("title"));
              if (lifecycle.containsKey("changedAt")) result.put("lifecycleChangedAt", lifecycle.get("changedAt"));
              return result;
            })
        .list();
  }

  private Map<String, Object> latestLifecycle(UUID targetId) {
    return jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_LIFECYCLE' AND payload->>'targetRecordId'=:target ORDER BY created_at DESC,id DESC LIMIT 1")
        .param("target", targetId.toString()).query(String.class).optional().map(this::read).orElse(Map.of());
  }

  private String inferredLifecycle(Map<String, Object> record) {
    if ("STORY_APPROVAL".equals(record.get("role")) || "APPROVED".equals(record.get("status"))) return "APPROVED";
    if ("STORY".equals(record.get("role")) && record.get("recordId") != null) {
      if (hasExactStoryApproval(record)) return "APPROVED";
    }
    if ("BUILD_PROMPT".equals(record.get("role")) || record.containsKey("prompt")) return "DRAFT";
    return "DRAFT";
  }

  @Transactional
  public Map<String, Object> changeLifecycle(UUID id, Map<String, Object> request) {
    var record = get(id);
    String requested = String.valueOf(request.getOrDefault("status", "")).trim().toUpperCase(java.util.Locale.ROOT);
    if (!List.of("DRAFT", "IN_REVIEW", "APPROVED", "ARCHIVED", "DELETED").contains(requested))
      throw new IllegalArgumentException("Unsupported lifecycle status");
    var previousLifecycle = latestLifecycle(id);
    String current = String.valueOf(previousLifecycle.getOrDefault("status", inferredLifecycle(record)));
    if ("ARCHIVED".equals(current) && "DRAFT".equals(requested)) {
      String restoreTo = String.valueOf(previousLifecycle.getOrDefault("previousStatus", "DRAFT"));
      if (List.of("DRAFT", "IN_REVIEW", "APPROVED").contains(restoreTo)) requested = restoreTo;
    }
    if ("DELETED".equals(requested)) {
      if ("APPROVED".equals(current) || hasProtectedReferences(id, record))
        throw new IllegalStateException("This record is referenced by approved or downstream evidence. Archive it instead of deleting it.");
    }
    if ("APPROVED".equals(requested) && !"STORY_APPROVAL".equals(record.get("role"))
        && !("STORY".equals(record.get("role")) && hasExactStoryApproval(record)))
      throw new IllegalArgumentException("Only an explicit story approval can create APPROVED lifecycle state");
    var event = new LinkedHashMap<String, Object>();
    event.put("targetRecordId", id.toString()); event.put("targetKind", "CREATIVE_ROLE");
    event.put("status", requested); event.put("previousStatus", current);
    event.put("reason", request.getOrDefault("reason", "Operator lifecycle action"));
    if (request.get("title") != null) event.put("title", String.valueOf(request.get("title")));
    event.put("changedAt", Instant.now().toString());
    event.put("recordId", save("CREATIVE_STUDIO_LIFECYCLE", id.toString(), event));
    return Map.of("targetRecordId", id.toString(), "status", requested, "previousStatus", current, "changedAt", event.get("changedAt"), "recordId", event.get("recordId"));
  }

  private boolean hasExactStoryApproval(Map<String, Object> story) {
    Object rawId = story.get("recordId");
    if (rawId == null) return false;
    UUID storyId;
    try { storyId = UUID.fromString(String.valueOf(rawId)); }
    catch (IllegalArgumentException ignored) { return false; }
    var source = getByKind(storyId, "CREATIVE_ROLE");
    var approvals = jdbc.sql("SELECT payload::text FROM post_family_workflow_events WHERE kind='STORY_APPROVAL' AND payload->>'storyRecordId'=:id ORDER BY created_at DESC")
        .param("id", storyId.toString()).query(String.class).list();
    for (String jsonPayload : approvals) {
      var approval = read(jsonPayload);
      String candidateId = String.valueOf(approval.getOrDefault("candidateId", "")).trim();
      String revisionId = String.valueOf(approval.getOrDefault("revisionId", "")).trim();
      String fingerprint = String.valueOf(approval.getOrDefault("contentFingerprint", "")).trim();
      String approvedText = String.valueOf(approval.getOrDefault("approvedText", "")).trim();
      String candidateText = storyCandidateText(source, storyId, candidateId);
      if (candidateText != null && !approvedText.isBlank() && approvedText.equals(candidateText.trim())) {
        String expected = storyFingerprint(approvedText);
        if (expected.equals(fingerprint) && (candidateId + "-revision-" + expected).equals(revisionId)) return true;
      }
    }
    return false;
  }

  private boolean hasStoryApproval(UUID storyId, String candidateId, String revisionId, String approvalRecordId) {
    var approvals = jdbc.sql("SELECT id,payload::text FROM post_family_workflow_events WHERE kind='STORY_APPROVAL' AND payload->>'storyRecordId'=:id ORDER BY created_at DESC")
        .param("id", storyId.toString()).query((rs, row) -> Map.of("id", rs.getString("id"), "payload", rs.getString("payload"))).list();
    for (var row : approvals) {
      if (!approvalRecordId.isBlank() && !approvalRecordId.equals(row.get("id"))) continue;
      var approval = read(String.valueOf(row.get("payload")));
      if (!candidateId.equals(String.valueOf(approval.getOrDefault("candidateId", "")))
          || !revisionId.equals(String.valueOf(approval.getOrDefault("revisionId", "")))) continue;
      String text = String.valueOf(approval.getOrDefault("approvedText", "")).trim();
      String fingerprint = String.valueOf(approval.getOrDefault("contentFingerprint", "")).trim();
      if (!text.isBlank() && fingerprint.equals(storyFingerprint(text))
          && revisionId.equals(candidateId + "-revision-" + fingerprint)) return true;
    }
    return false;
  }

  private boolean hasProtectedReferences(UUID id, Map<String, Object> record) {
    String idText = id.toString();
    return jdbc.sql("SELECT EXISTS(SELECT 1 FROM post_family_workflow_events WHERE kind NOT IN ('CREATIVE_STUDIO_SESSION','CREATIVE_STUDIO_LIFECYCLE') AND id<>:id AND payload::text LIKE :needle)")
        .param("id", id).param("needle", "%" + idText + "%").query(Boolean.class).single();
  }

  @Transactional
  public Map<String, Object> duplicateCreativeRole(UUID id) {
    var source = getByKind(id, "CREATIVE_ROLE");
    if (!"STORY".equals(source.get("role"))) throw new IllegalArgumentException("Only a saved story can be duplicated");
    var copy = new LinkedHashMap<String, Object>(source);
    copy.remove("recordId"); copy.remove("createdAt"); copy.put("sourceRecordId", id.toString());
    copy.put("lifecycleStatus", "DRAFT"); copy.put("duplicatedAt", Instant.now().toString());
    copy.put("title", String.valueOf(copy.getOrDefault("title", "Saved story")) + " (Copy)");
    var result = new LinkedHashMap<String, Object>(); result.put("role", "STORY"); result.put("sourceRecordId", id.toString());
    result.put("alternatives", map(source.get("result")).getOrDefault("alternatives", List.of())); result.put("title", copy.get("title"));
    copy.put("result", result); copy.put("recordId", save("CREATIVE_ROLE", null, copy));
    return copy;
  }

  private UUID save(String kind, String binding, Map<String, Object> value) {
    UUID id = UUID.randomUUID();
    value.putIfAbsent("createdAt", java.time.Instant.now().toString());
    try {
      jdbc.sql(
              "INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload)"
                  + " VALUES(:id,:kind,:binding,CAST(:payload AS jsonb))")
          .param("id", id)
          .param("kind", kind)
          .param("binding", binding)
          .param("payload", json.writeValueAsString(value))
          .update();
      return id;
    } catch (org.springframework.dao.DataIntegrityViolationException error) {
      throw error;
    } catch (Exception error) {
      throw new IllegalStateException("Cannot persist workflow event", error);
    }
  }

  private static String sha256(String value) {
    try {
      return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    } catch (java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("SHA-256 is unavailable", error);
    }
  }

  private Map<String, Object> read(String text) {
    try {
      return json.readValue(text, new TypeReference<Map<String, Object>>() {});
    } catch (Exception error) {
      throw new IllegalStateException("Stored workflow payload invalid", error);
    }
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> map(Object value) {
    return value instanceof Map<?, ?> ? (Map<String, Object>) value : Map.of();
  }

  @SuppressWarnings("unchecked")
  private static List<Map<String, Object>> maps(Object value) {
    return value instanceof List<?> ? (List<Map<String, Object>>) value : List.of();
  }

  public static void requireAuthorized(Map<String, Object> review, String bindingHash) {
    if ("EDITORIAL_ASSESSMENT_ONLY".equals(review.get("authorizationScope")))
      throw new IllegalStateException("Editorial candidate is not render admission evidence");
    var authorization = map(map(review.get("family8")).get("renderAuthorization"));
    if (!"AUTHORIZED".equals(authorization.get("status"))
        || !bindingHash.equals(review.get("bindingHash"))
        || Boolean.TRUE.equals(review.get("needsSavedPromptVersion")))
      throw new IllegalStateException(
          "Post-family evidence is pending, stale or not canonically AUTHORIZED");
  }

  public record ReviewRequest(
      Long contentId,
      Long promptVersionId,
      String prompt,
      String sourcePath,
      Map<String, Object> options) {}
}
