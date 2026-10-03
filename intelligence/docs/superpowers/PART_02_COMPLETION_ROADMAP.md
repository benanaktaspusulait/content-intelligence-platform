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
| B2 | Variant-aware ingest, import, publication, performance queries + path-alias dedup | Phase B.2-5 | backend, frontend | ⬜ Not started |
| C | Creative analysis completion (stop duplicate ML calls, surface analysis in Video Detail) | Phase C | backend, frontend | ⬜ Not started |
| D | Evidence honesty (error-vs-empty, completion/watch metrics, overview placeholders, platform validation) | Phase D | backend, frontend | ⬜ Not started |
| E | Deployment and scale boundaries (media mount, scan truncation, pagination) | Phase E | backend, frontend, deployment config | ⬜ Not started |

### Dependency notes
- **A is independent** of B/C/D/E — pure backend query-correctness fix on existing columns. Can be
  done first or in parallel with B1; sequenced first here for lower risk and because Part 03's
  dataset-construction phase needs correct trajectory math regardless of variant identity.
- **B2 depends on B1** (needs the `VideoVariant` entity/service to exist before anything can
  reference a real variant ID).
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

### Plan B2 — Variant-aware ingest, import, publication, performance queries + path-alias dedup
**Audit section:** Phase B, items 2-5
**Files:**
- `VideoService.java` (associate discovered physical files with a canonical video/variant identity
  rather than treating folder-as-creative; fix the content-hash dedup path from P1-01 — add a
  path-alias relationship so a second path resolving to the same content hash is recorded, not
  discarded)
- New migration `V32__...sql` (never edit V1-V31; add the path-alias table from P1-01; add
  `intervention_events.variant_id` nullable FK, since that table has no variant column at all per
  the audit's P0-03 finding)
- `PerformanceImportService.java` (extend the existing exact/manual resolution step to accept and
  write `variant_id` on `writeObservation()`'s INSERT — no fuzzy attribution, per P1-08)
- `PlatformStateService.java` (`publication(videoId, platform)`'s read path becomes variant-aware,
  matching the already-variant-aware write path `recordPublication()`, per P1-09)
- `PerformanceTrajectoryController.java`, `PlatformGrowthProfileService.java`,
  `DiscoveryProfileService.java` (accept and filter by `variantId` where provided)
- Frontend: `video-library.page.ts`/`video-detail.page.ts` (introduce a real `variantId` concept
  in TypeScript interfaces/HTTP calls/routes; replace folder-grouping-as-variant heuristic with the
  persisted identity from Plan B1 — folder grouping may remain a *discovery aid* but must not be
  the identity model)
**Goal:** a creative and its variants are persisted identities, not inferred from directory layout;
every published edit can be linked to the exact variant that generated its outcome; import
resolution can target that exact variant; duplicate bytes at multiple paths no longer show as
permanently "Not ingested."

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
`docs/superpowers/plans/2026-10-03-part02-plan-a-observation-mathematics.md`.

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
`docs/superpowers/plans/2026-10-03-part02-plan-b1-variant-domain.md`.

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
