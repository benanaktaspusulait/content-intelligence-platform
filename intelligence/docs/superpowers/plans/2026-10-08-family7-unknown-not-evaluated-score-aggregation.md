# Family 7 — UNKNOWN / NOT_EVALUATED / Score Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lossless Family 7 aggregation contract that distinguishes evaluated outcomes, unevaluated work, non-applicability, evidence gaps, and technical errors without changing creative semantics or render policy.

**Architecture:** Preserve the existing five-value `RuleOutcome` enum and add a separate `EvaluationState` plus an additive `AggregationSummary`. Scoring consumes only PASS/FAIL rows; UNKNOWN, NOT_EVALUATED, NOT_APPLICABLE, and SERVICE_ERROR remain explicit excluded/error categories. The summary is propagated through ML, Golden snapshots/comparator, API, backend DTO/PDF, and frontend representations without changing evaluator semantics, creative grade, readiness, or render authorization.

**Tech Stack:** Python 3.14/pytest/PyYAML, existing ML contracts and RuleEngine aggregation boundaries, FastAPI/Pydantic, Java 21 Spring DTO/PDF, Angular/TypeScript, deterministic Golden comparator.

## Approved decisions and constraints

- Family 1–6 remain frozen and are not reopened.
- `RuleOutcome` remains exactly `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`, `SERVICE_ERROR`.
- `EvaluationState` is additive: `EVALUATED` or `NOT_EVALUATED`.
- `evaluationState=NOT_EVALUATED` requires `outcome=null`; no numeric zero may be synthesized.
- Numeric score denominator is PASS + FAIL only.
- UNKNOWN, NOT_EVALUATED, NOT_APPLICABLE, and SERVICE_ERROR are excluded from numeric score denominator.
- A family with PASS/FAIL plus SERVICE_ERROR retains the PASS/FAIL numeric score and exposes the technical error separately.
- A family or overall aggregation with zero scored rows returns `score=null` and `aggregationState=INCOMPLETE/NO_EVALUATED_ITEMS`.
- Score and evaluation coverage are separate representations.
- `NOT_APPLICABLE` never lowers creative score and is excluded from coverage denominator.
- `BASELINE_NOT_CAPTURED` is reusable only for provenance-verified historical absence of a dimension that exists in current/Gold; it is non-gating.
- Parser semantics, canonical Family 1–6 evidence, RuleEngine evaluator semantics, rulesets, creative grade, readiness, render authorization, Meta/public-comment, publisher code, and RULESET 1.8 remain unchanged.
- No implementation starts until this plan is reviewed and approved.

## Canonical design

### Evaluation row

```python
class EvaluationState(StrEnum):
    EVALUATED = "EVALUATED"
    NOT_EVALUATED = "NOT_EVALUATED"

@dataclass(frozen=True)
class AggregationRow:
    rule_id: str
    outcome: RuleOutcome | None
    evaluation_state: EvaluationState
    configured_severity: Severity | None
    family: str
    reason: str
```

Rules:

- PASS/FAIL/UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR rows use `evaluation_state=EVALUATED`.
- Missing evaluator execution, parser timeout, unavailable projection, or omitted historical row uses `evaluation_state=NOT_EVALUATED` and `outcome=None`.
- `NOT_EVALUATED` is not added to `RuleOutcome` and is not passed through existing evaluator return types until the aggregation boundary is explicitly adapted.

### Aggregation summary

```python
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

Formula contract:

```text
passCount          = count(PASS)
failCount          = count(FAIL)
scoredCount        = passCount + failCount
denominator        = scoredCount
evaluationCoverage = scoredCount /
                     (scoredCount + UNKNOWN + NOT_EVALUATED + SERVICE_ERROR)
                     or null when the coverage denominator is zero
score              = existing configured PASS/FAIL score over scoredCount
                     or null when scoredCount == 0
```

`NOT_APPLICABLE` is excluded from `evaluationCoverage` denominator. A service error remains explicit and may set `aggregationState=SERVICE_ERROR`, but it does not erase an otherwise available PASS/FAIL score. Zero scored rows always produce null score.

### Data flow

```text
RuleEvaluation / missing evaluation source
        ↓
EvaluationState + RuleOutcome|null
        ↓
AggregationSummary
        ↓
ML report + Golden snapshot/comparator
        ↓
