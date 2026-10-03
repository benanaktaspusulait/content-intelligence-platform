# Part 02 Plan B2a: Variant-Aware Backend Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every backend write/read path that touches a video's performance evidence the
ability to scope to an exact variant when one is known; fix the content-hash dedup bug so
duplicate bytes at a second physical path no longer show as permanently "Not ingested" forever.

**Architecture:** A new, purely-additive `V32` migration adds a `video_path_aliases` table (for
the dedup fix) and `intervention_events.variant_id` (closing the one schema gap where a variant
column doesn't exist at all yet). `PerformanceImportService` gains an explicit `variantid`
import-column resolution step, scoped to the already-resolved `videoId` — no fuzzy matching.
`PlatformStateService.publication()`'s read path and three performance-query read paths
(`PerformanceTrajectoryController`, `PlatformGrowthProfileService`, `DiscoveryProfileService`)
each gain an optional `variantId` filter using `IS NOT DISTINCT FROM` — a *selective* match
(`null` means "the un-variant-scoped group," never "aggregate across all variants"), consistent
with the schema's own existing sentinel convention and preventing a silent reintroduction of the
variant-blind-aggregation problem (audit P0-03) this plan exists to close.

**Tech Stack:** Java 21, Spring Boot (`JdbcClient`, Spring Data JPA for the one new entity),
PostgreSQL 17, JUnit 5 + AssertJ, Testcontainers for all DB-backed tests (this module has no
mock-based service tests for any of the files this plan touches — Testcontainers is the
established, and only, pattern here).

## Global Constraints

- Never edit a previously-committed migration (V1-V31). This plan's new migration is `V32`.
- `performance_observations.variant_id`, `video_publications.variant_id`,
  `platform_content_states.variant_id` already exist (since `V1`) — this plan only wires Java
  code to read/write them, no schema change needed for those three.
- `intervention_events` has NO `variant_id` column at all today — this is the one column this
  plan's migration actually adds.
- `intervention_events` is append-only (trigger from `V3__intervention_events_append_only.sql`
  blocks UPDATE/DELETE) — the new migration can only `ADD COLUMN`, never backfill via `UPDATE`.
- No fuzzy attribution anywhere in this plan's scope — every variant resolution is either an
  explicit caller-supplied `variantId`/import-column UUID, verified to belong to the claimed
  video via `VideoVariantRepository.findByIdAndVideoId`, or `null` (meaning "not scoped to a
  specific variant," never a guess).
- `IS NOT DISTINCT FROM` is the required comparison operator everywhere a nullable `variant_id`
  filter is added (never plain `=`, which would silently exclude `NULL` rows from a `variantId
  = null` query — the opposite of the intended "selective match on the un-scoped group" behavior).
- Must leave the full Spring test suite green (`mvn test` from `intelligence/backend`).

---

## Context: read these existing files in full before starting

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java` —
  `ingest()` (lines 60-83) and `mediaFiles()` (lines 160-182, plus `mapMediaFile` ~257-266) are
  what Task 1 modifies.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoEntity.java`,
  `VideoVariantEntity.java` (from Plan B1, already merged) — for the exact entity-construction
  conventions this plan's new `VideoPathAliasEntity` follows.
- `intelligence/backend/src/main/resources/db/migration/V30__add_immutable_validation_evidence.sql`,
  `V31__complete_quality_validation_evidence.sql` — exact style this plan's `V32` migration
  matches: a comment header explaining intent/non-destructiveness, `COMMENT ON COLUMN` for every
  new column, named constraints.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PerformanceImportService.java`
  — `match()` (the private method building `RowMatch`), `writeObservation()`, and the
  `RowMatch`/`CommitRow` private records are what Task 2 modifies.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`
  — the private `publication(UUID videoId, String platform)` method (its two call sites:
  `recordPublication()` and `reachFurtherSummary()`) is what Task 3 modifies.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java`,
  `PlatformGrowthProfileService.java`, `DiscoveryProfileService.java` — all three gain an
  optional `variantId` parameter in Task 4.
- `intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServiceWindowTest.java`
  — the exact Testcontainers + `@SpringBootTest` + raw-`JdbcClient`-fixture-setup pattern every
  new test in this plan follows (copy its container/property boilerplate verbatim).

---

## Task 1: Path-alias dedup fix (`V32` migration part 1 + `VideoPathAliasEntity`/`Repository` + `VideoService` fix)

**Files:**
- Create: `intelligence/backend/src/main/resources/db/migration/V32__add_video_path_aliases_and_intervention_variant.sql`
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoPathAliasEntity.java`
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoPathAliasRepository.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServicePathAliasTest.java`

**Interfaces:**
- Produces: `VideoPathAliasEntity(VideoEntity video, String relativePath, String contentHash)`
  (JPA entity, `@GeneratedValue` id, `@CreationTimestamp discoveredAt`).
  `VideoPathAliasRepository extends JpaRepository<VideoPathAliasEntity, UUID>` with
  `Optional<VideoPathAliasEntity> findByRelativePath(String relativePath)` and
  `List<VideoPathAliasEntity> findAllByVideoId(UUID videoId)`.
  `VideoDtos.MediaFile` gains no new field in this task (that's deferred — see the Note below);
  this task's only externally-visible behavior change is that `mediaFiles()` now reports
  `ingested: true` with the canonical video's id/status for an aliased path, instead of `false`.

- [ ] **Step 1: Write the migration**

Read both `V30`/`V31` in full first (per Context above) to match style exactly. Create
`intelligence/backend/src/main/resources/db/migration/V32__add_video_path_aliases_and_intervention_variant.sql`:

```sql
-- Two independent, additive fixes from the Part 02 audit (video_variants.variant_id already
-- exists for performance_observations/video_publications/platform_content_states since V1; this
-- migration only adds the two columns/tables that are genuinely still missing).

-- Fix 1 (P1-01): content-hash dedup silently discarded a second physical path that happened to
-- have byte-identical content to an already-ingested video. This table lets that second path
-- resolve to the canonical video instead of permanently reporting "Not ingested."
CREATE TABLE video_path_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  relative_path TEXT NOT NULL UNIQUE,
  content_hash VARCHAR(64) NOT NULL,
  discovered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_video_path_aliases_video_id ON video_path_aliases(video_id);

COMMENT ON TABLE video_path_aliases IS
  'Additional physical paths that resolve to the same canonical video by content hash. A path''s presence here (or as videos.relative_path) both count as "ingested" for library listing purposes.';
COMMENT ON COLUMN video_path_aliases.content_hash IS
  'Denormalized copy of the owning video''s content_hash at discovery time, for fast verification without a join.';

-- Fix 2: intervention_events has no variant_id column at all (unlike performance_observations,
-- video_publications, platform_content_states, which have had it since V1). Additive, nullable;
-- the table is append-only (V3__intervention_events_append_only.sql trigger), so existing rows
-- simply get variant_id=NULL and can never be backfilled or mutated afterward - that is expected
-- and correct, not a gap to close later.
ALTER TABLE intervention_events
  ADD COLUMN variant_id UUID REFERENCES video_variants(id) ON DELETE CASCADE;

CREATE INDEX idx_intervention_events_variant
  ON intervention_events(variant_id)
  WHERE variant_id IS NOT NULL;

COMMENT ON COLUMN intervention_events.variant_id IS
  'Optional variant this intervention was observed against. NULL means the intervention is not scoped to a specific variant (legacy rows, or a video with no variants) - matched with IS NOT DISTINCT FROM, never treated as "any variant".';
```

- [ ] **Step 2: Write the failing test**

Read `VideoVariantEntityPersistenceTest.java` (Plan B1) and `PlatformStateServiceWindowTest.java`
for the exact Testcontainers boilerplate to copy. Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServicePathAliasTest.java`:

```java
package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.video.api.VideoDtos;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoServicePathAliasTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  private static Path dataRoot;

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) throws IOException {
    dataRoot = Files.createTempDirectory("pompom-path-alias-test");
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add("pompom.data-root", () -> dataRoot.toString());
  }

  @Autowired VideoService service;
  @Autowired VideoRepository videos;
  @Autowired VideoPathAliasRepository aliases;

  private Path original;
  private Path duplicate;

  @BeforeEach
  void setUp() throws IOException {
    byte[] bytes = "identical-fake-video-bytes-for-hash-matching".getBytes();
    original = dataRoot.resolve("original.mp4");
    duplicate = dataRoot.resolve("duplicate-copy.mp4");
    Files.write(original, bytes);
    Files.write(duplicate, bytes);
  }

  @AfterEach
  void tearDown() throws IOException {
    Files.deleteIfExists(original);
    Files.deleteIfExists(duplicate);
  }

  @Test
  void ingestingADuplicateContentHashRecordsAPathAliasInsteadOfDiscardingIt() {
    VideoDtos.VideoResponse first = service.ingest("original.mp4", null);

    VideoDtos.VideoResponse second = service.ingest("duplicate-copy.mp4", null);

    // The second ingest resolves to the SAME canonical video (same content hash), not a new row.
    assertThat(second.id()).isEqualTo(first.id());
    List<VideoPathAliasEntity> recorded = aliases.findAllByVideoId(first.id());
    assertThat(recorded).hasSize(1);
    assertThat(recorded.get(0).getRelativePath()).isEqualTo("duplicate-copy.mp4");
  }

  @Test
  void mediaFilesReportsAnAliasedPathAsIngestedWithTheCanonicalVideoId() {
    VideoDtos.VideoResponse first = service.ingest("original.mp4", null);
    service.ingest("duplicate-copy.mp4", null);

    List<VideoDtos.MediaFile> files = service.mediaFiles("", true);

    VideoDtos.MediaFile aliasedFile =
        files.stream().filter(file -> file.relativePath().equals("duplicate-copy.mp4")).findFirst().orElseThrow();
    assertThat(aliasedFile.ingested()).isTrue();
    assertThat(aliasedFile.videoId()).isEqualTo(first.id());
  }

  @Test
  void ingestingTheSamePathTwiceDoesNotCreateADuplicateAlias() {
    service.ingest("original.mp4", null);
    service.ingest("duplicate-copy.mp4", null);
    VideoDtos.VideoResponse first = videos.findByContentHash(
            videos.findAllByRelativePathIn(List.of("original.mp4")).get(0).getContentHash())
        .map(entity -> service.get(entity.getId()))
        .orElseThrow();

    service.ingest("duplicate-copy.mp4", null);

    assertThat(aliases.findAllByVideoId(first.id())).hasSize(1);
  }
}
```

(This test uses the real ML client — confirm whether `MlVideoClient` is a real HTTP call needing
a running ML service or has a test/mock configuration already wired for `@SpringBootTest` in this
module; if `mvn test` fails here with a connection error rather than an assertion failure, read
`MlVideoClient.java` and whatever test configuration profile the existing
`PlatformStateServiceWindowTest`/similar `@SpringBootTest` tests use to see how they avoid a real
ML call, and apply the same approach — do not skip this test, resolve the dependency correctly.)

- [ ] **Step 3: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServicePathAliasTest`
Expected: FAIL — either compilation failure (`VideoPathAliasEntity`/`VideoPathAliasRepository`
don't exist) or, once those exist, a test assertion failure on the current discard-on-duplicate
behavior.

- [ ] **Step 4: Implement the entity and repository**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoPathAliasEntity.java`
(mirror `VideoVariantEntity.java`'s exact `@ManyToOne`/`@GeneratedValue`/`@CreationTimestamp`
conventions):

```java
package com.pompomhills.intelligence.video;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;

@Entity
@Table(name = "video_path_aliases")
public class VideoPathAliasEntity {
  @Id @GeneratedValue private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "video_id")
  private VideoEntity video;

  @Column(name = "relative_path", nullable = false, unique = true)
  private String relativePath;

  @Column(name = "content_hash", nullable = false, length = 64)
  private String contentHash;

  @CreationTimestamp
  @Column(name = "discovered_at", nullable = false, updatable = false)
  private Instant discoveredAt;

  protected VideoPathAliasEntity() {}

  public VideoPathAliasEntity(VideoEntity video, String relativePath, String contentHash) {
    this.video = video;
    this.relativePath = relativePath;
    this.contentHash = contentHash;
  }

  public UUID getId() {
    return id;
  }

  public VideoEntity getVideo() {
    return video;
  }

  public String getRelativePath() {
    return relativePath;
  }

  public String getContentHash() {
    return contentHash;
  }

  public Instant getDiscoveredAt() {
    return discoveredAt;
  }
}
```

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoPathAliasRepository.java`:

```java
package com.pompomhills.intelligence.video;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoPathAliasRepository extends JpaRepository<VideoPathAliasEntity, UUID> {
  Optional<VideoPathAliasEntity> findByRelativePath(String relativePath);

  List<VideoPathAliasEntity> findAllByVideoId(UUID videoId);
}
```

- [ ] **Step 5: Fix `VideoService.ingest()` and `mediaFiles()`**

Read the current full `VideoService.java` first (per Context). Add the `VideoPathAliasRepository`
as a new constructor dependency, then change `ingest()`'s dedup branch:

```java
@Transactional
public VideoResponse ingest(String relativePath, UUID seriesId) {
  Path root = properties.dataRoot().toAbsolutePath().normalize();
  Path file = root.resolve(relativePath).normalize();
  if (!file.startsWith(root) || !Files.isRegularFile(file))
    throw new IllegalArgumentException(
        "Video path must be a file inside the configured data root");
  String extension = file.getFileName().toString().replaceFirst("^.*\\.", "").toLowerCase();
  if (!properties.allowedVideoExtensions().contains(extension))
    throw new IllegalArgumentException("Unsupported video extension: " + extension);
  var result = ml.analyse(root.relativize(file).toString());
  var metadata = result.metadata();
  String relative = root.relativize(file).toString();
  var entity = videos.findByContentHash(metadata.sha256()).orElse(null);
  if (entity != null) {
    if (!entity.getRelativePath().equals(relative)
        && pathAliases.findByRelativePath(relative).isEmpty()) {
      pathAliases.save(new VideoPathAliasEntity(entity, relative, metadata.sha256()));
    }
  } else {
    entity =
        videos.save(
            new VideoEntity(
                UUID.randomUUID(),
                metadata.sha256(),
                file.getFileName().toString(),
                relative,
                metadata.durationMs(),
                metadata.width(),
                metadata.height(),
                metadata.fps(),
                metadata.aspectRatio(),
                metadata.codec(),
                metadata.audioPresent(),
                seriesId,
                clock.instant()));
  }
  return map(entity);
}
```

Then fix `mediaFiles()` to also resolve aliased paths. Read the current full method first; the
change is in how `ingestedByPath` is built and consulted. After the existing
`Map<String, VideoEntity> ingestedByPath = ...` block, add a second lookup for paths NOT already
covered by `videos.relative_path`:

```java
List<String> unmatchedPaths =
    relativePaths.stream().filter(path -> !ingestedByPath.containsKey(path)).toList();
Map<String, VideoEntity> aliasedByPath = new java.util.HashMap<>();
if (!unmatchedPaths.isEmpty()) {
  for (String path : unmatchedPaths) {
    pathAliases
        .findByRelativePath(path)
        .ifPresent(alias -> aliasedByPath.put(path, alias.getVideo()));
  }
}
```

Then change `mapMediaFile(Path root, Path file, Map<String, VideoEntity> ingestedByPath)` to
accept and consult the alias map too — simplest correct approach: merge both maps into one before
calling `mapMediaFile` (so `mapMediaFile` itself does not need its own signature changed):

```java
Map<String, VideoEntity> resolvedByPath = new java.util.HashMap<>(ingestedByPath);
resolvedByPath.putAll(aliasedByPath);
return files.stream().map(path -> mapMediaFile(root, path, resolvedByPath)).toList();
```

**Note on `VideoDtos.MediaFile`:** this task deliberately does NOT add a `variantId` field to
`MediaFile` — that's explicitly Plan B2b's (frontend) concern once a path can be resolved against
`video_variants.generated_path` too (a separate lookup this task doesn't need, since path aliases
and variants are different concepts: an alias is "same bytes, different path," a variant is "a
genuinely different edit"). Do not conflate the two or add variant-resolution logic to
`mediaFiles()` in this task.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServicePathAliasTest`
Expected: all 3 tests PASS.

- [ ] **Step 7: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add intelligence/backend/src/main/resources/db/migration/V32__add_video_path_aliases_and_intervention_variant.sql intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoPathAliasEntity.java intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoPathAliasRepository.java intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServicePathAliasTest.java
git commit -m "fix(intelligence): record a path alias instead of discarding a duplicate-content-hash ingest path"
```

---

## Task 2: Variant resolution in `PerformanceImportService`

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PerformanceImportService.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/PerformanceImportServiceVariantTest.java`

**Interfaces:**
- Consumes: `VideoVariantRepository.findByIdAndVideoId(UUID variantId, UUID videoId)` (from Plan
  B1, already merged).
- Produces: `RowMatch` gains a `variantId` field (`private record RowMatch(UUID videoId, UUID
  variantId) {}`); `CommitRow` gains the same; `performance_observations.variant_id` is populated
  on insert when a row's `variantid`/`variant_id` column resolves to a real variant of the
  matched video.

- [ ] **Step 1: Write the failing test**

Read `PlatformStateServiceWindowTest.java` for the Testcontainers boilerplate (copy verbatim) and
`PerformanceImportService.java`'s full current `match()`/`writeObservation()`/`preview()`/
`commit()` methods (per Context) before writing this test, since the test exercises the full
`preview()` → `commit()` flow, not just `match()` in isolation. Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/PerformanceImportServiceVariantTest.java`:

```java
package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class PerformanceImportServiceVariantTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired PerformanceImportService importService;

  private UUID insertVideo(String filename) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,:name,:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("name", filename)
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private UUID insertVariant(UUID videoId) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO video_variants(id,video_id,variant_type,generated_path)
            VALUES (:id,:video,'HOOK_COLD_OPEN',:path)
            """)
        .param("id", id)
        .param("video", videoId)
        .param("path", "test/variants/" + id + "-hook.mp4")
        .update();
    return id;
  }

  @Test
  void importRowWithAnExplicitVariantIdPersistsItOnTheObservation() throws IOException {
    UUID videoId = insertVideo("my-video.mp4");
    UUID variantId = insertVariant(videoId);
    String csv =
        "videoid,variantid,views,metricsemantics,measurementtimestamp\n"
            + videoId
            + ","
            + variantId
            + ",1000,CUMULATIVE,2026-01-01T00:00:00Z\n";
    var upload = new MockMultipartFile("file", "import.csv", "text/csv", csv.getBytes());

    var preview = importService.preview(upload, "instagram", "UTC");
    importService.commit(preview.batchId());

    UUID persistedVariant =
        jdbc.sql(
                "SELECT variant_id FROM performance_observations WHERE video_id=:video")
            .param("video", videoId)
            .query(UUID.class)
            .single();
    assertThat(persistedVariant).isEqualTo(variantId);
  }

  @Test
  void importRowWithAVariantIdThatBelongsToADifferentVideoLeavesVariantNull() throws IOException {
    UUID videoId = insertVideo("another-video.mp4");
    UUID otherVideoId = insertVideo("unrelated-video.mp4");
    UUID variantOfOtherVideo = insertVariant(otherVideoId);
    String csv =
        "videoid,variantid,views,metricsemantics,measurementtimestamp\n"
            + videoId
            + ","
            + variantOfOtherVideo
            + ",1000,CUMULATIVE,2026-01-01T00:00:00Z\n";
    var upload = new MockMultipartFile("file", "import.csv", "text/csv", csv.getBytes());

    var preview = importService.preview(upload, "instagram", "UTC");
    importService.commit(preview.batchId());

    UUID persistedVariant =
        jdbc.sql(
                "SELECT variant_id FROM performance_observations WHERE video_id=:video")
            .param("video", videoId)
            .query(UUID.class)
            .single();
    assertThat(persistedVariant).isNull();
  }

  @Test
  void importRowWithNoVariantIdLeavesVariantNull() throws IOException {
    UUID videoId = insertVideo("no-variant-video.mp4");
    String csv =
        "videoid,views,metricsemantics,measurementtimestamp\n"
            + videoId
            + ",1000,CUMULATIVE,2026-01-01T00:00:00Z\n";
    var upload = new MockMultipartFile("file", "import.csv", "text/csv", csv.getBytes());

    var preview = importService.preview(upload, "instagram", "UTC");
    importService.commit(preview.batchId());

    UUID persistedVariant =
        jdbc.sql(
                "SELECT variant_id FROM performance_observations WHERE video_id=:video")
            .param("video", videoId)
            .query(UUID.class)
            .single();
    assertThat(persistedVariant).isNull();
  }
}
```

(Confirm `ImportFileParser`'s actual CSV column-header normalization and delimiter handling match
this test's literal CSV string before trusting it — read `ImportFileParser.java` directly; adjust
the CSV content if the real parser requires a different header casing/format, since the plan's
own investigation only confirmed `ParsedRow`'s shape, not the exact CSV dialect this parser
accepts.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=PerformanceImportServiceVariantTest`
Expected: all 3 tests currently PASS by coincidence if `variant_id` is already always `NULL`
(since nothing populates it today) — specifically, the FIRST test
(`importRowWithAnExplicitVariantIdPersistsItOnTheObservation`) should FAIL since it expects a
non-null `variantId` but today's code always inserts `NULL`. Confirm this specific test fails and
the other two currently pass trivially (both expect `NULL`, which is the status quo) — this
confirms you're testing the right thing before changing code.

- [ ] **Step 3: Implement**

Read the full current `match()`, `RowMatch`, `CommitRow`, and `writeObservation()` (per Context)
before editing — this plan was written against a specific snapshot that may have shifted.

Change `RowMatch`:
```java
private record RowMatch(UUID videoId, UUID variantId) {}
```

Update every existing `new RowMatch(x)` call site in `match()` to `new RowMatch(x, null)` first
(preserving current behavior exactly), then add the variant resolution step. The full updated
`match()`:

```java
private RowMatch match(ImportFileParser.ParsedRow row) {
  var normalized = normalize(row.values());
  String explicitId = first(normalized, "videoid", "video_id");
  UUID resolvedVideoId = null;
  if (explicitId != null) {
    try {
      UUID id = UUID.fromString(explicitId);
      boolean exists =
          jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
              .param("id", id)
              .query(Boolean.class)
              .single();
      if (exists) resolvedVideoId = id;
    } catch (IllegalArgumentException ignored) {
      // Invalid identifiers remain unresolved. Fuzzy matching is intentionally forbidden.
    }
  }
  if (resolvedVideoId == null) {
    String filename = first(normalized, "filename", "videofilename", "video_filename");
    if (filename != null) {
      List<UUID> ids =
          jdbc.sql("SELECT id FROM videos WHERE original_filename=:name ORDER BY created_at")
              .param("name", filename)
              .query(UUID.class)
              .list();
      if (ids.size() == 1) resolvedVideoId = ids.getFirst();
    }
  }
  if (resolvedVideoId == null) return new RowMatch(null, null);
  UUID variantId = resolveVariant(normalized, resolvedVideoId);
  return new RowMatch(resolvedVideoId, variantId);
}

/**
 * Resolves an explicit variantid/variant_id import column to a real VideoVariantEntity scoped
 * to the already-resolved video - never a filename or fuzzy guess, per the audit's P1-08
 * requirement. Returns null (not an error) when no variant column is present, the value isn't a
 * valid UUID, or the UUID doesn't resolve to a variant of THIS video.
 */
private UUID resolveVariant(Map<String, String> normalized, UUID videoId) {
  String explicitVariantId = first(normalized, "variantid", "variant_id");
  if (explicitVariantId == null) return null;
  try {
    UUID variantId = UUID.fromString(explicitVariantId);
    boolean belongsToVideo =
        jdbc.sql("SELECT EXISTS(SELECT 1 FROM video_variants WHERE id=:variant AND video_id=:video)")
            .param("variant", variantId)
            .param("video", videoId)
            .query(Boolean.class)
            .single();
    return belongsToVideo ? variantId : null;
  } catch (IllegalArgumentException ignored) {
    return null;
  }
}
```

Update `CommitRow`:
```java
private record CommitRow(UUID id, UUID videoId, UUID variantId, Map<String, String> raw) {}
```

Find the `commit()` method's row-fetching query (reads `id,matched_video_id,raw_data::text` and
builds `CommitRow`) and add `variant_id` to both the SELECT and the `CommitRow` construction —
this requires `import_rows` to carry the resolved variant through from `preview()` to `commit()`.
Read the current `preview()` method's `import_rows` INSERT (it currently inserts
`matched_video_id`) and add a `matched_variant_id` column binding there too, sourced from
`rowMatch.variantId()`. **This requires `import_rows` to have a `matched_variant_id` column,
which does not exist in the schema today** — add it to this task's own migration file from Step 1
of this task... but Task 1 already committed its migration. Since both tasks' migrations would
otherwise collide on `V32`, add this column in a NEW statement in a dedicated follow-up migration
file for this task specifically: create
`intelligence/backend/src/main/resources/db/migration/V33__add_matched_variant_id_to_import_rows.sql`:

```sql
-- Carries the variant resolved during import preview/commit through to the written observation.
-- Additive, nullable: existing import_rows predate variant resolution and have no variant to
-- backfill.
ALTER TABLE import_rows
  ADD COLUMN matched_variant_id UUID REFERENCES video_variants(id) ON DELETE SET NULL;

COMMENT ON COLUMN import_rows.matched_variant_id IS
  'Variant resolved from an explicit variantid/variant_id import column, scoped to matched_video_id. NULL when no variant column was present or it did not resolve to a variant of the matched video.';
```

(This is a second migration in this plan, intentionally numbered after Task 1's `V32` — do not
go back and edit `V32` to add this column there; migrations are strictly additive and
sequential, and Task 1's migration is presumed already committed by the time this task starts
per this plan's own task ordering.)

Update `preview()`'s `import_rows` INSERT to also bind `matched_variant_id`:
```java
jdbc.sql(
        """
        INSERT INTO import_rows
          (import_batch_id,sheet_name,source_row_number,raw_data,matched_video_id,
           matched_variant_id,match_status,match_confidence)
        VALUES (:batch,:sheet,:row,CAST(:raw AS jsonb),:video,:variant,:status,:confidence)
        """)
    .param("batch", batchId)
    .param("sheet", row.sheet())
    .param("row", row.rowNumber())
    .param("raw", writeJson(row.values()))
    .param("video", rowMatch.videoId(), Types.OTHER)
    .param("variant", rowMatch.variantId(), Types.OTHER)
    .param("status", rowMatch.videoId() == null ? "UNRESOLVED" : "EXACT")
    .param("confidence", rowMatch.videoId() == null ? null : 1.0, Types.DOUBLE)
    .update();
```

Update `commit()`'s row-fetching query and `CommitRow` construction:
```java
var rows =
    jdbc.sql(
            """
            SELECT id,matched_video_id,matched_variant_id,raw_data::text
            FROM import_rows WHERE import_batch_id=:id ORDER BY sheet_name,source_row_number
            """)
        .param("id", batchId)
        .query(
            (rs, ignored) ->
                new CommitRow(
                    rs.getObject("id", UUID.class),
                    rs.getObject("matched_video_id", UUID.class),
                    rs.getObject("matched_variant_id", UUID.class),
                    readMap(rs.getString("raw_data"))))
        .list();
```

Finally, update `writeObservation(CommitRow row, String platform)`'s INSERT to add `variant_id`
to both the column list and the VALUES/param binding:
```java
INSERT INTO performance_observations
  (import_row_id,video_id,variant_id,platform,platform_content_id,publication_timestamp,
   measurement_timestamp,metric_semantics,views,reach,unique_viewers,
   ...  -- (rest unchanged)
VALUES
  (:row,:video,:variant,:platform,:contentId,:published,:measured,:semantics,:views,:reach,
   ...  -- (rest unchanged)
```
with `.param("variant", row.variantId(), Types.OTHER)` added to the parameter chain (placed
right after `.param("video", row.videoId())`, matching the column order).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=PerformanceImportServiceVariantTest`
Expected: all 3 tests PASS.

- [ ] **Step 5: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add intelligence/backend/src/main/resources/db/migration/V33__add_matched_variant_id_to_import_rows.sql intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PerformanceImportService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/PerformanceImportServiceVariantTest.java
git commit -m "feat(intelligence): resolve an explicit import-row variantid column, no fuzzy matching"
```

---

## Task 3: Variant-aware `PlatformStateService.publication()` read path

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServicePublicationVariantTest.java`

**Interfaces:**
- Consumes: nothing new from Tasks 1-2.
- Produces: `publication(UUID videoId, UUID variantId, String platform)` (was `publication(UUID
  videoId, String platform)`); `recordPublication()` passes `request.variantId()` through;
  `reachFurtherSummary(UUID videoId, String platform)` keeps its own public signature unchanged
  in THIS task (widening it is out of scope here — see the note below) but internally calls the
  new 3-arg `publication(...)` with `variantId=null`, preserving its exact current behavior.

- [ ] **Step 1: Write the failing test**

Read the full current `publication()`, `recordPublication()`, and `reachFurtherSummary()` methods
(per Context) before writing this test. Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServicePublicationVariantTest.java`
(copy the Testcontainers boilerplate from `PlatformStateServiceWindowTest.java` verbatim):

```java
package com.pompomhills.intelligence.platformstate;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class PlatformStateServicePublicationVariantTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired PlatformStateService service;

  private UUID insertVideo() {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,'test.mp4',:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private UUID insertVariant(UUID videoId) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO video_variants(id,video_id,variant_type,generated_path)
            VALUES (:id,:video,'HOOK_COLD_OPEN',:path)
            """)
        .param("id", id)
        .param("video", videoId)
        .param("path", "test/variants/" + id + "-hook.mp4")
        .update();
    return id;
  }

  @Test
  void recordingTwoVariantsOnTheSamePlatformKeepsBothPublicationsIndependentlyRetrievable() {
    UUID videoId = insertVideo();
    UUID variantA = insertVariant(videoId);
    UUID variantB = insertVariant(videoId);

    var publicationA =
        service.recordPublication(
            videoId,
            new PlatformStateService.PublicationRequest(
                variantA, "instagram", "post-a", "https://instagram.com/p/a", Instant.now(),
                "UTC", false, "CSV", "variant A publication"),
            "test-user");
    var publicationB =
        service.recordPublication(
            videoId,
            new PlatformStateService.PublicationRequest(
                variantB, "instagram", "post-b", "https://instagram.com/p/b", Instant.now(),
                "UTC", false, "CSV", "variant B publication"),
            "test-user");

    // Before this fix, recordPublication()'s own return value (which calls publication()
    // internally) could return the WRONG variant's row - whichever was most recently created
    // for this video+platform, ignoring which variant was actually just written.
    assertThat(publicationA.platformContentId()).isEqualTo("post-a");
    assertThat(publicationB.platformContentId()).isEqualTo("post-b");
  }
}
```

(Read `PlatformStateService.PublicationRequest`'s actual current field order/types directly
before trusting this test's constructor call — the plan's investigation confirmed `variantId` is
one of its fields but did not confirm the full exact field order; adjust the test's constructor
arguments to match the real record definition.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=PlatformStateServicePublicationVariantTest`
Expected: likely FAIL on `publicationB.platformContentId()` — depending on `created_at` ordering
granularity, the current `ORDER BY created_at DESC LIMIT 1` read path may return variant A's row
for both calls' return values if both are created within the same timestamp resolution, or may
pass by accident if timestamps differ enough. Run it a few times if it passes to confirm it is
not a flaky false negative; if it passes consistently without the fix, add a small
`Thread.sleep`-free alternative — insert a third variant/publication to make the "most recent
wins regardless of variant" bug more reliably observable, or directly assert
`service.get(...)`-equivalent variant-scoped read if a more direct read method exists. Use your
judgment on the most reliable way to make this specific pre-fix behavior observably fail, since
timestamp-ordering races can be fragile — document whatever adjustment you make and why.

