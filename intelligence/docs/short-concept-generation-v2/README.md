# Short concept generation V2: compatible causal grammar

V2 is implemented as a local deterministic composition/search workflow. V1 remains callable and byte-stable for the same configuration; SHORT_FORM_ENGINE, STORY_PREMISE_ENGINE, CPQ, accepted ranking source/semantics, historical projections and accepted evidence remain unchanged.

V2 is the default choice in the generator UI after verification. Existing API/CLI requests that omit the version continue to select V1 for backward compatibility. Explicit `v1` / `v2` and full version identifiers are accepted by the API. No model calls, paid evaluations, media or PDF renders, prompts, production dispatch, adaptive weight updates, deployment or publication occurred.

## Review the actual output

- [All 20 complete concepts](complete-20-concepts.md): title, character, environment, goal, object, engine, trigger, frame zero, all five timed beats, final payoff, short-form and ranking scores, creative-distance summary, editorial production result and every accepted failure reason.
- [Human-readable Top 3](top3-ideas.txt): production-readable summaries, risks and closest historical engine; these are not video prompts.
- [Complete machine run](example-run.json), [configuration](example-config.json), [compact report](example-report.txt).
- [V1/V2 benchmark](benchmark.json), [seed proof](seed-evidence.json), [ranking reuse proof](ranking-reuse-evidence.json), [verification](verification.json).

These are proposed story scenes. None is observed footage or measured viewer retention. `SELECTED_FOR_SLATE` is an editorial recommendation; actual production is **NOT RENDERED**.

## Architecture and compositional model

`short_concept_generation_v2.GenerationRequest` adds version selection and bounded `internalPoolSize` to existing constraints. Dispatch delegates V1 requests directly into the unchanged V1 function, stripping only V2 configuration. V2 `generate_v2` uses `search`, `sanity_errors` and `compose`; normalized candidate fields feed the unchanged `ranking_input` adapter and accepted `rank_concepts` function once. That function continues to own hard gates, SHORT_FORM_ENGINE, CPQ previews, canonical ranking scores and its original slate. A separate `select_production` adds V2 editorial selection. `rankingResult` retains the exact original result, including raw order, raw slate and raw first candidate.

The JSON grammar stores goal taxonomy, object affordances, independent engines, visible triggers, escalation shapes, response strategies, compatible payoffs and goal-linked environments. Engines contain transition identifiers, compatible interaction/trigger lists, escalation/payoff permissions and risk hints; no titles, openings or finished beat sequences. The renderer realizes an engine's single transition across stages with different strategies, a pause/information beat and a causally linked ending. This is a finite grammar and a small realization vocabulary, not unlimited semantic invention.

The present grammar has 15 goals, 23 object entries, 8 independent engines, six visible trigger types, seven escalation topologies and six authored payoff topologies. Opening-recreated and self-created-loop remain separately authored endings, but are conservatively grouped as **RECURRENCE** for distance/novelty/concentration; labels alone cannot create payoff novelty.

Goal families: BODY_SELF_CARE, FOOD, HOUSEHOLD, SCHOOL_CRAFT, DRESSING and CONCRETE_PLAY. Every play goal has a physical action. Familiar environments follow the goal: bedroom, bathroom, kitchen, dining area, playroom, garden, classroom-like craft area, entryway and living room.

| Engine | Visible state transition | Valid triggers |
|---|---|---|
| PROGRESSIVE_GROWTH | SCALE_UP | LIFT, PRESSURE, PULL, RELEASE, STROKE, WEIGHT_APPLIED |
| PROGRESSIVE_SHRINK | SCALE_DOWN | LIFT, PRESSURE, PULL, RELEASE, STROKE, WEIGHT_APPLIED |
| ADHESION | CONTACT_RETAINS | LIFT, PULL, PRESSURE, STROKE |
| RESET_TO_START | RETURN_ORIGIN | PULL, RELEASE, LIFT |
| REVERSAL | INVERT_ORIENTATION | PRESSURE, WEIGHT_APPLIED, PULL |
| ELASTIC_EXTENSION | EXTEND_CONTACT | PULL, STROKE |
| ESCAPING_TARGET | MOVE_AWAY | PRESSURE, WEIGHT_APPLIED, LIFT |
| WEIGHT_SHIFT | FLOAT_AWAY | LIFT, PRESSURE, WEIGHT_APPLIED |

