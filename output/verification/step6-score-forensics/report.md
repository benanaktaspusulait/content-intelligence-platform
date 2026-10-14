# Step 6 score forensics — completed

Decision: **SCORING_DEFECT_FOUND** (reproducible applicability inconsistency and incomplete inherited ruleset loading). Numeric 85 is reproduced exactly under the currently deployed configuration. No scoring correction has been applied; historical records remain unchanged.

## Exact arithmetic

The actual path is `workflow/review.py:_run_canonical_evaluation` → `parse_prompt` → `RuleEngine.evaluate` → `_generate_report` → `_calculate_family_scores` → `_calculate_overall_score`. It reparses each prompt and uses the default ruleset 1.7. It does not consume F8 authorization as a numeric scoring input.

There is no starting score, additive bonus, explicit overall cap, or floor. Evaluated PASS/FAIL rows are scored first, then averaged within each family, then normalized by the weights of non-null families.

| Rule | Configured severity | Outcome | Numeric contribution | Family weight |
|---|---|---|---:|---:|
| MINI_STORY_LOCK | BLOCKER | PASS | 85 | 0.12 |
| GOAL_VISIBLE_EARLY | CRITICAL | PASS | 85 | 0.12 |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | BLOCKER | PASS | 85 | 0.09 |
| BEAT_DENSITY_RULE | CRITICAL | PASS | 85 | 0.11 |
| CONTINUATION_LOCK | BLOCKER | NOT_APPLICABLE | excluded | same generation family |
| STUBBORN_RETURN_LOOP | BLOCKER | UNKNOWN | excluded | same progression family |
| STUBBORN_RETURN_HOOK | CRITICAL | NOT_APPLICABLE | excluded | same hook family |
| STUBBORN_RETURN_PAYOFF | CRITICAL | NOT_APPLICABLE | excluded | 0.09, null family excluded |

`(85×0.12 + 85×0.12 + 85×0.09 + 85×0.11) / (0.12+0.12+0.09+0.11) = 37.4/0.44 = 85`.

`rule_engine.py:361–395`: PASS is 100 only when configured severity is PASS; every other severity gives 85. FAIL gives BLOCKER 0, CRITICAL 40, otherwise 70. UNKNOWN, NOT_APPLICABLE, NOT_EVALUATED, SERVICE_ERROR and evidence-gap rows are excluded from the numeric denominator. An entirely unscored family is null, not zero. SERVICE_ERROR separately forces service-error status. `rule_engine.py:439–451` normalizes family weights; `quality/family_weights.py` supplies them.

`workflow/review.py:936–940`: A >=92, B >=80, C >=60, F <60; null score has null grade. 90 would still be B. Render-ready status separately requires >=92 and no failed blocker/critical; F8 authorization is another independent gate.

The missing 15 points are the hardcoded PASS valuation, not a penalty for UNKNOWN, production complexity, missing Mimi reference, or missing start frame. This is verified behavior, not a claim that creative quality is exactly 85%.

## Applicability defect and proposed minimal correction

All three real IRs contain the explicit source-supported rule “each pull doubles the number of sticky notes”. None provides autonomous return, a safe/danger boundary, or recurrent return. Only CHARACTER_INTERVENTION and NO_DEAD_RESET are true. `engine_profile_evidence` gives LOW confidence, DEFAULT profile, inactive, but `candidate_only=True` because line 783 uses `bool(score and not active)` for any nonzero signal count. `_evaluate_stubborn_return_loop` at `rule_engine.py:3334–3344` consequently returns UNKNOWN.

For those same IRs, the existing generic `specialized_applicability_evidence` at `canonical_evidence.py:563–638` establishes STICKY_DEFORMATION outside the stubborn-return domain and returns NOT_APPLICABLE. The ruleset policy explicitly keeps MEDIUM inference candidate-only; it does not justify treating any LOW generic signal as a specialized-domain candidate. This is a diagnostic applicability inconsistency, not a 15-point deduction. No exception for Mimi is needed.

Proposed smallest correction, **not applied**: in the inferred engine-profile constructor, change `bool(score and not active)` to `confidence == "MEDIUM" and not active`. This makes LOW/DEFAULT evidence non-candidate while preserving explicit valid HIGH activation, inferred HIGH activation, and existing MEDIUM uncertain-return behavior. Regression assertions reproduce the current low-confidence mismatch and verify the proposed predicate against real three inputs and positive HIGH/MEDIUM spoon fixtures. Do not map all UNKNOWN results to PASS or NOT_APPLICABLE globally.

A second reproducible configuration problem was discovered: `_load_ruleset` at `rule_engine.py:195–210` loads only the immediate base YAML. 1.7 extends 1.6, and 1.6 extends 1.5, but the deployed 1.7 engine contains only five 1.6 rules plus three 1.7 rules; 1.5 ancestors are omitted. The method advertises an additive immutable base, yet inheritance is not recursive. Thus the current Step 5 score is an eight-rule structural score, not the complete inherited creative ruleset. Proposed correction, **not applied**: resolve the extends chain recursively with cycle/missing-file checks, then append child rules while preserving immutable YAML and explicit override semantics. A future correction requires focused compatibility/semantic-provider isolation tests and an explicitly authorized new evaluation, never rewriting saved results. See inheritance-proof.json for exact configured/omitted IDs.

