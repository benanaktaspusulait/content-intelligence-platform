# Investigation Prompt — Generic Golden Baseline Divergence

## Status

**READ-ONLY INVESTIGATION ONLY — NO IMPLEMENTATION**

This investigation is a follow-up to the completed Family 5 calibration. It must not reopen or modify Family 5 applicability semantics.

## Context

Family 5 is approved/frozen with a documented waiver. The formal Family 5 Golden gate is green:

```text
314 assertions
newSemanticRegressions = 0
unexpectedPolicyRegressions = 0
releaseGate = PASS
```

The separate generic baseline divergence is:

```text
box-cat-01
  GOAL_VISIBLE_EARLY: FAIL → PASS
  BEAT_DENSITY_RULE: FAIL → PASS
  score: 38.2954545 → 61.8181818
  creative grade: F → F
  render authorization: BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE
  criticals: 2 → 0

spot-cat-01
  GOAL_VISIBLE_EARLY: FAIL → PASS
  BEAT_DENSITY_RULE: FAIL → PASS
  score: 38.2954545 → 61.8181818
  creative grade: F → F
  render authorization: BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE
  criticals: 2 → 0
```

The three Family 5 specialized RuleEngine outcomes are unchanged across 24 parsed-asset comparisons:

```text
STUBBORN_RETURN_LOOP: no outcome differences
STUBBORN_RETURN_HOOK: no outcome differences
STUBBORN_RETURN_PAYOFF: no outcome differences
```

## Objective

Determine the first root cause of the Box Cat / Spot Cat baseline-current divergence without changing any repository behavior or generated artifact.

Answer:

> Why do the current snapshots produce `GOAL_VISIBLE_EARLY=PASS` and `BEAT_DENSITY_RULE=PASS` while the captured v1.7 baseline records `FAIL`, and why do the corresponding score/critical-count policy fields change?

## Required investigation path

1. **Verify artifact identity**
   - Compare the baseline fingerprint, current fingerprint, parser version, assessment version, RuleEngine version, scoring version, ruleset version, prompt hashes, and recorded git commits.
   - Confirm whether the baseline and current snapshots were produced from the same effective source/runtime revision.
   - Confirm the exact source prompt bytes for `box-cat-01` and `spot-cat-01` match the frozen manifest hashes.

2. **Compare raw evaluator evidence**
   - Inspect `report.evaluations` for both assets in:
     - `intelligence/data/golden/pompom-golden-v1/baselines/v1.7/baseline.json`
     - `intelligence/data/golden/pompom-golden-v1/reports/family5-current/current.json`
   - Compare for `GOAL_VISIBLE_EARLY` and `BEAT_DENSITY_RULE`:
     - outcome;
     - actual value;
     - required value;
     - threshold value;
     - message;
     - details/evidence payload.
   - Identify whether the difference is evaluator logic, parser IR, assessment projection, or serialized artifact state.

3. **Trace the first divergent input**
   - Inspect the parsed `videoPlanIR` for both assets in baseline/current.
   - Compare `goalEvidence`, beat count/roles, timestamps, durations, `majorBeat`, `consequenceType`, `visualStateId`, generation mode, and any structured timeline metadata consumed by the two rules.
   - Trace the exact evaluator functions for `GOAL_VISIBLE_EARLY` and `BEAT_DENSITY_RULE`.
   - Locate the first value that differs before the final outcome changes.

4. **Check provenance and generated artifacts**
   - Verify whether `current.json` was generated under the same deterministic provider mode and ruleset as baseline.
   - Check whether baseline/current are stale relative to their recorded git commits.
   - Do not regenerate baseline or current reports in-place. If a rerun is necessary, write all output to a temporary directory outside the repository and delete it afterward or leave no repository changes.

5. **Check policy projection only after evaluator divergence is explained**
   - Confirm that `creativeScore` and `criticals` changes are downstream effects of the two generic outcome changes.
   - Confirm `creativeGrade` and `renderAuthorization` remain unchanged.
   - Do not tune policy or scorer behavior.

## Files to inspect

- `intelligence/data/golden/pompom-golden-v1/baselines/v1.7/baseline.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/current.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family5-current/golden-regression-report.json`
- `intelligence/data/golden/pompom-golden-v1/manifest.yaml`
- `intelligence/data/golden/pompom-golden-v1/approved_hashes.yaml`
- `intelligence/data/golden/pompom-golden-v1/prompts/box-cat-01.md`
- `intelligence/data/golden/pompom-golden-v1/prompts/spot-cat-01.md`
- `intelligence/ml-service/app/parser/prompt_parser.py`
- `intelligence/ml-service/app/rules/rule_engine.py`
- `intelligence/ml-service/app/assessment/pre_render_assessment.py`
- `intelligence/ml-service/app/golden/deterministic_runner.py`
- `intelligence/ml-service/app/golden/baseline.py`
- `intelligence/ml-service/app/golden/comparator.py`
- `intelligence/data/rules/RULESET_1.7.yaml`
- `intelligence/data/rules/RULESET_1.6.yaml`

## Hard boundaries

Do **not**:

- change `GOAL_VISIBLE_EARLY`;
- change `BEAT_DENSITY_RULE`;
- change any RuleEngine evaluator;
- change parser behavior;
- change canonical Family 1–5 evidence;
- change scoring, creative grades, or render authorization;
- rebase, rewrite, or regenerate the v1.7 baseline in place;
- update Gold Truth or policy expectations;
- change Family 1–4 semantics;
- use performance data or corpus role;
- start Family 6 or any later family;
- touch Meta/public-comment work;
- create a commit;
- modify repository files other than an explicitly approved investigation report.

## Required output

Return a concise investigation result containing:

1. **Root cause:** the first divergent layer and exact evidence.
2. **Baseline/current matrix:** raw values and outcomes for both assets and both rules.
3. **Provenance finding:** whether the snapshots are comparable and why.
4. **Classification:** parser, canonical evidence, evaluator, assessment projection, baseline artifact, or unknown.
5. **Impact boundary:** confirm whether Family 5 specialized applicability, scoring, grade, and render authorization were affected.
6. **Recommendation:** one or more separate follow-up options, with no implementation performed.

If the root cause cannot be proven from repository evidence, return `UNKNOWN_ROOT_CAUSE` and list the missing evidence. Do not infer or repair.

## Stop condition

Stop after the read-only root-cause report. Family 5 remains **APPROVED / FROZEN WITH DOCUMENTED WAIVER** throughout this investigation, and Family 6 remains unstarted.