## Compatibility and bounded search

1. Enumerate only configured goal/object bindings. Respect required affordances; apply engine/object/category exclusions before composition.
2. Check valid engine interaction and visible trigger, escalation and payoff compatibility, declared transition and goal-linked environment. New-object payoffs and unknown primitives are rejected explicitly. For example, a cup/brush-hair mismatch is invalid, and inversion is excluded from rubbing/washing: flipping a symmetric soap surface does not itself obstruct washing hands.
3. Retain every incompatible plan with a reason. Sort compatible primitive tuples by seed-dependent canonical SHA-256. Realize at most the configured pool, default 240 (allowed 20–600).
4. Assign an id/name from the canonical cast after the mechanics are complete. Cast and catalog input ordering are canonicalized. The application backend continues to supply the active registry; direct CLI/ML uses the explicitly labelled repository seed snapshot or supplied snapshot.
5. Suppress unchanged V1 structural-core duplicates, then planned silhouettes with at least 7/8 matching axes. Preserve full suppressed concepts, reasons and duplicate links.
6. Greedily select output concepts using low cumulative concentration across engine, goal, object category, escalation, payoff, environment and character; then larger minimum distance; then seed hash. No equal quotas. Pairwise admission requires creative distance at least 0.28. This selection occurs before all quality scoring and does not tune itself from score results.
7. Stop at the requested count, exhausted distinct pool, or the unchanged 30-candidate ranking boundary. `DIVERSITY_CAPACITY_REACHED` means capacity of this bounded search, not proof that all possible ideas are exhausted. `RANKING_CAPACITY_REACHED` separately identifies the evaluator boundary. No cosmetic duplicates are appended to fill a request for 100.
8. Normalize and invoke accepted ranking once. Retain each output candidate's disposition, short-form/CPQ evidence, scores and reasons. Keep internal composition rejections and suppressions separate from evaluated output failures.

Checks establish typed consistency, not semantic truth. All transitions, information beats and payoffs still require human inspection. Repetitive phrasing and coarse blocking remain real limitations. The renderer's underneath approach is a planned broad blocking hypothesis; production legibility has not been visually verified.

## Creative distance and planned silhouette

The visual fingerprint records characterPoseFamily, objectRelativePosition, dominantDirection, objectScaleRelation, characterObjectContact, finalFrameComposition, movementAxis and environmentInteraction. It is planned staging metadata, never extracted pixels. Different engines can share a horizontal pull/extension silhouette; a changed title is irrelevant.

For comparable candidates:

```text
D = 0.20 * engine mismatch
  + 0.08 * trigger mismatch
  + 0.10 * goal-family mismatch
  + 0.10 * object-category mismatch
  + 0.14 * escalation-topology mismatch
  + 0.14 * canonical-payoff mismatch
  + 0.24 * visual-axis mismatch fraction
```

Unknown categorical axes are excluded. Visual distance is computed only across supported axes. Available weights are normalized to sum to one, and `supportedWeight` is exposed; no comparable axes gives null distance. Reported silhouette similarity is matching supported visual axes / 8, with supported-axis count reported separately. Zero shared metadata is not a similarity claim. Complete V2 candidates support all weights. The function is symmetric and does not depend on candidate order; self-distance is zero when supported.

`engineSimilarity` separately reports matching engine/trigger/escalation axes divided by three. Object-swapped lift/growth spoon and brush remain engine-close. Shrinking after strategy change differs materially. This distance is structured creative distance, not semantic similarity or video quality.

Per-candidate current-batch novelty exposes engineNovelty, goalNovelty, objectNovelty, escalationNovelty, payoffNovelty and visualSilhouetteNovelty. Engine/visual novelty use one minus the maximum corresponding peer similarity; the categorical axes disclose whether a peer shares that dimension. They remain separate. A transparent non-visual arithmetic mean is used only at the production tie stage, not as a canonical creative score.

Historical novelty reuses the accepted two-reference comparison. High risk maps to an engine similarity proxy of 1.0, supported partial similarities to 0.5 and an evaluated no-match to 0.0. Other unavailable axes stay null. There is no comparable V2 staging taxonomy or verified winner-performance label in that corpus, so historical silhouette rate is null and winner vectors are explicitly unavailable. This avoids inventing historical originality or successful outcomes. `NO_MATCH` means only no supported match in this limited corpus.

