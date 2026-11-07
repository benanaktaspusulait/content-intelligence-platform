package com.pompom.creative.queue;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ProductionLifecycleGuardTest {
  private static final String PROMPT_SHA = "62a6001845ea6d39f928ca91de1601c471584b4d27ff1496483f6ac4626c94ff";
  @TempDir Path temp;
  private Path data;
  private Path library;
  private Path source;
  private ProductionLifecycleGuard guard;
  private Map<String, Object> entry;

  @BeforeEach
  void setUp() throws Exception {
    data = Files.createDirectories(temp.resolve("data"));
    library = Files.createDirectories(temp.resolve("library"));
    source = library.resolve("candidate/prompt.md");
    Files.createDirectories(source.getParent());
    Files.writeString(source, "source-bound prompt");
    guard = new ProductionLifecycleGuard(data, library, new ObjectMapper());
    entry = eligibleEntry();
    writeRegistry(List.of(entry));
  }

  @Test
  void publishedCandidateIsExcluded() {
    entry.put("lifecycleStatus", "PUBLISHED");
    entry.put("publicationStatus", "PUBLISHED");
    entry.put("renderStatus", "RENDERED");
    writeRegistry(List.of(entry));
    assertBlocked("PUBLISHED_OR_DUPLICATE_CONTENT");
  }

  @Test
  void exactDuplicateOfPublishedCandidateIsExcluded() {
    entry.put("duplicateClassification", "EXACT_DUPLICATE_OF_PUBLISHED");
    writeRegistry(List.of(entry));
    assertBlocked("PUBLISHED_OR_DUPLICATE_CONTENT");
  }

  @Test
  void storyEquivalentPublishedCandidateIsExcluded() {
    entry.put("duplicateClassification", "STORY_EQUIVALENT_TO_PUBLISHED");
    writeRegistry(List.of(entry));
    assertBlocked("PUBLISHED_OR_DUPLICATE_CONTENT");
  }

  @Test
  void sameCharacterWithDistinctStoryCanBeEligible() {
    entry.put("protagonist", "Kiko");
    entry.put("duplicateClassification", "DISTINCT");
    writeRegistry(List.of(entry, Map.of("candidateId", "published-kiko", "protagonist", "Kiko",
        "lifecycleStatus", "PUBLISHED", "promptSha256", "b".repeat(64))));
    assertThatCode(() -> guard.assertEligible(10, 11, PROMPT_SHA, Map.of())).doesNotThrowAnyException();
  }

  @Test
  void renderedButUnpublishedCandidateIsHeldForReuseReview() {
    entry.put("lifecycleStatus", "RENDERED_NOT_PUBLISHED");
    entry.put("renderStatus", "RENDERED");
    entry.put("publicationStatus", "NOT_PUBLISHED_CONFIRMED");
    writeRegistry(List.of(entry));
    assertBlocked("PRODUCTION_REUSE_REVIEW_REQUIRED");
  }

  @Test
  void unknownPublicationOrDuplicateStatusBlocks() {
    entry.put("publicationStatus", "UNKNOWN");
    writeRegistry(List.of(entry));
    assertBlocked("PRODUCTION_HUMAN_REVIEW_REQUIRED");
  }

  @Test
  void explicitRemakeAuthorizationIsSeparateAndMustMatchTheExactPrompt() {
    entry.put("lifecycleStatus", "PUBLISHED");
    entry.put("publicationStatus", "PUBLISHED");
    entry.put("renderStatus", "RENDERED");
    entry.put("humanRemakeAuthorization", Map.of(
        "id", "human-remake-approval-001", "authorized", true, "scope", "REMAKE_ONLY",
        "humanReviewer", "owner", "contentId", 10, "promptVersionId", 11,
        "promptSha256", PROMPT_SHA));
    writeRegistry(List.of(entry));
    assertBlocked("PUBLISHED_OR_DUPLICATE_CONTENT");
    assertThatCode(() -> guard.assertEligible(10, 11, PROMPT_SHA,
        Map.of("remakeAuthorizationId", "human-remake-approval-001")))
        .doesNotThrowAnyException();
  }

  @Test
  void newUnusedCandidateIsEligibleOnlyWithCompleteReviewedEvidence() {
    assertThatCode(() -> guard.assertEligible(10, 11, PROMPT_SHA, Map.of()))
        .doesNotThrowAnyException();
  }

  @Test
  void newConceptUsesCreationProvenanceInsteadOfHistoricalNeverPublishedProof() throws Exception {
    prepareNewConcept("DISTINCT", "NO_POSITIVE_MATCH");
    entry.put("lifecycleStatus", "NEW_CONCEPT");
    entry.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    entry.put("publicationStatus", "NO_RENDER_LINKED");
    entry.put("candidateOrigin", "NEW_CONCEPT");
    entry.put("candidateId", "net-new-run-001-opening-a-seed-one");
    entry.put("linkedRenderCount", 0);
    entry.put("creationRecord", creationRecord());
    entry.put("noveltyReview", noveltyReview("NO_POSITIVE_MATCH"));
    entry.put("duplicateClassification", "DISTINCT");
    writeRegistry(List.of(entry));
    assertThatCode(() -> guard.assertEligible(10, 11, PROMPT_SHA,
        Map.of("candidateId", "net-new-run-001-opening-a-seed-one")))
        .doesNotThrowAnyException();
  }

  @Test
  void highSimilarityNeedsHumanClearance() throws Exception {
    prepareNewConcept("HIGH_SIMILARITY_REVIEW", "PENDING");
    entry.put("lifecycleStatus", "NEW_CONCEPT");
    entry.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    entry.put("publicationStatus", "NO_RENDER_LINKED");
    entry.put("candidateOrigin", "NEW_CONCEPT");
    entry.put("candidateId", "net-new-run-001-opening-a-seed-one");
    entry.put("linkedRenderCount", 0);
    entry.put("creationRecord", creationRecord());
    entry.put("noveltyReview", noveltyReview("PENDING"));
    entry.put("duplicateClassification", "HIGH_SIMILARITY_REVIEW");
    writeRegistry(List.of(entry));
    assertBlocked("PRODUCTION_HUMAN_REVIEW_REQUIRED", Map.of("candidateId", "net-new-run-001-opening-a-seed-one"));

    entry.put("noveltyReview", noveltyReview("CLEARED_DISTINCT"));
    writeRegistry(List.of(entry));
    assertThatCode(() -> guard.assertEligible(10, 11, PROMPT_SHA,
        Map.of("candidateId", "net-new-run-001-opening-a-seed-one")))
        .doesNotThrowAnyException();
  }

  @Test
  void newIdCannotReclassifyUnknownOrExactHistoricalContent() throws Exception {
    prepareNewConcept("DISTINCT", "NO_POSITIVE_MATCH");
    entry.put("lifecycleStatus", "NEW_CONCEPT");
    entry.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    entry.put("publicationStatus", "NO_RENDER_LINKED");
    entry.put("candidateOrigin", "NEW_CONCEPT");
    entry.put("candidateId", "net-new-run-001-opening-a-seed-one");
    entry.put("linkedRenderCount", 0);
    entry.put("creationRecord", creationRecord());
    entry.put("noveltyReview", noveltyReview("NO_POSITIVE_MATCH"));
    entry.put("duplicateClassification", "DISTINCT");
    writeRegistry(List.of(entry, Map.of("candidateId", "old-unknown", "lifecycleStatus", "UNKNOWN",
        "promptSha256", PROMPT_SHA)));
    assertBlocked("PUBLISHED_OR_DUPLICATE_CONTENT", Map.of("candidateId", "net-new-run-001-opening-a-seed-one"));

    writeRegistry(List.of(entry));
    assertBlocked("PRODUCTION_CANDIDATE_BINDING_INVALID", Map.of("candidateId", "different-id"));
  }

  @Test
  void linkedRenderBlocksNewConcept() throws Exception {
    prepareNewConcept("DISTINCT", "NO_POSITIVE_MATCH");
    entry.put("lifecycleStatus", "NEW_CONCEPT");
    entry.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    entry.put("publicationStatus", "NO_RENDER_LINKED");
    entry.put("candidateOrigin", "NEW_CONCEPT");
    entry.put("candidateId", "net-new-run-001-opening-a-seed-one");
    entry.put("linkedRenderCount", 1);
    entry.put("creationRecord", creationRecord());
    entry.put("noveltyReview", noveltyReview("NO_POSITIVE_MATCH"));
    entry.put("duplicateClassification", "DISTINCT");
    writeRegistry(List.of(entry));
    assertBlocked("PRODUCTION_REUSE_REVIEW_REQUIRED", Map.of("candidateId", "net-new-run-001-opening-a-seed-one"));
  }

  @Test
  void candidateIdMustBeUniqueAcrossRegistry() throws Exception {
    prepareNewConcept("DISTINCT", "NO_POSITIVE_MATCH");
    entry.put("lifecycleStatus", "NEW_CONCEPT");
    entry.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    entry.put("publicationStatus", "NO_RENDER_LINKED");
    entry.put("candidateOrigin", "NEW_CONCEPT");
    entry.put("candidateId", "net-new-run-001-opening-a-seed-one");
    entry.put("linkedRenderCount", 0);
    entry.put("creationRecord", creationRecord());
    entry.put("noveltyReview", noveltyReview("NO_POSITIVE_MATCH"));
    entry.put("duplicateClassification", "DISTINCT");
    var duplicate = new LinkedHashMap<>(entry);
    duplicate.put("contentId", 12);
    duplicate.put("promptSha256", "d".repeat(64));
    writeRegistry(List.of(entry, duplicate));
    assertBlocked("PRODUCTION_CANDIDATE_ID_NOT_UNIQUE",
        Map.of("candidateId", "net-new-run-001-opening-a-seed-one"));
  }

  @Test
  void newConceptNoveltyReviewMustBindItsOwnHashedEvidence() throws Exception {
    prepareNewConcept("DISTINCT", "NO_POSITIVE_MATCH");
    entry.put("lifecycleStatus", "NEW_CONCEPT");
    entry.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    entry.put("publicationStatus", "NO_RENDER_LINKED");
    entry.put("candidateOrigin", "NEW_CONCEPT");
    entry.put("candidateId", "net-new-run-001-opening-a-seed-one");
    entry.put("linkedRenderCount", 0);
    entry.put("creationRecord", creationRecord());
    entry.put("noveltyReview", Map.of("disposition", "NO_POSITIVE_MATCH",
        "checkedAt", "2026-11-02T12:30:00Z", "reviewEvidenceSha256", PROMPT_SHA));
    entry.put("duplicateClassification", "DISTINCT");
    writeRegistry(List.of(entry));
    assertBlocked("PRODUCTION_HUMAN_REVIEW_REQUIRED",
        Map.of("candidateId", "net-new-run-001-opening-a-seed-one"));
  }

  @Test
  void promptBindingAndEvidenceHashMustMatch() throws Exception {
    assertThatThrownBy(() -> guard.assertEligible(10, 11, "c".repeat(64), Map.of()))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(error -> ((ValidationEvidenceRejectedException) error).getErrorCode())
        .isEqualTo("PRODUCTION_LIFECYCLE_UNKNOWN");
    Files.writeString(source, "changed source");
    assertBlocked("PRODUCTION_LIFECYCLE_UNKNOWN");
  }

  private Map<String, Object> eligibleEntry() throws Exception {
    String fileSha = java.util.HexFormat.of().formatHex(
        MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(source)));
    var result = new LinkedHashMap<String, Object>();
    result.put("candidateId", "new-candidate");
    result.put("contentId", 10);
    result.put("promptVersionId", 11);
    result.put("promptSha256", PROMPT_SHA);
    result.put("lifecycleStatus", "PROMPT_READY_NOT_RENDERED");
    result.put("renderStatus", "NOT_RENDERED_CONFIRMED");
    result.put("publicationStatus", "NOT_PUBLISHED_CONFIRMED");
    result.put("duplicateClassification", "DISTINCT");
    result.put("protagonist", "Mimi");
    result.put("reviewedBy", "human-reviewer");
    result.put("reviewedAt", "2026-11-02T12:00:00Z");
    result.put("evidence", List.of(Map.of("kind", "LOCAL_PROMPT", "path", "candidate/prompt.md", "sha256", fileSha)));
    return result;
  }

  private void prepareNewConcept(String classification, String disposition) throws Exception {
    Path review = library.resolve("candidate/novelty-review.json");
    Files.writeString(review, "{\"status\":\"" + disposition + "\"}");
    String reviewSha = java.util.HexFormat.of().formatHex(
        MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(review)));
    var evidence = new ArrayList<Map<String, Object>>();
    evidence.add(Map.of("kind", "LOCAL_PROMPT", "path", "candidate/prompt.md", "sha256",
        entry.get("evidence") instanceof List<?> list ? ((Map<?, ?>) list.getFirst()).get("sha256") : ""));
    evidence.add(Map.of("kind", "NOVELTY_REVIEW", "path", "candidate/novelty-review.json", "sha256", reviewSha));
    entry.put("evidence", evidence);
    entry.put("_reviewSha", reviewSha);
  }

  private Map<String, Object> creationRecord() {
    var record = new LinkedHashMap<String, Object>();
    record.put("candidateId", "net-new-run-001-opening-a-seed-one");
    record.put("generationArchitecture", "TWO_STAGE_V1");
    record.put("provider", "openai");
    record.put("model", "gpt-6.1-sol");
    record.put("reasoningEffort", "low");
    record.put("generationRunId", "net-new-run-001");
    record.put("phaseARequestId", "opening-a");
    record.put("createdAt", "2026-11-02T12:00:00Z");
    record.put("sourceSha256", PROMPT_SHA);
    record.put("contentId", 10);
    record.put("promptVersionId", 11);
    return record;
  }

  private Map<String, Object> noveltyReview(String disposition) {
    return Map.of("disposition", disposition, "checkedAt", "2026-11-02T12:30:00Z",
        "reviewEvidenceSha256", entry.get("_reviewSha"), "reviewedBy", "human-reviewer",
        "reviewedAt", "2026-11-02T12:31:00Z");
  }

  private void assertBlocked(String code) {
    assertBlocked(code, Map.of());
  }

  private void assertBlocked(String code, Map<String, Object> settings) {
    assertThatThrownBy(() -> guard.assertEligible(10, 11, PROMPT_SHA, settings))
        .isInstanceOf(ValidationEvidenceRejectedException.class)
        .extracting(error -> ((ValidationEvidenceRejectedException) error).getErrorCode())
        .isEqualTo(code);
  }

  private void writeRegistry(List<Map<String, Object>> entries) {
    try {
      var registry = new LinkedHashMap<String, Object>();
      registry.put("schemaVersion", "pompom-production-lifecycle-screen-v1");
      registry.put("entries", entries);
      Path path = data.resolve("workflow/production-lifecycle-registry.json");
      Files.createDirectories(path.getParent());
      new ObjectMapper().writeValue(path.toFile(), registry);
    } catch (Exception error) {
      throw new AssertionError(error);
    }
  }
}
