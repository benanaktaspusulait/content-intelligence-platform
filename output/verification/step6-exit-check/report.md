# Step 6 final exit check

**STEP_6_EXIT_CHECK_BLOCKED** — motion defect repaired, deployed and officially re-evaluated. Recommendation: **KEEP_ORIGINAL**. The remaining exit blocker is the existing no-repair approval eligibility policy, not an unfinished parser repair. No approval was submitted and no policy guard was weakened.

## Motion defect and shared repair

`PromptParser._estimate_motion_amount` used `"no" in description.lower()`, so note/notes established `motionAmount=none`. All five saved beats of Original/A/B were incorrectly marked motionless. A separate literal `static` check also treated A's static camera as a static subject; B's no-pause instruction was unrelated motion negation. Merely adding word boundaries around `no` leaves these false signals.

Ruleset **1.10**, extending frozen 1.9, selects **TOKEN_MOTION_V2**. Motion keywords are token-bound; negative immobility evidence requires a motion predicate (no motion/movement), explicit motionless/stationary/static state, or a stillness predicate. Temporal “still pulling”, no dialogue, no pause and note/notes do not establish immobility. Static camera/shot directives are scoped separately, retaining actor actions in mixed descriptions. Existing intensity precedence and moderate fallback remain heuristic. Each new beat retains exact source quote/span plus motionEvidence labelled INFERRED, semantic/visual verification NOT_PERFORMED. No render success is inferred.

Frozen 1.7/1.8/1.9 use HISTORICAL_V1. No historical YAML, record, story, prompt or score was overwritten. No rule weight, threshold, outcome evaluator, grade boundary or attempt policy changed.

## Exact canonical effect

| Input | Frozen 1.9 | Official 1.10 | Delta |
|---|---:|---:|---:|
| Original Prompt 10 | 82.80208333333336 / B | 84.20833333333334 / B | +1.40625 |
| Candidate A | 82.80208333333336 / B | 84.20833333333334 / B | +1.40625 |
| Candidate B | 82.80208333333336 / B | 84.20833333333334 / B | +1.40625 |

All five beats now estimate moderate motion. **MOTION_001 is the only changed rule outcome: FAIL → PASS.** Previously the supposed longest motionless beat was 5s; now 0s. The 1.9 motion-family score55 becomes70, giving `(70−55)×0.09/0.96 = 1.40625`. This follows the unchanged existing aggregation implementation; the rise corrects parser evidence and does not establish better creativity. There are46 rule records:23PASS,6FAIL,10UNKNOWN,7NOT_APPLICABLE. Other45 outcomes are unchanged.

**CONTINUOUS_ACTION_MOMENTUM remains FAIL.** Its evidence changes from passive7s/46.7% to0s/0%. Attempt gap remains0s; standalone reaction count remains0; finalAftermathSeconds remains3s, above the unchanged1.5s limit. That last metric sums non-attempt beats starting at finalPayoff.startsAt=12s. Here it includes the actual sneeze/scatter/landing ending; it is not proof of a three-second motionless hold. No new claim that the ending is visibly defective is warranted. No unrelated MOMENTUM-policy refactor was made. Full per-rule before/after entries are in deterministic-evaluation.json; family arithmetic in family-score-proof.json.

## ATTEMPT_001 policy confirmation

Architecture documentation (`QUALITY_FAMILY_SCHEMAS.md`, Attempt Count implementation; `VIDEO_PLAN_IR_SCHEMA.md`, Duration Tiers) specifies3attempts for duration≤20s and7 for longer videos. The inherited rule description and evaluator agree. 1.8's explicit profile exclusions are CURIOSITY_ADVENTURE and EDUCATIONAL; ABSURD_PHYSICS is not excluded. Content10 has authoritative ABSURD_PHYSICS/15s production settings, so this policy applies.

The two source-bound attempts are PEEL at2–5s and PULL at5–10s. Opening REACH is setup, static camera is a directive, and the ending sneeze is not a third problem-solving attempt. The rule therefore remains FAIL/BLOCKER with count2 and required3. Its existing zero contribution remains; no extra attempt was fabricated, source events added, or weights adjusted. This confirms implementation fidelity to the documented policy; it does not justify changing the approved story merely to satisfy the metric.

## Official records and deployment

Current authoritative Content10 / Prompt10 analysis: **05726ece-caaf-483a-a0af-d93e91a76c88**.

Current local revalidated comparison: **c16eb200-1381-478b-ad62-9578ea2f9be2**.

`intelligence/scripts/deploy.sh ml-service` rebuilt and deployed the affected service. Readiness returns UP/ruleset_version1.10. Image: `sha256:dbb9542b991cd6e3ebfb937a7dc9c3fbb8b202158f7f06dc45a4ab60406f640a`. Full deployment checks passed; backend/frontend unchanged.

