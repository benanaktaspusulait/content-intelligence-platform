# FAMILY 2 — Escalation Calibration Report

**Golden Set:** `POMPOM_GOLDEN_V1`

**Family:** `ESCALATION`

**Ruleset:** `1.7`

**Status:** FAMILY 2 COMPLETE — FAMILY 3 NOT STARTED

## 1. Gold Truth Lock

| Asset | Gold escalation | Confidence | Review |
|---|---|---|---|
| Sticky Ball | STRONG | HIGH | APPROVED |
| Ball-Multiplying Crocodile | STRONG | HIGH | APPROVED |
| Upside-Down Chair | STRONG | MEDIUM | APPROVED |
| Lamp | MODERATE | MEDIUM | APPROVED |
| Snack Box | MODERATE | MEDIUM | APPROVED |
| Box Cat | MODERATE | MEDIUM | APPROVED |
| Spot-Stealing Cat | WEAK | HIGH | APPROVED |
| Sneaky Door | MODERATE | MEDIUM | APPROVED |
| Island Journal | NOT_APPLICABLE | HIGH | APPROVED |

Confidence remains separate from review status.

## 2. Root Cause

The previous escalation path had two interpretation problems:

1. Assessment `_escalation` required at least two parsed attempts and compared only attempt intensity, so Crocodile, Lamp, and other structurally useful prompts produced `UNKNOWN` even when consequence evidence existed.
2. Canonical escalation evidence exposed only a small set of signals and did not distinguish strong multi-axis escalation from weak repetition.

Family 2 now consumes canonical escalation evidence directly. It does not recalculate escalation from attempt intensity in assessment or require a new strategy.

## 3. Canonical Escalation Axes

The canonical evidence projection now keeps separate axes for:

```text
forceRise
consequenceExpansion
deformation
scopeExpansion
difficultyRise
stakesRise
persistence
quantityGrowth
```

The projection also carries:

```text
applicability
strength = STRONG | MODERATE | WEAK | UNKNOWN | NOT_APPLICABLE
```

A single event may provide multiple axes, but the evaluator does not add points mechanically for every axis. Strong classification requires material evidence such as quantity growth, deformation plus scope/persistence, force plus difficulty/stakes, or character-impact scope. Repetition alone remains weak.

## 4. Minimal Changes

- Extended `CanonicalEscalationEvidence` with typed multi-axis fields and strength/applicability.
- Preserved JSON-safe `to_dict()` projection.
- Added applicability handling for prompts without an established local mechanic.
- Updated `ESCALATION_005` to use canonical strength while preserving numeric `actual_value`/`required_value` compatibility for existing API consumers.
- Updated `ESCALATION_005` to use canonical strength. STRONG/MODERATE map to PASS; WEAK maps to FAIL; UNKNOWN remains UNKNOWN; NOT_APPLICABLE remains NOT_APPLICABLE.
- Updated pre-render assessment `_escalation` to consume canonical escalation evidence rather than attempt-intensity comparison.
- Did not modify ruleset thresholds, severity, Family 1 strategy evidence, payoff policy, or scoring policy.

## 5. Per-Asset Result

| Asset | Gold | v1.7 baseline | Current | Classification |
|---|---|---|---|---|
| Sticky Ball | STRONG | NEEDS_ATTENTION | STRONG | IMPROVED_FROM_BASELINE |
| Ball-Multiplying Crocodile | STRONG | UNKNOWN | STRONG | IMPROVED_FROM_BASELINE |
| Upside-Down Chair | STRONG | unavailable | unavailable | UNCHANGED_KNOWN_ISSUE |
| Lamp | MODERATE | UNKNOWN | MODERATE | IMPROVED_FROM_BASELINE |
| Snack Box | MODERATE | UNKNOWN | MODERATE/REVIEW-SAFE | GOLD REVIEW STATUS MEDIUM |
| Box Cat | MODERATE | UNKNOWN | MODERATE | IMPROVED_FROM_BASELINE |
| Spot-Stealing Cat | WEAK | UNKNOWN | WEAK | GOLD REVIEW STATUS HIGH |
| Sneaky Door | MODERATE | UNKNOWN | UNKNOWN | UNCHANGED parser gap |
| Island Journal | NOT_APPLICABLE | UNKNOWN | NOT_APPLICABLE | PASS / applicability corrected |

The comparator report remains the authoritative machine-readable result; the table summarizes the escalation dimension only.

## 6. Golden Gate Result

Generated report:

```text
intelligence/data/golden/pompom-golden-v1/reports/family2-current/golden-regression-report.json
```

| Metric | Result |
|---|---:|
| Golden assertions | 261 |
| Semantic passed | 25 |
| Semantic failed | 8 |
| Improved from baseline | 15 |
| Unchanged known issues | 59 |
| Gold review required | 57 |
| NEW semantic regressions | 0 |
| Expected policy changes | 4 |
| Unexpected policy regressions | 0 |
| Release gate | PASS |

The four policy changes remain expected downstream consequences of canonical evidence improvements. No policy threshold or grade policy was tuned.

## 7. Regression Coverage

Added deterministic cases for:

- Sticky wall deformation as strong escalation without a new strategy;
- Crocodile 1 → 3 → 6 quantity growth;
- Lamp repeated visibility interaction not being strong by repetition alone;
- Spot Cat repeated target claims remaining weak;
- Island Journal escalation being NOT_APPLICABLE;
- assessment using canonical escalation without requiring attempt intensity;
- JSON-safe escalation evidence on every rule outcome.

## 8. Validation

- Family 2 focused tests: **6 passed**
- Existing Family 1/escalation-focused tests: **56 passed**
- Full ML suite after Family 2 changes: **466 passed**
- Golden release gate: **PASS**
- NEW semantic regressions: **0**
- Unexpected policy regressions: **0**
- Performance dependencies: **0**

## 9. Deferred Scope

Family 3 — `GOAL + REALIZATION` has not started. Family 2 is complete and must be approved before any later calibration family begins.
