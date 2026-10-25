# Concept candidate ranking v1

A deterministic, stateless orchestration workflow for **supplied** approximately 15-second concepts, before prompt writing. It reuses the accepted SHORT_FORM_ENGINE, its source-bound structural signatures, production risk screen and historical reference catalog, plus the existing uncalibrated CPQ preview. It is not another quality validator. Neither accepted engine nor CPQ implementation was changed.

## Interfaces and files

- `ml-service/app/workflow/concept_ranking.py`: shared models, normalization, eligibility, policy composition, anchored close-score ordering, diverse production slate, explanations and pure text report projection.
- `POST /api/v1/workflow/concepts/rank`: `{ "candidates": [...] }`, 1–30 supplied concept objects or plain-text concepts.
- `POST /api/v1/workflow/concepts/validate`: one supplied object. Returns the same ranking envelope for a one-item batch, using the same function.
- Backend browser bridges: `/api/v1/intelligence/workflow/concepts/rank` and `/validate`. They forward through the existing ML client. No persistence, regrading, provider calls or generation dispatch.
- CLI: from `intelligence/ml-service`, `.venv/bin/python ../scripts/rank-concepts.py ../docs/concept-ranking-v1/example-input.json`. Add `--text-report` for the human-readable projection. Accepts one object, an array, a `{candidates: [...]}` batch, or one labeled text concept. Invalid input exits 2; valid batches with excluded concepts return a completed report.
- UI: `/concept-ranking`, linked from Prompt Quality. Paste supplied JSON or labeled text concepts separated by a `---` line. Explicit action only; expanding rows shows weighted dimensions, penalties, historical comparison, CPQ signals and normalization evidence. Editing input cancels pending requests and clears stale results. The existing UI was not redesigned.
- `tests/fixtures/concept_ranking_batches.json`: accepted repository fixture plans and mechanical test mutations, not generated production concepts. Tests cover all requested A–G batch cases.
- Report: response `reportLines` and CLI `--text-report`. This pure text projection answers what to produce first and why. No new PDF-generation path was needed; existing pure PDF projection tests remain passing. No PDFs or media were rendered.

[verification.json](verification.json) lists every changed file and exact test commands.

## Input and normalization

Each concept supports `id`, `title`, `protagonist`, `protagonistGoal`, `objectOrPrimaryInteraction`, `impossibleRuleOrCoreContradiction`, `frameZeroDescription`, `escalationPlan`, `finalPayoff`, `optionalDialogue`, and `intendedDurationSeconds`.

`text` optionally supplies an authoritative complete timed plan. Otherwise `escalationPlan` can be a complete timed string or an array of `{startSeconds, endSeconds, description}`. A timed array can contain all beats, or only middle beats: explicit first/last middle boundaries can bound the separately supplied opening/payoff descriptions. No action, escalation, concept, dialogue placement or arbitrary timing quota is generated. Untimed concepts remain unverified and need revision.

Labeled text accepts readable labels such as `Title:`, `Protagonist:`, `Goal:`, `Object:`, `Rule:`, `Frame Zero:`, `Escalation Plan:`, `Final Payoff:`, `Dialogue:` and `Duration:`. Supported source excerpts can supply an observable goal, actor, object, opening and ending. Normalization records where each value came from; unknown fields remain missing. Absent IDs become stable content-derived identifiers. A missing title remains missing. Duplicate IDs and unsupported/self-awarded fields are rejected.

Declared opening, ending, supported goal and rule cannot contradict the actual timed plan. A conflicting named actor also requires revision; pronouns can refer to an explicitly supplied protagonist. Optional dialogue supplied separately must be placed in the timed plan before eligibility, rather than receiving invented speech timing. These are source-consistency checks, not new engine scores.

The accepted English pattern screen retains its limitations. Implicit goals, unfamiliar wording or mechanics can require human clarification. Source text describes intended visuals; no actual video frames or audience outcomes are verified.

## Eligibility before ranking

All required concept fields must be present. The accepted short-form assessment must return PASS or PASS_WITH_WARNINGS. Its existing revision findings enforce compatible 10–20 second timing, a visible everyday goal and immediate problem, a coherent dominant rule, enough causal progression, silent core causality and an identifiable physical payoff. Missing fields and specific validator findings are returned as `eligibilityReasons`.

