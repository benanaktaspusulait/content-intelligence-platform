# FAMILY 1 — Strategy / Attempt Calibration Report

**Golden Set:** `POMPOM_GOLDEN_V1`

**Family:** `STRATEGY / ATTEMPT CANONICALIZATION`

**Ruleset:** `1.7`

**Status:** FAMILY 1 COMPLETE — FAMILY 2 NOT STARTED

## 1. Gold Truth Lock

Family 1 human review is approved and locked separately from confidence:

| Asset | Gold active attempts | Gold distinct strategies | Gold strategy families | Confidence / review |
|---|---:|---:|---|---|
| Sticky Ball | 2 | 2 | PULL, TEST_SQUEEZE | HIGH / APPROVED |
| Ball-Multiplying Crocodile | 3 | 2 | THROW_TOSS, ROLL/TEST | MEDIUM / APPROVED |
| Upside-Down Chair | 3 | 2 | FLIP, GUARD_AND_APPROACH | MEDIUM / APPROVED |
| Lamp | 3 | 1 | OBSERVE_CONTROL_VISIBILITY | MEDIUM / APPROVED |
| Snack Box | 4 | 2 | REOPEN/TEST, TAP_TURN/CONTROLLED_REOPEN | MEDIUM / APPROVED |
| Box Cat | 3 | 3 | DISPLACE, RELOCATE, GUARD | MEDIUM / APPROVED |
| Spot-Stealing Cat | 3 | 1 | COMMIT_TO_TARGET | HIGH / APPROVED |
| Sneaky Door | 3 | 3 | PULL, OBSERVE_TEST, DECOY_CAPTURE | MEDIUM / APPROVED |
| Island Journal | 0 | 0 | — | HIGH / APPROVED |

`confidence` and `reviewStatus` are separate fields. Medium confidence means semantic uncertainty remains; it does not mean the human review is pending.

## 2. Root Cause

Family 1 divergence was caused by two upstream interpretation boundaries:

1. **Timestamp-only timeline parsing:** Box Cat and Spot-Stealing Cat use existing markdown section headings such as `Attempt 1`, `Attempt 2`, and `Attempt 3` rather than timestamp-labelled beats. The parser therefore returned zero timeline/attempt evidence even though the source prompt contained complete structured attempt sections.
2. **Strategy-family normalization:** canonical strategy inference previously trusted only primary verbs and did not normalize source-specific but structurally obvious methods such as `COMMIT_TO_TARGET`, `DISPLACE`, `RELOCATE`, and `GUARD`. Reactive actions and small execution changes risked becoming separate strategies.

The fix was applied at the parser/canonical evidence boundary. Downstream attempt rules continue consuming `attempt_evidence`; no downstream family-score or policy threshold was changed.

## 3. Minimal Changes

### Parser

- Added markdown-labelled timeline section fallback for existing source formats.
- Recognizes `Frame zero`, `Attempt N`, `Fake win/final payoff`, `Escalation`, and `Payoff` sections.
- Assigns deterministic synthetic time windows only inside the parsed IR; source prompt bytes are unchanged.
- Preserves parser incompatibility baseline behavior for sources not in the frozen cohort.

### Canonical evidence

- Keeps `primaryAction`/reactive action separate from `strategyFamily`.
- Normalizes Box Cat methods as `DISPLACE`, `RELOCATE`, and `GUARD`.
- Normalizes Spot Cat target changes/decoy execution to one `COMMIT_TO_TARGET` family.
- Keeps Sticky Ball `CATCH` as reactive setup and `SQUEEZE` as intended test strategy.
- Does not count escalation-only or reaction-only beats as new attempts.

### Gold Truth

- Lamp changed from `DIRECT_WATCH + INDIRECT_WATCH` to one approved strategy family: `OBSERVE_CONTROL_VISIBILITY`.
- Family 1 dimensions now carry `reviewStatus: APPROVED` independently from confidence.
- No corpus role or performance data was added to engine inputs.

