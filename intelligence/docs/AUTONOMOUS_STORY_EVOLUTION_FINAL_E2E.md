STORY_MULTI_ROUND: VERIFIED
BEST_DRAFT_SELECTION: VERIFIED
OWNER_APPROVAL: VERIFIED
NEW_IMMUTABLE_STORY_SOURCE: VERIFIED
ACTUAL_BUILD_PROMPT: NOT_VERIFIED
NEW_PROMPT_SOURCE_BINDING: VERIFIED
RULESET_1_11_EVALUATION: NOT_VERIFIED
AUTONOMOUS_PROMPT_HANDOFF: PARTIAL
BROWSER_E2E: NOT_VERIFIED
REAL_PROVIDER_CALLS: 0
PRODUCTION_STORY_MUTATIONS: 0
CPQ_GRADING: INACTIVE
RENDER_AUTHORIZED: false

# Acceptance report

## Current baseline and changes

The deployed V69 implementation provides a durable `story_evolution_runs`, `story_evolution_drafts`, and `story_evolution_events` workflow. The worker advances rounds without a browser command, carries the retained candidate, independent review, rejected candidates and source constraints into the next request, and binds owner approval to `bestDraftId` plus the candidate SHA-256.

The final integration change is in `StoryEvolutionService.handoff`. After the exact approved STORY revision is checked, the existing `WorkflowService` `BUILD_PROMPT` operation is invoked with the new story record, candidate, revision, approval record and source fingerprint. Empty builder output is rejected. A returned prompt is fingerprinted and sent through `QualityMlClient.validatePromptForWorkflow(prompt, "1.11", ...)`; the stored run progress now includes the prompt fingerprint, source fingerprint, ruleset version, score/status, parser confidence, failed rules, unknown rules and Video Plan IR. The old source and prompt records are never overwritten.

The Step 6 frontend loads the protected source read-only, polls READY/RUNNING story runs, supports stop, shows the source beside evolved drafts, and approves the persisted `bestDraftId`.

## Deterministic/disposable evidence

`StoryEvolutionServiceTest` uses a disposable PostgreSQL container and complete mocked STORY/STORY_REVIEW responses. It verified two automatic rounds, equivalent-candidate rejection, retained candidate context propagation, duplicate-start idempotency, stale fingerprint rejection, exact best-draft approval and the separate BUILD_PROMPT plus Ruleset 1.11 handoff contract. The handoff test records a new prompt fingerprint and canonical evaluation payload from the evaluator boundary. Result: 3 tests passed, 0 failures, 0 errors.

This is application-service evidence with mocked external transport. It is not evidence of real provider creativity and it does not mutate production data.

## What is verified

- Round 1 and Round 2 execute automatically after one start command.
- Round 2 receives the original story, retained first-round candidate, prior review, accepted changes and rejected candidates.
- At least one equivalent candidate is rejected and a materially changed candidate is retained.
- Approval requires the exact current `bestDraftId` and candidate fingerprint.
- A new immutable STORY revision is created through the existing WorkflowService boundary.
- BUILD_PROMPT receives the new story record and exact approval provenance.
- The new prompt is fingerprinted and evaluated with the actual Ruleset 1.11 client path in the handoff implementation.
- Real dispatch remains disabled and no provider request was issued.

## What remains unverified

A disposable HTTP/browser run with an authenticated test owner was not executed. Therefore the following are not claimed as verified:

- HTTP transport from the deployed backend through the ML service with mocked external provider output.
- A non-mocked production `BUILD_PROMPT` response body.
- A persisted prompt version and analysis record for the newly generated prompt.
- Target-aware preflight against that newly persisted analysis.
- Automatic entry into `OptimizationLoopService` for the new source.
- Authenticated browser click-through from Start through handoff.

The existing Mimi source remains subject to its current target-aware block. No production story, prompt version, analysis, score, CPQ policy or render authorization was modified.

## Verification and deployment

- Backend compile: passed.
- `StoryEvolutionServiceTest`: 3/3 passed.
- Frontend production build: passed; existing Angular bundle warnings remain.
- Full frontend Vitest run was not green (23/29 files passed); failures are in existing video-detail fixtures and Angular test-environment setup, outside this integration path.
- Backend deployed with `./intelligence/scripts/deploy.sh backend`; health check passed.
- Frontend health check passed.
- Backend image: `sha256:f618f0ab7ac1f7c30792472cd83e045a855f94a72e61c8799b1a81d711483a48`.
- Frontend image: `sha256:d90cef1dd4270207b24f8d3faf42b2e6a068df763cad1e637b7d026eaebd052d`.
- `REAL_PROVIDER_CALLS=0`, `PRODUCTION_STORY_MUTATIONS=0`, `CPQ_GRADING=INACTIVE`, `RENDER_AUTHORIZED=false`.

## Final answer to the acceptance question

The complete production workflow cannot be answered YES from the current evidence. The durable story loop, approval boundary, new-source binding and evaluator handoff code are present and tested, but authenticated browser E2E, HTTP mocked transport, persisted new prompt analysis and automatic optimizer entry remain unverified. The honest status is `PARTIAL`, not a successful full end-to-end acceptance.
