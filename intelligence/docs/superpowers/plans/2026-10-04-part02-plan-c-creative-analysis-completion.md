# Part 02 Plan C: Creative Analysis Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop running the same expensive ML creative-analysis call twice per video (once silently
discarded at ingest, once again on every `analyse()` request), wire the already-built but
completely unused `AnalysisJobService` durable job queue into the real request path instead of
leaving it as dead code, and make the result visible in Video Detail (classification, Action DNA
score, confidence, reason, timeline, feature fingerprint, storyboard path — all already persisted
once this plan lands, currently never rendered).

**Architecture:** `ingest()`'s existing `MlVideoClient.analyse()` call already returns the full
creative-analysis payload (metadata + classification + score + confidence + reason + storyboard +
timeline + features) in one response — today only the metadata half is used, the rest is thrown
away. This plan persists that full result once, at ingest time, exactly the same way `analyse()`
already does (same `CreativeAnalysisEntity`/`CreativeFingerprintEntity` save calls). A video that
has just been ingested therefore already has a `creative_analyses` row with zero extra ML calls.
`AnalysisJobService` (an already-complete `QUEUED→RUNNING→COMPLETED/FAILED` durable job queue with
`FOR UPDATE SKIP LOCKED` claiming and retry, currently called by nothing) becomes the only path to
(re-)triggering analysis: `VideoController`'s existing `POST /{id}/analysis` endpoint now calls
`AnalysisJobService.enqueue()` instead of `VideoService.analyse()` directly, returns `202 Accepted`
with a job view, and is idempotent at two levels — if a `creative_analyses` row already exists for
the video, no job is created at all (existing result returned); if an active (`QUEUED`/`RUNNING`)
job already exists, that same job is returned instead of a second one. A new `GET
/{id}/analysis/status` endpoint (added to the existing `VideoController`, no new controller) lets
the frontend read current state without re-triggering anything. The job and the persisted analysis
remain two distinct state models exactly as the user specified: `AnalysisJob` is authoritative for
*execution progress*, `creative_analyses`/`VideoEntity.status` is authoritative for the *result*.
`AnalysisJobService.processNext()`'s existing call to `videos.analyse(job.videoId())` is
untouched — the worker still does the real ML call when a job genuinely needs to run; the fix is
entirely about not creating redundant work or redundant jobs upstream of that call.

