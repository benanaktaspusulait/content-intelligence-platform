# Step 6 governance acceptance report

Final status: **STEP_6_GOVERNANCE_IMPLEMENTED**

## 1. Approved architecture

ADR `STEP6-GOVERNANCE-001`, version 1.0, is APPROVED. The previously inactive draft has been finalized; the canonical copy is `intelligence/docs/ADR_STEP6_GOVERNANCE_001.md`. This approval authorizes the architecture, not a Mimi exception or a render.

## 2. Authority and policy

The authoritative backend service is `Step6GovernanceService`. It derives identity and roles exclusively from the authenticated servlet principal and container role checks. Roles are `ARCHITECTURE_APPROVER`, `EVIDENCE_REVIEWER` and `PRODUCTION_OPERATOR`. JSON role claims and arbitrary role headers grant no authority.

`ATTEMPT_COUNT_EXCEPTION_V1` targets only ATTEMPT_001. The default three-attempt requirement remains. Eligibility requires at least two genuine source-bound attempts in an eligible short-form case, independent source/story evidence for mini-story, active progression and payoff, preserved approved events, concrete justification and explicit approval. The evidence reviewer cannot approve their own exception.

Records bind the exact prompt ID and SHA-256, current analysis, ruleset, approved story and production settings. They expire after 24 hours and support audited revocation. Stale or revoked supporting evidence invalidates effective admission. Canonical outcomes, original failure counts and score are retained.

**Operational limitation:** the deployed local application currently supplies no authenticated principal/role source. All governed writes therefore correctly deny authorization. A trusted container/SSO role integration is required before an operator can exercise the positive path in this local deployment. No anonymous fallback or fabricated operator identity was added. Authorized behavior was verified using trusted test principals and disposable databases; no authorized live Mimi write was attempted.

## 3. Separate text acceptance and render admission

`TEXT_ACCEPTED_RENDER_BLOCKED` requires explicit authenticated operator confirmation and immutable provenance. It records unresolved findings and accepted production risks without changing canonical results or authorizing rendering. Evidence preparation remains independently accessible.

The frontend loads server `allowedActions` and exact blocking reasons; every POST recomputes permissions against current persisted evidence. The legacy public no-text-repair command routes through this policy.

`ValidationEvidenceService` and render-queue `ValidationEvidencePolicy` require a complete internal, scope-bound effective-admission proof. Only the specifically authorized ATTEMPT_001 admission exception and eligible production-risk acknowledgement are recognized. Failure ledgers and counts remain intact. Other hard failures, unknown evidence, independent validation, visual gates, expiry, F8 and the existing >=92 quality threshold remain enforced. Text acceptance alone cannot enqueue a render.

## 4. Evaluator corrections: governed Ruleset 1.11

- BEAT_004 previously treated the entire 5–10s multiplication beat as a static state. Its exact source explicitly says notes multiply from two to four to eight. It now returns UNKNOWN / SUBSTATE_TIMING_UNKNOWN, retaining source quote and span, with `substateTimes: null`. No invented sub-beat timing or unearned PASS.
- CONTINUOUS_ACTION_MOMENTUM previously counted the final 3 seconds of active sneeze/scatter payoff as passive aftermath. The generic source-action and negation-aware measurement now reports zero passive aftermath and PASS for these saved inputs. Explicit still holds remain failures in deterministic tests.

No weights or thresholds changed. Frozen Ruleset 1.10 and earlier records were not rewritten.

## 5. Official persisted workflow verification

Content 10; saved Prompt ID 10 (the UI labels its version number as v1).

- Current authoritative analysis: `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`.
- Current comparison: `9275c94b-fc35-4207-8648-dfd8d166e502`.
- Ruleset: 1.11.
- Original, Candidate A and Candidate B: **88.40625000000001 / B** (88.41 displayed to two decimals).
- Previous Ruleset 1.10: 84.20833333333334 / B for each.
- Only changed canonical rules: BEAT_004 FAIL→UNKNOWN; CONTINUOUS_ACTION_MOMENTUM FAIL→PASS.
- ATTEMPT_001 remains FAIL with two genuine attempts against the default three; PRODUCIBILITY_003 and both missing-visual-evidence failures remain visible.
- New analysis has 24 PASS, 4 FAIL, 11 UNKNOWN and 7 NOT_APPLICABLE outcomes.

