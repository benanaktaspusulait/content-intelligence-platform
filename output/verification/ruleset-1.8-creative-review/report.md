# Ruleset 1.8 creative review

**Decision: RULE_ENGINE_DEFECT.** **Status: RULESET_1_8_CREATIVE_REVIEW_COMPLETE.** This is a completed review, not a deployed parser repair or candidate approval.

## Exact +4.17 explanation

Live records: analysis0a2a88a7-9efd-4ecd-bb48-b0d661fa46f5; comparisone0458d65-0f81-40ee-8fe3-68b093394bf8; Content10 / PromptID10 / Ruleset1.8. Original82.80208333333336/B; A86.96875000000003/B; B82.80208333333336/B.

A introduces `[static close-up; keep the cabinet and her finger visible together in the same frame]`. `prompt_parser.py:1250–1281` sends the complete beat content, including this camera directive, into `_resolve_attempt_evidence`. The pattern at lines998–1001 matches **“keep the”**; the resolver at lines1216–1221 accepts **THE** as the action verb and marks the opening `isAttempt=true`, sourceNATURAL_LANGUAGE_ATTEMPT. Original/B do not have that directive and their opening has `isAttempt=false`.

This is camera/operator staging language, not a new action undertaken by Mimi. First-beat narrative action and consequence are preserved. `_attach_goal_evidence` subsequently attaches the existing goal to the false attempt, giving it apparently plausible goal provenance; that does not validate the incorrect verb.

Only ATTEMPT_001 changes outcome: FAIL/BLOCKER0 at2 attempts → PASS/PASS100 at3 attempts. The concept family has3 scored rows: its average rises61.6666667→95. Weight0.12, total scored-family weight0.96: `(95−61.6666667)×0.12/0.96 =4.1666667`, displayed+4.17. Numerators79.49→83.49; Original/B79.49/0.96=82.8020833333, A83.49/0.96=86.96875. All other45 outcomes and numeric contributions are unchanged. Some derived messages/counts change without a PASS/FAIL change.

Diagnostic-only interception of the camera match, with A's exact prompt text preserved, restores A to82.80208333333336/B. No application code, stored score, prompt, rule weight or threshold was changed. All three live stored scores were independently reproduced. Every46-row contribution sum matches the stored result.

Full rule-by-rule applicability, outcome, numeric contribution, source evidence/details, and differences are in **rule-by-rule.json**; the compact46-row table is **rule-by-rule.txt**. Contributions are additive points after the family average and normalized weight, not an inferred flat deduction per rule. UNKNOWN/NOT_APPLICABLE and EVIDENCE_INCOMPLETE failures are unscored.

## New findings

The saved canonical analysis has22PASS/7FAIL/10UNKNOWN/7NOT_APPLICABLE. A has23/6/10/7; B matches Original. `planQuality.findings` and `executionRisk.findings` are empty; their HYPOTHESIS/PASS labels do not erase canonical findings. Actual video and audience benefit are unreviewed.

| Rule | Severity | Classification | Affected source beats | Pre-visual action |
|---|---|---|---|---|
| BEAT_004 | CRITICAL | IR aggregation / production-risk hypothesis | beat_03 | Audit before correction: 5-10s contains explicit two→four→eight transitions; a 5s source range is not proof of a static rendered state. |
| MOTION_001 | WARNING | Confirmed parser defect, not confirmed motionless video | beat_01, beat_02, beat_03, beat_04, beat_05 | Fix generic token/negation handling; no is a substring of note/notes. Separate camera STATIC from character/object motion. |
| ATTEMPT_001 | BLOCKER | Recorded policy blocker with confirmed candidate-A classification defect | beat_01, beat_02, beat_03 | Review actor-bound attempt evidence. Do not add an approved-story event merely to satisfy minimum3. |
| PRODUCIBILITY_003 | CRITICAL | Source-supported production risk; human-review trigger | beat_01, beat_02, beat_03 | Review thin sticky-note and face-contact execution/occlusion; not evidence the generator has failed. |
| CONTINUOUS_ACTION_MOMENTUM | CRITICAL | Derived classifier risk / hypothesis | beat_01, beat_04, beat_05 | Motion substring defect and false attempt affect passive ratio. Final sneeze/transfer is classified as aftermath because it is not an attempt; not verified passive footage. |
| INSTANT_VISUAL_ABSURDITY_GATE | BLOCKER | Missing-evidence render gate, not confirmed weak opening | beat_01 | Missing five first-frame properties/verified visual evidence. Do not mark PASS from a camera instruction. |
| ENGINE_SILHOUETTE_DUPLICATE | BLOCKER | Missing-evidence render gate, not confirmed duplication | beat_01, beat_05 | Supply authoritative first/final-silhouette comparison evidence; absence of evidence does not establish a duplicate. |
| CONSISTENCY_001 | WARNING | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| HOOK_003 | CRITICAL | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| ATTEMPT_002 | CRITICAL | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| PAYOFF_003 | CRITICAL | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| CONCEPT_007 | BLOCKER | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| GOAL_001 | BLOCKER | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| CONCEPT_008 | CRITICAL | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| HOOK_004 | CRITICAL | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| PERFORMANCE_001 | WARNING | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |
| GENERATION_EXECUTABLE_ATTEMPTS | BLOCKER | UNKNOWN; required structured or semantic evidence unavailable | beat_01, beat_02, beat_03, beat_04, beat_05 | Source/contract review is possible before visual generation; missing judgment must remain UNKNOWN. No provider dispatch. |

