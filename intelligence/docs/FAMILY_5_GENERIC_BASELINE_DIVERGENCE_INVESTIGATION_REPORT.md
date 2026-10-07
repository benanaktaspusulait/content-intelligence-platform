# Investigation Report — Generic Golden Baseline Divergence

**Status:** Read-only investigation complete  
**Family 5 status:** `APPROVED / FROZEN WITH DOCUMENTED WAIVER`  
**Follow-up implementation:** Not started

## Conclusion

**Root classification:** `PARSER`, with a secondary baseline provenance/comparability mismatch.

The frozen prompt bytes are identical, but the captured v1.7 baseline and current Family 5 snapshot were produced with different effective parser behavior:

- Baseline fingerprint commit: `4dde76e01717f9e58f17485e7e7cb4cbd40ad8cf`
- Current snapshot fingerprint commit: `72e59a315b574c8e48fd0e3d3ae9dbded0dbe919`
- Parser fallback that recognizes Markdown timeline sections was added in commit `878e0e5`.

The baseline parser produced no timeline beats for Box Cat and Spot Cat. The current parser recognizes their Markdown sections and produces five beats. That is the first divergence, before canonical evidence, RuleEngine evaluator logic, scoring, or assessment projection.

## 1. Prompt identity

Independent SHA-256 checks match the frozen manifest and approved hashes:

```text
box-cat-01  d93add25456b009ad9937920d1d40d56cbbd517ba6883b743f99a6c6f60bb854
spot-cat-01 76ea701ceb81d9bc4bc0ac6b9ed6998cea84c8423bb4fa1fa9793d9c523622e5
```

The prompt bytes are not the source of the baseline/current difference.

## 2. First divergence in the data path

### Baseline parser input/output

The two prompts use Markdown headings such as `Frame zero`, `Attempt 1`–`Attempt 3`, and `Fake win + final payoff`, rather than numeric timestamp ranges.

At the recorded baseline revision, the parser did not recognize these headings as timeline sections. The resulting IR had:

```text
beats = []
goalEvidence.goalExplicitness = UNKNOWN
goalEvidence.source = NONE
hook.startsAt = null
parser confidence = 0.45
evidenceMissing = ["beats"]
```

The baseline metadata also recorded warnings about missing explicit timeline beats and fallback parsing.

### Current parser input/output

The later Markdown-section fallback recognizes the same headings, assigns five 3-second beats, and derives goal evidence:

```text
beats = 5
roles = HOOK, ATTEMPT, ATTEMPT, ATTEMPT, FAKE_RESOLUTION
timestamps = 0–3, 3–6, 6–9, 9–12, 12–15
goalEvidence.goalExplicitness = EXPLICIT
hook.startsAt = 0.0
parser confidence = 0.62
```

The parser implementation is `intelligence/ml-service/app/parser/prompt_parser.py`, specifically Markdown-section parsing and goal extraction. The fallback addition is present in `878e0e5` and absent from the recorded baseline commit.

## 3. Why `GOAL_VISIBLE_EARLY` changes

`RuleEngine._evaluate_goal_visible_early` uses only:

- `videoPlanIR.goalEvidence.goalExplicitness`;
- the first beat;
- the first beat’s `startTime <= 0.8` condition.

Baseline:

```text
goalExplicitness = UNKNOWN
first beat = {}
actual = false
required = true
outcome = FAIL
```

Current:

```text
goalExplicitness = EXPLICIT
first beat starts at 0.0
actual = true
required = true
outcome = PASS
```

The evaluator implementation did not change. The evaluator receives different IR evidence because the parser behavior changed.

## 4. Why `BEAT_DENSITY_RULE` changes

`BEAT_DENSITY_RULE` consumes `story_density_evidence(videoPlanIR)` and passes a single-generation plan when canonical major beats are between 4 and 6.

Baseline:

```text
raw beats = 0
major beats = 0
load beats = 0
state transitions = 0
outcome = FAIL
```

Current:

```text
raw beats = 5
major beats = 5
load beats = 5
state transitions = 5
critical durations = [3, 3, 3, 3, 3]
outcome = PASS
```

The current five roles are classified as major beats by existing canonical role logic. No density threshold, ruleset, scorer, or evaluator implementation changed.

## 5. Downstream score and policy effects

The generic evaluator changes cause the downstream differences:

| Asset | Score | Creative grade | Render authorization | Critical count |
|---|---:|---|---|---:|
| `box-cat-01` | `38.2954545 → 61.8181818` | `F → F` | `BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE` | `2 → 0` |
| `spot-cat-01` | `38.2954545 → 61.8181818` | `F → F` | `BLOCKED_CREATIVE_FAILURE → BLOCKED_CREATIVE_FAILURE` | `2 → 0` |

The grade and authorization remain blocked because `MINI_STORY_LOCK` remains a failed blocker. The score and critical count change because the two generic critical failures disappear from the current parsed representation.

## 6. Family 5 independence

The investigation compared the three specialized RuleEngine outcomes across the eight parsed assets:

```text
STUBBORN_RETURN_LOOP: 0 differences
STUBBORN_RETURN_HOOK: 0 differences
STUBBORN_RETURN_PAYOFF: 0 differences
```

The source/history evidence shows the first divergence is the parser’s Markdown timeline fallback, not Family 5 applicability logic. The current Family 5 canonical read model consumes the parsed evidence but does not gate or alter the generic evaluators.

There is a shared dependency at the parser/IR layer, so absolute process isolation is not possible: a parser change can affect multiple rule families. However, the observed generic drift is semantically independent of Family 5 because:

1. the specialized outcomes are unchanged;
2. the changed generic evaluator implementations are outside Family 5;
3. the changed values are exactly the generic goal/beat evidence created by the parser fallback;
4. no Family 5 code path changes RuleEngine evaluation, scoring, or authorization.

## 7. Provenance finding

Declared version labels are insufficient to prove baseline comparability:

```text
parser_version             = prompt-parser-v2 in both
canonical_evidence_version = canonical-attempt-evidence-v2 in both
ruleset_version            = 1.7 in both
scoring_version            = quality-scorer-v2 in both
```

The behavioral parser change occurred under the same broad parser version label. The baseline is internally coherent for its recorded commit, but it is stale/incomparable as a same-runtime baseline for the current parser.

## 8. Separate follow-up recommendation

Do not repair the divergence in Family 5. The separate work item is:

```text
intelligence/docs/FAMILY_5_GENERIC_BASELINE_DIVERGENCE_FOLLOWUP.md
```

When explicitly opened, that work should:

1. add effective parser source/behavior provenance to Golden fingerprints;
2. replay the assets in temporary output locations at the relevant revisions (`4dde76e`, `72e59a3`, and current HEAD);
3. decide whether v1.7 remains a historical baseline or a new baseline is approved;
4. preserve the existing Gold Truth, Family 5 applicability model, RuleEngine semantics, and Family 1–4 scope until that decision is separately approved.

No source, baseline, policy, Gold Truth, scoring, evaluator, or runtime files were changed during this investigation. Family 6 remains unstarted.
