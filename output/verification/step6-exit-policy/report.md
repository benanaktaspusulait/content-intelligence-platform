# Step 6 exit policy audit

**STEP_6_EXIT_POLICY_DECISION_REQUIRED**. No application policy or evaluator change was activated. The attached request explicitly requires stopping when current architecture does not authorize the proposed decision. A concrete, inactive ADR draft is provided in ADR-DRAFT.md. No new production evaluation or deployment was performed in this audit.

## Root cause and governing conflict

Frontend `requiredTextRepair` counts every canonical failedRule. Backend `saveProductionReviewDecision` rejects any nonempty failedRules list. Both therefore conflate missing evidence, production risk, evaluator defects and actual text defects. They are consistent in this blanket rejection, but have no shared typed resolution contract.

The governed metadata has description/severity/thresholds, but none of the six rules defines a workflow resolution or waiver policy. `QUALITY_FAMILY_SCHEMAS.md` says BLOCKER must be fixed before render consideration, and CRITICAL before render. ATTEMPT_001 explicitly requires3short-tier attempts; ABSURD_PHYSICS is not an excluded profile.

The master architecture does mention “Manual override with audit trail”, a human_overrides table and an override-rule endpoint sketch. No corresponding implemented runtime or rule-specific eligibility/authority policy was found. That sketch does not establish which BLOCKER can be waived or how an override can supersede the later zero-blocker/zero-critical render queue gate. PRODUCIBILITY_003's human-review description conflicts with the general CRITICAL gate. An explicit governing decision is needed; inventing that authority in code would violate the request.

## Audit of all six failures

All canonical results below remain FAIL in immutable Ruleset1.10 evidence. The classifications are **audit proposals**, not an active authority or relabelled rule result.

| Rule / severity | Original purpose / actual evidence | Confirmed text defect? / text repair | Visual evidence / exception / hard-block status | Earliest resolution |
|---|---|---|---|---|
| BEAT_004 / CRITICAL | Prevent one unchanged visual state occupying>30%. Beat5–10s is assigned one action-derived state for5/15=33.33%; source explicitly says notes multiply2→4→8, covering arms, legs, face. | Static-state measurement is unsupported by this coarse representation. EVALUATOR_DEFECT; editing the approved prompt is not justified by this finding. Substate durations are UNKNOWN. | Rendering can verify the planned progression; visual success is not proven. No documented rule waiver. Current failure remains enforced, but it is not established as a genuine non-waivable source defect. | Evaluator correction/re-evaluation at Step5; visual verification Step7/QA. |
| ATTEMPT_001 / BLOCKER | Require minimum3active attempts for15s/profile. Exact source establishes PEEL2–5s and PULL5–10s; count2. | Confirmed policy violation. Adding an event could meet it, but changes the immutable approved story and is forbidden. POLICY_EXCEPTION_REQUIRED if keeping this story for rendering. | Visual evidence cannot fabricate a third textual attempt. No applicable documented exception. Current gate is mandatory/fails closed; universal non-waivability versus an explicit exception is an architecture decision, not something inferred from a generic override sketch. | Step6 architecture decision; no automatic text repair. |
| PRODUCIBILITY_003 / CRITICAL | Thin notes and face contact trigger FACE_CONTACT/THIN_OBJECT. Rule describes a mid-tier human-review trigger, not an outright render block. | Confirmed production risk, not confirmed output failure. Text could reduce contact/object complexity, but may alter required story events. PRODUCTION_RISK_REVIEW. | Visual tests may reduce uncertainty. Human review is documented; effective risk-acceptance authority against the general zero-CRITICAL render gate is not implemented/specified. Not inherently a non-waivable defect under its own description; currently still gated. | Step6 risk review, Step7 visual evidence; explicit governance to define effective acceptance. |
| CONTINUOUS_ACTION_MOMENTUM / CRITICAL | Avoid inactive reaction/reset gaps and excessive aftermath. Current passive0s, attempt gap0s; finalAftermath3s counts12–15s sneeze/scatter/landing merely because the beat is not an attempt. | EVALUATOR_DEFECT: active payoff is not demonstrated passive aftermath. No supported shortening or extra attempt follows. | Visual quality remains unverified. No documented waiver. Existing result remains, but the claimed inactive ending is not confirmed. | Evaluator correction/re-evaluation Step5; visual timing validation later. |
| INSTANT_VISUAL_ABSURDITY_GATE / BLOCKER | Verify a large, history-free wrongness at framezero with engaged character. Current details identify missingEvidence/failureBasis=EVIDENCE_INCOMPLETE_FAILURE. | Missing evidence, not a verified bad frame. EVIDENCE_REQUIRED; wording cannot supply actual visual proof. | Step7 first-frame evidence required. No waiver/pending-as-PASS authority. A verified FAIL would be a different, substantive hard failure. | Step7 prepared/uploaded frame and verified assessment. |
| ENGINE_SILHOUETTE_DUPLICATE / BLOCKER | Reject a known-winner engine/silhouette duplicate. Current failure is absent first/final silhouette comparison evidence, not an observed duplicate. | EVIDENCE_REQUIRED; no confirmed duplicate or justified text rewrite. | Verified comparison required. No waiver/pending-as-PASS authority. A verified duplicate must remain blocking under current policy. | Step7 evidence planning/comparison; any later required output comparison at its proper stage. |

Exact canonical messages, governed descriptions, source quotes and spans are in deterministic-audit.json. No source spans or intra-beat timings were invented.

## Confirmed measurement defects; no fixes activated

