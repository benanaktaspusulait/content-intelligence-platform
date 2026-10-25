# Deterministic short-form concept generation v1

Implemented upstream generation and orchestration with no changes to accepted creative scores. All recommendations are pre-render hypotheses; no retention measurements, external AI calls, provider spend, images, video or PDF renders were produced.

## Architecture and algorithm

`ConceptCandidateGenerator.generate(config, cast)` is the thin future ideation boundary. Only `DeterministicConceptGenerator` exists in v1. `generate_and_rank` normalizes strict records, fingerprints them, retains structural duplicates without scoring them, adapts unique records into existing `ConceptInput`, and calls the existing `concept_ranking.rank_concepts` once. That function continues to own SHORT_FORM_ENGINE, CPQ/hard gates, penalties, ranking and top-three diversity selection. Generation diagnostics never feed back into those scores.

The versioned JSON catalog contains 25 complete authored causal recipes. Each binds a concrete goal, primary interaction, one impossible rule, direct goal obstruction, immediate trouble, five changing beats and a rule-linked payoff. Object/effect pairs are not independently shuffled. Only the character placeholder is substituted. Silent comprehension is the default (`NONE`); one character, primary interaction and stable location are preferred. Production notes describe contact/scale risks without inventing another feasibility score.

The local algorithm:

1. Canonicalize catalog, cast and filter ordering; validate count 10–100, seed and duration 10–20 seconds.
2. Filter whole recipes by engine family, object or category. Empty results fail explicitly.
3. Order compatible recipes by SHA-256 of seed, cycle and recipe ID. Prefer families below a soft 25% cap (minimum two). Under constrained catalogs, choose remaining least-used families; report concentration rather than fabricate alternatives.
4. Assign a configured canonical character after choosing goal/object/rule. Allocate equal planned beat windows across the requested duration; these are story timing hypotheses.
5. Fingerprint, preserve and deduplicate before accepted quality validation. Record every attempt and its disposition/reasons.
6. Invoke accepted ranking once for admitted concepts. Return its eligible order, diversity slate and first-render ID unchanged, plus original candidates and diagnostic evidence.

The catalog is intentionally finite. A request for 100 means 100 raw attempts, not 100 unique inventions: the default catalog produces 25 unique admissions and 75 retained structural duplicates. `catalogExhausted` and recipe reuse provenance disclose this. Adding families requires authored catalog records, not scorer changes. Existing ranking capacity remains 30; a future adapter yielding more unique admissions retains excess records as `DEFERRED_RANKING_CAPACITY` and labels scope `FIRST_30_CANONICAL_ID_ADMISSIONS_ONLY`. It makes no global-best claim for that partial evaluation.

No adaptive weights, score-guided regeneration, reinforcement learning, persistence or render dispatch are included.

## Fingerprints, duplication and historical evidence

`short-concept-fingerprint-v1` records nine dimensions: goal type, interaction type, engine family, transformation direction, trigger, escalation topology, resolution topology, final silhouette topology and loop topology. The full hash includes all nine. The core hash excludes goal type and optional loop wording, preventing cosmetic changes from becoming engine novelty. Near duplicates require equal core dimensions and at least four supported core dimensions. Growth/shrink direction cannot be hidden by metadata.

The supplied spoon/brush fixture produces `nearDuplicate=true` despite different objects and goals. Shrinking on strategy change produces `nearDuplicate=false`, with different interaction, family, direction, trigger, escalation and resolution. See [fingerprint evidence](fingerprint-evidence.json). Authored structural metadata and conservative text patterns are descriptors, not semantic proof.

Existing ranking's historical engine/interaction/final-silhouette comparison is reused; no second historical scorer or corpus is introduced. High accepted duplicate risk maps to `ENGINE_SILHOUETTE_DUPLICATE`; other observed similarities map to `PROVEN_ENGINE_WITH_NEW_EXECUTION`; no match means `NOVELTY_UNVERIFIED`. Coverage remains the accepted two-reference corpus, so absence of a match does not establish originality.

## Interfaces and identity

- ML API: `POST /api/v1/workflow/concepts/generate`.
- Application API: `POST /api/v1/intelligence/workflow/concepts/generate`.
- Existing `/concept-ranking` UI: supplied-concept ranking plus count, seed and Generate controls; statistics, distribution, failures, existing ranking, top three and first recommendation. No automatic generation on page load.
- Compact text report is a pure projection of run evidence, not a PDF/rendering path.

API inputs include `count`, `seed`, `duration`, `rank`, `characterIds`, `excludeEngineFamilies`, `excludeObjects`, `excludeObjectCategories`, and `generatorVersion`. Default API ranking is enabled. CLI ranking requires `--rank`; generation-only results contain no invented validation scores.

The application backend replaces incoming cast data with the active canonical database registry. Direct ML/CLI calls read the repository's canonical seed migration when no snapshot is supplied; this is explicitly a seed snapshot, not a live registry. CLI `--cast-file` supplies an id/name JSON array for other deployments. Generation has no hard-coded character descriptions. Reproduction depends on versioned configuration, catalog hash and cast snapshot hash, all returned in evidence.