Neither proposal should be silently deployed as part of a read-only forensic request. The PASS-to-85 policy is existing documented behavior; changing PASS to 100 just to reach A is not proposed.

## Evidence ceiling and sensitivity

Under the deployed eight-rule configuration every rule has BLOCKER or CRITICAL severity. Every possible scored PASS is <=85, and each FAIL is <=85. An average of these values cannot exceed85. Algebra-only upper-bound test with all eight PASS gives85; that test does not assert fabricated story or rendered evidence. Current genuine saved inputs already attain the maximum85. No valid source-faithful text improvement, reference, accepted frame, or rendered video can produce90+ through this eight-rule score without a configuration/policy correction. UNKNOWN removal alone also leaves85.

- Prompt text/source-plan: parser changes source evidence and staging; relevant outcome changes can alter score, but currently passed structural gates are saturated.
- Verified character reference: resolves an F8 reference authorization requirement; not used by these eight numeric rules.
- Accepted start frame: resolves an execution-input authorization requirement; not used by these eight numeric rules.
- Rendered video: can establish actual visual execution and audience claims only with the appropriate evidence; this pre-render eight-rule function does not grant numerical bonuses for it.

Baseline, A and B were rerun in the deployed ML container with the same ruleset and semantic providers disabled: exact saved scores/grades/outcome IDs reproduced. All remain four PASS, zero FAIL, one UNKNOWN, three NOT_APPLICABLE.

A makes cabinet/finger simultaneous framing explicit and static. Parsed opening source action/goal/attempt evidence changes; active intervention count rises2→3 and strategy-change count1→2. It also exposes a deterministic extraction weakness: “her finger” can absorb the following Mimi/location clause in the source surface value. No visual claim is promoted to proven readability.

B adds continuous peel→two-hands focus and ordered two→four→eight holds. Parsed source quotes/actions/physical-rule spans change; durations remain2/3/5/2/3 seconds, five major beats, five state transitions, same ending, manageable temporal load. Neither candidate changes a canonical rule outcome. Actual creative improvement stays a hypothesis. Complete machine-readable field differences are in input-differences.json.

Controlled provider-free counterfactual: delay the source opening beat/goal to3 seconds → GOAL_VISIBLE_EARLY FAIL, hook family40, score72.7272727. Restore real source timing0–2 seconds → PASS, score85. This demonstrates sensitivity to the relevant gate; it is not a proposed story edit. Remove available goal evidence → score49.5454545, demonstrating that absent evidence is not promoted to PASS. No new candidate or production evaluation was persisted.

## At most three actual execution opportunities

1. Beat1, 0–2s: wrong attachment target may be visually unclear. Candidate A’s simultaneous cabinet/finger staging is an appropriate source-faithful hypothesis. Measure with an operator-reviewed first frame and eventual opening-video evidence; canonical score delta currently0, actual readability UNKNOWN until visual evidence.
2. Beats2–3, 2–10s: hand separation and doubling may be hard to track. Candidate B’s continuous action→consequence view and source-backed two/four/eight exposure are appropriate hypotheses. Measure actual note-state continuity and legible hand/note placement in visual/video QA. Current score delta0; text cannot verify generator success.
3. Beat5, 12–15s: sneeze, note transfer, relief and messy cabinet must remain readable together. Preserve those source events and the ending; review the final held cabinet/character composition and transfer continuity. Source text already protects the ending; visual execution requires video evidence, no score increase is derivable.

Do not add comedy, a seamless loop, new story actions, or a returning-object mechanic.

## Decision and exact next step

**SCORING_DEFECT_FOUND**. Current arithmetic is correct for the deployed eight rules; LOW return-loop applicability and omitted recursive ancestry are implementation issues. A higher score cannot be promised after correction. First review the two narrowly described corrections and their regressions, then authorize a separate implementation/revalidation task if desired. Continue Step7 only after resolving the verified Mimi-reference and accepted-start-frame requirements; these resolve render authorization, not the missing15. No generation or render authorization was granted here.

Focused deterministic tests:12 passed. Existing canonical/source/F8 regressions:61 passed. Read-only deployed-container recomputation:3/3 exact scores and rule outcomes reproduced. No paid provider calls, candidate generation, production evaluation persistence, story/prompt mutation, image/video generation, history rewrite, commit or push.

Final status: **SCORE_DIAGNOSIS_COMPLETE**.

Reproduction from `intelligence/ml-service`: `POMPOM_DATA_ROOT=../data POMPOM_SEMANTIC_ENABLED=false .venv/bin/pytest -q ../../output/verification/step6-score-forensics/test_score_forensics.py`. Deployed recomputation script is reproduce.py; set PYTHONPATH and POMPOM_DATA_ROOT for that runtime. Saved analysis and current comparison payloads compared byte-for-byte/structurally before and after and remained unchanged.
