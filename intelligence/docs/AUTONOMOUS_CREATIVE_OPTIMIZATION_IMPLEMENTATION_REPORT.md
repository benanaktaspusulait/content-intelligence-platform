# Autonomous Creative Optimization V1 — Implementation Report

## Operator answer

**Can I now start optimization from Step 6 and let it continue without manually editing/reanalyzing each candidate?**

**PARTIALLY.** The bounded multi-round loop, persistence model, actual Ruleset 1.11 evaluation path, cancellation and ambiguous-dispatch handling are deployed and ready for an explicitly authorized run. The local `benan` owner profile is mounted and configured, but no browser owner session or production run was created in this verification. Real provider dispatch remains disabled (`CPQ_PILOT_REAL_ENABLED=false`) and CPQ grading remains inactive. Therefore Step 6 is ready to inspect and preflight, but a real autonomous optimization run cannot start until an authenticated session and a separate operator grant are present.

## Delivered implementation

- Added the worklist at `intelligence/docs/AUTONOMOUS_CREATIVE_OPTIMIZATION_WORKLIST.md`.
- Added the ML loop helper in `intelligence/ml-service/app/workflow/optimization_loop.py`. It calls the existing Ruleset 1.11 evaluator, performs source-fidelity and integrity checks, distinguishes parser/evidence artifacts from real score changes, and compiles one bounded candidate per round.
- Added read-only local ML operations and an HMAC-protected dispatch operation in `intelligence/ml-service/app/workflow/api.py`. The dispatch endpoint refuses calls while the real flag is false.
- Added durable V68 run/request/draft/event tables and immutability triggers in `intelligence/backend/src/main/resources/db/migration/V68__bounded_optimization_runs.sql`.
- Added `OptimizationLoopService` and `OptimizationLoopController`. The worker owns the loop: baseline evaluation, generation, independent source-fidelity review, critic review, comparison, retention, stop conditions, cancellation and resume. The browser does not own the loop.
- Added explicit grant binding: owner, analysis/prompt/ruleset/profile, model and reasoning, token and USD limits, max rounds/requests/time, no-retry policy, source authority and idempotency key are persisted and hashed before work begins.
- Added a separate final acceptance command. It requires an exact draft fingerprint, retained candidate, independent source support, compiler approval and explicit owner consent. It never authorizes render, changes the canonical score, or activates CPQ grading.
- Added the Step 6 `OptimizationLoopComponent` and mounted it in the owner pilot. It supports baseline selection, bounded preflight, explicit consent, start/stop/reconnect and progress/evidence display. CPQ A/A+ is shown as unavailable because no active calibrated contract exists.

## Safety and routing

The deployed capability response reports:

- target `CANONICAL_RULESET_1_11_A`: supported, minimum score 92;
- target `CPQ_A_PLUS`: unsupported because no approved active calibrated contract exists;
- DeepSeek and OpenAI profiles with fixed role/model/token/cost contracts;
- maximum five rounds, fifteen requests, USD 20 and 1,800 seconds;
- official CPQ grading `INACTIVE`, render `false`, real dispatch `false`.

Generation, source-fidelity and critic calls must use the configured role/profile contracts. Source and critic profiles must differ from every generator profile. A timeout, network ambiguity or cancellation never replays an unknown request. A failed candidate is retained as evidence and cannot be silently promoted.

## Mimi regression handling

The loop treats the saved Mimi traces as evidence rather than as creative progress:

- original prompt: Ruleset 1.11 `88.40625 / B`, two attempts;
- V2: `80.25520833333334 / B`, zero parsed attempts and `EVALUATOR_UNRELIABLE` integrity evidence;
- V3: `88.40625 / B`, two attempts.

The V2 parser/evidence failure cannot be counted as an improvement. Protected story text, source beats, identity, physical rule and ending remain immutable inputs to every candidate.

## Verification evidence

- ML regression and optimization-loop suite: **152 passed**, 1,958 warnings, no failures; real provider environment variables were removed and `CPQ_PILOT_REAL_ENABLED=false`.
- Backend `OptimizationLoopTest`: **11 passed, 0 failures, 0 errors**. The disposable Testcontainers database exercised multi-round progression, idempotency, authorization and inactive targets, cancellation, ambiguous accounting, request/budget/time limits, equivalent-plan rejection and binding immutability through the Python mock bridge and actual evaluator/compiler path.
- Frontend focused tests: **18 passed** across the optimization-loop and owner-pilot specs. They cover no automatic POST, inactive target handling, bounded start payload/CSRF, reconnect, stop uncertainty and consent invalidation.
- Backend health: **UP**. Flyway migration `68` is applied. `optimization_runs` is empty in the production database because no run was started.
- Deployed backend image: `sha256:b51367255e8543a9aa524059de7cd5673a8f3b67e3b293375a78b0974e2143b4`.
- Deployed ML image: `sha256:bcf5371af5d92639474980639ae3ee4a89c016fed279164e09bb4eb1687ebff5`.
- Deployed frontend image: `sha256:8616ecf5e35557677318e79d7382305baca66f51596bbed3bc76dd94d76f8be3`.
- Live capability endpoint returned the bounded contract and `realDispatchEnabled:false`.
- Pre-deployment protected-table digests and the V68 database backup were created before deployment. No prompt version, saved analysis, owner-pilot evidence, policy state or historical record was changed.

## UI and real-provider boundary

The frontend build and container health check passed. The deployed Chrome tab was reconnected and the Step 6 panel was inspected. The owner login control is visible, but no credential was entered in this verification, so a real click-through of Start/Stop was not claimed as passed. No POST start request was sent from the browser, and no provider request was dispatched. This is an authentication boundary, not evidence of a UI failure.

The isolated tests prove implementation readiness with mock transport and real local evaluation. They do not prove that a real model will create an A candidate. No real provider optimization, prompt approval, render authorization or CPQ grade activation was performed.

## Status

| Area | Status |
|---|---|
| UI-driven bounded loop deployed | **VERIFIED (build/health; click-through pending browser bridge)** |
| Multi-round actual evaluator path | **VERIFIED** |
| Single bounded authorization and idempotency | **VERIFIED** |
| Mimi regression/evaluator-integrity handling | **VERIFIED** |
| Real provider optimization | **NOT EXECUTED** |
| Genuine A-producing acceptance | **NOT VERIFIED** |
| CPQ grading | **INACTIVE** |
| Render authorization | **false** |

The next permitted step is an explicitly authorized operator grant followed by one controlled real run. Until that grant is present, the correct Step 6 state is preflight-ready, not production-running.
