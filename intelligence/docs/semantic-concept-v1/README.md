# Semantic Concept Ideation Provider V1 — mocks only

The semantic boundary proposes candidate possibilities. The existing deterministic stack remains authoritative for validation, scores, eligibility, ranking, and production selection. This release makes **zero external provider calls**, adds no SDK, spends no money, and renders no media.

The motivating accepted baseline remains frozen: requested 20, returned 9, DIVERSITY_CAPACITY_REACHED, all nine HIGH template-shape risk. No Creative Shape threshold is weakened to fill the batch.

## Architecture / provider boundary

`SemanticConceptGeneratorV1.generate(config, cast)` structurally implements the existing `ConceptCandidateGenerator` protocol. Its transport reuses the existing `app.llm.provider.LLMProvider.complete` abstraction. A controlled `MockSemanticProvider` implements that transport using a bundled JSON fixture. No vendor factory, SDK construction, credentials, network adapter, retry, fallback, or model discovery occurs.

New modules:

- `semantic_concept_provider.py`: request/response data contracts, versioned prompt, strict parser, mock transport, generator boundary.
- `semantic_concept_adapter.py`: canonical-character normalization and conservative text-to-plan classification using accepted analyzers.
- `semantic_concept_generation.py`: explicit deterministic/semantic/hybrid orchestration over the common judges and production selector.
- `semantic_concept_benchmark.py`: mock-only architectural comparison.
- `semantic_concept_analysis_v1.json`: isolated non-canonical water-transfer classification coverage.
- `semantic_concept_mock_v1.json`: authored test corpus, executable only through an explicit mock configuration.

API/CLI dispatch and the existing UI are extended minimally. Two new test modules and a fixture-category manifest verify the boundary. `changed-files.json` records the exact files/hashes.

When `generatorMode` is omitted, all new fields are removed while preserving unset fields, and the accepted dispatcher runs. Six legacy configurations have byte-serialization equality tests. Explicit deterministic V1 retains its original workflow with source annotations. Explicit V2 deterministic, semantic, and hybrid modes use the full current validation stack; omitted V2 stack switches are filled for explicit new modes, while explicitly disabled required layers are rejected.

## Configuration / CLI / API

```json
{
  "generatorMode": "semantic",
  "count": 20,
  "seed": 42,
  "semanticConceptPromptVersion": "v1",
  "semanticRawCount": 40,
  "allowExternalGeneration": false,
  "semanticProvider": {
    "provider": "mock",
    "model": "fixture-v1",
    "temperature": 0.7,
    "maxCandidates": 60,
    "maxOutputTokens": 16000,
    "timeoutSeconds": 30,
    "mockCorpus": "review-v1"
  }
}
```

