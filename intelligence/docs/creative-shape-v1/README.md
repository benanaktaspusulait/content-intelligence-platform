# Creative Shape V1

An additive, opt-in curation layer over the accepted V2 + Beat Grammar V2 + Premise Naturalness V1 stack. It constructs no new stories, rewrites no prose, and changes no canonical score. It detects repetition in the complete planned sequence, beyond object nouns and engine labels, then exposes the deterministic grammar's quality/diversity capacity.

## Configuration

```json
{
  "generatorVersion": "v2",
  "beatGrammarVersion": "v2",
  "premiseNaturalnessGateVersion": "v1",
  "creativeShapeVersion": "v1",
  "seed": 42,
  "count": 20,
  "premisePoolSize": 480,
  "minimumStoryShapeDistance": 0.22,
  "minimumShapeShortFormScore": 85,
  "minimumShapeRankingScore": 75,
  "allowHighHistoricalTerritoryRisk": false,
  "rank": true
}
```

API: existing ML `/api/v1/workflow/concepts/generate`, through existing Java proxy `/api/v1/intelligence/workflow/concepts/generate`. CLI:

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v2 --beat-grammar-version v2 --premise-naturalness-gate-version v1 --creative-shape-version v1 --seed 42 --count 20 --rank --text-report
```

The CLI also exposes `--minimum-story-shape-distance`. Other selection parameters are available through explicit API configuration and recorded with every run. Invalid stacks and external-provider fields are rejected. When disabled, the dispatcher removes all five new configuration fields and delegates to the accepted Naturalness dispatcher; exact legacy V1/V2/Beat Grammar/Naturalness dispatch equality is tested.

## Architecture and selection

1. Reuse the accepted naturalness search and recover **all 480 realized candidates**, including its suppressed candidates. Earlier affordance/naturalness rejections remain recorded separately.
2. Annotate copies with story shape, planned-scene historical territory, nearest batch shape, and non-canonical template risk.
3. Apply the **unchanged canonical validator** once to each pool candidate. Quality admission requires accepted eligibility, short-form score at least 85, ranking score at least 75, acceptable/strong Beat Grammar, and admitted naturalness. HIGH historical-territory risk is separately withheld by this new configurable curation policy; it is not a canonical rejection or altered historical duplicate metric.
4. Greedily select from the quality-controlled pool using minimum distance to already selected shapes, payoff concentration, historical-territory distance, accepted short-form/ranking scores, physical-payoff potential, and seeded deterministic fallback. Distance must meet 0.22 for every selected pair. No low-quality candidate enters merely because it is unusual. There is no rewrite, iterative tuning, or final-score feedback loop.
5. Stop instead of padding. Seed 42 returns **9 of 20**, from 91 quality-admitted pool candidates: `DIVERSITY_CAPACITY_REACHED`. This is a bounded greedy capacity result, not proof of a global maximum or a universal creative ceiling.
6. Rank the selected candidates using the unchanged accepted ranker and retain its result verbatim. Apply a separate shape-aware production selector. Save all 471 suppressed realized candidates with full story, exact quality evidence, and reasons, plus a compact suppression index.

Accepted validators are applied twice to final candidates: once during pool admission and once by the final ranker. Tests prove final accepted output equals a direct ranker invocation. Scores are never written back or adjusted.

## Story-shape fingerprint

`creative_shape.annotate` uses actual structured state fields, not the advertised progression-shape or engine name. Character names, object nouns, titles, engine labels, and exact timestamps are absent from fingerprint dimensions:

- openingState
- goalStateSequence / successDistanceSequence
- controlStateSequence
- strategyRoleSequence
- bodyStateSequence
- environmentUsageSequence
- falseSuccessPosition
- payoffMechanism
- finalCharacterObjectRelation
- loopMechanism
- temporalShape

Goal states include BLOCKED, FARTHER, PARTIAL_PROGRESS, NEAR_SUCCESS, APPARENT_SUCCESS, NEW_PROBLEM, RESET, and supported explicit states. Controls map plan relationships into OBJECT_RESISTS, CONTESTED, OBJECT_DOMINATES, FALSE_CONTROL, CHARACTER_REGAINS_CONTROL, ROLE_REVERSED, or UNKNOWN. Strategy roles coarsen action IDs into ESTABLISH, ADAPT_CONTACT, ADAPT_APPROACH, FORCE, MODULATE_INPUT, CONSTRAIN, GUIDE_WITH_ENVIRONMENT, PAUSE_TRIGGER, MOVE_SELF, RELEASE_CONTACT, TIME_INTERACTION, and TEST_NORMAL_USE.

FALSE_SUCCESS requires the plan's false-success body/relationship evidence; stopping the trigger alone is not equated with success. Concrete trapped-body/contact state overrides generic final control/reset labels. This identifies an adhesion-to-cheek ending as CONTACT_ENTANGLEMENT rather than inventing property transfer. Temporal events (problem, tactic change, control shift, false success, payoff) use relative early/middle/late phases; duration changes do not manufacture novelty.

The full shape hash covers all dimensions. A macro hash omits body/environment detail while retaining goal, control, strategy roles, false-success position, payoff, final relation, and loop. These are deterministic abstractions, not semantic equivalence proofs.

## Distance formula

For scalar dimensions, difference is 0 for equality and 1 otherwise. For sequences, use positional mismatch count divided by the larger length; missing positions count as mismatches, two empty lists have distance 0. Weighted sum:

| Dimension | Weight |
|---|---:|
| Goal-state sequence | .16 |
| Control-state sequence | .16 |
| Strategy-role sequence | .12 |
| Body-state sequence | .08 |
| Environment-usage sequence | .06 |
| Payoff mechanism | .14 |
| Final relationship | .12 |
| False-success position | .06 |
| Loop mechanism | .04 |
| Temporal shape | .06 |

Weights sum to 1. The result is symmetric and bounded [0,1]. UNKNOWN is retained as a category; sparse legacy text annotations can underrepresent differences and are explicitly marked. Distance is independent of input order, character/object/engine renaming when the state plan is unchanged, and exact duration. Engine identity is not itself a distance axis. Two RESET_TO_START concepts can differ materially when their state arcs differ.

## Payoff and final relationships

The documented payoff vocabulary includes RESET, OPENING_RECREATED, FALSE_SUCCESS_COLLAPSE, ROLE_REVERSAL, CONTROL_REVERSAL, GOAL_INVERSION, OBJECT_FUNCTION_REVERSAL, PROPERTY_TRANSFER, ENVIRONMENTAL_TAKEOVER, CHARACTER_TRANSFORMATION, OBJECT_TRANSFORMATION, HIDDEN_CAUSE_REVEAL, SELF_CAUSED_PROBLEM, CHAIN_REACTION, LOGICAL_EXTREME, SCALE_EXTREME, POSITION_EXTREME, ABSURD_SUCCESS, PARTIAL_SUCCESS_NEW_PROBLEM, CONTACT_ENTANGLEMENT, and UNKNOWN.

Current structured extraction supports the families evidenced by this grammar: opening recreation, false-success collapse, control reversal, contact entanglement, and terminal environmental takeover. The broader taxonomy is **not** a claim that the generator can produce all those endings. Unsupported families are never assigned merely to improve distribution. No new physical rules or surprise events are introduced.

Final relationships currently distinguish OPENING_STATE_RECREATED, OBJECT_CONTROLS_CHARACTER, CHARACTER_ATTACHED_TO_OBJECT, ENVIRONMENT_BECOMES_PROBLEM, and UNKNOWN. Raw body and environment sequences remain available for finer review.

Batch diagnostics report payoff distribution, dominant payoff warning (>50%), payoff concentration, strategy-sequence concentration/warning (>35%), temporary trigger-stop rate, Beat-4 false-success rate, reset rate, final relationships, and mean/minimum shape distance. Reset endings receive no global quality penalty. `TEMPLATE_SHAPE_RISK` records repeated strategy sequences, false-success positions, payoffs, final relationships, and temporal shapes. Risk is HIGH with at least three repeated dimensions or a nearest shape below .20; MEDIUM with any repeated dimension; otherwise LOW. Peer counts and denominators are explicit; these warnings can remain HIGH even after distance filtering.

## Historical creative territory

`creative_territories_v1.json` adds structural annotations of the two existing frozen prompts, with their original paths and hashes. Those prompts were read for this task; no new video, winner-performance evidence, or pixel comparison was obtained.

Candidate scene signatures use configured functional object archetype, everyday-goal role, opening obstruction relation, impossible-response transformation, final relation, and silhouette topology. Inverted seating geometry is derived from SEATING + inversion, irrespective of candidate title or supplied engine label. This makes a chair flipping during sitting HIGH territory risk against Upside-Down Chair despite a different engine signature.

Similarity weights: object category .20, goal .20, opening relation .10, dominant transformation .25, final relation .10, silhouette topology .15. HIGH is at least .75, MEDIUM at least .45, otherwise LOW. Matching axes, source hashes, and closest reference are returned. LOW means low match in this tiny corpus, not verified originality. Existing engine/historical duplicate metrics remain untouched.

## Production slate and frontier

Quality prerequisites apply first. Within anchored 3-point quality bands, prefer instant causal legibility, accepted payoff strength, premise naturalness, minimum shape distance to already selected slate members, historical-territory distance, final-relationship novelty, payoff-family novelty, feasibility, planned visual-silhouette novelty, object/goal-experience novelty, then stable ID. The latter two are additional diversity fallbacks before ID; they do not replace the required quality/causality/shape ordering. Unknown silhouette support earns no novelty credit. If no shape-distinct candidate is available in the band, the existing 5-point diversity margin bounds promotion. No engine-label exclusion is applied. Candidates with the same reset engine may coexist if their full shapes differ.

Every production decision records quality anchor/gap, chosen signals, and alternatives. Raw rank and rankingScore are preserved. A Pareto-like review set separately exposes accepted ranking quality versus minimum shape distance to the final selected reference set, excluding self. Dominated points are not hidden. This is reference-set dependent and does not claim a globally optimal frontier.

## Evidence / manual review

- `experiment-seed-42-count-20.json`: final candidates, full suppressed candidates, canonical validations, configuration, pool admission, frontier, raw ranking, and slate.
- `complete-final-concepts.md`: every final candidate's full opening/five beats, premise, fingerprint, goal/control arc, payoff, final relation, closest batch/historical evidence, risk, scores, and ranks.
- `suppression-index.json`: every suppressed candidate and exact reason; full story remains in experiment JSON.
- `benchmark-abcd.json`: original V2 / Beat Grammar / Naturalness / Creative Shape. Old runs are read only; new annotations are explicitly retrospective.
- `immutable-before.json`, `immutable-after.json`, `verification.json`: protected evidence/source hashes and exact verification.

**Generator-controlled diagnostic improvements are expected after filtering and are not independent evidence of creative quality.** D also filters on accepted quality while A/B/C retain failures, so yield and mean-score comparisons are selection-biased. Counts differ. The batch still shares choreography and three final-relation categories; the shape model can miss narrative similarities. Human inspection remains pending. Creative success is not claimed.

No external AI calls, paid evaluations, or media renders.

## Four-stage benchmark

| Metric | A | B | C | D |
|---|---:|---:|---:|---:|
| Final count | 20 | 20 | 20 | 9 |
| Eligibility yield | 0.3 | 0.2 | 0.45 | 1 |
| Average short-form | 73.7 | 65.7 | 70.15 | 97.6667 |
| Mean pairwise creative distance | 0.839 | 0.796211 | 0.762368 | 0.675 |
| Mean story-shape distance | 0.250596 | 0.474293 | 0.464769 | 0.557333 |
| Strategy-sequence concentration | 0.55 | 0.2 | 0.2 | 0.333333 |
| False success Beat 4 | 0 | 0.55 | 0.6 | 0.444444 |
| Reset payoff rate | 0.15 | 0.25 | 0.2 | 0.444444 |
| Dominant payoff concentration | 0.65 | 0.6 | 0.6 | 0.333333 |
| Historical territory HIGH rate | 0.05 | 0 | 0.05 | 0 |

Rates use [0,1]. A = original V2; B = Beat Grammar; C = Naturalness; D = Creative Shape. D returns fewer candidates and filters accepted quality before selection. Some diagnostics worsen (engine-based creative distance, sequence concentration versus C, reset rate); this is a tradeoff, not an all-metric improvement. A false-success estimate is not comparable coverage: legacy text annotations do not expose the same structured evidence as B/C/D.

| Slate diagnostic | A | B | C | D |
|---|---:|---:|---:|---:|
| Size | 3 | 2 | 3 | 3 |
| Mean shape distance | 0.419524 | 0.561091 | 0.610424 | 0.645535 |
| Mean creative distance | 0.97 | 0.94 | 0.79 | 0.66 |
| Dominant payoff concentration | 0.333333 | 0.5 | 0.333333 | 0.333333 |
| HIGH territory collision rate | 0.333333 | 0 | 0.333333 | 0 |

## Reproducibility detail

Enabled requests normalize numeric defaults, so explicit API/CLI duration 15 and omitted duration produce the same serialized 15.0 representation. Disabled dispatch preserves unset fields when delegating, retaining the accepted stack’s default behavior. Cross-process CLI output under PYTHONHASHSEED=17 is byte-identical to the saved experiment; stories and scores were unchanged by numeric normalization. See reproducibility.json for hashes.

## Final verification

36 new tests: 18 shape/payoff/control/goal/territory/selection cases and 18 generation/API/CLI/reproducibility/benchmark/protection cases. Final focused suite: 391 passed, 4 warnings. UI: 104 passed in 5 files. Java dispatch/report projection: 9 passed. Ruff passed. Full offline regression: 2050 passed, 36 failed, 2 skipped, 3030 warnings in 133.51 seconds. All 36 failure IDs exactly match the accepted Naturalness baseline; zero new failures. Previous baseline: 2014 passed, 36 failed, 2 skipped. QA and video-QC suites excluded; no render suites invoked.

184 protected sources, fixtures and prior experiment/evidence files retain identical SHA-256 values. Legacy disabled paths have byte-serialization equality tests. Final enabled API/CLI parity includes byte equality, and a separate CLI process with PYTHONHASHSEED=17 matches the saved experiment byte for byte. Exact commands, hashes and results are in verification.json.