Existing high duplicate risk is ineligible. The ranking workflow also identifies exact historical winner resubmissions by comparing the same three accepted structural axes. The accepted engine's self-reference exemption remains unchanged in its own report; the production shortlist separately refuses to recommend the same historical engine without supported novelty. Moderate two-axis similarity remains eligible with an explicit penalty; familiar one-axis similarity is not rejected.

Ineligible records appear only in `revisionCandidates`; they have no rank and `rankingScore: null`. They cannot crowd out complete concepts or appear in the production slate. Their original validator outputs remain available for revision.

## Ranking formula

Only eligible concepts receive a ranking score:

`baseCompositeScore = sum(existing dimension score × weightPercent) / 100`

`rankingScore = max(0, baseCompositeScore − rankingPenaltyPoints)`

| Named dimension | Existing signal | Weight |
| --- | --- | ---: |
| Instant causal legibility | instantPremiseLegibility.score | 22% |
| Scroll-stop / visual contradiction | hookScore | 8% |
| Goal clarity | goalScore | 10% |
| One-rule strength | ruleClarityScore | 8% |
| Progress density | progressDensityScore | 18% |
| Escalation quality | escalationScore | 10% |
| Payoff strength | payoffScore | 18% |
| Rewatch potential | rewatchScore | 6% |

The first two entries intentionally share existing hook evidence: opening legibility receives 30% aggregate priority, rather than inventing a new scroll-stop measurement. Progression/escalation receives 28% and payoff 18%. No moral lesson, dialogue volume or decorative novelty score is invented. CPQ's existing strengths/weaknesses remain visible as uncalibrated advisory evidence; no CPQ grade, dimension number or aggregate is fabricated. Canonical scores and both accepted engine scores are preserved.

Novelty is an explicit structural risk penalty. Production feasibility is secondary, not another equal-weight quality dimension.

### Penalties

Each named penalty applies once per concept; evidence codes are returned. Penalties are also visible diagnostically on excluded concepts, but those concepts receive no production ranking score.

| Penalty | Quality points | Trigger from accepted evidence |
| --- | ---: | --- |
| PASSIVE_PREMISE | 8 | EVERYDAY_GOAL_UNCLEAR or TOO_FEW_CAUSAL_BEATS |
| HIGH_ACTIVITY_LOW_PROGRESS | 12 | Same-named finding |
| DUPLICATE_ENGINE | 25 HIGH / 8 MODERATE | Accepted duplicate risk or historical three-axis match; HIGH is also ineligible |
| DIALOGUE_DEPENDENT | 20 | AUDIO_DEPENDENT_CAUSALITY |
| TEMPORAL_OVERLOAD | 6 | Same-named finding |
| PRODUCTION_COMPLEXITY | **0 quality** | Secondary penalty = 100 − productionFeasibilityScore; only used inside close-score bands |
| WEAK_PAYOFF | 15 | WEAK_VISUAL_PAYOFF |
| LATE_HOOK | 15 | OPENING_NOT_IN_TROUBLE |
| RANDOM_ESCALATION | 20 | MULTIPLE_UNRELATED_RULES or CORE_RULE_UNSUPPORTED |

A familiar rule alone has no duplicate penalty. The same opening/progression/ending with renamed objects is structurally different from mere familiarity.

### Production efficiency and ties

`productionEfficiency.score` is the existing `productionFeasibilityScore`, with its TEXT_RISK_SCREEN_ONLY limitation. It is not a verified dollar-cost estimate. The secondary complexity deficit is reported explicitly, without subtracting it again from creative quality.

First sort by ranking score descending and stable candidate ID. Form an anchored band from the current highest remaining score through **three points below it**. Sort within that band by production efficiency descending, then ranking score, then ID. Repeat for remaining candidates. Anchors prevent a non-transitive chain of pairwise “close” comparisons. `rawRank`, final `rank`, `tieBand` and band anchors are returned.

Therefore a 97.6 concept can rank above a production-heavy 100 concept inside the same band. A materially stronger 100 concept remains above an easier 91.6 concept. Equal creative value and equal feasibility use a stable-ID tie break, explicitly labeled as such; no creative superiority is claimed.

### Diverse top-three slate

`rankedEligibleCandidates` preserves the explainable quality/efficiency ordering. `productionSlate` selects up to three pairwise different engines using the accepted opening, ordered progression and ending signature axes. Two matching nonempty axes indicate a near-duplicate for slate selection.