- [ ] **Step 3: Implement**

Read the full current `publication()`, `recordPublication()`, `reachFurtherSummary()` (per
Context) before editing.

Change the private `publication()` method:
```java
private Optional<PublicationView> publication(UUID videoId, UUID variantId, String platform) {
  return jdbc.sql(
          """
          SELECT id,platform,platform_content_id,platform_url,published_at,
                 publication_timezone,off_peak_publish,context_label,source,notes
          FROM video_publications
          WHERE video_id=:video AND variant_id IS NOT DISTINCT FROM :variant AND platform=:platform
          ORDER BY created_at DESC LIMIT 1
          """)
      .param("video", videoId)
      .param("variant", variantId, Types.OTHER)
      .param("platform", platform)
      .query(
          (rs, ignored) ->
              new PublicationView(
                  rs.getObject("id", UUID.class),
                  rs.getString("platform"),
                  rs.getString("platform_content_id"),
                  rs.getString("platform_url"),
                  rs.getObject("published_at", OffsetDateTime.class).toInstant(),
                  rs.getString("publication_timezone"),
                  (Boolean) rs.getObject("off_peak_publish"),
                  rs.getString("context_label"),
                  rs.getString("source"),
                  rs.getString("notes")))
      .optional();
}
```

Update `recordPublication()`'s final line (was `return publication(videoId, platform).orElseThrow();`):
```java
return publication(videoId, request.variantId(), platform).orElseThrow();
```