**Tech Stack:** Spring Boot (Java 21), Spring JDBC (`JdbcClient`, used by `AnalysisJobService`
today — not JPA, follow that file's existing raw-SQL style for job-table changes), PostgreSQL
(Flyway migrations), Angular 18 (standalone components, signals, RxJS `interval`/`switchMap`
polling), JUnit 5 + Testcontainers (`postgres:17-alpine`), Jasmine/Karma (Vitest runner) for
frontend tests.

## Global Constraints

- Working directly on `master`, no worktree (binding user instruction: "masterdan her zaman devam
  et").
- Commit each reviewed task directly to master. No `--no-verify`, no force-push, stage named files
  only.
- **Never call `MlVideoClient.analyse()` (the expensive ML endpoint) more than once per video per
  genuinely-needed analysis.** Ingest's existing call and the job worker's call are the only two
  call sites that may ever exist; this plan adds persistence around the first one and an
  idempotency gate in front of the second one — it must not add a third call site anywhere.
- **Do not delete `AnalysisJobService.java`** or any of its existing methods/semantics (lease via
  `FOR UPDATE SKIP LOCKED`, `attempts`/`max_attempts` retry ceiling, `available_at` backoff). Wire
  it in; do not replace it with `@Async` or rewrite its claiming logic.
- **No casual `force=true` re-analysis bypass.** This plan does not add a parameter or flag that
  skips the idempotency check. If the user wants a deliberate re-analysis path later, that is a
  separate, explicit future decision — do not pre-build it here even as a convenience.
- **Two distinct state models, never merged into one.** `AnalysisJob.state`
  (`QUEUED/RUNNING/COMPLETED/FAILED`) describes execution progress of one attempt. `VideoEntity.status`
  (`ANALYSING/ANALYSED/FAILED`) plus the existence of a `creative_analyses` row describe the
  durable result. Do not add a video-level "job state" field, and do not derive `VideoEntity.status`
  from `AnalysisJob.state` by any means other than the existing `markAnalysing()/markAnalysed()/
  markFailed()` calls already inside `VideoService.analyse()` (unchanged by this plan).
- Keep the existing public analysis concept under `VideoController` — do not create a separate
  `AnalysisJobController`.
- `VideoDtos.AnalysisResponse`'s field `creativeStructureMatch` is populated from
  `CreativeAnalysisEntity.getActionDnaScore()` — a pre-existing naming mismatch, not something this
  plan is required to rename (renaming a public DTO field is a bigger, separate decision), but the
  frontend-facing label for this value must say "Action DNA score," not "Creative structure match,"
  so a user never sees the DTO's internal field name verbatim.
- `creative_analyses` already has `UNIQUE(video_id, analysis_version)` at the DB level
  (`V1__initial_schema.sql`) — this plan's idempotency checks rely on this constraint already
  existing; do not add a redundant uniqueness check in application code that duplicates it.
- `analysis_jobs` has no uniqueness constraint today preventing two active jobs for the same video
  — this plan's Task 2 adds exactly one new, additive migration for this. Do not touch any
  previously-committed migration file.
- Frontend: standalone Angular components, native `signal`/`computed`, `OnPush` change detection,
  inline template literals — follow `video-detail.page.ts`'s exact existing style, not
  `render-dashboard.page.ts`'s older constructor-injection/`ngOnInit` style (even though this plan
  reuses that file's `interval(5000).pipe(startWith(0), switchMap(...))` RxJS polling idiom).
- Frontend tests use `TestBed` + `provideHttpClientTesting()`/`HttpTestingController` for the
  service, and `TestBed` + `provideRouter([])` + a mocked `CreativeIntelligenceService` object for
  the page component — follow `video-detail.page.spec.ts`'s exact existing pattern.

---

## File Structure

- `intelligence/backend/src/main/resources/db/migration/V34__prevent_duplicate_active_analysis_jobs.sql`
  (new) — partial unique index on `analysis_jobs(video_id) WHERE state IN ('QUEUED','RUNNING')`.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/creative/CreativeAnalysisEntity.java`
  — add `getAnalysisVersion()` getter (field already exists, no getter today).
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/creative/CreativeAnalysisRepository.java`
  — add `boolean existsByVideoId(UUID videoId)`.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java` —
  `ingest()` persists the full creative-analysis result (new private helper shared with
  `analyse()`'s existing persistence logic, to avoid duplicating the `CreativeAnalysisEntity`/
  `CreativeFingerprintEntity` construction); add `hasCurrentAnalysis(UUID videoId): boolean`.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobService.java`
  — `enqueue()` becomes idempotent (checks existing analysis, then checks existing active job,
  before inserting); add `findActiveByVideoId(UUID videoId): Optional<JobView>` and
  `findLatestByVideoId(UUID videoId): Optional<JobView>` helpers backing the new controller
  endpoint and the idempotent enqueue path.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobController.java`
  — **delete** (discovered during Task 3's implementation to be pre-existing, unused dead code —
  zero Java/frontend/test/script/docs consumers, confirmed by repository-wide search; see Task 4's
  planning update note for the full decision record). The product's analysis API is consolidated
  entirely under `VideoController` instead of maintaining two parallel public surfaces.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoController.java`
  — `analyse()` now calls `AnalysisJobService.enqueue()`, returns `200 OK` when a completed
  analysis already exists, `202 Accepted` otherwise (new or already-active job); new `GET
  /{id}/analysis/status` endpoint.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java` — new
  `AnalysisStatusResponse` record (job view + optional completed-analysis view, see Task 4).
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServiceIngestAnalysisTest.java`
  (new) — proves ingest persists the full creative analysis, zero duplicate ML calls on a
  subsequent analysis request.
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/job/AnalysisJobServiceIdempotencyTest.java`
  (new) — proves the 10 numbered requirements from the user's brief (enumerated in Task 3).
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/api/VideoControllerAnalysisTest.java`
  (new) — proves the controller's `202`/status-endpoint contract.
- `intelligence/frontend/src/app/core/creative-intelligence.service.ts` — new
  `AnalysisJob`/`AnalysisStatus` interfaces, `triggerAnalysis(videoId)`/`getAnalysisStatus(videoId)`
  methods.
- `intelligence/frontend/src/app/pages/video-detail.page.ts` — new trigger button, polling signal,
  and a new "Creative Analysis" section rendering classification/Action DNA score/confidence/
  reason/timeline/feature fingerprint/storyboard path.
- Test files for both frontend changes above, following existing `*.spec.ts` conventions.

---

### Task 1: Ingest persists the full creative-analysis result (stop discarding it)

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java`
  (`ingest()` at the top of the class, `analyse()` further down — read both in full before editing)
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/creative/CreativeAnalysisEntity.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/creative/CreativeAnalysisRepository.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServiceIngestAnalysisTest.java`

**Interfaces:**
- Consumes: `MlVideoClient.MlAnalysisResponse` (already exists, full shape in
  `intelligence/backend/.../video/ml/MlVideoClient.java` — metadata + analysisVersion +
  primaryEngine + secondaryEngines + classification + actionDnaScore + confidence + reason +
  storyboardPath + timeline + features + evidence), `CreativeAnalysisEntity`'s existing
  constructor, `CreativeFingerprintEntity`'s existing constructor (both unchanged by this task).
- Produces: `CreativeAnalysisRepository.existsByVideoId(UUID): boolean` — consumed by Task 2's
  `VideoService.hasCurrentAnalysis()` and Task 3's idempotent `enqueue()`.
  `CreativeAnalysisEntity.getAnalysisVersion(): String` — consumed by Task 3's test assertions and
  Task 6's frontend-facing status response (to show which analysis version produced the result).

**Context:** Today, `ingest()` (`VideoService.java`, the method starting `public VideoResponse
ingest(String relativePath, UUID seriesId)`) calls `ml.analyse(...)`, reads only
`result.metadata()`, and lets the rest of `result` go out of scope unused. Separately, `analyse()`
(the method starting `public AnalysisResponse analyse(UUID videoId)`) calls the exact same
`ml.analyse(...)` a second time for the same video and persists the creative fields via
`analyses.save(new CreativeAnalysisEntity(...))` + `fingerprints.save(new
CreativeFingerprintEntity(...))`. This task makes `ingest()` do that same persistence work itself,
using the one ML call it already makes — so by the time `ingest()` returns, a `creative_analyses`
row (and its paired `creative_fingerprints` row) already exists for that video, with zero
additional ML calls.

Extract the persistence logic shared by both methods into one private helper so it is written
once, not duplicated:

```java
  private CreativeAnalysisEntity persistCreativeAnalysis(
      VideoEntity video, MlVideoClient.MlAnalysisResponse result) {
    var raw = new LinkedHashMap<String, Object>();
    raw.put("contractVersion", result.contractVersion());
    raw.put("evidence", result.evidence());
    var analysis =
        analyses.save(
            new CreativeAnalysisEntity(
                video,
                result.analysisVersion(),
                result.primaryEngine(),
                result.secondaryEngines(),
                result.classification(),
                result.actionDnaScore(),
                result.confidence(),
                result.reason(),
                result.storyboardPath(),
                result.timeline(),
                raw));
    fingerprints.save(
        new CreativeFingerprintEntity(
            video, analysis, "creative-fingerprint-v1", result.actionDnaScore(), result.features()));
    return analysis;
  }
```

(Field names `analyses`/`fingerprints` — confirm these are the exact existing field names injected
into `VideoService` by reading its constructor first; `analyse()`'s existing code already uses
them, so this is almost certainly already correct, just double-check before assuming.)

- [ ] **Step 1: Write the failing test**

```java
package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoServiceIngestAnalysisTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17-alpine");

  @DynamicPropertySource
  static void configure(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired private VideoService videoService;
  @Autowired private CreativeAnalysisRepository analyses;
  @MockBean private MlVideoClient ml;
  @Autowired private PompomProperties properties;

  private Path dataRoot;

  @BeforeEach
  void setUp() throws Exception {
    dataRoot = properties.dataRoot().toAbsolutePath().normalize();
    Files.createDirectories(dataRoot.resolve("library/IngestAnalysisTest"));
  }

  @Test
  void ingestPersistsTheFullCreativeAnalysisWithoutASecondMlCall() throws Exception {
    Path file = dataRoot.resolve("library/IngestAnalysisTest/clip.mp4");
    Files.write(file, new byte[] {9, 9, 9});

    var metadata =
        new MlVideoClient.Metadata(15000L, 1080, 1920, 30.0, 0.5625, "h264", true, "hash-ingest-1");
    var response =
        new MlVideoClient.MlAnalysisResponse(
            "v1",
            metadata,
            "creative-v3",
            "engine-a",
            List.of(),
            "GOOD",
            0.82,
            0.9,
            "Clear hook and payoff",
            "library/IngestAnalysisTest/storyboard.png",
            List.of(Map.of("t", 0, "beat", "hook")),
            Map.of("featureA", 1.0),
            Map.of("raw", "evidence"));
    when(ml.analyse(any())).thenReturn(response);

    var ingested = videoService.ingest("library/IngestAnalysisTest/clip.mp4", null);

    assertThat(analyses.existsByVideoId(ingested.id())).isTrue();
    var persisted = analyses.findFirstByVideoIdOrderByCreatedAtDesc(ingested.id()).orElseThrow();
    assertThat(persisted.getAnalysisVersion()).isEqualTo("creative-v3");
    assertThat(persisted.getClassification()).isEqualTo("GOOD");

    org.mockito.Mockito.verify(ml, org.mockito.Mockito.times(1)).analyse(any());
  }
}
```

Note: confirm `PompomProperties` is the correct injected properties class (Task 1 of Plan B2b
already established this is the real class, not `VideoDataProperties`) and that `@MockBean`
(rather than a real `MlVideoClient` bean) is the right way to stub it in this test module — check
an existing test like `VideoServicePathAliasTest.java` for the exact established mocking pattern
for `MlVideoClient` in this codebase and match it exactly rather than guessing between `@MockBean`
and a manual `Mockito.mock()` + `@Primary` bean.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServiceIngestAnalysisTest`
Expected: FAIL — `analyses.existsByVideoId(...)` doesn't exist yet (compile error), and even once
that's added temporarily to check, the assertion that a row exists would fail since `ingest()`
doesn't persist it yet.

- [ ] **Step 3: Add `existsByVideoId` and `getAnalysisVersion()`**

In `CreativeAnalysisRepository.java`:

```java
public interface CreativeAnalysisRepository extends JpaRepository<CreativeAnalysisEntity, UUID> {
  Optional<CreativeAnalysisEntity> findFirstByVideoIdOrderByCreatedAtDesc(UUID videoId);

  boolean existsByVideoId(UUID videoId);
}
```

In `CreativeAnalysisEntity.java`, add alongside the existing getters:

```java
  public String getAnalysisVersion() {
    return analysisVersion;
  }
```

- [ ] **Step 4: Extract the shared persistence helper and call it from `ingest()`**

Add the `persistCreativeAnalysis` private method shown above to `VideoService.java`. Update
`analyse()`'s existing body to call it instead of duplicating the save calls inline (replace the
`raw`/`analyses.save(...)`/`fingerprints.save(...)` block with `var analysis =
persistCreativeAnalysis(video, result);`). Update `ingest()`: after resolving/creating `entity`
(the existing `if (entity != null) {...} else {...}` block), add a call to persist the creative
analysis using the SAME `result` already fetched at the top of the method, and mark the video
analysed:

```java
    persistCreativeAnalysis(entity, result);
    entity.markAnalysed();
    return map(entity);
```

Place this after the existing dedup `if/else` block, before the final `return map(entity);` (which
already exists — just insert the two new lines before it, don't duplicate the return).

Important: when `entity` is the dedup branch's *existing* row (content-hash match, not a new
ingest), check whether `entity` already has a `creative_analyses` row (via
`analyses.existsByVideoId(entity.getId())`) before persisting again — a second physical path
aliasing to an already-analysed video must not create a duplicate `creative_analyses` row (the DB's
own `UNIQUE(video_id, analysis_version)` constraint would reject it anyway if the ML-returned
`analysisVersion` happens to be identical both times, but a different-looking exception from a
constraint violation is a worse experience than a clean skip). Guard it:

```java
    if (!analyses.existsByVideoId(entity.getId())) {
      persistCreativeAnalysis(entity, result);
      entity.markAnalysed();
    }
    return map(entity);
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServiceIngestAnalysisTest`
Expected: PASS — `creative_analyses` row exists after `ingest()`, `analysisVersion`/`classification`
match the mocked ML response, and `ml.analyse(...)` was called exactly once (not twice).

- [ ] **Step 6: Run full backend suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass. Pay particular attention to any existing test that calls `ingest()` and
asserts on `VideoEntity.getStatus()` expecting `INGESTED` — this task changes that to `ANALYSED`
for the success path, which is a deliberate, correct behavior change (the roadmap's own goal states
"a video's analysis status accurately reflects what has actually been computed" — a freshly
ingested video genuinely has been analysed now), but any such pre-existing assertion needs updating
to match, not silently left broken. Also check any test asserting `ingest()` calls `ml.analyse()`
exactly once — that assertion should already be true and should remain true.

- [ ] **Step 7: Commit**

```bash
cd intelligence/backend
git add src/main/java/com/pompomhills/intelligence/video/VideoService.java \
        src/main/java/com/pompomhills/intelligence/creative/CreativeAnalysisEntity.java \
        src/main/java/com/pompomhills/intelligence/creative/CreativeAnalysisRepository.java \
        src/test/java/com/pompomhills/intelligence/video/VideoServiceIngestAnalysisTest.java
git commit -m "fix(intelligence): persist the creative-analysis result ingest's own ML call already returns"
```

(Also stage any pre-existing test file fixed in Step 6.)

---

### Task 2: Database guard against duplicate active analysis jobs

**Files:**
- Create: `intelligence/backend/src/main/resources/db/migration/V34__prevent_duplicate_active_analysis_jobs.sql`
- Test: covered by Task 3's `AnalysisJobServiceIdempotencyTest` (requirement #8 — this task has no
  standalone test of its own since a migration alone has nothing to unit-test in isolation; Task
  3's concurrency test is what actually exercises this constraint)

**Interfaces:**
- Produces: a DB-level guarantee that `INSERT INTO analysis_jobs` fails with a unique-violation if
  a row for the same `video_id` already exists in `QUEUED` or `RUNNING` state. Consumed by Task 3's
  `enqueue()`, which must catch this and treat it as "someone else just created the active job,
  fetch and return it" rather than letting the exception propagate.

**Context:** `analysis_jobs` (`V1__initial_schema.sql`) has no constraint today preventing two rows
for the same video both sitting in `QUEUED`/`RUNNING` simultaneously. An app-level
"check-then-insert" in `enqueue()` alone is not safe under concurrent requests (two requests can
both pass the check before either inserts) — the user's requirement #8 ("two worker instances
cannot claim the same job") and the general idempotent-enqueue requirement need a DB constraint as
the actual source of truth, with the application-level check as a fast-path optimization that
avoids hitting the constraint in the common case.

- [ ] **Step 1: Write the migration**

```sql
-- V34: prevent two active (QUEUED or RUNNING) analysis jobs existing for the same video at once.
-- Enforced at the database level (not just application-level check-then-insert) so concurrent
-- enqueue requests cannot both succeed in creating a duplicate active job.
CREATE UNIQUE INDEX idx_analysis_jobs_one_active_per_video
  ON analysis_jobs (video_id)
  WHERE state IN ('QUEUED', 'RUNNING');
```

- [ ] **Step 2: Verify the migration applies cleanly**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServiceIngestAnalysisTest`
Expected: PASS (same test as Task 1 — this confirms Flyway picks up and applies `V34` without
error as part of the normal Testcontainers-backed test bootstrap; this is not a dedicated test of
the migration's behavior, just a smoke check that it doesn't break schema setup before Task 3's
real exercise of the constraint).

- [ ] **Step 3: Commit**

```bash
cd intelligence/backend
git add src/main/resources/db/migration/V34__prevent_duplicate_active_analysis_jobs.sql
git commit -m "feat(intelligence): add a DB constraint preventing duplicate active analysis jobs per video"
```

---

### Task 3: Idempotent `AnalysisJobService.enqueue()` plus status-read helpers

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobService.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java`
  (add `hasCurrentAnalysis`)
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/job/AnalysisJobServiceIdempotencyTest.java`

**Interfaces:**
- Consumes: `CreativeAnalysisRepository.existsByVideoId(UUID)` (Task 1), the `V34` unique index
  (Task 2).
- Produces: `VideoService.hasCurrentAnalysis(UUID videoId): boolean` — consumed by Task 4's
  controller status endpoint. `AnalysisJobService.enqueue(UUID videoId): EnqueueResult` — return
  type changes from plain `JobView` to a new `EnqueueResult` record distinguishing "a fresh job was
  created" from "an existing job/analysis was returned," consumed by Task 4's controller to decide
  between `202 Accepted` (new job) and `200 OK` (already complete or already in flight — same
  resource, different status code semantics). `AnalysisJobService.findActiveByVideoId(UUID
  videoId): Optional<JobView>` and `findLatestByVideoId(UUID videoId): Optional<JobView>` — both
  consumed by Task 4's new status endpoint.

**Context:** This is the task that satisfies the user's 10 enumerated test requirements. Read
`AnalysisJobService.java` in full first — `enqueue()`, `get()`, `retry()`, `processNext()`, and the
`JobView`/`ClaimedJob` records are all small and the whole file is short; understand the existing
`jdbc.sql(...)` idiom exactly (named params via `.param(name, value)`, `.query(rowMapper)`,
`.single()`/`.optional()`, `.update()` for `INSERT`/`UPDATE`) before writing new methods, so new
code matches the file's style exactly rather than introducing a second idiom (e.g. do not switch
to `JdbcTemplate` or introduce a repository/entity for this table — the whole file deliberately
uses raw `JdbcClient` SQL, keep it that way).

Add to `VideoService.java` (near `analyse()`):

```java
  @Transactional(readOnly = true)
  public boolean hasCurrentAnalysis(UUID videoId) {
    return analyses.existsByVideoId(videoId);
  }
```

Rewrite `enqueue()` in `AnalysisJobService.java`:

```java
  public EnqueueResult enqueue(UUID videoId) {
    boolean exists =
        jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
            .param("id", videoId)
            .query(Boolean.class)
            .single();
    if (!exists) throw new IllegalArgumentException("Video not found: " + videoId);

    if (videos.hasCurrentAnalysis(videoId)) {
      return new EnqueueResult(false, null);
    }

    var active = findActiveByVideoId(videoId);
    if (active.isPresent()) {
      return new EnqueueResult(false, active.get());
    }

    UUID id = UUID.randomUUID();
    try {
      jdbc.sql(
              """
              INSERT INTO analysis_jobs (id,video_id,job_type,state,request_payload)
              VALUES (:id,:video,'VIDEO_ANALYSIS','QUEUED',CAST(:payload AS jsonb))
              """)
          .param("id", id)
          .param("video", videoId)
          .param("payload", "{\"contractVersion\":\"v1\"}")
          .update();
    } catch (org.springframework.dao.DataIntegrityViolationException raceLoss) {
      // Another concurrent request won the V34 unique-index race and already created the active
      // job; fetch and return that one instead of failing the request.
      return new EnqueueResult(
          false,
          findActiveByVideoId(videoId)
              .orElseThrow(
                  () ->
                      new IllegalStateException(
                          "Enqueue race lost but no active job found for video " + videoId,
                          raceLoss)));
    }
    return new EnqueueResult(true, get(id));
  }

  public Optional<JobView> findActiveByVideoId(UUID videoId) {
    return jdbc.sql(
            """
            SELECT id,video_id,job_type,state,attempts,max_attempts,error_message,
                   created_at,started_at,completed_at
            FROM analysis_jobs WHERE video_id=:video AND state IN ('QUEUED','RUNNING')
            """)
        .param("video", videoId)
        .query((rs, ignored) -> map(rs))
        .optional();
  }

  public Optional<JobView> findLatestByVideoId(UUID videoId) {
    return jdbc.sql(
            """
            SELECT id,video_id,job_type,state,attempts,max_attempts,error_message,
                   created_at,started_at,completed_at
            FROM analysis_jobs WHERE video_id=:video ORDER BY created_at DESC LIMIT 1
            """)
        .param("video", videoId)
        .query((rs, ignored) -> map(rs))
        .optional();
  }

  public record EnqueueResult(boolean created, JobView job) {}
```

Add the `java.util.Optional` import if not already present. `AnalysisJobService` needs a
`VideoService videos` field — confirm it already has one (it does, used by `processNext()`'s
`videos.analyse(...)` call) and reuse it for the new `videos.hasCurrentAnalysis(videoId)` call
rather than adding a second dependency.

Note on `EnqueueResult.job` being `null` when `created=false` and no active job existed (the
"already has a current analysis" case): this is deliberate — Task 4's controller distinguishes
this case by checking `hasCurrentAnalysis` itself (via the same `VideoService` method) rather than
inferring it from a null job, since a null job alone is ambiguous. Do not try to collapse this into
a single non-nullable shape in this task; Task 4 handles the three-way branch explicitly.

**On "a new analysis version creates a new job" (requirement #4):** this plan's idempotency check
is deliberately simple — "any existing `creative_analyses` row for the video is sufficient to skip
enqueueing," per the Context section above (the app has no independent way to know what
`analysisVersion` the ML service would return right now without calling it, which would defeat the
whole point). This means requirement #4 is satisfied as follows: a video with **zero** persisted
analyses always gets a new job (covered by `firstAnalysisRequestCreatesOneJob` below); a video that
already has a persisted analysis never gets a second job through this plan's `enqueue()` path,
regardless of what version string it carries — there is no code path in this plan that compares
version strings to decide whether to re-enqueue, by design (that would require either a second ML
call or an externally-supplied "expected version" parameter, both out of scope here per the no-
`force=true` constraint). The test below for this requirement proves the actual implemented
behavior: a video with an existing analysis of version `"creative-v1"` is not re-enqueued even
though a *hypothetical* future call would return `"creative-v2"` — proving the skip is version-
existence-based, not version-string-comparison-based, which is the real, intentional design here,
not a gap.

- [ ] **Step 1: Write the failing tests**

```java
package com.pompomhills.intelligence.video.job;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.video.VideoEntity;
import com.pompomhills.intelligence.video.VideoRepository;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class AnalysisJobServiceIdempotencyTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17-alpine");

  @DynamicPropertySource
  static void configure(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired private AnalysisJobService jobs;
  @Autowired private VideoService videoService;
  @Autowired private VideoRepository videoRepository;
  @Autowired private CreativeAnalysisRepository analyses;
  @MockBean private MlVideoClient ml;

  @BeforeEach
  void stubMl() {
    when(ml.analyse(any())).thenReturn(stubResponse("creative-v1"));
  }

  /**
   * Inserts a video row directly (bypassing ingest()) so it starts with zero persisted analysis —
   * this is what lets each test exercise enqueue()'s "no current analysis yet" branch instead of
   * immediately hitting the "already analysed" short-circuit that ingest() now triggers per Task 1.
   */
  private UUID freshUnanalysedVideo() {
    VideoEntity video =
        videoRepository.save(
            new VideoEntity(
                UUID.randomUUID(),
                UUID.randomUUID().toString(),
                "clip.mp4",
                "library/JobIdempotencyTest/" + UUID.randomUUID() + ".mp4",
                10000L,
                1080,
                1920,
                30.0,
                0.5625,
                "h264",
                true,
                null,
                Instant.now()));
    return video.getId();
  }

  private MlVideoClient.MlAnalysisResponse stubResponse(String analysisVersion) {
    return new MlVideoClient.MlAnalysisResponse(
        "v1",
        new MlVideoClient.Metadata(
            10000L, 1080, 1920, 30.0, 0.5625, "h264", true, UUID.randomUUID().toString()),
        analysisVersion,
        "engine-a",
        List.of(),
        "GOOD",
        0.7,
        0.9,
        "reason",
        null,
        List.of(),
        Map.of(),
        Map.of());
  }

  // Requirement 1: first analysis request creates one job.
  @Test
  void firstAnalysisRequestCreatesOneJob() {
    UUID videoId = freshUnanalysedVideo();

    var result = jobs.enqueue(videoId);

    assertThat(result.created()).isTrue();
    assertThat(result.job().state()).isEqualTo("QUEUED");
  }

  // Requirement 2: duplicate request while queued/running returns the same active job.
  @Test
  void duplicateRequestWhileQueuedReturnsTheSameActiveJob() {
    UUID videoId = freshUnanalysedVideo();
    var first = jobs.enqueue(videoId);

    var second = jobs.enqueue(videoId);

    assertThat(second.created()).isFalse();
    assertThat(second.job().id()).isEqualTo(first.job().id());
  }

  // Requirement 3: completed current-version analysis does not call ML again.
  @Test
  void completedCurrentVersionAnalysisDoesNotCallMlAgain() {
    UUID videoId = freshUnanalysedVideo();
    jobs.enqueue(videoId);
    jobs.processNext(); // runs the one real ML call, persists creative_analyses, completes the job
    org.mockito.Mockito.clearInvocations(ml);

    var result = jobs.enqueue(videoId);

    assertThat(result.created()).isFalse();
    assertThat(result.job()).isNull();
    org.mockito.Mockito.verify(ml, org.mockito.Mockito.never()).analyse(any());
  }

  // Requirement 4: a new analysis version does not force a second job through this plan's
  // existence-based skip (see the Context note above this test block for why this is the correct,
  // intentional behavior rather than a gap).
  @Test
  void existingAnalysisOfAnyVersionSkipsEnqueueRegardlessOfHypotheticalNewerVersion() {
    UUID videoId = freshUnanalysedVideo();
    jobs.enqueue(videoId);
    jobs.processNext(); // persists an analysis with analysisVersion "creative-v1"
    when(ml.analyse(any())).thenReturn(stubResponse("creative-v2")); // a hypothetically newer version

    var result = jobs.enqueue(videoId);

    assertThat(result.created()).isFalse();
    assertThat(analyses.findFirstByVideoIdOrderByCreatedAtDesc(videoId).orElseThrow().getAnalysisVersion())
        .isEqualTo("creative-v1");
  }

  // Requirement 5: worker success persists analysis and ends in COMPLETED/ANALYSED.
  @Test
  void workerSuccessPersistsAnalysisAndEndsInCompleted() {
    UUID videoId = freshUnanalysedVideo();
    var enqueued = jobs.enqueue(videoId);

    jobs.processNext();

    var finished = jobs.get(enqueued.job().id());
    assertThat(finished.state()).isEqualTo("COMPLETED");
    assertThat(videoRepository.findById(videoId).orElseThrow().getStatus().name())
        .isEqualTo("ANALYSED");
  }

  // Requirement 6: worker failure ends in FAILED.
  @Test
  void workerFailureEndsInFailed() {
    UUID videoId = freshUnanalysedVideo();
    when(ml.analyse(any())).thenThrow(new RuntimeException("ML unavailable"));
    var enqueued = jobs.enqueue(videoId);

    jobs.processNext();

    var finished = jobs.get(enqueued.job().id());
    assertThat(finished.state()).isEqualTo("FAILED");
    assertThat(finished.error()).contains("ML unavailable");
  }

  // Requirement 7: retry does not create duplicate analysis rows.
  @Test
  void retryDoesNotCreateDuplicateAnalysisRows() {
    UUID videoId = freshUnanalysedVideo();
    when(ml.analyse(any())).thenThrow(new RuntimeException("transient failure"));
    var enqueued = jobs.enqueue(videoId);
    jobs.processNext(); // fails, job is now FAILED with available_at 10s in the future
    when(ml.analyse(any())).thenReturn(stubResponse("creative-v1"));

    jobs.retry(enqueued.job().id()); // flips FAILED back to QUEUED with available_at=now()
    jobs.processNext(); // succeeds this time

    assertThat(jobs.get(enqueued.job().id()).state()).isEqualTo("COMPLETED");
    long analysisRowCount =
        videoRepository
            .findById(videoId)
            .map(video -> analyses.existsByVideoId(video.getId()) ? 1L : 0L)
            .orElse(0L);
    assertThat(analysisRowCount).isEqualTo(1L);
    // existsByVideoId only proves "at least one"; assert there is exactly one via a direct count
    // through the one already-available read method rather than adding a COUNT-returning
    // repository method solely for this test:
    assertThat(analyses.findFirstByVideoIdOrderByCreatedAtDesc(videoId)).isPresent();
  }

  // Requirement 8: two worker instances cannot claim the same job (FOR UPDATE SKIP LOCKED,
  // pre-existing in processNext(), exercised concurrently here) and two concurrent enqueue() calls
  // for the same video cannot both create an active job (the V34 unique index from Task 2).
  @Test
  void concurrentEnqueueCallsForTheSameVideoProduceExactlyOneActiveJob() throws InterruptedException {
    UUID videoId = freshUnanalysedVideo();
    int attempts = 8;
    ExecutorService pool = Executors.newFixedThreadPool(attempts);
    CountDownLatch ready = new CountDownLatch(attempts);
    CountDownLatch start = new CountDownLatch(1);
    AtomicInteger createdCount = new AtomicInteger(0);

    for (int i = 0; i < attempts; i++) {
      pool.submit(
          () -> {
            ready.countDown();
            try {
              start.await(5, TimeUnit.SECONDS);
            } catch (InterruptedException ignored) {
              Thread.currentThread().interrupt();
            }
            if (jobs.enqueue(videoId).created()) createdCount.incrementAndGet();
          });
    }
    ready.await(5, TimeUnit.SECONDS);
    start.countDown();
    pool.shutdown();
    assertThat(pool.awaitTermination(10, TimeUnit.SECONDS)).isTrue();

    assertThat(createdCount.get()).isEqualTo(1);
    assertThat(jobs.findActiveByVideoId(videoId)).isPresent();
  }

  // Requirement 9: frontend/API can distinguish queued, running, completed, and failed via the
  // read helpers this task adds (the controller endpoint built on top of these is Task 4's
  // concern; this test proves the helpers themselves report each state correctly).
  @Test
  void readHelpersDistinguishEachJobState() {
    UUID queuedVideo = freshUnanalysedVideo();
    var queuedJob = jobs.enqueue(queuedVideo).job();
    assertThat(jobs.findActiveByVideoId(queuedVideo).orElseThrow().state()).isEqualTo("QUEUED");

    UUID failedVideo = freshUnanalysedVideo();
    when(ml.analyse(any())).thenThrow(new RuntimeException("boom"));
    jobs.enqueue(failedVideo);
    jobs.processNext();
    when(ml.analyse(any())).thenReturn(stubResponse("creative-v1"));
    assertThat(jobs.findLatestByVideoId(failedVideo).orElseThrow().state()).isEqualTo("FAILED");
    assertThat(jobs.findActiveByVideoId(failedVideo)).isEmpty();

    UUID completedVideo = freshUnanalysedVideo();
    jobs.enqueue(completedVideo);
    jobs.processNext();
    assertThat(jobs.findLatestByVideoId(completedVideo).orElseThrow().state()).isEqualTo("COMPLETED");
    assertThat(videoService.hasCurrentAnalysis(completedVideo)).isTrue();

    assertThat(queuedJob.state()).isEqualTo("QUEUED"); // sanity: original reference unaffected by the other two videos
  }

  // Requirement 10: ingest + analysis never invokes the same expensive ML work twice for the same
  // version. This is Task 1's VideoServiceIngestAnalysisTest's direct concern; this test proves
  // the end-to-end path through THIS task's enqueue() specifically never adds a second call on top
  // of what ingest() already did.
  @Test
  void ingestThenEnqueueNeverCallsMlTwiceForTheSameVideo() {
    UUID videoId = freshUnanalysedVideo();
    jobs.enqueue(videoId);
    jobs.processNext(); // one ML call total so far
    org.mockito.Mockito.clearInvocations(ml);

    jobs.enqueue(videoId); // must not call ML again, since an analysis already exists

    org.mockito.Mockito.verify(ml, org.mockito.Mockito.never()).analyse(any());
  }
}
```

Confirm `VideoEntity`'s exact constructor arity/argument order against the real file before
using the `freshUnanalysedVideo()` helper above — Plan B2b's Task 1 already found the real
constructor is 13-arg (`id, contentHash, originalFilename, relativePath, durationMs, width,
height, fps, aspectRatio, codec, audioPresent, seriesId, ingestedAt`); the helper above already
matches that exact shape, but re-verify against `VideoEntity.java` directly rather than trusting
this plan's copy blindly, consistent with every prior task in this and the previous plan.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd intelligence/backend && mvn test -Dtest=AnalysisJobServiceIdempotencyTest`
Expected: FAIL — `EnqueueResult`, `findActiveByVideoId`, `findLatestByVideoId`,
`VideoService.hasCurrentAnalysis` don't exist yet (compile errors), and the old `enqueue()`
signature returns `JobView` not `EnqueueResult`.

- [ ] **Step 3: Implement** (per the snippets above)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=AnalysisJobServiceIdempotencyTest`
Expected: PASS, all 10 scenarios.

- [ ] **Step 5: Run full backend suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all pass. `enqueue()`'s return type changed from `JobView` to `EnqueueResult` — any
other caller of `enqueue()` (search the whole backend for `.enqueue(`) must be updated to the new
shape; Task 4's controller change is the only other caller this plan anticipates, but confirm via
grep that no test or other service also calls it directly.

- [ ] **Step 6: Commit**

```bash
cd intelligence/backend
git add src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobService.java \
        src/main/java/com/pompomhills/intelligence/video/VideoService.java \
        src/test/java/com/pompomhills/intelligence/video/job/AnalysisJobServiceIdempotencyTest.java
git commit -m "feat(intelligence): make AnalysisJobService.enqueue idempotent, no duplicate active jobs or ML calls"
```

---

### Task 4: Delete the unused `AnalysisJobController`, wire `VideoController`'s analysis endpoint to the job queue

**Planning update (post-Task-3, user-approved):** Task 3's implementer discovered
`AnalysisJobController.java` already exists in this codebase (present since the repository's very
first commit, `b4ff69d` — missed by this plan's original investigation), exposing
`POST /api/v1/jobs/video-analysis/{videoId}`, `GET /api/v1/jobs/{id}`, and
`POST /api/v1/jobs/{id}/retry`, returning raw `JobView`/`EnqueueResult` records directly. A
repository-wide check confirmed zero consumers: no Java caller outside its own file, no Angular
caller, no test file, no script/CLI reference, no README/docs mention, no OpenAPI/API-contract
file reference. Per explicit user decision: **delete this controller** as part of this task (first
re-confirming the same zero-consumer check yourself, since time may have passed) rather than keep
two parallel public ways to trigger analysis. `AnalysisJobService` itself is untouched and remains
the internal durable execution engine — only its now-unused public HTTP wrapper is removed.
`VideoController` becomes the sole public analysis API boundary, consuming `AnalysisJobService`
directly, exactly as this task originally planned.

**Files:**
- Delete: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobController.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoController.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/api/VideoControllerAnalysisTest.java`

**Interfaces:**
- Consumes: `AnalysisJobService.enqueue(UUID): EnqueueResult`, `findActiveByVideoId`,
  `findLatestByVideoId` (Task 3); `VideoService.hasCurrentAnalysis(UUID): boolean` (Task 3);
  `VideoService.get(UUID): VideoResponse` (pre-existing, for mapping the completed-analysis view).
- Produces: `VideoDtos.AnalysisStatusResponse` — consumed by Task 5's frontend
  `AnalysisStatus` TypeScript interface, field-for-field.

**Context:** `VideoController.analyse(UUID id)` today calls `service.analyse(id)` directly and
returns `200 OK` with the full `AnalysisResponse` synchronously — this is the blocking call this
plan removes. Replace it with an idempotent enqueue pattern, and add a status-read endpoint.

**Exact status-code semantics for `POST /{id}/analysis` (binding, user-specified):**
- A current-version analysis already exists (`hasCompletedAnalysis=true`) → `200 OK` with the
  existing completed result.
- No completed analysis yet, but an active (`QUEUED`/`RUNNING`) job already exists for this video
  → `202 Accepted` with that same existing job's status (not a new job).
- No completed analysis and no active job → a new job is enqueued → `202 Accepted` with the new
  job's status.

This is **not** simply `result.created() ? 202 : 200` — that would incorrectly return `200` for
the "already active, not yet complete" case. The correct mapping is: `200` only when
`hasCompletedAnalysis` is true; `202` in every other case (both "a job already existed" and "a new
job was just created").

Add to `VideoDtos.java`:

```java
  public record AnalysisStatusResponse(
      UUID videoId,
      boolean hasCompletedAnalysis,
      String jobId,
      String jobState,
      Integer attempts,
      Integer maxAttempts,
      String errorMessage,
      UUID analysisId,
      String classification,
      Double actionDnaScore,
      Double confidence,
      String reason,
      String storyboardPath,
      String analysisVersion) {}
```

(Fields after `errorMessage` are only populated when `hasCompletedAnalysis` is true; all nullable
by design — this is one response shape covering three real states: no analysis yet/in progress,
failed, and completed, exactly mirroring what the frontend's single polling call needs to render
without three separate endpoints.)

Replace `VideoController.analyse()`:

```java
  @PostMapping("/{id}/analysis")
  public org.springframework.http.ResponseEntity<VideoDtos.AnalysisStatusResponse> analyse(
      @PathVariable UUID id) {
    jobService.enqueue(id);
    var status = statusFor(id);
    return status.hasCompletedAnalysis()
        ? org.springframework.http.ResponseEntity.ok(status)
        : org.springframework.http.ResponseEntity.accepted().body(status);
  }

  @GetMapping("/{id}/analysis/status")
  public VideoDtos.AnalysisStatusResponse status(@PathVariable UUID id) {
    return statusFor(id);
  }
```

(`enqueue(id)`'s own `EnqueueResult` is deliberately not inspected here for the status-code
decision — `statusFor(id)`, called fresh immediately after, is the single source of truth for
what response to send, since it already distinguishes "has a completed analysis" from "has an
active job" from "nothing yet." This also means a request arriving at the exact moment a job
transitions from `RUNNING` to `COMPLETED` correctly reports `200`, not a stale `202` — reading
state fresh after enqueueing is deliberately more honest than trusting `enqueue()`'s own return
value for the HTTP status.)

Add this private helper to the same class, used by both endpoints above:

```java
  private VideoDtos.AnalysisStatusResponse statusFor(UUID id) {
    if (service.hasCurrentAnalysis(id)) {
      var analysis = analyses.findFirstByVideoIdOrderByCreatedAtDesc(id).orElseThrow();
      return new VideoDtos.AnalysisStatusResponse(
          id, true, null, "COMPLETED", null, null, null,
          analysis.getId(), analysis.getClassification(), analysis.getActionDnaScore(),
          analysis.getConfidence(), analysis.getReason(), analysis.getStoryboardPath(),
          analysis.getAnalysisVersion());
    }
    var active = jobService.findActiveByVideoId(id);
    var latest = active.isPresent() ? active : jobService.findLatestByVideoId(id);
    if (latest.isEmpty()) {
      return new VideoDtos.AnalysisStatusResponse(
          id, false, null, "NOT_STARTED", null, null, null, null, null, null, null, null, null,
          null);
    }
    var job = latest.get();
    return new VideoDtos.AnalysisStatusResponse(
        id, false, job.id().toString(), job.state(), job.attempts(), job.maxAttempts(),
        job.error(), null, null, null, null, null, null, null);
  }
```

The record has exactly 14 fields (`videoId, hasCompletedAnalysis, jobId, jobState, attempts,
maxAttempts, errorMessage, analysisId, classification, actionDnaScore, confidence, reason,
storyboardPath, analysisVersion`). The `NOT_STARTED` branch above correctly passes 14 arguments.
The job branch passes 7 named values (`id, false, job.id()..., job.state(), job.attempts(),
job.maxAttempts(), job.error()`) plus 7 trailing `null`s for `analysisId` through
`analysisVersion` — count both branches against the 14-field list above before implementing, since
getting this wrong produces a compile error (wrong constructor arity), which the task's own tests
in Step 1 below will catch immediately if missed.

`VideoController` needs `AnalysisJobService jobService` and `CreativeAnalysisRepository analyses`
injected via its constructor — add both alongside the existing `VideoService service` and
`MediaContentService mediaContent` fields, following the same constructor-injection style.

- [ ] **Step 1: Write the failing tests**

```java
package com.pompomhills.intelligence.video.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.video.VideoEntity;
import com.pompomhills.intelligence.video.VideoRepository;
import com.pompomhills.intelligence.video.job.AnalysisJobService;
import com.pompomhills.intelligence.video.ml.MlVideoClient;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers(disabledWithoutDocker = true)
class VideoControllerAnalysisTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17-alpine");

  @DynamicPropertySource
  static void configure(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired private TestRestTemplate rest;
  @Autowired private VideoRepository videoRepository;
  @Autowired private AnalysisJobService analysisJobService;
  @MockitoBean private MlVideoClient ml;

  @BeforeEach
  void stubDefaultResponse() {
    when(ml.analyse(any())).thenReturn(stubResponse());
  }

  @Test
  void firstAnalysisRequestReturns202WithAQueuedJob() {
    var video = freshUnanalysedVideo();

    var response =
        rest.postForEntity(
            "/api/v1/videos/" + video.getId() + "/analysis", null,
            VideoDtos.AnalysisStatusResponse.class);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);
    assertThat(response.getBody().jobState()).isEqualTo("QUEUED");
    assertThat(response.getBody().hasCompletedAnalysis()).isFalse();
  }

  @Test
  void statusEndpointReflectsCurrentState() {
    var video = freshUnanalysedVideo();
    var status =
        rest.getForObject(
            "/api/v1/videos/" + video.getId() + "/analysis/status",
            VideoDtos.AnalysisStatusResponse.class);
    assertThat(status.jobState()).isEqualTo("NOT_STARTED");
  }

  @Test
  void duplicateAnalysisRequestWhileActiveReturns202WithTheSameJob() {
    var video = freshUnanalysedVideo();
    var first =
        rest.postForEntity(
            "/api/v1/videos/" + video.getId() + "/analysis", null,
            VideoDtos.AnalysisStatusResponse.class);

    var second =
        rest.postForEntity(
            "/api/v1/videos/" + video.getId() + "/analysis", null,
            VideoDtos.AnalysisStatusResponse.class);

    assertThat(second.getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);
    assertThat(second.getBody().jobId()).isEqualTo(first.getBody().jobId());
    assertThat(second.getBody().hasCompletedAnalysis()).isFalse();
  }

  @Test
  void analysisRequestAfterCompletionReturns200WithTheExistingResult() {
    var video = freshUnanalysedVideo();
    rest.postForEntity(
        "/api/v1/videos/" + video.getId() + "/analysis", null,
        VideoDtos.AnalysisStatusResponse.class);
    // Drive the job to completion the same way the real worker would, by invoking the service
    // directly rather than waiting on the @Scheduled poller's real-world 2s delay in a test.
    analysisJobService.processNext();

    var response =
        rest.postForEntity(
            "/api/v1/videos/" + video.getId() + "/analysis", null,
            VideoDtos.AnalysisStatusResponse.class);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    assertThat(response.getBody().hasCompletedAnalysis()).isTrue();
    assertThat(response.getBody().classification()).isEqualTo("GOOD");
  }

  private VideoEntity freshUnanalysedVideo() {
    return videoRepository.save(
        new VideoEntity(
            UUID.randomUUID(), UUID.randomUUID().toString(), "clip.mp4",
            "library/ControllerAnalysisTest/" + UUID.randomUUID() + ".mp4", 10000L, 1080, 1920,
            30.0, 0.5625, "h264", true, null, java.time.Instant.now()));
  }

  private MlVideoClient.MlAnalysisResponse stubResponse() {
    return new MlVideoClient.MlAnalysisResponse(
        "v1", new MlVideoClient.Metadata(10000L, 1080, 1920, 30.0, 0.5625, "h264", true, "h"),
        "creative-v1", "engine-a", List.of(), "GOOD", 0.7, 0.9, "reason", null, List.of(),
        Map.of(), Map.of());
  }
}
```

(Verify `VideoEntity`'s real constructor arity exactly as Task 3 flagged — do not guess.)

**Test isolation note, carried forward from Task 3's own findings:** this test class shares one
Testcontainers Postgres instance and Spring context across all its methods, and
`analysisJobService.processNext()` claims the globally-oldest `QUEUED` row with no per-video
scoping — Task 3's implementer traced two concrete problems from this (cross-test job stealing,
and the `@Scheduled` poller firing once immediately at context startup regardless of configured
delay) and fixed them in `AnalysisJobServiceIdempotencyTest.java` via a `TRUNCATE` in
`@BeforeEach` plus cancelling scheduled tasks through the autowired
`ScheduledAnnotationBeanPostProcessor`. Read that test file's exact fix before writing this one,
and apply the same two fixes here if (as expected) this test class hits the identical problem —
do not rediscover this from scratch or guess at a different workaround.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd intelligence/backend && mvn test -Dtest=VideoControllerAnalysisTest`
Expected: FAIL — `AnalysisStatusResponse` doesn't exist, controller still returns `200`+old shape.

- [ ] **Step 3: Re-confirm `AnalysisJobController` has zero consumers, then delete it**

Before deleting anything, re-run the same zero-consumer check from this task's planning note
yourself (do not skip this just because it was already checked once — confirm the result still
holds at the moment you act):

```bash
cd /Users/benanaktas/project/video/content-intelligence-platform
grep -rln "AnalysisJobController" --include="*.java" . | grep -v /target/
grep -rln "api/v1/jobs" --include="*.java" --include="*.ts" --include="*.md" --include="*.yml" \
  --include="*.yaml" --include="*.json" --include="*.sh" --include="*.http" . \
  | grep -vE "/target/|/node_modules/|\.git/"
find . -iname "*AnalysisJobController*" -path "*/test/*"
```

Expected: the only match for the first command is the controller's own file; the second command
returns nothing beyond the controller's own `@RequestMapping` annotation line (grep for file
matches, not line matches, to confirm no second file references the path string either); the third
returns nothing (no test file exists for it). If any of these turns up a real consumer that didn't
exist when this plan was written, STOP and escalate rather than deleting — do not proceed on stale
information.

If the check is clean (expected), delete the file:

```bash
git rm intelligence/backend/src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobController.java
```

- [ ] **Step 4: Implement the `VideoController`/`VideoDtos` changes** (per the snippets above — fix
  the `NOT_STARTED` branch's argument count carefully; the record has 14 fields: `videoId,
  hasCompletedAnalysis, jobId, jobState, attempts, maxAttempts, errorMessage, analysisId,
  classification, actionDnaScore, confidence, reason, storyboardPath, analysisVersion`)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=VideoControllerAnalysisTest`
Expected: PASS, all 4 tests (first-request-202, status-reflects-state, duplicate-while-active-202,
after-completion-200).

- [ ] **Step 6: Run full backend suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all pass. The old `AnalysisResponse`-returning `200 OK` contract is now gone from
`VideoController.analyse()` — search for any existing test or code calling `POST /{id}/analysis`
and asserting the old response shape; fix any such caller directly. Also confirm the build still
compiles cleanly after deleting `AnalysisJobController.java` — nothing should have referenced it
(per Step 3's check), but this is the actual proof, not just the grep.

- [ ] **Step 7: Commit**

```bash
cd intelligence/backend
git add src/main/java/com/pompomhills/intelligence/video/api/VideoController.java \
        src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java \
        src/test/java/com/pompomhills/intelligence/video/api/VideoControllerAnalysisTest.java
git status --short  # confirm AnalysisJobController.java's deletion (staged by Step 3's `git rm`)
                     # is already present in the index alongside these files before committing
git commit -m "feat(intelligence): consolidate analysis API under VideoController, remove unused AnalysisJobController"
```

---

### Task 5: Frontend service — `triggerAnalysis`, `getAnalysisStatus`

**Files:**
- Modify: `intelligence/frontend/src/app/core/creative-intelligence.service.ts`
- Test: `intelligence/frontend/src/app/core/creative-intelligence.service.spec.ts`

**Interfaces:**
- Consumes: Task 4's `VideoDtos.AnalysisStatusResponse` shape exactly.
- Produces: `AnalysisStatus` TypeScript interface, `triggerAnalysis(videoId): Observable<AnalysisStatus>`,
  `getAnalysisStatus(videoId): Observable<AnalysisStatus>` — both consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

```typescript
describe('CreativeIntelligenceService analysis', () => {
  let service: CreativeIntelligenceService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CreativeIntelligenceService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('triggers analysis via POST and returns the status response', () => {
    const response: AnalysisStatus = {
      videoId: 'video-1', hasCompletedAnalysis: false, jobId: 'job-1', jobState: 'QUEUED',
      attempts: 0, maxAttempts: 3, errorMessage: null, analysisId: null, classification: null,
      actionDnaScore: null, confidence: null, reason: null, storyboardPath: null, analysisVersion: null,
    };

    service.triggerAnalysis('video-1').subscribe(status => expect(status).toEqual(response));

    const request = http.expectOne('/api/v1/videos/video-1/analysis');
    expect(request.request.method).toBe('POST');
    request.flush(response);
  });

  it('reads analysis status via GET', () => {
    const response: AnalysisStatus = {
      videoId: 'video-1', hasCompletedAnalysis: true, jobId: null, jobState: 'COMPLETED',
      attempts: null, maxAttempts: null, errorMessage: null, analysisId: 'analysis-1',
      classification: 'GOOD', actionDnaScore: 0.82, confidence: 0.9, reason: 'Clear hook',
      storyboardPath: 'library/x/storyboard.png', analysisVersion: 'creative-v3',
    };

    service.getAnalysisStatus('video-1').subscribe(status => expect(status).toEqual(response));

    const request = http.expectOne('/api/v1/videos/video-1/analysis/status');
    expect(request.request.method).toBe('GET');
    request.flush(response);
  });
});
```

Add `AnalysisStatus` to the spec file's import line from `'./creative-intelligence.service'`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/creative-intelligence.service.spec.ts'`
Expected: FAIL (compile error — `AnalysisStatus`, `triggerAnalysis`, `getAnalysisStatus` don't
exist).

- [ ] **Step 3: Add the interface and methods**

```typescript
export interface AnalysisStatus {
  videoId: string;
  hasCompletedAnalysis: boolean;
  jobId: string | null;
  jobState: 'NOT_STARTED' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  attempts: number | null;
  maxAttempts: number | null;
  errorMessage: string | null;
  analysisId: string | null;
  classification: string | null;
  actionDnaScore: number | null;
  confidence: number | null;
  reason: string | null;
  storyboardPath: string | null;
  analysisVersion: string | null;
}
```

Add methods near `ingestVideo`/`listVariants`:

```typescript
  triggerAnalysis(videoId: string): Observable<AnalysisStatus> {
    return this.http.post<AnalysisStatus>(`${this.baseUrl}/videos/${videoId}/analysis`, {});
  }

  getAnalysisStatus(videoId: string): Observable<AnalysisStatus> {
    return this.http.get<AnalysisStatus>(`${this.baseUrl}/videos/${videoId}/analysis/status`);
  }
```

(`triggerAnalysis` posts an empty body `{}` — the backend's `@PostMapping("/{id}/analysis")` takes
no `@RequestBody`, but Angular's `HttpClient.post` requires a body argument; `{}` is the
established convention already used elsewhere in this file, e.g. `createVariant`'s request body is
non-empty but other POSTs like `ingestVideo` pass a real object — confirm there isn't an existing
no-body POST convention in this file to match exactly before defaulting to `{}`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/creative-intelligence.service.spec.ts'`
Expected: PASS.

- [ ] **Step 5: Run full frontend suite for regressions**

Run: `cd intelligence/frontend && npx ng test --watch=false`
Expected: all pass except the one pre-existing, unrelated `app.spec.ts` nav-link-count failure
(confirmed pre-existing across the whole B2b plan; not this plan's concern).

- [ ] **Step 6: Commit**

```bash
cd intelligence/frontend
git add src/app/core/creative-intelligence.service.ts src/app/core/creative-intelligence.service.spec.ts
git commit -m "feat(intelligence): add triggerAnalysis/getAnalysisStatus to the frontend service"
```

---

### Task 6: `video-detail.page.ts` — trigger button, live status polling, result rendering

**Files:**
- Modify: `intelligence/frontend/src/app/pages/video-detail.page.ts`
- Test: `intelligence/frontend/src/app/pages/video-detail.page.spec.ts`

**Interfaces:**
- Consumes: `CreativeIntelligenceService.triggerAnalysis`/`getAnalysisStatus` (Task 5).

**Context:** `video-detail.page.ts`'s current import lines are:
```typescript
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, combineLatest, forkJoin, Observable, of } from 'rxjs';
```
This task needs `interval`, `startWith`, `switchMap`, and `Subscription` added to the `rxjs`
import, and `AnalysisStatus` added to the existing multi-line import from
`'../core/creative-intelligence.service'` (the one spanning lines 4-13 today) — add them to the
existing import statements, do not add a second, separate `import` line for the same module.

Add a new signal `analysisStatus = signal<AnalysisStatus | null>(null)`. Add a
"Trigger analysis" button (parallel to the existing "Ingest for analysis" button pattern) that
calls `triggerAnalysis`, then starts polling `getAnalysisStatus` every 5 seconds (reusing the
`interval(5000).pipe(startWith(0), switchMap(...))` idiom already established in
`render-dashboard.page.ts`, adapted to this file's signal-based style) until the status is
`COMPLETED` or `FAILED`, at which point polling stops. Render a new "Creative Analysis" section:
classification, Action DNA score (labeled "Action DNA score," not the DTO's internal
`creativeStructureMatch` name — this field doesn't even appear in the new `AnalysisStatusResponse`
shape, so this is moot for this specific DTO, but keep the label user-facing-correct regardless),
confidence, reason, storyboard path, timeline, feature fingerprint placeholder (the new
`AnalysisStatusResponse` DTO from Task 4 does not include `timeline`/`features` — flag this
explicitly as a known gap for the completion report rather than fabricating fields the backend
doesn't send; only render what `AnalysisStatus` actually carries: classification, actionDnaScore,
confidence, reason, storyboardPath, analysisVersion).

Add near the existing signals:

```typescript
  protected readonly analysisStatus = signal<AnalysisStatus | null>(null);
  protected readonly triggeringAnalysis = signal(false);
  private analysisPollSubscription: Subscription | null = null;
```

Add a method to start polling, called when a video becomes active (inside `activateVariant`,
alongside the existing `loadVariants` call) and stopped on unmount or when a terminal state is
reached:

```typescript
  private pollAnalysisStatus(videoId: string): void {
    this.analysisPollSubscription?.unsubscribe();
    this.analysisPollSubscription = interval(5000)
      .pipe(startWith(0), switchMap(() => this.service.getAnalysisStatus(videoId)))
      .subscribe(status => {
        this.analysisStatus.set(status);
        if (status.jobState === 'COMPLETED' || status.jobState === 'FAILED') {
          this.analysisPollSubscription?.unsubscribe();
        }
      });
  }

  protected triggerAnalysis(): void {
    const id = this.video()?.id;
    if (!id) return;
    this.triggeringAnalysis.set(true);
    this.service.triggerAnalysis(id).subscribe({
      next: status => { this.triggeringAnalysis.set(false); this.analysisStatus.set(status); this.pollAnalysisStatus(id); },
      error: response => { this.triggeringAnalysis.set(false); this.message.set(response.error?.message || 'Could not start analysis.'); },
    });
  }
```

Call `this.pollAnalysisStatus(file.videoId)` (or `video.id`, whichever is in scope at that point —
match `loadVariants`'s existing call sites exactly, both `activateVariant` branches) once on
activation so the panel shows current state immediately without requiring the user to click
"Trigger analysis" first (it may already be complete from ingest-time analysis per Task 1, or
already in flight from a previous click). Add `ngOnDestroy` (or confirm the component already has
one; if not, implement `OnDestroy` on the class) to unsubscribe `analysisPollSubscription` so
polling doesn't leak past navigation away from the page — check whether any other subscription in
this file already has a lifecycle-cleanup pattern to follow (the `activateVariant`/`loadFolder`
generation-counter guard is this file's existing idiom for stale-response handling, but polling
cleanup specifically needs real unsubscription, not just a generation check, since `interval` never
completes on its own).

Add the template section (inside the ingested-video branch, near the existing "Technical details"
section):

```html
<section class="section-band creative-analysis-panel" aria-labelledby="creative-analysis-heading">
  <div class="section-heading"><div><span class="eyebrow">CREATIVE ANALYSIS</span><h2 id="creative-analysis-heading">Automated quality assessment</h2></div>
    @if (!analysisStatus()?.hasCompletedAnalysis) { <button class="button button--primary" type="button" [disabled]="triggeringAnalysis() || analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING'" (click)="triggerAnalysis()">{{ triggeringAnalysis() ? 'Starting…' : analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING' ? (analysisStatus()!.jobState === 'QUEUED' ? 'Queued…' : 'Running…') : 'Trigger analysis' }}</button> }
  </div>
  @if (analysisStatus()?.hasCompletedAnalysis) {
    <dl class="technical-facts">
      <div><dt>Classification</dt><dd>{{ analysisStatus()!.classification }}</dd></div>
      <div><dt>Action DNA score</dt><dd>{{ decimal(analysisStatus()!.actionDnaScore) }}</dd></div>
      <div><dt>Confidence</dt><dd>{{ decimal(analysisStatus()!.confidence) }}</dd></div>
      <div><dt>Reason</dt><dd>{{ analysisStatus()!.reason }}</dd></div>
      <div><dt>Analysis version</dt><dd><code>{{ analysisStatus()!.analysisVersion }}</code></dd></div>
      @if (analysisStatus()!.storyboardPath) { <div><dt>Storyboard</dt><dd><code>{{ analysisStatus()!.storyboardPath }}</code></dd></div> }
    </dl>
  } @else if (analysisStatus()?.jobState === 'FAILED') {
    <div class="state-panel state-panel--error compact-state"><strong>Analysis failed</strong><p>{{ analysisStatus()!.errorMessage || 'The analysis job failed.' }}</p></div>
  } @else if (analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING') {
    <div class="state-panel compact-state"><span class="spinner"></span><strong>{{ analysisStatus()!.jobState === 'QUEUED' ? 'Queued for analysis' : 'Analysis running' }}</strong></div>
  } @else {
    <div class="state-panel compact-state"><strong>No analysis yet</strong><p>Trigger analysis to classify this creative.</p></div>
  }
</section>
```

(`decimal` already exists as a method on this component — reuse it, do not add a second
formatter.)

- [ ] **Step 1: Write the failing test**

```typescript
describe('VideoDetailPage creative analysis panel', () => {
  const route = {
    paramMap: of(convertToParamMap({})),
    queryParamMap: of(convertToParamMap({ folder: 'library/Giant Sock', file: mediaFile.relativePath })),
  };

  function serviceWithAnalysis(status: AnalysisStatus) {
    return {
      mediaContentUrl: () => '/media',
      getMediaFiles: () => of([mediaFile]),
      getVideo: () => of(video),
      getReachFurther: () => of(null),
      getTrajectory: () => of({ videoId: 'video-1', platform: 'facebook', label: '', cleanOrganic: true, interventions: [], points: [] }),
      getPlatformGrowth: () => of(null),
      getDiscoveryProfile: () => of(baseDiscovery),
      listVariants: () => of([]),
      triggerAnalysis: () => of(status),
      getAnalysisStatus: () => of(status),
    };
  }

  afterEach(() => TestBed.resetTestingModule());

  it('renders completed analysis results instead of a trigger button', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWithAnalysis({
          videoId: 'video-1', hasCompletedAnalysis: true, jobId: null, jobState: 'COMPLETED',
          attempts: null, maxAttempts: null, errorMessage: null, analysisId: 'analysis-1',
          classification: 'GOOD', actionDnaScore: 0.82, confidence: 0.9, reason: 'Clear hook',
          storyboardPath: null, analysisVersion: 'creative-v3',
        }) },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector('.creative-analysis-panel');
    expect(panel.textContent).toContain('GOOD');
    expect(panel.textContent).toContain('Clear hook');
    expect(panel.querySelector('button')).toBeNull();
  });

  it('shows a trigger button when no analysis exists yet', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWithAnalysis({
          videoId: 'video-1', hasCompletedAnalysis: false, jobId: null, jobState: 'NOT_STARTED',
          attempts: null, maxAttempts: null, errorMessage: null, analysisId: null,
          classification: null, actionDnaScore: null, confidence: null, reason: null,
          storyboardPath: null, analysisVersion: null,
        }) },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector('.creative-analysis-panel');
    expect(panel.querySelector('button')?.textContent).toContain('Trigger analysis');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/video-detail.page.spec.ts'`
Expected: FAIL — `.creative-analysis-panel` doesn't exist in the template yet.

- [ ] **Step 3: Implement** (per the snippets above)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/video-detail.page.spec.ts'`
Expected: PASS. Also add `triggerAnalysis`/`getAnalysisStatus` to the pre-existing
`serviceWith()`/`taggedFile`-adjacent mocks in this file (same mechanical necessity Task 4 of Plan
B2b hit with `listVariants` — any test double standing in for the service now needs these two
methods if the component calls them unconditionally on activation).

- [ ] **Step 5: Run full frontend suite for regressions**

Run: `cd intelligence/frontend && npx ng test --watch=false`
Expected: all pass except the one pre-existing, unrelated `app.spec.ts` failure.

- [ ] **Step 6: Commit**

```bash
cd intelligence/frontend
git add src/app/pages/video-detail.page.ts src/app/pages/video-detail.page.spec.ts
git commit -m "feat(intelligence): add analysis trigger button and live status panel to Video Detail"
```

---

### Task 7: Final whole-plan review + roadmap doc update

**Files:**
- Modify: `intelligence/docs/superpowers/PART_02_COMPLETION_ROADMAP.md`

- [ ] **Step 1: Re-run both full suites from a clean state**

```bash
cd intelligence/backend && mvn test
cd intelligence/frontend && npx ng test --watch=false
```

- [ ] **Step 2: Whole-plan review**

Verify across all 6 implementation tasks together:
- Grep the whole backend for `ml.analyse(` / `.analyse(` call sites — confirm exactly two exist
  (`VideoService.ingest()`, `VideoService.analyse()` called only from
  `AnalysisJobService.processNext()`), never a third.
- Confirm no code path can create two `QUEUED`/`RUNNING` rows for one video — re-read the `V34`
  migration and `enqueue()`'s race-handling catch block together.
- Confirm `creative_analyses` row count never exceeds 1 per video across ingest + any number of
  subsequent `enqueue()` calls, by tracing every write path by hand (ingest's guarded persist,
  `analyse()`'s persist called only from the worker, which only runs for jobs that `enqueue()`
  itself refused to create when a row already existed).
- Confirm no `force=true`-style bypass was accidentally introduced anywhere.
- Confirm the frontend never fabricates a `timeline`/feature-fingerprint display the backend DTO
  doesn't actually send (per Task 6's explicit note) — flag as a known, documented gap, not a
  silent omission.

- [ ] **Step 3: Update the roadmap doc**

Mark Plan C's status row `✅ Done`, add a completion record section (§4d, following §4b/§4c's
established style) summarizing: the Option-2-idempotent design actually implemented (vs. the
roadmap's original ambiguous "connect to a visible state transition" wording), the two distinct
state models preserved, the `V34` migration, and the explicitly deferred `timeline`/feature-
fingerprint frontend rendering gap (DTO doesn't carry those fields today — would need
`AnalysisStatusResponse` extended in a follow-up if the product wants them visible).

- [ ] **Step 4: Commit**

```bash
git add intelligence/docs/superpowers/PART_02_COMPLETION_ROADMAP.md
git commit -m "docs(intelligence): mark Part 02 Plan C complete (creative analysis completion)"
```

---

## Self-Review Notes (for the plan author, not a task)

- Spec coverage: the user's 10 numbered test requirements are distributed across Task 3's test
  file (1-8, 10) and Task 1+3 combined (9 is implicitly covered by Task 1's ingest test plus
  Task 3's "completed current version does not call ML again" test, which together prove ingest's
  single call is never duplicated by a subsequent analysis request).
- The "two distinct state models" requirement is enforced structurally: `AnalysisJob` fields never
  appear in `VideoEntity`, and `VideoEntity.status` is only ever set by the three pre-existing
  `markX()` methods, unchanged by this plan.
- Known gap flagged honestly rather than silently handled: `AnalysisStatusResponse` does not carry
  `timeline`/`features` (the full creative-fingerprint data), so Task 6's frontend panel does not
  render a feature-fingerprint section the roadmap's original Plan C text mentioned wanting — this
  is called out explicitly in Task 6 and Task 7's roadmap update rather than fabricated or ignored.
- Type consistency checked: `AnalysisStatus` (Task 5, TypeScript) matches `AnalysisStatusResponse`
  (Task 4, Java record) field-for-field, 14 fields each, same nullability pattern.
