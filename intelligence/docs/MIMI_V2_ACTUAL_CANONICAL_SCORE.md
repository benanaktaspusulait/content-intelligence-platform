ORIGINAL_SCORE: 88.40625
ORIGINAL_GRADE: B

V2_SCORE: 80.25520833333334
V2_GRADE: B

SCORE_DELTA: -8.151041666666671
A_THRESHOLD: 92
A_ACHIEVED: NO

# Mimi V2 — actual canonical Ruleset 1.11 execution

Executed 2026-10-16. **The actual evaluator scores V2 at 80.25520833333334/B, down 8.151041666666671 points from the reproduced original.** This is an executed result, not an estimate or the previous conditional ceiling. The rule engine reports BLOCKED for both inputs, independently of their numeric B grade.

The main new loss is a reproducible extraction limitation: V2's explicit peeling and continuing-pull prose produces **zero source-bound attempts**, compared with two in the original. The resulting score must be retained, but it is not proof that the approved story suddenly contains no attempts or that a rendered V2 video is worse. No score, parser or prompt was corrected to improve this result.

## Actual invocation and control

The running production ML container was used via a separate, provider-free `docker exec -i ... python` process, with all inputs in memory and no production database access from evaluation. This is the existing offline invocation used by `tests/test_ruleset_1_11_measurements.py`: **`app.workflow.review._run_canonical_evaluation(request)`**, calling the actual production parser and **`RuleEngine.evaluate`** with **`RULESET_1.11.yaml`**. The parser policies are `ACTOR_SOURCE_BOUND_V2` and `TOKEN_MOTION_V2`; stage PRE_RENDER. This is not a mock provider, rewritten evaluator, fixture score or server-side inferred ceiling.

The immutable original was loaded through the live saved-analysis GET and parsed afresh. Its result is **88.40625000000001/B**, the native floating-point representation of 88.40625/B, exactly equal to the live saved score. The **entire JSON-normalized canonical projection** equals the historical saved projection, including all rule outcomes, severities, messages, parsed IR and density evidence. An initial stronger native-Python object assertion encountered tuple/list representation differences before serialization and stopped before V2; normalized comparison subsequently confirmed no semantic difference. No control-score mismatch was waived.

V2's exact prompt body was separately parsed afresh, using the same bound settings, canonical version and absence of verified visual/semantic evidence. No original parsed IR, attempt annotations, source spans, model judgments or score was injected into V2. The canonical offline function consumes prompt/profile/ruleset; it does not turn inherited request identifiers or source-gate claims into evidence. The original's AUTO footer remains verbatim; the authoritative profile passed to both evaluations is ABSURD_PHYSICS.

