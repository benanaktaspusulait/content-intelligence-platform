package com.pompom.creative.queue;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.time.Instant;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Fail-closed lifecycle and duplicate check immediately before a render job is persisted. */
@Component
public final class ProductionLifecycleGuard {
  private static final String REGISTRY = "workflow/production-lifecycle-registry.json";
  private static final String SCHEMA = "pompom-production-lifecycle-screen-v1";

  private final Path dataRoot;
  private final Path libraryRoot;
  private final ObjectMapper mapper;

  @Autowired
  public ProductionLifecycleGuard(
      @Value("${POMPOM_DATA_ROOT:/data}") String dataRoot,
      @Value("${POMPOM_LIBRARY_ROOT:/data/library}") String libraryRoot,
      ObjectMapper mapper) {
    this(Path.of(dataRoot), Path.of(libraryRoot), mapper);
  }

  ProductionLifecycleGuard(Path dataRoot, Path libraryRoot, ObjectMapper mapper) {
    this.dataRoot = dataRoot.toAbsolutePath().normalize();
    this.libraryRoot = libraryRoot.toAbsolutePath().normalize();
    this.mapper = mapper;
  }

  /**
   * Admit only an exact reviewed prompt whose lifecycle, publication, render, and duplicate
   * evidence establish a genuinely new production. Remakes require a separately bound approval.
   */
  public void assertEligible(long contentId, long promptVersionId, String promptSha256,
      Map<String, Object> settings) {
    if (promptSha256 == null || !promptSha256.matches("[0-9a-f]{64}"))
      reject("PRODUCTION_LIFECYCLE_BINDING_INVALID", "A valid prompt hash is required for lifecycle screening");
    Path registryPath = dataRoot.resolve(REGISTRY).normalize();
    if (!registryPath.startsWith(dataRoot) || !Files.isRegularFile(registryPath))
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle registry is unavailable; paid render is blocked");
    final Map<String, Object> registry;
    try {
      registry = mapper.readValue(registryPath.toFile(), new TypeReference<>() {});
    } catch (IOException | RuntimeException error) {
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle registry could not be verified; paid render is blocked");
      return;
    }
    if (!SCHEMA.equals(registry.get("schemaVersion")))
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle registry schema is unsupported; paid render is blocked");
    Object rawEntries = registry.get("entries");
    if (!(rawEntries instanceof List<?>))
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle registry has no reviewed entries; paid render is blocked");
    List<?> entries = (List<?>) rawEntries;

    Map<String, Object> candidate = null;
    for (Object item : entries) {
      if (!(item instanceof Map<?, ?> raw)) continue;
      Map<String, Object> entry = stringMap(raw);
      boolean sameBinding = Objects.equals(String.valueOf(entry.get("contentId")), Long.toString(contentId))
          && Objects.equals(String.valueOf(entry.get("promptVersionId")), Long.toString(promptVersionId))
          && promptSha256.equals(entry.get("promptSha256"));
      if (sameBinding) {
        candidate = entry;
      }
    }
    if (candidate == null)
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "No exact lifecycle review exists for this content and prompt version");
    for (Object item : entries) {
      if (!(item instanceof Map<?, ?> raw)) continue;
      Map<String, Object> previous = stringMap(raw);
      if (sameBinding(previous, candidate)) continue;
      if (exactDuplicate(previous, candidate, contentId, promptSha256)) {
        if (isPublished(previous)
            && validRemakeAuthorization(candidate.get("humanRemakeAuthorization"), settings,
                contentId, promptVersionId, promptSha256)) continue;
        reject("PUBLISHED_OR_DUPLICATE_CONTENT",
            "Exact prompt, video, content, or production lineage already exists in historical records");
      }
    }
    Map<String, Set<String>> verifiedEvidenceHashes = verifyEvidence(candidate.get("evidence"), promptSha256);

    if ("NEW_CONCEPT".equals(candidate.get("candidateOrigin"))) {
      assertNewConceptEligible(candidate, settings, contentId, promptVersionId, promptSha256,
          verifiedEvidenceHashes);
      return;
    }

