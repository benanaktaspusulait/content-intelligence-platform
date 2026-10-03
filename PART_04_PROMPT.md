You are working on the existing Pompom Hills Content Intelligence Platform.

Your task is to COMPLETE PART 03:

PERFORMANCE IMPORT
NORMALIZED TRAINING DATASETS
PREDICTION GENERATION
MULTI-HORIZON EVALUATION
MODEL TRAINING
TEMPORAL BACKTESTING
MODEL GOVERNANCE
RELIABILITY
LEARNING LOOP

Do not redesign the entire product.
Do not create another prediction subsystem.
Do not preserve competing production sources of truth.

Assume Part 01 and Part 02 have been completed or verify their required contracts before depending on them.

SOURCE OF TRUTH

Read and verify the repository against:

AUDIT_PART_03_IMPORT_PREDICTION_AND_LEARNING.md

Also respect the architecture established in Part 02:

- canonical video identity
- persisted variant identity
- exact publication identity
- normalized metric semantics
- reconciled observation sources
- canonical trajectory builder
- cutoff/as-of evidence access
- explicit provenance
- no fuzzy analytics attribution

Do not bypass Part 02 by querying raw mixed performance observations directly.

==================================================
PRIMARY ARCHITECTURAL DECISION
==================================================

Declare:

SPRING + POSTGRESQL = CANONICAL PRODUCTION SYSTEM OF RECORD

for:

- imports
- normalized evidence
- dataset snapshots
- model versions
- model evaluations
- predictions
- prediction targets
- prediction audits
- experiments
- human model promotion decisions

The standalone Lab is NOT a second production database.

The creative-render analytics schema is NOT a second prediction domain.

Useful Lab algorithms may be ported deliberately into the canonical Spring/ML architecture.

Do not synchronize three prediction databases indefinitely.

==================================================
PHASE 0 — INVENTORY AND MIGRATION BOUNDARY
==================================================

Before coding, inspect:

Main Spring/PostgreSQL:
- import_batches
- import_rows
- performance_observations
- predictions
- prediction_targets
- prediction_audits
- model_versions
- model_evaluations
- experiments
- experiment_variants
- human_predictions
- all related repositories/services/controllers

ML service:
- prediction.py
- training endpoints
- backtest/evaluation endpoints
- contracts
- feedback package
- model loading code
- feature extraction

Lab:
- spreadsheet_ingest.py
- trajectory.py
- prediction.py
- learning.py
- test_planner.py
- relevant migrations

Creative render:
- performance_predictions
- PredictiveAnalyticsService
- ab_tests
- ABTestingService

Produce a short architectural inventory:

1. Which prediction tables are actively written?
2. Which are legacy?
3. Which model registries exist?
4. Which experiment domains exist?
5. Which Lab algorithms are useful enough to port?
6. Which Lab records require migration, if any?
7. Which paths should be frozen immediately?
8. Which schema is canonical after this implementation?

Do not delete legacy data blindly.

==================================================
PHASE 1 — FREEZE COMPETING WRITE PATHS
==================================================

The repository currently contains multiple prediction domains.

Do not allow new production writes to:

- Lab SQLite prediction/model tables
- creative_render.performance_predictions
- creative_render.ab_tests
- legacy public.performance_predictions if it is not the selected canonical model

Mark inactive systems explicitly as LEGACY / READ_ONLY / DEPRECATED.

Do not expose the creative-render predictive analytics services to Angular.

The current render A/B implementation contains fabricated statistical certainty
such as fixed confidence/p-values.

It must not become production-visible.

==================================================
PHASE 2 — COMPLETE IMPORT INTAKE
==================================================

Preserve the strong existing import properties:

- immutable raw files
- hash deduplication
- raw row JSON
- null instead of invented zero
- exact/manual identity matching
- no fuzzy matching
- audited manual resolution
- unresolved rows block commit
- Reach Further provenance
- audience/country provenance

Fix the incomplete product flow.

A. FIELD MAPPING

The Angular mapping UI must affect backend normalization.

Either:
- persist reviewed mappings and apply them during commit,

or:
- remove operator-editable mapping controls.

Preferred implementation:
make the reviewed mapping real.

Persist:
- source column
- canonical target field
- transformation if any
- mapping confidence
- operator-reviewed flag

Do not display a mapping that the backend ignores.

