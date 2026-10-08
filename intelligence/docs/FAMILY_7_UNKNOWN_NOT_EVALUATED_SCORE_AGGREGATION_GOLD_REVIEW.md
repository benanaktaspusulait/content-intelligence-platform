# FAMILY 7 — UNKNOWN / NOT_EVALUATED / SCORE AGGREGATION
## Read-only Gold Review

**Review status:** READ-ONLY AUDIT — IMPLEMENTATION NOT STARTED  
**Golden set:** `POMPOM_GOLDEN_V1`  
**Ruleset observed:** `RULESET_1.7`  
**Scope:** Preserve semantic meaning when evidence is incomplete, unavailable, not applicable, unevaluated, or failed technically.

No parser, canonical evidence behavior, RuleEngine evaluator, ruleset, scorer, grade, render authorization, Gold Truth, policy expectation, baseline, Family 1–6, Meta, or publisher file was changed by this audit. This report is the only requested artifact created by the audit.

## Executive summary

The repository has two partially overlapping status systems:

1. **Python pre-render quality path** — `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`, and `SERVICE_ERROR` are explicit `RuleOutcome` values. `NOT_EVALUATED` is not a Python `RuleOutcome`.
2. **Post-render evidence path** — Java `EvidenceStatus` explicitly contains `AVAILABLE`, `NOT_EVALUATED`, `UNKNOWN`, `SERVICE_ERROR`, and `NOT_APPLICABLE`, but this status is not normalized into the Python `QualityReport`, scoring, API, PDF, or frontend aggregation contract.

The Python RuleEngine correctly keeps `UNKNOWN` and `NOT_APPLICABLE` separate and excludes both from family score numerators. It also makes `SERVICE_ERROR` fail closed at overall status level. However, several Family 7 gaps remain:

- `NOT_EVALUATED` is implicit through missing rows, null snapshots, `PARSER_TIMEOUT`, or post-render fields; it is not a first-class pre-render aggregation status.
- A missing evaluator becomes `SERVICE_ERROR`, not `NOT_EVALUATED`.
- Family score denominator is the evaluable `PASS`/`FAIL` subset, while family evidence coverage uses all RuleEvaluation rows including `UNKNOWN` and `NOT_APPLICABLE`.
- Overall score renormalizes weights over non-null family scores; it is not a global scored-rule denominator.
- If no family is scoreable, `_calculate_overall_score()` returns numeric `0.0`, even though there may be zero evaluated creative evidence. This violates the invariant that zero evaluated items must not be presented as creative zero.
- Parser timeout produces a Golden snapshot with `report=null`, `assessment=null`, and `apiReport=null`, but some historical `dimensionValues` still contain zero/empty values. This can look like measured negative evidence.
- API and backend DTOs preserve five Python outcome lists but do not expose explicit scored denominator, coverage denominator, `NOT_EVALUATED`, or zero-evaluated state.
- PDF preserves the five Python outcome buckets but filters null family scores and does not make missing evaluation rows explicit.
- Angular quality-validator has only the five Python outcomes and groups some unscored states under a generic “not evaluated” presentation.
- The committed v1.7 Golden report is a stale representation relative to newer Family 5/6 comparator capabilities: it has no Family 6 assertions and uses the older Family 5 aggregate shape.

The smallest semantically correct Family 7 model is **not another creative-label matrix**. It should be a versioned aggregation contract consisting of global invariants plus representative boundary fixtures, with per-asset aggregation facts only where a frozen snapshot actually contains rows.

## 1. Repository/runtime sources audited

Authoritative runtime sources inspected:

- `intelligence/ml-service/app/quality/contracts.py`
- `intelligence/ml-service/app/quality/canonical_evidence.py`
- `intelligence/ml-service/app/rules/rule_engine.py`
- `intelligence/ml-service/app/scoring/quality_scorer.py`
- `intelligence/ml-service/app/assessment/pre_render_assessment.py`
- `intelligence/ml-service/app/api/quality.py`
- `intelligence/ml-service/app/golden/deterministic_runner.py`
- `intelligence/ml-service/app/golden/baseline.py`
- `intelligence/ml-service/app/golden/comparator.py`
- `intelligence/data/rules/RULESET_1.5.yaml`
- `intelligence/data/rules/RULESET_1.6.yaml`
- `intelligence/data/rules/RULESET_1.7.yaml`
- `intelligence/data/golden/pompom-golden-v1/manifest.yaml`
- `intelligence/data/golden/pompom-golden-v1/baselines/v1.7/baseline.json`
- `intelligence/data/golden/pompom-golden-v1/reports/v1.7/current.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/current.json`
- `intelligence/data/golden/pompom-golden-v1/reports/v1.7/golden-regression-report.json`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportPdfService.java`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportSnapshots.java`
- `intelligence/frontend/src/app/pages/quality-validator/quality-validator.component.ts`
- `intelligence/frontend/src/app/pages/quality-validator/quality-validator.component.html`
- post-render `EvidenceStatus`/temporal evidence code under `intelligence/creative-render-service`