    String lifecycle = value(candidate, "lifecycleStatus");
    String render = value(candidate, "renderStatus");
    String publication = value(candidate, "publicationStatus");
    String duplicate = value(candidate, "duplicateClassification");

    if ("RENDERED_NOT_PUBLISHED".equals(lifecycle)
        || ("RENDERED".equals(render) && !"PUBLISHED".equals(lifecycle)
            && !"PUBLISHED".equals(publication)
            && !"OPERATOR_ATTESTED_PUBLISHED".equals(publication)))
      reject("PRODUCTION_REUSE_REVIEW_REQUIRED", "Previously rendered content must be reviewed for reuse or publication before another render");
    if ("PUBLISHED".equals(lifecycle) || "PUBLISHED".equals(publication)
        || "OPERATOR_ATTESTED_PUBLISHED".equals(publication)
        || "EXACT_DUPLICATE_OF_PUBLISHED".equals(duplicate)
        || "STORY_EQUIVALENT_TO_PUBLISHED".equals(duplicate)) {
      if (!validRemakeAuthorization(candidate.get("humanRemakeAuthorization"), settings,
          contentId, promptVersionId, promptSha256))
        reject("PUBLISHED_OR_DUPLICATE_CONTENT", "Published or published-equivalent content requires separate explicit remake authorization");
      return;
    }
    if ("HIGH_SIMILARITY_REVIEW".equals(duplicate)
        || "INSUFFICIENT_EVIDENCE".equals(duplicate)
        || "UNKNOWN".equals(lifecycle)
        || "UNKNOWN".equals(render)
        || "UNKNOWN".equals(publication))
      reject("PRODUCTION_HUMAN_REVIEW_REQUIRED", "Lifecycle, publication, render, or duplicate evidence is unresolved");

