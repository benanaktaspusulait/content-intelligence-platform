# Rule Engine corrections — Ruleset 1.8

Status: **RULE_ENGINE_CORRECTIONS_DEPLOYED**. Functional dispatch and applicability corrections are versioned; unchanged golden/archive failures and evidence limitations remain listed below.

## Root causes and exact corrections

1. `rule_engine.py:_load_ruleset` merged only the immediate base YAML. 1.7 therefore saw five rules from1.6 and three rules from1.7, omitting all38 rules in1.5. No missing evaluator registration was found: all38 have registered evaluators and active declarations. Ruleset1.8 opts into recursive ancestry with cycle, missing-file, duplicate-ID and explicit-override validation. Ruleset1.7 retains its previous shallow loader and eight-rule behavior. Existing immutable YAML versions were not edited.
2. The historical inferred engine-profile constructor marked any nonzero generic signal count candidate-only, including LOW/DEFAULT non-return concepts. 1.8 adds a source-domain gate distinguishing multiplication/persistence from autonomous return. A supported non-return mechanic is NOT_APPLICABLE; supported but incomplete autonomous-return or explicit unresolved return-profile evidence is UNKNOWN; all required genuine return signals can activate PASS. No character-specific exception exists. Recurrence alone is insufficient for autonomous return.
3. Restoring legacy dispatch exposes semantic checks that formerly were unreachable in this workflow. The new version's local `EXISTING_EVIDENCE_ONLY` policy blocks provider construction/calls and preserves UNKNOWN when an applicable judgment is not verified. It does not convert missing evidence to PASS. Historical ruleset semantics are not rewritten. A no-provider mock that raises on any provider construction is part of the regression suite.

No scoring constant, severity declaration, family weight, threshold, approved story, prompt text or Prompt VersionID10 changed.

`RULESET_1.8.yaml` and the existing `versions.yaml` release registry record a breaking dispatch/applicability release. Historical explicit1.7 evaluates the three saved prompt strings as85/B, eight rules, unchanged. Golden1.7 assertions also match the prior deployed engine exactly.

## Legacy rule audit

All38 declarations are active and registered. They enter the corrected dispatcher, then existing stage/scope/evidence contracts apply. This is not unconditional PASS or unconditional scoring. Three legacy rows are NOT_APPLICABLE for Content10: CONSISTENCY_002 needs POST_RENDER pixels, PAYOFF_005 needs an actual fake-win beat, and CONCEPT_009 is scoped to `social_reel`, which is not established in this parsed source. The unchanged continuation and three return-family rows account for the other four NOT_APPLICABLE rows.

The established profile-admission exclusions are carried into1.8 for CURIOSITY_ADVENTURE and EDUCATIONAL; authoritative operational routing supplies the effective profile. ABSURD_PHYSICS uses the applicable mechanics rules. Retirement and content-family scopes are preserved. Semantically unresolved rules remain UNKNOWN. Exact per-rule input descriptions, consumed fields, evaluator names, applicability docstrings, exclusion profiles and actual reasons are in legacy-dispatch-audit.json.

| Legacy rule | Registry/status | Scope | Stage | Content10 outcome |
|---|---|---|---|---|
| CONCEPT_006 | yes / active | GLOBAL | PRE_RENDER | PASS |
| BEAT_004 | yes / active | GLOBAL | PRE_RENDER | FAIL |
| REPETITION_002 | yes / active | GLOBAL | PRE_RENDER | PASS |
| REPETITION_003 | yes / active | GLOBAL | PRE_RENDER | PASS |
| NOVELTY_001 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PROGRESSION_005 | yes / active | GLOBAL | PRE_RENDER | PASS |
| ESCALATION_004 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PAYOFF_001 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PRODUCIBILITY_001 | yes / active | GLOBAL | PRE_RENDER | PASS |
| CONSISTENCY_001 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| HOOK_002 | yes / active | GLOBAL | PRE_RENDER | PASS |
| HOOK_003 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| MOTION_001 | yes / active | GLOBAL | PRE_RENDER | FAIL |
| ATTEMPT_001 | yes / active | GLOBAL | PRE_RENDER | FAIL |
| CHAR_002 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PRODUCIBILITY_002 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PAYOFF_002 | yes / active | GLOBAL | PRE_RENDER | PASS |
| ATTEMPT_002 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| PAYOFF_003 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| CONSISTENCY_002 | yes / active | GLOBAL | POST_RENDER | NOT_APPLICABLE |
| CONCEPT_007 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| BEAT_005 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PAYOFF_004 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PAYOFF_005 | yes / active | GLOBAL | PRE_RENDER | NOT_APPLICABLE |
| REPETITION_004 | yes / active | GLOBAL | PRE_RENDER | PASS |
| PAYOFF_006 | yes / active | GLOBAL | PRE_RENDER | PASS |
| GOAL_001 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| CONCEPT_008 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| PROGRESSION_006 | yes / active | GLOBAL | PRE_RENDER | PASS |
| ESCALATION_005 | yes / active | GLOBAL | PRE_RENDER | PASS |
| HOOK_004 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| PERFORMANCE_001 | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| PRODUCIBILITY_003 | yes / active | GLOBAL | PRE_RENDER | FAIL |
| GENERATION_EXECUTABLE_ATTEMPTS | yes / active | GLOBAL | PRE_RENDER | UNKNOWN |
| CONTINUOUS_ACTION_MOMENTUM | yes / active | GLOBAL | PRE_RENDER | FAIL |
| INSTANT_VISUAL_ABSURDITY_GATE | yes / active | GLOBAL | PRE_RENDER | FAIL |
| ENGINE_SILHOUETTE_DUPLICATE | yes / active | GLOBAL | PRE_RENDER | FAIL |
| CONCEPT_009 | yes / active | CONTENT_FAMILY:social_reel | PRE_RENDER | NOT_APPLICABLE |