## Additive production tie-breaking and Top 3

Canonical `rankingScore`, eligible ordering and accepted ranking policy are untouched. V2 creates separate anchored three-point quality bands and sorts within them by:

1. Higher payoff.
2. Higher progress density.
3. Higher frame-zero legibility.
4. Lower accepted duplicate risk.
5. Higher transparent batch novelty.
6. Higher planned visual novelty.
7. Fewer accepted production-risk flags.
8. Higher accepted rewatch hypothesis.
9. Candidate ID, only after the preceding signals tie.

Anchored bands prevent comparator cycles or chains of small promotions crossing a large quality gap. The evidence records tie values and the first differing signal. Production candidates then require **different engine or trigger AND different canonical payoff or escalation**, distance at least 0.32, and no same-object-category pair with silhouette similarity at least 0.625. Diversity promotion is limited to five quality points relative to the current leading available candidate. When no sufficiently distinct comparable candidate exists, the slate underfills instead of inventing diversity.

Each selected row records `rawRank`, `productionSlateRank`, `diversityAdjustmentReason`, scores and tie signals. A synthetic 100/100/98/98/97 chair/chair/lid/brush/shoe fixture selects chair/lid/brush. It does not ban chairs; a genuinely different chair can still qualify. Separate tests show creative signals beating an adverse ID and ID appearing only when signals are exhausted.

## Final seed-42 run

Requested 20; internal realized pool 240; compatible primitive tuples 766; incompatible plans retained 522. Pool suppression: 15 structural, 168 silhouette, 37 diversity/search. Final output: **20 concepts, 6 eligible, 13 revision required, 1 rejected**, no structural duplicates in the selected output.

Internal pool duplicate count/rate and selected-output duplicate count/rate have different denominators. `generationSummary.rawCandidateCount` describes output concepts before validation, while `generationEvidence.internalPoolSize` describes realized search attempts. Sanity rejections are incompatible primitive tuples before realization. Every category is separately retained and accounted for.

| Slate rank | Concept | Raw rank | Existing ranking | Existing short form |
|---|---|---:|---:|---:|
| 1 | Shoe / Reset To Start / Opening Recreated | 3 | 97.6 | 100 |
| 2 | Brush / Progressive Growth / Goal Inversion | 2 | 97.6 | 100 |
| 3 | Chair / Reversal / Role Reversal | 1 | 97.6 | 100 |

First recommendation: **Shoe / Reset To Start / Opening Recreated**. The accepted raw #1 is Chair / Reversal / Role Reversal. The V2 choice follows the exposed creative tie signals; it does not revise either score. Exact decision evidence: `{"candidateId": "v2-69e8e1f5cbc4a53d", "comparedWith": "v2-5a0870794e171ea8", "firstDifferentiatingSignal": "visualNovelty", "values": [0.5, 0.375]}`.

No recommendation is a promise of audience performance or a render authorization. Read all twenty complete ideas before judging the generator's creative quality.

## V1 versus V2 benchmark: same seed 42, requested 20

| Diagnostic | V1 | V2 |
|---|---:|---:|
| Eligibility yield | 0.4 | 0.3 |
| Selected-output structural duplicate rate | 0.0 | 0.0 |
| Maximum object-category share | 0.15 | 0.15 |
| Maximum engine share | 0.05 | 0.2 |
| Maximum canonical payoff share | 0.25 | 0.3 |
| Mean pairwise creative distance | 0.885247 | 0.839 |
| Minimum pairwise creative distance | 0.5 | 0.36 |
| Average SHORT_FORM_ENGINE score | 61.9 | 73.7 |
| Accepted production-risk flag rate | 0.05 | 0.0 |
| Top-3 mean distance | 0.7 | 0.97 |
| Top-3 minimum distance | 0.56 | 0.94 |

V2 does **not** win every metric. It has lower eligibility yield, fewer engine families and smaller batch distances than the authored V1 bank. Its average text-screen score and Top-3 distances are higher in this run. Object/payoff concentration does not automatically improve. This benchmark gives no basis for a general claim that V2 is creatively superior.

