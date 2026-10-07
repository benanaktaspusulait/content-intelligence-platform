# Family 5 — Final Golden Validation and Applicability Lock

**Golden set:** `POMPOM_GOLDEN_V1`  
**Ruleset:** `RULESET_1.7`  
**Validation worktree:** `/Users/benanaktas/.kiro/worktrees/content-intelligence-family5`  
**Task:** 7 — full regression, Golden regeneration, and Family 5 acceptance report  
**Implementation changes in Task 7:** none; no commit created.

## Final status

**Family 5 applicability: APPROVED / FROZEN WITH DOCUMENTED OUT-OF-SCOPE WAIVER.**

The approved Tasks 1–6 per-rule lock, canonical applicability propagation, three independent comparator assertions, taxonomy isolation, focused tests, full ML suite, backend checks, frontend checks, and Golden CI all passed. The formal Golden release gate is **PASS** (`newSemanticRegressions=0`, `unexpectedPolicyRegressions=0`).

A pre-existing generic baseline divergence is explicitly waived for Family 5: Box Cat and Spot Cat show `GOAL_VISIBLE_EARLY` and `BEAT_DENSITY_RULE` changes versus the captured v1.7 baseline, which changes their score and critical-count policy projection. This is outside specialized applicability and is recorded as a separate follow-up work item; no generic evaluator, scorer, baseline, or Family 1–4 behavior was changed here.

Family 6 and later families did not start. No ruleset, policy expectation, creative grade threshold, render-authorization rule, RuleEngine implementation, Family 1–4 semantic implementation, performance work, Meta/public-comment work, or other implementation behavior was changed by this waiver decision.

## 1. Approved per-rule Gold Truth lock

Tasks 1–6 supplied the approved rule-id-keyed lock in `intelligence/data/golden/pompom-golden-v1/truth/gold_truth.yaml`. All 27 entries have `reviewStatus: APPROVED`. The legacy aggregate is not authoritative; the comparator skips the aggregate dimension and emits exact per-rule assertions only.

Legend: `A` = `APPLICABLE`, `NA` = `NOT_APPLICABLE`, `U` = `UNKNOWN`; suffixes are Gold Truth confidence (`H`/`M`).

| Asset | `STUBBORN_RETURN_LOOP` | `STUBBORN_RETURN_HOOK` | `STUBBORN_RETURN_PAYOFF` | Gold evidence / rationale |
|---|---|---|---|---|
| `sticky-ball-01` | `NA (M)` | `NA (M)` | `NA (M)` | Sticky deformation; no stubborn-return boundary/profile. |
| `ball-crocodile-01` | `NA (M)` | `NA (M)` | `NA (M)` | Quantity multiplication; no return/reclaim boundary/profile. |
| `upside-chair-01` | `NA (M)` | `NA (M)` | `NA (M)` | `chair turns upside down by itself` (`FIRST ESCALATION`); final inversion (`FINAL TWIST`) is not a return/reclaim profile. |
| `lamp-01` | `NA (M)` | `NA (M)` | `NA (M)` | Observation-dependent light state, not a stubborn-return boundary. |
| `snack-box-01` | `NA (M)` | `NA (M)` | `NA (M)` | Changing contents, not a stubborn-return boundary. |
| `box-cat-01` | `A (H)` | `U (M)` | `A (H)` | `cat claims it again`; `recurrence across attempts`; opening access conflict; final cat reclaim after apparent success. |
| `spot-cat-01` | `NA (M)` | `NA (M)` | `NA (M)` | `cat claims that exact spot first` (`SINGLE ANIMAL RULE`), but changing targets do not establish the fixed return/reclaim profile. |
| `sneaky-door-01` | `NA (M)` | `NA (M)` | `NA (M)` | Multi-clip door behavior, not the low-memory stubborn-return profile. |
| `island-journal-01` | `NA (M)` | `NA (M)` | `NA (M)` | No central absurd mechanic establishes a specialized profile. |

`UNKNOWN` and `NOT_APPLICABLE` remain distinct exact values. The approved lock contains both values, and the generated canonical outputs contain both values; no conversion to `FAIL` or creative zero is permitted.

## 2. Canonical per-rule outputs and evidence references

The generated `current.json` carries the canonical `pre_render_assessment.specialized_applicability` map. Status assertions compare the three rule ids independently; confidence and evidence references remain additive explanatory data.

| Asset | Canonical Loop | Canonical Hook | Canonical Payoff | Canonical evidence references |
|---|---|---|---|---|
| `sticky-ball-01` | `NA/H` | `NA/H` | `NA/H` | `beat_01`–`beat_07` for each row. |
| `ball-crocodile-01` | `NA/H` | `NA/H` | `NA/H` | `beat_03`, `beat_05` for each row. |
| `upside-chair-01` | no output | no output | no output | `PARSER_TIMEOUT`; no safe applicability inference. Gold remains locked `NA/M`. |
| `lamp-01` | `NA/M` | `NA/M` | `NA/M` | No canonical beat references. |
| `snack-box-01` | `NA/M` | `NA/M` | `NA/M` | No canonical beat references. |
| `box-cat-01` | `A/M` | `U/M` | `A/M` | `beat_01`–`beat_05` for each row. |
| `spot-cat-01` | `NA/M` | `NA/M` | `NA/M` | `beat_01`–`beat_05` for each row. |
| `sneaky-door-01` | `NA/H` | `NA/H` | `NA/H` | No canonical beat references. |
| `island-journal-01` | `NA/H` | `NA/H` | `NA/H` | `beat_02`, `beat_07` for each row. |

