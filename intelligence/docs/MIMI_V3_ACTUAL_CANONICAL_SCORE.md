ORIGINAL_SCORE: 88.40625000000001
ORIGINAL_GRADE: B

V2_SCORE: 80.25520833333334
V2_GRADE: B

V3_SCORE: 88.40625000000001
V3_GRADE: B

V3_DELTA_FROM_V2: 8.151041666666671
V3_DELTA_FROM_ORIGINAL: 0.0

A_THRESHOLD: 92
A_ACHIEVED: NO

ORIGINAL_ATTEMPTS: 2
V2_ATTEMPTS: 0
V3_ATTEMPTS: 2

# Mimi V3 — targeted causal repair and actual canonical evaluation

Executed 2026-10-16. **V3 scores 88.40625/B**, restoring V2's 8.151041666667-point parsing-related loss and matching the original. The native serialized 88.40625000000001 is ordinary floating-point precision; no score override/rounding was applied inside the evaluator. **A was not achieved.** Both controls reproduced before V3 ran; all three prompts were independently parsed by the actual deployed Ruleset 1.11 path.

This is legitimate recovery of source-bound PEEL/PULL recognition and explicit state-progression interpretation, **not independently demonstrated creative superiority**. V3 still has canonical blockers and unavailable semantic/visual evidence. The targeted repair does not authorize rendering or an approved prompt version.

## Complete V3 production prompt

Settings remain separate from prompt-body text: **ABSURD_PHYSICS / SEEDANCE_2_0_MINI / configured model `byte-plus-seedance-2-mini` / 15s / image2video / 480p / 9:16**. The V2 settings header is byte-identical in V3; the configured model is the existing mapping, not an added prompt instruction.

Standalone complete artifact: `CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V3.txt`.

```text
TITLE / FORMAT
Mimi Sticky / 15s Video

VISUAL STYLE
Bright and colorful animation with a playful tone. Make Mimi, the sticky note, and the toy cabinet easy to read together at the opening. Keep staging simple and spatially consistent; reframe only when needed to keep the action clear.

CHARACTER / CONTINUITY
Mimi is the established anthropomorphic bunny. Preserve that identity and do not invent unverified appearance details. Keep the toy cabinet and mirror in the same scene.

TIMED SHOT PLAN
0-2s: Mimi reaches to place one sticky note on the toy cabinet as a cleanup reminder. In a clear view that includes Mimi, the note, and the cabinet, the note visibly sticks to one fingertip instead of the cabinet. The cleanup intention should read from the action; readable lettering is not required.
2-5s: Mimi tries to peel the stuck note away with her other hand. The note splits into two, with one note sticking to each hand.
5-10s: Mimi continues to pull; the sticky notes multiply from two to four to eight as she pulls. The notes progressively cover Mimi's arms, legs, and parts of her face, while keeping her eyes and mouth readable. Mimi becomes visibly overwhelmed; stop pulling once the existing two-to-four-to-eight escalation is complete; add no further doubling beyond eight.
10-12s: Mimi sees herself in the mirror and screams. Show the same already note-covered, overwhelmed Mimi in the reflection. Keep the existing note coverage unchanged through the mirror reaction and directly into the sneeze; add no pulling action, notes, or escalation here.
12-15s: Mimi sneezes; all the notes fly off her and stick to the toy cabinet. Mimi visibly breathes a sigh of relief. End with Mimi relieved and the cabinet still visibly messy.

AUDIO
Playful background music with simple sneeze and sticky-note sounds. No speech or captions.

NEGATIVE CONSTRAINTS
No dark themes, violence, injury, or choking imagery.

CHARACTER IDENTITY LOCK
Mimi is the established anthropomorphic bunny character. Preserve that identity; do not render a human or invent unverified visual details. No approved visual reference is currently bound, so appearance details remain unverified.
```

## Exact authorized edit and fingerprints

Only the two requested sentence replacements were applied, once each. The rest of each beat, the stop-at-eight restriction, and every other line are unchanged.

