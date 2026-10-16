# POMPOM HILLS — REAL A AND A+ CAPABILITY VERIFICATION

This report records the bounded, no-spend verification run for the autonomous Story → Prompt → First Frame path. It does not convert fixture evidence into production evidence and does not claim that a real model has produced an A or A+ prompt.

DISPOSABLE_BACKEND_HTTP: FAILED
ISOLATED_OWNER_LOGIN: FAILED
ISOLATED_PROVIDER_TRANSPORT: VERIFIED

NEW_STORY_CREATED: FAILED
NEW_PROMPT_CREATED: FAILED
NEW_ANALYSIS_CREATED: FAILED

AUTONOMOUS_OPTIMIZATION_EXECUTED: NO

BASELINE_SCORE: 88.40625
ROUND_1_SCORE: NOT_EXECUTED
ROUND_2_SCORE: NOT_EXECUTED
BEST_SCORE: NOT_EVALUATED
BEST_GRADE: NOT_EVALUATED

CANONICAL_A_THRESHOLD: 92
ISOLATED_CANONICAL_A_REACHED: NOT_EVALUATED

REAL_PROVIDER_A_GENERATION:
NOT_VERIFIED

REAL_PROVIDER_A_REPEATABILITY:
NOT_VERIFIED

OFFICIAL_A_PLUS_CONTRACT:
INACTIVE

A_PLUS_CALIBRATION:
PROPOSED

CREATIVE_A_PLUS_CAPABILITY:
NOT_VERIFIED

FIRST_FRAME_GENERATION:
MOCK_ONLY

FIRST_FRAME_VISUAL_QA:
NOT_EXECUTED

REAL_PROVIDER_CALLS: 0
REAL_IMAGE_CALLS: 0
REAL_VIDEO_CALLS: 0

PRODUCTION_TEST_RECORDS: 0
RENDER_AUTHORIZED: false

## Evidence actually executed

`./intelligence/scripts/acceptance-story-firstframe.sh` completed with exit code 0. The run used a disposable internal-only network, disposable PostgreSQL/Testcontainers and the repository's real parser, validator and Ruleset 1.11 test paths. The loopback FastAPI fixture was called through the real `/api/v1/workflow/creative-role` HTTP route and returned `provider=ISOLATED_FIXTURE`, `providerDispatched=false`, `calls=0` and `actualCostUsd=0.0`. The fixture transport is guarded by `POMPOM_ISOLATED_ACCEPTANCE`, a temporary fixture directory and a per-run token; those settings are not enabled by production compose.

The run passed the focused ML contract suite (35 tests, including fixture transport and first-frame contracts), the focused fixture transport tests (2 tests), and the backend Spring/Testcontainers/Flyway tests. `CpqOwnerAccessTest` passed separately, covering fail-closed credentials, rate limiting, owner session creation, CSRF/origin, logout and remote HTTP rejection. These tests prove the components and contracts; they do not constitute a running authenticated disposable backend workflow.

## The remaining concrete blocker

The harness does not start a separate Spring HTTP server with a temporary owner credential, a temporary database reachable by an external HTTP client and the fixture ML base URL. Therefore it cannot perform the required cookie/CSRF owner login, business-service content/story creation, story approval, BUILD_PROMPT handoff, immutable prompt persistence, REVIEW analysis persistence and autonomous optimization rounds over HTTP. Direct SQL seeding was not used to hide this missing path. No production owner credential or production database was read or changed.

The immutable production control is unchanged: analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, content `10`, prompt `10`, Ruleset 1.11, `88.40625/B`, with canonical A threshold `92`; render authorization remains false.

## Answers to the required capability questions

### 1. Can the application autonomously produce and evaluate a new prompt?

The production business services contain the Story Evolution, BUILD_PROMPT, source-fidelity, canonical evaluation and optimization-loop path. The no-egress fixture transport and deterministic tests exercise the contracts. The complete authenticated HTTP path was not executed in this run, so autonomous production-like execution is **not verified**.

### 2. Did a new prompt reach canonical A?

No new prompt or analysis was persisted. The only actual score available is the immutable baseline `88.40625/B`. A score of `92` or higher was not evaluated in isolation.

### 3. Did a real AI provider produce an A prompt?

No. `REAL_PROVIDER_CALLS` is zero and provider dispatch is disabled. There is no real-provider A generation evidence.

### 4. Is real-provider repeatability demonstrated?

No. Repeatability requires at least the separately authorized real generation protocol and immutable comparison evidence. No such call occurred.

### 5. Is there an approved, calibrated A+ contract?

No. The existing CPQ implementation reports `CPQ_GRADING: INACTIVE` and `CALIBRATION_INCOMPLETE`. `CPQ_A_PLUS` is explicitly unsupported by the optimization capability response. The available CPQ dimensions are `SCROLL_STOP_VISUAL_PROMISE`, `CAUSAL_PROGRESSION`, `VISUAL_STORYTELLING`, `PRODUCTION_EXECUTABILITY`, `ENDING_REPLAY` and `DISTINCTIVE_CREATIVE_VALUE`; they are suitable calibration dimensions for a future proposal, not an active grade.

### 6. Did the prompt meet A+?

Not evaluated. Text differences, canonical B scores, fixture responses or a higher heuristic signal cannot establish A+ without an approved corpus, calibrated thresholds, held-out error analysis, independent agreement and source/visual evidence.

### 7. Does a first frame support quality?

Only the mocked contract is verified: deterministic tests produce decodable first-frame bytes. No newly persisted Mimi first-frame candidate, owner approval, visual QA record or production image exists. Visual quality is therefore not verified.

## A+ calibration proposal (inactive)

If the owner later authorizes calibration work, retain the existing six CPQ dimensions and create a versioned, held-out corpus of source-bound original/improved pairs. Each example needs exact prompt/story/settings fingerprints, independent source-fidelity evidence, two independently executed `MACHINE_REVIEW` packets (never relabelled as human review), reviewer agreement, leakage-group separation and an explicit activation record. Thresholds and aggregation must be frozen only after held-out error analysis. Until that record is approved, every A+ result remains `NOT_QUALIFIED` and `OFFICIAL_A_PLUS_UNAVAILABLE`.

## Bounded next experiment, requiring separate authorization

The next real experiment must first complete the missing disposable Spring HTTP acceptance path, then run one explicitly authorized provider generation under the existing budget/idempotency gate. It must bind the exact Mimi prompt/story/settings, capture the model's structured decision separately from compiler output, run source/canonical/critic gates, persist immutable evidence only in the disposable or explicitly authorized scope, and stop before prompt approval, rendering or publishing. No provider, image or video call is authorized by this report.

## Integrity and limits

No story, Prompt 10, Ruleset 1.11 semantics, score, historical analysis or CPQ activation was changed. No real provider, image, video, render, publish, commit or push occurred. The honest classification is implementation readiness for the fixture contracts with the full isolated HTTP acceptance still incomplete; it is not proof of autonomous creative A/A+ generation.

**STATUS: REAL_A_AND_A_PLUS_CAPABILITY_NOT_VERIFIED**

## Subsequent P0 HTTP checkpoint — 2026-10-16

The disposable Spring HTTP + authenticated owner + approved source milestone subsequently passed. See [DISPOSABLE_OWNER_HTTP_ACCEPTANCE.md](DISPOSABLE_OWNER_HTTP_ACCEPTANCE.md) and its actual HTTP evidence. The statuses above describe the earlier run; they are preserved rather than rewritten. This P0 success does not establish autonomous A/A+ generation or the full first-frame workflow.