The current canonical status matches the approved status for every parsed asset/rule row. Box Cat canonical confidence is `MEDIUM` while Gold confidence is `HIGH` for Loop and Payoff; this is an evidence-confidence difference, not a status substitution. Chair is intentionally unresolved because the parser timeout precedes canonical/RuleEngine output.

## 3. Golden comparator assertions and divergence

The regenerated report is:

- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/current.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/golden-regression-report.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/golden-regression-report.md`

Per-rule assertion check:

- 9 assets × 3 independent rule ids = **27 applicability assertion rows**.
- Every asset has exactly three rows.
- Applicability rows: **22 `PASS`**, **2 `IMPROVED_FROM_BASELINE`** (Box Cat Loop and Payoff), **3 `GOLD_REVIEW_REQUIRED`** (Chair parser timeout).
- No legacy aggregate row is used as an authoritative assertion.
- `UNKNOWN != NOT_APPLICABLE` check: **PASS**.

The two Box Cat improved rows represent the approved canonical applicability projection moving from the old baseline `UNKNOWN` to current `APPLICABLE`; they do not alter the current RuleEngine outcome, which remains `UNKNOWN` until the engine activation evidence is independently active. Chair's three rows are review-required because current output is absent, not because `UNKNOWN` was converted to `NOT_APPLICABLE`.

The current specialized RuleEngine comparison covered 24 rows (8 parsed assets × 3 rules; Chair has no evaluation in either snapshot): **0 specialized outcome differences**. RuleEngine behavior for the specialized rules is therefore unchanged.

### Full Golden metrics

| Metric | Result |
|---|---:|
| Assets | 9 |
| Golden assertions | 314 |
| Semantic passed | 75 |
| Semantic failed | 5 |
| Improved from baseline | 28 |
| Unchanged known issues | 52 |
| Gold review required | 61 |
| New semantic regressions | 0 |
| Expected policy changes | 4 |
| Unexpected policy regressions | 0 |
| Release gate | **PASS** |

## 4. Documented out-of-scope generic baseline drift waiver

The strict before/after comparison used `baselines/v1.7/baseline.json` versus the generated `family5-current/current.json` and compared:

- `report.evaluations`;
- `report.overallScore`;
- `assessment.creative_grade`;
- `assessment.creative_score`;
- `assessment.render_authorization`;
- the comparator's policy projection: `baselineStatus`, `creativeGrade`, `creativeScore`, `evidenceCompleteness`, `renderAuthorization`, `blockers`, `criticals`, `warnings`, `unknowns`, and `notApplicable`.

**Waiver status: ACCEPTED FOR FAMILY 5.** The specialized Family 5 scope is unaffected; the generic drift is documented below and deferred to a separate follow-up work item.

| Asset | Changed evaluator outcomes | Score change | Grade | Render authorization | Policy change |
|---|---|---:|---|---|---|
| `box-cat-01` | `GOAL_VISIBLE_EARLY`: `FAIL → PASS`; `BEAT_DENSITY_RULE`: `FAIL → PASS` | `38.2954545 → 61.8181818` (`creative_score` `38.30 → 61.82`) | `F → F` | `BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE` | `criticals: 2 → 0`; other policy fields unchanged |
| `spot-cat-01` | `GOAL_VISIBLE_EARLY`: `FAIL → PASS`; `BEAT_DENSITY_RULE`: `FAIL → PASS` | `38.2954545 → 61.8181818` (`creative_score` `38.30 → 61.82`) | `F → F` | `BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE` | `criticals: 2 → 0`; other policy fields unchanged |

The changed generic outcomes are a pre-existing baseline/current consistency issue, not a Family 5 applicability effect. Family 5 specialized RuleEngine rows remain unchanged across 24 comparisons, and the creative grade/render authorization remain unchanged for the affected assets. The drift is intentionally waived here rather than hidden or repaired by changing generic evaluators, scoring, or the v1.7 baseline.

Follow-up work item: `intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_FOLLOWUP.md`. It records the exact Box Cat/Spot Cat deltas and is not started as part of Family 5.

## 5. Validation commands and results

All commands below were executed from the isolated worktree. The worktree-local `intelligence/ml-service/.venv/bin/python` was available and used.

### Focused ML validation

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q \
  tests/test_family5_specialized_applicability.py \
  tests/test_golden_comparator.py \
  tests/test_golden_representation_contract.py \
  tests/test_api_conversions.py \
  tests/test_ruleset_1_7_stubborn_return.py \
  --no-header -p no:cacheprovider
```