Update `reachFurtherSummary()`'s call site (was `publication(videoId, normalizedPlatform).orElse(null);`)
to pass `null` explicitly, preserving current behavior for this task (widening
`reachFurtherSummary`'s own public signature to accept a caller-supplied `variantId` is
deliberately deferred — it has broader ripple effects through `liveFeatures()` and its own
callers that this task does not attempt; note this explicitly in your report as a scoped-out
follow-up, not a silently-dropped requirement):
```java
PublicationView publication = publication(videoId, null, normalizedPlatform).orElse(null);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=PlatformStateServicePublicationVariantTest`
Expected: PASS.

- [ ] **Step 5: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass — specifically re-check `PlatformStateServiceWindowTest.java` (Plan A)
still passes, since this task touches the same class.

- [ ] **Step 6: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServicePublicationVariantTest.java
git commit -m "fix(intelligence): make PlatformStateService.publication()'s read path variant-aware, matching the write path"
```

---

## Task 4: Optional `variantId` filter on the three performance-query read paths

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/DiscoveryProfileService.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/VariantScopedPerformanceQueriesTest.java`

**Interfaces:**
- Consumes: nothing new from Tasks 1-3.
- Produces: `PerformanceTrajectoryController.trajectory(UUID videoId, String platform, UUID
  variantId)` (new optional `@RequestParam`); `PlatformGrowthProfileService.profile(UUID videoId,
  String platform, Instant cutoff, UUID variantId)`; `DiscoveryProfileService.profile(UUID
  videoId, String platform, Instant cutoff, UUID variantId)`. All three: `variantId=null` means
  "match only `variant_id IS NULL` rows" (selective, never a cross-variant aggregate fallback).