No Family 7 or Family 8 authoritative specification was found. The conclusions below follow current code and artifacts, not older prose where they disagree.

## 2. Current taxonomy

### 2.1 Python `RuleOutcome`

`intelligence/ml-service/app/quality/contracts.py:29-45` defines exactly five values:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
SERVICE_ERROR
```

The runtime docstring gives the following current meanings:

| Status | Current Python meaning |
|---|---|
| `PASS` | The evaluator produced an explicit passing result. |
| `FAIL` | The evaluator produced an explicit failing result. |
| `UNKNOWN` | The rule applies, but required evidence is missing or indeterminate. |
| `NOT_APPLICABLE` | The rule does not apply to this concept or evaluation stage. |
| `SERVICE_ERROR` | Evaluation was attempted but provider/runtime infrastructure failed. |

`NOT_EVALUATED` is **not** a member of `RuleOutcome`.

### 2.2 Derived `QualityReport` buckets

`QualityReport` derives separate tuples:

```text
passed_rules
failed_rules
service_errors
not_applicable_rules
unknown_rules
```

`RuleEvaluation.passed` is true only for exact `PASS`. It does not treat unknown, not-applicable, or service error as pass.

Important count distinctions:

- `blocker_count` counts only `FAIL` with configured `BLOCKER` severity.
- `critical_count` counts only `FAIL` with configured `CRITICAL` severity.
- `warning_count` counts every evaluation configured as `WARNING`, regardless of PASS or FAIL.
- `pass_count` counts only `PASS` whose configured severity is `PASS`; it is not the number of all PASS outcomes.
- `service_error_count`, `unknown_count`, and `not_applicable_count` are separate derived counts.

`RuleEvaluation.effective_severity` maps `SERVICE_ERROR` to effective `BLOCKER`, but `QualityReport.blocker_count` still counts only configured `BLOCKER` failures. Therefore service errors are fail-closed through overall `QualityStatus`, not through the normal failed-blocker counter.

### 2.3 RuleEngine production paths

`RuleEngine.evaluate()` in `intelligence/ml-service/app/rules/rule_engine.py:191-289` behaves as follows:

- Scope mismatch → `NOT_APPLICABLE`.
- POST_RENDER rule invoked during PRE_RENDER → `NOT_APPLICABLE`.
- Registered evaluator → evaluator outcome.
- Missing evaluator registration → `SERVICE_ERROR` with configured severity escalated to `BLOCKER`.
- Aggregation then calculates family scores, family assessments, overall score, and overall status.

A missing evaluator is therefore **not** represented as `NOT_EVALUATED`; it is a fail-closed `SERVICE_ERROR`.

Semantic provider failures are also mapped to `SERVICE_ERROR` in evaluator-specific exception handlers, including `ATTEMPT_002`, `PAYOFF_003`, and `CONCEPT_007` paths.

## 3. Where `NOT_EVALUATED` exists today

### 3.1 Not explicit in Python pre-render RuleOutcome

There is no Python `RuleOutcome.NOT_EVALUATED`. The following situations are therefore represented indirectly:

| Situation | Current Python/G​​olden representation |
|---|---|
| Rule never entered the evaluation list | Missing evaluation row; no explicit state. |
| Evaluator not registered | `SERVICE_ERROR`, not `NOT_EVALUATED`. |
| Dimension not projected | Missing/null assessment or canonical field. |
| Parser timeout | Golden `status=PARSER_TIMEOUT`, `report=null`, `assessment=null`, `apiReport=null`. |
| Provider-dependent check not executed | Usually `UNKNOWN` if evaluator ran and reports missing evidence; `SERVICE_ERROR` if provider call failed. |
| Historical snapshot lacks a newer dimension | Missing `dimensionValues` key, sometimes stored zero/empty fallback. |
| Post-render semantic field not executed | Explicit Java `EvidenceStatus.NOT_EVALUATED`; not normalized to Python quality aggregation. |

### 3.2 Explicit in post-render evidence

Post-render Java evidence has an explicit `EvidenceStatus` including:

```text
AVAILABLE
NOT_EVALUATED
UNKNOWN
SERVICE_ERROR
NOT_APPLICABLE
```

Examples include visual motion, semantic loop continuity, character continuity, action novelty, and plan-render fidelity. `NOT_EVALUATED` is used when semantic vision, a structured plan, or a required post-render analysis is not configured or not run.

This is a separate vocabulary from Python `RuleOutcome`. The repository currently has a cross-layer taxonomy split rather than one lossless aggregation contract.

## 4. Parser timeout and missing evaluation behavior

`PromptParser` fallback behavior can return an empty beat list while recording missing evidence/warnings. The deterministic Golden runner additionally bounds parsing with a timeout:

```text
timeout → GoldenRun.status = PARSER_TIMEOUT
          known issue = PARSER_DISCOVERY_TIMEOUT
          report = null
          assessment = null
          apiReport = null
          videoPlanIR = null