Official POST `/api/v1/intelligence/workflow/review` loaded immutable Prompt10 through the backend; the request omitted options.prompt. POST `/records/{newAnalysisId}/creative-optimization/revalidate` reused the existing root comparison7291a6c5-07a0-4b4e-b033-09680889224a, with no provider dispatch or new candidate generation. Official canonical responses exactly match deterministic results for all three inputs. Selection and approval remain null. Previous1.9 analysis38a57f84-b61a-470c-8342-cd522bdbd38e remains immutable historical evidence.

## Current comparison and exit decision

**KEEP_ORIGINAL**. A retains a plausible joint cabinet/finger staging hypothesis. B retains the same essential progression with different shot emphasis. Neither has demonstrated a canonical advantage, validated risk reduction, generator success or audience benefit. Semantic story fidelity remains UNKNOWN; preserved source-event coverage is not semantic certification. Existing comparison software may label a source-bound staging intervention VALID_WITH_UNPROVEN_BENEFIT / REVIEW_MATERIAL_CANDIDATE; that is a textual materiality classification, not proof of improvement. It was not changed or auto-approved.

The explicit **NO_TEXT_REPAIR_JUSTIFIED** path exists in the frontend and backend, but **is not available for this actual run**. Frontend `requiredTextRepair` treats any canonical FAIL as requiring review. Backend `saveProductionReviewDecision` rejects a no-repair decision whenever canonical.failedRules is nonempty. The current six failures are:

- BEAT_004: a single normalized visual state occupies33.3%, limit30%.
- ATTEMPT_001: two attempts, minimumthree under the applicable policy.
- PRODUCIBILITY_003: FACE_CONTACT and THIN_OBJECT risk tags.
- CONTINUOUS_ACTION_MOMENTUM: finalAftermathSeconds3, limit1.5 (metric caveat above).
- INSTANT_VISUAL_ABSURDITY_GATE: missing first-frame visual evidence.
- ENGINE_SILHOUETTE_DUPLICATE: missing first/final silhouette comparison evidence.

Some failures are evidence requirements or production risks, rather than confirmed repairable text defects. Nevertheless the existing no-repair guard rejects all of them. A KEEP_ORIGINAL recommendation is not a bypass. Resolving that eligibility/policy distinction requires a separate explicit decision; this motion-only repair does not silently broaden approval authority. No production approval request was sent, even for probing. Existing disposable-DB regression tests verify explicit confirmation, successful eligibility for appropriate runs, stale-analysis rejection and canonical-failure rejection.

## Step 7 readiness

No render authorization. F8 remains **BLOCKED_PENDING_EVIDENCE**:

- Verified Mimi reference association is MISSING.
- Accepted start frame is missing for image2video; the production configuration requires it.
- Explicit Step6 operator approval/eligible exit remains unresolved as described above.
- Any later approval and downstream canonical/render authorization must bind Content10/Prompt10 to the current1.10 analysis and exact settings, not a historic1.7/1.8/1.9 comparison. No new prompt version exists or is required by this check alone.

15s / SEEDANCE_2_0_MINI / image2video /480p /9:16 capability is supported in saved capability evidence, but actual visual quality and execution are unverified. Missing first-frame/silhouette evidence remains missing. Improving a text score does not authorize a render.

## Verification and files

- 327 ML/parser/canonical/legacy/Step5/Step6/F8/optimization/autofix tests passed, including19 new motion tests (16classification cases +3saved end-to-end canonical comparisons). Focused motion rerun also passed. Provider acquisition is explicitly forbidden by mocks in saved-case tests.
- 19 backend tests passed,3optional live/mock integration cases skipped;0failures. Testcontainers database is disposable and separate from production.
- 69 frontend workflow regressions passed. No frontend implementation changed.
- Nine frozen golden assets each under1.7,1.8,1.9: report, dimensions, canonical evidence, aggregation and IR match previous snapshots exactly. JSON normalization accounts for tuple/list serialization. Archived golden expectations were not rewritten.
- Historical production record MD5s, all Content10 prompt text MD5s and total CREATIVE_ROLE count are identical before/after. Only authorized new REVIEW/CREATIVE_OPTIMIZATION records were appended by official endpoints.
- Ruff on the new tests and git diff --check pass.

Changed implementation files: `parser/prompt_parser.py`, `workflow/review.py`, `workflow/api.py`, `rules/rule_engine.py`, `api/quality.py`, `autofix/iteration_loop.py`, `golden/deterministic_runner.py`; new `RULESET_1.10.yaml` plus versions.yaml registration; new `test_motion_token_policy.py`; four existing release-registry tests updated only for latest-version assertions. All live/deterministic requests, responses, exact diffs, hash proof and logs are beside this report.

No paid provider calls, optimization generation/retries, prompt/story edits, image/video generation, publishing, automatic approval, production SQL writes, commit or push.
