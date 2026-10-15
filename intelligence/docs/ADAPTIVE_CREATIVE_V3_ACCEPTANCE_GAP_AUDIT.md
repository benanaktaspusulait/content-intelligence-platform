# Adaptive Creative Optimization V3 — B→A acceptance gap audit

Date: 2026-10-15  
Status: **CREATIVE_QUALITY_ARCHITECTURE_DECISION_REQUIRED**  
Scope: read-only audit of the deployed V3 workflow, Ruleset 1.11, Content 10 / immutable Prompt 10 v1, and the saved golden calibration inventory. No provider request, candidate generation, approval, prompt/story mutation, render, or database write was performed.

## Decision

The canonical letter is not an authoritative measure of pre-render creative prompt quality. It is a canonical rule-compliance score, with its own evidence and applicability semantics. A separate, versioned and calibrated creative prompt quality contract is justified. The proposed `CREATIVE_PROMPT_QUALITY_V1` is in [the inactive ADR](ADR_CREATIVE_PROMPT_QUALITY_V1_DRAFT.md); it is not active.

No eligible independently evidenced B→A golden case exists in the inspected inventory. **`NO_ELIGIBLE_B_TO_A_GOLDEN_CASE`**. Accordingly, no full B→A product acceptance was run and no candidate or source-fidelity PASS was manufactured.

## 1. Creative quality and canonical compliance are different contracts

Canonical Ruleset 1.11 grades the weighted canonical rule score in `intelligence/ml-service/app/workflow/review.py`: A ≥92, B ≥80, C ≥60, otherwise F. A+ is undefined. Rule-family aggregation and Mimi’s exact score losses are recorded in [the V3 grade audit](ADAPTIVE_CREATIVE_OPTIMIZATION_V3_GRADE_AUDIT.md). Ruleset 1.11 returned **88.40625/B** for saved analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`.

The separately exposed pre-render `creative_grade` in `intelligence/ml-service/app/assessment/pre_render_assessment.py::_creative_grade` is also not a calibrated creative-quality grade. It derives a letter from canonical evaluated failures and configured severity: blocker FAIL→F, critical FAIL→D, other FAIL→C, a warning-severity evaluated rule→B, otherwise A. It is not based on the six V2 dimensions, has no calibration set, and does not establish independent source fidelity, visual success, or audience response. Either existing letter can therefore be misread if presented as “creative quality.”

| V2 dimension (`creative-quality-v2.json`) | Intrinsic prompt creativity | Source fidelity | Production complexity / feasibility | Requires image/video evidence for full judgment | Architectural compliance | Render admission |
|---|---|---|---|---|---|---|
| `SCROLL_STOP_VISUAL_PROMISE` | Yes: proposed opening visual interest | Must preserve approved premise; preservation alone is not a quality PASS | Text can state an executable opening | Actual first-frame legibility, anomaly visibility and viewer-facing composition | Protected opening/story constraints still apply | First-frame evidence and independent render gates remain separate |
| `CAUSAL_PROGRESSION` | Yes: legible action→consequence progression | Must preserve source event order and causal premise | Text can describe planned transitions | Rendered cause/effect readability and continuity | Canonical beat/event contracts apply independently | Visual evidence may be an admission requirement |
| `VISUAL_STORYTELLING` | Yes: information conveyed through visible action/state | Source-faithful expression is required | Text can propose staging | Actual state readability, continuity, identity and visual adherence | Protected character/mechanic/ending contracts | Character reference and accepted frame are separate gates |
| `PRODUCTION_EXECUTABILITY` | No; this is feasibility/risk, not intrinsic creativity | Must remain faithful while executable | Yes: action load, timing, continuity and generator limits | Actual generator adherence and artifact risk need output evidence | Generator, duration and profile bindings are mandatory | Independent execution checks and unresolved risk controls remain |
| `ENDING_REPLAY` | Yes: textual ending construction may invite a loop/replay | Ending must remain the approved ending | Text can specify the final transition | Actual visual loop and audience replay response | Ending is protected | Render authorization is separate; replay response needs audience data |
| `DISTINCTIVE_CREATIVE_VALUE` | Yes: distinctiveness of the execution/premise | Cannot gain distinctiveness by changing protected story | Feasibility is a separate judgment | Visual distinctiveness in the rendered result cannot be inferred from text | Identity/event/rule constraints still apply | No render permission follows from a text judgment |

These six labels are declared in `intelligence/data/workflow/creative-quality-v2.json` with authority `QUALITATIVE_TEXT_EVIDENCE_ONLY`. That contract explicitly reserves `MATERIAL_IMPROVEMENT_SUPPORTED`; the text-only implementation never emits it. It also keeps semantic source fidelity `UNKNOWN` without independent evidence, visual benefit `UNVERIFIED` without visual evidence, and audience benefit `UNMEASURED` without audience evidence. The six dimensions are therefore not six current numeric metrics or an existing A/A+ rubric.

### Current Mimi case: attempt rule and missing visuals

- Saved analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`: Content 10, Prompt 10 v1, Ruleset 1.11, **88.40625/B**.
- The exact current-evidence score audit attributes **4.166666667 overall points** of loss to `ATTEMPT_001`: two source-bound attempts versus the applicable minimum of three. The source attempt count and protected event/timing constraints cannot be changed by relabeling shots or inventing sub-beats. No third attempt is authorized.
- `INSTANT_VISUAL_ABSURDITY_GATE` lacks five first-frame measures; `ENGINE_SILHOUETTE_DUPLICATE` lacks a reference comparison. These are evidence/admission gaps. UNKNOWN and evidence-incomplete results are excluded from canonical numeric aggregation, not silently made PASS or FAIL. They do not themselves subtract numeric points in this saved result, but they prevent a complete visual judgment and keep render admission blocked.
- Under the current eligible rows, denominator and protected-source assumptions, granting only the two potentially changeable `NOVELTY_001` and `PAYOFF_004` rows 100 yields a conditional ceiling of **89.3125/B**. This is not a universal ceiling if genuinely new evidence changes the evaluated denominator. It proves no currently justified prompt-only path to canonical A≥92 under the saved evidence.
- Pre-render creative quality, canonical score, production-risk acknowledgement, text acceptance, source-fidelity evidence, and F8/render authorization must remain separate decisions.

