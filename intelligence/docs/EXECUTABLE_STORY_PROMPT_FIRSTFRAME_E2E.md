ISOLATED_OWNER_AUTH: FAILED
RUNNING_ML_HTTP_FIXTURES: VERIFIED
NO_EGRESS: VERIFIED

STORY_EVOLUTION_HTTP: FAILED
STORY_APPROVAL_HTTP: FAILED
BUILD_PROMPT_HTTP: FAILED

NEW_PROMPT_PERSISTED: FAILED
NEW_ANALYSIS_PERSISTED: FAILED
RULESET_1_11_EVALUATED: VERIFIED

AUTONOMOUS_OPTIMIZER: BLOCKED
BEST_CANONICAL_SCORE: 88.40625/B
CANONICAL_A_REACHED_IN_ISOLATION: NOT_EVALUATED
REAL_PROVIDER_A_VERIFIED: NO

FIRST_FRAME_HTTP: FAILED
FIRST_FRAME_ASSET_PERSISTED: FAILED
FIRST_FRAME_VISUAL_QA: MOCK_CONTRACT_ONLY
FIRST_FRAME_OWNER_APPROVAL: FAILED

STEP_7_READY: NO
RENDER_AUTHORIZED: false

BROWSER_E2E: FAILED

REAL_PROVIDER_CALLS: 0
REAL_IMAGE_CALLS: 0
REAL_VIDEO_CALLS: 0
PRODUCTION_TEST_RECORDS: 0

FULL_ISOLATED_E2E: PARTIAL

# Executable acceptance evidence

## Harness and command

The repeatable command is:

```text
./intelligence/scripts/acceptance-story-firstframe.sh
```

It creates a disposable Docker internal-only network, runs the ML contract suite with the repository virtualenv, runs backend Spring/Testcontainers tests against disposable PostgreSQL, emits a JSON result, and removes the network and temporary result directory on exit. It never reads the production owner credential, never sets `CPQ_PILOT_REAL_ENABLED=true`, and never starts a production provider or image request.

The first run exposed a missing `PYTHONPATH`; the harness was corrected to use the ML virtualenv and the repository `data` directory. The current run passed **35 ML tests** (including fixture transport fail-closed tests). It also started the real FastAPI HTTP service on loopback and successfully called `/api/v1/workflow/creative-role`, receiving a complete `ISOLATED_FIXTURE` STORY response with `providerDispatched=false`. The backend command exited successfully and Flyway applied all 67 migrations (schema v69) inside disposable PostgreSQL. The JVM emitted scheduled-task connection warnings while Testcontainers rotated its database, but the Maven command completed with exit code 0.

## What is verified

- Disposable PostgreSQL and actual Flyway migrations are exercised by the Spring test context.
- The real Python parser/rule/evaluator code is exercised; no score is copied from a fixture. Existing deterministic tests cover story review contracts, optimization transport boundaries, start-frame PNG bytes, candidate lifecycle and rejection/acceptance rules.
- The existing backend integration tests exercise prompt provenance, story approval checks, character-reference storage and workflow persistence authorities.
- No provider, GPT-Image-2 or video-render request was made. The internal Docker network is marked `--internal`; the test command has no provider credentials and the result reports zero real calls.
- The production database and owner configuration were not mounted or mutated.

The fixture implementation is guarded by `POMPOM_ISOLATED_ACCEPTANCE=true`, a disposable fixture directory and a 32-character fixture token. It is disabled in the production compose configuration. Missing or malformed fixture files fail before any SDK/provider client is constructed. The HTTP response was validated by the normal STORY parser and included zero calls and zero cost.

## Why the full HTTP chain remains failed

The repository does not currently expose a supported disposable provider-fixture adapter for the running ML HTTP service. `creative-role` still requires the normal paid-role configuration and adaptive HMAC boundary. Enabling `CPQ_PILOT_REAL_ENABLED` would only open the application gate; it would not safely supply STORY, STORY_REVIEW or BUILD_PROMPT responses and could create an accidental paid-dispatch path. I did not weaken that boundary.

There is also no supported API for creating a complete disposable source analysis and approved story without either an authenticated owner session or direct seed SQL. The acceptance task explicitly forbids using direct SQL to skip business validation. Consequently no HTTP story run, owner login, new prompt version, new REVIEW analysis, persisted quality validation, optimizer round, image candidate or owner image approval was fabricated.

The production control remains unchanged and was re-read before this task: analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, content `10`, prompt `10`, Ruleset 1.11 `88.40625/B`, target `92/A`, and render authorization `false`.

## First-frame result

`tests/test_start_frame_generation.py` proves the existing first-frame contract with a mocked provider and real decodable PNG bytes at the test boundary. It does not prove that a newly persisted story/prompt can reach `/start-frame/generate` through a running browser session. No production Mimi image was substituted, and no test asset was persisted through the live application for this run, so the required image ID, candidate SHA, visual QA record and owner approval do not exist.

## Exact next engineering action

Add a test-only, deployment-profile-gated ML transport adapter that is reachable only when all of the following are true: an explicit disposable profile, a fixture directory outside production storage, a no-egress network, and a signed per-run fixture token. The adapter must return complete STORY, STORY_REVIEW and BUILD_PROMPT contracts and a mock GPT-Image-2 byte response; the backend must keep the existing owner authentication, persistence authorities, Ruleset 1.11 evaluator and render gates unchanged. Then run this command against that isolated profile and add Playwright browser evidence. Do not enable the adapter in the production compose profile.

Until that adapter and a disposable owner HTTP session exist, the correct status is `END_TO_END_ISOLATED_ACCEPTANCE: PARTIAL`, not success.
