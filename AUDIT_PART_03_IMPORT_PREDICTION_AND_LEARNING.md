# Content Intelligence Platform Audit - Part 03

## Performance Import, Predictions, Evaluation and Learning Loop

**Audit date:** 2026-10-03  
**Scope:** Existing and partially implemented functionality only. No unrelated feature proposal.  
**Method:** Source, schema, documentation and read-only local data inspection. Tests were not run.

---

## 1. Executive Summary

The repository contains many of the nouns required for a learning platform:

- immutable performance imports;
- normalized observations;
- creative fingerprints;
- pre-publish and live predictions;
- prediction locking;
- prediction audits;
- model versions;
- challenger/champion status;
- temporal backtesting concepts;
- experiments and test planning;
- reliability and calibration documentation.

However, these pieces do not currently form one operational learning loop.

There are three independent implementations:

1. **Angular + Spring + PostgreSQL** under `intelligence/frontend`, `intelligence/backend` and
   `intelligence/ml-service`.
2. **Standalone Python + SQLite Lab** under `lab/`.
3. **Creative Render analytics** under `intelligence/creative-render-service` with separate
   prediction and A/B-test tables in the `creative_render` schema.

The active Angular application talks to the Spring backend. It does not talk to the Lab. The
Spring prediction endpoint always calls a cold-start function that deliberately returns no
expected values and uniform probabilities. Registered champion models are never loaded by that
function. The training and backtest ML endpoints are placeholders that do not train, evaluate or
persist a model.

The Lab contains the most complete empirical workflow: import mapping, normalized evidence,
trajectory rebuild, median predictions, multi-horizon audits, reliability summaries and dataset
snapshots. But it uses its own SQLite database, is not started by Docker Compose, is not visible to
Angular, and has no data bridge to PostgreSQL.

The local Lab database is not a hidden trained system. At audit time it contained:

| Record type | Count |
|---|---:|
| Videos | 1 |
| Performance imports | 1 |
| Normalized observations | 1 |
| Performance trajectories | 0 |
| Predictions | 0 |
| Prediction audits | 0 |
| Model versions | 0 |
| Model evaluations | 0 |
| Experiments | 0 |

The one observation is the approximately 60,000-view Facebook result for the `What’s Wrong?`
Giant Spoon-related file already discussed in the project history.

### Overall assessment

| Area | State | Assessment |
|---|---|---|
| Raw import staging | Implemented | Immutable and hash-deduplicated |
| Import field mapping UI | Misleading | User changes do not reach backend |
| Row matching | Backend implemented | Exact/manual policy is sound; manual UI is absent |
| Timestamp normalization | Incomplete | Supplied timezone is stored but not applied |
| Prediction persistence | Implemented | Draft/locked/evaluated lifecycle exists |
| Prediction generation | Cold-start only | No learned expected values |
| Live feature cutoff safety | Incorrect | Historical cutoff can receive later information |
| Prediction evaluation | Incorrect lifecycle | Only one horizon can be evaluated |
| Model registry | CRUD-like shell | Promotion is not validation-gated |
| Training/backtest | Stub | No trained artifact or metrics are produced |
| Reliability | Lab only | Angular route is a placeholder |
| Experiments/test planner | Backend partial | Angular routes are placeholders |
| Learning feedback | Multiple prototypes | No canonical production loop |

---

## 2. The Three Existing Systems

## 2.1 Angular/Spring/PostgreSQL system

This is the application exposed by `intelligence/docker-compose.yml`.

### It currently owns

- `import_batches`, `import_rows`, `performance_observations`;
- `predictions`, `prediction_audits`;
- `model_versions`, `model_evaluations`;
- `experiments`, `experiment_variants`;
- creative analyses and fingerprints;
- Angular Import Data and Predictions pages;
- placeholder routes for Experiments, Test Planner, Performance, Reliability and Model Versions.

### Its prediction behavior

Spring sends the latest creative fingerprint to the ML service. The ML service returns:

