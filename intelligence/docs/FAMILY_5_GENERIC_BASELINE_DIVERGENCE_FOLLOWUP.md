# Follow-up — Generic Golden Baseline Divergence for Box Cat / Spot Cat

**Status:** Deferred follow-up work item — not started  
**Origin:** Family 5 final validation waiver  
**Scope:** Golden baseline consistency / generic evaluator maintenance  
**Family 5 status:** Approved and frozen with this issue explicitly waived

## Observed divergence

Comparing the captured RULESET 1.7 baseline with the regenerated Family 5 current snapshot shows the same generic evaluator drift for two assets:

| Asset | Evaluator changes | Score | Creative grade | Render authorization | Policy change |
|---|---|---|---|---|---|
| `box-cat-01` | `GOAL_VISIBLE_EARLY`: `FAIL → PASS`; `BEAT_DENSITY_RULE`: `FAIL → PASS` | `38.2954545 → 61.8181818` | `F → F` | `BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE` | `criticals: 2 → 0` |
| `spot-cat-01` | `GOAL_VISIBLE_EARLY`: `FAIL → PASS`; `BEAT_DENSITY_RULE`: `FAIL → PASS` | `38.2954545 → 61.8181818` | `F → F` | `BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE` | `criticals: 2 → 0` |

The Family 5 specialized outcome comparison is independent and unchanged:

```text
24 specialized RuleEngine rows compared
0 specialized outcome differences
```

The formal Family 5 Golden gate remains green:

```text
314 assertions
newSemanticRegressions = 0
unexpectedPolicyRegressions = 0
releaseGate = PASS
```

## Scope boundary

This follow-up is not Family 5 implementation work. It must not be addressed by:

- changing `GOAL_VISIBLE_EARLY`;
- changing `BEAT_DENSITY_RULE`;
- changing scoring or creative grade logic;
- changing render authorization;
- changing Family 1–4 Gold semantics;
- rebasing or mutating the immutable v1.7 baseline without a separate decision;
- using performance or corpus-role data;
- starting Family 6.

## Future investigation

When explicitly opened as a separate maintenance task, compare the baseline fingerprint/commit against the current evaluator implementation and determine whether the correct resolution is:

1. a historical baseline provenance correction;
2. a separately approved baseline regeneration; or
3. a generic evaluator regression/behavior review.

The follow-up must preserve the Family 5 applicability read model and must not use Family 5 as a reason to alter generic evaluator behavior.
