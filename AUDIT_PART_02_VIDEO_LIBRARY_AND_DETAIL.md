# Content Intelligence Platform Audit - Part 02

## Video Library, Video Detail, Variant Identity and Performance Evidence

**Audit date:** 2026-10-03  
**Scope:** Existing implementation only. This report does not propose unrelated new features.  
**Method:** Source-code and schema inspection. Tests were intentionally not run.

---

## 1. Executive Summary

The Video Library and Video Detail area is not an empty shell. A substantial real-data workflow
already exists:

1. Mounted video folders can be discovered and searched.
2. Multiple folders can be selected and their files can be browsed together.
3. A video can be played without ingesting it.
4. Ingest creates a durable `videos` record with technical metadata.
5. Imported performance observations, publication context, manual interventions, audience shares,
   country shares and Reach Further evidence can be shown on the video detail page.
6. Instagram Graph snapshots can enter the same `performance_observations` ledger after a strict
   publication identity match.
7. Missing metrics are usually kept as `null`, rather than invented.

The primary problem is not lack of screens. It is that the identity model between a creative,
its physical files, its edit variants, its publications and its performance evidence is only
partially connected.

The database already contains `video_variants`, `variant_id` columns and variant-aware publication
constraints. The active backend has no variant entity/service/API, the import flow never writes a
variant ID, and the frontend calls every file in the same folder a variant. As a result, the UI
looks more complete than the underlying relationship model actually is.

There is also a serious performance-math correctness problem: observations declare whether a row
is `DAILY_INCREMENT`, `CUMULATIVE`, `SNAPSHOT` or `UNKNOWN`, but trajectory and growth calculations
treat every row as a cumulative checkpoint. CSV and Meta API observations can also be mixed into
one sequence without source reconciliation. The displayed chart, velocity, burst ratio and tail
ratio can therefore be mathematically wrong even though every individual database value is real.

### Overall assessment

| Area | State | Assessment |
|---|---|---|
| Folder discovery | Implemented | Useful, but deployment mount is wrong for the intended media source |
| Multi-folder selection | Implemented | Good user workflow |
| File playback | Implemented | Real file streaming with containment checks |
| Technical metadata | Partially implemented | Complete only after ingest |
| Creative identity | Incomplete | Folder path is incorrectly acting as creative identity |
| Variant model | Schema only | Present in PostgreSQL, absent from active application flow |
| Analysis workflow | Partially implemented | Backend exists, detail page cannot start or inspect it |
| Performance import | Implemented | Strict and auditable, but variant-unaware |
| Performance detail | Partially correct | Real observations, unsafe semantics/source mixing |
| Meta snapshot linkage | Implemented for Instagram | Strict deterministic match, append-only snapshots |
| Error transparency | Incomplete | Four detail API failures are silently rendered as no data |

---

## 2. What Exists Today

### 2.1 Video Library

The library page currently supports:

- loading immediate child folders under `library`;
- showing recursive video counts for each folder;
- folder autocomplete-style filtering;
- multi-select and select-all-filtered behavior;
- recursive or non-recursive file loading;
- filename/path filtering;
- ingested/not-ingested filtering;
- folder-level and single-file ingest;
- partial failure reporting when one selected folder cannot be read;
- direct navigation to a playable detail page.

Relevant implementation:

