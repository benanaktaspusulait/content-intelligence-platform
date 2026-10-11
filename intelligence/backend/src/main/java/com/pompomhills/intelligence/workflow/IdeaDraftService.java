package com.pompomhills.intelligence.workflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import com.pompomhills.intelligence.video.VideoService;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Free operator drafts using the existing append-only studio session store. */
@Service
public class IdeaDraftService {
  private final JdbcClient jdbc;
  private final ObjectMapper json;
  private final VideoService videos;
  private final ContentWorkspaceController contents;
  private static final List<String> FIELDS =
      List.of(
          "inputMode",
          "idea",
          "storyText",
          "promptText",
          "sourceTexts",
          "title",
          "workspacePath",
          "mainCharacterId",
          "profile",
          "storyMode",
          "preferences",
          "lockedRequirements",
          "duration",
          "durationPreset",
          "aspectRatio",
          "candidateCount",
          "targetGenerator",
          "constraints");

  public IdeaDraftService(
      JdbcClient jdbc,
      ObjectMapper json,
      VideoService videos,
      ContentWorkspaceController contents) {
    this.jdbc = jdbc;
    this.json = json;
    this.videos = videos;
    this.contents = contents;
  }

  static Map<String, Object> normalizedState(Map<String, Object> input) {
    var state = new LinkedHashMap<String, Object>();
    for (String field : FIELDS) if (input.containsKey(field)) state.put(field, input.get(field));
    String mode = text(state, "inputMode");
    if (!List.of("IDEA", "DETAILED_STORY", "EXISTING_PROMPT").contains(mode))
      throw new IllegalArgumentException("Choose an idea, detailed story or production prompt");
    String profile = text(state, "profile");
    if (!profile.isBlank()
        && !List.of("AUTO", "ABSURD_PHYSICS", "CURIOSITY_ADVENTURE", "EDUCATIONAL")
            .contains(profile)) throw new IllegalArgumentException("Unsupported content profile");
    String strategy = text(state, "storyMode");
    if (!strategy.isBlank()
        && !List.of("EXPLORE_DIFFERENT_STORIES", "IMPROVE_EXISTING_STORY").contains(strategy))
      throw new IllegalArgumentException("Unsupported generation strategy");
    if (state.containsKey("duration")
        && (!(state.get("duration") instanceof Number n)
            || !Double.isFinite(n.doubleValue())
            || n.doubleValue() < 1
            || n.doubleValue() > 60))
      throw new IllegalArgumentException("Duration must be between 1 and 60 seconds");
    if (state.containsKey("candidateCount")
        && (!(state.get("candidateCount") instanceof Number n)
            || n.doubleValue() != n.intValue()
            || n.intValue() < 1
            || n.intValue() > 3))
      throw new IllegalArgumentException("Choose 1 to 3 story candidates");
    if (state.containsKey("aspectRatio")
        && !List.of("9:16", "16:9", "1:1").contains(text(state, "aspectRatio")))
      throw new IllegalArgumentException("Unsupported aspect ratio");
    return state;
  }

  static String sourceText(Map<String, Object> state) {
    String mode = text(state, "inputMode");
    String key =
        mode.equals("DETAILED_STORY")
            ? "storyText"
            : mode.equals("EXISTING_PROMPT") ? "promptText" : "idea";
    return state.containsKey(key) ? text(state, key) : text(state, "idea");
  }

  private void validateWorkspace(Map<String, Object> state) {
    String path = text(state, "workspacePath");
    if (path.isBlank())
      throw new IllegalArgumentException("Select a workspace or create one before saving");
    videos.requirePromptWorkspace(path);
    String character = text(state, "mainCharacterId");
    if (!character.isBlank()
        && !jdbc.sql("SELECT EXISTS(SELECT 1 FROM characters WHERE id::text=:id)")
            .param("id", character)
            .query(Boolean.class)
            .single())
      throw new IllegalArgumentException(
          "Select an existing catalog character or leave it unconfirmed");
  }

  private static String text(Map<String, Object> m, String key) {
    Object value = m.get(key);
    return value == null ? "" : String.valueOf(value);
  }

  private static int revision(Map<String, Object> m, String key) {
    Object n = m.get(key);
    if (!(n instanceof Number number)
        || number.doubleValue() != number.intValue()
        || number.intValue() < 0)
      throw new IllegalArgumentException("An exact draft revision is required");
    return number.intValue();
  }

  private void lock(UUID id) {
    jdbc.sql("SELECT pg_advisory_xact_lock(hashtextextended(:id,0))")
        .param("id", "idea-draft:" + id)
        .query(
            rs -> {
              rs.next();
              return 0;
            });
  }

  @Transactional
  public Map<String, Object> save(Map<String, Object> request) {
    var state = normalizedState(map(request.get("state")));
    validateWorkspace(state);
    if (sourceText(state).isBlank())
      throw new IllegalArgumentException("Enter source text before saving a draft");
    UUID id = UUID.fromString(text(request, "draftId"));
    int expected = revision(request, "expectedRevision");
    lock(id);
    var previous = find(id);
    int current = previous.map(p -> revision(p, "revision")).orElse(0);
    if (previous.isPresent()) {
      var p = previous.get();
      requireWorkspace(p, text(state, "workspacePath"));
      if (map(p.get("state")).equals(state) && (expected == current || expected == current - 1))
        return p;
    }
    if (expected != current)
      throw new IllegalStateException("Draft changed in another tab. Reopen it before saving");
    var draft = new LinkedHashMap<String, Object>();
    draft.put("draftId", id.toString());
    draft.put("sessionId", id.toString());
    draft.put("ideaDraft", true);
    draft.put("revision", current + 1);
    draft.put("state", state);
    draft.put("status", "DRAFT");
    draft.put("checkpoint", "IDEA");
    draft.put("sourceType", "OPERATOR");
    draft.put("createdAt", previous.map(p -> p.get("createdAt")).orElse(Instant.now().toString()));
    draft.put("updatedAt", Instant.now().toString());
    append(draft, "CREATIVE_STUDIO_SESSION", id.toString());
    return draft;
  }

