# V3 Phase 1 — Canonical grade feasibility audit

Completed before routing changes, 2026-10-15. Source: live saved analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, Content 10 / Prompt 10 v1; Ruleset 1.11. Read-only evidence: `output/verification/adaptive-creative-v3/baseline.json`.

## Actual grade and aggregation

`app/workflow/review.py::_canonical_rule_evaluation`: A >=92, B >=80, C >=60, otherwise F. No authoritative A+ grade exists. Render readiness independently also requires >=92 and no BLOCKER/CRITICAL findings; matching thresholds do not make these contracts interchangeable.

`RuleEngine._calculate_family_scores`: evaluated PASS earns 100 only when its returned configured severity is PASS; other PASS earns 85. FAIL earns 0/40/70 for BLOCKER/CRITICAL/other severity. UNKNOWN, NOT_APPLICABLE, service errors and `failureBasis=EVIDENCE_INCOMPLETE` are excluded, never treated as PASS. Family score is the mean of eligible rows. Overall is the family-weighted mean, normalized over families having numeric scores, including PARTIAL families (the current function docstring says fully evaluated, but executable code does not require full coverage). Mimi's denominator is 0.96. Weight catalog total need not equal 1 because normalization is explicit.

## Every current numeric loss

Loss is relative to 100, with the *current* eligible rows and denominator. It is not a promise of recoverable points.

| Rule | Family weight / scored rows | Current row points | Overall loss | Classification / evidence |
|---|---:|---:|---:|---|
| ATTEMPT_001 | .12 / 3 | 0 | 4.166666667 | PROTECTED_STORY_CONFLICT; two source-bound attempts, required three. GOVERNED_POLICY_DECISION_REQUIRED for admission only; exception preserves FAIL and score. |
| MINI_STORY_LOCK | .12 / 3 | 85 | .625 | NOT_CURRENTLY_ATTAINABLE: successful evaluator always returns BLOCKER/PASS, so 85; no prompt edit changes that branch to 100. |
| NOVELTY_001 | .14 / 5 | 85 | .4375 | CREATIVE_RECONSTRUCTION_REPAIRABLE only with grounded progression timing; current 5–10s gap. Existing beat windows are protected; invented sub-beat timings are disallowed. No verified repair currently supplied. |
| PAYOFF_002 | .11 / 5 | 85 | .34375 | PROTECTED_STORY_CONFLICT: no approved fake win. Optional bonus, not a universal creative requirement. |
| BEAT_DENSITY_RULE | .11 / 5 | 85 | .34375 | NOT_CURRENTLY_ATTAINABLE: successful evaluator returns CRITICAL/PASS for the valid five-beat plan. |
| ESCALATION_004 | .10 / 2 | 85 | .78125 | PROTECTED_STORY_CONFLICT: payoff at 12s; earlier timing would change protected source windows. |
| PAYOFF_004 | .09 / 3 | 85 | .46875 | EVIDENCE_REQUIRED / CREATIVE_RECONSTRUCTION_REPAIRABLE: final salience ties earlier peak; stronger source-bound staging may support a different judgment, text alone cannot establish rendered salience. |
| PRODUCIBILITY_003 | .10 / 3 | 40 | 2.083333333 | EVALUATOR_DEFECT risk: substring `stick` matches sticky notes and `face` can match surface; inspect exact matches before any correction. Sticky-note interaction itself remains a real execution risk. Removing source words to game the parser is prohibited. No scoring changes authorized in V3. |
| GOAL_VISIBLE_EARLY | .12 / 2 | 85 | .9375 | NOT_CURRENTLY_ATTAINABLE: successful evaluator always returns CRITICAL/PASS. |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | .09 / 1 | 85 | 1.40625 | NOT_CURRENTLY_ATTAINABLE: successful evaluator always returns BLOCKER/PASS, including split/return-loop branches. |

Loss sum = 11.59375; score = **88.40625/B**, matching the persisted live result.

## Ceiling and unavailable evidence

With protected events/windows and current available evidence/classification held fixed, even optimistically granting the two potentially changeable NOVELTY_001 and PAYOFF_004 rows 100 gives **89.3125/B**. This is an optimistic conditional bound, not an achieved candidate score. Even additionally removing the entire fragile-interaction penalty (which V3 must not do) gives **91.395833333/B**. Thus no currently justified prompt-only A path exists. This is not a universal bound after acquiring new independent evidence: newly evaluated rows/families change denominators and scores and must be recomputed, never assumed PASS.

Excluded visual blockers: INSTANT_VISUAL_ABSURDITY_GATE (five missing first-frame measures), ENGINE_SILHOUETTE_DUPLICATE (no reference comparison). Eleven UNKNOWN rows include BEAT_004 substate timing, CONSISTENCY_001, HOOK_003/004, ATTEMPT_002, PAYOFF_003, CONCEPT_007/008, GOAL_001, PERFORMANCE_001 and GENERATION_EXECUTABLE_ATTEMPTS. These require their actual semantic/visual/source timing evidence. Seven NA rows confer no bonus. A number alone cannot establish enough applicable quality evidence or render authorization.

## Decision before generation

Mimi: **TARGET_BLOCKED_BY_STORY_CONSTRAINT**, with additional evidence and evaluator-policy dependencies. No provider dispatch is justified against the current canonical A target. Resolve the exact evidence/architecture issues through separately governed work and a new official analysis before reconsidering. ATTEMPT_COUNT_EXCEPTION_V1 cannot repair the numeric grade. Do not generate a third attempt or alter weights/severity/thresholds.

A separate pre-render rubric, if desired, requires an ADR with a fixed scope, blinded approved-source golden cases, independent human quality judgments, calibrated thresholds, unknown-evidence handling, regression tests and explicit architecture approval. It must retain the canonical score/grade and F8 separately. **No new grade or scoring semantics are activated by this task.**