## 2. Golden inventory and B→A eligibility

Read-only production inventory snapshot: `output/verification/creative-quality-contract-audit/saved-evidence-inventory.json`; the pre-audit integrity fingerprint is `output/verification/creative-quality-contract-audit/integrity-before.json`. This task made no database writes. Inventory counts: one PromptVersion (ID 10, Content 10, v1); 75 workflow events; one prompt creative provenance record; four synthetic `reference_prompts`; **zero** `quality_validations`; **zero** `governed_rule_reviews`.

The four reference prompts are threshold fixtures (three failure cases and one Mimi progression case with expected score 94). They do not form approved, independently reviewed original/candidate pairs with source revision, candidate fingerprint, intervention, Ruleset 1.11 evidence and full application-pipeline provenance. They cannot serve as B→A acceptance.

The nine frozen `pompom-golden-v1` cases are fixed-source, human-reviewed structural assessment assets, but their persisted baselines are **Ruleset 1.7 / `FROZEN_DETERMINISTIC`**, not current Ruleset 1.11 provider-authored candidate improvements. They contain no independently reviewed candidate intervention bound to a current prompt fingerprint. The Sticky Ball case has canonical **85/B** and a separate pre-render `creative_grade=A` with partial evidence; it is not a B→A improvement and demonstrates why the grades must not be conflated. The other cases are failure/timeout baselines. The Mimi golden story is not the immutable Prompt 10 source/revision and is not a candidate improvement for this task.

The six saved analyses for Content 10 / Prompt 10 are historical evaluations, not a golden candidate pair: Rulesets 1.7 (85/B twice), 1.8 (82.80208333333336/B), 1.9 (82.80208333333336/B), 1.10 (84.20833333333334/B), and 1.11 (88.40625000000001/B). Historical records remain untouched.

Thus no inspected case satisfies all required elements: approved original story, actual B original production prompt, material source-faithful intervention, sufficient independent evidence, and attainable A under the governing contract. **`NO_ELIGIBLE_B_TO_A_GOLDEN_CASE`**. Per the acceptance requirement, stop the acceptance claim here: no synthetic 92-point output, seeded grade, artificial candidate, or full pipeline claim is substituted.

## 3. Independent source-fidelity evidence

Current V2 reconstruction preserves protected narrative/source spans but reports `semanticFidelity=UNKNOWN`; that is the correct result without a separate verifier. The generator’s assertion, compiler provenance, source-span preservation, canonical score, or candidate length cannot certify the semantic fidelity of that same generated candidate.

Available systems do not close the evidence gap:

- `QualityValidationEntity` / `ValidationEvidenceService` records are render validation evidence, not an implemented independent story-fidelity judgment. The saved production inventory has no validation records.
- Story approval workflow events record approvals of a story revision; they do not bind an independent review to an exact production-prompt/candidate fingerprint, analysis, ruleset, and intervention. No persisted `STORY_REVIEW` event was found in the 75-event inventory.
- Frozen Golden truth is useful independently reviewed structural truth for its own frozen source asset, but does not attest a newly generated candidate or connect it to Prompt 10’s immutable approved story.
- `governed_rule_reviews` handles governed rule exceptions, not candidate fidelity; no saved records exist.

No existing authoritative independent candidate-fidelity producer with the required binding was found. Therefore no producer/consumer binding was implemented and Mimi source semantic fidelity remains **UNKNOWN**. A future evidence record must bind original story/revision, exact prompt and candidate fingerprint, source analysis and ruleset, evaluated intervention, verifier identity/method and provenance, decision rationale, and expiry/revalidation policy. The trust model and verifier authority need architecture approval before implementation.

## 4. Full pipeline and readiness status

A legitimate full B→A acceptance cannot be executed with this inventory. The required original-to-diagnosis-to-provider reconstruction-to-independent fidelity-to-canonical evaluation-to-materiality-to-critic-to-routing-to-durable-evidence chain would start from an ineligible case and has no independent fidelity producer. No real or mocked candidate was run for this audit; no false end-to-end claim is made.

| Achievement | Audit result | Evidence / limitation |
|---|---|---|
| `SYSTEM_ROUTING_READY` | **READY for the previously verified safe routing contract** | Prior V3 tests/deployment support routing, authorization, budget and stopping behavior. This is a routing result only, not product-quality acceptance. |
| `SOURCE_FIDELITY_EVIDENCE_READY` | **NO** | Semantic source fidelity is UNKNOWN; no independent producer and no bound production validation record. |
| `B_TO_A_GOLDEN_ACCEPTED` | **NO** | `NO_ELIGIBLE_B_TO_A_GOLDEN_CASE`; no full-pipeline qualifying case exists. |
| `REAL_MODEL_CREATIVE_EFFECTIVENESS_VERIFIED` | **NO** | This audit made no provider call; prior real tests do not meet this task’s complete independent fidelity and B→A acceptance contract. |

## 5. Optimizer target states

The current safe-stop behavior should remain in force until an authorized target policy exists. The pre-generation gate must expose two separate questions: “is a meaningful source-faithful creative opportunity supported?” and “can this current canonical result attain A under current evidence and protected constraints?” A negative answer to the second must not be displayed as proof that no creative opportunity exists.

Proposed distinct diagnostic states (not activated):

- `CREATIVE_OPTIMIZATION_POTENTIALLY_WORTHWHILE` — a grounded opportunity exists; it is not provider authorization.
- `CANONICAL_A_UNATTAINABLE_WITH_CURRENT_EVIDENCE` — current evidence/protected constraints cannot support canonical A; retain the exact safe-stop until an approved target policy says what action is allowed.
- `SOURCE_STORY_REVISION_REQUIRES_APPROVAL` — the desired change crosses a protected source boundary.
- `PROMPT_CREATIVE_GRADE_TARGET_NOT_YET_ATTAINED` — the selected, versioned target has not been independently qualified.
- `RENDER_AUTHORIZATION_BLOCKED` — independent visual, risk, identity, source and F8 conditions are not all satisfied.

These statuses must never authorize a paid request, imply source-fidelity PASS, change canonical scores, or imply render permission. `CREATIVE_PROMPT_QUALITY_V1` must be approved before any new creative grade target is active.

## Recommended architecture decision and remaining provider-test conditions

Review and approve or reject [ADR `CREATIVE_PROMPT_QUALITY_V1`](ADR_CREATIVE_PROMPT_QUALITY_V1_DRAFT.md) before implementing a new grade. The proposal requires calibrated good/weak approved examples, a current independent source-fidelity verifier, explicit dimension evidence and unknown handling, blinded reviewer calibration, false-positive/false-negative tests, disagreement handling, held-out regression and a versioned threshold. After that, obtain a legitimately improvable approved B source, run the real application pipeline with isolated persistence and mocked providers first, then separately authorize any real provider experiment. Any later real-provider A/A+ test needs fresh, bounded authorization, complete binding and durable evidence; provider opinion alone cannot qualify a result.

**Final status: `CREATIVE_QUALITY_ARCHITECTURE_DECISION_REQUIRED`.**