```

For `upside-chair-01`, this is the actual frozen behavior. There are no RuleEvaluation rows to count as PASS, FAIL, UNKNOWN, NOT_APPLICABLE, or SERVICE_ERROR.

That is an implicit `NOT_EVALUATED`/unavailable state, but it is not named as such. The historical snapshot also contains `dimensionValues` entries such as zero/empty strategy fields, which can be mistaken for evaluated zero rather than absent evaluation. This is a Family 7 violation of the “missing evidence is not negative evidence” principle.

The normal API path has another distinction: a total ML-service failure is raised through the backend client as an exception rather than being serialized as a `QualityReport` with a `SERVICE_ERROR` row. Rule-level provider failure and service-unavailable failure therefore do not share one aggregation representation.

## 5. Current scoring formulas

### 5.1 Family score numerator and denominator

`RuleEngine._calculate_family_scores()` at `rule_engine.py:340-376` groups evaluations by family and selects:

```python
scored = [
    rule for rule in rules
    if rule.outcome in {RuleOutcome.PASS, RuleOutcome.FAIL}
    and not is_evidence_gap(rule)
]
```

Therefore:

- `PASS` and valid `FAIL` are eligible.
- `UNKNOWN` is excluded.
- `NOT_APPLICABLE` is excluded.
- `SERVICE_ERROR` is excluded from the score and forces that family score to `None`.
- Evidence-incomplete FAIL values are excluded through `is_evidence_gap()`.

Per eligible rule score:

```text
PASS with configured severity PASS     = 100
PASS with another configured severity  = 85
FAIL with BLOCKER severity             = 0
FAIL with CRITICAL severity            = 40
other FAIL                             = 70
```

Family denominator is `len(scored)`, i.e. only valid PASS/FAIL evaluations. This is a scored-subset denominator, not all declared rules.

### 5.2 Family assessment coverage

`_calculate_family_assessments()` at `rule_engine.py:378-410` calculates:

```text
evaluated_count = PASS + FAIL rows that are not evidence gaps
evidenceCoverage = evaluated_count / len(all family rows) * 100
```

Unlike family score denominator, this denominator includes all rows in the family, including UNKNOWN and NOT_APPLICABLE. This is why score and coverage are different concepts.

Family assessment states:

```text
SERVICE_ERROR if any service error
PARTIAL if evidence gaps exist alongside an evaluated PASS/FAIL
UNKNOWN if evidence gaps exist and no evaluated PASS/FAIL exists
NOT_APPLICABLE if no PASS/FAIL/UNKNOWN and at least one NA
PARTIAL if evaluated rows coexist with UNKNOWN or NA
EVALUATED otherwise
```

### 5.3 Overall score

`_calculate_overall_score()` at `rule_engine.py:411-423` sums only family scores that are not `None`:

```text
weighted_sum = sum(family_score * family_weight)
total_weight = sum(weights for non-null family scores)
overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
```

Consequences:

- Families with null scores are removed from the overall denominator.
- Remaining family weights are effectively renormalized.
- A family with no evaluated rule does not directly contribute zero.
- If no family is scoreable, overall score becomes numeric `0.0`.
- There is no explicit global scored-rule denominator in the `QualityReport`.

The last behavior violates the Family 7 invariant that zero evaluated items must not produce a misleading creative zero.

### 5.4 Severity and overall status

Overall status is fail-closed for service errors:

```text
SERVICE_ERROR if any service error
RENDER_READY if overall >= 92 and blocker_count == 0 and critical_count == 0
BLOCKED if overall < 80 or blocker_count > 0
NEEDS_REVISION otherwise
```

Because service errors are checked before score thresholds, a service error cannot produce `RENDER_READY`. However, the service error is not counted as a normal failed rule or blocker in `blocker_count`.

## 6. Pre-render assessment aggregation

`build_pre_render_assessment()` in `pre_render_assessment.py:28-143` calculates:

```python
applicable = evaluations where outcome != NOT_APPLICABLE
evaluated = applicable where not is_evidence_gap(evaluation)
coverage = evaluated / max(len(applicable), 1) * 100
```

Thus:

- `NOT_APPLICABLE` is excluded from the coverage denominator.
- `UNKNOWN` is included in the denominator and lowers coverage.
- `SERVICE_ERROR` is included in the denominator and lowers coverage.
- There is no `NOT_EVALUATED` branch.
- Missing evaluation rows are invisible to this calculation unless another layer provides a declared denominator.

`evidence_completeness` becomes `INCOMPLETE` when `report.service_error_count > 0` or coverage is below 80; otherwise it is `PARTIAL` when evidence gaps exist and `COMPLETE` when no gaps exist.

`_creative_grade()` excludes evidence gaps and NOT_APPLICABLE from creative judgments. It returns `INCOMPLETE` when no creative judgments remain, so UNKNOWN/SERVICE_ERROR are not directly converted into creative FAIL.

`_grade()` returns `INCOMPLETE` for service errors or coverage below 80 before evaluating blocker/critical/failed rules.

`readiness` maps the grade:

```text
A/B → READY_TO_RENDER
C/D → EDIT_PLAN
F   → BLOCKED
INCOMPLETE → INCOMPLETE
```

Render authorization is separate. It produces:

```text
BLOCKED_TECHNICAL_FAILURE when service errors exist
BLOCKED_CREATIVE_FAILURE when evaluated creative FAIL exists
BLOCKED_PENDING_EVIDENCE when final policy/visual evidence is incomplete
AUTHORIZED otherwise
```

The current runtime therefore distinguishes creative score/grade, evidence completeness, readiness, and render authorization, but does not expose a single explicit Family 7 aggregation state that combines all missing/unevaluated categories.

## 7. Nine Golden asset audit

Source artifacts:

- baseline: `intelligence/data/golden/pompom-golden-v1/baselines/v1.7/baseline.json`
- available current artifact: `intelligence/data/golden/pompom-golden-v1/reports/family5-current/current.json`
- effective RULESET 1.7 rows: 8 per parsed asset
- no corpus role or performance data used

The counts below are RuleEvaluation outcome counts, not `QualityReport.pass_count`.

| Asset | Baseline/current rows | PASS | FAIL | UNKNOWN | NOT_APPLICABLE | SERVICE_ERROR | implicit NOT_EVALUATED | scored denominator | coverage | overall score | grade/readiness/render |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Sticky Ball | 8 / 8 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 80% | 85.0 | A / READY_TO_RENDER / BLOCKED_PENDING_EVIDENCE |
| Ball-Multiplying Crocodile | 8 / 8 | 3 | 1 | 1 | 3 | 0 | 0 | 4 | 80% | 61.8182 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |
| Upside-Down Chair | 0 / 0 | 0 | 0 | 0 | 0 | 0 | 8 | N/A | N/A | null | null / null / null |
| Lamp | 8 / 8 | 2 | 2 | 1 | 3 | 0 | 0 | 4 | 80% | 49.5455 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |
| Snack Box | 8 / 8 | 2 | 2 | 1 | 3 | 0 | 0 | 4 | 80% | 49.5455 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |
| Box Cat | 8 / 8 | 1 | 3 | 1 | 3 | 0 | 0 | 4 | 80% | 38.2955 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |
| Spot Cat | 8 / 8 | 1 | 3 | 1 | 3 | 0 | 0 | 4 | 80% | 38.2955 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |
| Sneaky Door | 8 / 8 | 1 | 3 | 1 | 3 | 0 | 0 | 4 | 80% | 38.2955 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |
| Island Journal | 8 / 8 | 0 | 4 | 1 | 3 | 0 | 0 | 4 | 80% | 20.9091 | F / BLOCKED / BLOCKED_CREATIVE_FAILURE |

Notes:

- `upside-chair-01` has `PARSER_TIMEOUT`; no evaluation rows are present. It is an implicit unevaluated/unavailable case, not eight creative failures.
- Parsed assets have one UNKNOWN and three NOT_APPLICABLE rows. With five applicable rows, four evaluated PASS/FAIL rows yield the displayed 80% assessment coverage.
- Family score denominator is four valid PASS/FAIL rows for the listed assets; it is not the five applicable-rule denominator.
- `SERVICE_ERROR` is zero in these frozen Golden snapshots; provider/runtime failures are covered by synthetic and RuleEngine paths rather than these asset outputs.
- Current Family 5 report can change Box Cat/Spot Cat policy fields versus baseline because of the documented parser provenance drift; that is not a Family 7 fix.

## 8. Special cases

### A. Upside-Down Chair parser timeout

Current behavior:

```text
Golden status       = PARSER_TIMEOUT
RuleEvaluation rows = none
report              = null
assessment          = null
apiReport           = null
videoPlanIR         = null
score               = null
coverage            = null
```

This is not represented as UNKNOWN, NOT_APPLICABLE, or SERVICE_ERROR in the Golden snapshot. It is an implicit `NOT_EVALUATED`/unavailable state. The historical `dimensionValues` block contains zero/empty fields, which risks presenting absence as measured zero.

### B. Family 5 specialized applicability

Family 5’s canonical applicability map is separate from RuleEngine outcomes. `UNKNOWN` applicability must remain a status/evidence gap, not a FAIL or numeric zero. `NOT_APPLICABLE` applicability is not a creative failure and should remain outside score denominators.

### C. Family 6 `BASELINE_NOT_CAPTURED`

The Family 6 comparator capability now returns `BASELINE_NOT_CAPTURED` when the raw historical baseline lacks the new dimension. This is explicitly non-gating and does not increment `newSemanticRegressions`. It must remain a reporting state, not a creative outcome.

### D. Historical snapshots

Older snapshots may lack newer dimensions entirely. A missing dimension key is not an expected negative value and must not be compared as FAIL, zero, or `NOT_APPLICABLE` without an explicit migration contract.

## 9. Synthetic boundary-case proposal

These are review hypotheses, not implementation decisions.

Assume each case is a single declared applicable family with a stable configured severity. Numeric score uses the existing severity-dependent score mapping only when a scored denominator exists.

| Case | Inputs | Should score? | Recommended denominator | Recommended numeric result | Coverage | Aggregation state |
|---|---|---:|---:|---:|---:|---|
| 1 | PASS, PASS, FAIL | Yes | 3 (`PASS+FAIL`) | Existing evaluated-subset score | 100% | EVALUATED |
| 2 | PASS, PASS, UNKNOWN | Yes | 2 scored; 3 applicable | Existing score over 2; no zero penalty | 66.7% | PARTIAL |
| 3 | PASS, PASS, NOT_EVALUATED | Yes | 2 scored; 3 declared applicable | Existing score over 2; no zero penalty | 66.7% | INCOMPLETE/PARTIAL with explicit unevaluated count |
| 4 | PASS, PASS, NOT_APPLICABLE | Yes | 2 scored; 2 applicable | Existing score over 2 | 100% applicable coverage | EVALUATED |
| 5 | PASS, PASS, SERVICE_ERROR | No stable creative score for affected aggregation | 2 attempted scored, 1 technical error | `null` for affected family; never zero | 66.7% or explicit technical coverage | SERVICE_ERROR |
| 6 | UNKNOWN only | No | 0 | `null`, never 0 | 0% | UNKNOWN/INCOMPLETE |
| 7 | NOT_EVALUATED only | No | 0 | `null`, never 0 | 0% with unevaluated count | NOT_EVALUATED/INCOMPLETE |
| 8 | NOT_APPLICABLE only | No | 0 applicable | `null`, never 0 | N/A, not a coverage failure | NOT_APPLICABLE |
| 9 | SERVICE_ERROR only | No | 0 scored | `null`, never 0 | 0% evaluated plus technical error | SERVICE_ERROR |
| 10 | PASS + FAIL + UNKNOWN + NOT_EVALUATED + NOT_APPLICABLE + SERVICE_ERROR | No stable family score while service error exists | 2 scored; 5 declared/attempted categories, NA excluded from applicable denominator | `null` for affected family | Explicit scored/applicable/unknown/unevaluated/service counts | SERVICE_ERROR with separate evidence coverage |

Recommended denominator invariant:

```text
scoredRuleDenominator = PASS + FAIL
coverageDenominator   = PASS + FAIL + UNKNOWN + NOT_EVALUATED + SERVICE_ERROR
NOT_APPLICABLE         = excluded from coverage denominator
```

This is a proposal. The current runtime uses a related but not identical denominator model and does not have a first-class NOT_EVALUATED row.

## 10. Current gaps and violations

1. Python `RuleOutcome` lacks `NOT_EVALUATED`.
2. Missing evaluation rows have no declared denominator or state.
3. Parser timeout has a Golden status but no normalized aggregation status.
4. Missing/timeout snapshot `dimensionValues` can contain zero/empty values that resemble measured results.
5. RuleEngine overall score returns `0.0` when no family is scoreable.
6. Family weights are renormalized over non-null family scores without exposing the denominator.
7. Family score denominator (`PASS+FAIL`) differs from family evidence coverage denominator (all family rows).
8. `SERVICE_ERROR` produces overall `QualityStatus.SERVICE_ERROR`, but is not included in configured blocker/critical counters.
9. API response has five rule buckets but no explicit `NOT_EVALUATED`, scored denominator, coverage denominator, or count fields.
10. Java DTO null-to-empty normalization loses absent-vs-empty distinction.
11. PDF filters null family scores and does not render an explicit no-evaluation state.
12. Frontend types only the five Python outcomes and collapses some unscored states in presentation.
13. Committed v1.7 Golden report does not contain Family 6 assertions or the newer Family 5 per-rule assertion form.
14. Post-render Java `EvidenceStatus.NOT_EVALUATED` is not normalized into pre-render `QualityReport` aggregation.
15. Current Golden report migration does not surface `BASELINE_NOT_CAPTURED` counts in the committed summary.

## 11. Recommended canonical Family 7 model

Do not immediately add one creative status per Golden asset. Family 7 is an aggregation contract.

Recommended normalized internal representation:

```text
EvaluationRecord:
  ruleId
  applicability: APPLICABLE | NOT_APPLICABLE
  evaluationState: EVALUATED | UNKNOWN | NOT_EVALUATED | SERVICE_ERROR
  outcome: PASS | FAIL | null
  severity
  evidenceReferences
  reason
