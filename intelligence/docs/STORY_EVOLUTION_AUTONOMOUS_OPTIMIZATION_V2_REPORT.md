V68_START_TARGET_GATE: VERIFIED
MIMI_UNAUTHORIZED_DISPATCH: BLOCKED
STORY_EVOLUTION: PARTIAL
STORY_MULTI_ROUND: NOT_VERIFIED
OWNER_STORY_APPROVAL: EXISTING_WORKFLOW_REUSED
NEW_STORY_SOURCE_BINDING: EXISTING_WORKFLOW_REUSED
AUTONOMOUS_PROMPT_HANDOFF: NOT_VERIFIED
BROWSER_END_TO_END: PARTIAL_OWNER_AUTH_BLOCKED
REAL_PROVIDER_CALLS: 0
CPQ_GRADING: INACTIVE
RENDER_AUTHORIZED: false

# Story Evolution + Autonomous Prompt Optimization V2

## Result

The V68 bounded optimization start path now performs the authoritative, target-aware feasibility calculation before validating or recording a paid grant. The worker repeats that calculation at its durable dispatch boundary. Mimi therefore fails closed with `TARGET_BLOCKED_BY_STORY_CONSTRAINT` before a reservation, optimization job, or provider request can be created. The deployed Step 6 browser path shows the same state: score 88.41, conditional ceiling 89.31, A minimum 92, and no defensible prompt-only path.

The story lifecycle is deliberately kept on the existing Creative Studio/WorkflowService contracts. Story revision creates a new immutable `CREATIVE_ROLE` record, approval is a separate authenticated operation, and the existing prompt creation flow binds the resulting approved story revision to a new prompt. No new story or prompt was approved during this work. Autonomous provider-backed story generation was not run.

## Implementation

### Authoritative V68 gate

`OptimizationLoopService` now calls `WorkflowService.adaptiveOptimizationPreflight(UUID)` through a small overridable seam. The response is surfaced in V68 preflight as `targetAwarePreflight`, together with `generationAllowed` and `state`. `start(...)` recomputes this result immediately before any grant validation, advisory lock, idempotency lookup, reservation, or insert. A blocked target returns a structured conflict reason containing the state, score/ceiling evidence when available, provider call count `0`, and the non-paid next action (`STORY_EVOLUTION_OR_UPDATED_SOURCE_EVIDENCE`).

`processNext/step(...)` recomputes the same policy after loading the persisted run and before `PREFLIGHT_REQUEST` or request insertion. A changed source, analysis, ruleset, or feasibility result stops the run and records the fresh blocker. Browser inspection therefore cannot carry stale eligibility into dispatch.

### Story Evolution path

The UI now distinguishes:

- **Optimize Existing Prompt** — preserves the approved story and cannot repair protected story constraints.
- **Evolve Story & Optimize** — opens the existing Creative Studio story workflow with the source analysis context. The existing revision endpoint (`POST /api/v1/intelligence/workflow/records/{id}/story-revisions`) creates a new immutable draft record; `POST /api/v1/intelligence/workflow/creative-role/{id}/approve-story` requires exact candidate text, revision ID, and fingerprint. The existing prompt builder then creates the next immutable prompt version. Approval and prompt creation remain separate boundaries.

No parallel story authority or alternate source binding was introduced.

## Verification

### Deterministic backend tests

`mvn -q -f intelligence/backend/pom.xml -Dtest=OptimizationLoopTest test`

Result: 12 tests passed, 0 failures, 0 errors. The suite includes the new disposable target-block test: Mimi-style `TARGET_BLOCKED_BY_STORY_CONSTRAINT` returns before `optimization_runs` insertion and before any provider dispatch. The eligible fixture continues through the existing bounded loop tests, proving the gate does not block every target.

### Builds and deployment

- Backend compile: passed.
- Frontend production build: passed (Angular emitted existing bundle-size/unused-component warnings only).
- Deployment command: `./intelligence/scripts/deploy.sh backend frontend`.
- Backend image: `sha256:6044055d99c38224f60cad6c65912a6948d2484925a7a22a933e92e5dbc7292e`.
- Frontend image: `sha256:07885fbe0f10aa767af35132010df9bcf62e5c2275cd3a9bfe2be190eb1e28b6`.
- Backend and frontend health checks passed; the script verified the running image IDs.
- ML, render service, database, prompt version 10, analysis history, and saved story records were not rebuilt or mutated.

### Browser verification

On the deployed Step 6 page for Content 10 / Prompt 10 / analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, clicking **Check A feasibility (no provider call)** visibly returned:

- `TARGET_BLOCKED_BY_STORY_CONSTRAINT`
- Current score `88.41`
- Conditional ceiling `89.31`
- A minimum `92`
- “No defensible prompt-only path to A with current evidence and protected story.”

The owner pilot panel visibly shows the two protected workflow choices and the Story Evolution link to `/quality/new?mode=STORY_EVOLUTION&sourceAnalysisId=...`. The live owner session was not re-authenticated after the container recreation, so the owner-only controls remained read-only in this browser check. No paid control was enabled or invoked.

## Reuse and boundaries

The implementation reuses the existing target-aware policy, source/stories/approval records, prompt version creation, provider profiles, idempotency ledger, and F8/render gates. It does not alter canonical scoring, rulesets, protected story text, historical analyses, prompt version 10, or render authorization. Story assessments remain provisional text evidence; no audience or visual success claim is made.

## Remaining limitations

This change does not claim autonomous creative quality. A multi-round provider-backed Story Evolution run requires a separate operator authorization and an eligible, source-supported target after approval. Mimi remains blocked under the current protected story and evidence ceiling, so no new source or optimization handoff can be created for it. The existing owner authentication must be re-established in the browser before an owner-only inspection can be completed end to end. Real provider calls remain disabled (`CPQ_PILOT_REAL_ENABLED=false`).
