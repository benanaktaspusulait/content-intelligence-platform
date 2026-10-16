ISOLATED_OWNER_AUTH: FAILED
DISPOSABLE_SOURCE_CREATED: FAILED
RUNNING_ML_FIXTURES: VERIFIED
NO_EGRESS: VERIFIED

STORY_EVOLUTION_HTTP: FAILED
AUTONOMOUS_STORY_ROUNDS: FAILED
OWNER_STORY_APPROVAL: FAILED

BUILD_PROMPT_HTTP: FAILED
NEW_PROMPT_PERSISTED: FAILED
NEW_ANALYSIS_PERSISTED: FAILED
RULESET_1_11_EVALUATED: VERIFIED

PROMPT_OPTIMIZATION_STARTED: NO
AUTONOMOUS_PROMPT_ROUNDS: NOT_EXECUTED

INITIAL_PROMPT_SCORE: 88.40625/B
ROUND_1_SCORE: NOT_EXECUTED
ROUND_2_SCORE: NOT_EXECUTED
BEST_PROMPT_SCORE: NOT_EXECUTED
BEST_PROMPT_GRADE: NOT_EVALUATED

CANONICAL_A_THRESHOLD: 92
ISOLATED_CANONICAL_A_REACHED: NOT_EVALUATED
REAL_PROVIDER_CANONICAL_A_VERIFIED: NO

CHARACTER_REFERENCE: BLOCKED
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

# Execution evidence

## Command and exit code

```text
./intelligence/scripts/acceptance-story-firstframe.sh
exit code: 0
```

The command now starts a loopback FastAPI ML fixture service, calls the real `/api/v1/workflow/creative-role` endpoint, validates the response through the normal STORY parser, runs 35 ML tests, and runs backend Testcontainers/Flyway v69 tests. The HTTP fixture response was `provider=ISOLATED_FIXTURE`, `providerDispatched=false`, `calls=0`, `actualCostUsd=0.0`. No real provider, image or video request occurred.

## Owner authentication milestone

The existing owner implementation was inspected and the focused `CpqOwnerAccessTest` passed. It verifies missing credentials fail closed, invalid credentials are rate limited, valid disposable credentials establish the owner session, OWNER role is present without reviewer roles, logout revokes the session, CSRF/origin checks apply, and remote HTTP is denied.

This is not an authenticated disposable backend HTTP run. The current harness does not yet start a separate backend with a temporary `CPQ_OWNER_ID`/credential mount, so `ISOLATED_OWNER_AUTH` remains `FAILED` and no owner credential was used against production.

## Source and story milestones

No disposable content/story/prompt/analysis records were created. The required source setup must use business services in a separate backend/Testcontainers HTTP process; direct SQL seeding was intentionally not used. Therefore there are no honest story run IDs, draft IDs, approval IDs, new story SHA, prompt version ID, analysis ID or quality validation ID to report.

The immutable production control remains analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, prompt `10`, Ruleset 1.11 `88.40625/B`, target `92/A`. It was not modified.

## Optimization and first-frame milestones

Because no new prompt and analysis exist, the target-aware preflight and existing OptimizationLoopService were not started. No score progression exists and no A claim is made. No character reference, first-frame candidate, image bytes, visual QA record or owner image approval was created. Render authorization remains `false`.

## Exact remaining integration defect

The missing piece is not the ML fixture transport. It is a disposable backend HTTP process that uses the existing owner authentication configuration and invokes normal content/story/prompt/review services before calling Story Evolution. The current shell harness only starts the ML HTTP fixture and uses Testcontainers from backend tests; it does not start a Spring HTTP server with a temporary owner secret and a database that can be reached by an external HTTP client.

The next implementation should add a test-only Spring Boot `RANDOM_PORT` acceptance profile (or an equivalent disposable compose project) with a temporary owner credential mount, ML base URL pointed at the loopback fixture, and a business-logic bootstrap client. It must expose no production route and must be removed with the disposable database after the run. Only after that server exists can the required cookie/CSRF HTTP trace and browser Playwright trace be collected.

## Production integrity

No production owner credential was read. No production database row, prompt, story, analysis, image, render job or approval was written. No deployment was performed for the test-only fixture mode. No real provider, GPT-Image-2 or Seedance call was made.

## Subsequent P0 HTTP checkpoint — 2026-10-16

The disposable Spring HTTP + authenticated owner + approved source milestone subsequently passed. See [DISPOSABLE_OWNER_HTTP_ACCEPTANCE.md](DISPOSABLE_OWNER_HTTP_ACCEPTANCE.md) and its actual HTTP evidence. The statuses above describe the earlier run; they are preserved rather than rewritten. This P0 success does not establish autonomous A/A+ generation or the full first-frame workflow.