- model version `cold-start-baseline-v1`;
- dataset version `<platform>-no-observed-training-data`;
- comparable sample size `0`;
- confidence `LOW`;
- `expectedValue = null` for every horizon;
- uniform performance-band and trajectory probabilities.

This behavior is honest as a cold-start response, but it is not learning from imported outcomes.

## 2.2 Standalone Lab system

`lab/` is a separate local-first Python application with its own CLI, HTTP dashboard, migrations
and SQLite database.

It includes substantially more complete implementations for:

- spreadsheet alias mapping;
- timezone conversion;
- raw/normalized/derived data separation;
- import row reconciliation;
- trajectory rebuilds;
- empirical platform medians and quantile intervals;
- multi-horizon prediction target tables;
- immutable lock behavior;
- automatic prediction audit from trajectories;
- reliability summaries;
- expanding-window backtest;
- human blind predictions;
- dataset snapshots;
- challenger creation;
- experiment planning;
- character performance research.

None of those records are read by the Spring backend or Angular frontend.

## 2.3 Creative Render analytics system

The render service contains another prediction implementation:

- `performance_predictions`;
- `ab_tests`;
- `PredictiveAnalyticsService`;
- `ABTestingService`.

This implementation uses fixed formulas such as quality-to-view multipliers and simplified A/B
statistics. The A/B service literally stores `95` confidence and `0.05` p-value after comparing the
latest two values; it does not run the t-test claimed by its class comment.

The services have no controller callers for prediction or A/B operations. The frontend Nginx
configuration proxies only `/api/v1/render-jobs` to the render service; all other `/api/` traffic
goes to the main backend. Therefore this analytics implementation is not part of the current
Angular product flow.

---

## 3. Existing Spring Import Flow

The active flow is:

```text
Angular file selection
  -> POST /api/v1/imports/preview
  -> unchanged file stored under data/imports/raw
  -> SHA-256 duplicate check
  -> CSV/TSV/XLSX parse
  -> exact video UUID or unique filename match
  -> unresolved rows persisted
  -> POST /api/v1/imports/{id}/commit
  -> performance_observations
```

### Strong parts

1. Raw source files are preserved.
2. File hashes prevent accidental duplicate batches.
3. Raw row JSON remains available.
4. Empty/invalid numeric values become null rather than zero.
5. Fuzzy video matching is forbidden.
6. Manual row resolution creates an audit event.
7. Commit is blocked while unresolved rows remain.
8. Explicit Reach Further fields are imported without inferring state from views.
9. Country shares and new-audience score retain provenance.

These behaviors should remain in the canonical implementation.

---

## 4. Critical Findings

## P0-01 - No production learning loop reaches prediction generation

**Status:** Existing architecture is disconnected  
**Impact:** Imported outcomes never improve the predictions shown in Angular.

The intended loop appears to be:

```text
performance observations
  -> normalized trajectories
  -> temporal dataset snapshot
  -> challenger training
  -> backtest/evaluation
  -> human promotion
  -> champion inference
  -> immutable predictions
  -> prediction audits
```

The active Spring/ML path stops after the first item:

- Spring stores observations.
- The ML prediction function does not query or receive them.
- It always emits the same uniform cold-start prior.
- The ML training endpoint returns only a status string and row count.
- The ML backtest endpoint always returns `promotionEligible: false` without metrics.
- No Spring client calls either training endpoint.
- The model registry is not consulted during prediction.
- No model artifact is loaded for inference.

The richer learning path exists only in the disconnected Lab.

**Required completion:** Select one canonical runtime, then connect observation normalization,
dataset versioning, challenger creation, temporal evaluation, human promotion and champion
inference in that runtime. For the current product, the natural canonical target is the active
Spring/PostgreSQL application; Lab algorithms can be ported deliberately rather than maintained as
a second database.

## P0-02 - Prediction evaluation makes multi-horizon auditing impossible

One prediction contains nine horizons. The database also allows one `prediction_audits` row per
prediction/horizon.

But `PredictionService.evaluate()`:

1. accepts one `horizonMinutes` and one manually entered actual value;
2. inserts one audit row;
3. marks the entire prediction `EVALUATED`.

`PredictionEntity.markEvaluated()` only accepts a `LOCKED` prediction. A second horizon evaluation
therefore fails because the prediction is already `EVALUATED`.

Additional defects:

- the requested horizon does not have to exist in the prediction payload;
- when the horizon is absent, an audit with `expectedAvailable: false` is still inserted;
- that empty comparison still marks the whole prediction evaluated;
- actual value is not tied to a persisted observation or measurement timestamp;
- the audit does not preserve observation/source identity;
- interval coverage, band correctness, Brier score and trajectory correctness are never computed.

**Required completion:** Evaluate all eligible horizons independently from persisted, cutoff-safe
observations. Mark the prediction fully evaluated only when the required evaluation policy is
satisfied. Keep partial evaluation state explicit.

## P0-03 - Live prediction cutoff can leak future information

`generateLive()` accepts a caller-supplied `knowledgeCutoff`. Growth and discovery services receive
that cutoff, but Reach Further features are built through `reachFurtherSummary(videoId, platform)`,
which has no cutoff parameter.

The resulting feature map can include:

- three-hour post-status velocity calculated with observations later than the requested cutoff;
- publication context recorded after the cutoff;
- summary values built from current/all-time state;
- a creative fingerprint created after a historical cutoff, because the latest fingerprint is
  selected without a creation-time filter.

The API also does not reject a null or future cutoff.

This violates the repository's stated rule that a live forecast may use only information available
at its knowledge cutoff.

**Required completion:** Every selected fingerprint, platform state, publication fact and derived
metric must be queried as-of the same cutoff. Reject invalid/future cutoffs and persist the exact
feature provenance used.

## P0-04 - Three competing prediction domains have no source-of-truth decision

The repository has:

- `public.predictions` in the main backend;
- `public.performance_predictions` from the main backend's legacy V24 migration;
- `creative_render.performance_predictions` in the render service;
- SQLite `predictions` in Lab.

It also has two different experiment domains (`experiments` and `ab_tests`) and multiple model
registries with incompatible schemas.

These are not replicas and are not synchronized. IDs, features, horizons, confidence meanings and
evaluation methods differ.

This makes terms such as “prediction count”, “champion model” and “experiment result” ambiguous.

**Required completion:** Declare one canonical domain and migration boundary. Mark the other tables
and services as legacy, migrate any required data, then remove or archive the inactive write paths.

---

## 5. High-Priority Findings

## P1-01 - Import field mapping controls do not affect the import

The Angular page allows users to select mappings and run `Auto-map fields`. Those selections remain
only in browser signals.

The frontend sends neither mapping nor sample decisions to the backend. The backend stores:

```json
{}
```

in `import_batches.column_mapping` and interprets rows using hardcoded header aliases during commit.

`Auto-map fields` is particularly unsafe: every unresolved column is visually assigned to `views`,
but the backend ignores that choice.

The UI therefore claims an operator-reviewed schema mapping that does not exist.

**Required completion:** Either remove the nonfunctional controls and show the backend's detected
mapping, or persist/apply reviewed mappings before commit. The screen must not imply that a local
selection changed normalization when it did not.

## P1-02 - Unresolved rows cannot be resolved in Angular

The backend exposes:

- `GET /imports/{id}/rows`;
- `POST /imports/{id}/rows/{rowId}/match`.

The Angular service and Import Data page expose neither operation. When preview contains unresolved
rows, commit is disabled and the user has no path on that screen to resolve them.

The flow is therefore complete only through direct API use, not through the product UI.

## P1-03 - Import platform is hardcoded to Instagram

The Import Data page:

- displays `Instagram` as static text;
- always calls preview with `instagram`;
- has no Facebook, TikTok or YouTube selection.

This directly conflicts with the multi-platform observation schema and the Facebook/TikTok work
already present elsewhere in the product.

## P1-04 - Timezone assumption is stored but never used to parse timestamps