```

Recommended aggregation result:

```text
AggregationSummary:
  declaredCount
  evaluatedCount
  scoredCount
  unknownCount
  notEvaluatedCount
  notApplicableCount
  serviceErrorCount
  coverageDenominator
  coveragePercent: null when denominator is zero
  score: null when scoredCount is zero or technical policy invalidates the family
  aggregationState: EVALUATED | PARTIAL | UNKNOWN | NOT_EVALUATED | NOT_APPLICABLE | SERVICE_ERROR
```

The status/outcome split avoids forcing `NOT_EVALUATED` into `RuleOutcome` immediately. It also preserves the distinction between “this rule applies but evidence is indeterminate” (`UNKNOWN`) and “no semantic judgment exists because it never ran” (`NOT_EVALUATED`).

Global invariants:

```text
PASS/FAIL are the only scored outcomes.
UNKNOWN is not FAIL and is never numeric zero.
NOT_EVALUATED is not UNKNOWN and is never numeric zero.
NOT_APPLICABLE is excluded from applicable/scored denominators and never lowers creative score.
SERVICE_ERROR is technical, not creative FAIL; it is fail-closed for readiness but separate in counts.
Zero scored items produce score=null, not score=0.
Missing historical dimensions produce BASELINE_NOT_CAPTURED, not FAIL.
Every denominator is explicitly serialized and reproducible.
```

## 12. Proposed Gold Truth structure

Recommended smallest model: **Option C — global aggregation invariants plus representative boundary fixtures**, with per-asset audit facts only for frozen snapshots.

Reasoning:

- Family 7 does not judge whether Sticky Ball or Island Journal is creative quality.
- A nine-asset creative label matrix would encode downstream policy rather than aggregation semantics.
- The important truth is how statuses combine, what counts as scored, and what happens when no row exists.
- Representative synthetic cases exercise every boundary more directly than arbitrary asset labels.

Suggested future contract shape, not to be implemented in this audit:

```yaml
family7AggregationTruthVersion: FAMILY7_AGGREGATION_V1
statuses:
  evaluated: [PASS, FAIL]
  indeterminate: [UNKNOWN]
  notEvaluated: [NOT_EVALUATED]
  notApplicable: [NOT_APPLICABLE]
  technical: [SERVICE_ERROR]