API response → backend DTO/PDF → frontend
```

Creative grade, readiness, and render authorization continue to consume their existing policy inputs. Family 7 exposes facts; Family 8 decides policy interactions.

## Task-by-task TDD plan

### Task 1: Red tests for the aggregation contract

**Files:**
- Create: `intelligence/ml-service/tests/test_family7_aggregation_contract.py`
- Do not change production code.

- [ ] Define concrete synthetic rows for:
  - PASS + PASS + FAIL
  - PASS + PASS + UNKNOWN
  - PASS + PASS + NOT_EVALUATED
  - PASS + PASS + NOT_APPLICABLE
  - PASS + PASS + SERVICE_ERROR
  - UNKNOWN only
  - NOT_EVALUATED only
  - NOT_APPLICABLE only
  - SERVICE_ERROR only
  - mixed PASS + FAIL + UNKNOWN + NOT_EVALUATED + NOT_APPLICABLE + SERVICE_ERROR
- [ ] Assert exact expected scored count, denominator, null/numeric score, coverage, and aggregation state from the approved decision lock.
- [ ] Assert `NOT_EVALUATED` rows have `outcome is None`.
- [ ] Assert `UNKNOWN`, `NOT_APPLICABLE`, and `SERVICE_ERROR` never become FAIL or numeric zero.
- [ ] Assert zero scored rows yield `score is None`, not `0.0`.
- [ ] Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_family7_aggregation_contract.py --no-header -p no:cacheprovider
```

Expected initial result: RED because `EvaluationState`, `AggregationRow`, and `AggregationSummary` do not yet exist.

### Task 2: Add the additive ML aggregation contract

**Files:**
- Modify: `intelligence/ml-service/app/quality/contracts.py`
- Create or modify only the named Family 7 aggregation helper module if the existing contract file becomes too coupled: `intelligence/ml-service/app/quality/aggregation.py`
- Test: `tests/test_family7_aggregation_contract.py`

- [ ] Add `EvaluationState` without changing `RuleOutcome`.
- [ ] Add immutable aggregation row/summary types with stable serialization keys:

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

- [ ] Implement PASS/FAIL-only score denominator and null score for zero scored rows.
- [ ] Implement `NOT_APPLICABLE` exclusion from coverage denominator.
- [ ] Preserve numeric score when PASS/FAIL rows exist alongside SERVICE_ERROR; expose service error count/state separately.
- [ ] Run the focused red tests and confirm GREEN.
- [ ] Run existing `contracts`, RuleEngine, scorer, Family 1–6 focused tests to prove existing RuleOutcome behavior remains compatible.

### Task 3: Integrate aggregation facts at the ML report boundary

**Files:**
- Modify only aggregation/report construction paths identified after Task 2:
  - `intelligence/ml-service/app/rules/rule_engine.py` aggregation methods, not evaluator methods;
  - `intelligence/ml-service/app/assessment/pre_render_assessment.py` coverage/evidence summary only;
  - `intelligence/ml-service/app/api/quality.py` response fields.
- Tests:
  - `tests/test_family7_aggregation_contract.py`
  - additive API/assessment tests

- [ ] Write red tests proving family score uses PASS/FAIL denominator while retaining UNKNOWN/NA/SERVICE_ERROR counts.
- [ ] Write red tests proving overall score is null when zero families have scored rows.
- [ ] Write red tests proving a family with PASS/FAIL + SERVICE_ERROR retains a numeric score but exposes `serviceErrorCount` and technical aggregation state.
- [ ] Preserve existing `RuleEngine` evaluator and status behavior; change only aggregation representation.
- [ ] Keep creative-grade/readiness/render-authorization outputs unchanged in this Family 7 slice; test the existing values remain unchanged for current Golden fixtures.
- [ ] Serialize `AggregationSummary` separately from `creative_score`, `creative_grade`, `readiness`, and `render_authorization`.

### Task 4: Normalize missing evaluation and historical snapshot behavior

**Files:**
- Modify: `intelligence/ml-service/app/golden/deterministic_runner.py`
- Modify: `intelligence/ml-service/app/golden/baseline.py` only for explicit snapshot state, not baseline artifact regeneration.
- Modify: `intelligence/ml-service/app/golden/comparator.py`
- Tests: `tests/test_family7_aggregation_contract.py`, `tests/test_golden_comparator.py`