Angular sends the browser timezone and the backend stores it on the import batch. During commit,
timestamps are parsed only as `Instant` or `OffsetDateTime`.

Common export values such as:

```text
2026-09-28 07:00
28/09/2026 07:00
```

have no offset and become null. XLSX date cells formatted as local dates are affected as well.

The standalone Lab already contains timezone-aware parsing for ISO, common local formats and Excel
serial dates, but that implementation was not carried into the active importer.

**Required completion:** Apply the stored timezone during canonicalization and preserve raw, local,
UTC and assumption fields as designed.

## P1-05 - Model promotion is not validation-gated

The model registry documentation says promotion requires:

- sufficient sample size;
- temporal validation;
- calibration quality;
- improvement over champion and simple baselines;
- audited human approval.

`ModelRegistryController.promote()` checks only that status is `CHALLENGER`. It does not query
`model_evaluations`, verify metrics, verify artifact existence/hash or compare against the current
champion. Any registered challenger, including one with empty metrics, can be promoted.

## P1-06 - Registered champion models do not affect predictions

Predictions store a model-version string returned by the ML service. There is no foreign key to
`model_versions`, no registry lookup, no artifact loader and no platform/model-type champion
selection.

A promoted model therefore changes registry state but changes no inference behavior.

## P1-07 - ML training and backtest endpoints are status stubs

`POST /v1/training/train`:

- rejects fewer than 30 rows;
- otherwise returns `CHALLENGER_CREATED`, dataset version and row count;
- creates no fitted model;
- writes no artifact;
- computes no metrics;
- registers no challenger.

`POST /v1/evaluation/backtest` always returns expanding-window metadata and
`promotionEligible: false` without running a backtest.

These endpoints currently describe intent, not implementation.

## P1-08 - Predictions UI labels view forecasts as completion percentages

The ML payload declares each target metric as `views`. The frontend takes the first target and
renders it under:

```text
Expected completion
```

It appends `%` to `expectedValue` and places the value directly on a percentage interval bar.

Once a model returns an actual expected view count, the page would display, for example,
`5000% completion`. This is a semantic display defect currently hidden by cold-start null values.

The page also displays only the first target, which is the 30-minute horizon, without identifying
that horizon.

## P1-09 - Prediction controls are present but disconnected

On the Predictions page:

- `New prediction` has no click handler;
- row inspect buttons have no handler or route;
- there is no generate form;
- there is no lock action;
- there is no prediction detail;
- there is no live prediction action;
- there is no evaluation workflow;
- there is no payload/provenance view.

The backend lifecycle exists, but the page is list-only.

## P1-10 - Existing reliability, model and experiment backends are hidden behind placeholders

Angular routes for:

- Experiments;
- Test Planner;
- Performance;
- Model Reliability;
- Model Versions

all render `PlaceholderPage`.

The backend already has experiment, test-planner and model-registry endpoints. Prediction audits
exist in the schema. The incomplete state is therefore not just an unstarted feature; existing
backend functionality has no product surface.

## P1-11 - YouTube is represented in UI types but rejected by ML contracts

The frontend prediction platform type includes YouTube. The ML Pydantic contract accepts only:

- Instagram;
- Facebook;
- TikTok.

A YouTube prediction request reaching the ML service receives validation failure. Platform support
is inconsistent across layers.

## P1-12 - Prediction variants are not implemented

The `predictions` table and entity contain `variant_id`, but prediction generation never accepts or
sets it, and `PredictionView` does not return it. This is the same disconnected variant model found
in Part 02 and prevents edit-specific forecasts and audits.

## P1-13 - Lab challenger promotion cannot be completed either

The Lab is more complete, but its model lifecycle also stops short:

- `create_challenger()` always sets `promotion_eligible: false`;
- `backtest()` writes a model evaluation but never updates the challenger's validation JSON;
- `promote()` requires that flag to be true;
- the CLI does not expose the `promote()` function.

So even the isolated Lab cannot complete challenger-to-champion promotion through its documented
operator workflow.