invariants:
  unknownIsNotFail: true
  notEvaluatedIsNotUnknown: true
  notApplicableExcludedFromScore: true
  serviceErrorIsNotCreativeFail: true
  missingNeverBecomesZero: true
  zeroScoredIsNull: true
representativeCases:
  - id: PASS_FAIL_UNKNOWN
  - id: PASS_FAIL_NOT_EVALUATED
  - id: PASS_FAIL_NOT_APPLICABLE
  - id: PASS_FAIL_SERVICE_ERROR
  - id: ZERO_EVALUATED
  - id: HISTORICAL_DIMENSION_MISSING
```

No Family 7 Gold Truth file was created during this read-only audit.

## 13. Implementation options

### Option A — Two-field normalized aggregation contract (recommended)

Keep `RuleOutcome` unchanged for the first migration and add an additive `evaluationState`/aggregation summary contract. Map existing Python rows into it, map post-render `EvidenceStatus` into it, and serialize explicit counts/denominators. This avoids breaking existing ruleset/evaluator code while making NOT_EVALUATED explicit at aggregation boundaries.

### Option B — Add `NOT_EVALUATED` to Python `RuleOutcome`

More uniform at the enum level, but high blast radius: RuleEngine, score aggregation, API response, Java DTO, PDF, frontend unions, tests, policy reports, and historical snapshots all need migration. This should not be selected without a cross-layer versioned contract.

### Option C — Keep missing rows implicit

Lowest code change, but it violates reproducibility and makes parser timeout, unavailable provider, historical missing dimensions, and zero evaluated indistinguishable. Not recommended.

## 14. Risks to Family 1–6

- Changing `_calculate_family_scores` could change all existing Family 1–6 scores and invalidate frozen calibration outputs.
- Introducing NOT_EVALUATED into `RuleOutcome` could alter RuleEngine counts and Family 5/6 comparator assertions.
- Recomputing historical snapshots with new denominator rules could appear as Family 5 generic baseline drift.
- Treating `SERVICE_ERROR` as creative FAIL would violate existing fail-closed technical behavior.
- Converting null family scores to zero would make parser timeout and unscored families look semantically negative.
- Adding API/PDF/UI fields without a shared contract could produce lossless ML but lossy Java/Angular representations.
- Changing render authorization in Family 7 would prematurely enter Family 8 scope.
- Any parser/canonical changes to fill missing evidence would reopen frozen Family 1–6 semantics.

## 15. Human decisions required

1. Should Family 7 use the recommended two-field `outcome + evaluationState` contract, or introduce `NOT_EVALUATED` into Python `RuleOutcome`?
2. Should zero scored rules/families return `score=null` and `INCOMPLETE`, replacing current overall numeric `0.0` behavior?
3. Should `SERVICE_ERROR` invalidate the affected family score only, or the entire overall score, while preserving separate technical status?
4. Should `NOT_APPLICABLE` be excluded from coverage as it is now, with explicit `applicableCount` and `coverageDenominator` fields added?
5. Should `UNKNOWN` and `NOT_EVALUATED` both lower coverage but remain outside score, or should NOT_EVALUATED be excluded from coverage when the rule was never declared applicable?
6. Should parser timeout become explicit `NOT_EVALUATED` in Golden snapshots instead of a null report with legacy zero/empty dimension values?
7. Should API/backend/PDF/frontend expose explicit outcome counts and denominators, rather than requiring consumers to count lists?
8. Should `BASELINE_NOT_CAPTURED` become a general comparator classification for every historical missing dimension, not only Family 6?
9. Should current committed Golden artifacts be regenerated under an explicit versioned migration after the aggregation contract is approved?
10. Should `READY_TO_RENDER` and `BLOCKED_PENDING_EVIDENCE` remain separate simultaneous outputs, as in Sticky Ball, or be normalized in Family 8?

## 16. Stop condition

Family 7 remains **AUDIT COMPLETE / IMPLEMENTATION NOT STARTED**. No parser, RuleEngine, scorer, ruleset, policy, Gold Truth, baseline, Family 1–6, Meta, publisher, API, backend, PDF, or frontend behavior was changed by this audit.

Family 8+ remain NOT STARTED until the human decisions above are explicitly approved.


## 17. Approved Family 7 decision lock

Human review approved the following decisions after this audit.

### 17.1 `NOT_EVALUATED` is separate from `RuleOutcome`

Do not add `NOT_EVALUATED` to the existing Python `RuleOutcome` enum. Preserve compatibility for:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
SERVICE_ERROR
```