## 4. Before / After Matrix

| Asset | Gold attempts | v1.7 attempts | Current attempts | Gold distinct | v1.7 distinct | Current distinct | Gold families | Current families | Result |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| Sticky Ball | 2 | 2 | 2 | 2 | 2 | 2 | PULL, TEST_SQUEEZE | PULL, SQUEEZE | PASS_AFTER_NORMALIZATION |
| Crocodile | 3 | 0 | 0 | 2 | 0 | 0 | THROW_TOSS, ROLL/TEST | — | UNCHANGED_KNOWN_ISSUE |
| Upside-Down Chair | 3 | unavailable | unavailable | 2 | unavailable | unavailable | FLIP, GUARD_AND_APPROACH | — | UNCHANGED_KNOWN_ISSUE |
| Lamp | 3 | 0 | 0 | 1 | 0 | 0 | OBSERVE_CONTROL_VISIBILITY | — | UNCHANGED_KNOWN_ISSUE |
| Snack Box | 4 | 0 | 0 | 2 | 0 | 0 | REOPEN/TEST, TAP_TURN/CONTROLLED_REOPEN | — | UNCHANGED_KNOWN_ISSUE |
| Box Cat | 3 | 0 | 3 | 3 | 0 | 3 | DISPLACE, RELOCATE, GUARD | DISPLACE, RELOCATE, GUARD | IMPROVED_FROM_BASELINE |
| Spot Cat | 3 | 0 | 3 | 1 | 0 | 1 | COMMIT_TO_TARGET | COMMIT_TO_TARGET | IMPROVED_FROM_BASELINE |
| Sneaky Door | 3 | 0 | 0 | 3 | 0 | 0 | PULL, OBSERVE_TEST, DECOY_CAPTURE | — | UNCHANGED_KNOWN_ISSUE |
| Island Journal | 0 | 0 | 0 | 0 | 0 | 0 | — | — | PASS |

## 5. Golden Comparator Result

Generated report:

```text
intelligence/data/golden/pompom-golden-v1/reports/family1-current/golden-regression-report.json
intelligence/data/golden/pompom-golden-v1/reports/family1-current/golden-regression-report.md
```

| Metric | Result |
|---|---:|
| Golden assertions | 261 |
| Semantic passed | 25 |
| Semantic failed | 9 |
| Improved from baseline | 11 |
| Unchanged known issues | 60 |
| Gold review required | 59 |
| NEW semantic regressions | 0 |
| Expected policy changes | 4 |
| Unexpected policy regressions | 0 |
| Release gate | PASS |

The four policy changes are expected downstream effects of parser/canonical evidence improvement for Box Cat and Spot Cat. No policy threshold or grade policy was tuned.

## 6. Regression Coverage Added

- Markdown section prompts become canonical attempt events without source rewriting.
- Box Cat resolves to 3 attempts / 3 strategy families.
- Spot Cat resolves to 3 attempts / 1 strategy family.
- Reactive LOOK/SMILE/WAIT beats remain non-attempts.
- CATCH remains reactive when followed by SQUEEZE/TEST behavior.
- Same-family execution variants remain one family.
- Existing Sticky Ball, escalation, confidence, and full Golden infrastructure tests remain green.

## 7. Validation

- Full ML suite: **460 passed, 103 warnings**
- Golden infrastructure suite: **26 passed**
- Final deterministic Golden gate: **PASS**
- Backend DTO/PDF representation tests: **passed**
- Frontend representation tests: **4 passed**
- New semantic regressions: **0**
- Unexpected policy regressions: **0**
- Performance dependencies detected: **0**

## 8. Deferred Scope

Family 2 — `ESCALATION` has not started. No escalation policy tuning was performed. Family 1 changes only ensure escalation beats do not become attempts or distinct strategies merely because they contain a stronger action or narrative escalation label.

**Recommendation:** `READY_FOR_FAMILY_2` only after the human-approved Family 1 report is accepted. This report does not authorize beginning Family 2 automatically.