The official review and local comparison revalidation used saved sources without provider dispatch. Candidate prompt bytes were reused. Selection and approval remain unset. **Recommendation: KEEP_ORIGINAL**; no superior candidate or score-based render readiness is asserted.

## 6. Actual deployed browser/backend verification

All four services were rebuilt/deployed with `intelligence/scripts/deploy.sh`; built/running image IDs and HTTP health checks match (`deployment-check.log`).

The deployed Step 6 page loaded the real policy through its DOM button and issued GET `/api/v1/intelligence/workflow/records/f0d36feb-ee0f-4da8-ae21-2071a3ddea18/governance` (200). Browser DOM and screenshot show ATTEMPT_001 as POLICY_EXCEPTION_REQUIRED and PRODUCIBILITY_003 as PRODUCTION_RISK_REVIEW. Text acceptance, exception approval and risk acknowledgement buttons are disabled; authenticated-role and independent-evidence reasons are visible. No confirmation checkbox or approval button was submitted.

The browser automation CLI's native click command initially reported completion without issuing the request; verification used the actual deployed button's DOM click handler, not a fixture or direct component invocation. The resulting network request and rendered policy were inspected. This is a verification-tool limitation, not a claimed successful physical mouse test.

The actual Continue to Render Preparation link opened Step 7 with Prompt ID 10 and the exact current analysis/workflowReview ID. The real First Frame tab shows “Rendering not authorized”, no accepted image, and disabled Generate Start Frame with “Upload and verify a character reference first.” No preparation save/upload/generation action was invoked.

An unauthenticated backend command with spoofed role headers/JSON was rejected with HTTP 403 before record lookup/write; a synthetic nonexistent UUID was used, not a Mimi approval request.

Evidence: `browser-policy.json`, `step6-policy.png`, `browser-preparation.json`, `browser-first-frame.json`, `step7-first-frame.png`, `live-policy.json`, `live-unauthorized-denial.json`.

## 7. Regression results

- ML/parser/canonical/Step 5/Step 6/F8/optimization/autofix focused regressions: **343 passed** (existing deprecation warnings remain).
- Frontend workflow/preparation/governance: **98 passed**.
- Backend: **45 passed, 3 skipped, 0 failures/errors** across 48 selected tests; all 14 new governance tests passed. Three pre-existing optional live/mock tests were skipped, not counted as passing.
- Render admission policy: **27 passed**.
- Frozen golden evidence for Rulesets 1.7–1.9 and exact canonical equality for three saved 1.10 inputs verified unchanged.
- Authorized, unauthorized, missing justification, wrong rule scope, stale binding, expiry/revocation, independent reviewer separation, canonical FAIL preservation, separate acceptance, unresolved risk/visual gates and complete effective admission were tested with mocked providers and disposable test databases. A synthetic high-score fixture tests the unchanged >=92 admission threshold; no production score was adjusted.

See `backend-test-summary.json`, `historical-preservation.json` and test logs.

## 8. Historical integrity and actual Mimi eligibility

All 67 pre-existing workflow-event hashes are unchanged. Exactly two new official events were added: the review and comparison above. Saved prompt text hashes are unchanged; no prompt version or candidate was created. CREATIVE_ROLE record count stayed 23. No GOVERNANCE_* approval records were created, and render jobs remained zero. Production database inspection was read-only.

Mimi meets the deterministic two-attempt count precondition; this is not sufficient authorization. Live exception approval remains denied because there is no authenticated Architecture Approver and no independently recorded story/progression/payoff support. Text acceptance and risk acknowledgement remain denied without an authenticated Production Operator.

## 9. Remaining Step 7/F8 requirements

1. Establish trusted authentication/role mapping, then obtain independent scoped source/story review and explicit operator decisions where required.
2. Supply and verify the canonical Mimi character reference.
3. Prepare, inspect and explicitly accept a start frame for the exact saved prompt/settings.
4. Supply missing required visual/semantic/independent evidence; UNKNOWN is not PASS. Resolve other non-waivable failures and explicitly accept eligible production risks.
5. Revalidate current prompt/hash/analysis/ruleset/settings binding, quality threshold and all independent F8/queue requirements before any separate render authorization.

Evidence preparation can proceed now. No Mimi exception, text approval, paid provider call, image/video generation, publication, historical overwrite, prompt/story change, or commit/push was performed.