---

## 6. Medium-Priority Findings

## P2-01 - Import mapping shows fake sample values

Every source column displays `From source file` instead of an actual sample value. The preview DTO
does not return samples. Confidence is generated locally from a small name heuristic and is not the
backend's normalization confidence.

## P2-02 - Mapping targets cover only a small subset of imported metrics

The UI mapping dropdown offers only:

- video ID;
- views;
- completion rate;
- hook rate;
- published at.

The backend schema supports many more metrics and identifiers. `hook_rate` is not one of the
backend importer's recognized canonical columns, so even that visible target has no active effect.

## P2-03 - Import workflow step state begins at step 2

The page initializes `step = 2` before a file has been selected, while the visual step list marks
Source as complete. It presents a staged workflow before any source exists.

## P2-04 - Duplicate import status is not represented correctly in UI

Preview can return an existing PREVIEWED or COMMITTED batch for a duplicate hash. The page resets
its local `committed` flag and does not explain that the uploaded file was already known. The
backend's `duplicate` and `status` fields are not shown.

## P2-05 - Prediction list uses video UUID instead of a useful identity

The API returns only `videoId`; the frontend displays that UUID as the video name. It does not join
the video filename, creative, variant or publication identity.

## P2-06 - Small-sample warning threshold is a frontend constant

The page labels every prediction with `n < 80` as a small-sample flag. Other project documents use
30, 15/50 or model-specific thresholds. The value is not supplied by the model response or model
registry and can drift from actual policy.

## P2-07 - Platform validation is inconsistent

Spring controllers usually lowercase arbitrary strings, the frontend has its own platform union,
the ML service has a strict three-platform enum, and the render service uses a Java enum. Typos can
create database partitions that inference cannot consume.

## P2-08 - Prediction target table is orphaned in Spring

PostgreSQL has a normalized `prediction_targets` table with interval and probability fields plus an
immutability trigger. Spring stores every target inside `predictions.payload` and never writes or
reads `prediction_targets`.

The table's trigger therefore protects no active Spring prediction data. Payload immutability is
still protected by the parent prediction trigger, but there are two competing representations.

## P2-09 - Model evaluations and human predictions are orphaned in Spring

`model_evaluations` and `human_predictions` are migrated but have no Spring service, controller or
frontend usage. Their equivalent workflows exist only in Lab.

## P2-10 - Root README overstates completion

The repository README marks the Learning Engine and Advanced Analytics phases complete and labels
the system `Production Ready`. It also documents analytics endpoints that do not expose the
prediction services described.

The active state is materially different: predictions are cold-start only, training/backtest are
stubs, reliability/model pages are placeholders, and multiple data stores are disconnected.

## P2-11 - ML feedback package is a non-persistent prototype

`intelligence/ml-service/app/feedback` describes PostgreSQL tables, API endpoints, dashboards and
version generation, but the active collector stores data in an in-memory Python list. The package
is referenced only by tests and its own documentation. The documented `version_generator.py` does
not exist.

It is another prototype path, not part of the active feedback loop.

## P2-12 - Render-service analytics contain fabricated statistical certainty

`ABTestingService` assigns fixed values:

```text
confidence level = 95
p-value = 0.05
```

without a statistical test. Its class documentation says it performs a t-test. This code is not
currently exposed through the Angular proxy, but it must not become active in its present form.

The same module predicts views with fixed quality multipliers and labels them as predictive
analytics. This conflicts with the main application's explicit cold-start honesty.

---

## 7. What Should Be Preserved

1. **Immutable locked predictions.** PostgreSQL trigger protection is the correct evidence model.
2. **Knowledge cutoff as a first-class field.** The concept is correct; all feature queries must
   honor it.