| Input | Verified fingerprint / settings |
|---|---|
| Original | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`; Content 10 / Prompt 10 version 1 |
| V2 body | `44779084f986b4a7b1b3a5d1eab9c617f2e6f518a9c5b771cab02bce446cd219`; body after `PROMPT BODY` and blank separator, trailing file newlines excluded |
| Approved story | `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`; unchanged source context |
| Shared settings | ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15s / image2video / 480p / 9:16 |
| Runtime rules YAML | SHA-256 `8222f3208b4ee70d318429d4d72d7eb1cdae56c023f18131fd8651c7954b0a97` |

Deployed review, rule engine, parser, actor-attempt extractor, canonical evidence and family-weight file hashes were verified against local source, without modifying them. A network-denial guard surrounded actual evaluation: **zero network connection attempts**. The existing Ruleset 1.11 policy keeps missing semantic judgments UNKNOWN without dispatch. No SDK result or rule result was stubbed. Engine aggregation was independently exposed using a second direct call to the same production parser/engine; its score exactly matches the canonical wrapper for each input.

Missing evidence does not prevent this evaluator from calculating a **partial-evidence numeric score**: this is how the original control is also scored. UNKNOWN/NOT_APPLICABLE and explicit EVIDENCE_INCOMPLETE failures are excluded, never changed to PASS. V2 genuinely returned status EVALUATED with 46 rows: 21 PASS, 9 FAIL, 9 UNKNOWN, 7 NOT_APPLICABLE. It did not return NOT_EVALUATED/ERROR; no surrogate score is supplied for missing evidence.

## Weighted calculation and every changed outcome

Production scoring: eligible PASS earns 100 only when returned severity is PASS, otherwise 85. Eligible FAIL earns BLOCKER 0 / CRITICAL 40 / other 70. Each family averages its eligible rows; the overall score normalizes family weights over numeric families. Both runs have eligible family-weight denominator **0.96**. No weights or thresholds changed.

A row's overall contribution is `rowPoints × familyWeight / 0.96 / eligibleRowsInThatFamily`. Excluded rows have **no numeric contribution**, not a scored zero. When a row becomes eligible/excluded, other rows in its family change coefficient; direct per-rule changes therefore require the denominator accounting below.

| Changed rule | Original outcome / severity | V2 outcome / severity | Row points original → V2 | Weighted contribution original → V2 | Actual interpretation |
|---|---|---|---|---|---|
| BEAT_004 | UNKNOWN / CRITICAL | FAIL / CRITICAL | excluded → 40 | excluded → 0.833333333333 | Progression synonym is missed; 5s is treated as one static state (33.33% > 30%). |
| CHAR_002 | PASS / PASS | FAIL / CRITICAL | 100 → 40 | 2.291666666667 → 0.916666666667 | Extracted active-attempt duration falls from 8s/15s to 0s/15s. |
| ATTEMPT_002 | UNKNOWN / CRITICAL | FAIL / CRITICAL | excluded → 40 | excluded → 0.833333333333 | No extracted attempts: deterministic FAIL replaces unavailable semantic judgment. |
| ESCALATION_005 | PASS / PASS | FAIL / WARNING | 100 → 70 | 5.208333333333 → 3.645833333333 | No recognized measurable escalation axis; quantity-growth classification missed. |
| GENERATION_EXECUTABLE_ATTEMPTS | UNKNOWN / BLOCKER | PASS / PASS | excluded → 100 | excluded → 4.6875 | Vacuous PASS for fewer than two extracted attempts; not proven improved executability. |
| CONTINUOUS_ACTION_MOMENTUM | PASS / PASS | UNKNOWN / CRITICAL | 100 → excluded | 4.6875 → excluded | Fewer than two extracted attempts prevents strategy-transition assessment. |
| MINI_STORY_LOCK | PASS / BLOCKER | FAIL / BLOCKER | 85 → 0 | 3.541666666667 → 0 | Missing parsed attempts removes mini-story support; not evidence of missing source events. |

ATTEMPT_001 keeps the same FAIL/BLOCKER and 0-point row but its extracted count changes 2→0; this evidence change is not hidden merely because its outcome stays FAIL. PRODUCIBILITY_003 keeps FAIL/CRITICAL and 40 row points, while tags change FACE_CONTACT+THIN_OBJECT→THIN_OBJECT; no numeric improvement follows.

The following unchanged outcomes have different weighted contributions solely because the number of scored family rows changed:

| Rule | Same outcome / severity | Contribution original → V2 |
|---|---|---|
| REPETITION_002 | PASS / PASS | 2.916666666667 → 2.083333333333 |
| REPETITION_003 | PASS / PASS | 2.916666666667 → 2.083333333333 |
| NOVELTY_001 | PASS / WARNING | 2.479166666667 → 1.770833333333 |
| MOTION_001 | PASS / PASS | 4.6875 → 9.375 |
| BEAT_005 | PASS / PASS | 2.916666666667 → 2.083333333333 |
| REPETITION_004 | PASS / PASS | 2.916666666667 → 2.083333333333 |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | PASS / BLOCKER | 7.96875 → 3.984375 |

Family-level reconciliation includes all those denominator changes:

| Family | Weight | Scored rows original → V2 | Family score original → V2 | Net overall score change |
|---|---|---|---|---|
| concept_strength | 0.12 | 3 → 3 | 61.666666666667 → 33.333333333333 | -3.541666666667 |
| visual_novelty | 0.14 | 5 → 7 | 97 → 80.714285714286 | -2.375 |
| progression | 0.11 | 5 → 5 | 94 → 82 | -1.375 |
| escalation | 0.1 | 2 → 2 | 92.5 → 77.5 | -1.5625 |
| final_payoff | 0.09 | 3 → 3 | 95 → 95 | 0 |
| ai_producibility | 0.1 | 3 → 3 | 80 → 80 | 0 |
| hook_strength | 0.12 | 2 → 2 | 92.5 → 92.5 | 0 |
| motion_quality | 0.09 | 2 → 1 | 100 → 100 | 0 |
| generation_executability | 0.09 | 1 → 2 | 85 → 92.5 | 0.703125 |

These family changes sum to **-8.151041666667**. Positive generation-executability contribution (+0.703125 overall) is the short-circuit PASS caused by missing parsed attempts, not a real production gain. Motion-quality stays numerically 100 because the remaining eligible MOTION_001 row is 100; UNKNOWN momentum is excluded rather than scored zero.

## Exact source/parser causes — unchanged code

**Actor/attempt extraction.** The actual actor-bound pattern in `app/parser/actor_attempts.py::classify_content` accepts actor + optional `tries to`, `attempts to`, `continues to`, etc. + supported physical verb. V2 says:

> Mimi tries once to peel the stuck note away with her other hand.

The intervening `once` is not accepted by the intent-prefix pattern; the subsequent token `tries` is not recognized as the physical PEEL root. The emitted beat_02 `characterActions` is empty and `isAttempt=false`. Original “Mimi tries to peel …” is recognized as PEEL, source-bound.

V2's next beat begins:

> Continuing the same note-pulling action, show the notes doubling clearly from two to four to eight.

This participial/directorial construction has no matching actor-plus-verb continuation clause. The later “Mimi becomes visibly overwhelmed; stop pulling …” does not establish a parsed actor-directed PULL attempt. Beat_03 likewise has `characterActions=[]`, `isAttempt=false`. Original “Mimi continues to pull …” is recognized. These are measurable extraction limitations for supported existing actions; they are not justification for inventing a third attempt.

**BEAT_004.** The actual SOURCE_PROGRESSION_V2 branch accepts `from X to Y to Z` only in combination with a narrow verb list: multiply/multiplies, grow/grows, change/changes, transform/transforms. It does not accept V2's “doubling”. V2 has the explicit three counts but misses this branch, so the coarse 5/15 state is FAIL. Original “multiply from two to four to eight” produces UNKNOWN with unprovided substate times. The 33.33% measurement is real; the inference that the entire V2 state is visually unchanged is not established from this text. No timestamps were fabricated to evade it.

**ESCALATION_005.** `canonical_evidence.escalation_evidence` uses normalized candidate action/consequence words. V2's abbreviated beat action ends around “from tw...” with no structured consequence, and its vocabulary/quantity detector does not establish growth from this prose. Actual output says `quantityGrowth=false`, strength UNKNOWN, and returns FAIL/WARNING (not UNKNOWN outcome) because the candidate window is otherwise AVAILABLE. Original's parsed multiplication/consequence evidence yields PASS. No intensity values or rendered claims were injected.

Additional unchanged-score extraction differences are retained in the raw output: V2 loses structured consequence strings in all five beats; its `coreMechanic.physicalRule` becomes “Inferred from beat actions” instead of the original explicit “each pull doubles the number of sticky notes”, and recurrence becomes false. The V2 body still states the doubling progression, so this is a difference in structured extraction, not an authorized change to the source physical rule. No missing structured field was backfilled manually.

The comparison is **Original versus the complete V2 draft**, which contains the earlier V1 rewrites as well as the single final correction. It does not attribute every regression to the V1→V2 phrase replacement alone. No extra counterfactual prompt was written or evaluated.

## Required four-rule inspection

| Rule | Actual V2 outcome / severity | Row points / weighted contribution | Why it did not provide a score gain |
|---|---|---|---|
| ATTEMPT_001 | FAIL / BLOCKER | 0 / 0 | Count 0, minimum 3 for 15s. Original already failed with count 2. Zero is extraction loss; even recognizing the two protected attempts would not satisfy the three-attempt policy. |
| PRODUCIBILITY_003 | FAIL / CRITICAL | 40 / 1.388888888889 | THIN_OBJECT remains; original also had FACE_CONTACT. Same FAIL/CRITICAL earns 40 regardless of tag count. Face coverage remains in actual V2 text, so missing tag is not proof that face-contact risk vanished. |
| NOVELTY_001 | PASS / WARNING | 85 / 1.770833333333 | Still 5.0s between recognized new-consequence beat starts at 5s and 10s, above 4.5s; PASS/WARNING earns 85, not 100. No substate timing evidence was invented. |
| PAYOFF_004 | PASS / WARNING | 85 / 2.65625 | Final intensity 5 ties earlier peak 5; PASS/WARNING earns 85. This is parser-derived salience, not measured audience/visual superiority. |

## Unchanged failures and missing evidence

All original FAIL outcomes remain FAIL:

| Rule | Severity | V2 numeric treatment | Reason retained |
|---|---|---|---|
| ATTEMPT_001 | BLOCKER | 0 row points; contribution 0 | Only 0 active attempt(s) detected for a short-tier (15s) video. Minimum: 3. |
| PRODUCIBILITY_003 | CRITICAL | 40 row points; contribution 1.388888888889 | Fragile interaction risk tags detected: ['THIN_OBJECT']. These are mid-tier AI-generation risks (precision alignment, cloth/rope simulation, liquids, thin objects, face/hair contact, multi-object stacking) worth a human look before committing render budget, even though they don't rise to very-high-complexity blocking. |
| INSTANT_VISUAL_ABSURDITY_GATE | BLOCKER | excluded row points; contribution excluded | First-frame absurdity evidence is incomplete; the concept is blocked before render. |
| ENGINE_SILHOUETTE_DUPLICATE | BLOCKER | excluded row points; contribution excluded | No first-frame/final-silhouette comparison evidence was supplied; the concept is blocked before render. |

The two visual blockers have `failureBasis=EVIDENCE_INCOMPLETE`, so remain explicit FAIL findings while excluded from the numeric denominator. The nine V2 UNKNOWN rules remain excluded, not silently passed:

- **CONSISTENCY_001 / WARNING:** coreMechanic.consistency was not explicitly stated in the prompt and cannot be verified.
- **HOOK_003 / CRITICAL:** hook.soundOffClear was not explicitly stated in the prompt and cannot be verified.
- **PAYOFF_003 / CRITICAL:** Semantic judgment has no verified evidence; provider dispatch is disabled for this local ruleset.
- **CONCEPT_007 / BLOCKER:** Semantic judgment has no verified evidence; provider dispatch is disabled for this local ruleset.
- **GOAL_001 / BLOCKER:** Semantic judgment has no verified evidence; provider dispatch is disabled for this local ruleset.
- **CONCEPT_008 / CRITICAL:** Semantic judgment has no verified evidence; provider dispatch is disabled for this local ruleset.
- **HOOK_004 / CRITICAL:** Semantic judgment has no verified evidence; provider dispatch is disabled for this local ruleset.
- **PERFORMANCE_001 / WARNING:** Semantic judgment has no verified evidence; provider dispatch is disabled for this local ruleset.
- **CONTINUOUS_ACTION_MOMENTUM / CRITICAL:** At least two attempts are required to evaluate momentum between strategies.

## Why A was not reached, protected constraints and genuine repair scope

The actual `review.py` grade branch tests score **>=92** for A; V2's 80.25520833333334 is **11.744791666667 points below 92**. No rounding to A, alternate threshold, CPQ grade or waiver was used. Numeric B does not make the engine's BLOCKED state render-ready.

Some existing losses concern protected story/policy rather than missing adjectives:

- ATTEMPT_001: default minimum three versus the two source-supported attempts in the original. Its current overall loss is 4.166666666667 points; V2's false zero count does not further change that already-zero row. No extra attempt is authorized. An admission exception, if separately governed, cannot change this FAIL or calculated score.
- PAYOFF_002: no approved fake win; existing warning-level PASS earns 85. Adding a fake win would alter the approved story.
- ESCALATION_004: payoff begins at the protected 12s point; changing windows to obtain points would violate the task.
- PRODUCIBILITY_003: thin sticky-note handling and face/body coverage belong to the protected mechanism. Real staging/risk evidence may guide production, but deleting the mechanism or avoiding trigger words is not a legitimate improvement.
- Some successful gates retain non-PASS severity and score 85 by architecture (for example BEAT_DENSITY_RULE and TEMPORAL_COMPLEXITY_SPLIT_GATE). They cannot be made 100 by declaring a stronger prompt.

Genuinely addressable issues **without changing approved events** are the generic extractor's recognition of adverb-bearing “tries once to peel”, actor-continuation constructions and explicit doubling state progressions. Those are parser/evidence fidelity issues, not permission to alter this task's scoring code. A future authorized correction would need regression coverage and any required semantics governance; this task implements none. Evidence for actual substate durations, sound-off readability, reflection continuity and ending salience must be real; it must not be fabricated to recover points. Whether opening/face-readable staging produces a better video remains separate and unverified.

### Comparison with the earlier conditional 89.3125/B ceiling

**80.25520833333334/B is the actual V2 result; 89.3125/B was never an achieved result.** V2 is **9.057291666667 points below** that older conditional bound. The earlier calculation assumed the original's eligible rows and protected windows stayed fixed while NOVELTY_001 and PAYOFF_004 hypothetically earned 100. Here neither row improved (both remain 85), and other outcomes plus family row counts changed: visual_novelty 5→7, motion_quality 2→1, generation_executability 1→2. That invalidates treating the older ceiling as a V2 prediction or minimum. No new optimistic ceiling replaces this actual score.

## Complete actual rule ledger

This table includes all 46 rows. Contribution is in overall score points, not an independent rule weight. “Excluded” means no numeric term; full details, spans, measurements and production source hashes are in `mimi-v2-actual-canonical-evidence/actual-evaluations.json`.

| Rule | Original outcome / severity | V2 outcome / severity | Row points original → V2 | Overall contribution original → V2 |
|---|---|---|---|---|
| CONCEPT_006 | PASS / PASS | PASS / PASS | 100 → 100 | 4.166666666667 → 4.166666666667 |
| BEAT_004 | UNKNOWN / CRITICAL | FAIL / CRITICAL | excluded → 40 | excluded → 0.833333333333 |
| REPETITION_002 | PASS / PASS | PASS / PASS | 100 → 100 | 2.916666666667 → 2.083333333333 |
| REPETITION_003 | PASS / PASS | PASS / PASS | 100 → 100 | 2.916666666667 → 2.083333333333 |
| NOVELTY_001 | PASS / WARNING | PASS / WARNING | 85 → 85 | 2.479166666667 → 1.770833333333 |
| PROGRESSION_005 | PASS / PASS | PASS / PASS | 100 → 100 | 2.291666666667 → 2.291666666667 |
| ESCALATION_004 | PASS / WARNING | PASS / WARNING | 85 → 85 | 4.427083333333 → 4.427083333333 |
| PAYOFF_001 | PASS / PASS | PASS / PASS | 100 → 100 | 3.125 → 3.125 |
| PRODUCIBILITY_001 | PASS / PASS | PASS / PASS | 100 → 100 | 3.472222222222 → 3.472222222222 |
| CONSISTENCY_001 | UNKNOWN / WARNING | UNKNOWN / WARNING | excluded → excluded | excluded → excluded |
| HOOK_002 | PASS / PASS | PASS / PASS | 100 → 100 | 6.25 → 6.25 |
| HOOK_003 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| MOTION_001 | PASS / PASS | PASS / PASS | 100 → 100 | 4.6875 → 9.375 |
| ATTEMPT_001 | FAIL / BLOCKER | FAIL / BLOCKER | 0 → 0 | 0 → 0 |
| CHAR_002 | PASS / PASS | FAIL / CRITICAL | 100 → 40 | 2.291666666667 → 0.916666666667 |
| PRODUCIBILITY_002 | PASS / PASS | PASS / PASS | 100 → 100 | 3.472222222222 → 3.472222222222 |
| PAYOFF_002 | PASS / WARNING | PASS / WARNING | 85 → 85 | 1.947916666667 → 1.947916666667 |
| ATTEMPT_002 | UNKNOWN / CRITICAL | FAIL / CRITICAL | excluded → 40 | excluded → 0.833333333333 |
| PAYOFF_003 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| CONSISTENCY_002 | NOT_APPLICABLE / CRITICAL | NOT_APPLICABLE / CRITICAL | excluded → excluded | excluded → excluded |
| CONCEPT_007 | UNKNOWN / BLOCKER | UNKNOWN / BLOCKER | excluded → excluded | excluded → excluded |
| BEAT_005 | PASS / PASS | PASS / PASS | 100 → 100 | 2.916666666667 → 2.083333333333 |
| PAYOFF_004 | PASS / WARNING | PASS / WARNING | 85 → 85 | 2.65625 → 2.65625 |
| PAYOFF_005 | NOT_APPLICABLE / WARNING | NOT_APPLICABLE / WARNING | excluded → excluded | excluded → excluded |
| REPETITION_004 | PASS / PASS | PASS / PASS | 100 → 100 | 2.916666666667 → 2.083333333333 |
| PAYOFF_006 | PASS / PASS | PASS / PASS | 100 → 100 | 3.125 → 3.125 |
| GOAL_001 | UNKNOWN / BLOCKER | UNKNOWN / BLOCKER | excluded → excluded | excluded → excluded |
| CONCEPT_008 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| PROGRESSION_006 | PASS / PASS | PASS / PASS | 100 → 100 | 2.291666666667 → 2.291666666667 |
| ESCALATION_005 | PASS / PASS | FAIL / WARNING | 100 → 70 | 5.208333333333 → 3.645833333333 |
| HOOK_004 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| PERFORMANCE_001 | UNKNOWN / WARNING | UNKNOWN / WARNING | excluded → excluded | excluded → excluded |
| PRODUCIBILITY_003 | FAIL / CRITICAL | FAIL / CRITICAL | 40 → 40 | 1.388888888889 → 1.388888888889 |
| GENERATION_EXECUTABLE_ATTEMPTS | UNKNOWN / BLOCKER | PASS / PASS | excluded → 100 | excluded → 4.6875 |
| CONTINUOUS_ACTION_MOMENTUM | PASS / PASS | UNKNOWN / CRITICAL | 100 → excluded | 4.6875 → excluded |
| INSTANT_VISUAL_ABSURDITY_GATE | FAIL / BLOCKER | FAIL / BLOCKER | excluded → excluded | excluded → excluded |
| ENGINE_SILHOUETTE_DUPLICATE | FAIL / BLOCKER | FAIL / BLOCKER | excluded → excluded | excluded → excluded |
| CONCEPT_009 | NOT_APPLICABLE / BLOCKER | NOT_APPLICABLE / BLOCKER | excluded → excluded | excluded → excluded |
| MINI_STORY_LOCK | PASS / BLOCKER | FAIL / BLOCKER | 85 → 0 | 3.541666666667 → 0 |
| GOAL_VISIBLE_EARLY | PASS / CRITICAL | PASS / CRITICAL | 85 → 85 | 5.3125 → 5.3125 |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | PASS / BLOCKER | PASS / BLOCKER | 85 → 85 | 7.96875 → 3.984375 |
| BEAT_DENSITY_RULE | PASS / CRITICAL | PASS / CRITICAL | 85 → 85 | 1.947916666667 → 1.947916666667 |
| CONTINUATION_LOCK | NOT_APPLICABLE / BLOCKER | NOT_APPLICABLE / BLOCKER | excluded → excluded | excluded → excluded |
| STUBBORN_RETURN_LOOP | NOT_APPLICABLE / BLOCKER | NOT_APPLICABLE / BLOCKER | excluded → excluded | excluded → excluded |
| STUBBORN_RETURN_HOOK | NOT_APPLICABLE / CRITICAL | NOT_APPLICABLE / CRITICAL | excluded → excluded | excluded → excluded |
| STUBBORN_RETURN_PAYOFF | NOT_APPLICABLE / CRITICAL | NOT_APPLICABLE / CRITICAL | excluded → excluded | excluded → excluded |

## Reproduction and integrity

Reproduction harness: `mimi-v2-actual-canonical-evidence/run_actual_canonical.py`, run from repository root with `python3 intelligence/docs/mimi-v2-actual-canonical-evidence/run_actual_canonical.py`. It resolves the live immutable original and exact V2 file, checks hashes/settings, uses the existing running ML runtime with bytecode writes disabled, forbids network connections during evaluation, and saves only local evidence. It calls no write API or database mutation. The report describes this executed offline result; it does not create an official persisted V2 analysis.

Before/after full-row SHA-256 digests for **all** production prompt-version rows and workflow-event rows are identical. Original Prompt 10/version 1, original analysis, approved story and evidence remain untouched. No prompt approval, new attempt, grading activation, render, paid call, rebuild/deployment, commit or push occurred. No missing semantic/visual evidence was converted to PASS by the harness. The production engine's own fewer-than-two-attempts executability PASS is disclosed above rather than interpreted as independent verification.