- [ ] Add explicit snapshot aggregation state for parser timeout/no-report and missing evaluation rows without manufacturing zero values.
- [ ] Generalize provenance-verified `BASELINE_NOT_CAPTURED` only when raw baseline dimension absence is proven and current/Gold contains the dimension.
- [ ] Keep parser failure, null value where a dimension should exist, and corrupted artifact as explicit data/review gaps rather than `BASELINE_NOT_CAPTURED`.
- [ ] Add tests for:
  - parser timeout/no report;
  - historical dimension absent by provenance;
  - dimension present with null value;
  - malformed snapshot;
  - current canonical output with stale stored value;
  - missing row with `evaluationState=NOT_EVALUATED`.
- [ ] Do not rewrite `baselines/v1.7/baseline.json` in this task.

### Task 5: Lossless API/backend/PDF/frontend representation

**Files:**
- Modify: `intelligence/ml-service/app/api/quality.py`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportPdfService.java`
- Modify: `intelligence/frontend/src/app/pages/quality-validator/quality-validator.component.ts`
- Modify: corresponding templates/tests only for explicit aggregation fields.

- [ ] Add additive response/DTO fields for the full `AggregationSummary`.
- [ ] Preserve null vs zero and absent vs empty semantics at every boundary.
- [ ] Render PASS, FAIL, UNKNOWN, NOT_EVALUATED, NOT_APPLICABLE, and SERVICE_ERROR counts separately in PDF/UI.
- [ ] Render score and coverage as separate values; never show null score as `0`.
- [ ] Keep `creative_grade`, `readiness`, and `render_authorization` unchanged and separately represented.
- [ ] Add ML/API, DTO/PDF, and frontend representation tests for all six states plus zero-scored aggregation.
- [ ] Do not add a new RuleOutcome union member to TypeScript or Java; use the additive evaluation-state contract.

### Task 6: Golden boundary validation and Family 1–6 regression gate

**Files:**
- Add only Family 7 tests/report fixtures required by prior tasks.
- Do not modify Family 1–6 Gold Truth or baseline artifacts.

- [ ] Run synthetic aggregation matrix tests.
- [ ] Run all existing Family 1–6 focused suites.
- [ ] Run full ML suite.
- [ ] Run backend DTO/PDF and frontend representation tests.
- [ ] Run deterministic Golden comparator with historical missing-dimension checks.
- [ ] Confirm no new Family 1–6 semantic regressions, no unintended policy changes, and no performance/corpus-role inputs.
- [ ] Stop for human review before any Family 8 policy decision.

## Deferred scope

- Creative-grade redesign.
- Readiness policy redesign.
- Render-authorization policy redesign.
- Parser semantic changes.
- RuleEngine evaluator changes.
- Ruleset changes and RULESET 1.8.
- Family 1–6 changes.
- Meta/public-comment and publisher changes.
- Performance/prediction integration.

## Review gate

This plan contains design and TDD steps only. No Family 7 runtime implementation is included. Human approval is required before Task 1 or any production/test runtime change begins.


## Approved clarifications governing execution

These rules override any earlier ambiguous wording in this plan:

- `scoredCount = PASS + FAIL`.
- `scoredCount == 0` with one or more semantic rows (`UNKNOWN`, or other non-scored rows) produces `score=null` and `aggregationState=NO_SCORED_ITEMS`.
- `NO_EVALUATED_ITEMS` is reserved for no relevant evaluation actually running; UNKNOWN-only is never `NO_EVALUATED_ITEMS`.
- `applicableCount = PASS + FAIL + UNKNOWN + NOT_EVALUATED + SERVICE_ERROR`; `NOT_APPLICABLE` is excluded.
- `semanticEvaluationCount = PASS + FAIL + UNKNOWN`.
- `evaluationCoverage = semanticEvaluationCount / applicableCount` when `applicableCount > 0`; otherwise coverage is `null`/`NOT_APPLICABLE`.
- Numeric score and evaluation coverage are independent fields.
- Parser timeout before downstream evaluation yields `evaluationState=NOT_EVALUATED`, `outcome=null`, and preserved reason/provenance.
- `BASELINE_NOT_CAPTURED` is comparator-only provenance classification and is never a runtime evaluation state.
- Task 1’s desired pure function is `summarize_aggregation(rows) -> AggregationSummary`; its red tests establish the approved contract before implementation.