- `intelligence/frontend/src/app/pages/video-library.page.ts`
- `intelligence/frontend/src/app/core/creative-intelligence.service.ts`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java`

This is a real filesystem browser, not a mocked list.

### 2.2 Video playback

The detail screen streams the selected file through:

```text
GET /api/v1/videos/content?path=...
```

`MediaContentService` normalizes the requested path, resolves real paths and checks symlink
containment under `POMPOM_DATA_ROOT`. It also restricts extensions to the configured video set.
This is a sound implementation for local read-only media playback.

### 2.3 Ingest and technical metadata

Ingest currently:

1. validates that the file is inside the data root;
2. validates the extension;
3. calls the ML video endpoint;
4. obtains hash, duration, dimensions, FPS, aspect ratio, codec and audio presence;
5. stores a `videos` row;
6. returns a `VideoResponse`.

The detail page groups metadata into Video, File and Evidence sections. The revised layout is
compact and has explicit desktop/mobile constraints. The oversized-video problem has already been
addressed in CSS with a maximum 1040 px workspace and a bounded 290-500 px stage.

### 2.4 Persisted performance evidence

For an ingested video and selected platform, the detail page loads four independent views:

- Reach Further summary;
- performance trajectory;
- platform growth profile;
- audience discovery profile.

The page also supports recording:

- publication context;
- off-peak status;
- manual engagement interventions;
- manual Reach Further observations;
- screenshot evidence for Reach Further.

These are stored as durable records and not inferred from views.

### 2.5 Instagram Graph snapshots

The Meta implementation follows a conservative identity policy:

- external media is first matched by exact `platform_content_id`;
- then by canonicalized permalink;
- caption/title/filename fuzzy matching is forbidden;
- ambiguous or conflicting matches do not attach analytics to a local video;
- snapshots are append-only performance observations;
- unavailable Graph metrics remain `null` and carry an availability reason.

This is one of the stronger parts of the current implementation.

---

## 3. Actual End-to-End Data Flow

### 3.1 Filesystem to library

```text
Docker bind mount
  -> /data/library
  -> GET /videos/media-directories
  -> GET /videos/media-files
  -> Video Library groups files by parent directory
```

No database identity is required for browsing or playback.

### 3.2 File to evidence record

```text
POST /videos/ingest
  -> ML /v1/analysis/video
  -> SHA-256 and technical metadata
  -> videos row
  -> status INGESTED
```

Despite the ML endpoint name, ingest does not persist the returned creative analysis. That is done
only by the separate analysis operation.

### 3.3 Creative analysis

```text
POST /videos/{id}/analysis
  -> ML /v1/analysis/video again
  -> creative_analyses row
  -> creative_fingerprints row
  -> video status ANALYSED
```

The frontend has no method or control for this endpoint and no view for the resulting analysis,
classification, fingerprint, timeline or storyboard.

### 3.4 CSV/XLSX performance import

```text
Upload
  -> raw file is hash-staged
  -> rows parsed
  -> exact video ID or unique exact filename match
  -> unresolved rows require manual video selection
  -> commit writes performance_observations
```

The import is auditable and avoids fuzzy matches. It attaches rows only to `video_id`; it does not
resolve or write `variant_id`.

### 3.5 Meta Graph performance

```text
Instagram media
  -> exact publication ID/permalink match
  -> local video ID when match is EXACT
  -> append-only performance_observations snapshot
  -> Video Detail performance queries
