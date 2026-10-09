# Part 02 Completion Roadmap — Video Library, Video Detail, Variant Identity

**Status file. Read this first in any new session before touching Part 02 code.**

Source task: complete `AUDIT_PART_02_VIDEO_LIBRARY_AND_DETAIL.md` (repo root). This work is a
**prerequisite for Part 03** (`AUDIT_PART_03_IMPORT_PREDICTION_AND_LEARNING.md`), whose spec
assumes "canonical video identity," "persisted variant identity," and "Part 02 normalized
trajectories feed dataset construction" already exist. They do not yet. Do not start Part 03
until this roadmap's plans are done (or Part 03 is explicitly scoped around what's missing,
per the user's decision 2026-10-03 to complete Part 02 first rather than work around it).

Do not redesign the platform; fix and complete the existing architecture.

**Branch policy: work directly on `master`. No worktrees, no feature branches — single
user, single active session at a time. Always check `git log --oneline -10` and `git status`
at the start of a session before assuming anything about current state (this repo has had
multiple parallel sessions working in it; verify, don't assume).**

---

## 0. Phase 0 audit verification (done)

Verified against actual code, not just the audit doc or the pre-existing
`docs/PART_02_PHASE_0_IMPLEMENTATION_NOTE.md` investigation note (which itself was independently
re-verified against live source during this roadmap's creation — all of its claims held, nothing
had drifted). Confirmed by direct inspection:

- **No `VideoVariant` entity/service/API exists anywhere in the Java backend** — a repo-wide grep
  for `VideoVariant` and `variant_id`/`variantId` across all `**/*.java` returns zero matches
  outside the schema itself. The concept does not exist in code at all, not even as a comment.
- **P0-01 confirmed**: `PerformanceTrajectoryController.trajectory()` and
  `PlatformGrowthProfileService.profile()` both query `performance_observations` with no
  `metric_semantics` filter anywhere, and compute velocity/checkpoints as raw `views` diffs
  regardless of whether a row is `DAILY_INCREMENT`, `CUMULATIVE`, or `SNAPSHOT`.
- **P0-02 confirmed**: neither query filters on `source`/`source_version`; CSV-origin and any
  future Meta Graph API rows are queried together unconditionally.
- **P0-03 confirmed**: `video_variants` (with `parent_variant_id`, `variant_type` CHECK constraint,
  `generated_path`, `edit_operations`) and `variant_id` FK columns on `performance_observations`,
  `predictions`, `experiments` all exist in `V1__initial_schema.sql`, completely unused by any
  Java code. `intervention_events` has no `variant_id` column at all (schema gap).
- **P1-01 confirmed**: `VideoService.ingest()`'s content-hash dedup path returns the existing
  entity on a hash match and never records the new path anywhere — `mediaFiles()` will show that
  second path as `ingested: false` forever.
- **P1-02 confirmed**: `docker-compose.yml` mounts `"../:/data/library:ro"` — the repo root one
  level up from the compose file, not a production media tree.
- **P1-03/P1-04 confirmed**: `VideoService.ingest()` discards the creative-analysis portion of the
  ML response; a second, separate `analyse()` call re-runs the same ML analysis to persist
  `creative_analyses`/`creative_fingerprints`. The Angular frontend has zero references to any
  analysis-triggering call — no button, method, or HTTP call invokes it.
- **P1-05 confirmed verbatim**: `video-detail.page.ts`'s `loadPerformance()` wraps all 4 detail API
  calls (Reach Further, trajectory, growth profile, discovery profile) in
  `catchError(() => of(null))`, collapsing real failures and genuine absence into one
  indistinguishable UI state.
- **P1-06 confirmed, but nuanced**: the frontend's "Not available in imported data" is honest
  given what `PerformanceTrajectoryController`'s `TrajectoryPoint` DTO actually returns (it has no
  `completionRate`/`averageWatchSeconds` fields at all) — but `performance_observations` does
  store these columns (written by `PerformanceImportService.writeObservation`). This is a backend
  exposure gap, not a frontend display bug — fix belongs in the controller/DTO, not just the UI.
- **P1-07 confirmed**: `PlatformGrowthProfileService.checkpoint()` is a strict "last observation at
  or before horizon" scan with zero tolerance — a point at `horizon + 1s` is excluded entirely in
  favor of a much staler earlier point. Same pattern in `PlatformStateService`'s
  `pointAtOrBefore`/`pointAtOrAfter`.
- **P1-08/P1-09 confirmed**: `PerformanceImportService.match()`/`writeObservation()` never
  reference `variant_id`; `PlatformStateService.publication(videoId, platform)` (the read path)
  ignores `variant_id` entirely even though the write path (`recordPublication()`) is already
  variant-aware (`variant_id IS NOT DISTINCT FROM :variant`).
- **Latest migration on disk is `V31__complete_quality_validation_evidence.sql`** (Part 01's Plan
  C2 migration) — any new Part 02 migration starts at **V32**.
- No uncommitted or recent-commit Part 02 work exists anywhere in the repo as of this roadmap's
  creation — clean baseline.

No contradiction found between the audit and the actual schema/code.

---

## 1. Decomposition into sub-plans

Per `writing-plans` skill's scope-check rule, this work is split into sub-plans mapped onto the
audit's own §8 "Completion Order" (Phase A-E), each independently plannable/testable/committable.
**Work them in order — later plans assume earlier plans' deliverables exist**, with one exception
noted below (Plan B2 is the hard dependency for everything else; Plan A is independent and could
be done in parallel if desired, but is sequenced first here because it's lower-risk and does not
touch the variant model Plan B introduces).

