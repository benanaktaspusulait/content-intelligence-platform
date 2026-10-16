STORY_EVOLUTION_MULTI_ROUND: VERIFIED
OWNER_STORY_APPROVAL: VERIFIED
BUILD_PROMPT_REAL_APPLICATION_PATH: IMPLEMENTED_NOT_VERIFIED
NEW_PROMPT_PERSISTED: NOT_VERIFIED
RULESET_1_11_EVALUATION: NOT_VERIFIED
NEW_ANALYSIS_PERSISTED: NOT_VERIFIED
AUTONOMOUS_PROMPT_OPTIMIZATION: NOT_VERIFIED
BASELINE_CANONICAL_SCORE: 88.40625/B
ROUND_1_CANONICAL_SCORE: NOT_EVALUATED
ROUND_2_CANONICAL_SCORE: NOT_EVALUATED
BEST_RETAINED_CANONICAL_SCORE: NOT_EVALUATED
CANONICAL_A_TARGET: 92
ISOLATED_TEST_CANONICAL_A_REACHED: NOT_EVALUATED
REAL_PROVIDER_AUTONOMOUS_A_VERIFIED: NO
CHARACTER_REFERENCE_BINDING: BLOCKED
FIRST_FRAME_GENERATION_INTEGRATION: NOT_VERIFIED
FIRST_FRAME_VISUAL_QA: NOT_VERIFIED
FIRST_FRAME_OWNER_APPROVAL: NOT_VERIFIED
STEP_7_READY: NO
RENDER_AUTHORIZED: false
BROWSER_E2E: NOT_VERIFIED
REAL_PROVIDER_CALLS: 0
REAL_IMAGE_GENERATION_CALLS: 0
REAL_VIDEO_RENDER_CALLS: 0
PRODUCTION_TEST_RECORDS: 0
CPQ_GRADING: INACTIVE
END_TO_END_ISOLATED_ACCEPTANCE: PARTIAL

# Story → A-grade prompt → first-frame acceptance

## Scope

This report covers the requested integration seam only. Story Evolution and the existing autonomous optimizer were reused. No story, Prompt v10, canonical ruleset, score, F8 policy, historical record, render permission or production database row was changed by this task.

## Implemented application path

`StoryEvolutionService.handoff` now performs the following sequence after exact owner story approval:

1. Calls the existing `WorkflowService` `BUILD_PROMPT` role with the approved story, revision, approval record, source fingerprint and production settings.
2. Rejects an empty BUILD_PROMPT result.
3. Runs the existing `QualityMlClient` Ruleset 1.11 evaluator against the complete prompt and records canonical evidence in run progress.
4. When `contentId` and `parentPromptVersionId` are supplied, calls the existing `ContentWorkspaceController.createPrompt` authority. This creates the normal immutable prompt version and provenance link; it does not insert a row directly.
5. Calls `WorkflowService.runReview(..., true)` for the new content/prompt binding, then calls `IntelligenceQualityValidationService.validateWorkflowProfile` to persist the quality validation.
6. Runs `WorkflowService.adaptiveOptimizationPreflight` against the new REVIEW record, rather than reusing the original Mimi analysis.
7. Returns the new prompt/version, REVIEW analysis, quality-validation ID and preflight result. It also provides a Step 7 link bound to the new content and prompt IDs, with state `RENDER_PREPARATION_BLOCKED_UNTIL_CHARACTER_AND_FIRST_FRAME`.

The Step 6 story-source endpoint now returns the real `contentId` and `promptVersionId`, so the UI can submit the correct parent binding. The UI keeps story approval and BUILD_PROMPT authorization as separate explicit actions and exposes the Step 7 preparation link only after a successful handoff.

The existing first-frame implementation remains authoritative. It is already exposed by `/api/v1/intelligence/workflow/start-frame/generate`, `/start-frame/candidates`, `/start-frame/accept` and `/start-frame/reject`, and Render Preparation binds accepted assets to the exact content/prompt version. This task did not bypass those gates or generate an image.

## Verified evidence

- Deployed backend image: `sha256:a208f27262697aac6dfed679fc62cf98b7b086b595ac6bfb433ceec04a97007c`.
- Deployed frontend image: `sha256:12483eaafe7a8a2b8bb9c80f8521747d3e09b59a7afd03d40e6c7461ab114487`.
- Backend and frontend health checks passed; provider-capabilities endpoint passed.
- Read-only source inspection after deployment returned analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, content `10`, prompt version `10`, approved story record `bc1cf798-d20b-4b98-8b73-56e1581c3afc`, and story SHA `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`.
- The same read-only response reproduced the existing canonical control as `88.40625000000001 / B` (display-equivalent to the authoritative `88.40625 / B`). It still reports ATTEMPT_001 and the existing pre-render evidence blockers; no new analysis was created.
- Focused backend test: `StoryEvolutionServiceTest`, 3/3 passed with Testcontainers PostgreSQL.
- Frontend production build passed. Angular emitted existing bundle/style budget warnings only.
- `./intelligence/scripts/deploy.sh backend frontend` passed and both containers were healthy.

## Why full isolated acceptance is not claimed

The deployment keeps `CPQ_PILOT_REAL_ENABLED=false`. No authenticated disposable owner session with an internal no-egress provider transport fixture was available for this turn. Therefore the application was not allowed to start a paid Story Evolution or BUILD_PROMPT run, and there is no honest new story approval, prompt-version ID, REVIEW analysis ID, optimization run, first-frame candidate, visual QA record or owner image approval to report.

A previous incomplete-prompt validation returned the normal HTTP 409 contract rejection. It was not bypassed and no score was fabricated. The required next test must supply a complete mocked STORY, STORY_REVIEW and BUILD_PROMPT response through the real HTTP path, then re-read the persisted records and exercise the existing optimizer and Render Preparation gates.

## Current Step 7 blockers

- Verified Mimi character reference is not bound to the new prompt (and no new prompt exists yet).
- An accepted start frame and image-aware visual QA are not present.
- Owner image approval is not present.
- Canonical target-aware preflight remains authoritative; the original Mimi target gate is unchanged.
- Render authorization remains `false`; no ATTEMPT_001 waiver or other canonical waiver was created.

Final status: `END_TO_END_ISOLATED_ACCEPTANCE: PARTIAL`.