B. SAMPLE VALUES

Preview responses should include real safe sample values from the imported file.

Do not show fake “From source file” placeholders.

C. ROW RESOLUTION

Expose the existing unresolved-row workflow in Angular.

The operator must be able to resolve:

- video
- exact variant
- publication where relevant

without direct API calls.

No fuzzy attribution.

D. PLATFORM

Allow canonical platform selection:

INSTAGRAM
FACEBOOK
TIKTOK
YOUTUBE

Use the same platform domain across frontend, Spring, ML and persistence.

E. TIMEZONE

Apply the stored import timezone when parsing naive timestamps.

Support:
- ISO
- OffsetDateTime
- common local date/time formats
- XLSX/Excel date values where existing parser capability allows

Persist:
- raw value
- parsed local value
- assumed timezone
- normalized UTC instant

Never silently drop a valid local timestamp because it lacks an explicit offset.

==================================================
PHASE 3 — CANONICAL NORMALIZED TRAINING EVIDENCE
==================================================

Do not train directly from raw performance_observations.

Consume the canonical normalized trajectory/evidence layer completed in Part 02.

Training input must exclude or separately classify:

- UNKNOWN metric semantics
- incompatible source streams
- ambiguous video/variant attribution
- invalid platform identity
- observations after the feature knowledge cutoff
- evidence that fails required provenance policy

Define explicit policy for:

- organic vs paid evidence
- manual interventions
- promoted/boosted posts
- Reach Further status
- missing metrics
- partial snapshots

Do not silently mix paid and organic examples.

==================================================
PHASE 4 — LABEL MATURITY / CENSORING
==================================================

This is required for multi-horizon learning.

A video that is only 3 hours old does NOT have a 24h result of zero.

For every prediction target/horizon define eligibility.

Example:

30m target:
eligible only after target measurement window has matured.

24h target:
eligible only when enough elapsed time/evidence exists according to the Part 02 checkpoint tolerance policy.

48h / 7d:
same principle.

Represent target states such as:

AVAILABLE
NOT_MATURED
MISSING_EVIDENCE
INCOMPATIBLE_EVIDENCE

Do not encode NOT_MATURED as zero.

Dataset generation must exclude immature labels from that horizon.

==================================================
PHASE 5 — VERSIONED DATASET SNAPSHOTS
==================================================

Implement one reproducible immutable dataset snapshot model.

Every training/backtest run must reference a dataset snapshot.

A snapshot should identify at minimum:

- dataset ID/version
- platform
- target metric(s)
- horizon(s)
- creation timestamp
- knowledge cutoff policy
- feature schema version
- normalization policy version
- source reconciliation policy version
- inclusion/exclusion policy
- row count
- canonical video IDs
- variant IDs
- publication identities where used
- row-level evidence provenance
- label maturity state

Persist enough information to rebuild or audit the dataset.

Do not use a human-readable dataset version string as the only lineage.

==================================================
PHASE 6 — FEATURE SNAPSHOTS
==================================================

Predictions must use immutable feature snapshots.

For every prediction persist the exact input features used.

A feature snapshot must be cutoff-safe.

Include provenance such as:

- videoId
- variantId
- platform
- publication identity
- creative fingerprint version
- normalized performance checkpoint IDs
- audience/discovery evidence IDs
- Reach Further evidence IDs
- feature extractor/schema version
- knowledge cutoff

Do not later recompute the prediction from current/latest state and pretend it is the original input.

==================================================
PHASE 7 — KNOWLEDGE CUTOFF SAFETY
==================================================

This is correctness-critical.

Every feature used for a live or historical prediction must satisfy:

feature.observedAt <= knowledgeCutoff

or equivalent version creation time where appropriate.

Apply the same cutoff to:

- creative fingerprint
- platform-state evidence
- performance observations
- Reach Further state
- publication context
- audience/discovery features
- interventions

Do not call a helper that internally reads “latest” without a cutoff.

Reject:
- null cutoff when required
- future cutoff
- invalid cutoff before publication where incompatible with prediction type

Persist exact feature provenance.

Add tests specifically designed to catch future leakage.

==================================================
PHASE 8 — TRAINING-SERVING PARITY
==================================================

Training and inference must use the same feature definition.

Do not create:

trainingFeatureExtractor
and
productionFeatureExtractor

with independent behavior.