Result: **47 passed**, 20 warnings, 1.90s. The warnings are existing `datetime.utcnow()` deprecation warnings from `app/parser/prompt_parser.py`.

### Full ML suite

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q --no-header -p no:cacheprovider
```

Result: **498 passed**, 125 warnings, 24.74s. Warnings include the same `datetime.utcnow()` deprecation and the existing `google.generativeai` end-of-support `FutureWarning`.

### Family 5 Golden CI

```bash
cd intelligence/ml-service
.venv/bin/python scripts/run_pompom_golden_ci.py \
  --manifest ../data/golden/pompom-golden-v1/manifest.yaml \
  --baseline ../data/golden/pompom-golden-v1/baselines/v1.7/baseline.json \
  --ruleset ../data/rules/RULESET_1.7.yaml \
  --truth ../data/golden/pompom-golden-v1/truth/gold_truth.yaml \
  --policy ../data/golden/pompom-golden-v1/policy/policy_expectations_v1.7.yaml \
  --reports ../data/golden/pompom-golden-v1/reports/family5-current
```

Result: exit 0; `releaseGate: PASS`; `newSemanticRegressions=0`; `unexpectedPolicyRegressions=0`; summary metrics are recorded in Section 3. This command generated only the three `family5-current` report artifacts listed above.

### Backend representation validation

```bash
cd intelligence/backend
mvn -q -Dtest=QualityReportDtoTest,QualityReportPdfServiceTest test
```

Result: **PASS**, exit 0.

### Frontend production build

```bash
cd intelligence/frontend
NG_CLI_ANALYTICS=false npm run build
```

Result: **PASS**, exit 0; application bundle generation completed in 8.201s. Existing budget warnings were emitted: initial bundle `923.78 kB` over the `500.00 kB` budget, `render-dashboard.page.ts` component styles `5.79 kB` over `4.00 kB`, and `quality-validator.component.scss` `19.97 kB` over `4.00 kB`.

### Frontend focused mapper representation test

```bash
cd intelligence/frontend
NG_CLI_ANALYTICS=false npx ng test --watch=false --include='src/app/pages/quality-validator/specialized-applicability.spec.ts'
```

Result: **1 test file passed; 2 tests passed**, exit 0. The tests preserve all three specialized rule rows and keep missing applicability evidence neutral.

### Additional read-only validation

The following read-only checks were also executed against the generated snapshots:

1. Per-rule truth/output audit: 27 approved truth entries, 27 assertion rows, 3 rows per asset, and canonical statuses `APPLICABLE`, `UNKNOWN`, and `NOT_APPLICABLE` all present.
2. Taxonomy assertion: `UNKNOWN_NEQ_NOT_APPLICABLE PASS`.
3. Specialized RuleEngine comparison: `SPECIALIZED_RULEENGINE_ROWS 24 ... DIFFS [] ... RESULT PASS`.
4. Strict outcome/policy isolation comparison: `ALL_REQUESTED_FIELDS_UNCHANGED False`; the accepted generic drift waiver is detailed in Section 4.

## 6. Acceptance checklist

| Acceptance criterion | Result |
|---|---|
| Per-rule Gold Truth locked | **PASS** — 27 approved rule-id-keyed entries. |
| Three independent assertions per asset | **PASS** — 27 rows, exactly 3 per asset. |
| `UNKNOWN` distinct from `NOT_APPLICABLE` | **PASS** — exact taxonomy and focused tests. |
| RuleEngine behavior unchanged | **PASS for Family 5 specialized rows** — 24 compared, 0 diffs; Chair has no evaluation. |
| Score unchanged | **WAIVED** — pre-existing generic GOAL/BEAT drift is documented separately; no Family 5 applicability path changes score |
| Creative grade unchanged | **PASS** — remained `F` for the changed assets. |
| Render authorization unchanged | **PASS** — remained `BLOCKED_CREATIVE_FAILURE` for the changed assets. |
| Policy projection unchanged | **WAIVED** — generic critical-count/score drift is documented separately and not changed here. |
| Family 1–4 regressions zero | **PASS WITH WAIVER** — no Family 1–4 implementation or specialized outcome drift; generic baseline divergence is out of scope. |
| Golden release gate PASS | **PASS** — formal gate PASS; Family 5 is approved with the documented waiver. |
| Family 6+ started | **NO** — explicitly out of scope and not started. |

## 7. Waiver and follow-up

- `upside-chair-01` remains a parser timeout; its Gold Truth lock is `NOT_APPLICABLE` for all three rules, but no canonical/RuleEngine output is emitted. The comparator correctly records three `GOLD_REVIEW_REQUIRED` rows rather than inventing output.
- The formal Golden report gate measures new semantic and unexpected policy regressions. The separately documented generic baseline drift is accepted as an out-of-scope waiver and is not used to alter Family 1–4, scoring, or baseline behavior here.
- The exact follow-up is recorded in `intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_FOLLOWUP.md`; it is not started as part of Family 5.
- No commit was created by this waiver documentation change.

**Completion decision:** Family 5 is **APPROVED / FROZEN WITH DOCUMENTED WAIVER**. Family 6 and all later families remain unstarted.
