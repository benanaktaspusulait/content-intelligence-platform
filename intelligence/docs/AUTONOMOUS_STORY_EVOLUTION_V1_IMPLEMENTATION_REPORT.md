STORY_EVOLUTION_ENGINE: PARTIAL

AUTONOMOUS_STORY_MULTI_ROUND: NOT_VERIFIED

MEANINGFUL_CANDIDATE_COMPARISON: NOT_VERIFIED

OWNER_STORY_APPROVAL: VERIFIED

IMMUTABLE_NEW_SOURCE: VERIFIED

PROMPT_GENERATION_HANDOFF: VERIFIED

AUTONOMOUS_PROMPT_OPTIMIZATION_HANDOFF: NOT_VERIFIED

MIMI_CANONICAL_A_START_GATE: BLOCKED_CORRECTLY

BROWSER_E2E: NOT_VERIFIED

REAL_PROVIDER_CALLS: 0

CPQ_GRADING: INACTIVE

RENDER_AUTHORIZED: false

# Implementation report

## Reused components

The implementation reuses `WorkflowService` story records, exact candidate fingerprints, the existing owner authentication, `approveStory`, the normal `CREATIVE_ROLE` event ledger, the existing prompt builder contract, `OptimizationLoopService`, the target-aware Ruleset 1.11 preflight, and existing provider/cost restrictions. The Mimi prompt-optimization target gate was not changed.

## Added components

- `V69__autonomous_story_evolution.sql` adds durable run, immutable draft and event tables.
- `StoryEvolutionService` adds bounded authorization, idempotent start, durable round state, candidate persistence, owner approval, cancellation and separate prompt-handoff authorization.
- `WorkflowService.persistStoryEvolutionDraft` records an autonomous candidate as a normal STORY revision so the existing approval boundary remains authoritative.
- `WorkflowController` exposes start, reconnect, latest, approve, stop and prompt-handoff endpoints under `/api/v1/intelligence/workflow/cpq/story-evolution-runs`.
- Step 6 already exposes the separate Story Evolution path; it remains explicitly distinct from protected prompt optimization.

## Lifecycle and bindings

A run stores the exact source story record and SHA-256, owner grant, objective, round, parent draft, candidate SHA-256, provider response payload, and event history. A candidate can reach `AWAITING_OWNER_STORY_APPROVAL`, but it cannot mutate the original story. Approval requires the current draft ID and candidate fingerprint. Approval creates a new immutable STORY record and a normal STORY_APPROVAL record. The previous approved source remains unchanged.

Prompt handoff is a separate command. It requires the new approval record, exact approved candidate/revision/fingerprint, an explicit prompt-generation authorization, and retries disabled. It calls the existing `BUILD_PROMPT` workflow against the new story source; it does not reuse Mimi's old approval or canonical score.

## What was verified

- Backend compilation passed.
- Flyway applied V69 in the deployed database: `Successfully applied 1 migration ... now at version v69`.
- Deployment completed with `./intelligence/scripts/deploy.sh backend`; backend image `sha256:dcfb3f370084e10b7334eaeb32ff2171bce9c7c2e67d440431404d0d3606edaf` and frontend image `sha256:07885fbe0f10aa767af35132010df9bcf62e5c2275cd3a9bfe2be190eb1e28b6` passed health/image checks.
- The live API route exists and is protected; an unauthenticated POST returned HTTP 403 before any story or provider operation.
- `CPQ_PILOT_REAL_ENABLED=false` remained in force. No OpenAI or DeepSeek call was made.
- The existing live Step 6 read-only feasibility check still returns `TARGET_BLOCKED_BY_STORY_CONSTRAINT`, score `88.41`, conditional ceiling `89.31`, A threshold `92`.

## Not yet verified

A disposable PostgreSQL + mocked-ML integration test has not yet been completed for the full chain: two generated candidates, independent story assessment, automatic second-round context, owner approval, new prompt compilation, and prompt-optimizer handoff. The current service has the durable endpoints and transitions, but the deployed UI still only links into the Story Evolution route and does not yet render the complete running/side-by-side approval/handoff screen. Therefore the product is intentionally classified PARTIAL and no claim of autonomous creative effectiveness is made.

The current implementation also stops a production run when real dispatch is disabled, as required. Positive candidate generation must be exercised only in an isolated test with a mocked `QualityMlClient`; it must never be enabled against the production database or paid providers.

## Next owner action

After a disposable no-egress integration fixture and the dedicated Story Evolution UI are added, re-authenticate the owner in Step 6 and run the mock acceptance flow. Do not enable real dispatch or approve a production story as part of that verification.