## Exact scores and changes

| Input | Historical1.7 | Corrected1.8 | PASS | FAIL | UNKNOWN | NOT_APPLICABLE |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 85 / B | 82.80208 / B | 22 | 7 | 10 | 7 |
| candidate-a | 85 / B | 86.96875 / B | 23 | 6 | 10 | 7 |
| candidate-b | 85 / B | 82.80208 / B | 22 | 7 | 10 | 7 |

Each row has46 rule records under the same corrected configuration. The official baseline and candidate results match these offline results. Of the newly restored38 baseline rows,18PASS,7FAIL,10UNKNOWN and3NOT_APPLICABLE.

Arithmetic remains the existing per-rule → family average → normalized family-weight average. PASS evaluates to100 when the existing evaluator returns severityPASS, otherwise85. FAIL is BLOCKER0, CRITICAL40, otherwise70. UNKNOWN, NOT_APPLICABLE, evidence gaps and other unscored states are omitted from numeric denominators; null families are omitted from overall weight. The legacy evaluators' existing PASS severity behavior is preserved, not introduced here. A>=92, B>=80, C>=60, F<60.

Original andB: weighted numerator79.49 / scored-family weight0.96 =82.8020833333. A:83.49 /0.96 =86.96875. Full per-rule numeric values, evidence-gap exclusions, family means/weights and reasons are in offline-evaluations.json.

A's sole outcome difference from the corrected baseline is ATTEMPT_001 FAIL→PASS: parsed active-attempt count2→3. That rule contributes0→100 within the concept family; its family score rises61.6667→95, adding4 to the weighted numerator, or4.1667 overall. B has no outcome change. This is a deterministic parser/gate response; it does not establish better audience response or independent semantic fidelity. A's source-action parsing/verb label deserves operator review before treating this numerical difference as a creative benefit.

STUBBORN_RETURN_LOOP UNKNOWN→NOT_APPLICABLE removes an unsupported applicability diagnostic, and contributes no numerical increase because both outcomes were unscored.

Controlled deterministic tests cover delayed versus early goal visibility, genuine temporal overload, multiplication/persistence without autonomous return, supported return, incomplete return evidence, profile/stage exclusions, registry/severity preservation and malformed inheritance. Existing action/consequence, escalation, source-contract and optimization tests also passed.

## Golden governance and regressions

Frozen source prompts, reviewed truth,1.7 policy expectations, and historical baselines were not changed. All323 assertions across the nine historical golden assets are identical when run using the prior deployed engine and the updated explicit1.7 engine. Introduced semantic/policy regressions:0.

The archived baseline gate already reports4 semantic regressions and2 policy regressions; the same counts occur before and after this correction. The unrelated Island Journal escalation test also already fails against the unchanged parser/evidence path. It was explicitly deselected only for the scoped green run; the full failing run is retained, and it was not presented as fixed.

Corrected1.8 golden snapshots were generated separately: eight assetsOK, Upside Chair retains a bounded parser timeout. The baseline harness's top-level wrapper label is still hardcoded1.7; actual per-asset fingerprints and engine results identify1.8. golden-corrected-summary.json records this tooling limitation without relabeling an archived policy expectation as passing.