V1 gets new derived annotations only on a copy, with explicit category/payoff/escalation mappings. At most four staging axes are shared from its affordance data; V2 supplies eight. Distances normalize supported weights, so cross-version visual distance remains an approximate structured comparison. V1's generic environment label and V2's goal-linked labels are also a schema/content difference. Both use exactly the same accepted quality checks. No weights are adapted using these results.

## API, CLI and UI

Application API remains `POST /api/v1/intelligence/workflow/concepts/generate`; ML API remains `POST /api/v1/workflow/concepts/generate`. Existing backend registry/dispatch behavior is reused without backend source changes.

```json
{"generatorVersion":"v2","seed":42,"count":20,"duration":15,"internalPoolSize":240,"rank":true}
```

Object, category, engine-family exclusions and canonical-character constraints remain available. API defaults preserve V1 callers; new UI defaults to V2 and offers V1 explicitly. CLI generation without `--rank` does not invoke any quality checks.

From repository root:

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v2 --count 20 --seed 42 --rank
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v2 --count 20 --seed 42 --rank --text-report
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --generator-version v1 --count 20 --seed 42 --rank
intelligence/ml-service/.venv/bin/python intelligence/scripts/benchmark-short-concepts.py --seed 42 --count 20
```

The existing concept-ranking page adds a generator selector, object/payoff distributions, concentration warnings, full Top-3 summaries, and per-candidate creative distance, engine similarity, silhouette similarity, raw rank and production rank. It keeps the original table as accepted raw ranking and displays the additive V2 recommendation separately. Version/config changes cancel stale requests. Nothing runs on page load.

## Verification and limitations

Final results: **50 new V2 tests passed; 58 V1 regression tests passed; 286 focused integration tests passed (4 warnings); 98 UI tests passed across 5 files; 9 backend dispatch/report tests passed**. Full permitted offline regression: **1,945 passed, 36 failed, 2 skipped, 3,030 warnings**. All 36 failure IDs exactly match the accepted baseline; a separate control run with V2 generation disabled reproduces them. The suite therefore retains preexisting failures and is not fully green.

Final exact commands, test counts, baseline failure IDs, protected hashes and file inventory are in [verification.json](verification.json). Tests cover V1 output/golden preservation; composition compatibility and visible triggers; engine/escalation separation; payoff relations; object-swapped and silhouette duplicates; symmetric/order-invariant distance; recurrence alias equivalence; concentration; capacity; creative tie order; chair fixture; accepted engine/ranking reuse; API/CLI parity; UI rendering/cancellation; pure report output; and protected evidence.

Both a direct accepted-ranker call and V2's stored `rankingResult` produce identical hashes. V1 before/after comparison is exact. Same-seed full results are byte-stable under canonical serialization; another seed changes structural selections. All 109 protected files have unchanged SHA-256 values, including V1 implementation/catalog/fixtures/evidence and accepted engines/historical files.

The full offline regression retains known baseline failures; it is not represented as green. The runner disables provider credentials/paid flags, blocks network and non-provenance subprocesses, and isolates production data. QA/video-render suites are excluded consistently with previous accepted verification to respect the no-render requirement. Java report tests exercise projections/dispatch without PDF generation.

The main remaining limitation is realization quality. Typed compatibility, concentration and distance can reject impossible combinations and cosmetic variation, but cannot establish humor, readable motion, semantic novelty or viewer response. Some generated goals/rules still exceed accepted English pattern coverage. Failure reasons are preserved instead of weakening validators or changing scores. V2 remains an inspectable deterministic grammar baseline for future ideation work.

## Files changed in this task

- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/short_concept_generation_v2.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/short_concept_grammar_v2.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/creative_distance.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/concept_production_selection.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/short_concept_benchmark.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/api.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/scripts/generate-short-concepts.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/scripts/benchmark-short-concepts.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_short_concept_v2.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_concept_production_selection.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_short_concept_v2_api.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/fixtures/short_concept_v2_golden.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/fixtures/chair_concentration_v2.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/frontend/src/app/pages/concept-ranking.page.ts`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/frontend/src/app/pages/concept-generation.page.spec.ts`

This new evidence directory is also added. Preexisting unrelated dirty files were preserved; no commit or deployment was made.
