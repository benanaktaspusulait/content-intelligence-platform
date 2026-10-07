# Family 5 Session Summary

**Session scope:** POMPOM Golden calibration — Family 5 specialized rule applicability  
**Golden set:** `POMPOM_GOLDEN_V1`  
**Ruleset:** `RULESET_1.7`  
**Final status:** **APPROVED / FROZEN WITH DOCUMENTED WAIVER**

This document records what was investigated, designed, implemented, validated, deferred, and explicitly left unchanged during the session.

## 1. Starting context

Before this session:

```text
Family 1 — Strategy / Attempt                 FROZEN
Family 2 — Escalation                         FROZEN
Family 3 — Goal / Realization                 FROZEN
Family 4 — Mechanic / Fake Resolution /      FROZEN
             Recurrence / Payoff
Family 5 — Specialized Rule Applicability    REVIEW ONLY
Family 6+                                      NOT STARTED
```

Family 5 was initially a Gold Review only. The first objective was to inspect the effective runtime and existing Golden evidence without changing parser behavior, canonical evidence, RuleEngine behavior, scoring, rulesets, policy expectations, or Gold Truth.

## 2. Hard constraints maintained

The following boundaries were enforced throughout the implementation:

- No Family 1–4 semantic changes.
- No parser redesign or parser behavior change.
- No RuleEngine evaluator or evaluator-gating change.
- No RULESET 1.7 or immutable ruleset change.
- No scorer, creative grade, blocker/critical count, or render-authorization change intended by Family 5.
- No performance data or corpus-role input.
- No Family 6+ work.
- No Meta/public-comment work.
- No policy threshold or policy expectation change.
- No RULESET 1.8.
- Applicability remained separate from RuleEngine outcome.

## 3. Initial Family 5 runtime audit

The effective runtime was inspected rather than assuming a specialized-rule list.

`RULESET_1.7.yaml` extends `RULESET_1.6.yaml`, but the current loader resolves only the immediate base. The effective RULESET 1.7 contains eight entries:

```text
MINI_STORY_LOCK
GOAL_VISIBLE_EARLY
TEMPORAL_COMPLEXITY_SPLIT_GATE
BEAT_DENSITY_RULE
CONTINUATION_LOCK
STUBBORN_RETURN_LOOP
STUBBORN_RETURN_HOOK
STUBBORN_RETURN_PAYOFF
```

The actual Family 5 specialized targets are only:

```text
STUBBORN_RETURN_LOOP
STUBBORN_RETURN_HOOK
STUBBORN_RETURN_PAYOFF
```

`CONCEPT_009` is a specialized historical `RULESET_1.5` declaration but is not effective in the current RULESET 1.7 runtime because inheritance is not transitive. Generic rules such as `MINI_STORY_LOCK`, `BEAT_DENSITY_RULE`, and `GOAL_VISIBLE_EARLY` were not promoted into Family 5 merely because they consume semantic evidence.

The audit also found that:

- `engine_profile_evidence()` is the existing runtime profile selector;
- current specialized RuleEngine outcomes for the eight parsed assets were `LOOP=UNKNOWN`, `HOOK=NOT_APPLICABLE`, `PAYOFF=NOT_APPLICABLE`;
- Upside-Down Chair is a parser timeout with no RuleEngine evaluation;
- assessment exposes `engine_profile` at the top level;
- assessment dimensions do not contain `ENGINE_PROFILE`;
- the old comparator therefore projected aggregate specialized applicability as `null`;
- current RuleEngine outcome buckets already distinguish `UNKNOWN` from `NOT_APPLICABLE`;
- non-applicable outcomes are excluded from scoring subsets rather than converted to creative zero.

## 4. Gold Review corrections

The initial review proposed `UNKNOWN` for Upside-Down Chair and Spot Cat. Human review corrected both labels before lock:

### Upside-Down Chair

Changed from `UNKNOWN` to `NOT_APPLICABLE`.

Reason: the frozen Family 4 mechanic is `AUTONOMOUS_CHAIR_INVERSION`. The chair turning upside down is a different established mechanic, not insufficient evidence for a stubborn return/reclaim profile. The parser timeout is a runtime evidence problem and must not leak into source-backed Gold Truth.

### Spot Cat

Changed from `UNKNOWN` to `NOT_APPLICABLE`.

Reason: the frozen mechanic is `REPEATED_TARGET_CLAIM`; Family 1 records three attempts but one strategy family, `COMMIT_TO_TARGET`. Changing target spots and repeatedly claiming the committed spot is not the same as one entity being displaced and autonomously reclaiming a fixed boundary.

### Final approved matrix

| Asset | `STUBBORN_RETURN_LOOP` | `STUBBORN_RETURN_HOOK` | `STUBBORN_RETURN_PAYOFF` |
|---|---|---|---|
| Sticky Ball | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Ball-Multiplying Crocodile | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Upside-Down Chair | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Lamp | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Snack Box | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Box Cat | `APPLICABLE` | `UNKNOWN` | `APPLICABLE` |
| Spot Cat | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Sneaky Door | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| Island Journal | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |

## 5. Approved architecture: Approach A

The approved architecture deliberately separates applicability from RuleEngine outcome:

```text
Canonical Evidence
      ↓
Assessment
      ↓
Golden comparator
      ↓
API / backend / PDF
      ↓
Frontend UI
```

The canonical contract is a rule-id keyed collection:

```json
{
  "specializedApplicability": {
    "STUBBORN_RETURN_LOOP": {
      "status": "APPLICABLE | NOT_APPLICABLE | UNKNOWN",
      "confidence": "HIGH | MEDIUM | LOW",
      "evidenceReferences": [],
      "reason": "..."
    },
    "STUBBORN_RETURN_HOOK": {},
    "STUBBORN_RETURN_PAYOFF": {}
  }
}
```

The new map does not enter:

- `RuleEvaluation`;
- RuleEngine evaluator gates;
- family scores;
- creative grade or creative score;
- evidence coverage denominators;
- render authorization;
- policy fields.

This allows a visible and measurable divergence such as:

```text
canonical applicability: Box Cat / LOOP = APPLICABLE
current RuleEngine outcome: STUBBORN_RETURN_LOOP = UNKNOWN
```

The runtime behavior is not changed to hide the divergence.

## 6. Sequential implementation tasks

### Task 1 — Gold Truth lock

Changed:

- `intelligence/data/golden/pompom-golden-v1/truth/gold_truth.yaml`
- `intelligence/ml-service/tests/test_pompom_golden_truth_schema.py`

Work:

- Removed the aggregate as authoritative truth.
- Added three rule-id-keyed authoritative dimensions for all nine assets.
- Set `applicable: true` because the dimension asserts applicability status itself.
- Set all approved entries to `reviewStatus: APPROVED`.
- Preserved Family 1–4 dimensions and source metadata.

Validation:

```text
Truth schema tests: 3 passed
```

Task review: **APPROVED**.

### Task 2 — Canonical per-rule applicability

Changed:

- `intelligence/ml-service/app/quality/canonical_evidence.py`
- `intelligence/ml-service/tests/test_family5_specialized_applicability.py`

Added:

- `SPECIALIZED_RULE_IDS`
- `SpecializedApplicabilityEvidence`
- `specialized_applicability_evidence(video_plan_ir)`

Behavior:

- Box Cat → `APPLICABLE / UNKNOWN / APPLICABLE`.
- Spot Cat → all `NOT_APPLICABLE`.
- Sticky, Crocodile, Lamp, Snack, Sneaky Door, Island → all `NOT_APPLICABLE` with usable IR.
- Missing IR → all `UNKNOWN` with unavailable-evidence reason.
- Evidence references come from existing canonical mechanic/attempt beat IDs.
- RuleEngine evaluator outputs remain separate.

Validation:

```text
Focused Family 5 + Family 4 + RULESET 1.7 tests: 25 passed
```

Task review: **APPROVED**. Minor note: one serialization test initially checked field keys more strongly than all values; implementation and broader tests still validated the values.

### Task 3 — Snapshot, assessment, and API propagation

Changed:

- `intelligence/ml-service/app/golden/deterministic_runner.py`
- `intelligence/ml-service/app/assessment/pre_render_assessment.py`
- `intelligence/ml-service/app/api/quality.py`
- representation/API tests

Added:

```text
canonicalEvidence.specializedApplicability
assessment.specialized_applicability
PreRenderAssessmentResponse.specialized_applicability
```

The map is not added to dimensions, coverage, evidence completeness, or RuleEngine outcome buckets.

Validation:

```text
Focused Task 3 representation/API tests: 23 passed
```

Task review: **APPROVED**.

### Task 4 — Golden projection and comparator

Changed:

- `intelligence/ml-service/app/golden/comparator.py`
- `intelligence/ml-service/tests/test_golden_comparator.py`
- `intelligence/ml-service/tests/test_pompom_golden_baseline.py`

Behavior:

- Canonical snapshot map is preferred.
- Historical snapshots without the new map are recomputed from usable IR.
- No-IR/parser-timeout snapshots preserve unavailable/stored values.
- Three independent assertion names are emitted:

```text
SPECIALIZED_RULE_APPLICABILITY:STUBBORN_RETURN_LOOP
SPECIALIZED_RULE_APPLICABILITY:STUBBORN_RETURN_HOOK
SPECIALIZED_RULE_APPLICABILITY:STUBBORN_RETURN_PAYOFF
```

- Legacy aggregate is not an authoritative assertion.
- `UNKNOWN` and `NOT_APPLICABLE` compare as exact distinct values.
- Existing confidence semantics were preserved:
  - HIGH mismatch → `REGRESSED_FROM_BASELINE`;
  - MEDIUM mismatch → `GOLD_REVIEW_REQUIRED`.

A plan divergence was found and resolved by choosing HIGH confidence for the synthetic regression case plus a separate MEDIUM-confidence review case. Existing comparator semantics were not changed.

Validation:

```text
Focused comparator/baseline tests: 20 passed
Related Family 5/schema/representation tests: 32 passed
Full ML suite at task stage: 498 passed
```

Task review: **APPROVED**.

### Task 5 — Backend/PDF representation

Changed:

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportPdfService.java`
- `QualityReportDtoTest.java`
- `QualityReportPdfServiceTest.java`

Behavior:

- Existing `preRenderAssessment` map remains the lossless backend container.
- PDF receives a separate neutral applicability table:

```text
Rule | Applicability | Confidence | Reason | Evidence
```

- `UNKNOWN` and `NOT_APPLICABLE` stay literal and are not rendered as failures.
- Existing outcome coverage table remains separate.

Validation:

```text
QualityReportDtoTest + QualityReportPdfServiceTest: passed
Task-scoped Spotless: passed
```

Task review: **APPROVED**.

### Task 6 — Frontend

Changed:

- `quality-validator.component.ts`
- `quality-validator.component.html`
- `specialized-applicability.ts`
- `specialized-applicability.spec.ts`

Behavior:

- Stable rule order is preserved.
- Status, confidence, reason, and evidence references are displayed from `preRenderAssessment.specialized_applicability`.
- Missing data maps to neutral `UNKNOWN / LOW` rows.
- No derivation from `videoPlanIr` and no new API service.

Validation:

```text
Focused frontend mapper: 2 passed
Production build: passed
```

Task review: **APPROVED**. Minor note: focused coverage is mapper-level rather than DOM-level; production template compilation passed.

### Task 7 — Full validation and waiver

Validation executed:

```text
Focused ML: 47 passed
Full ML: 498 passed
Backend DTO/PDF: passed
Frontend focused mapper: 2 passed
Frontend production build: passed
Golden assertions: 314
New semantic regressions: 0
Unexpected policy regressions: 0
Formal Golden release gate: PASS
```

A strict before/after comparison found generic baseline drift for Box Cat and Spot Cat:

```text
GOAL_VISIBLE_EARLY: FAIL → PASS
BEAT_DENSITY_RULE: FAIL → PASS
score: 38.2954545 → 61.8181818
criticals: 2 → 0
creative grade: F → F
render authorization: BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE
```

The three specialized RuleEngine outcomes remained unchanged across 24 comparisons. The drift is therefore outside Family 5 specialized applicability and was accepted as a documented waiver rather than repaired in scope.

Task review status: final formal gate **PASS**; strict generic isolation **waived and documented**.

## 7. Investigation result for the waived drift

A separate read-only investigation established:

- Prompt hashes are identical between baseline and current.
- Baseline was captured at commit `4dde76e`.
- Current snapshot records commit `72e59a3`.
- Parser Markdown-section fallback was added in `878e0e5`.
- Baseline parser output for Box Cat/Spot Cat had no beats and unknown goal evidence.
- Current parser output has five Markdown-derived beats and explicit goal evidence.
- `GOAL_VISIBLE_EARLY` changes because `goalEvidence` changes from `UNKNOWN` to `EXPLICIT` and the current first beat starts at `0.0`.
- `BEAT_DENSITY_RULE` changes because canonical major beats change from `0` to `5`.
- The evaluator implementations and thresholds do not need to change to explain the drift.
- The drift is parser/provenance related and semantically independent of Family 5, while still passing through a shared parser/IR dependency.

Investigation report:

```text
intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_INVESTIGATION_REPORT.md
```

Separate deferred work item:

```text
intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_FOLLOWUP.md
```

The follow-up must not change Family 5, Family 1–4, scoring, baseline, or generic evaluator behavior until explicitly opened as a separate task.

## 8. Final status

```text
Family 1 ✅ FROZEN
Family 2 ✅ FROZEN
Family 3 ✅ FROZEN
Family 4 ✅ FROZEN
Family 5 ✅ APPROVED / FROZEN WITH DOCUMENTED WAIVER
Family 6+ ⏸ NOT STARTED
```

Master is the active checkout. The isolated Family 5 worktree remains preserved for historical/task diagnostics because the generic baseline follow-up is deferred.

## 9. Files and artifacts created or updated

### Family 5 implementation/report artifacts

- `intelligence/data/golden/pompom-golden-v1/truth/gold_truth.yaml`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/current.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/golden-regression-report.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/golden-regression-report.md`
- `intelligence/docs/FAMILY_5_GOLD_REVIEW_REPORT.md`
- `intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_FOLLOWUP.md`
- `intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_INVESTIGATION_PROMPT.md`
- `intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_INVESTIGATION_REPORT.md`

### Design/process artifacts

- `docs/superpowers/specs/2026-10-06-family-5-specialized-applicability-design.md`
- `docs/superpowers/plans/2026-10-06-family-5-specialized-applicability.md`

### Main code areas touched by Family 5

- ML canonical evidence, deterministic snapshots, assessment, API conversion, comparator, and tests.
- Backend quality PDF representation and DTO/PDF tests.
- Frontend quality-validator assessment presentation and mapper tests.

No Family 6 implementation or Meta/public-comment implementation was started in this session.
