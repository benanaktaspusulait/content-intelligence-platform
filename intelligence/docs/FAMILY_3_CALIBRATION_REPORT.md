# FAMILY 3 — Goal + Realization Calibration Report

**Golden Set:** `POMPOM_GOLDEN_V1`

**Family:** `GOAL + REALIZATION`

**Ruleset:** `1.7`

**Status:** FAMILY 3 COMPLETE — FAMILY 4 NOT STARTED

## 1. Gold Truth Contract

### Goal

```text
EXPLICIT
IMPLICIT_BUT_OBSERVABLE
NOT_ESTABLISHED
UNKNOWN
NOT_APPLICABLE
```

### Realization

```text
status:
  AVAILABLE
  NOT_ESTABLISHED
  UNKNOWN
  NOT_APPLICABLE

mode:
  EXPLICIT
  IMPLICIT_BUT_OBSERVABLE
  null
```

`status=AVAILABLE` is intentionally not sufficient to describe the evidence mode. The canonical evidence now preserves the mode separately.

## 2. Locked Gold Distribution

| Asset | Goal | Intended effect | Realization status | Realization mode |
|---|---|---|---|---|
| Sticky Ball | IMPLICIT_BUT_OBSERVABLE | Control/retrieve / restore normal use | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Ball-Multiplying Crocodile | IMPLICIT_BUT_OBSERVABLE | Limit/control ball output | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Upside-Down Chair | EXPLICIT | Restore usable chair / sit safely | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Lamp | IMPLICIT_BUT_OBSERVABLE | Keep light usable while reading | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Snack Box | EXPLICIT | Obtain expected cracker/content | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Box Cat | EXPLICIT | Clear and keep box usable | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Spot Cat | EXPLICIT | Secure target sitting spot | AVAILABLE | IMPLICIT_BUT_OBSERVABLE |
| Sneaky Door | IMPLICIT_BUT_OBSERVABLE | Control/keep doorway usable | AVAILABLE | EXPLICIT |
| Island Journal | NOT_ESTABLISHED | NOT_ESTABLISHED | NOT_ESTABLISHED | null |

## 3. Minimal Changes

- Added `realization_mode` to canonical `StoryDensityEvidence`.
- Explicit REALIZATION/DECISION roles and explicit realization verbs map to `mode=EXPLICIT`.
- Normal-state result plus positive reaction/fake-resolution evidence maps to `mode=IMPLICIT_BUT_OBSERVABLE`.
- Smile alone does not establish realization.
- Narrative twist recognition does not become mechanic realization.
- Assessment now projects `realization_mode` alongside `story_structure.realization`.
- Goal assessment now consumes canonical `goalEvidence` when rule results are absent, preserving explicit versus implicit goal semantics.
- No Family 1/2 strategy or escalation behavior was changed.

## 4. Invariants Locked

```text
Missing explicit goal field != no goal
Missing explicit realization sentence != no realization
Observable purposeful behavior can establish implicit goal
Observable belief/action change can establish implicit realization
Realization != final resolution
Realization != payoff
Realization != fake resolution
Character smile alone != realization
“Aha!” alone != realization
Narrative twist != mechanic realization
NOT_ESTABLISHED != UNKNOWN
UNKNOWN != creative failure
```

## 5. Golden Result

Generated report:

```text
intelligence/data/golden/pompom-golden-v1/reports/family3-current/golden-regression-report.json
```

| Metric | Result |
|---|---:|
| Golden assertions | 269 |
| Semantic passed | 25 |
| Semantic failed | 8 |
| Improved from baseline | 16 |
| Unchanged known issues | 59 |
| Gold review required | 63 |
| NEW semantic regressions | 0 |
| Expected policy changes | 4 |
| Unexpected policy regressions | 0 |
| Release gate | PASS |

## 6. Validation

- Family 3 focused tests: **6 passed**
- Full ML suite: **463 passed, 8 skipped**
- Golden release gate: **PASS**
- Performance dependencies: **0**
- Family 4 not started

Family 3 is complete. No mechanic/fake-resolution/payoff calibration was started.