```diff
--- CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V2.txt
+++ CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V3.txt
@@ -21,8 +21,8 @@
 
 TIMED SHOT PLAN
 0-2s: Mimi reaches to place one sticky note on the toy cabinet as a cleanup reminder. In a clear view that includes Mimi, the note, and the cabinet, the note visibly sticks to one fingertip instead of the cabinet. The cleanup intention should read from the action; readable lettering is not required.
-2-5s: Mimi tries once to peel the stuck note away with her other hand. The note splits into two, with one note sticking to each hand.
-5-10s: Continuing the same note-pulling action, show the notes doubling clearly from two to four to eight. The notes progressively cover Mimi's arms, legs, and parts of her face, while keeping her eyes and mouth readable. Mimi becomes visibly overwhelmed; stop pulling once the existing two-to-four-to-eight escalation is complete; add no further doubling beyond eight.
+2-5s: Mimi tries to peel the stuck note away with her other hand. The note splits into two, with one note sticking to each hand.
+5-10s: Mimi continues to pull; the sticky notes multiply from two to four to eight as she pulls. The notes progressively cover Mimi's arms, legs, and parts of her face, while keeping her eyes and mouth readable. Mimi becomes visibly overwhelmed; stop pulling once the existing two-to-four-to-eight escalation is complete; add no further doubling beyond eight.
 10-12s: Mimi sees herself in the mirror and screams. Show the same already note-covered, overwhelmed Mimi in the reflection. Keep the existing note coverage unchanged through the mirror reaction and directly into the sneeze; add no pulling action, notes, or escalation here.
 12-15s: Mimi sneezes; all the notes fly off her and stick to the toy cabinet. Mimi visibly breathes a sigh of relief. End with Mimi relieved and the cabinet still visibly messy.
```