    boolean eligible = "PROMPT_READY_NOT_RENDERED".equals(lifecycle)
        && "NOT_RENDERED_CONFIRMED".equals(render)
        && "NOT_PUBLISHED_CONFIRMED".equals(publication)
        && "DISTINCT".equals(duplicate)
        && !value(candidate, "reviewedBy").isBlank()
        && !value(candidate, "reviewedAt").isBlank();
    if (!eligible)
      reject("PRODUCTION_HUMAN_REVIEW_REQUIRED", "Candidate lacks complete reviewed evidence of unused, distinct production status");
  }

  private void assertNewConceptEligible(Map<String, Object> candidate, Map<String, Object> settings,
      long contentId, long promptVersionId, String promptSha256,
      Map<String, Set<String>> verifiedEvidenceHashes) {
    String candidateId = value(candidate, "candidateId");
    if (candidateId.isBlank() || settings == null
        || !candidateId.equals(settings.get("candidateId")))
      reject("PRODUCTION_CANDIDATE_BINDING_INVALID", "The exact new candidate ID must be bound to the render request");

    Object entriesObject;
    try {
      Map<String, Object> registry = mapper.readValue(
          dataRoot.resolve(REGISTRY).toFile(), new TypeReference<>() {});
      entriesObject = registry.get("entries");
    } catch (IOException | RuntimeException error) {
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Candidate registry could not be re-read");
      return;
    }
    if (!(entriesObject instanceof List<?> entries)
        || entries.stream().filter(item -> item instanceof Map<?, ?> raw
            && candidateId.equals(stringMap(raw).get("candidateId"))).count() != 1)
      reject("PRODUCTION_CANDIDATE_ID_NOT_UNIQUE", "A new candidate ID must identify exactly one registry record");

    Object creationObject = candidate.get("creationRecord");
    if (!(creationObject instanceof Map<?, ?> rawCreation))
      reject("PRODUCTION_CANDIDATE_CREATION_UNVERIFIED", "An explicit new-concept creation record is required");
    Map<String, Object> creation = stringMap((Map<?, ?>) creationObject);
    if (!candidateId.equals(value(creation, "candidateId"))
        || !promptSha256.equals(value(creation, "sourceSha256"))
        || !"TWO_STAGE_V1".equals(value(creation, "generationArchitecture"))
        || !"openai".equals(value(creation, "provider"))
        || !"gpt-6.1-sol".equals(value(creation, "model"))
        || !"low".equals(value(creation, "reasoningEffort"))
        || number(creation.get("contentId")) != contentId
        || number(creation.get("promptVersionId")) != promptVersionId
        || value(creation, "generationRunId").isBlank()
        || value(creation, "phaseARequestId").isBlank()
        || !validInstant(value(creation, "createdAt")))
      reject("PRODUCTION_CANDIDATE_CREATION_UNVERIFIED", "Creation provenance must bind the unique candidate, run, timestamp, and exact source hash");
    if (!"NOT_RENDERED_CONFIRMED".equals(value(candidate, "renderStatus"))
        || number(candidate.get("linkedRenderCount")) != 0)
      reject("PRODUCTION_REUSE_REVIEW_REQUIRED", "New concept must have no render linked to its candidate ID");
    if ("EXACT_DUPLICATE_OF_PUBLISHED".equals(candidate.get("duplicateClassification"))
        || "STORY_EQUIVALENT_TO_PUBLISHED".equals(candidate.get("duplicateClassification")))
      reject("PUBLISHED_OR_DUPLICATE_CONTENT", "A confirmed published duplicate cannot enter normal new-content production");

    Object screenObject = candidate.get("noveltyReview");
    if (!(screenObject instanceof Map<?, ?> rawScreen))
      reject("PRODUCTION_HUMAN_REVIEW_REQUIRED", "A source-bound historical novelty review is required");
    Map<String, Object> screen = stringMap((Map<?, ?>) screenObject);
    String classification = value(candidate, "duplicateClassification");
    String disposition = value(screen, "disposition");
    boolean clearedHighSimilarity = "HIGH_SIMILARITY_REVIEW".equals(classification)
        && "CLEARED_DISTINCT".equals(disposition)
        && !value(screen, "reviewedBy").isBlank()
        && validInstant(value(screen, "reviewedAt"));
    boolean noPositiveMatch = "DISTINCT".equals(classification)
        && "NO_POSITIVE_MATCH".equals(disposition);
    if ((!noPositiveMatch && !clearedHighSimilarity)
        || !validInstant(value(screen, "checkedAt"))
        || !verifiedEvidenceHashes.getOrDefault("NOVELTY_REVIEW", Set.of())
            .contains(value(screen, "reviewEvidenceSha256")))
      reject("PRODUCTION_HUMAN_REVIEW_REQUIRED", "Novelty must show no positive match; unresolved similarity needs explicit human clearance");

    if (!"NEW_CONCEPT".equals(value(candidate, "lifecycleStatus"))
        || !"NO_RENDER_LINKED".equals(value(candidate, "publicationStatus")))
      reject("PRODUCTION_CANDIDATE_CREATION_UNVERIFIED", "Historical UNKNOWN lifecycle cannot be relabeled as new content");
  }

  private static boolean validInstant(String value) {
    try { Instant.parse(value); return true; }
    catch (RuntimeException error) { return false; }
  }

  private static long number(Object value) {
    return value instanceof Number n ? n.longValue() : -1;
  }

  private Map<String, Set<String>> verifyEvidence(Object raw, String promptSha256) {
    if (!(raw instanceof List<?>) || ((List<?>) raw).isEmpty())
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle evidence provenance is missing");
    List<?> evidence = (List<?>) raw;
    boolean verifiedPrompt = false;
    var verifiedHashes = new java.util.HashMap<String, Set<String>>();
    for (Object item : evidence) {
      if (!(item instanceof Map<?, ?> rawEntry))
        reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle evidence entry is malformed");
      Map<String, Object> entry = stringMap((Map<?, ?>) item);
      String pathText = value(entry, "path");
      String expected = value(entry, "sha256");
      if (!expected.matches("[0-9a-f]{64}") || pathText.isBlank())
        reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle evidence path or digest is invalid");
      Path path = libraryRoot.resolve(pathText).normalize();
      if (!path.startsWith(libraryRoot) || !Files.isRegularFile(path))
        reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle evidence file is unavailable");
      try (var input = Files.newInputStream(path)) {
        var digest = java.security.MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[8192];
        for (int count; (count = input.read(buffer)) >= 0;) if (count > 0) digest.update(buffer, 0, count);
        String actual = java.util.HexFormat.of().formatHex(digest.digest());
        if (!expected.equals(actual))
          reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle evidence hash does not match its source file");
        String kind = value(entry, "kind");
        if (!kind.isBlank()) {
          verifiedHashes.computeIfAbsent(kind, ignored -> new java.util.HashSet<>()).add(expected);
        }
        verifiedPrompt |= "LOCAL_PROMPT".equals(entry.get("kind"))
            && promptSha256.equals(expected);
      } catch (IOException | java.security.NoSuchAlgorithmException error) {
        reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Lifecycle evidence could not be hashed");
      }
    }
    if (!verifiedPrompt)
      reject("PRODUCTION_LIFECYCLE_UNKNOWN", "Exact source-prompt evidence is required");
    var immutable = new java.util.HashMap<String, Set<String>>();
    verifiedHashes.forEach((kind, hashes) -> immutable.put(kind, Set.copyOf(hashes)));
    return Map.copyOf(immutable);
  }

  private boolean validRemakeAuthorization(Object raw, Map<String, Object> settings,
      long contentId, long promptVersionId, String promptSha256) {
    if (!(raw instanceof Map<?, ?> auth) || settings == null) return false;
    String authId = value(stringMap(auth), "id");
    return Boolean.TRUE.equals(auth.get("authorized"))
        && "REMAKE_ONLY".equals(auth.get("scope"))
        && !value(stringMap(auth), "humanReviewer").isBlank()
        && Long.toString(contentId).equals(String.valueOf(auth.get("contentId")))
        && Long.toString(promptVersionId).equals(String.valueOf(auth.get("promptVersionId")))
        && promptSha256.equals(auth.get("promptSha256"))
        && authId.matches("[A-Za-z0-9._:-]{8,160}")
        && authId.equals(settings.get("remakeAuthorizationId"));
  }

  private static boolean isPublished(Map<String, Object> entry) {
    return "PUBLISHED".equals(entry.get("lifecycleStatus"))
        || "PUBLISHED".equals(entry.get("publicationStatus"))
        || "OPERATOR_ATTESTED_PUBLISHED".equals(entry.get("publicationStatus"));
  }

  private static boolean sameBinding(Map<String, Object> left, Map<String, Object> right) {
    return Objects.equals(String.valueOf(left.get("contentId")), String.valueOf(right.get("contentId")))
        && Objects.equals(String.valueOf(left.get("promptVersionId")), String.valueOf(right.get("promptVersionId")))
        && Objects.equals(left.get("promptSha256"), right.get("promptSha256"));
  }

  private static boolean exactDuplicate(Map<String, Object> published, Map<String, Object> candidate,
      long contentId, String promptSha256) {
    return promptSha256.equals(published.get("promptSha256"))
        || Long.toString(contentId).equals(String.valueOf(published.get("contentId")))
        || nonBlankEqual(published.get("videoSha256"), candidate.get("existingVideoSha256"))
        || nonBlankEqual(published.get("productionLineageId"), candidate.get("productionLineageId"));
  }

  private static boolean nonBlankEqual(Object left, Object right) {
    return left != null && right != null && !String.valueOf(left).isBlank()
        && String.valueOf(left).equals(String.valueOf(right));
  }

  private static String value(Map<String, Object> map, String key) {
    Object value = map.get(key);
    return value == null ? "" : String.valueOf(value);
  }

  private static Map<String, Object> stringMap(Map<?, ?> input) {
    var output = new java.util.LinkedHashMap<String, Object>();
    input.forEach((key, value) -> { if (key instanceof String name) output.put(name, value); });
    return output;
  }

  private static void reject(String code, String message) {
    throw new ValidationEvidenceRejectedException(code, message);
  }
}