3. **Cold-start honesty.** Returning null expectations is preferable to fabricated view counts.
4. **Raw import preservation.** Source evidence must remain unchanged.
5. **Strict/manual identity matching.** Avoid fuzzy attribution.
6. **Null metrics.** Missing metrics should never become zero.
7. **Human model promotion.** Promotion should stay explicit and audited.
8. **Temporal evaluation requirement.** Expanding-window validation is the right policy.
9. **Prediction audits separate from payloads.** Outcomes should not mutate forecasts.
10. **Lab's raw/normalized/derived separation.** This is stronger than the current Spring
    observation calculations and is worth carrying into the canonical system.

---

## 8. Canonicalization Plan

This is a completion plan for existing designs, not a new product direction.

### Phase A - Choose the source of truth

1. Declare Spring/PostgreSQL the canonical production evidence store.
2. Freeze new writes to Lab and legacy render prediction tables.
3. Document which Lab algorithms will be ported.
4. Inventory any Lab records requiring migration.
5. Mark legacy tables/services clearly before removal.

### Phase B - Finish import intake

1. Make field mapping real or remove the controls.
2. Add row-resolution UI using existing backend endpoints.
3. Add platform selection.
4. Apply timezone assumptions during timestamp normalization.
5. Preserve actual sample values and backend mapping confidence.
6. Carry variant identity from Part 02.

### Phase C - Build one normalized training dataset

1. Normalize metric semantics and sources as defined in Part 02.
2. Rebuild checkpoint trajectories deterministically.
3. Exclude paid/intervened/incompatible evidence according to explicit policy.
4. Create versioned, cutoff-safe dataset snapshots.
5. Persist row-level provenance for every training example.

### Phase D - Repair prediction lifecycle

1. Make generation choose a registered model family/version.
2. Persist exact feature snapshot and provenance.
3. Make every input cutoff-safe.
4. Carry `variantId`.
5. Evaluate all horizons independently.
6. Populate interval, band, trajectory and calibration audits.
7. Represent partial vs complete evaluation.

### Phase E - Complete model governance

1. Implement real training artifact creation.
2. Implement temporal backtest metrics.
3. Write `model_evaluations` from backtests.
4. Enforce promotion gates in the backend transaction.
5. Verify artifact identity/hash before promotion.
6. Make champion selection affect inference.
7. Keep promotion human and audited.

### Phase F - Connect product surfaces

1. Implement New Prediction and prediction detail.
2. Add lock/live/evaluate actions.
3. Replace completion-percent labels with metric/horizon-aware displays.
4. Connect Experiments, Test Planner, Reliability and Models pages to existing APIs.
5. Display model, dataset, feature and evidence provenance.

---

## 9. Definition of Done

- [ ] One canonical database owns observations, trajectories, models, predictions and audits.
- [ ] Lab and render analytics are either integrated, migrated or explicitly archived.
- [ ] Import field mappings shown in UI are the mappings used at commit.
- [ ] Unresolved rows can be resolved without direct API calls.
- [ ] Import timezone is applied to naive timestamps.
- [ ] Platform support is consistent across frontend, Spring, ML and storage.
- [ ] A versioned dataset snapshot is reproducible from persisted evidence.
- [ ] Training produces a real artifact and metrics.
- [ ] Backtesting produces persisted temporal evaluations.
- [ ] Promotion is impossible without passing configured evaluation gates.
- [ ] The promoted champion is the model used for inference.
- [ ] Prediction features are fully cutoff-safe.
- [ ] Every prediction identifies its exact video variant.
- [ ] All prediction horizons can be audited.
- [ ] Actual values come from identifiable persisted observations.
- [ ] Prediction list/detail show the correct metric and horizon units.
- [ ] Reliability is calculated from audits and visible in the application.
- [ ] No screen presents a visual-only mapping or inactive action as functional.
- [ ] Documentation no longer calls stub/disconnected paths production-ready.

---

## 10. Local Data Snapshot

The committed Lab SQLite file at `lab/.lab_data/library.sqlite3` was inspected read-only through a
temporary copy because SQLite attempted to open journal state beside the original file.

The single video record was:

```text
ID:       4b5d0cfc9b928821
Series:   What’s Wrong? uploaded
Duration: 15.104 seconds
Format:   1080 x 1920
```