Introduce an additive evaluation-state field at aggregation boundaries:

```text
evaluationState = EVALUATED | NOT_EVALUATED
```

Rules:

- `evaluationState=NOT_EVALUATED` requires `outcome=null`.
- `evaluationState=NOT_EVALUATED` never synthesizes numeric zero.
- PASS, FAIL, UNKNOWN, NOT_APPLICABLE, and SERVICE_ERROR remain existing `RuleOutcome` values with `evaluationState=EVALUATED` when a row exists.
- Rule evaluator logic is not redesigned by Family 7.

### 17.2 Zero evaluated/scored behavior

When a family or overall aggregation has zero scored/evaluated items:

```text
score = null
aggregationState = INCOMPLETE / NO_EVALUATED_ITEMS
```

The system must never emit numeric `0` as a creative score merely because no evidence was evaluated. Render authorization, readiness policy, and creative-grade policy remain unchanged and are deferred to Family 8.

### 17.3 Scored denominator and service errors

Numeric scoring denominator is exactly:

```text
scoredDenominator = PASS + FAIL
```

The following are excluded from the numeric score denominator:

```text
UNKNOWN
NOT_EVALUATED
NOT_APPLICABLE
SERVICE_ERROR
```

When a family contains some PASS/FAIL rows and also SERVICE_ERROR:

- calculate the numeric score from PASS/FAIL rows;
- expose `serviceErrorCount` and `aggregationState` explicitly;
- do not automatically invalidate every overall score solely because one family has a service error.

When a family contains zero PASS/FAIL rows, its score is null. The same rule applies to overall score: at least one scored item permits a partial numeric score with explicit coverage; zero scored items yields null.

### 17.4 Required cross-layer aggregation representation

The additive Family 7 aggregation representation must preserve at least:

```text
score
scoredCount
denominator
passCount
failCount
unknownCount
notEvaluatedCount
notApplicableCount
serviceErrorCount
evaluationCoverage
aggregationState
```

Score and coverage are separate fields. Family 7 does not redesign creative grade, readiness, or render authorization.

### 17.5 Reusable `BASELINE_NOT_CAPTURED`

`BASELINE_NOT_CAPTURED` becomes a reusable structural comparator classification only when all of the following are true:

- the dimension exists in current output and/or approved Gold Truth;
- the historical baseline predates that dimension;
- the absence is provenance-verified.

It is non-gating and does not increment semantic regressions. It must not be used for parser failures, null values where the dimension should have existed, corrupted artifacts, or unexpected missing baseline data. Those remain explicit data/review gaps.

### 17.6 Sticky Ball policy boundary