  public List<Map<String, Object>> list() {
    return jdbc.sql(
            "SELECT DISTINCT ON (payload->>'draftId') payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'ideaDraft'='true' ORDER BY payload->>'draftId',(payload->>'revision')::int DESC,payload->>'updatedAt' DESC,created_at DESC,id DESC")
        .query((rs, i) -> read(rs.getString(1)))
        .list();
  }

  public Map<String, Object> get(UUID id, String workspace) {
    var draft = find(id).orElseThrow(() -> new IllegalArgumentException("Saved draft not found"));
    requireWorkspace(draft, workspace);
    validateWorkspace(map(draft.get("state")));
    return draft;
  }

  private void requireWorkspace(Map<String, Object> draft, String workspace) {
    if (workspace.isBlank() || !workspace.equals(text(map(draft.get("state")), "workspacePath")))
      throw new IllegalArgumentException(
          "This draft belongs to a different workspace. Reopen it from Saved Projects");
  }

  private Optional<Map<String, Object>> find(UUID id) {
    return jdbc.sql(
            "SELECT payload::text FROM post_family_workflow_events WHERE kind='CREATIVE_STUDIO_SESSION' AND payload->>'ideaDraft'='true' AND payload->>'draftId'=:id ORDER BY (payload->>'revision')::int DESC,payload->>'updatedAt' DESC,created_at DESC,id DESC LIMIT 1")
        .param("id", id.toString())
        .query(String.class)
        .optional()
        .map(this::read);
  }

  @Transactional
  public Map<String, Object> continueDraft(UUID id, Map<String, Object> request) {
    lock(id);
    var draft = get(id, text(request, "workspacePath"));
    if (revision(request, "expectedRevision") != revision(draft, "revision"))
      throw new IllegalStateException(
          "Draft changed. Reopen the current revision before continuing");
    if (!"IDEA".equals(draft.get("checkpoint"))) return draft;
    var state = map(draft.get("state"));
    String mode = text(state, "inputMode");
    String source = sourceText(state);
    if (source.isBlank()) throw new IllegalArgumentException("Source text is required");
    var next = new LinkedHashMap<>(draft);
    next.putAll(state);
    String title =
        text(state, "title").isBlank()
            ? source.strip().substring(0, Math.min(80, source.strip().length()))
            : text(state, "title").strip();
    if ("DETAILED_STORY".equals(mode)) {
      String candidate = "operator-story-1";
      var result =
          Map.<String, Object>of(
              "role",
              "STORY",
              "sourceType",
              "OPERATOR",
              "alternatives",
              List.of(Map.of("candidateId", candidate, "title", title, "text", source)));
      var story = new LinkedHashMap<String, Object>();
      story.put("role", "STORY");
      story.put("title", title);
      story.put("sourceType", "OPERATOR");
      story.put("revisionType", "OPERATOR_IMPORT");
      story.put(
          "sourceRequest", Map.of("role", "OPERATOR_STORY", "text", source, "context", state));
      story.put("result", result);
      UUID storyId = append(story, "CREATIVE_ROLE", null);
      next.put("storyRecordId", storyId.toString());
      next.put("result", result);
      next.put("checkpoint", "STORY");
    } else if ("EXISTING_PROMPT".equals(mode)) {
      var content =
          contents.create(
              new ContentWorkspaceController.CreateContentRequest(
                  title, source, "9:16".equals(state.get("aspectRatio")) ? "REEL" : "SHORT"));
      var prompt =
          contents.createPrompt(
              content.id(),
              new ContentWorkspaceController.CreatePromptRequest(source, null, null, null));
      next.put("contentId", content.id().toString());
      next.put("promptVersionId", prompt.id().toString());
      next.put("rawText", prompt.rawText());
      next.put("promptSource", "USER_SUPPLIED");
      next.put("checkpoint", "PRODUCTION_REVIEW");
    } else
      throw new IllegalArgumentException("Save your idea or explicitly authorize story generation");
    next.put("updatedAt", Instant.now().toString());
    append(next, "CREATIVE_STUDIO_SESSION", id.toString());
    return next;
  }

  private UUID append(Map<String, Object> payload, String kind, String binding) {
    UUID id = UUID.randomUUID();
    payload.put("recordId", id.toString());
    payload.putIfAbsent("createdAt", Instant.now().toString());
    try {
      jdbc.sql(
              "INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES(:id,:kind,:binding,CAST(:payload AS jsonb))")
          .param("id", id)
          .param("kind", kind)
          .param("binding", binding)
          .param("payload", json.writeValueAsString(payload))
          .update();
      return id;
    } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
      throw new IllegalArgumentException("Invalid draft state", e);
    }
  }

  private Map<String, Object> read(String value) {
    try {
      return json.readValue(value, new TypeReference<>() {});
    } catch (Exception e) {
      throw new IllegalStateException("Invalid saved draft", e);
    }
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> map(Object value) {
    return value instanceof Map<?, ?> ? (Map<String, Object>) value : Map.of();
  }
}