| # | Plan name | Audit section | Codebase(s) | Status |
|---|---|---|---|---|
| A | Observation mathematics correctness (metric semantics + source reconciliation + checkpoint tolerance) | Phase A | backend | ✅ Done, backend-only (commit `ffbdf84`, see §4 for completion record and 2 open follow-ups) |
| B1 | Variant domain (entity/repository/service/API) | Phase B.1 | backend | ✅ Done (commit `bb35667`, see §4 for completion record) |
| B2a | Variant-aware backend wiring (path-alias dedup, import variant resolution, publication read path, performance query filters, V32/V33 migrations) | Phase B.2-5 (backend) | backend | ✅ Done (commit `284105f`, see §4 for completion record) |
| B2b | Frontend variant consumption (Angular service methods + replace folder-grouping heuristic) | Phase B.3 (frontend) | frontend | ✅ Done (commit `c11dfd9`, see §4c for completion record) |
| C | Creative analysis completion (stop duplicate ML calls, surface analysis in Video Detail) | Phase C | backend, frontend | ✅ Done (commit `50b16ee`, see §4d for completion record) |
| D | Evidence honesty (error-vs-empty, completion/watch metrics, overview placeholders, platform validation) | Phase D | backend, frontend | ⬜ Not started |
| E | Deployment and scale boundaries (media mount, scan truncation, pagination) | Phase E | backend, frontend, deployment config | ⬜ Not started |

### Dependency notes
- **A is independent** of B/C/D/E — pure backend query-correctness fix on existing columns. Can be
  done first or in parallel with B1; sequenced first here for lower risk and because Part 03's
  dataset-construction phase needs correct trajectory math regardless of variant identity.
- **B2a depends on B1** (needs the `VideoVariant` entity/service to exist before anything can
  reference a real variant ID). Split from the original single "B2" into B2a (backend)/B2b
  (frontend) on 2026-10-03 after investigating B2's actual scope — it touches 6+ backend files
  (`VideoService`, `PerformanceImportService`, `PlatformStateService`,
  `PerformanceTrajectoryController`, `PlatformGrowthProfileService`, `DiscoveryProfileService`)
  plus a new `V32` migration, which is independently plannable/testable/committable from the
  Angular frontend half, per `writing-plans`' scope-check rule.
- **B2b depends on B2a** (the frontend cannot consume real `variantId`s or a variant-aware
  `MediaFile.variantId` field until the backend endpoints/fields exist).
- **C is independent of A/B** — the duplicate-ML-call and analysis-surfacing fix touches
  `VideoService`/`AnalysisJobService`/frontend detail page, not performance or variant code. Can
  be done in parallel with A/B if desired.