The seven recordedFAIL rows must not be described as seven confirmed creative/video defects. Two are explicit missing-evidence authorization gates and excluded from score: INSTANT_VISUAL_ABSURDITY_GATE lacks staticWrongness/noHistoryRequired/noMicroComparison/largeVisualSignal/characterAlreadyEngaged; ENGINE_SILHOUETTE_DUPLICATE lacks comparison evidence. PROD003 is a human-review risk trigger. The attempt/motion/momentum results need source-classification correction/audit before story editing.

A second confirmed parser defect affects all three prompts: `_estimate_motion_amount` at `prompt_parser.py:1443–1454` checks `"no" in desc_lower`, which matches **note/notes**. Diagnostic controls: “Sticky notes fly through the air.”→none, equivalent “Cards fly through the air.”→moderate; “Zed pulls notes; notes multiply.”→none versus cards→moderate. Explicit “Zed stands still.” correctly→none. All five actual beats are parsednone despite stated pulling, splitting, multiplying, sneezing and flying. CameraSTATIC is also not proof that the character/object is stationary.

MOTION_001's5s motionless claim therefore lacks reliable physical-motion evidence. CONTINUOUS_ACTION_MOMENTUM derives7s/15s passive time forOriginal/B versus5s/15s forA because the false opening attempt removes2s; both remainFAIL. It also calls the entire12–15s sneeze/transfer/relief payoff3s aftermath solely because those beats are not attempts. These are derived classifications, not observations of passive rendered footage. BEAT_004 treats5–10s as one5s/33.3% visual-state range although source text includes two→four→eight growth; actual within-shot state exposure is unverified. Do not arbitrarily split timing or add actions to satisfy these metrics.

Source-supported general risks are CONTACT_PHYSICS_COMPLEXITYHIGH (finger/cabinet and both hands), TRANSFORMATION_COMPLEXITYMODERATE (note splitting/multiplication), SPATIAL_RELATIONSHIP_COMPLEXITYHIGH (mirror/reflection). PROD003 adds THIN_OBJECT and FACE_CONTACT. These persist for A/B. Twelve further general-producibility dimensions remainUNKNOWN, including identity continuity, exact-count dependency, occlusion, camera/action coupling and fine-motor precision. Every dimension and input reference is retained in **findings.json**. They are not confirmed failures or score bonuses.

Optional improvements remain optional: fake-win progression isNOT_APPLICABLE; no comedy or seamless-loop requirement is added; the approved messy-cabinet ending remains protected. No extra attempt, altered doubling rule or changed story event is recommended.

## Candidate A: seven questions

