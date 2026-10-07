# Golden Regression Workflow V1

## Before a calibration family change

Run the deterministic baseline/golden command from `intelligence/ml-service`:

```bash
.venv/bin/python -m app.golden.baseline \
  --manifest ../data/golden/pompom-golden-v1/manifest.yaml \
  --ruleset ../data/rules/RULESET_1.7.yaml \
  --out ../data/golden/pompom-golden-v1/baselines/v1.7/baseline.json
```

Then generate the comparison report:

```bash
python3 - <<'PY'
from pathlib import Path
from app.golden.report import write_regression_report

base = Path('../data/golden/pompom-golden-v1')
write_regression_report(
    base / 'truth/gold_truth.yaml',
    base / 'policy/policy_expectations_v1.7.yaml',
    base / 'baselines/v1.7/baseline.json',
    base / 'baselines/v1.7/baseline.json',
    base / 'reports/v1.7',
)
PY
```

## Calibration family loop

```text
FIX ONE FAMILY
      ↓
RUN ALL 9 FROZEN PROMPTS
      ↓
COMPARE GOLD TRUTH + v1.7 BASELINE + CURRENT
      ↓
NEW SEMANTIC REGRESSION?
      ├─ YES → STOP, trace root cause, make one minimal fix, rerun
      └─ NO  → review policy diffs and continue
```

The first family after infrastructure approval is:

```text
STRATEGY / ATTEMPT CANONICALIZATION
```

## Release gate

A calibration change is releasable only when:

```text
NEW SEMANTIC REGRESSIONS = 0
UNEXPECTED POLICY REGRESSIONS = 0
```

Total pass count and average creative grade are not the release KPI.

## Deterministic test boundary

Golden CI must not call:

- OpenAI or another live semantic provider
- OpenArt
- Meta, TikTok, YouTube, or any social API
- video rendering
- performance/prediction tables

Provider integration tests remain separate from deterministic Golden regression.

## Source drift

A changed prompt hash is `GOLDEN_FIXTURE_DRIFT` and stops the gate. Updating a frozen prompt requires a deliberate Golden Set version/review update; it must never silently reuse old Gold Truth.

## Representation contract

Canonical state shares use `PERCENT_0_100` and must render as:

```text
3 seconds / 15 seconds → 20%
```

UI, API, PDF, and Golden representation tests must not independently reinterpret the unit.

## Documentation location

Critical calibration artifacts live under tracked `intelligence/docs`. Root `/docs` is ignored in this repository and is not used for release-critical calibration specifications.