Use one versioned feature schema / extraction pipeline.

Persist:
- featureSchemaVersion
- preprocessingVersion

A model may only serve predictions using a compatible feature schema.

If incompatible:
fail clearly.

==================================================
PHASE 9 — IMPLEMENT REAL TRAINING
==================================================

Replace the current training stub.

The training endpoint must:

1. select/build a canonical dataset snapshot;
2. validate minimum eligible sample requirements;
3. construct features/labels;
4. train a real model or empirical baseline according to the registered model family;
5. compute training metadata;
6. serialize an artifact;
7. compute artifact hash;
8. register a CHALLENGER model version;
9. link it to:
    - dataset snapshot
    - feature schema
    - training code/model family version
    - artifact path/hash
10. preserve metrics/provenance.

Do not return CHALLENGER_CREATED if no model artifact exists.

Initial model complexity should be proportional to available data.

Do not overfit a tiny dataset with unnecessary complexity.

An empirical median/quantile model is acceptable as a real baseline if implemented honestly.

==================================================
PHASE 10 — BASELINES
==================================================

Maintain explicit baseline models.

At minimum support comparison against:

- cold-start/no-data baseline
- simple platform median baseline where enough data exists

Do not promote a challenger merely because it trained successfully.

A challenger must demonstrate benefit over configured baselines.

Cold-start behavior must remain honest:

if there is insufficient training evidence,
return null/low-confidence predictions rather than fabricated expected views.

==================================================
PHASE 11 — TEMPORAL BACKTESTING
==================================================

Replace the backtest stub with real temporal evaluation.

Do NOT use random train/test splits for time-dependent social performance.

Use expanding-window or other explicitly approved temporal splits.

Example:

train on oldest period
validate on later unseen period
advance window
repeat

Never let a future video influence a historical prediction.

Persist evaluation splits and cutoff boundaries.

For each model evaluate applicable targets/horizons.

Potential metrics should be selected according to target type.

For numeric view targets consider:
- MAE
- median absolute error
- log-scale error where appropriate
- interval coverage
- quantile loss if quantiles are predicted

For probability outputs consider:
- Brier score
- calibration error
- reliability bins

Do not calculate meaningless percentage errors when actual values can be zero/small without explicit policy.

==================================================
PHASE 12 — MODEL EVALUATIONS
==================================================

Persist real model_evaluations.

Every evaluation must identify:

- modelVersion
- datasetSnapshot
- split strategy/version
- evaluation period
- sample size
- target metric
- horizon
- baseline metrics
- challenger metrics
- calibration metrics where applicable
- promotion eligibility decision
- reasons

Do not store promotionEligible=true without supporting evaluation evidence.

==================================================
PHASE 13 — MODEL ARTIFACT IDENTITY
==================================================

Every registered learned model must reference an actual immutable artifact.

Persist:

- artifact location
- cryptographic hash
- model family
- model implementation/version
- feature schema version
- training dataset ID
- createdAt

Before inference:
verify artifact availability and identity.

Before promotion:
verify artifact/hash.

Do not allow an empty registry row to become champion.

==================================================
PHASE 14 — MODEL GOVERNANCE / PROMOTION
==================================================

Promotion must remain HUMAN and AUDITED.

But human approval is necessary, not sufficient.

Backend promotion transaction must verify configured gates.

Example gates:

- CHALLENGER status
- artifact exists and hash matches
- minimum eligible sample size
- temporal backtest completed
- required horizons evaluated
- reliability/calibration requirements satisfied where applicable
- challenger meets configured baseline/champion comparison rules
- feature schema compatible
- no critical validation failure

Thresholds must come from model/promotion policy configuration,
not frontend constants.

Do not hardcode `n < 80` in Angular.

Store:
- approver
- timestamp
- evaluation IDs
- promotion reason
- previous champion ID

Allow explicit rollback.

Enforce:
for a given platform + model family/type,
at most one active champion.

Promotion/demotion must be transactional.

==================================================
PHASE 15 — CHAMPION MUST DRIVE INFERENCE
==================================================

Currently registry promotion does not affect predictions.

Fix this.

Prediction generation must:

1. determine prediction type/platform;
2. resolve active champion model;
3. verify compatible feature schema;
4. load verified artifact;
5. use exact feature snapshot;
6. generate targets;
7. persist modelVersion/modelId;
8. persist dataset/model provenance.