Existing ML endpoint: `POST /api/v1/workflow/concepts/generate`. Existing Java proxy: `/api/v1/intelligence/workflow/concepts/generate`. Modes: deterministic, semantic, hybrid. The old generatorVersion/Beat Grammar/Naturalness/Creative Shape configuration remains available and is recorded.

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --mode semantic --mock --count 20 --seed 42 --rank
intelligence/ml-service/.venv/bin/python intelligence/scripts/generate-short-concepts.py --mode hybrid --mock --count 20 --seed 42 --rank
```

CLI also supports provider/model, raw count, output-token cap, and an explicit external-generation flag. These express the future contract; **non-mock execution remains disabled even when the external flag is true**. Missing provider returns SEMANTIC_PROVIDER_NOT_CONFIGURED. Non-mock without permission returns EXTERNAL_GENERATION_DISABLED. Non-mock with permission returns LIVE_SEMANTIC_TRANSPORT_NOT_ENABLED. Arbitrary injected transports, including mock subclasses, are refused before execution. Provider/model strings are vendor-neutral; a future separately authorized live adapter can reuse the existing transport boundary.

The UI starts in deterministic mode, never generates on load, labels semantic modes as requiring configuration, offers an explicit mock checkbox, and shows source per candidate. It sends `allowExternalGeneration=false`; no live-spend UI is enabled. Changing mode/mock choice cancels stale requests.

## Prompt V1 and schemas

`semantic-prompt-v1.txt` stores the exact system prompt and request JSON. The prompt emphasizes object-specific affordance contradiction, strange-but-intuitive physics, frame-zero comprehension, one causal rule, 4–5 major beats, varied story shapes/payoffs/silhouettes, and avoidance of bracing → paused trigger → false success → reset collapse. Inspiration categories are abstract families, not recipes. Only two compact historical structural caution zones are included; full historical prompts and finished story examples are absent.

The provider is explicitly forbidden to select winners, award scores/confidence, assert eligibility, or change validators. `request-schema-v1.json` and `response-schema-v1.json` preserve generated JSON schemas.

Raw candidate fields: ideaId, title, protagonistSuggestion, everydayGoal, primaryObject, normalExpectation, impossibleRule, visibleTrigger, whyThisObject, goalRuleRelationship, frameZeroDescription, 4–5 beats (strategy/visibleConsequence/newInformation), finalPayoff, suggestedPayoffFamily, loopPotential, environment, dialogueNeed, providerRationale, durationSeconds.

## Untrusted-output behavior

The parser requires bounded JSON with only an `ideas` envelope. It rejects duplicate JSON keys, non-finite numbers, invalid envelopes, excess candidates, and responses over 2 MB. Individual malformed candidates are retained as SCHEMA rejections while valid siblings continue. All occurrences of duplicate idea IDs are rejected. Extra score/confidence/winner fields are forbidden. Required text is stripped and length-bounded; beats must number 4–5, duration 10–20 seconds, repeated identical beats fail, and finalPayoff must match the final visible consequence.

A conservative lexical child-safety screen and control/format-character checks reject obvious unsuitable data. Canonical-character normalization rejects unknown suggestions and conflicting known canonical characters before creative validation. These checks do not claim complete semantic moderation or detection of every unnamed additional character.

Raw provider rationale, expected behavior, why-object explanation, and payoff suggestion are retained as data. They are excluded from `ranking_input` and cannot set canonical scores or bypass quality gates. Actor suggestions resolve only to the supplied canonical registry. Raw frame and payoff remain in providerData; normalized canonical frame/payoff match their actual timed-plan windows, avoiding contradictory plan fields. Opening admission is assessed independently against the **raw frame-zero still**; later Beat-1 action cannot rescue an unreadable opening.

## Semantic → deterministic pipeline

1. Strict schema parsing and canonical-character normalization.
2. Normalized candidate fields and accepted structural fingerprinting.
3. Accepted Premise Naturalness assessment based on rule/object/use, not provider explanations.
4. Structured strategy/consequence extraction and the accepted Beat Grammar assessor.
5. The unchanged SHORT_FORM_ENGINE/CPQ/ranking validator on the actual sourced timed plan.
6. Accepted Creative Shape distances, template risk, historical territory, and quality/diversity curation.
7. The unchanged canonical ranker on the selected candidates, then the unchanged shape-aware production selector.

The same functions process both sources in hybrid mode. Provider metadata and generation source are not selection dimensions. Tests prove direct canonical ranker equality, source-agnostic production decisions, rationale/label invariance, history checks, arbitrary-magic rejection, opening rejection, and shape repetition detection.

All pool attempts keep canonical validation and selection-block evidence. Final candidates, suppressed candidates, schema rejections, and partial normalization rejections remain separate. Canonical eligibility is retained independently from new-layer selection blocks. No rewrite or self-awarded quality feedback loop exists.

## Novel-mechanic coverage and honest failures

Semantic proposals are not restricted to current engine labels. The adapter classifies recognized responses and retains unclassified engines for review. It does not invent a new canonical scoring engine.

Water-patch transfer uses an isolated, versioned model copy with a functional-transfer policy and a faithful lexical normal form. It calls the same accepted Naturalness assessor/formula; the original rule and unextended baseline assessment are retained. The accepted default model file and behavior remain unchanged. New transfer consequence/state categories are passed to the existing Beat Grammar assessor through an isolated data copy. PROPERTY_TRANSFER is an existing Creative Shape taxonomy value, newly extracted from supported transfer rule/state evidence; baseline shape extraction remains visible. Provider-suggested payoff labels have no authority.

The towel and eraser fixtures receive high object specificity and functional irony and a property-transfer topology. **They remain canonical revisions**: the accepted short-form English goal/rule/payoff patterns do not adequately recognize drying/erasing/transfer. Those scores are not repaired or overwritten. A strong novel environmental-takeover lid fixture survives the unchanged stack. This is evidence that the boundary works, not evidence that all useful novel mechanics are supported.

The adapters are lexical planned-scene approximations with false positives/negatives. No pixels, semantic equivalence, retention, or actual causal execution are verified.

## Fixtures / costs / provenance

The bundled corpus has 15 authored entries: 8 schema-valid normalized ideas and 7 schema-rejected entries. Categories cover diverse/new shapes, repeated cross-object templates, arbitrary floating-fork magic with enthusiastic rationale, historically close chair inversion, poor frame-zero legibility, forbidden score fields, invalid beats/duration/empty text/unsafe content, and duplicate IDs. Towel/eraser transfer and the new lid story are fixture-only proposals, never automatically injected into ordinary deterministic production.

Default raw request count is max(2 × final count, 40), capped by maxCandidates (at most 60). The finite mock corpus can return fewer; exhaustion and ignored valid oversupply are explicit. Each semantic/hybrid run records one logical mock request, prompt/version/hash, requested/received/schema-valid/normalized counts, output-token cap, timeout, provider/model, zero external requests, and zero automatic retries. There are no live token/cost claims or silent retry loops.

Every new-mode candidate records generationSource (DETERMINISTIC_V1, DETERMINISTIC_V2, SEMANTIC_V1), generationRunId, and semantic provider/model/prompt-version where applicable. IDs/run IDs are deterministic. Legacy omitted-mode outputs stay byte-identical; UI derives their source label without mutating historical evidence.

## Mock comparison and human review

`mock-comparison-abc.json` compares explicit deterministic, semantic-mock, and hybrid modes at seed 42/count 20. It includes schema-valid yield, quality-admitted yield (excluding only distance/count suppression), mean final short-form score, story-shape distance, payoff distribution, historical collision, template risk, slate size, and source counts. A single candidate has null pairwise distance, not an invented diversity score.

Complete deterministic/hybrid run JSON is stored as deterministic gzip archives to retain all pool/suppression evidence without large duplicate plain-text artifacts. `mock-semantic-seed-42.json` and `mock-semantic-review.md` retain every semantic attempt and its actual judgment. Schemas, exact prompt, reproducibility hashes, source manifest, protected before/after manifests, test logs, and verification.json accompany them.

**Authored fixtures validate architecture only. They cannot demonstrate semantic superiority, live model capability, creative quality, or retention.** Final score/yield are conditional on existing quality floors and different pool sizes. The actual semantic model has not been called.

Workflow remains: generate possibilities → deterministic validation/ranking → inspect actual candidates → human approve → prompt generation → render. This task authorizes neither live generation nor rendering.

## Recorded mock comparison

| Metric | A deterministic | B semantic mock | C hybrid |
|---|---:|---:|---:|
| Normalized pool | 480 | 8 | 488 |
| Schema-valid yield | null | 0.533333 | 0.533333 |
| Quality-admitted yield | 0.189583 | 0.125 | 0.188525 |
| Final candidates | 9 | 1 | 10 |
| Mean final short-form score | 97.6667 | 100 | 97.9 |
| Mean final shape distance | 0.557333 | null | 0.58897 |
| HIGH historical collision rate | 0 | 0 | 0 |
| Production slate size | 3 | 1 | 3 |

Rates use [0,1]. Semantic schema yield is 8/15; deterministic normalized ideas do not pass through the semantic schema. The finite mock corpus was exhausted against a request for 40 raw proposals. Quality-admitted yield excludes only distance/count suppression; it is not the final selection rate.

| Payoff family | A | B | C |
|---|---:|---:|---:|
| CONTACT_ENTANGLEMENT | 2 | 0 | 3 |
| CONTROL_REVERSAL | 3 | 0 | 2 |
| ENVIRONMENTAL_TAKEOVER | 0 | 1 | 1 |
| FALSE_SUCCESS_COLLAPSE | 2 | 0 | 2 |
| OPENING_RECREATED | 2 | 0 | 2 |

Template risk: A HIGH=9; B LOW=1; C HIGH=9, LOW=1. These fixture-controlled changes are not independent creative evidence.


## Final verification

51 new tests (26 provider/parser/configuration cases, 25 generation/integration/provenance/protection cases). Final focused suite: 442 passed, 4 warnings. UI: 106 passed in 5 files. Java dispatch/report projection: 9 passed. Ruff passed. Full offline regression: 2101 passed, 36 failed, 2 skipped, 3030 warnings in 177.22 seconds. All 36 failure IDs exactly match the accepted Creative Shape baseline; zero added failures. The prior baseline had 2050 passes. QA/video-QC suites were excluded; no media or PDF renders were invoked.

The raw-frame-zero admission guard has a dedicated regression test; later Beat-1 context cannot repair it. Two additional focused transfer/model-isolation checks passed after correcting the water-transfer expectation to absorption rather than merely a drier surface. This changes only new non-canonical coverage metadata, preserving canonical results.

214 protected files retain identical SHA-256 values. Omitted-mode legacy configurations have byte-serialization equality tests. Cross-process mock CLI output under PYTHONHASHSEED=17 is byte-identical to saved evidence. Normal mock execution and refused live requests are tested with a provider factory that fails if called; evidence generation also blocks socket connections. No vendor SDK was added or constructed, and there were zero external provider calls.