Tests:380 scoped ML tests passed; full run380passed/1unrelated failure. All22 backend tests passed with all mocked-provider and real deployed-ML/Testcontainers integration cases enabled,0skipped. Frontend69focused tests passed, production build passed. Previously observed unrelated full frontend VideoDetail failures remain out of scope; no claim they are fixed. git diff --check passed.

## Official re-evaluation, immutable history and Step6

Official POST `/api/v1/intelligence/workflow/review` created new saved analysis **0a2a88a7-9efd-4ecd-bb48-b0d661fa46f5**, Content10 / Prompt VersionID10 / Ruleset1.8 /82.8020833333/B. This used stored prompt bytes and authoritative evidence adapters, not a unit-test fixture.

New local-only POST `/api/v1/intelligence/workflow/records/{analysisId}/creative-optimization/revalidate` created comparison **e0458d65-0f81-40ee-8fe3-68b093394bf8** from saved comparison7291a6c5-07a0-4b4e-b033-09680889224a. Both exact candidate prompts were re-evaluated through the deployed source-plan and review paths; no Creative Optimization provider was called. New comparison lineage is valid; selection and approval are null. Revalidation is idempotent. Candidate evaluation is pinned to the saved baseline's authoritative ruleset version.

The original provider record/context keeps its original analysis binding; the new comparison records its revalidation ancestry instead of rewriting that provider evidence. Historical comparison's current read model is stale, lineageVerified=false, and both approvalEligible=false. Its persisted payload remains unchanged.

Checksums for historical analysis9208e75a-b158-4ffb-94fe-03c15ca96395, historical comparison7291a6c5-07a0-4b4e-b033-09680889224a, provider record62cf4323-ea96-410f-b9c4-545664e18078, every Content10 prompt text, and total creative-role record count match before/after. No new prompt version or provider attempt was created. No direct production SQL update occurred; all production writes used authorized append-only workflow endpoints.

Step5/6 browser verification shows the current1.8 evaluation/provenance. Both actual Review buttons focus and scroll to the right heading while selection stays empty and Approve remains disabled. Fractional score display is rounded to two decimal places only; stored numeric values remain exact. No candidate was approved.

## Remaining issues and recommendation

The restored rules expose genuine gates and evidence limitations previously hidden: a5s visual-state hold, parsed motionless duration, limited active-attempt count in the original/B, fragile thin-object/face contact, action-momentum classification, and missing first-frame/silhouette evidence. Evidence-gap rows do not become numerical penalties merely because they are reported as blocked pre-render gates. Ten unresolved judgments remain UNKNOWN; approved-story semantic fidelity and actual generator success are unproven.

F8 remains BLOCKED_PENDING_EVIDENCE for missing verified Mimi reference and accepted start frame. No image/video generation, publishing, paid provider retry or automatic approval occurred. No commit/push command was executed.

Recommendation: **review the newly visible source/plan findings before another optimization attempt**. Do not pay for another rewrite simply to chase a higher score. Step7 visual preparation can address the reference/first-frame evidence requirements, but it does not bypass the current canonical repair/gate review or grant render authorization. The Step5 operational “next evidence step” recommendation and Step6 canonical “text repair required” guard come from separate existing decision layers; the no-repair continuation control is disabled for this new analysis.

Deployment commands, running image IDs, health/version checks, live API responses, test logs and browser captures are retained beside this report.

## Files changed

- intelligence/data/rules/RULESET_1.8.yaml and versions.yaml: new governed policy; old YAML unchanged.
- intelligence/ml-service/app/rules/rule_engine.py: versioned recursive loader, guarded semantic boundary, source-domain profile use, retirement/profile dispatch.
- intelligence/ml-service/app/quality/canonical_evidence.py: generic return-domain applicability.
- intelligence/ml-service/app/workflow/review.py and api.py: explicit ruleset selection, effective profile, version-bound fingerprint.
- intelligence/backend/.../workflow/WorkflowService.java and WorkflowController.java: local immutable candidate revalidation, baseline ruleset pinning, revalidation ancestry and refreshed derived risk/unknown read models.
- intelligence/frontend/.../post-family-workflow.component.ts: decimal score/delta display only; exact stored numbers preserved.
- Dedicated ML1.8/history/registry tests, backend live-ML/Testcontainers integration and frontend regression coverage/fixtures.

No frontend layout redesign or candidate-generation/scoring-formula rewrite was performed.