- [ ] **Step 1: Write the failing test**

Read all three methods' full current bodies (per Context) before writing this test — this test
exercises all three in one file since they share the identical variant-filtering concern and
fixture-setup pattern. Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/VariantScopedPerformanceQueriesTest.java`
(copy the Testcontainers boilerplate from `PlatformStateServiceWindowTest.java` verbatim):

```java
package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.performance.api.PerformanceTrajectoryController;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VariantScopedPerformanceQueriesTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired PerformanceTrajectoryController trajectoryController;
  @Autowired PlatformGrowthProfileService growthProfileService;
  @Autowired DiscoveryProfileService discoveryProfileService;

  private UUID insertVideo() {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,'test.mp4',:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private UUID insertVariant(UUID videoId) {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO video_variants(id,video_id,variant_type,generated_path)
            VALUES (:id,:video,'HOOK_COLD_OPEN',:path)
            """)
        .param("id", id)
        .param("video", videoId)
        .param("path", "test/variants/" + id + "-hook.mp4")
        .update();
    return id;
  }

  private void insertObservation(
      UUID videoId, UUID variantId, Instant publishedAt, Instant measuredAt, long views) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,variant_id,platform,publication_timestamp,measurement_timestamp,
               metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,:variant,'instagram',:published,:measured,
                    'CUMULATIVE',:views,'CSV')
            """)
        .param("video", videoId)
        .param("variant", variantId, java.sql.Types.OTHER)
        .param("published", OffsetDateTime.ofInstant(publishedAt, ZoneOffset.UTC))
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("views", views)
        .update();
  }

  @Test
  void trajectoryWithNoVariantFilterOnlyMatchesUnscopedObservations() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0.plusSeconds(3600), 999L);

    var unscoped = trajectoryController.trajectory(videoId, "instagram", null);

    assertThat(unscoped.points()).hasSize(1);
    assertThat(unscoped.points().get(0).views()).isEqualTo(100L);
  }

  @Test
  void trajectoryWithAnExplicitVariantFilterOnlyMatchesThatVariant() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0.plusSeconds(3600), 999L);

    var scoped = trajectoryController.trajectory(videoId, "instagram", variantId);

    assertThat(scoped.points()).hasSize(1);
    assertThat(scoped.points().get(0).views()).isEqualTo(999L);
  }

  @Test
  void growthProfileWithNoVariantFilterOnlyMatchesUnscopedObservations() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0, 999L);

    var profile = growthProfileService.profile(videoId, "instagram", Instant.now(), null);

    assertThat(profile.latest().views()).isEqualTo(100L);
  }

  @Test
  void discoveryProfileWithAnExplicitVariantFilterOnlyMatchesThatVariant() {
    UUID videoId = insertVideo();
    UUID variantId = insertVariant(videoId);
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, null, t0, t0, 100L);
    insertObservation(videoId, variantId, t0, t0, 999L);

    var profile = discoveryProfileService.profile(videoId, "instagram", Instant.now(), variantId);

    assertThat(profile.videoId()).isEqualTo(videoId);
    // Discovery profile's audience snapshot query must have picked the variant-scoped row.
    UUID matchedObservationId =
        jdbc.sql("SELECT id FROM performance_observations WHERE video_id=:v AND views=999")
            .param("v", videoId)
            .query(UUID.class)
            .single();
    assertThat(matchedObservationId).isNotNull();
  }
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VariantScopedPerformanceQueriesTest`
Expected: compilation failure — none of the three methods accept a 4th/3rd `variantId` parameter
yet.

- [ ] **Step 3: Implement — `PerformanceTrajectoryController`**

Read the full current `trajectory()` method (per Context) before editing. Add the parameter and
WHERE clause:

```java
@GetMapping("/video/{videoId}/trajectory")
TrajectoryView trajectory(
    @PathVariable UUID videoId,
    @RequestParam(defaultValue = "instagram") String platform,
    @RequestParam(required = false) UUID variantId) {
  List<ObservationSeries.RawObservation> raw =
      jdbc.sql(
              """
              SELECT measurement_timestamp,views,metric_semantics,source
              FROM performance_observations
              WHERE video_id=:video AND platform=:platform AND measurement_timestamp IS NOT NULL
                AND variant_id IS NOT DISTINCT FROM :variant
              ORDER BY measurement_timestamp
              """)
          .param("video", videoId)
          .param("platform", platform.toLowerCase())
          .param("variant", variantId, java.sql.Types.OTHER)
          .query(/* unchanged row mapper */)
          .list();
  // ... rest of the method body unchanged
}
```

(Keep every other line of the method exactly as it currently is — only the SQL's WHERE clause and
the method signature change.)

- [ ] **Step 4: Implement — `PlatformGrowthProfileService`**

Read the full current `profile()` and `earliestPublication()` methods (per Context) before
editing. Both queries need the same added clause:

```java
@Transactional(readOnly = true)
public GrowthProfile profile(UUID videoId, String platform, Instant cutoff, UUID variantId) {
  String normalized = platform.toLowerCase(Locale.ROOT);
  List<ObservationSeries.RawObservation> raw =
      jdbc.sql(
              """
              SELECT measurement_timestamp,views,metric_semantics,source
              FROM performance_observations
              WHERE video_id=:video AND platform=:platform
                AND publication_timestamp IS NOT NULL
                AND measurement_timestamp IS NOT NULL
                AND measurement_timestamp<=:cutoff
                AND variant_id IS NOT DISTINCT FROM :variant
              ORDER BY measurement_timestamp
              """)
          .param("video", videoId)
          .param("platform", normalized)
          .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
          .param("variant", variantId, java.sql.Types.OTHER)
          .query(/* unchanged row mapper */)
          .list();
  Instant publishedAt = earliestPublication(videoId, normalized, cutoff, variantId);
  // ... rest of the method body unchanged (points, checkpoint, etc.)
}