```

Unmatched snapshots can be preserved with a null `video_id`, but they do not appear in the local
video detail until publication identity has been established and a later snapshot is captured.

---

## 4. Critical Findings

## P0-01 - Performance calculations ignore metric semantics

**Status:** Incorrect existing behavior  
**Impact:** The chart and derived metrics can be numerically wrong.

`performance_observations.metric_semantics` explicitly supports:

- `DAILY_INCREMENT`
- `CUMULATIVE`
- `SNAPSHOT`
- `UNKNOWN`

However:

- `PerformanceTrajectoryController` orders every row by timestamp and subtracts the previous
  `views` value;
- `PlatformGrowthProfileService` treats every `views` value as a cumulative checkpoint;
- `PlatformStateService` computes velocity and windows from the same unfiltered observation set.

Example failure:

```text
Day 1 DAILY_INCREMENT: 1,000 views
Day 2 DAILY_INCREMENT:   300 views
```

The current trajectory reports `-700` views and negative velocity. The real cumulative trajectory
is 1,000 then 1,300.

**Required completion:** Before any trajectory, velocity, burst or tail calculation, normalize
observations into one declared cumulative series. Reject or isolate `UNKNOWN`; accumulate
`DAILY_INCREMENT`; treat `CUMULATIVE`/compatible `SNAPSHOT` according to an explicit policy.

## P0-02 - Multiple observation sources are mixed without reconciliation

**Status:** Incorrect existing behavior  
**Impact:** A real CSV row and a real Meta API row can jointly produce a false trend.

Trajectory/growth queries filter only by `video_id` and `platform`. They do not separate or
reconcile:

- CSV observations;
- Meta Graph API observations;
- different source versions;
- different metric availability states;
- duplicate checkpoints for the same external post and measurement period.

This can create interleaved series with conflicting definitions and apparent negative/positive
velocity that did not occur on the platform.

**Required completion:** Define a canonical source selection/reconciliation rule for each
platform-content identity and metric. Detail APIs must return provenance and must not calculate a
single trajectory from incompatible streams.

## P0-03 - The implemented variant schema is disconnected from the product

**Status:** Designed and migrated, but not implemented end to end  
**Impact:** Variant comparison and performance attribution are not trustworthy.

The initial schema includes:

- `video_variants`;
- `parent_variant_id`;
- `variant_type`;
- `generated_path`;
- `edit_operations`;
- `performance_observations.variant_id`;
- `video_publications.variant_id`;
- `platform_content_states.variant_id`.

But the active application has:

- no `VideoVariant` entity;
- no variant repository;
- no variant service;
- no variant API;
- no ingest-to-variant association;
- no import row variant resolution;
- no frontend variant ID;
- no variant-aware performance query.

The frontend instead defines a creative as a physical parent folder and defines every video file in
that folder as one of its variants. This is only a presentation heuristic.

Consequences:

1. Two unrelated videos in one folder are shown as variants of one creative.
2. The same creative spread across folders is split into unrelated groups.
3. Publication context is recorded against the raw video, with `variantId = null`.
4. Imported outcomes cannot identify which edit was published.
5. Existing experiment and prediction `variant_id` fields cannot be connected to the files in the
   library.

**Required completion:** Finish the already-designed variant domain and make the UI consume it.
Folder grouping may remain a discovery aid, but it must not be the persisted identity model.

---

## 5. High-Priority Findings

## P1-01 - Content-hash deduplication loses additional file paths

`videos.content_hash` and `videos.relative_path` are both unique. During ingest, an existing content
hash returns the original row and does not store the newly encountered path.

The media-files endpoint later determines ingest state only by exact `relative_path`.

Result:

```text
folder-a/final.mp4 -> ingested as video A
folder-b/final-copy.mp4 -> same bytes, ingest returns video A
folder-b/final-copy.mp4 -> still displayed as Not ingested
```

This creates a permanent inconsistency between the ingest result and the library state.

**Required completion:** Add the missing path/asset alias relationship or change identity rules so
every physical file path can resolve to the canonical content record.

## P1-02 - Fresh Docker startup mounts the application repository as the media library

`intelligence/docker-compose.yml` mounts:

```yaml
- "../:/data/library:ro"
```

From the compose file location, `../` is the `content-intelligence-platform` repository root. It is
not the Pompom production media tree under `yuvarlak-dunya/POMPOM_HILLS_PRODUCTION`.

A fresh checkout therefore exposes application folders such as `intelligence`, `lab` and
`publisher` to Video Library, instead of the intended production series folders. Any currently
running environment that shows the production library is relying on an external/old override not
captured in this compose file.

**Required completion:** Make the intended read-only host media root an explicit environment-backed
bind mount and document its required value. Keep generated application data on the separate
`./data:/data` mount.

## P1-03 - Ingest performs ML analysis work but discards creative results

`VideoService.ingest()` calls `ml.analyse(...)` to obtain technical metadata. The returned contract
also contains creative analysis data, but ingest stores only technical facts and leaves status as
`INGESTED`.

`VideoService.analyse()` later calls the same ML endpoint again and only then persists
`creative_analyses` and `creative_fingerprints`.

This means:

- expensive video analysis may run twice;
- the first result is discarded;
- the detail button says `Ingest for analysis`, but analysis is not persisted;
- there is no frontend action that invokes the second call;
- videos can remain `INGESTED` indefinitely despite analysis already having been executed once.

**Required completion:** Separate cheap probe/hash from creative analysis, or persist the one ML
result exactly once. Connect the existing analysis job/endpoint to a visible state transition.

## P1-04 - Creative analysis output is absent from Video Detail

The backend can persist:

- primary and secondary creative engines;
- classification;
- Action DNA score;
- confidence;
- reason;
- timeline;
- feature fingerprint;
- storyboard path.

Video Detail exposes none of these and has no analysis trigger. A video marked `ANALYSED` looks
almost the same as an ingested technical record. This is unfinished existing functionality, not a
request for a new module.

## P1-05 - Detail API failures are silently converted to empty evidence

Video Detail loads four APIs through `forkJoin`, with each request wrapped in:

```typescript
catchError(() => of(null))
```

The page then shows dashes, `No trajectory available` or `No imported value` exactly as it would
for a successful empty response.

A database error, backend exception or incompatible migration is therefore indistinguishable from
genuinely missing evidence.

**Required completion:** Preserve independent loading but expose per-section error state. Empty,
unavailable and failed are three different facts.

## P1-06 - Existing imported completion/watch metrics are hidden as unavailable

The import service writes:

- `average_watch_seconds`;
- `total_watch_seconds`;
- `completion_rate`;
- `skip_rate`;
- `three_second_views`;
- `fifteen_second_views`;
- `plays`;
- `profile_visits`;
- `follows_attributed`.

Video Detail unconditionally displays:

```text
Completion rate      - Not available in imported data
Average watch time   - Not available in imported data
```

The trajectory API does not select these columns, so the UI says unavailable even when the import
contains them. This is a factual display error.

**Required completion:** Return and display the latest compatible imported values with their
timestamp/source. Only show `Not available` when the stored value is actually null.

## P1-07 - “24h” and “6h” checkpoints may be much earlier than their labels

`PlatformGrowthProfileService.checkpoint()` selects the last observation at or before the target
horizon.

If a video has observations at 1h and 30h:

- the `24h` checkpoint becomes the 1h value;
- the UI labels it `First 24h`;
- `viewsAfter24h` becomes `latest - 1h`;
- Facebook tail ratio is overstated.

The response carries the real measurement time, but the UI does not show it beside the label.

**Required completion:** Define a checkpoint tolerance/selection policy. A horizon with no suitably
close observation should be unavailable, or explicitly labeled with its actual age.

## P1-08 - Performance import cannot identify an edit variant

Automatic import matching accepts only:

- explicit `videoId`; or
- a filename that occurs exactly once in `videos`.

Manual resolution also selects only `videoId`. `writeObservation()` never writes `variant_id` even
though the schema supports it.

Once Original, Hook, HD and End Card versions are represented as true variants, the current import
flow still cannot attribute platform results to the published edit.

**Required completion:** Extend the existing exact/manual resolution step to the existing variant
identity. Do not add fuzzy attribution.

## P1-09 - Publication retrieval is not variant-aware

Publication creation accepts `variantId` and uniqueness is variant-aware. Retrieval in
`PlatformStateService.publication(videoId, platform)` ignores `variant_id` and returns the latest
publication for the video/platform.

When variant support is connected, opening one edit can show another edit's publication context.
The frontend currently never sends a variant ID, which hides the defect rather than resolving it.

---

## 6. Medium-Priority Findings

## P2-01 - Folder/file scan limits are silent

- Directory ingest stops after 1,000 files.
- Media file listing stops after 1,000 files.
- Folder counting stops after 10,000 files.

Responses do not say that results were truncated. A folder may claim more files than the UI can
ever list or ingest, and the user cannot distinguish truncation from completion.

## P2-02 - Variant labels are narrow filename guesses

The label parser recognizes only a small suffix set:

- `_vN_original`
- `_vN_hd`
- `_vN_hook`
- `_hook_endcard_test`
- `_hook`
- `_hd_1080x1920`
- `_hd`
- `_no_text`

Every other edit becomes `Original`, then `Original 2`, `Original 3`, and so on. The label can be
misleading even before the deeper variant identity issue is solved.

## P2-03 - Un-ingested technical metadata is intentionally incomplete

An un-ingested file is playable and has size/modified time, but duration, resolution, FPS, codec and
audio are dashes. This is internally consistent, but `Real file metadata` in the section header can
suggest those facts were read and missing. They simply have not been probed.

## P2-04 - Latest-row summary can lose still-valid metrics

The six summary values are taken from the final trajectory row. If the latest observation contains
views/reach but omits likes/comments/shares/follows, the screen shows dashes even if the immediately
previous snapshot reported those values.

This may be correct under strict snapshot semantics, but the UI does not explain whether a dash
means never reported or absent from the latest partial snapshot.

## P2-05 - Discovery score can combine observations from different dates without a staleness rule

Audience shares and US country share are queried independently. The API correctly exposes both
timestamps, but it will calculate one score even if the audience and country observations are far
apart in time.

The calculation is transparent, but it needs an alignment/staleness quality state before the score
is used for model training or ranking.

## P2-06 - Platform values are free-form in backend services

Most platform inputs are only lowercased, not checked against a controlled set. A typo such as
`facebok` creates a separate evidence partition that the normal tabs never query.

## P2-07 - Only the first intervention is marked on the chart

The ledger lists all interventions, but the chart marker uses only `interventions[0]`. A second or
third manual boost is not visible on the trajectory, even though later points remain globally
marked as intervened after the first event.

## P2-08 - Overview constructs placeholder facts from real records

The shared frontend service maps real videos to overview rows but hardcodes:

- format: `Unclassified`;
- character: `Unassigned`;
- platform: `Unknown`;
- hook rate: `0`;
- completion: `0`;
- views: `0`;
- published date: ingest date.

Zero is presented where the real state is unknown, and ingest date is presented as publication
date. This conflicts with the product's explicit no-fake-data principle.

Additionally, the platform mapper converts every value other than YouTube/TikTok to Instagram, so
Facebook and unknown platform values are mislabeled as Instagram.

## P2-09 - Meta detail and local video detail are separate operator workflows

The Meta Reels screens can fetch/capture Instagram analytics, while Video Detail reads persisted
observations. Video Detail does not expose whether the latest data came from CSV or Graph API and
does not offer the existing snapshot capture action.

The storage is shared, but the operator cannot see that connection from the local video page. This
contributes to the silent-source-mixing problem.

---

## 7. What Is Already Strong

The following should be preserved while completing this area:

1. **No automatic fuzzy analytics attribution.** Exact identifiers and manual resolution are the
   right default.
2. **Filesystem containment.** Playback and ingest reject paths outside the configured root.
3. **Read-only mounted media.** Production source files are not modified by the application.
4. **Append-only evidence.** Performance and platform-state evidence favor immutable observations
   and correction events.
5. **Explicit intervention ledger.** Manual engagement is modeled separately from organic
   trajectory.
6. **Explicit Reach Further evidence.** Views do not silently infer Meta UI state.
7. **Null rather than invented metrics.** Most backend flows preserve unavailable data as null.
8. **Strict Meta identity conflict handling.** Conflicting ID/permalink matches do not attach data.
9. **Playable before ingest.** Browsing is separated from database mutation.
10. **Responsive detail layout.** Video size and technical information hierarchy are now bounded
    and usable on desktop/mobile.

---

## 8. Completion Order

This order fixes correctness before presentation polish.

### Phase A - Repair observation mathematics

1. Define canonical metric semantics normalization.
2. Separate/reconcile CSV and API sources.
3. Reject incompatible rows from one trajectory.
4. Add explicit provenance and quality state to trajectory responses.
5. Correct horizon checkpoint selection.

### Phase B - Finish the existing variant model

1. Add backend access to `video_variants` already present in the schema.
2. Associate discovered physical files with a canonical video/variant identity.
3. Replace folder-as-creative grouping with persisted identity.
4. Carry `variantId` through publication context, imports, performance queries and detail routes.
5. Resolve the same-hash/multiple-path alias case.

### Phase C - Complete analysis in Video Detail

1. Stop doing duplicate ML work.
2. Make analysis status and failure visible.
3. Connect the existing analysis operation/job.
4. Display the persisted analysis, timeline, fingerprint and storyboard.

### Phase D - Make evidence states honest

1. Distinguish empty from failed APIs.
2. Display imported completion/watch metrics when present.
3. Show metric source, measurement time and availability.
4. Remove overview zero placeholders and ingest-as-published labeling.
5. Validate platform identifiers.

### Phase E - Correct deployment and scale boundaries

1. Parameterize the production media bind mount.
2. Report scan truncation.
3. Add pagination/cursors before libraries exceed current limits.

---

## 9. Definition of Done for This Existing Feature Area

Video Library and Video Detail should be considered complete only when all statements below are
true:

- [ ] A physical file can always resolve to its canonical content identity after ingest.
- [ ] Duplicate bytes at multiple paths do not remain falsely marked `Not ingested`.
- [ ] A creative and its variants are persisted identities, not inferred from directory layout.
- [ ] Every published edit can be linked to the exact variant that generated its outcome.
- [ ] Import resolution can target that exact variant without fuzzy matching.
- [ ] Trajectory math uses compatible, normalized observation semantics.
- [ ] CSV and API sources cannot silently form one contradictory series.
- [ ] 6h/24h/48h/7d labels represent observations close enough to those horizons.
- [ ] Existing completion/watch metrics appear when they were imported.
- [ ] API failure is visibly different from no evidence.
- [ ] Creative analysis runs once and its persisted result is visible in detail.
- [ ] The default Docker configuration mounts the intended production media root.
- [ ] Overview and detail never turn unknown values into zero or an incorrect platform/date.
- [ ] Scan truncation is disclosed.

---

## 10. Files Reviewed

### Frontend

- `intelligence/frontend/src/app/pages/video-library.page.ts`
- `intelligence/frontend/src/app/pages/video-detail.page.ts`
- `intelligence/frontend/src/app/core/creative-intelligence.service.ts`
- `intelligence/frontend/src/app/core/meta-read.service.ts`
- `intelligence/frontend/src/app/core/meta-read.models.ts`
- `intelligence/frontend/src/app/pages/meta-reels.page.ts`
- `intelligence/frontend/src/app/pages/meta-reel-analytics.page.ts`
- `intelligence/frontend/src/app/app.routes.ts`
- `intelligence/frontend/src/styles.scss`

### Backend

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoEntity.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoRepository.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/MediaContentService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/ml/MlVideoClient.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/job/AnalysisJobService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PerformanceImportService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/DiscoveryProfileService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/InterventionService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/meta/MetaMediaMatcher.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/meta/MetaReelsService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/meta/MetaPageContentService.java`

### Schema and deployment

- `intelligence/backend/src/main/resources/db/migration/V1__initial_schema.sql`
- `intelligence/backend/src/main/resources/db/migration/V2__platform_state_observations.sql`
- `intelligence/backend/src/main/resources/db/migration/V5__observation_quality_and_discovery_metrics.sql`
- `intelligence/backend/src/main/resources/db/migration/V28__add_external_publication_identity.sql`
- `intelligence/backend/src/main/resources/db/migration/V29__add_meta_readonly_snapshot_fields.sql`
- `intelligence/backend/src/main/resources/application.yml`
- `intelligence/backend/src/main/resources/application-docker.yml`
- `intelligence/docker-compose.yml`

---

## 11. Audit Boundary

This report does not claim runtime record counts or test pass/fail status. It evaluates what the
current source and schema implement, what they leave disconnected, and where the current code can
display a mathematically or semantically incorrect result.

