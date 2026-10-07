# POMPOM GOLDEN V1 — v1.7 Baseline Report

This document is generated from:

```text
intelligence/data/golden/pompom-golden-v1/reports/v1.7/golden-regression-report.json
intelligence/data/golden/pompom-golden-v1/reports/v1.7/golden-regression-report.md
```

## Baseline identity

- Golden Set: `POMPOM_GOLDEN_V1`
- Assets: `9`
- Corpus: `3 WINNER / 3 MIDDLE / 3 NEGATIVE`
- Ruleset: `1.7`
- Baseline: `BASELINE_V1_7`
- Provider mode: `FROZEN_DETERMINISTIC`
- Performance dependencies detected: `0`

## Current baseline report

| Metric | Value |
|---|---:|
| Golden assertions | 261 |
| Semantic passed | 22 |
| Semantic failed | 10 |
| Improved from baseline | 0 |
| Unchanged known issues | 70 |
| NEW semantic regressions | 0 |
| Expected policy changes | 0 |
| Unexpected policy regressions | 0 |
| Gold review required | 62 |

## Calibration release gate

```text
PASS
```

The baseline comparison has no **new** semantic regressions and no unexpected policy regressions because current output is compared against itself. Existing semantic failures and parser gaps remain visible in the per-asset JSON/Markdown report and are not silently converted into Gold Truth.

## Important baseline observations

- Sticky Ball is parsed with two attempts and `PULL + SQUEEZE` canonical strategy families in the deterministic harness.
- Box Cat and Spot-Stealing Cat retain `TIMELINE_PARSE_INCOMPATIBLE` baseline issues.
- Upside-Down Chair retains an explicit bounded `PARSER_DISCOVERY_TIMEOUT` baseline status.
- Policy output remains separate from Gold Truth; current grades and render authorization are not structural labels.
- The current report is a baseline artifact, not a claim that all nine prompts are semantically correct under the existing engine.

## Per-asset detail

The machine-readable report is authoritative for assertion-level expected/current/baseline values:

```text
intelligence/data/golden/pompom-golden-v1/reports/v1.7/golden-regression-report.json
```

No calibration rule fix has been applied in this phase.