From repository root:

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --count 20 --seed 42 --rank
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --count 20 --seed 42 --rank --text-report
```

Example request:

```json
{"count":20,"seed":42,"duration":15,"rank":true,"excludeEngineFamilies":[],"excludeObjects":[],"excludeObjectCategories":[],"characterIds":[]}
```

## Recorded 20-candidate run

[Complete run](example-run.json), [configuration](example-config.json), [compact report](example-report.txt). Seed 42: **20 raw, 0 structural duplicates, 8 eligible, 8 requiring revision, 4 rejected**. Every attempt remains addressable with its source and accepted failure reasons. Twenty engine families occur once each; normalized family entropy is 1.0 and displayed diversity is 100, with no concentration warning. Entropy is a distribution diagnostic, not creative quality; warning threshold is more than 35% in one family.

| Production rank | Candidate | Existing ranking | Existing short form |
|---|---|---:|---:|
| 1 | Chair Answers The Armrest | 97.6 | 100 |
| 2 | Chair Marks Its Spot | 97.6 | 100 |
| 3 | Runaway Lid | 97.6 | 100 |

First render recommendation: **Chair Answers The Armrest**, `local-chair-answers-the-armrest-011`. Kiko is already trying to sit on an inverted chair at frame zero. Opposite armrest pressure changes its orientation; clamping changes the consequence; lifting underneath produces apparent success; resting on the armrest flips chair and rider. All events are proposed story beats, not observed video.

The accepted dimensions are 100 for instantaneous legibility, contradiction, goal, rule, progress, escalation and payoff; rewatch is 60. The three selected candidates tie at 97.6 and have equal reported production efficiency and duplicate-risk categories. The actual reason for #1 is **STABLE_ID_TIE_BREAK**. There is no measured payoff/retention advantage over #2 or #3. Full dimension comparisons and historical/production flags are retained in `WHY_THIS_ONE_FIRST`.

| Attempt | Disposition | Accepted failure codes |
|---|---|---|
| Backward Brush Stroke | REVISION_REQUIRED | MULTIPLE_UNRELATED_RULES, WEAK_VISUAL_PAYOFF |
| Blanket Reverses The Fold | REJECTED | OPENING_NOT_IN_TROUBLE, EVERYDAY_GOAL_UNCLEAR, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, WEAK_VISUAL_PAYOFF, DECLARED_GOAL_UNSUPPORTED |
| Box Multiplies The Task | REVISION_REQUIRED | OPENING_NOT_IN_TROUBLE, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF |
| Box Passes The Buckle | REVISION_REQUIRED | OPENING_NOT_IN_TROUBLE, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF |
| Brush Shrinks Away | REVISION_REQUIRED | OPENING_NOT_IN_TROUBLE, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, WEAK_VISUAL_PAYOFF |
| Brush Will Not Let Go | ELIGIBLE | — |
| Chair Answers The Armrest | ELIGIBLE | — |
| Chair Marks Its Spot | ELIGIBLE | — |
| Cloth Returns The Dust | REJECTED | OPENING_NOT_IN_TROUBLE, EVERYDAY_GOAL_UNCLEAR, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF, DECLARED_GOAL_UNSUPPORTED |
| Cup Will Not Be Heavy | REVISION_REQUIRED | OPENING_NOT_IN_TROUBLE, EVERYDAY_GOAL_UNCLEAR, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF, DECLARED_GOAL_UNSUPPORTED |
| Drawer Borrows The Room | ELIGIBLE | — |
| Drawer Repels The Pull | ELIGIBLE | — |
| Hanger Repels The Coat | REJECTED | OPENING_NOT_IN_TROUBLE, EVERYDAY_GOAL_UNCLEAR, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF, DECLARED_GOAL_UNSUPPORTED |
| Runaway Lid | ELIGIBLE | — |
| Shoe Stretches The Step | REVISION_REQUIRED | OPENING_NOT_IN_TROUBLE, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF |
| Soap Lends Its Stick | ELIGIBLE | — |
| Spoon Delays The Bite | REVISION_REQUIRED | OPENING_NOT_IN_TROUBLE, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, IDENTICAL_ATTEMPTS, WEAK_VISUAL_PAYOFF |
| Spoon Outgrows Breakfast | ELIGIBLE | — |
| Tray Loses Its Bottom | REJECTED | OPENING_NOT_IN_TROUBLE, EVERYDAY_GOAL_UNCLEAR, CORE_RULE_UNSUPPORTED, TOO_FEW_CAUSAL_BEATS, HIGH_ACTIVITY_LOW_PROGRESS, WEAK_VISUAL_PAYOFF, DECLARED_GOAL_UNSUPPORTED |
| Wall Borrows The Stretch | REVISION_REQUIRED | IDENTICAL_ATTEMPTS |

Several authored goals/mechanisms exceed the accepted English pattern screen's coverage. A written visible action therefore does not guarantee recognized source support. Unsupported goals/rules, unrecognized causal progress, repeated-attempt flags and weak payoff flags remain visible. The generator does not weaken those gates or rewrite text merely to game a score. This finite bank and a 40% eligibility yield are material v1 limitations.

Metrics for this run: eligibility yield 0.40; duplicate rate 0; family entropy 1.0; average accepted short-form score 61.9; highest accepted ranking score 97.6; high-activity/low-progress rate 0.50; weak-payoff rate 0.55; late-hook rate 0.50; production-risk rate 0.05. Yield and duplication use all 20 raw attempts. Finding/risk rates use the 20 evaluated unique attempts; the score average uses evaluated non-null short-form scores. Production risk means accepted text-based flags, not verified production cost. Rejected count includes structural duplicates when present; revision/deferred/not-evaluated categories are separately disclosed.

## Reproducibility and reuse proof

Two seed-42 runs have identical candidate SHA-256 `92709b6cc6f6ea46d4a6cb51ac35c1d83cc0d0d8a7e066df0ec76b3344987bfe` and identical complete-run hash. Seed 43 changes four structural cores in each direction; this is more than renamed characters. Catalog/cast/filter ordering invariance is tested. [Seed evidence](seed-evidence.json) records hashes and provenance.

[Ranking reuse evidence](ranking-reuse-evidence.json) confirms exact equality between the orchestrated ranking result and a direct call to accepted `rank_concepts` on the same adapted admissions. Integration spies additionally verify one ranking invocation, accepted SHORT_FORM_ENGINE invocation after dedup, and unchanged slate selection. Accepted ranking source, fixtures, engines and historical projections retain their protected hashes.

## Verification

- New generator/fingerprint/orchestration/API/CLI tests: **58 passed**.
- Focused generator plus accepted short/long/ranking integration: **236 passed, 4 warnings**.
- UI: **96 passed across 5 files**, including 6 new generation tests.
- Backend dispatch/report projection: **9 passed**, including 2 new controller tests. No PDF generation was invoked.
- Full permitted offline ML regression: **1,895 passed, 36 failed, 2 skipped, 3,030 warnings**.
- All 36 failure IDs exactly match the previous accepted baseline. A control run disabling the new generation entry point reproduces all 36 failures. These are unresolved preexisting failures; the full suite is not green.
- **86 protected files** have identical before/after SHA-256 hashes. New logs/examples live only in this new evidence directory. Existing accepted documents, frozen scores and production results were preserved.

Logs, exact failure IDs, file inventory and machine-readable assertions are in [verification.json](verification.json). The regression runner disables provider credentials/paid flags, blocks sockets and non-provenance subprocesses, and uses isolated data. QA/media-generation suites remain excluded as in the accepted baseline to honor the no-render requirement.

Commands (ML commands run from `intelligence/ml-service`):

```sh
.venv/bin/python ../scripts/test-story-premise-offline.py tests/test_short_concept_generation.py tests/test_concept_fingerprint.py tests/test_short_concept_generation_api.py -q --tb=short
.venv/bin/python ../scripts/test-story-premise-offline.py tests/test_short_concept_generation.py tests/test_concept_fingerprint.py tests/test_short_concept_generation_api.py tests/test_concept_ranking.py tests/test_concept_ranking_api.py tests/test_short_form_engine.py tests/test_short_form_integration.py tests/test_story_premise_engine.py tests/test_story_premise_integration.py -q --tb=short
.venv/bin/python ../scripts/test-story-premise-offline.py tests --ignore=tests/qa --ignore=tests/test_video_qc.py -q --tb=short
```

Backend, from `intelligence/backend`:

```sh
mvn -o -q -Dtest=ConceptGenerationControllerTest,ConceptRankingControllerTest,ShortFormReportTest,StoryPremiseReportTest test
```

Frontend, from `intelligence/frontend`:

```sh
npm exec ng test -- --watch=false --include=src/app/pages/concept-generation.page.spec.ts --include=src/app/pages/concept-ranking.page.spec.ts --include=src/app/pages/short-form-report.component.spec.ts --include=src/app/pages/story-premise-report.component.spec.ts --include=src/app/pages/workflow.page.spec.ts
```

## Changed files

The following inventory describes this task only. Other preexisting dirty ranking/engine/IDEA files remain in the shared checkout.

- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/concept_fingerprint.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/short_concept_generation.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/short_concept_catalog.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/api.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityMlClient.java`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/ConceptGenerationController.java`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/ConceptGenerationControllerTest.java`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/frontend/src/app/pages/concept-ranking.page.ts`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/frontend/src/app/pages/concept-generation.page.spec.ts`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/scripts/generate-short-concepts.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_short_concept_generation.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_concept_fingerprint.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/test_short_concept_generation_api.py`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/fixtures/concept_fingerprint_cases.json`
- `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/tests/fixtures/short_concept_generation_golden.json`

This evidence directory is also new. No commits, deployment or external publication were performed.