| Input/artifact | SHA-256 |
|---|---|
| Original body, immutable Prompt 10/version 1 | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` |
| Unchanged V2 body | `44779084f986b4a7b1b3a5d1eab9c617f2e6f518a9c5b771cab02bce446cd219` |
| **V3 body** | **`f362df56f7a54ee37002ee9e6f756edd59eb50fe5d0c484ee80416b4d954498a`** |
| Full V3 file | `4d0af04ed796989096828076ba3cf13d322abc38ce7bac43f6c01ca9ed12c667` |
| Approved story, unchanged | `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b` |

Body extraction is UTF-8 text after `PROMPT BODY` plus its blank separator, removing trailing file newline characters only; identical to V1/V2. Original and V1/V2 artifacts were not overwritten. V2 full-file SHA remains `7d3517ac1f906225f586a05f5bfb4a259f7f534da45c286dad008e81e1452c5d`; V1 remains `716ce953d65a98fd7386d6533f7f320f064876423819b4e2a9655f1fc726ea46`.

## Actual evaluator invocation and controls

Used the running production ML runtime via a separate `docker exec -i -e PYTHONDONTWRITEBYTECODE=1 intelligence-ml-service-1 python ...` process, with inputs sent over stdin and results saved only to local documentation evidence. No deployment/rebuild and no production write endpoint were used.

Actual function: **`app.workflow.review._run_canonical_evaluation(request)`**, actual production `parse_prompt`, `RuleEngine.evaluate`, `RULESET_1.11.yaml`, `ACTOR_SOURCE_BOUND_V2`, `TOKEN_MOTION_V2`, PRE_RENDER. YAML SHA-256: `8222f3208b4ee70d318429d4d72d7eb1cdae56c023f18131fd8651c7954b0a97`. Runtime review/parser/actor extraction/evidence/weights hashes match the preceding V2 run and repository files. No parser, YAML, severity, weight, threshold or engine code changed.

Each input received the same original bound production settings and evidence availability, replacing only the complete prompt body. The offline canonical function parses that body afresh and consumes profile/ruleset; no source IDs are used to import another prompt's IR/outcomes. No manual attempts, new semantic decisions, visual evidence or original parser fields were injected. Ruleset semantic dispatch stays disabled; a network-denial guard recorded **zero attempted network connections**. It did not stub rule results. A direct second parser/engine call for each exact input exposes weights/measurements omitted by the public projection and returns exactly the same score as the production wrapper.

Control checks ran sequentially before V3: original reproduced 88.40625/B within normal float tolerance, and its complete JSON-normalized projection equals the saved authoritative analysis. V2 reproduced **80.25520833333334/B** and its complete projection equals the preceding actual V2 run. Either mismatch would have stopped the harness before V3. Raw outputs are in `mimi-v3-actual-canonical-evidence/actual-evaluations.json`.

| Input | Actual score / grade | Engine status | Eligible family-weight denominator |
|---|---|---|---|
| original | 88.40625000000001 / B | BLOCKED | 0.96 |
| v2 | 80.25520833333334 / B | BLOCKED | 0.96 |
| v3 | 88.40625000000001 / B | BLOCKED | 0.96 |

V3−V2 = **8.151041666667**. V3−Original = **0**. Remaining gap to 92 = **3.593750000000**. Numeric B does not override the engine's BLOCKED status. UNKNOWN/evidence-gap rows remain excluded from numeric aggregation, not changed to PASS.

## Actual attempt and progression extraction

| Property | Original | V2 | V3 |
|---|---|---|---|
| Source-bound active attempts | 2 | 0 | **2** |
| Beat 2 actor-directed action | PEEL | Empty | **PEEL** |
| Beat 3 actor-directed action | PULL | Empty | **PULL** |
| Exact 2→4→8 words present | Yes | Yes | Yes |
| BEAT_004 recognizes changing three-state progression | Yes: UNKNOWN substate timing | No: FAIL/static inference | **Yes: UNKNOWN substate timing** |
| ESCALATION_005 quantityGrowth flag | false (other escalation support gives PASS) | false | **true** |
| Source-bound PEEL→PULL sequence | Observed | Not extracted | **Observed** |
| Character active-attempt duration | 8/15s = 53.33% | 0/15s | **8/15s = 53.33%** |

V3 supplies literal actor/action evidence: “Mimi tries to peel the stuck note away with her other hand” and “Mimi continues to pull”. The V2 extractor could not bridge `tries once to` or the actor-less participial/directorial opening. V3 also uses “multiply from two to four to eight”, which enters BEAT_004's existing SOURCE_PROGRESSION_V2 branch. Actual source spans, not invented spans, accompany both recognized attempts in the saved raw IR.

This establishes recognition of the **same two** approved actions. It does not create a third attempt, independently verify distinct strategy semantics or show the rendered note count. BEAT_004 is **UNKNOWN**, not PASS: the planned state changes are recognized but their individual dwell times remain unavailable. No sub-beat timestamp was invented.

## Every outcome/severity change from V2 to V3

Eligible row scoring is unchanged: PASS with severity PASS =100, other PASS =85; FAIL BLOCKER=0, CRITICAL=40, other=70. Overall contribution = row points × family weight / eligible weight denominator / scored rows in that family. Excluded rows contribute no numeric term, rather than being scored zero.

| Rule | V2 outcome / severity | V3 outcome / severity | Row points V2 → V3 | Weighted contribution V2 → V3 | Trigger and classification |
|---|---|---|---|---|---|
| BEAT_004 | FAIL / CRITICAL | UNKNOWN / CRITICAL | 40 → excluded | 0.833333333333 → excluded | “multiply from two to four to eight” recognizes planned change; unavailable timing stays UNKNOWN. Better extraction, no visual PASS. |
| CHAR_002 | FAIL / CRITICAL | PASS / PASS | 40 → 100 | 0.916666666667 → 2.291666666667 | PEEL/PULL restore 8s active duration; better extraction of existing actions. |
| ATTEMPT_002 | FAIL / CRITICAL | UNKNOWN / CRITICAL | 40 → excluded | 0.833333333333 → excluded | Restored actor actions remove the zero-attempt deterministic FAIL; unavailable semantic evidence remains UNKNOWN. |
| ESCALATION_005 | FAIL / WARNING | PASS / PASS | 70 → 100 | 3.645833333333 → 5.208333333333 | Explicit actor-led multiplication survives action extraction; quantityGrowth=true. Better extraction, not a new escalation event. |
| GENERATION_EXECUTABLE_ATTEMPTS | PASS / PASS | UNKNOWN / BLOCKER | 100 → excluded | 4.6875 → excluded | Two attempts remove the zero-attempt vacuous PASS; semantic executability is now correctly unavailable/UNKNOWN. |
| CONTINUOUS_ACTION_MOMENTUM | UNKNOWN / CRITICAL | PASS / PASS | excluded → 100 | excluded → 4.6875 | Recognized adjacent 2–5s and 5–10s attempts allow deterministic transition check; no measured video claim. |
| MINI_STORY_LOCK | FAIL / BLOCKER | PASS / BLOCKER | 0 → 85 | 0 → 3.541666666667 | Recognized attempts complete the same goal/obstruction/progression/payoff arc; better extraction. |

ATTEMPT_001 remains FAIL/BLOCKER, row points 0, contribution 0, but its measured count changes **0→2**. This fixes evidence extraction without satisfying minimum three. PRODUCIBILITY_003 remains FAIL/CRITICAL, row points 40, contribution 1.388888888889; THIN_OBJECT remains.

**False-positive PASS inspection:** V2's GENERATION_EXECUTABLE_ATTEMPTS PASS came from “Fewer than two attempts; nothing to compare”. V3 removes that vacuous PASS, yielding UNKNOWN/BLOCKER with unavailable verified semantic judgment. This is improved honesty, not a production regression. REPEAT/verb-variety PASS checks in V3 now have two supported verbs instead of relying on empty attempts; semantic distinctness and Seedance feasibility remain unverified. No new PASS is promoted to render authorization.

### Family denominator reconciliation

The eligible weight total stays 0.96, but eligible row counts change. The following unchanged outcomes have contribution changes solely from their family denominator:

| Rule | Unchanged outcome / severity | Contribution V2 → V3 |
|---|---|---|
| REPETITION_002 | PASS / PASS | 2.083333333333 → 2.916666666667 |
| REPETITION_003 | PASS / PASS | 2.083333333333 → 2.916666666667 |
| NOVELTY_001 | PASS / WARNING | 1.770833333333 → 2.479166666667 |
| MOTION_001 | PASS / PASS | 9.375 → 4.6875 |
| BEAT_005 | PASS / PASS | 2.083333333333 → 2.916666666667 |
| REPETITION_004 | PASS / PASS | 2.083333333333 → 2.916666666667 |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | PASS / BLOCKER | 3.984375 → 7.96875 |

Complete net family changes, including all denominator effects:

| Family | Numeric rows V2 → V3 | Family score V2 → V3 | Net overall delta |
|---|---|---|---|
| concept_strength | 3 → 3 | 33.333333333333 → 61.666666666667 | 3.541666666667 |
| visual_novelty | 7 → 5 | 80.714285714286 → 97 | 2.375 |
| progression | 5 → 5 | 82 → 94 | 1.375 |
| escalation | 2 → 2 | 77.5 → 92.5 | 1.5625 |
| final_payoff | 3 → 3 | 95 → 95 | 0 |
| ai_producibility | 3 → 3 | 80 → 80 | 0 |
| hook_strength | 2 → 2 | 92.5 → 92.5 | 0 |
| motion_quality | 1 → 2 | 100 → 100 | 0 |
| generation_executability | 2 → 1 | 92.5 → 85 | -0.703125 |

Family deltas reconcile exactly within floating-point tolerance to +8.151041666667. In particular, generation_executability decreases by 0.703125 when the vacuous PASS is removed; motion_quality stays numerically 100 because both its restored eligible checks pass. Restoration of missing checks and their denominators must not be described as independent creative gains.

### Other changed evidence with unchanged outcome

- BEAT_005 PASS changes from no-active-problem short circuit to an actual measured 0s detached stretch.
- REPETITION_004 PASS and PROGRESSION_006 PASS change from fewer/no-attempt short circuits to measured PEEL dominance of 50%; no root dominates.
- GOAL_VISIBLE_EARLY stays PASS/CRITICAL but now includes an observed secondary recovery attempt with its actual source span.
- MINI_STORY_LOCK, BEAT_DENSITY_RULE and TEMPORAL_COMPLEXITY_SPLIT_GATE density evidence updates strategy_change_count 0→1; five major beats and all durations stay unchanged.
- STUBBORN_RETURN_LOOP/HOOK/PAYOFF remain NOT_APPLICABLE. Their engine-profile evidence updates character intervention false→true and intervention count 0→2; this does not activate the unrelated return-loop exception or introduce recurrence.
- ENGINE_SILHOUETTE_DUPLICATE remains excluded FAIL/BLOCKER with missing visual comparison; CONTINUATION_LOCK remains NOT_APPLICABLE. Their reported scored-family-row count changes with the family, without adding any numeric term.

All changed details, values, messages and contributions are retained verbatim in the raw 46-rule ledger. V3 still lacks a source-extracted explicit `coreMechanic.physicalRule` clause (it remains “Inferred from beat actions”), still has recurrence=false, and still lacks contrastive surface-attachment evidence in that parser field. Those limitations are not filled manually. The body still states the physical progression and wrong attachment; narrower structured extraction is not proof the source mechanic changed.

## Remaining major numeric losses and A feasibility

V3's remaining losses sum to **11.59375** relative to 100:

| Rule | Actual outcome / severity | Row points | Overall loss | Nature of remaining loss |
|---|---|---|---|---|
| NOVELTY_001 | PASS / WARNING | 85 | 0.4375 | 5s gap exceeds 4.5s; protected window and missing real substate timing. No invented timestamps. |
| ESCALATION_004 | PASS / WARNING | 85 | 0.78125 | Protected 12s payoff timing; windows unchanged. |
| ATTEMPT_001 | FAIL / BLOCKER | 0 | 4.166666666667 | Protected story/policy: two supported attempts versus minimum three; no third may be fabricated. |
| PAYOFF_002 | PASS / WARNING | 85 | 0.34375 | Protected story: no approved fake win; optional bonus not added. |
| PAYOFF_004 | PASS / WARNING | 85 | 0.46875 | Ending salience 5 ties earlier 5; parser/real visual evidence limitation, not proven weak payoff. |
| PRODUCIBILITY_003 | FAIL / CRITICAL | 40 | 2.083333333333 | Actual fragile sticky-note interaction risk; THIN_OBJECT still detected. Face coverage remains textually present even though FACE_CONTACT is not tagged. |
| MINI_STORY_LOCK | PASS / BLOCKER | 85 | 0.625 | Fixed successful-branch severity cap: PASS/BLOCKER earns 85. |
| GOAL_VISIBLE_EARLY | PASS / CRITICAL | 85 | 0.9375 | Fixed successful-branch severity cap: PASS/CRITICAL earns 85. |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | PASS / BLOCKER | 85 | 1.40625 | Fixed successful-branch severity cap: PASS/BLOCKER earns 85. |
| BEAT_DENSITY_RULE | PASS / CRITICAL | 85 | 0.34375 | Fixed successful-branch severity cap: PASS/CRITICAL earns 85. |

The six categories are distinct:

1. **Prompt clarity:** the two authorized sentences now explicitly name Mimi and the existing actions; the stop-at-eight constraint remains. Remaining fingertip, face/reflection readability and compressed ending clarity are actual production hypotheses, not a reason to add synonyms for points. No new confirmed textual omission is asserted from the score alone.
2. **Protected story constraints:** two attempts, no fake win, unchanged 12s payoff onset. An ATTEMPT_001 admission exception, if separately authorized through governance, preserves the canonical FAIL and score.
3. **Parser limitations:** explicit core physical-rule and surface-attachment fields remain incompletely extracted; salience defaults and lexical classifiers are not real visual observations. No parser repair is made in this task.
4. **Fixed severity caps:** valid gates intentionally earn 85 because their returned severity is BLOCKER/CRITICAL. No prompt phrasing can administratively convert those branches to 100.
5. **Missing independent evidence:** BEAT_004 substate timing, semantic distinctness/executability and first-frame/silhouette evidence are unavailable. Their UNKNOWN/excluded status is retained, not imputed PASS. Source fidelity and official creative grade are separate.
6. **Actual production risks:** small finger contacts, discrete 2→4→8 counts, adhered notes covering face/body, reflection matching and the three-second sneeze/landing/relief finale still require real video inspection.

With the **current eligible rows/evidence and protected story** the original numeric profile is restored. The earlier **89.3125/B** bound remains only the conditional calculation granting NOVELTY_001 and PAYOFF_004 100 while everything else stays fixed; neither achieved that here (both stay PASS/WARNING, 85). It is not a V3 score, a promise, or a universal ceiling after future independent evidence changes applicability/denominators. Even that conditional value is 2.6875 below 92. **A≥92 has no demonstrated legitimate prompt-only path in this fixed context.** Do not invent another attempt, timing evidence, fake win or risk-free execution to reach A. No further rewrite/evaluation loop was attempted.

## Story preservation and safety

Verification reconstructs V3 by exactly two replacements from V2, with byte-identical settings/header and all other text. Five windows remain 0–2, 2–5, 5–10, 10–12 and 12–15. Initial attachment, PEEL/split, continuing PULL with 2→4→8, stop-at-eight, readable expression, mirror/scream under unchanged coverage, sneeze-to-cabinet, relief and messy ending are retained. This task's approved-source preservation check is not an independent source-fidelity PASS.

The owner's cleanup-intent interpretation without exact “Topla!” lettering is unchanged. Mirror beat still prohibits new pulling/multiplication; note-covered overwhelmed state carries to sneeze; no choking imagery, extra character/object, extra action, new physical rule, twist, dialogue or sub-beat timing was added. The exact approved story approval row was read and its source hash reverified.

Production prompt-version and workflow-event full-row digests match before/after. The two controls and historical evidence were not persisted again or overwritten; V3 remains a file-only draft. Backend and ML real-dispatch flags remain false. No paid AI calls, generation, rendering, new approval, SQL writes, parser/ruleset/weight/threshold edits, rebuild/deployment, commit or push occurred.

## One next product action

**Obtain and verify the owner's actual Mimi character reference image**, using the existing asset/reference workflow. That is the immediate missing input for visual preparation; do not start another score-driven rewrite. It does not approve this draft, satisfy all source/canonical evidence requirements, or authorize a paid start frame/render. After separate exact-version approval, accepted start-frame preparation and legitimate gate resolution, a separately authorized bounded Seedance visual test can examine the protected physical progression. V3's recovered score alone grants none of those permissions.

## Reproduction and complete rule evidence

Run from repository root: `python3 intelligence/docs/mimi-v3-actual-canonical-evidence/run_actual_canonical.py`. The harness parses original, V2 and V3 independently, verifies both complete controls, records production rule outputs and aggregation, and makes only read-only production data accesses. Evidence: `actual-evaluations.json`, `verification.json`, and `execution-stderr.log` in that same directory. Runtime source hashes and production before/after digests are included.

| Rule | V2 outcome / severity | V3 outcome / severity | Row points V2 → V3 | Overall contribution V2 → V3 |
|---|---|---|---|---|
| CONCEPT_006 | PASS / PASS | PASS / PASS | 100 → 100 | 4.166666666667 → 4.166666666667 |
| BEAT_004 | FAIL / CRITICAL | UNKNOWN / CRITICAL | 40 → excluded | 0.833333333333 → excluded |
| REPETITION_002 | PASS / PASS | PASS / PASS | 100 → 100 | 2.083333333333 → 2.916666666667 |
| REPETITION_003 | PASS / PASS | PASS / PASS | 100 → 100 | 2.083333333333 → 2.916666666667 |
| NOVELTY_001 | PASS / WARNING | PASS / WARNING | 85 → 85 | 1.770833333333 → 2.479166666667 |
| PROGRESSION_005 | PASS / PASS | PASS / PASS | 100 → 100 | 2.291666666667 → 2.291666666667 |
| ESCALATION_004 | PASS / WARNING | PASS / WARNING | 85 → 85 | 4.427083333333 → 4.427083333333 |
| PAYOFF_001 | PASS / PASS | PASS / PASS | 100 → 100 | 3.125 → 3.125 |
| PRODUCIBILITY_001 | PASS / PASS | PASS / PASS | 100 → 100 | 3.472222222222 → 3.472222222222 |
| CONSISTENCY_001 | UNKNOWN / WARNING | UNKNOWN / WARNING | excluded → excluded | excluded → excluded |
| HOOK_002 | PASS / PASS | PASS / PASS | 100 → 100 | 6.25 → 6.25 |
| HOOK_003 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| MOTION_001 | PASS / PASS | PASS / PASS | 100 → 100 | 9.375 → 4.6875 |
| ATTEMPT_001 | FAIL / BLOCKER | FAIL / BLOCKER | 0 → 0 | 0 → 0 |
| CHAR_002 | FAIL / CRITICAL | PASS / PASS | 40 → 100 | 0.916666666667 → 2.291666666667 |
| PRODUCIBILITY_002 | PASS / PASS | PASS / PASS | 100 → 100 | 3.472222222222 → 3.472222222222 |
| PAYOFF_002 | PASS / WARNING | PASS / WARNING | 85 → 85 | 1.947916666667 → 1.947916666667 |
| ATTEMPT_002 | FAIL / CRITICAL | UNKNOWN / CRITICAL | 40 → excluded | 0.833333333333 → excluded |
| PAYOFF_003 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| CONSISTENCY_002 | NOT_APPLICABLE / CRITICAL | NOT_APPLICABLE / CRITICAL | excluded → excluded | excluded → excluded |
| CONCEPT_007 | UNKNOWN / BLOCKER | UNKNOWN / BLOCKER | excluded → excluded | excluded → excluded |
| BEAT_005 | PASS / PASS | PASS / PASS | 100 → 100 | 2.083333333333 → 2.916666666667 |
| PAYOFF_004 | PASS / WARNING | PASS / WARNING | 85 → 85 | 2.65625 → 2.65625 |
| PAYOFF_005 | NOT_APPLICABLE / WARNING | NOT_APPLICABLE / WARNING | excluded → excluded | excluded → excluded |
| REPETITION_004 | PASS / PASS | PASS / PASS | 100 → 100 | 2.083333333333 → 2.916666666667 |
| PAYOFF_006 | PASS / PASS | PASS / PASS | 100 → 100 | 3.125 → 3.125 |
| GOAL_001 | UNKNOWN / BLOCKER | UNKNOWN / BLOCKER | excluded → excluded | excluded → excluded |
| CONCEPT_008 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| PROGRESSION_006 | PASS / PASS | PASS / PASS | 100 → 100 | 2.291666666667 → 2.291666666667 |
| ESCALATION_005 | FAIL / WARNING | PASS / PASS | 70 → 100 | 3.645833333333 → 5.208333333333 |
| HOOK_004 | UNKNOWN / CRITICAL | UNKNOWN / CRITICAL | excluded → excluded | excluded → excluded |
| PERFORMANCE_001 | UNKNOWN / WARNING | UNKNOWN / WARNING | excluded → excluded | excluded → excluded |
| PRODUCIBILITY_003 | FAIL / CRITICAL | FAIL / CRITICAL | 40 → 40 | 1.388888888889 → 1.388888888889 |
| GENERATION_EXECUTABLE_ATTEMPTS | PASS / PASS | UNKNOWN / BLOCKER | 100 → excluded | 4.6875 → excluded |
| CONTINUOUS_ACTION_MOMENTUM | UNKNOWN / CRITICAL | PASS / PASS | excluded → 100 | excluded → 4.6875 |
| INSTANT_VISUAL_ABSURDITY_GATE | FAIL / BLOCKER | FAIL / BLOCKER | excluded → excluded | excluded → excluded |
| ENGINE_SILHOUETTE_DUPLICATE | FAIL / BLOCKER | FAIL / BLOCKER | excluded → excluded | excluded → excluded |
| CONCEPT_009 | NOT_APPLICABLE / BLOCKER | NOT_APPLICABLE / BLOCKER | excluded → excluded | excluded → excluded |
| MINI_STORY_LOCK | FAIL / BLOCKER | PASS / BLOCKER | 0 → 85 | 0 → 3.541666666667 |
| GOAL_VISIBLE_EARLY | PASS / CRITICAL | PASS / CRITICAL | 85 → 85 | 5.3125 → 5.3125 |
| TEMPORAL_COMPLEXITY_SPLIT_GATE | PASS / BLOCKER | PASS / BLOCKER | 85 → 85 | 3.984375 → 7.96875 |
| BEAT_DENSITY_RULE | PASS / CRITICAL | PASS / CRITICAL | 85 → 85 | 1.947916666667 → 1.947916666667 |
| CONTINUATION_LOCK | NOT_APPLICABLE / BLOCKER | NOT_APPLICABLE / BLOCKER | excluded → excluded | excluded → excluded |
| STUBBORN_RETURN_LOOP | NOT_APPLICABLE / BLOCKER | NOT_APPLICABLE / BLOCKER | excluded → excluded | excluded → excluded |
| STUBBORN_RETURN_HOOK | NOT_APPLICABLE / CRITICAL | NOT_APPLICABLE / CRITICAL | excluded → excluded | excluded → excluded |
| STUBBORN_RETURN_PAYOFF | NOT_APPLICABLE / CRITICAL | NOT_APPLICABLE / CRITICAL | excluded → excluded | excluded → excluded |
