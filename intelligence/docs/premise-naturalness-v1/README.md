# Premise Naturalness Gate V1

This is an additive, deterministic, opt-in premise screen. It measures configured dependencies between an object's expected use and an impossible response. Its outputs are planning hypotheses, not canonical quality scores, rendered evidence, retention predictions, or human creative judgement.

## Configuration and architecture

```json
{"generatorVersion":"v2","beatGrammarVersion":"v2","premiseNaturalnessGateVersion":"v1","premisePoolSize":480,"seed":42,"count":20,"rank":true}
```

API: existing `POST /api/v1/workflow/concepts/generate` (Java proxy path `/api/v1/intelligence/workflow/concepts/generate`). CLI:

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v2 --beat-grammar-version v2 --premise-naturalness-gate-version v1 --premise-pool-size 480 --seed 42 --count 20 --rank --text-report
```

The new dispatcher strips its two added options when the gate is disabled, then delegates to the accepted Beat Grammar dispatcher. V1, legacy V2, and legacy Beat Grammar output equality are tested. No accepted generator, ranker, short-form engine, story-premise engine, CPQ module, historical output, or scoring formula is edited.

Enabled pipeline:

1. Enumerate existing goal/object/engine/topology/environment compositions; apply accepted affordance compatibility and caller exclusions.
2. Evaluate unique object/goal/response/trigger premises against the new expectation model, before constructing beat plans or prose. Preserve rejected compositions, stages, flags, and naturalness evidence.
3. Check accepted Beat Grammar strategy/shape compatibility. Order options by seeded canonical digest and realize up to 480 compatible plans with the accepted builder. Recheck premise and opening-frame evidence.
4. Suppress duplicate engine/attempt sequences. Select up to 20 using bounded naturalness preference, concentration, specificity, payoff potential, and seeded ID, with a minimum creative distance of 0.28. No final ranking scores guide this stage.
5. Send the final candidates once to the accepted validation/ranking pipeline. Preserve that complete result separately as `rankingResult`. Rejected/revision outcomes remain visible; there is no feedback rewrite.
6. Select a separate production slate using the new tie preferences, retaining accepted score bands and diversity rules.

The default model admits direct, clear contradictions with STRONG or ACCEPTABLE naturalness. Stronger functional irony is a preference, not its own universal admission requirement. Strange but intuitive policies remain allowed. Search is bounded and conservative; counts can fall short when exclusions or diversity exhaust capacity. Ranking accepts at most 30, preserving the existing capacity constraint.

## Data model and interpretation

`app/workflow/affordance_expectations_v1.json` contains object aliases, functional archetypes, primary expected behaviors, natural triggers, goal patterns, material properties, contradiction policies, and 13 comparison archetypes. It contains no finished story templates. New functional examples such as eraser transfer and towel wetness are supported by the gate and fixtures; they do not add new engine families to the accepted generator.

Each policy connects an archetype and observed rule-text response to an expected behavior, contradiction class, relationship strength, optional material connection, irony label, and strange-but-intuitive label. Rule response is derived from text rather than trusting the candidate's supplied engine label or Beat Grammar scores.

Contradiction taxonomy:

| Type | Intended meaning |
|---|---|
| DIRECT_NEGATION | Expected function fails, such as shoe retention. |
| OPPOSITE_BEHAVIOR | Motion or result reverses. |
| OVERCOMPLIANCE | Expected behavior proceeds excessively. |
| REFUSAL | Intended interaction is avoided. |
| PROPERTY_EXAGGERATION | Recognizable material/property behavior becomes absurd. |
| TRANSFER | Expected effect/property appears elsewhere. |
| FUNCTION_REVERSAL | Object produces the inverse of its purpose. |
| SELF_DEFEATING_FUNCTION | Correct use progressively undermines the goal. |

Natural triggers score 100; recognized but unconfigured triggers score 40; unknown triggers score 0. A natural trigger cannot rescue an unsupported functional relationship. Goal match, a configured contradiction, a natural trigger, and absence of a declared object/goal conflict are necessary for DIRECT interference. Unmatched goals are CONTRIVED; supported goals with insufficient trigger support are INDIRECT; absent rules are NONE. Missing essential fields or unsupported rule response is BROKEN.

An identifiable impossible effect without a configured functional relationship receives `ARBITRARY_MAGIC_RELATIONSHIP`. This means unsupported by this model, not proven creatively worthless. Ordinary response text receives TOO_SMALL expectation distance; supported direct contradictions receive CLEAR_CONTRADICTION; other relationships receive ARBITRARY_DISCONNECT.

STRONG naturalness requires direct interference and relationship strength at least 80. Lower supported direct strength can be ACCEPTABLE. Unsupported or indirect relationships are CONTRIVED. The six review labels are INTUITIVE_AND_STRONG, INTUITIVE_BUT_WEAK, STRANGE_BUT_LEGIBLE, CONTRIVED, ARBITRARY, and BROKEN. They are review categories, not additional canonical eligibility outcomes.

### Why this object / swap method

Hold the original violated expected function fixed, substitute each configured comparison archetype, and test whether that archetype supports the same function and response policy. Unbound effects remain portable. Specificity is:

`round(100 × (1 − portable fraction) × min(1, relationship strength / 80))`

Non-direct cases are capped at 45. HIGH is at least 75, MEDIUM at least 50. At least 70 yields OBJECT_SPECIFIC_PREMISE; otherwise GENERIC_ENGINE_APPLICATION. The comparison sample is explicit, finite, and uses configured expected-function vocabulary. It measures functional-family dependence, not unique-object originality or semantic counterfactual proof. Related objects can still share essentially the same idea.

Functional irony comes from a policy linking normal use to failure; non-direct cases cannot retain a HIGH label. Material support is reported independently and is not mandatory. Physical payoff potential is `round(.45 × relationship + .25 × specificity + .20 × trigger + 10 for direct)`, capped at 100 (45 for non-direct). Unsupported effects get 25 with a natural trigger, otherwise 10. This estimates physical consequence opportunity, not humor.

Premise energy uses directness and payoff potential: HIGH at 80+, MEDIUM at 60+, otherwise LOW. It does not estimate retention or inspect eventual audience behavior.

### Opening evidence

Object-name support, use-action support, and recognizable anomaly response are checked independently in the authored opening text. Instant causal legibility is 90 for supported direct openings, 60 for direct premises without an opening, 35 for textual opening support without directness, otherwise 15. Unsupported supplied openings receive CAUSE_NOT_VISIBLE_AT_FRAME_ZERO. Static-frame legibility is separate: 85 for supported direct shape/contact/functional effects, 65 for other supported direct effects, 25 for supported non-direct effects, 15 for unsupported supplied openings, and null without an opening.

These are lexical text-plan estimates. They have false positives and false negatives: e.g. the parser recognizes the rule's “slides ... away” but misses some rendered “slides ... farther” phrasings. Neither value proves a rendered still communicates causality. Opening warnings are not independent hard admission requirements.

## Production selection

Within unchanged anchored 3-point ranking-quality bands, prefer DIRECT interference, instant causal legibility, specificity, irony, physical payoff potential, Beat Grammar quality, production feasibility, then candidate ID. A 5-point diversity margin and accepted behavioral-distinctness checks constrain slate promotion. The accepted raw ranking result and rankingScore values remain unchanged. Tie bands, actual differentiating signals, production order, raw ranks, slate ranks, and diversity adjustments are recorded.

## Evidence and limitations

- `experiment-seed-42-count-20.json`: complete new experiment, configuration, rejected premises, suppressed candidates, accepted validation, tie evidence, 20 candidates, slate, and reports.
- `complete-20-concepts.md`: every full story with expected behavior, rule, opening, five beats, all requested new review fields, scores, and slate ranks.
- `benchmark-abc.json`: A original V2, B accepted Beat Grammar V2, C new gate. A/B naturalness and A beat metrics are newly computed, explicitly non-canonical annotations on copies of frozen runs. Historical scores and selections are preserved.
- `immutable-before.json` / `immutable-after.json`: 160 protected source/evidence hashes.
- `verification.json` and test logs: exact verification results, baseline failure comparison, and artifact hashes.

The new run has 9 eligible, 11 revision-required, and 0 rejected candidates. Selection uses the same eight engine families and retains accepted Beat Grammar prose, including awkward or repeated choreography. The new gate does not certify complete story quality. All selected premises having high specificity/irony is partly a consequence of curated filtering, not independent evidence of quality. Average short-form score (70.15) exceeds B (65.7), but remains below A (73.7). No overall creative superiority is established.

No external AI calls, paid evaluations, or image/video renders are used.

## A/B/C benchmark

| Metric | A: original V2 | B: Beat Grammar V2 | C: new gate |
|---|---:|---:|---:|
| Eligibility yield | 30% | 20% | 45% |
| Average SHORT_FORM_ENGINE | 73.7 | 65.7 | 70.15 |
| Strategy diversity | 50.0 | 100.0 | 100.0 |
| Consequence diversity | 50.0 | 96.25 | 97.5 |
| Arbitrary magic rate | 50% | 65% | 0% |
| Generic engine application rate | 50% | 65% | 0% |
| High object-specificity rate | 50% | 35% | 100% |
| High functional-irony rate | 35% | 20% | 100% |
| Mean physical-payoff potential | 57.85 | 47.2 | 92.6 |
| Production slate size | 3 | 2 | 3 |

## Verification results

34 new tests passed (19 gate unit cases, 15 integration/API/CLI/selection/benchmark/protection cases). The focused accepted-stack suite passed 355 tests with 4 warnings. UI: 102 passed across 5 files. Java dispatch/report projection: 9 passed. Ruff passed. Full offline regression: 2014 passed, 36 failed, 2 skipped, 3030 warnings; all 36 failure IDs match the accepted baseline exactly, with zero added failures. The prior baseline had 1980 passes. QA and video-QC suites are excluded, and no render tests were invoked.

160 protected files retain identical SHA-256 values. Disabled-mode equality and direct reuse of accepted ranker output are tested. See verification.json for commands and baseline-comparison.json for exact failure IDs.
