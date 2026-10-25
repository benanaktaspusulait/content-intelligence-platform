# Beat Grammar V2: opt-in structured strategy and consequence plans

This additive experiment keeps accepted V1/V2, STORY_PREMISE_ENGINE, SHORT_FORM_ENGINE, CPQ, ranking source/semantics and previous evidence unchanged. It does not establish creative success: accepted eligibility falls from 6/20 to 4/20, average accepted short-form score falls, and the production slate has only two candidates under the existing quality margins and new behavioral-distance guard. Structured diagnostic improvements must be reviewed against the actual stories.

[All 20 complete concepts](complete-20-concepts.md) · [Full experiment JSON](experiment-seed-42-count-20.json) · [Selected production slate](top-slate.txt) · [Old/new comparison](old-v2-vs-beat-grammar.json) · [Seed/ranker proof](reuse-and-seed-proof.json) · [Verification](verification.json).

No external providers, paid evaluations, media/PDF renders, prompt generation, production dispatch or adaptive learning. Scores below are text/plan hypotheses, never measured retention.

## Architecture and version boundary

`beat_generation.GenerationRequest` extends the existing request only with optional `beatGrammarVersion`. With it absent/null, dispatch strips that option and calls the unchanged old V1/V2 entry point. Exact equality is tested. Enabling it requires explicit generator V2. Existing API routes and backend registry forwarding are reused; the backend code is unchanged. UI defaults to the accepted baseline with Beat Grammar off, exposing an opt-in selector for generator V2.

Enabled flow:

```text
existing compatible goal/object/engine primitives
→ versioned progression shape and compatible strategies
→ structured state/attempt plan
→ continuity, rule, strategy and shape validation
→ human-readable prose
→ structural/choreography suppression and diversity selection
→ unchanged ranking_input + rank_concepts once
→ separate Beat Grammar production selection
```

The new bounded search enumerates primitive compositions using existing compatibility functions without calling the old prose renderer. Cast is resolved from the same repository/backend canonical data and assigned after the mechanics. Strategy and consequence evidence is created before prose. Neither previous generator source nor its catalog, distance code or production-selection module is edited. New orchestration adapts the new plans into the accepted ranker; it does not duplicate canonical grading or ranking formulas.

## Beat data model and taxonomies

Each structured beat records beatNumber, beatRole, characterStrategy, trigger, impossibleRule, objectResponse, characterConsequence, bodyStateBefore/After, objectStateBefore/After, spatialChange, goalProgress, newInformation, contactPattern, consequenceType, relationshipAfter, payoffContribution and payoffStateChange. Object states contain a transition kind and application count. Non-trigger beats must retain the prior object state exactly. Body/object state continuity is checked. A changed dominant rule is BROKEN.

Roles include hook/problem, first obvious fix, tactic change, environmental/body leverage, constraint escalation, control reversal, false success, payoff and loop reset. Three occurrences of one role are flagged. Plans use five roles without requiring every role.

The data-driven strategy taxonomy includes direct use, two-hand/increased force, angle/side/below approaches, body brace/load, environment anchor/surface guidance, path blocking, trapping, moving self rather than object, reduced force, timing, contact switching/release, temporarily stopping a trigger and normal use. Tiny precision handoff exists only as a risk-screen/compatibility option, not a default generation strategy.

Force-only methods share the **DIRECT_FORCE** family. Angle-only variants share **ANGLE_CHANGE**. Renaming one-hand to two-hand, or one side to another, cannot create a fully new strategy. The strategy text is an action primitive, not a finished story.

Consequence categories include object movement/growth/shrink/rotation/adhesion, character movement/drag/lift/balance loss, space reduction, path blocking, trapped body parts, object control over the character, blocked environment, farther goal, apparent goal, reset and opening reinterpretation. One transition can have different body/spatial consequences under a changed contact or anchor. This is planned causal evidence, not a physics simulation or proof of semantic truth.

Progression shapes: CONTROL_TRANSFER, SPACE_COLLAPSE, FALSE_MASTERY, BODY_ESCALATION, GOAL_DISTANCE_REVERSAL, ENVIRONMENTAL_ESCALATION. Space-collapse excludes shrinking and other incompatible transitions. Environment escalation has its own supported transition list. Beat 4 varies between body-route discovery, spatial constraint and false success; it is not a mandatory under-object move. Some profiles still rely on stopping the trigger, which remains a visible limitation.

## Compatibility and feasibility