- **D depends on A and B2** for its most substantial item (P1-06's completion/watch metrics need
  the corrected trajectory query from Plan A; honest empty/failed states and overview placeholders
  are independent of A/B but grouped here per the audit's own Phase D).
- **E is independent of everything** — deployment config and pagination are orthogonal to the
  identity/math fixes. Lowest architectural risk, can slot in anytime.
- **Part 03 depends on A and B1/B2 at minimum** — "persisted variant identity" and "canonical
  trajectory builder" are exactly what Plans A and B1/B2 deliver. C/D/E are not blocking for Part
  03 but should be done for overall platform correctness.

Suggested execution order: **A → B1 → B2 → C → D → E**, then re-evaluate Part 03's scope against
what's actually landed.

---

## 2. Per-plan detail

### Plan A — Observation mathematics correctness
**Audit section:** Phase A (Repair observation mathematics)
**Files (expected, confirm against current code before editing):**
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java`
  (stop computing velocity as a raw `views` diff between consecutive rows regardless of
  `metric_semantics`; normalize `DAILY_INCREMENT` by accumulating, treat `CUMULATIVE`/compatible
  `SNAPSHOT` per an explicit policy, reject/isolate `UNKNOWN`)
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java`
  (same normalization before computing checkpoints/burst/tail ratios; fix `checkpoint()`'s
  zero-tolerance "last observation at or before horizon" selection — add an explicit tolerance
  window or mark a horizon unavailable when no observation falls within it, per P1-07)
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`
  (same tolerance-window fix for `pointAtOrBefore`/`pointAtOrAfter`, used by Reach Further window
  calculations)
- Response DTOs for the above (add provenance/quality-state fields so API responses can say *why*
  a value is what it is — which source(s) contributed, whether semantics required exclusion)
- A query-level source reconciliation step (filter/separate by `source`/`source_version` before
  computing any single trajectory, per P0-02 — define the canonical selection rule explicitly, do
  not silently interleave CSV and Meta Graph rows)
**Goal:** trajectory, velocity, burst ratio, tail ratio, and checkpoint calculations are
mathematically correct given the declared `metric_semantics` of each observation, never mixing
incompatible sources into one series, and horizon checkpoints are either close enough to their
label or explicitly marked unavailable — never silently stale.

### Plan B1 — Variant domain
**Audit section:** Phase B, item 1 ("Add backend access to `video_variants` already present in the
schema")
**Files:**
- New: `VideoVariantEntity.java` (JPA entity over the existing `video_variants` table — do not
  alter the table; `id`, `videoId`, `parentVariantId`, `variantType` (enum matching the existing
  CHECK constraint: `ORIGINAL, HOOK_COLD_OPEN, TRIMMED, NO_CTA, LOOP_CUT, CUSTOM_EDIT`),
  `generatedPath`, `editOperations` (JSONB), `createdAt`)
- New: `VideoVariantRepository.java`
- New: `VideoVariantService.java` (create/list/get variant by ID, associate with a parent video)
- New: `VideoVariantController.java` (REST API: list variants for a video, create a variant record,
  get one variant)
**Goal:** the already-migrated `video_variants` table has a real, usable backend surface — this is
the prerequisite every later plan item (import, publication, performance queries, frontend) needs
a real `variantId` to reference.

### Plan B2a — Variant-aware backend wiring
**Audit section:** Phase B, items 2-5 (backend half; split from the original single "Plan B2" on
2026-10-03 after investigating actual scope — see roadmap §1's dependency notes)
**Files:**
- `VideoService.java` (fix the content-hash dedup path from P1-01 — add a path-alias relationship
  so a second path resolving to the same content hash is recorded, not discarded; `mediaFiles()`
  must then resolve an aliased path to its canonical video rather than showing it as permanently
  "Not ingested")
- New: `VideoPathAliasEntity.java`/`VideoPathAliasRepository.java` (new table, see migration below)
- New migration `V32__...sql` (never edit V1-V31; adds `video_path_aliases` table for the above;
  adds `intervention_events.variant_id` nullable FK, since that table has no variant column at all)
- `PerformanceImportService.java` (extend the existing exact/manual resolution step to accept and
  write `variant_id` on `writeObservation()`'s INSERT, resolved via a new explicit
  `variantid`/`variant_id` import-row column scoped to the already-resolved `videoId` — no fuzzy
  attribution, per P1-08)
- `PlatformStateService.java` (`publication(videoId, platform)`'s read path becomes
  `publication(videoId, variantId, platform)`, matching the already-variant-aware write path
  `recordPublication()`, per P1-09; `null` variantId means "the un-variant-scoped group,"
  consistent with the schema's own `IS NOT DISTINCT FROM` sentinel convention, never "match any
  variant")
- `PerformanceTrajectoryController.java`, `PlatformGrowthProfileService.java`,
  `DiscoveryProfileService.java` (accept an optional `variantId` filter; `IS NOT DISTINCT FROM`
  semantics so existing variant-blind data stays visible under the default `null` filter, while
  newly variant-tagged observations require an explicit variantId to see — never a silent
  aggregate-across-variants fallback, which would reintroduce the exact P0-03 problem this plan
  exists to fix)
**Goal:** every backend write/read path that touches a video's performance evidence can be scoped
to an exact variant when one is known, duplicate bytes at multiple paths no longer show as
permanently "Not ingested," and import resolution can target an exact variant with no fuzzy
matching.

### Plan B2b — Frontend variant consumption
**Audit section:** Phase B, item 3 (frontend half)
**Files:**
- `creative-intelligence.service.ts` (add `VideoVariant` interface matching
  `VideoVariantDtos.VariantResponse` exactly; add `listVariants(videoId)`/`createVariant(videoId,
  request)` HTTP methods against Plan B1's `/api/v1/videos/{videoId}/variants` endpoints, which
  currently have zero Angular consumers; add `variantId: string | null` to the `MediaFile`
  interface, mirroring the backend DTO change Plan B2a makes)
- `video-library.page.ts`/`video-detail.page.ts` (replace the `mediaVariant()` filename-suffix
  parser — currently the entire "variant" model, with labels that don't even align to
  `VideoVariantType`'s enum values — with real `variantId`-based grouping from the backend;
  filename-based folder grouping may remain as a *discovery aid* for browsing un-ingested files,
  but must not be the persisted identity a user acts on)
**Goal:** a creative and its variants are persisted identities a user can see and act on in the
product, not inferred from directory layout and filename guesswork.

### Plan C — Creative analysis completion
**Audit section:** Phase C
**Files:**
- `VideoService.java` (stop discarding the creative-analysis portion of the ML response during
  `ingest()`; either persist it once at ingest time, or make `analyse()` idempotent by skipping the
  redundant second ML call when a `creative_analyses` row for the current `analysis_version`
  already exists — per the Phase 0 note's own flagged resolution for this exact conflict, Option B
  preferred: least disruptive, no new ML endpoint needed)
- `AnalysisJobService.java` (connect the existing analysis operation to a visible state transition)
- Frontend: `video-detail.page.ts` (add the missing trigger/button for the analysis operation;
  display persisted classification, Action DNA score, confidence, reason, timeline, feature
  fingerprint, storyboard path — all already persisted by the backend today, just never rendered)
**Goal:** expensive video analysis runs at most once per file; its result is visible in Video
Detail, not silently discarded; a video's analysis status accurately reflects what has actually
been computed.

### Plan D — Evidence honesty
**Audit section:** Phase D
**Files:**
- Frontend: `video-detail.page.ts` (`loadPerformance()`'s `catchError(() => of(null))` pattern
  replaced with per-section error state distinct from genuine emptiness, per P1-05 — "failed to
  load," "no data available," and "loading" must be three different renderable states, not one)
- `PerformanceTrajectoryController.java`'s `TrajectoryPoint` DTO (add the already-imported
  `completionRate`/`averageWatchSeconds`/`totalWatchSeconds`/`skipRate` fields that
  `performance_observations` already stores — close the P1-06 backend exposure gap; only show
  "Not available" in the frontend when the actual stored value is null, not because the field was
  never selected)
- Frontend: whatever shared service builds the Overview page's placeholder rows (per P2-08 — remove
  hardcoded `format: 'Unclassified'`, `character: 'Unassigned'`, `platform: 'Unknown'`,
  `hookRate: 0`, `completion: 0`, `views: 0`, ingest-date-as-published-date; show unknown as
  genuinely unknown, not zero)
- Backend platform-handling code (validate platform identifiers against a controlled enum rather
  than free-form lowercasing, per P2-06 — prevents a typo like `facebok` from silently creating an
  unreachable evidence partition)
**Goal:** the UI never presents a database error, a genuinely empty result, and fabricated zero
placeholder data as the same thing. Every number on screen is either real, explicitly unavailable,
or explicitly failed — never an invented default.

### Plan E — Deployment and scale boundaries
**Audit section:** Phase E
**Files:**
- `docker-compose.yml` (parameterize the media library bind mount via an environment variable
  rather than hardcoding `"../:/data/library:ro"`, per P1-02; document the required value for a
  real production media root)
- `VideoService.java`/media-listing endpoints (disclose scan truncation explicitly — directory
  ingest's 1,000-file cap, media listing's 1,000-file cap, folder counting's 10,000-file cap, per
  P2-01 — responses must say when results were truncated, not silently stop)
- Pagination/cursor support for video library listing before libraries exceed current limits
**Goal:** a fresh checkout mounts the intended production media root, not the application
repository itself; truncated results are visibly truncated, never indistinguishable from complete
results.

---

## 4. Plan A completion record

**Status: ✅ Done (backend-only — see open follow-ups below).** Executed via
`subagent-driven-development`, 4 tasks, each with an implementer → review → fix-round cycle (no
fix rounds were actually needed — every task was Approved on first review). Plan doc:
the completed implementation plan retained in Git history.

Final state: Spring test suite 78/78 passing, `BUILD SUCCESS`. Full-plan diff reviewed
holistically (not just per-task) and found Approved-with-follow-ups — no cross-task
inconsistency, no global-constraint violation, but two gaps between the plan's stated Goal and
what actually landed, both now documented rather than silently assumed covered.

Commit range: `fad3c22..ffbdf84` (4 commits, one per task, no fix-round commits needed).

Delivered:
- New `ObservationSeries` utility (`intelligence/backend/.../performance/ObservationSeries.java`):
  converts raw, possibly-mixed-`metric_semantics` observation rows into one honest cumulative-views
  series — `DAILY_INCREMENT` rows accumulate into a running sum (scoped independently per
  `source`), `CUMULATIVE`/`SNAPSHOT` rows are used directly, `UNKNOWN`/null-views rows are excluded
  entirely (never guessed).
- `PerformanceTrajectoryController.trajectory()` now routes through this normalization instead of
  computing velocity as a raw consecutive-row `views` diff — closes the audit's exact failure case
  (two `DAILY_INCREMENT` rows of 1,000 then 300 no longer produce a nonsensical -700 delta). Also
  gained explicit source reconciliation: when more than one `source` is present, the response's
  new `sourcesPresent`/`sourceReconciliationApplied` fields disclose this, and the series uses only
  the dominant source rather than silently interleaving two incompatible streams.
- `PlatformGrowthProfileService.profile()`'s checkpoints (6h/24h/48h/7d) get the same
  normalization, plus a new `withinTolerance` flag on `MetricCheckpoint`: a checkpoint satisfied
  only by an observation more than 2 hours from its target horizon is now flagged as such rather
  than silently accepted as if accurate — closes the audit's "24h checkpoint built from a 1-hour
  observation" finding.
- `PlatformStateService`'s Reach Further window lookups (`pointAtOrBefore`/`pointAtOrAfter`) gained
  the same `withinTolerance` flag on `MetricPoint`, consistent naming/semantics with the above.

**Known, accepted gaps (NOT delivered by Plan A, documented in the plan doc's "Scope addendum"
added after the whole-plan review found them, 2026-10-03):**

1. **Frontend never consumes the three new fields.** `sourcesPresent`/`sourceReconciliationApplied`
   (on `TrajectoryView`) and both `withinTolerance` fields exist in API responses only —
   `intelligence/frontend/`'s TypeScript types and templates have zero references to any of them.
   A stale or multi-source-reconciled checkpoint is correctly flagged by the backend today but
   still renders identically to a clean one in the product. **This needs an explicit follow-up
   task** — most naturally folded into Plan D ("Evidence honesty") since that plan already touches
   `video-detail.page.ts`'s data-rendering logic, or Plan B2 if it ends up touching the same
   TypeScript interfaces for variant-aware queries. Do not assume this is silently covered by
   either plan without checking.
2. **`PlatformStateService`'s Reach Further velocity/window math remains metric-semantics-blind.**
   Task 4 only added the tolerance-window flag to `pointAtOrBefore`/`pointAtOrAfter`/`latestPoint`
   — it deliberately did NOT route this code path through `ObservationSeries.normalize()`, unlike
   Tasks 2 and 3. This means `velocity()`, used by `reachFurtherSummary()`'s before/after-3h
   acceleration calculation, can still compute an incorrect value from raw `DAILY_INCREMENT` rows
   — the identical bug class Tasks 2/3 fixed elsewhere, just not here. This was a deliberate,
   lower-priority scope cut to finish Plan A on the audit's Phase A schedule, not an oversight.
   **Should be closed before Reach Further evidence is used for anything higher-stakes than
   descriptive display** (e.g. as Part 03 training data).

Also independently flagged by Task 4's reviewer (not fixed, not blocking): `CHECKPOINT_TOLERANCE`
(`Duration.ofHours(2)`) is defined identically in both `PlatformGrowthProfileService.java` and
`PlatformStateService.java` — two independent constants with the same value today, no shared
source of truth. Low risk now, but recommend consolidating (e.g. into `ObservationSeries`, already
the shared home for cross-cutting observation-math concepts) before a third consumer appears or
before anyone needs to change the tolerance value, to prevent silent divergence between the two
files.

---

## 4a. Plan B1 completion record

**Status: ✅ Done.** Executed via `subagent-driven-development`, 4 tasks, each with an
implementer → review → fix-round cycle (no fix rounds were actually needed — every task was
Approved on first review, though two tasks' implementers found and fixed real bugs in the plan's
own draft code before that approval). Plan doc:
the completed implementation plan retained in Git history.

Final state: Spring test suite 92/92 passing, `BUILD SUCCESS`. Full-plan diff reviewed
holistically and found fully Approved — no cross-task inconsistency, no global-constraint
violation, no incursion into Plan B2's scope.

Commit range: `f39a7dd..bb35667` (4 commits, one per task, no fix-round commits needed).

Delivered: `video_variants` (migrated since `V1`, never previously touched by any Java code) now
has a full backend surface:
- `VideoVariantEntity`/`VideoVariantType` (`intelligence/backend/.../video/`) — JPA entity over
  the unchanged existing table, enum matching the DB's CHECK constraint exactly.
- `VideoVariantRepository` — video-scoped lookups (`findAllByVideoId`, `findByIdAndVideoId`),
  never a bare `findById` for anything variant-related, enforcing the no-fuzzy-attribution rule
  structurally.
- `VideoVariantService` — `create`/`list`/`get`, all requiring an explicit `videoId`; a duplicate
  `generatedPath` is translated from a raw `DataIntegrityViolationException` into a clear
  `DuplicateGeneratedPathException` rather than leaking an unstructured 500.
- `VideoVariantController` — `POST`/`GET /api/v1/videos/{videoId}/variants`,
  `GET .../variants/{variantId}`, correctly covered end-to-end by the pre-existing global
  `@RestControllerAdvice` (`EntityNotFoundException`→404, `IllegalArgumentException`→400) with no
  new per-controller exception handling needed.

Two real bugs were found and fixed during implementation (not plan-level issues, task-level
catches, documented here since they illustrate this plan's draft code was not perfect and needed
real engineering judgment, not just transcription):
1. Task 3's brief explicitly flagged its own draft `requireVariant` helper only threw
   `IllegalArgumentException`, which would fail a test expecting `EntityNotFoundException` from
   `get()`. Resolved with two separate exception-throwing call sites sharing one non-throwing
   `Optional`-returning lookup.
2. Task 3's implementer also found an unflagged Mockito `verifyNoMoreInteractions` test bug in the
   brief's own draft test code (missing an explicit `verify()` before the no-more-interactions
   assertion) and fixed it correctly.

No new migration was needed — the existing `V1` schema already supported everything this plan
required.

**Not delivered by Plan B1, by design (this is Phase B item 1 only; items 2-5 are Plan B2):** no
physical file is yet associated with a variant, the frontend still groups files by folder as a
variant-identity heuristic, no `variantId` flows through imports/publications/performance queries
yet, and the content-hash/multiple-path alias issue (P1-01) is unresolved. Plan B2 is the next
step and depends entirely on this plan's deliverables existing first.

---

## 4b. Plan B2a completion record

**Status: ✅ Done.** Executed via `subagent-driven-development`, 4 tasks (Task 2's original
implementer subagent timed out with no side effects; the controller completed that task
directly). Every task was Approved on first review — no fix rounds needed, though three
implementation-time bugs were found and fixed by implementers/controller before each task's
review (not left for the reviewer to catch). Plan doc:
the completed implementation plan retained in Git history.

Final state: Spring test suite 103/103 passing, `BUILD SUCCESS`. Full-plan diff reviewed
holistically and found fully Approved — no cross-task inconsistency, no global-constraint
violation, no incursion into Plan B2b's (frontend) scope.

Commit range: `4c0c925..284105f` (4 commits, one per task, no fix-round commits needed).

Delivered:
- **Task 1** (`088ab6b`): `V32` migration (`video_path_aliases` table +
  `intervention_events.variant_id`), `VideoPathAliasEntity`/`Repository`, and a fix to
  `VideoService.ingest()`/`mediaFiles()` closing the P1-01 content-hash dedup bug — a duplicate
  physical path with identical bytes to an already-ingested video now resolves to the canonical
  video via an alias record, instead of permanently showing "Not ingested."
- **Task 2** (`4c45f03`): `V33` migration (`import_rows.matched_variant_id`) and explicit,
  exact-UUID variant resolution in `PerformanceImportService` — an import row's `variantid`
  column, when present and valid, is verified to belong to the already-resolved video and
  persisted onto `performance_observations.variant_id`. No fuzzy matching at any point.
- **Task 3** (`f7562d7`): `PlatformStateService.publication()`'s read path became variant-aware
  (`variant_id IS NOT DISTINCT FROM :variant`), matching the write path (`recordPublication()`)
  that was already variant-aware — closes P1-09.
- **Task 4** (`284105f`): optional, selective `variantId` filter added to
  `PerformanceTrajectoryController.trajectory()`, `PlatformGrowthProfileService.profile()`
  (+ its `earliestPublication()` helper), and `DiscoveryProfileService.profile()`. `null` means
  "match only the unscoped group," never "match any variant" — preserves this constraint
  consistently with every other variant filter added in this plan.

Three real bugs were found and fixed during implementation (not plan-level issues — task-level
catches that illustrate the plan's own draft code/tests needed real engineering judgment):
1. Task 2's test asserted `null` via `.query(UUID.class).single()`, which throws on a null
   result rather than returning it — fixed to `.optional().orElse(null)`.
2. Task 3's brief-specified test scenario didn't actually exercise the bug it claimed to
   (`recordPublication()`'s own internal lookup is already variant-scoped, so two fresh INSERTs
   never collided) — fixed by forcing an UPDATE on an already-recorded variant's publication so
   the stale "most recent row regardless of variant" read bug became reliably observable.
3. Task 4 found 7 more arity-broken call sites than the brief's own grep anticipated
   (`PlatformGrowthController`, `DiscoveryProfileController`, `PlatformGrowthResearchService` in
   production code; three more in test code) plus a wrong test-package placement in the brief's
   own new test file (specified in a package that couldn't call the package-private controller
   method it needed) — all fixed, confirmed via independent whole-plan review that no residual
   trace of either defect remains in the final committed state.

**Known, accepted gaps (deliberate, documented deferrals, not oversights):**
- `PlatformStateService.reachFurtherSummary()`'s own public signature still does not accept a
  caller-supplied `variantId` (only its internal `publication()` call does, passing `null`) —
  widening it has a bigger ripple through `liveFeatures()` and that method's own callers than
  this plan attempted.
- `PlatformGrowthResearchService`'s cross-video research aggregation still only sees unscoped
  (`variantId=null`) observations — correct scope discipline for "keep the build compiling," not
  a behavior upgrade this plan attempted.
- `V33`'s new `matched_variant_id` column has no index (unlike `V32`'s indexed `variant_id`) —
  low impact today since nothing queries `import_rows` by this column yet; worth adding if that
  changes.

Next: Plan B2b (frontend variant consumption), which depends on both Plan B1's
`/api/v1/videos/{videoId}/variants` endpoints and this plan's variant-aware query parameters/
alias-resolution behavior existing before building the Angular-side `variantId` concept on top
of them.

---

## 4c. Plan B2b completion record

**Status: ✅ Done.** Executed via `subagent-driven-development`, 4 tasks + final review. Task 2's
and Task 1's implementer dispatches each timed out once (3600s, no side effects on one; partial-
but-correct Step 1 only on the other) — both completed directly by the controller rather than
re-dispatched, per this session's established precedent. Every task reached Approved or Approved
with minor notes on first review — no fix rounds needed, though two of the four tasks' implementers
caught and correctly fixed real false-positive bugs in the plan's own draft test fixtures before
review (not left for the reviewer to catch). Plan doc:
the completed implementation plan retained in Git history.

Final state: backend Spring suite 104/104 passing, `BUILD SUCCESS`; frontend suite 19/20 passing
(1 pre-existing, unrelated `app.spec.ts` nav-link-count failure, confirmed via `git stash` to
predate this entire plan — not caused or fixed by it, out of scope). Full-plan diff reviewed
holistically: scope boundary confirmed clean (only the 10 files the plan's File Structure section
named were touched, verified via `git diff --stat` against the plan-start commit), `VariantType`'s
6-value closed set used consistently with no 7th value invented anywhere, and both frontend pages'
variantId-first/filename-guess-fallback logic independently confirmed never leaves a blank/undefined
label on any path.

Commit range: `26d08b3..c11dfd9` (plan doc + 4 task commits, no fix-round commits needed).

Delivered:
- **Task 1** (`9737801`): a gap this roadmap had assumed Plan B2a already closed, but hadn't —
  `VideoDtos.MediaFile`/`VideoService.mapMediaFile()` had no `variantId` resolution at all before
  this task. Added `VideoVariantRepository.findByGeneratedPath()` and a trailing `variantId` field
  on `MediaFile`, resolved via exact `generated_path` string match (no fuzzy matching, consistent
  with Plan B2a's precedent).
- **Task 2** (`1520819`): `VideoVariant`/`CreateVariantRequest`/`VariantType` TypeScript interfaces
  and `listVariants(videoId)`/`createVariant(videoId, request)` methods added to
  `creative-intelligence.service.ts`, consuming Plan B1's `/api/v1/videos/{videoId}/variants`
  endpoints, which had zero Angular consumers before this task. `MediaFile.variantId: string | null`
  added to match Task 1's backend field.
- **Task 3** (`e9f0f54`): `video-library.page.ts`'s `displayFiles` grouping/counting key now prefers
  real `variantId` identity over the filename guess when present (`variantGroupKey` helper), so two
  files with different names but the same persisted variant are counted/numbered together. Per-row
  **label text** deliberately still uses the pre-existing `mediaVariant(file.name)` guess unchanged
  — only the grouping mechanism changed here, not what's displayed per file (see known gap below).
- **Task 4** (`c11dfd9`): `video-detail.page.ts`'s "Compare variants" rail now fetches a video's real
  `VideoVariant[]` (via `listVariants`, fired from both `activateVariant` branches) and labels any
  file with a matching `variantId` using its real, humanized `variantType` (`VARIANT_TYPE_LABELS`),
  overriding the filename guess. Files with no `variantId` keep the filename-guess fallback. Fetch
  fails open to an empty array on error — a display enhancement, never a page-blocking dependency.

Two real test-fixture bugs were found and fixed during implementation (not plan-level design
issues — the plan's own illustrative example filenames happened to not exercise the behavior they
were meant to prove):
1. Task 3's draft fixture (`take1.mp4` + `weird_name_v9.mp4`) both guess `'Original'` under
   `mediaVariant()` — the `_v9` suffix doesn't match the versioned-suffix regex without a trailing
   `_original`/`_hd`/`_hook` word, so the test would have passed identically before and after the
   fix. Replaced the second filename with `weird_name_hd.mp4` (guesses `'HD'`) and asserted the
   actual sequential-label behavior instead of a `.media-file-group` count that the plan's own text
   already flagged as not exercising the change.
2. Task 4's draft fixture reused `mediaFile.name` (`'giant-sock-hd.mp4'`, hyphen before `hd`), which
   `mediaVariant()` does not recognize as an `'HD'` suffix (the regex requires an underscore, `_hd`)
   — so it guesses `'Original'`, making the test's negative assertion (`not.toContain('HD')`)
   vacuous. Replaced with `'giant_sock_hd.mp4'` (underscore), confirmed empirically to guess `'HD'`
   under old code and the real variant type under new code.

**Known, accepted gaps (deliberate, documented deferrals, not oversights):**
- `video-library.page.ts`'s per-row **label text** is still `mediaVariant()`-only, even for files
  with a known `variantId` — only the grouping/counting key is variantId-aware (Task 3). Giving each
  row its own real `variantType` label there would require a `listVariants()` call per video shown
  in a multi-video folder listing, which this plan deliberately did not add (the library page lists
  files across many videos at once; `video-detail.page.ts`'s equivalent fetch is one call per single
  active video, a different cost profile). Candidate for a future small follow-up if a real
  per-group `variantType` label becomes a product requirement on the library page too.
- No test coverage for an unmapped/future 7th `variantType` value reaching `VARIANT_TYPE_LABELS` in
  `video-detail.page.ts` (behavior is correct — falls back to rendering the raw string — but
  untested). Flagged by Task 4's reviewer; not blocking since the brief didn't request it.
- The frontend test runner did not fail the suite on 3 uncaught exceptions thrown by
  `video-detail.page.spec.ts`'s pre-existing tests before Task 4's `serviceWith()` mock fix (the
  tests still reported "passed," with the exceptions surfacing only as console noise after
  assertions had already run). This masked a real, if narrow, regression risk during this plan and
  could do so again in a future task — worth a follow-up on the Vitest/Angular test configuration,
  outside this plan's scope.

Next: Plan C (creative analysis completion), independent of A/B2 per §1's dependency notes — can
proceed directly without further prerequisites from this plan.

---

## 4d. Plan C completion record

**Status: ✅ Done.** Executed via `subagent-driven-development`, 6 tasks + final review. One task
(the final controller task) required a planning revision mid-execution after a real discovery; one
task required a fix round after review found a genuine Critical gap. Plan doc:
the completed implementation plan retained in Git history.

**A real architecture decision was made mid-plan, not just an implementation detail:** the
original roadmap text for this plan was ambiguous about whether `AnalysisJobService` (a complete,
already-built `QUEUED→RUNNING→COMPLETED/FAILED` durable job queue with `FOR UPDATE SKIP LOCKED`
leasing and retry, but with zero callers anywhere in the product) should be wired into the real
request path (async, job-queue-backed) or left as dead code while the fix stayed purely
synchronous. The user explicitly chose the async, job-queue-backed path, with one hard constraint:
going async must never be used as an excuse to call the ML service a second time, and the queue's
execution-progress state (`AnalysisJob`) must never be merged with the durable result state
(`VideoEntity.status`/`creative_analyses` existence) — two distinct models, never one derived from
the other except via the three pre-existing `markAnalysing()/markAnalysed()/markFailed()` calls.

**A planning gap was discovered and corrected mid-execution:** Task 3's implementer found that
`AnalysisJobController.java` already existed in this codebase — present since the repository's
very first commit, exposing `POST /api/v1/jobs/video-analysis/{videoId}`, `GET /api/v1/jobs/{id}`,
`POST /api/v1/jobs/{id}/retry` — completely missed by this plan's own pre-execution investigation.
A repository-wide zero-consumer check (Java, Angular, tests, scripts, docs, OpenAPI/API-contract
files) confirmed it had no callers anywhere. Per explicit user decision, Task 4 was revised
in-flight to delete this controller and consolidate the entire public analysis API under the
existing `VideoController`, rather than maintain two parallel public surfaces for triggering
analysis. This is recorded as a deliberate scope correction, not scope creep: the user was asked
before any deletion, and the deletion was independently re-verified safe twice (once before
deleting, once after) by two different task executions.

Final state: backend Spring suite 119/119 passing, `BUILD SUCCESS`; frontend suite 24/25 passing
(1 pre-existing, unrelated `app.spec.ts` nav-link-count failure, confirmed to predate this entire
plan and the one before it — not caused or fixed by this plan, out of scope). Full-plan diff
reviewed holistically: exactly 2 production `MlVideoClient.analyse()` call sites exist anywhere in
the backend (`VideoService.ingest()`, `VideoService.analyse()`), plus exactly 1
`VideoService.analyse()` caller (`AnalysisJobService.processNext()`'s worker) — confirmed via
repository-wide grep, matching the plan's binding "never call the ML endpoint a third way" rule
precisely. `VideoEntity.status` is mutated only via its three pre-existing mark methods, called
only from the two places that already called them before this plan — the two-state-model
separation holds structurally, not just by convention. Zero `force=true`-style bypass exists
anywhere.

Commit range: `29efc70..50b16ee` (plan doc + 7 implementation/fix commits + 1 plan-doc fence-bug
fix + 1 mid-plan revision commit).

Delivered:
- **Task 1** (`e1a1338`): `VideoService.ingest()` now persists the full creative-analysis result
  its own existing ML call already returns (previously only the technical-metadata portion was
  used, the classification/score/confidence/etc. were silently discarded). Zero additional ML
  calls. Implementer found and fixed a real pre-existing test bug exposed only once persistence
  actually started happening: `VideoServicePathAliasTest.java`'s mock used an invalid
  `classification` literal that violated the DB's `CHECK` constraint, previously invisible because
  nothing ever wrote it to the database.
- **Task 2** (`a396c1e`): `V34` migration — a partial unique index,
  `analysis_jobs(video_id) WHERE state IN ('QUEUED','RUNNING')`, the DB-level guarantee behind
  Task 3's concurrency safety.
- **Task 3** (`d73611d`): `AnalysisJobService.enqueue()` became idempotent — no duplicate active
  jobs per video (verified under real `CountDownLatch`-gated thread contention, with the
  implementer empirically proving the DB constraint's `catch` block is load-bearing by temporarily
  removing it and observing 7/8 threads hit a genuine `DuplicateKeyException`), no re-enqueueing
  once any analysis exists for a video (existence-based skip, deliberately not version-string-
  based — see the plan's own documented rationale for why that's correct, not a shortcut). All 10
  of the user's numbered test requirements pass as individually named test methods. Implementer
  diagnosed and fixed 3 real test-infrastructure bugs (cross-test job stealing from the shared
  Testcontainers context, the `@Scheduled` poller firing immediately at startup, a classic
  Mockito re-stubbing pitfall) via genuine root-cause tracing, not workarounds.
- **Task 4** (`5772b66`): `AnalysisJobController.java` deleted (see architecture-decision note
  above); `VideoController` became the sole public analysis API —
  `POST /{id}/analysis` (`200` only when a completed analysis already exists, `202` for both
  "already active" and "newly created," deliberately not keyed off the enqueue result alone) and
  `GET /{id}/analysis/status`, both returning a new `AnalysisStatusResponse` DTO rather than
  leaking the internal `JobView`/`EnqueueResult` records over HTTP. Implementer found and fixed a
  real Spring Boot 4 API-compatibility bug in the plan's own draft test code
  (`TestRestTemplate` moved packages in Boot 4; replaced with `RestTestClient`).
- **Task 5** (`ea3ed56`): `AnalysisStatus` TypeScript interface and
  `triggerAnalysis`/`getAnalysisStatus` methods added to `creative-intelligence.service.ts`,
  matching the backend DTO field-for-field. Zero deviations from the plan.
- **Task 6** (`fab2bcd` + fix `50b16ee`): `video-detail.page.ts` gained a trigger button, 5-second
  status polling (wired into both `activateVariant` branches, not just one), and a result panel
  rendering classification/Action DNA score/confidence/reason/storyboard path/analysis version.
  Review initially found one Critical gap — the polling observable had no error handling,
  violating the plan's explicit "must fail gracefully, page must stay usable" constraint, since a
  single transient failure would permanently kill polling with the switchMap chain's error
  propagating up and tearing down the subscription. Fixed in `50b16ee` with the same
  `catchError(() => of(null))` idiom already used elsewhere in this same file
  (`loadPerformance()`), proven by a new fake-timer test that fails one tick and asserts a later
  tick still fires.

**Known, accepted gaps (deliberate, documented deferrals, not oversights):**
- `AnalysisStatusResponse` does not carry `timeline`/feature-fingerprint data (the full
  `creative_fingerprints` payload) — the frontend's result panel therefore does not render a
  feature-fingerprint section, even though the roadmap's original Plan C text mentioned wanting
  one. This is a backend DTO scope boundary, not a frontend omission: extending
  `AnalysisStatusResponse` to carry these fields is a reasonable, small follow-up if the product
  wants them surfaced, not something this plan silently dropped.
- No test coverage exists for an unmapped/future `jobState` value reaching the frontend's 5-value
  TypeScript union (`NOT_STARTED/QUEUED/RUNNING/COMPLETED/FAILED`) — the backend field is a plain
  `String` with no matching enum constraint, so a future 6th state would compile fine on the
  frontend while silently lying about the type's completeness. Flagged by a task reviewer as a
  latent risk, not acted on since no 6th state exists today.
- This session's `file_search`/`grep_search` tools produced multiple confirmed false-negative
  results during this plan's execution (reporting files/content as "not found" when they
  demonstrably existed and were read directly moments later via `find`/`cat`/`grep` in the same
  session) — independently reproduced by at least two different task reviewers across two
  different tasks. This did not affect any delivered code's correctness (every affected finding
  was re-verified via direct file reads before being acted on), but it's a real tooling reliability
  issue worth a separate investigation outside this plan's scope.

Next: Plan D (evidence honesty) or Plan E (deployment and scale boundaries) per §1's dependency
notes — D depends on Plan A (done) and Plan B2 (done, both B2a and B2b); E is independent of
everything. Re-evaluate Part 03's scope against what's now actually landed across Plans A/B1/B2/C
before starting Part 03 work, per the roadmap's own stated dependency ("Part 03 depends on A and
B1/B2 at minimum").

---

## 5. Session handoff protocol

- Before starting work in a new session: read this file, run `git log --oneline -10` on `master`
  to see what's actually landed, check the status table in §1 against reality (a plan may be
  "done" in this doc but verify the commits are actually on master) — this repo has had multiple
  parallel sessions; do not assume the working tree matches what you last saw.
- After finishing a plan (or a meaningful chunk of one): update this file's status table and
  commit it together with the code changes, or as its own small commit if the code commit already
  happened.
- Never start Plan N+1 if Plan N's status is not ✅ where a real dependency exists (see §1's
  Dependency notes) — Plan B2 cannot start before B1; Plan D's completion/watch metrics item
  depends on Plan A's corrected query. Plans without a real dependency (A/C/E relative to each
  other) may be reordered if convenient.
- Each plan gets its own `docs/superpowers/plans/YYYY-MM-DD-<plan-name>.md` written via the
  `writing-plans` skill before implementation starts on that plan.
- Once Plans A and B1/B2 are done, re-open `PART_03_PROMPT.md`/`AUDIT_PART_03_IMPORT_PREDICTION_AND_LEARNING.md`
  and re-verify which of its "assume Part 02 is done" prerequisites are now actually satisfied
  before writing Part 03's own roadmap.

Status legend: ⬜ Not started · 🟨 In progress · ✅ Done · ⛔ Blocked