If no eligible champion exists:

use explicit cold-start/baseline policy.

Do not silently use an arbitrary registered model.

==================================================
PHASE 16 — PREDICTION TARGET REPRESENTATION
==================================================

Inspect the existing dual representation:

- prediction payload JSON
- prediction_targets table

Choose one canonical representation.

Do not maintain two independently writable versions.

If prediction_targets already provides the intended normalized immutable model,
prefer using it and derive API payloads from it.

If schema constraints make payload canonical,
explicitly deprecate the unused target table.

Do not leave two contradictory sources of truth.

Each target must identify:

- metric
- horizon
- expected value where available
- interval/quantiles where available
- probabilities where applicable
- availability
- confidence/reliability state

==================================================
PHASE 17 — MULTI-HORIZON PREDICTION LIFECYCLE
==================================================

One prediction can contain several horizons.

Do not mark the whole prediction EVALUATED after one horizon.

Implement target-level evaluation state.

Example:

prediction:
LOCKED

targets:
30m = EVALUATED
1h = EVALUATED
2h = READY_TO_EVALUATE
6h = NOT_MATURED
24h = NOT_MATURED

Prediction aggregate state may be:

LOCKED
PARTIALLY_EVALUATED
EVALUATED

depending on policy.

Do not mutate the original prediction values.

==================================================
PHASE 18 — AUTOMATIC PREDICTION AUDIT
==================================================

Do not require manually typed actual values as the primary evaluation path.

Actual values must come from canonical persisted normalized observations/trajectories.

For each eligible horizon:

- locate the correct cutoff-safe actual checkpoint
- identify observation/source/variant/publication
- apply Part 02 checkpoint tolerance policy
- create immutable prediction audit

Persist:

- prediction target ID
- actual value
- actual observation/checkpoint ID
- actual measurement timestamp
- source provenance
- error
- interval coverage
- band correctness
- probability score where applicable
- trajectory-class correctness where applicable

If actual evidence is unavailable:
do not fabricate an audit.

==================================================
PHASE 19 — RELIABILITY AND CALIBRATION
==================================================

Port/adapt the useful Lab reliability logic into the canonical production architecture.

Do not read Lab SQLite at runtime.

Build reliability from persisted prediction audits.

Provide summaries by useful dimensions such as:

- model version
- platform
- target
- horizon
- time window

Display:
- sample size
- error metrics
- interval coverage
- calibration/reliability where meaningful

Do not report precise confidence with insufficient sample size.

Small-sample warnings must come from backend/model policy.

==================================================
PHASE 20 — PREDICTION UI
==================================================

Fix the current semantic defects.

Do not label view forecasts as:

Expected completion %

If the target metric is views, display views.

Every visible target must show:

- metric
- horizon
- expected value
- interval
- confidence/reliability state
- model
- dataset/version
- cutoff
- variant identity

Implement:

- New Prediction
- prediction detail
- pre-publish prediction
- live prediction where supported
- lock action
- evaluation state
- target audit details
- provenance view

The list must show meaningful video/variant identity,
not raw UUID as the user-facing name.

==================================================
PHASE 21 — PLATFORM CONSISTENCY
==================================================

Use one canonical platform domain across:

- Angular
- Spring
- ML
- PostgreSQL

Support policy must explicitly state:

INSTAGRAM
FACEBOOK
TIKTOK
YOUTUBE

If a model family does not yet support one platform:

return explicit unsupported/no-model state.

Do not let frontend offer a platform that ML rejects unexpectedly.

Do not permit typo partitions like `facebok`.

==================================================
PHASE 22 — EXPERIMENTS AND TEST PLANNER
==================================================

The backend already contains experiment/test-planner functionality.

Connect existing functionality only after verifying it is real.

Do not fabricate significance or statistical certainty.

Experiments must use exact:

- creative
- variant
- publication
- metric
- observation

identity from Part 02.

Do not revive the creative-render fake A/B statistics.

If existing experiment code cannot produce valid statistical evidence,
show it as planning/tracking only until implemented correctly.

==================================================
PHASE 23 — HUMAN BLIND PREDICTIONS
==================================================

The Lab contains human prediction concepts.

Do not make them part of model training automatically.

If the existing schema/workflow is retained:

- human predictions must be immutable once locked
- kept separate from machine predictions
- evaluated against the same actual evidence
- usable as a comparison baseline

This feature may be deferred if there is no active product requirement.

Do not block the core learning loop on it.

==================================================
PHASE 24 — FEEDBACK / RULE LEARNING BOUNDARY
==================================================

The ml-service feedback package is currently an in-memory prototype.

Do not treat it as production persistence.

The canonical learning loop in this task is:

PERFORMANCE EVIDENCE
-> NORMALIZED TRAJECTORY
-> DATASET SNAPSHOT
-> MODEL TRAINING
-> TEMPORAL EVALUATION
-> HUMAN PROMOTION
-> CHAMPION INFERENCE
-> IMMUTABLE PREDICTION
-> PREDICTION AUDIT
-> RELIABILITY

Rule-learning for creative quality rules is a separate governed process.

Do not auto-modify Part 01 quality rules from performance data.

At most produce rule-candidate evidence for human review in a later task.

==================================================
PHASE 25 — REPRODUCIBILITY
==================================================

Every learned model must be reproducible/auditable.

Persist where relevant:

- dataset snapshot ID/hash
- feature schema version
- normalization policy version
- source reconciliation policy version
- model code/family version
- training configuration
- random seed if algorithm uses randomness
- artifact hash
- training timestamp
- evaluation IDs

Given a modelVersion,
an engineer must be able to identify exactly what data and feature definitions produced it.

==================================================
PHASE 26 — DATA LEAKAGE TESTS
==================================================

Add explicit tests designed to detect future leakage.

Example:

Prediction cutoff:
2026-09-01 12:00

Evidence:
11:00 -> allowed
11:59 -> allowed
12:01 -> forbidden
later Reach Further state -> forbidden
fingerprint created after 12:00 -> forbidden
publication correction after 12:00 -> forbidden

The feature snapshot must prove that no post-cutoff evidence was used.

==================================================
PHASE 27 — TRAINING DATA EXCLUSIONS
==================================================

Define explicit reason codes for rows/examples excluded from a training target.

Examples:

IMMATURE_TARGET
MISSING_VARIANT_ID
AMBIGUOUS_PUBLICATION
UNKNOWN_METRIC_SEMANTICS
INCOMPATIBLE_SOURCE
PAID_EVIDENCE_EXCLUDED
INTERVENED_EVIDENCE_EXCLUDED
MISSING_REQUIRED_FEATURE
POST_CUTOFF_EVIDENCE
PLATFORM_UNSUPPORTED

Do not silently drop examples.

Dataset reports should show exclusion counts/reasons.

==================================================
PHASE 28 — MODEL DRIFT / CHAMPION HEALTH
==================================================

Do not automatically retrain or promote based on drift.

But expose enough production reliability data to answer:

- is champion error worsening?
- is calibration degrading?
- is current data distribution materially different?
- is sample size sufficient?

A future scheduler may create a challenger candidate,
but promotion remains human.

Keep monitoring descriptive and auditable.

==================================================
PHASE 29 — COLD START POLICY
==================================================

Cold start must remain honest.

When evidence is insufficient:

Allowed:
- expectedValue = null
- low confidence
- explicit baseline/no-data state
- broad empirical interval when legitimately supported

Not allowed:
- invented exact view counts
- arbitrary quality multipliers
- fabricated confidence
- fake p-values

Preserve the current honesty principle.

==================================================
PHASE 30 — TESTS
==================================================

The audit did not run tests.

Completion requires automated evidence.

Add unit/integration/contract tests covering at minimum:

IMPORT

1. reviewed field mapping is actually used by backend commit
2. real sample values appear in preview
3. unresolved rows can be manually matched
4. unresolved rows block commit
5. platform selection is persisted
6. naive timestamp uses supplied timezone
7. raw timestamp and UTC normalization are preserved
8. null metrics stay null

DATASET

9. dataset snapshot is immutable/versioned
10. row provenance is reproducible
11. immature 24h target is excluded, not zero
12. incompatible evidence is excluded with reason
13. paid/intervened evidence follows explicit policy
14. variant identity is retained

CUTOFF

15. no feature after knowledgeCutoff is included
16. future fingerprint is excluded
17. future Reach Further state is excluded
18. future publication corrections are excluded
19. invalid/future cutoff is rejected

TRAINING