The single import was:

```text
Source:   known_observations.csv
Platform: facebook
Rows:     1
Status:   COMMITTED
```

The normalized observation was:

```text
Semantics: SNAPSHOT
Views:     60000
Paid:      false
```

No trajectory or learning artifact has yet been built from that observation.

The Docker application stack was not running at the time of this audit, so no runtime PostgreSQL
record counts are asserted here.

---

## 11. Files Reviewed

### Angular

- `intelligence/frontend/src/app/pages/import-data.page.ts`
- `intelligence/frontend/src/app/pages/predictions.page.ts`
- `intelligence/frontend/src/app/core/creative-intelligence.service.ts`
- `intelligence/frontend/src/app/app.routes.ts`
- `intelligence/frontend/src/app/app.ts`
- `intelligence/frontend/nginx.conf`

### Spring backend

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PerformanceImportService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/ImportFileParser.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceImportController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/prediction/PredictionService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/prediction/PredictionEntity.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/prediction/PredictionRepository.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/prediction/api/PredictionController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/prediction/ml/MlPredictionClient.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/modelregistry/api/ModelRegistryController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/experiment/api/ExperimentController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/experiment/api/TestPlannerController.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`

### ML service

- `intelligence/ml-service/app/contracts.py`
- `intelligence/ml-service/app/main.py`
- `intelligence/ml-service/app/prediction.py`
- `intelligence/ml-service/app/feedback/README.md`
- `intelligence/ml-service/app/feedback/feedback_collector.py`
- `intelligence/ml-service/app/feedback/performance_analyzer.py`
- `intelligence/ml-service/app/feedback/rule_learner.py`

### Lab

- `lab/README.md`
- `lab/ARCHITECTURE.md`
- `lab/DATA_MODEL_V2.md`
- `lab/PERFORMANCE_IMPORT.md`
- `lab/PREDICTION_ARCHITECTURE.md`
- `lab/MODEL_EVALUATION.md`
- `lab/pompom_lab/spreadsheet_ingest.py`
- `lab/pompom_lab/trajectory.py`
- `lab/pompom_lab/prediction.py`
- `lab/pompom_lab/learning.py`
- `lab/pompom_lab/test_planner.py`
- `lab/pompom_lab/cli.py`
- `lab/migrations/003_experimentation_and_predictions.sql`
- `lab/migrations/004_performance_ingestion.sql`
- `lab/migrations/005_evaluation_and_calibration.sql`
- `lab/.lab_data/library.sqlite3`
- `lab/performance_imports/known_observations.csv`

### Creative Render service

- `intelligence/creative-render-service/src/main/java/com/pompom/creative/analytics/PerformancePrediction.java`
- `intelligence/creative-render-service/src/main/java/com/pompom/creative/analytics/PredictiveAnalyticsService.java`
- `intelligence/creative-render-service/src/main/java/com/pompom/creative/analytics/ABTest.java`
- `intelligence/creative-render-service/src/main/java/com/pompom/creative/analytics/ABTestingService.java`
- `intelligence/creative-render-service/src/main/resources/db/migration/V1__create_creative_render_schema.sql`
- `intelligence/creative-render-service/src/main/resources/application.yml`

### Schemas and documentation

- `intelligence/backend/src/main/resources/db/migration/V1__initial_schema.sql`
- `intelligence/backend/src/main/resources/db/migration/V24__create_analytics_tables.sql`
- `intelligence/docs/PERFORMANCE_IMPORT.md`
- `intelligence/docs/PREDICTION_MODEL.md`
- `intelligence/docs/MODEL_EVALUATION.md`
- `intelligence/docs/adr/ADR-005-immutable-predictions.md`
- `README.md`

---

## 12. Audit Boundary

No tests, training jobs, imports, predictions or database mutations were executed. The Lab SQLite
file was copied to `/tmp` and queried read-only to count and identify existing records. PostgreSQL
was not running, so this report distinguishes implementation capability from runtime data state.

