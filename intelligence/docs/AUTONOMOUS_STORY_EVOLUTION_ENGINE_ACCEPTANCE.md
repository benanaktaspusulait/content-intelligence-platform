STORY_EVOLUTION_ENGINE: PARTIAL

STORY_MULTI_ROUND: VERIFIED

REAL_STORY_CANDIDATE_GENERATION_PATH: VERIFIED_WITH_MOCK_PROVIDER

CREATIVE_COMPARISON: VERIFIED

OWNER_APPROVAL_HANDOFF: VERIFIED

NEW_IMMUTABLE_APPROVED_SOURCE: VERIFIED

NEW_SOURCE_PROMPT_GENERATION: NOT_VERIFIED

AUTONOMOUS_PROMPT_HANDOFF: NOT_VERIFIED

BROWSER_E2E: NOT_VERIFIED

REAL_PROVIDER_CALLS: 0

CPQ_GRADING: INACTIVE

RENDER_AUTHORIZED: false

# Acceptance evidence

## Implementation

The V69 durable schema now stores `story_evolution_runs`, immutable `story_evolution_drafts`, and `story_evolution_events`. `StoryEvolutionService` owns the server-side loop and does not require the browser to advance rounds. Each round loads the original story, current best, accepted changes, rejected candidates, previous assessment, objective, source fingerprint, and production profile. It requests complete STORY candidates through the existing `creative-role` contract, rejects equivalent candidates, calls the independent STORY_REVIEW contract, persists the review and candidate fingerprint, then either schedules the next round or enters `AWAITING_OWNER_STORY_APPROVAL`.

`WorkflowService.persistStoryEvolutionDraft` creates a normal STORY record for an approved candidate. Existing `approveStory` remains the authority for exact candidate/revision/fingerprint approval. The separate `prompt-handoff` endpoint requires the newly created approval and a new explicit prompt-generation authorization; it cannot reuse the story-evolution grant. The existing `BUILD_PROMPT` workflow is used for the handoff. Step 6 now exposes source, objective, round/request/budget controls, candidate drafts, approval and separate authorization messaging.

## Disposable two-round run

`StoryEvolutionServiceTest` uses disposable PostgreSQL and mocked `QualityMlClient` transport. No candidate body is hardcoded in production code.

Observed test trace:

1. `start` created one durable `READY` run with source story SHA-256, owner grant, objective, limits and idempotency key.
2. Round 1 generated two complete candidates through the mocked STORY response. One exact equivalent candidate was rejected as `EQUIVALENT_OR_MEANINGLESS`; the materially changed candidate was passed to the mocked STORY_REVIEW contract and retained.
3. The run automatically returned to `READY`; no browser command advanced it.
4. Round 2 was dispatched by the next worker tick. Its request context contained `bestCandidate`, `previousAssessment`, `acceptedChanges`, and `rejectedCandidates` from round 1. The second candidate was retained and the run entered `AWAITING_OWNER_STORY_APPROVAL`.
5. Durable drafts contained two rounds and each event recorded the retained round and draft ID.
6. Duplicate start with the same owner/idempotency key returned the saved run and did not create another run.

Test result: 3 tests passed, 0 failures, 0 errors in `StoryEvolutionServiceTest`.

## Approval and source binding

The disposable approval test rejected stale fingerprints by the service contract, then approved the exact current draft. It created a new STORY record ID and approval record through the existing WorkflowService boundary. The original source record remained the parent and was not overwritten. The test then exercised the separate handoff command with a mocked BUILD_PROMPT response and verified that the new story record ID was sent as `sourceStoryRecordId`.

This proves the durable approval boundary and new-source binding. It does not claim that a production prompt was created in the real database.

## Existing Mimi protection

The deployed Mimi Prompt Optimization path remains governed by the V68 target-aware gate. The live Step 6 feasibility check continues to show `TARGET_BLOCKED_BY_STORY_CONSTRAINT`, score `88.41`, conditional ceiling `89.31`, and A threshold `92`. Story Evolution does not call that gate as its admission decision. Prompt optimization still does.

## Deployment

- Backend compile passed.
- Frontend production build passed with existing Angular bundle-size/unused-component warnings.
- `./intelligence/scripts/deploy.sh backend frontend` passed.
- Backend image: `sha256:4ebc0864c6cd225623b649af60b01ff14b51678939485da3569d4554ce222c3f`.
- Frontend image: `sha256:d90cef1dd4270207b24f8d3faf42b2e6a068df763cad1e637b7d026eaebd052d`.
- Backend/frontend health and running-image checks passed.
- Flyway V69 remains applied.
- Real dispatch remained disabled and no OpenAI/DeepSeek request was sent.

## Browser result

The deployed Step 6 page visibly contains the autonomous Story Evolution controls, protected source SHA/story text, objective, round/request/budget fields, explicit separate consent, candidate area and approval state. The read-only source endpoint was verified in the browser after deployment. In the current browser session owner authentication was not established, so the Start button remained unavailable; no production run or approval was attempted. Authenticated browser E2E is therefore still `NOT_VERIFIED`.

## Remaining gaps

The full product chain is still partial because the following have not been proven in an isolated live browser run:

- actual backend-to-ML mocked transport through HTTP rather than the service-level mock;
- actual BUILD_PROMPT compiler output and Ruleset 1.11 evaluation for the new source;
- target-aware preflight against the new approved story;
- automatic entry into `OptimizationLoopService` under a separate prompt grant;
- refresh/stop behavior in the running Story Evolution UI;
- side-by-side original/evolved comparison presentation.

The final frontend pass now loads the read-only story source independently of owner authentication, polls READY/RUNNING Story Evolution runs, exposes a stop action, and selects the persisted `bestDraftId` for approval. The source story is shown beside the evolved drafts for review. These changes are build/deploy verified; an authenticated browser run remains unverified.

No historical Mimi story, prompt version, analysis, score, CPQ policy or render authorization was modified.