20. training with insufficient eligible data does not create fake challenger
21. successful training produces real artifact
22. artifact hash is persisted
23. challenger references dataset snapshot
24. feature schema version is persisted

BACKTEST

25. temporal split never trains on future samples
26. real evaluation metrics are persisted
27. baseline metrics are persisted
28. promotion eligibility is derived from policy/evidence

PROMOTION

29. unevaluated challenger cannot be promoted
30. missing artifact cannot be promoted
31. bad artifact hash cannot be promoted
32. failed gate cannot be bypassed by controller call
33. human approval is recorded
34. exactly one champion exists per model scope
35. rollback restores prior valid champion

INFERENCE

36. prediction loads active champion artifact
37. promoted champion changes inference path
38. incompatible feature schema blocks inference
39. no champion triggers explicit cold-start policy

PREDICTION

40. exact video variant is persisted
41. exact knowledge cutoff is persisted
42. feature snapshot is immutable
43. target units/horizons are correct

EVALUATION

44. evaluating 30m does not mark 24h evaluated
45. all horizons can be audited independently
46. actual value comes from persisted canonical observation
47. audit preserves source/observation identity
48. partial evaluation state works
49. interval coverage calculation is correct
50. probability scoring is calculated only when applicable

UI

51. view target is never shown as completion %
52. prediction list shows human-readable video/variant identity
53. placeholder routes are replaced only by working API-backed pages
54. unsupported actions are not shown as functional

LEGACY

55. render fake A/B analytics cannot become production prediction source
56. Lab SQLite is not written by production workflow
57. canonical Spring/PostgreSQL path owns prediction writes

==================================================
PHASE 31 — PRODUCT SURFACES
==================================================

Complete the existing Angular surfaces:

IMPORT DATA
- platform selection
- real mapping
- sample values
- row resolution
- batch status
- duplicate batch state

PREDICTIONS
- generate
- detail
- targets
- lock
- live prediction
- evaluation progress
- provenance

MODEL VERSIONS
- champion/challenger
- artifact identity
- evaluation summary
- promotion gates
- audited promote/rollback

MODEL RELIABILITY
- real audit-based metrics
- horizon/model/platform breakdown
- sample size warnings

EXPERIMENTS / TEST PLANNER
- connect real existing backend functionality
- no fabricated statistical certainty

Do not replace PlaceholderPage with another visual-only shell.

==================================================
PHASE 32 — DOCUMENTATION
==================================================

Create:

docs/PART_03_LEARNING_LOOP_COMPLETION.md

Document:

- canonical source of truth
- legacy systems frozen
- import normalization
- dataset snapshot model
- feature schema/versioning
- cutoff safety
- target maturity
- training pipeline
- model artifact format/identity
- temporal backtest
- promotion gates
- champion inference
- cold-start policy
- prediction lifecycle
- multi-horizon audit lifecycle
- reliability/calibration
- product UI
- deferred features
- migration notes

Update README claims.

Do not call the learning engine “production ready”
unless the full canonical loop and tests pass.

==================================================
FINAL DEFINITION OF DONE
==================================================

Part 03 is complete only when:

- Spring/PostgreSQL is the single canonical production evidence/model/prediction store
- legacy Lab/render write paths are frozen or migrated
- import mappings shown in UI are actually used
- unresolved rows can be resolved in Angular
- timezone normalization works
- platform identity is consistent
- Part 02 normalized trajectories feed dataset construction
- immature horizon labels are never encoded as zero
- versioned reproducible datasets exist
- every training example has provenance
- training creates a real artifact
- backtesting executes real temporal evaluation
- model evaluations are persisted
- promotion gates are enforced by backend
- artifact existence/hash is verified
- one champion exists per model scope
- promoted champion is actually used for inference
- predictions are fully cutoff-safe
- predictions identify exact variant
- immutable feature snapshot is persisted
- all horizons can be audited independently
- actual values come from persisted canonical evidence
- prediction UI shows correct metric and units
- reliability is derived from prediction audits
- cold-start predictions remain honest
- no fabricated statistical confidence remains in active product paths
- all automated tests pass
- documentation matches reality

Before coding, report any contradiction between this specification and the actual repository.

Prefer porting proven Lab algorithms into the canonical architecture over maintaining parallel databases.

Correctness, provenance, cutoff safety and reproducibility are more important than model sophistication.