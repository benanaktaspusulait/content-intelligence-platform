STORY_MULTI_ROUND: VERIFIED
OWNER_APPROVAL: VERIFIED

NEW_APPROVED_SOURCE: VERIFIED
ACTUAL_BUILD_PROMPT_WORKFLOW: FAILED
NEW_PROMPT_VERSION_PERSISTED: FAILED
ACTUAL_RULESET_1_11_EVALUATION: FAILED
NEW_ANALYSIS_PERSISTED: FAILED

TARGET_AWARE_PREFLIGHT: FAILED
AUTONOMOUS_OPTIMIZER_HANDOFF: BLOCKED

AUTHENTICATED_HTTP_E2E: FAILED
AUTHENTICATED_BROWSER_E2E: FAILED

REAL_PROVIDER_CALLS: 0
PRODUCTION_TEST_RECORDS: 0
CPQ_GRADING: INACTIVE
RENDER_AUTHORIZED: false

END_TO_END_ACCEPTANCE: PARTIAL

# Scope and current baseline

The V69 durable Story Evolution loop, automatic multi-round progression, candidate rejection, `bestDraftId` selection and owner approval were already present. This change closes the persistence seam in the handoff implementation; it does not create another optimizer.

## Code changes

`StoryEvolutionService.handoff` now accepts a scoped `contentId` and `parentPromptVersionId` binding. After exact approved-story verification it invokes the existing `WorkflowService` `BUILD_PROMPT` operation, rejects empty output, fingerprints the returned prompt, and runs `QualityMlClient.validatePromptForWorkflow` with Ruleset 1.11. When the content binding is supplied, it then uses the existing `ContentWorkspaceController.createPrompt` authority to create a normal immutable `prompt_versions` row, uses `WorkflowService.runReview(..., true)` to create the normal `REVIEW` event, uses `IntelligenceQualityValidationService.validateWorkflowProfile` to persist the quality validation, and recomputes `WorkflowService.adaptiveOptimizationPreflight` against the new review ID. The run progress records the new prompt ID/version/SHA, analysis ID, quality-validation ID and preflight result.

The Step 6 source endpoint now returns the existing `contentId` and `promptVersionId`; the UI passes them to the separate BUILD_PROMPT/evaluation handoff command and displays the resulting prompt/evaluation state. No original Mimi row is overwritten.

## Verified evidence

- Existing disposable Story Evolution test: 3/3 passed.
- Backend compile: passed.
- Frontend production build: passed.
- Deployed backend image: `sha256:cddd4a554e039a9b36359ac3164434a0489095fb0a5b45e52eb795042d9b5e4a`.
- Deployed frontend image: `sha256:0cb4cbae0d8d1f3551839bcb9ec2314b52d6906570c98d509b1bb641038e3cfd`.
- Backend and frontend health checks: passed.
- Read-only source endpoint returned the real bindings: content `10`, prompt version `10`, approved story record `bc1cf798-d20b-4b98-8b73-56e1581c3afc`, story SHA `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`.
- Real provider dispatch remained disabled and no production records were written.

## Why the final E2E statuses are not VERIFIED

No authenticated disposable owner session with an external-provider transport mock was available in this deployment, and `CPQ_PILOT_REAL_ENABLED=false` correctly prevents starting a paid Story Evolution or BUILD_PROMPT run. Consequently there is no real application HTTP run ID, approved evolved story ID, new prompt-version ID, new analysis ID or optimizer run ID to report.

A direct ad-hoc ML validation request also returned the normal contract rejection for an incomplete prompt fixture (HTTP 409); no score was fabricated and no persisted analysis was created.

The current production database contains no synthetic story approval, prompt version or analysis from this acceptance task. The old Mimi source remains unchanged and its target-aware gate remains authoritative.

## Required next owner action

Provide an isolated test-owner session and an internal no-egress ML transport fixture that returns a complete valid `STORY`, `STORY_REVIEW` and `BUILD_PROMPT` response. Then run the HTTP/browser scenario with `contentId=10`, `parentPromptVersionId=10`, a separately scoped prompt-generation grant, and the existing optimizer preflight. No production provider key or real paid inference is required.