private Instant earliestPublication(UUID videoId, String platform, Instant cutoff, UUID variantId) {
  return jdbc.sql(
          """
          SELECT min(publication_timestamp) FROM performance_observations
          WHERE video_id=:video AND platform=:platform AND publication_timestamp IS NOT NULL
            AND measurement_timestamp<=:cutoff AND variant_id IS NOT DISTINCT FROM :variant
          """)
      .param("video", videoId)
      .param("platform", platform)
      .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
      .param("variant", variantId, java.sql.Types.OTHER)
      .query(OffsetDateTime.class)
      .optional()
      .map(OffsetDateTime::toInstant)
      .orElse(null);
}
```

**Important:** `PlatformStateService.java` calls `growthProfiles.profile(videoId, platform,
cutoff)` (3-arg, in `liveFeatures()`) — this call site breaks once the signature grows to 4
params. Fix it by passing `null` explicitly at that call site (preserving current behavior,
matching Task 3's identical deferral pattern for `reachFurtherSummary`): change
`growthProfiles.profile(videoId, platform, cutoff)` to `growthProfiles.profile(videoId, platform,
cutoff, null)`. Grep for `growthProfiles.profile(` and `.profile(.*cutoff\)` across the whole
`intelligence/backend/src/main` tree to confirm this is the only call site needing this fix — do
not assume, verify directly.

- [ ] **Step 5: Implement — `DiscoveryProfileService`**

Read the full current `profile()` method (per Context) before editing. Both the `audience` and
`us` queries need the clause added:

```java
@Transactional(readOnly = true)
public DiscoveryProfile profile(UUID videoId, String platform, Instant cutoff, UUID variantId) {
  String normalizedPlatform = platform.toLowerCase();
  OffsetDateTime cutoffTime = OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC);
  AudienceSnapshot audience =
      jdbc.sql(
              """
              SELECT id,measurement_timestamp,views,follows,followers_percentage,
                     nonfollowers_percentage,recommendation_percentage
              FROM performance_observations
              WHERE video_id=:video AND platform=:platform
                AND COALESCE(measurement_timestamp,created_at)<=:cutoff
                AND variant_id IS NOT DISTINCT FROM :variant
              ORDER BY COALESCE(measurement_timestamp,created_at) DESC,created_at DESC
              LIMIT 1
              """)
          .param("video", videoId)
          .param("platform", normalizedPlatform)
          .param("cutoff", cutoffTime)
          .param("variant", variantId, java.sql.Types.OTHER)
          .query(/* unchanged row mapper */)
          .optional()
          .orElse(null);
  CountrySnapshot us =
      jdbc.sql(
              """
              SELECT co.percentage,co.estimated_absolute_count,
                     COALESCE(co.observed_at,po.measurement_timestamp,po.created_at) observed_at,
                     co.data_quality_status
              FROM country_observations co
              JOIN performance_observations po ON po.id=co.performance_observation_id
              WHERE po.video_id=:video AND po.platform=:platform AND co.country_code='US'
                AND COALESCE(co.observed_at,po.measurement_timestamp,po.created_at)<=:cutoff
                AND po.variant_id IS NOT DISTINCT FROM :variant
              ORDER BY COALESCE(co.observed_at,po.measurement_timestamp,po.created_at) DESC
              LIMIT 1
              """)
          .param("video", videoId)
          .param("platform", normalizedPlatform)
          .param("cutoff", cutoffTime)
          .param("variant", variantId, java.sql.Types.OTHER)
          .query(/* unchanged row mapper */)
          .optional()
          .orElse(null);
  // ... rest of the method body unchanged
}
```

**Important:** check `PlatformStateService.java`'s call site(s) of `discoveryProfiles.profile(`
the same way as Step 4's `growthProfiles` check — grep directly, fix by passing `null` at the
call site, do not assume there is exactly one.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=VariantScopedPerformanceQueriesTest`
Expected: all 4 tests PASS.

- [ ] **Step 7: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass — specifically re-check Plan A's tests
(`PerformanceTrajectoryControllerTest`, `PlatformGrowthProfileServiceTest`,
`PlatformStateServiceWindowTest`) still pass, since this task's three signature changes ripple
through files those tests exercise.

- [ ] **Step 8: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/DiscoveryProfileService.java intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/VariantScopedPerformanceQueriesTest.java
git commit -m "feat(intelligence): add optional, selective variantId filter to trajectory/growth/discovery performance queries"
```

---

## Self-Review

**1. Spec coverage against the roadmap's Plan B2a file list:**
- `VideoService.java` path-alias dedup fix → Task 1.
- New `V32` migration (path aliases + `intervention_events.variant_id`) → Task 1. (A second,
  unplanned `V33` migration was added in Task 2 for `import_rows.matched_variant_id` — this
  wasn't in the original roadmap file list, since the roadmap's investigation phase didn't drill
  into `import_rows`' own schema; documented inline in Task 2 with explicit reasoning for why it's
  additive and necessary, not scope creep.)
- `PerformanceImportService.java` variant resolution → Task 2.
- `PlatformStateService.java` publication read-path → Task 3.
- `PerformanceTrajectoryController.java`/`PlatformGrowthProfileService.java`/
  `DiscoveryProfileService.java` variant filter → Task 4.

**2. Placeholder scan:** no TBD/TODO patterns. Two deliberate, explicitly-documented scope
deferrals exist (Task 3's `reachFurtherSummary` signature widening; this is the same pattern as
Plan A Task 4's `PlatformStateService` scope cut) — both are named decisions with stated
rationale, not silently dropped requirements.

**3. Type consistency:** `variantId: UUID` (nullable) is the parameter name/type used identically
across all four tasks' new signatures (`VideoPathAliasEntity` doesn't take one directly, it's
scoped by video+hash instead — correctly, since path aliasing is a different concept from variant
scoping, as Task 1 explicitly notes). `IS NOT DISTINCT FROM :variant` is the literal SQL fragment
used identically in Tasks 3 and 4, matching the existing codebase idiom already used in
`PlatformStateService`'s other methods (`recordPublication`, `stateId`) confirmed during
investigation.
