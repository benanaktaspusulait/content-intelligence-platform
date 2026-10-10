package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.quality.ValidationEvidenceService;
import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

/** Append-only operational adapters over existing prompt, media and ML services. */
@Service
public class WorkflowService {
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
    var fresh =
        runReview(
            new ReviewRequest(
                ((Number) stored.get("contentId")).longValue(),
                ((Number) stored.get("promptVersionId")).longValue(),
                null,
                null,
                map(stored.get("boundRequest"))),
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

  public Map<String, Object> creativeRole(Map<String, Object> request) {
    String role = String.valueOf(request.get("role"));
    if (!List.of("STORY", "STORY_REVIEW", "BUILD_PROMPT", "MINIMAL_REPAIR").contains(role))
      throw new IllegalArgumentException("Unsupported creative role");
    if (map(request.get("context")).get("sourceStoryRecordId") instanceof String storyId
        && !storyId.isBlank() && !"MANUAL_STORY".equals(storyId)) {
      var story = getByKind(UUID.fromString(storyId), "CREATIVE_ROLE");
      if (!"STORY".equals(story.get("role")))
        throw new IllegalArgumentException("Story provenance requires an exact STORY record");
    }
    var verifiedRequest = new LinkedHashMap<>(request);
    var context = new LinkedHashMap<>(map(request.get("context")));
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
    Map<String, Object> workflowResponse;
    try {
      workflowResponse = ml.workflow("creative-role", verifiedRequest);
    } catch (RuntimeException error) {
      String detail = error.getMessage() == null ? "The ML service rejected the request" : error.getMessage();
      throw new IllegalStateException("Creative role request failed: " + detail, error);
    }
    var result = new LinkedHashMap<>(workflowResponse);
    result.put("retrievedLessons", lessons);
    result.put("sourceStoryRecordId", context.get("sourceStoryRecordId"));
    result.put("sourceRequest", verifiedRequest);
    result.put("validationStatus", "NOT_VALIDATED");
    result.put("recordId", save("CREATIVE_ROLE", null, result));
    return result;
  }

  public Map<String, Object> approveStory(UUID storyRecordId, Map<String, Object> request) {
    var story = getByKind(storyRecordId, "CREATIVE_ROLE");
    if (!"STORY".equals(story.get("role")))
      throw new IllegalArgumentException("Only a STORY role record can be approved");
    String approvedText = String.valueOf(request.getOrDefault("approvedText", "")).trim();
    if (approvedText.isBlank()) throw new IllegalArgumentException("approvedText is required");
    var approval = new LinkedHashMap<String, Object>();
    approval.put("role", "STORY_APPROVAL");
    approval.put("storyRecordId", storyRecordId.toString());
    approval.put("approvedText", approvedText);
    approval.put("candidateId", request.get("candidateId"));
    approval.put("revisionId", request.get("revisionId"));
    approval.put("contentFingerprint", request.get("contentFingerprint"));
    approval.put("reviewRecordId", request.get("reviewRecordId"));
    approval.put("originalStory", story.get("result"));
    approval.put("approvedAt", java.time.Instant.now().toString());
    approval.put("recordId", save("STORY_APPROVAL", storyRecordId.toString(), approval));
    return approval;
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
    var payload = new LinkedHashMap<String, Object>(request);
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

  public List<Map<String, Object>> list(String kind) {
    return list(kind, null, null, null);
  }

  public List<Map<String, Object>> list(
      String kind, String contentId, String promptVersionId, String bindingHash) {
    return jdbc.sql(
            "SELECT id,payload::text payload FROM post_family_workflow_events WHERE kind=:kind"
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
              return result;
            })
        .list();
  }

  private UUID save(String kind, String binding, Map<String, Object> value) {
    UUID id = UUID.randomUUID();
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