BEAT_004 uses `visualStateId` derived from the first action string and assigns the whole beat duration to it. It cannot represent the source's2→4→8 transformations within that beat. This does not prove a static5s hold. A governed correction should preserve explicit source progression, evaluate timed substates only when supported, otherwise keep static-duration measurement UNKNOWN. Arbitrarily splitting into equal timestamps or converting it to PASS would fabricate evidence.

MOMENTUM sums every non-attempt beat at/after finalPayoff.startsAt into finalAftermathSeconds. The read-only control replaces the active sneeze/scatter ending with a synthetic still hold and the metric remains3s in both. Active payoff and passive aftermath are conflated. A future generic correction must identify actual payoff motion and separately evidenced holds, without treating all non-attempts as inactive. Existing thresholds must remain unchanged.

These corrections would change canonical semantics and therefore need a new immutable ruleset, not a1.10 hot edit. Per the request's architecture-stop condition, they were diagnosed and specified, not implemented or deployed in this audit. No corrected score is claimed.

## Actual workflow and browser verification

A significant correction to the prior report: **Step7 evidence preparation is already reachable without recording no-repair approval.** The prior description overstated the navigation deadlock.

In the deployed real browser:

1. Loaded Content10/Prompt10 Step6. “Text repair required” and disabled no-repair checkbox/button are visible.
2. Clicked the actual “7 Render Preparation” navigation button. The page opens with exact analysis05726ece-caaf-483a-a0af-d93e91a76c88 and immutable prompt context.
3. Opened Character References. Mimi is identified, no project reference assets exist, upload/import controls are available. No upload/import/association was performed.
4. Opened First Frame. Local specification and image-upload controls exist. Generate Start Frame is disabled; missing verified reference remains unresolved. No generation or specification save occurred.
5. Opened Final Review. Outstanding requirements and revalidation actions are shown; no authorization or render was submitted.

Screenshots and DOM snapshots accompany this report. Entering these tabs uses read-only loading. Merely navigating to Step7 does not approve Step6 or grant F8 authorization. Existing first-frame generation has separate consent/cost/eligibility checks and was not invoked.

## Eligible/ineligible operations now

- Allowed: inspect current analysis, keep Original as a recommendation, open Step7, inspect reference catalog, prepare/upload evidence through the existing explicit services and their validation. No paid permission is implied.
- Ineligible: NO_TEXT_REPAIR_JUSTIFIED for this run under current guards; effective acceptance/waiver of ATTEMPT_001; actual video rendering with missing inputs or failed canonical gates.
- Conditional: production-risk acknowledgement is described conceptually but is not an implemented exception to canonical render gates. No backend success or operator authority is fabricated.
- Eventual render: exact F8 AUTHORIZED plus queue admission are both required. Neither reference binding nor text acceptance alone is sufficient.

The four-operation separation and proposed authoritative typed contract are fully specified in ADR-DRAFT.md. **It is a proposal, not an updated production state machine.** After the governing choices are made, frontend controls and backend command validation must consume one server policy result and recompute eligibility on POST. Until then, existing checks remain unchanged.

## Verification results and requested scenario coverage

Fresh runs:17ML/F8 tests passed;5backend no-repair tests passed,3optional live/mock tests skipped;24render-queue policy tests passed;93frontend Step6/Step7 tests passed. Read-only saved-run reproduction and both evaluator controls passed. Current official analysis canonical fields exactly match the prior saved1.10 snapshot.

| Requested scenario | What is verified now |
|---|---|
| Zero FAIL | Existing explicit no-repair success/idempotency tests pass. |
| Evidence-only findings | Existing F8 pending behavior passes; new typed no-repair eligibility not implemented or claimed. |
| Actionable text defect | Current no-repair rejection tests pass. |
| Risk acknowledgement | Descriptive governance found; new typed effective acceptance awaits ADR, not falsely tested as allowed. |
| Non-waivable blocker | Queue nonzero blocker/critical rejection passes; generic waiver authority not invented. |
| Mixed text/evidence | Existing failures stay blocked; typed transition matrix still awaits approved policy. |
| Stale analysis/ruleset | Analysis/binding staleness rejection tests pass; new independent workflow-policy/ruleset invalidation contract is proposed only. |
| Missing operator confirmation | Backend rejection tests pass. |
| Missing Mimi reference | ML and frontend tests pass; actual browser shows missing asset and accessible evidence preparation. |
| Missing start frame | ML and frontend tests preserve render blocking. |
| Evidence collection with render blocked | Actual Step6→Step7 reference/frame navigation works; upload/prepare routing regression tests pass. No operator approval was submitted or fabricated. |
| Eventual F8 authorization | Existing deterministic complete-evidence ML tests and valid render-evidence queue fixtures pass. This does not establish this actual run as authorized while its canonical failures persist. |

This is **not** a claim that all12scenarios passed for a newly implemented typed contract. No such contract has been activated. End-to-end policy acceptance remains incomplete pending the architectural decision.

## Current records, next action and constraints

Authoritative analysis remains **05726ece-caaf-483a-a0af-d93e91a76c88**, Ruleset1.10,84.20833333333334/B. Original/A/B unchanged; recommendationKEEP_ORIGINAL. Historical records, Prompt10 and approved story unchanged. No new persisted production evaluation, operator approval, provider call, candidate, image/video generation, publishing, direct production SQL mutation, commit/push or deployment occurred.

A legitimate immediate next action already exists: inspect/associate an independently verified Mimi reference and prepare appropriate frame evidence in Step7. Under the current task's constraints, no generation or user approval is executed automatically. Final render remains blocked by missing verified reference/start frame and the independent canonical/validation requirements. Resolving text acceptance and any ATTEMPT_001 exception requires the explicit ADR decisions; scores or UI navigation cannot substitute for them.