When a duplicate occupies the next slot, promote the next distinct engine only if the quality sacrifice is at most **five points**. Every promotion records displaced IDs and the score gap in `diversityAdjustments`. If no sufficiently strong different concept exists, return fewer than three and explain why; do not fill the slate with variants or invent replacements. Diversity does not change any score. `firstRenderCandidate` is the first slate member's ID, not a render authorization.

## Historical comparisons and explanations

Every row includes `historicalComparison`: `closestHistoricalEngine`, matching axes, differing signatures, duplicate risk, source SHA-256 and limitations. This reuses the accepted curated two-reference catalog, not a newly inferred performance model. No supported match means NO_MATCH_IN_LIMITED_CORPUS, not proven originality. Unknown or uncurated historical structures still need editorial comparison.

Every eligible row includes named dimension values/weights, source paths, strengths, weaknesses, penalties, production risk and `whyRankedHere`. Pairwise `whyThisBeatsTheOthers` matrices compare the first choice with every other eligible concept, including equal hook clarity, actual dimension differences, penalties, duplicate risk and production efficiency. Excluded concepts have concrete eligibility reasons instead of fabricated ranking explanations.

## Example supplied batch

Full input: [example-input.json](example-input.json). Full result and existing evidence: [example-ranked-batch.json](example-ranked-batch.json). Human projection: [example-report.txt](example-report.txt).

These are accepted synthetic test plans / historical-source mutations, **not new production concepts or measured production recommendations**.

| Rank | Supplied fixture | Short-form score | Ranking score | Production efficiency |
| --- | --- | ---: | ---: | ---: |
| 1 | Garden short adaptation | 100 | 100 | 100 |
| 2 | Existing growth test plan | 100 | 97.6 | 100 |
| 3 | Simple existing lid plan | 100 | 97.6 | 100 |
| 4 | Same lid engine with production constraints | 100 | 100 | 28 |
| 5 | Existing adhesion plan, moderate historical overlap | 100 | 89.6 | 100 |

The first production slate is Garden, growth, simple lid. The heavy 100-score variant falls below the 97.6 alternatives within the documented cost tie band. Adhesion has the same raw short-form score but an eight-point duplicate-risk penalty. Busy motion, the chair-to-stool historical duplicate and the incomplete record are excluded before ranking.

The separate diversity batch starts with three renamed variants of the lid engine as raw ranks 1–3. The production slate selects lid-a, z-garden and growth, promoting the distinct concepts from ranks 4 and 5 with quality gaps 0 and 2.4. The original ranking remains available.

## Verification

- New ranking/normalization/API/CLI/report tests: **53 passed**.
- Focused ranking + accepted short/long engines + CPQ + creative validation: **196 passed**, 4 warnings.
- Angular: **90 passed**, four files, including 8 new ranking-view tests and existing short/long/workflow tests.
- Java: **7 passed**, three classes: new controller dispatch (2), existing short-form report projection (3), accepted long-form report projection (2). No PDFs were generated.
- Full non-media ML regression: **1,837 passed, 36 failed, 2 skipped**, 3,030 warnings. All 36 failure IDs exactly match accepted baseline evidence.
- The same 36 failures reproduce with ranking functions replaced by a guard that rejects any call, proving those historical paths do not enter ranking.
- **All 120 permutations** of a five-candidate batch produce identical full serialized responses, including ranks, slates, explanations and fingerprints. Machine proof: [order-invariance.json](order-invariance.json).
- All **68** protected accepted engine/CPQ/fixture/historical-evidence files retain their original SHA-256 values: [immutable-before.json](immutable-before.json), [immutable-after.json](immutable-after.json). Existing nine-frozen-report byte-equality tests remain passing.
- Ruff F checks and `git diff --check` pass for the touched ranking/API files.

Python tests use the existing offline runner: provider credentials removed, paid flags disabled, outbound sockets denied, media subprocesses denied, original data/docs protected from test writes and disposable configuration copies used. Media-synthesizing QA/video-QC tests were excluded. Angular checks are DOM tests; Java checks are dispatch/pure projection. There were no external model calls, paid evaluations, concept generation, media/PDF renders, historical mutations or changes to accepted engine behavior.