Strategies require object properties such as large, graspable, usable surface, load-bearing, elevated or adhesion contact. Thus environment anchoring is rejected for a small eraser, body load for a tiny pencil, and moving below a ground-level shoe. The reference shoe can use a wall/floor boundary and body load. Fixed surfaces are declared as scene context, not introduced moving props. Shape/engine compatibility is validated before realization. Invalid compositions and suppressed plans are retained separately.

Production complexity is an independent plan screen. Intricate finger choreography, rapid handoff, multiple contact points, body/object entanglement and precise contact release produce explicit flags. Its score is 100 minus 15 per distinct flag, floored at zero. This is not a monetary or rendered feasibility estimate and never changes canonical rankingScore. Broad strategies without flags can still be difficult to render; the screen can miss physical or semantic problems.

## Attempt similarity and progression diagnostics

Attempt signatures preserve strategy family, trigger, contact, body states, object state kinds, spatial change, consequence, information and goal progress. Similarity compares eight categorical axes: strategy family, trigger, contact pattern, final body state, final object-state kind, consequence, goal-distance change and final relationship. All eight equal means IDENTICAL_ATTEMPT; similarity ≥0.71 means NEAR_DUPLICATE_ATTEMPT; otherwise DISTINCT_ATTEMPT. Prose wording and numeric magnitude/application count are excluded. Different body consequences can therefore count as progression under the same trigger.

Strategy/consequence scores are `100 * min(unique count, 4) / 4`; fewer than three families/states gets a low-diversity flag. Body progression is the percentage of beats changing body-state category. Spatial progression is the percentage of seven tracked spatial axes with a planned non-unchanged change: goal/object distance, vertical/horizontal movement, free space, object-relative position and environment use.

Each beat carries information fact identifiers. Repeated facts are not new information; no unseen fact gives NON_PROGRESSIVE_BEAT. Information score is the fraction of beats with an unseen fact; below 80 gives LOW_INFORMATION_GAIN. These facts are authored structured hypotheses, not facts verified from rendered frames.

Payoff distance compares Beat 5 separately with Beats 3 and 4 on body state, consequence, goal progress and relationship. It reports the smaller changed-axis fraction. Magnitude alone contributes nothing. Below 0.5 gives LOW_PAYOFF_DISTANCE as a soft flag. The final `payoffStateChange` is exposed separately.

BEAT_GRAMMAR_QUALITY is BROKEN for invalid state/schema/compatibility or changing rule; MECHANICAL for fewer than three strategy families/consequences or information below 60; STRONG requires non-mechanical structure, body progression ≥60, payoff distance ≥0.5, information ≥80 and no near-duplicate pairs; otherwise ACCEPTABLE. These are explicitly **non-canonical generation review labels**, not audience predictions or substitutes for SHORT_FORM_ENGINE.

## Integration and production selection

Accepted HIGH_ACTIVITY_LOW_PROGRESS/IDENTICAL_ATTEMPTS findings remain unchanged. Each run stores their original codes beside structured supporting/contrasting flags under `existingProgressFindingSupport`; it never rewrites them or asserts agreement when the two layers differ.

Within the existing anchored three-point close-quality band, production ordering preserves payoff, progress, frame-zero and duplicate-risk signals first, then prefers strategy diversity, consequence diversity, payoff distance and body progression before cosmetic batch/visual novelty and final ID. Canonical rankingScore and raw ranks remain the original ranker output. The existing five-point quality/diversity margin remains. Selection additionally requires materially different behavior: a different progression shape or payoff-state change. Different cosmetic payoff labels cannot make the same choreography distinct. When no comparable third candidate qualifies, the slate underfills explicitly rather than manufacturing a winner.

## Reference fixtures

The shoe golden is a test-only reference: failed pull/wear; wall anchor; body leverage causing displacement; temporary success while preventing the trigger; first step visibly pulling against the shoe, which resets and leaves the character in a sock. It is not read by the production generator. Generated shoe plans can use other compatible profiles.

The negative fixture repeats pull/two hands/harder, moves below the object and repeats the effect. It receives LOW_STRATEGY_DIVERSITY, LOW_CONSEQUENCE_DIVERSITY, NEAR_DUPLICATE_ATTEMPTS, LOW_INFORMATION_GAIN, NON_PROGRESSIVE_BEAT and LOW_PAYOFF_DISTANCE. Wording changes and bigger magnitude cannot evade it.

## Old V2 versus new seed-42 experiment

Both request 20 concepts with seed 42. Old V2 is read from its saved evidence, never overwritten. Old beat diagnostics are conservative text-to-taxonomy annotations; they have different coverage from new structured-first evidence and are not changes to old scores.