1. It adds a material **planning hypothesis**: static opening framing exposes both intended cabinet and actual finger attachment target together. This can improve causal legibility; successful visual legibility is not demonstrated.
2. The source narrative retains cabinet, finger and sticky-note relationships. Exact text/event coverage passes. A surface-extraction value also absorbs the following “Mimi is in front...” clause; textual source matching is not independent semantic verification of a clean object relationship.
3. It specifies a joint0–2s view, but does not explicitly establish an already-wrong note attachment at **t=0**. The beat still begins with reaching, then clinging. Five first-frame conditions remain unsupported.
4. Simultaneous tiny finger/note and cabinet visibility in a close-up may create depth/scale/occlusion/readability tradeoffs. These are execution hypotheses; neither an actual defect nor a validated reduction. High contact/precision risks remain.
5. All five source story events, ordering, timings, character identity text, explicit doubling mechanic and ending anchors are retained. Approved-story **semantic fidelity remainsUNKNOWN**.
6. The numeric advantage is not supported by a new character action: it is caused by camera language entering attempt evidence.
7. A may remain reviewable as a framing hypothesis, but cannot be offered as measured superiority using+4.17. This review does not recommend approval or select A.

## Candidate B

B preserves the same five timings0–2,2–5,5–10,10–12,12–15 seconds; it does **not** introduce a new timing split. It adds tracked medium action/consequence focus inbeat2 and static wide two/four/eight state holds inbeat3. The baseline already contains those actions and quantitative states. These are more explicit exposure/continuity instructions, not new story actions, consequences or proven strategy diversity.

Temporal clarity may improve if rendered as intended; exact hold lengths are not specified and successful execution isUNKNOWN. No validated reduction in production complexity occurs: all remainRISKY with the same contact, transformation and mirror risks. Camera tracking can itself introduce coupling risk. No canonical rule outcome changes, so B's score remains82.80/B. B is not merely adjective substitution, but its benefit remains an untested execution hypothesis.

## Decision and next action

**Selected recommendation: D — RULE_ENGINE_DEFECT.** Reproduced defects are camera-directed “keep the”→THE→false attempt and note/notes→motionnone. The arithmetic itself is correct for these incorrectly classified inputs;1.8 inheritance/return-domain corrections are not the cause of A's advantage.

A is not chosen because causal-staging improvement is plausible but the measured advantage is invalid. KEEP_ORIGINAL would leave the confirmed measurement defects unresolved; retain PromptID10 unchanged operationally while reviewing the defects. A story/prompt-targeted correction is not justified yet because the problematic evidence is produced by the parser, not an established story flaw.

Exact next action: a narrow, generic parser/evidence repair separating camera directives from actor actions, requiring a valid action verb, token-aware physical-motion/negation evidence, and preservingUNKNOWN when unsupported; then versioned deterministic revalidation of these same three prompts. No new candidate-generation request is needed. This report proposes that work and does not implement, deploy, approve or persist a new evaluation.

## Step6 finalization and Step7

**Step6 cannot yet be finalized as a trustworthy superiority/approval decision.** No candidate was selected or approved. The current comparison's source and1.8 analysis lineage are valid; historical1.7 comparison remains stale with approval eligibilityfalse. Binding validity does not validate measurement accuracy.

Current source iscontent:10/prompt:10; latest baseline0a2a88a7-9efd-4ecd-bb48-b0d661fa46f5; comparisone0458d65-0f81-40ee-8fe3-68b093394bf8; effectiveABSURD_PHYSICS /SEEDANCE_2_0_MINI /15s /image2video /480p /9:16. Any later approved revision would need its own correct prompt-version/evaluation binding; none was created here.

F8 remainsBLOCKED_PENDING_EVIDENCE: authoritative verifiedMimi reference absent/unverified, accepted startFrame missing. Step7 preparation requires those inputs bound to the exact current prompt; subsequent evaluation/visual evidence must remain fresh and source-bound. First-frame and silhouette gates, required execution inputs and final independent QA/authorization must pass before any render authorization. An improved text score cannot grant that authorization. Visual preparation does not resolve the demonstrated parser defects.

## Verification and safety

Read-only live record retrieval; three exact-score recomputations; additive46-rule contribution checks for all three; camera-directive diagnostic restoring A toOriginal; paired note/card physical-motion controls; genuine “Mimi keeps pulling...” positive attempt control; current lineage, old comparison staleness and unchanged current analysis checked. Provider construction was blocked in diagnostic runs. Saved analysis/comparison snapshots and reproduction evidence accompany this report.

No OpenAI/provider calls, candidate generation, prompt approval, image/video generation, publishing, stored-score manipulation, history modification, commit/push, application-code edit or deployment was performed in this review.