The coexistence of `READY_TO_RENDER` and `BLOCKED_PENDING_EVIDENCE` remains unchanged. Family 7 exposes the aggregation facts required to resolve that relationship, but does not change creative-grade, readiness, or render-authorization policy. That decision belongs to Family 8.

## 18. Smallest approved Family 7 canonical contract

Family 7 is an aggregation-contract family, not a creative-label family. The smallest proposed canonical shape is:

```python
class EvaluationState(StrEnum):
    EVALUATED = "EVALUATED"
    NOT_EVALUATED = "NOT_EVALUATED"

@dataclass(frozen=True)
class AggregationSummary:
    score: float | None
    scored_count: int
    denominator: int
    pass_count: int
    fail_count: int
    unknown_count: int
    not_evaluated_count: int
    not_applicable_count: int
    service_error_count: int
    evaluation_coverage: float | None
    aggregation_state: str
```

The contract must preserve `RuleOutcome` unchanged. A row with `evaluationState=NOT_EVALUATED` has `outcome=None`; all other row outcomes remain the existing five-value enum. The recommended state vocabulary is:

```text
EVALUATED
PARTIAL
UNKNOWN
NOT_EVALUATED
NOT_APPLICABLE
SERVICE_ERROR
INCOMPLETE / NO_EVALUATED_ITEMS
```

Recommended formulas:

```text
passCount            = count(outcome == PASS)
failCount            = count(outcome == FAIL)
scoredCount          = passCount + failCount
denominator          = scoredCount
evaluationCoverage   = scoredCount / (scoredCount + unknownCount + notEvaluatedCount + serviceErrorCount)
                       or null when that coverage denominator is zero
score                = configured PASS/FAIL score over scoredCount
                       or null when scoredCount == 0
```

`NOT_APPLICABLE` is excluded from the coverage denominator. A SERVICE_ERROR does not erase an available PASS/FAIL numeric score, but it remains explicit in counts and aggregation state. A family with no scored rows has `score=null` and `aggregationState=INCOMPLETE/NO_EVALUATED_ITEMS`.

The approved Gold Truth shape is global invariants plus representative boundary fixtures, not arbitrary per-asset creative labels. No Family 7 Gold Truth file or runtime contract was changed during this decision lock.


## 19. Final approved clarifications before implementation

### 19.1 Zero scored versus zero evaluated

`scoredCount` is exactly:

```text
PASS + FAIL
```

These states are distinct:

```text
scoredCount == 0 with semantic evaluation rows
  → score = null
  → aggregationState = NO_SCORED_ITEMS

no relevant evaluation actually ran
  → score = null
  → aggregationState = NO_EVALUATED_ITEMS
```

Therefore an UNKNOWN-only case is `NO_SCORED_ITEMS`, never `NO_EVALUATED_ITEMS`. A NOT_EVALUATED-only case is `NO_EVALUATED_ITEMS`.

### 19.2 Authoritative evaluation coverage

The approved coverage denominator is:

```text
applicableCount = PASS + FAIL + UNKNOWN + NOT_EVALUATED + SERVICE_ERROR
```

`NOT_APPLICABLE` is excluded. The semantic evaluation numerator is:

```text
semanticEvaluationCount = PASS + FAIL + UNKNOWN
```

The authoritative coverage formula is:

```text
evaluationCoverage = semanticEvaluationCount / applicableCount
```

when `applicableCount > 0`; otherwise coverage is `null`/`NOT_APPLICABLE`, never synthetic zero or 100. Numeric creative score remains independent and uses only PASS + FAIL.

### 19.3 Runtime missing evaluation versus historical baseline absence

When a parser timeout prevents downstream evaluation:

```text
evaluationState = NOT_EVALUATED
outcome = null
reason/provenance = preserved explicitly
```

Parser timeout must not become FAIL, UNKNOWN, or numeric zero.

`BASELINE_NOT_CAPTURED` is a Golden/comparator provenance classification only. It applies when historical baseline schema predates a dimension that exists in current/Gold. It is not a runtime evaluation state and must not be used for parser failures, null values that should exist, or corrupted artifacts.