| Metric | Old V2 | V2 + Beat Grammar |
|---|---:|---:|
| Average strategy diversity | 50.0 | 100.0 |
| Average consequence diversity | 50.0 | 96.25 |
| Average body progression | 69.0 | 81.0 |
| Near-duplicate attempt rate | 0.595 | 0.025 |
| Candidate rate using under-object move | 1.0 | 0.0 |
| Candidate rate using two-hand force | 0.85 | 0.0 |
| Low payoff-distance rate | 0.55 | 0.0 |
| Eligibility yield | 0.3 | 0.2 |
| Average accepted SHORT_FORM_ENGINE score | 73.7 | 65.7 |
| Accepted production-risk flag rate | 0.0 | 0.0 |
| New plan-complexity risk flag rate | 1.0 | 0.0 |

The large diagnostic changes partly reflect explicit structured metadata and the legacy annotation method. In particular, the new plan-risk taxonomy flags old under-object behavior, while the accepted production-risk screen remains zero for both runs. Do not interpret this as measured improvement in renderability. Overall accepted eligibility and average short-form score decline. This implementation removes the identified default force/under-object ladder and exposes richer plans, but does not demonstrate better creative outcomes.

The new batch uses six progression shapes. All raw attempts, rejection reasons, structured evidence, accepted warnings/penalties and scores are in the full JSON. The human report contains all twenty stories with frame zero, five strategies/consequences, information gain, payoff change, four requested diagnostics, label, short-form/ranking score and slate rank.

## Production slate

- 1. **Shoe / Reset To Start / Goal Distance Reversal** — accepted ranking 97.6, short form 99, raw rank 2.
- 2. **Lid / Reversal / Body Escalation** — accepted ranking 97.6, short form 99, raw rank 1.

There is no third selected candidate under the retained quality/distance limits. Top-slate distance metrics therefore cover one pair, not three. The report does not claim a complete Top 3 or a successful creative-quality improvement.

## API, CLI, UI

Existing routes remain unchanged. Explicit opt-in:

```json
{"generatorVersion":"v2","beatGrammarVersion":"v2","seed":42,"count":20,"duration":15,"rank":true}
```

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v2 --beat-grammar-version v2 --seed 42 --count 20 --rank
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v2 --beat-grammar-version v2 --seed 42 --count 20 --rank --text-report
```

Without `--beat-grammar-version`, existing behavior is unchanged. V1 with Beat Grammar enabled is rejected rather than silently changed. Run evidence records both versions, seed, configuration and all strategy/consequence/shape distributions. The existing UI adds an optional selector, five per-candidate metrics and beat expansion with strategy, consequence and information. Changing version/config cancels stale requests.

## Verification

Final verification: **35 new tests passed; 321 focused tests passed (4 warnings); 100 UI tests passed across five files; 9 backend tests passed**. Full permitted offline regression: **1,980 passed, 36 failed, 2 skipped, 3,030 warnings**. All 36 failure IDs exactly match the accepted baseline; the full suite is not green.

See [verification.json](verification.json) for exact commands, final test counts, known baseline failures and file inventory. Tests cover golden/negative references, grouping cosmetic strategy changes, attempt signatures, body/spatial progression, information, payoff distance, compatibility, production risk, concentrations, deterministic generation, disabled V1/V2 equality, API/CLI/UI and accepted ranking reuse.

The protected-file manifest includes previous V1/V2 evidence, generator/catalog/distance/selection source, accepted engines and historical evidence: **138 files have identical before/after SHA-256 values**. A direct accepted ranker call equals the new run's stored rankingResult. Same-seed full-run hashes match. No production data was written. The offline runner blocks network/provider credentials and isolates data; QA/render suites are excluded consistently with prior verification. Backend report tests exercise pure projection/dispatch, not PDF generation.

ENGINE DIVERSITY asks whether concepts use different causal mechanics. BEAT DIVERSITY asks whether responses materially change. CONSEQUENCE DIVERSITY asks whether those responses produce different visible states. All matter; none alone guarantees retention.

## Files changed

- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/beat_grammar.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/beat_grammar_v2.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/beat_generation.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/beat_grammar_benchmark.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/api.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/scripts/generate-short-concepts.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_beat_grammar.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_beat_generation.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_beat_generation_api.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/fixtures/beat_grammar_v2_reference.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/fixtures/beat_generation_v2_golden.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/frontend/src/app/pages/concept-ranking.page.ts`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/frontend/src/app/pages/concept-generation.page.spec.ts`

This new evidence directory is also added. No commit, deployment or publication. Preexisting unrelated workspace changes are preserved.
