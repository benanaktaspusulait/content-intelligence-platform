HOOK_002_REGRESSION_CAUSE: Whole-prompt token matching leaked later-beat "starting side" into opening-specific startsMidAction evidence
HOOK_002_EVALUATION_STABLE: YES
CANONICAL_SCORE_CONSISTENCY: VERIFIED

BASELINE_SCORE: 93.42708333333334
OPENAI_REPLAY_SCORE: 93.42708333333334
OPENAI_REPLAY_CREATIVE_VALIDITY: CREATIVE_RISK_DETECTED / PROVISIONAL_CREATIVE_VALIDITY_REQUIRED

HIGH_IMPACT_CREATIVE_BLOCKERS_IDENTIFIED: YES
PROMPT_ONLY_GAIN_LIMITED: YES
OWNER_APPROVED_STORY_REVISION_REQUIRED: YES

EXISTING_STORY_EVOLUTION_REUSED: YES
REAL_STORY_EXPERIMENT_PREPARED: YES
MAX_PLANNED_REAL_PROVIDER_CALLS: 2
RECOMPUTED_EXPERIMENT_CAP_USD: 0.017966

NEW_REAL_PROVIDER_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0
PRODUCTION_DB_WRITES: 0
GIT_HISTORY_MODIFICATIONS: 0

TEST_RESULT: 207 focused ML tests passed; 24 backend tests passed; saved real-response offline replay passed; git diff --check passed
READY_FOR_OWNER_AUTHORIZATION: YES

# Canonical stability and next creative step

## Actual saved evidence and root cause

This investigation uses the P2 Pip source and exact saved OpenAI/DeepSeek responses from `backend/target/disposable-owner-http/run-oT9HS7/real-execution-runtime`. No new creative response was supplied. The original baseline is a deterministic integration-fixture prompt; the replayed intervention was authored by the real OpenAI request. Those origins remain distinct.

The first timed beat is byte-identical in baseline and candidate:

> Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched.

Its full source-quote SHA-256, including the timed beat's original production annotation/result, is `7c7623ee1b4b673fd1ca953029755e314defee0313a17d1200b2ce5c06c94430` in both texts. Baseline prompt SHA-256 is `1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5`; candidate SHA-256 is `657cd1caf9f892bd986bfd2f2a92a757ee5cd4ad90d570a62dc8138463d50984`.

`PromptParser._identify_hook` previously searched the **entire prompt** for `start` and either `mid` or `action`. OpenAI's beat-2 instruction contains “starting side”. That supplies `start`, while the unchanged opening supplies `mid`/`action`. The resulting `startsMidAction=true` sends HOOK_002 through a branch requiring explicit visual-strength evidence, which is absent. Baseline lacked `start`, so the same rule used its existing textual-first-frame-intent branch and passed.

This is opening-evidence contamination, not a legitimate full-prompt dependency. Segmentation, the first action, consequence, visual state, offsets, source quote and source references did not change. The canonical request, Ruleset 1.11, production settings, PRE_RENDER context and absence of independent visual evidence were comparable.

| Input/result | Baseline before | OpenAI before | Both after |
|---|---|---|---|
| Opening action/consequence/visual state | Same | Same | Same |
| Opening source quote/span/reference | Same | Same | Same |
| `startsMidAction` | false | **true, leaked from beat 2** | false |
| `visualStrength` | null | null | null |
| `soundOffClear` | null | null | null |
| `textualFirstFrameIntent` | PASS / PROMPT_TEXT | PASS / PROMPT_TEXT | PASS / PROMPT_TEXT |
| HOOK_002 applicability | Applicable | Applicable | Applicable |
| HOOK_002 outcome/severity | PASS / PASS | UNKNOWN / CRITICAL | PASS / PASS |
| Canonical score | 93.42708333333334 | 92.48958333333336 | 93.42708333333334 |

The correction retains the existing lexical predicate and scopes it to the first parsed beat's source quote, action, consequence and visual state. It does not reinterpret “already mid-action” as verified imagery. Explicit visual-strength/sound-off fields retain their existing separately declared metadata dependencies.

### Exact score effect

Before the fix, the scored hook family contained only GOAL_VISIBLE_EARLY at 85; UNKNOWN HOOK_002 was excluded. After correction it contains HOOK_002 at 100 and GOAL_VISIBLE_EARLY at 85, averaging 92.5. The normalized hook-family weight is 0.125. Therefore the correction restores `(92.5 - 85) × 0.125 = 0.9375` points. No unknown was scored as zero or promoted to a visually verified pass.

The only changed candidate rule outcome is HOOK_002. After correction, baseline and accepted replay have **zero rule outcome/severity differences**. This does not establish equal rendered quality or creative superiority.

Complete before/after rule inputs, outputs and aggregation evidence are in [HOOK_002_EVALUATION_STABILITY_EVIDENCE.json](HOOK_002_EVALUATION_STABILITY_EVIDENCE.json). The saved responses were replayed through reconstruction and the actual evaluator using temporary copies; results are in [HOOK_002_SAVED_RESPONSE_REPLAY_AFTER_FIX.json](HOOK_002_SAVED_RESPONSE_REPLAY_AFTER_FIX.json). DeepSeek remains rejected for its genuine source-reference violation. OpenAI remains source-bound, accepted for research and creatively provisional.

### Versioning

No Ruleset YAML, weight, threshold or rule-evaluation branch changed. A new Ruleset version is not required for this extraction-scope repair. Historical persisted analyses and provider responses remain frozen; corrected calculations are separate offline artifacts. The old scores remain reproducible by applying the old extraction predicate in memory.

## Stability and safety verification

Focused tests exercise:

- The exact baseline/real OpenAI pair, identical opening fields and actual canonical evaluation.
- Later-beat source-valid staging, “starting side”, production-note whitespace and equivalent static-camera wording: identical HOOK_002 result.
- Formatting-only blank-line changes: every rule outcome/severity and total score remains identical.
- A genuinely changed opening: the opening flag changes; absent visual strength remains UNKNOWN in the corresponding branch.
- Missing anomaly/opening support: later `start` tokens cannot manufacture PASS.
- Existing production-profile normalization/conflict and source-plan rejection tests: stale metadata is separated, genuine protected changes remain rejected.
- Creative validity independent from numerical A; frame-zero excellence, repetitive consequences, ending overload and thin-object risks remain visible.
- Story proposal, independent review, owner approval and BUILD_PROMPT handoff as separate operations; no unauthorized provider construction.

An ordinary “already mid-action” label still cannot establish verified visual excellence. Missing semantic/visual evidence and F8 gates remain unresolved. Story fidelity does not become PASS from source-anchor preservation alone.

## Stop the low-value prompt loop

The real models were given only grounded source-bound operations. For P2, those chiefly allow beat-2 or beat-4 action/result staging. The approved events, consequences, ordering, ending and windows remain protected. The models' limited choices cannot establish that stronger story-level proposals are impossible.

The existing creative-validity assessment detects both repetitive viewer-visible consequences and an overloaded final window. When these two independent story-level risks occur together, the existing adaptive preflight now returns:

```text
state: NO_MATERIAL_PROMPT_ONLY_CREATIVE_GAIN
generationAllowed: false
researchGenerationEligibility.allowed: false
creativeOpportunity.nextAction: OWNER_APPROVED_STORY_EVOLUTION
```

The same decision is exposed in reconstruction diagnosis and carried through the backend's authoritative preflight snapshot. Existing POST and worker checks already re-evaluate this policy before reserving/dispatching. Old text-research permission cannot bypass this decision. This is a creative-scope stop, not a canonical score change or a claim that staging has no value.

Local contact visibility and action/result separation remain `SOURCE_BOUND_PRESENTATION_IMPROVEMENT`. Visual uncertainty by itself does **not** trigger this story-level stop or abandon the concept. New viewer-visible consequences, a revised opening promise, a less overloaded event sequence or redesigned payoff require an owner-approved source revision. No arbitrary extra attempt, mandatory joke or universal impossible-physics opening is introduced.

## Reuse Story Evolution for meaningful creative proposals

The existing path is:

1. Inspect the exact source with `GET /api/v1/intelligence/workflow/cpq/story-evolution-source?analysisId=10fc4c38-7cdf-4f71-b8dc-05b14315352a` in the environment that owns this saved P2 subject.
2. After fresh explicit authorization, use `POST /api/v1/intelligence/workflow/cpq/story-evolution-runs` with one round and at most two requests.
3. DeepSeek STORY proposes two complete narrative alternatives in one response. OpenAI STORY_REVIEW compares them independently against the complete original.
4. Retain only a review-supported, structurally promising draft. Owner story approval remains PENDING. No prompt is rewritten or approved automatically.
5. Only a later explicit owner decision may approve an exact story fingerprint. BUILD_PROMPT requires its existing separate authorization and fresh Ruleset 1.11 evaluation. No further optimization, image generation or render follows automatically.

Current instructions explicitly cover a readable opening, distinct consequences, natural pacing, active character choices, causal payoff, generator feasibility and artificial checklist density. Identity, premise, physical rule and ending remain locked in this first proposed experiment. Other source events/order may be proposed for revision. These proposals cannot alter the approved source without the owner.

For the new `creative-story-merit-v1` review contract, every candidate needs findings across all six existing CPQ dimensions. Supported findings must quote exact candidate text; unavailable support remains UNKNOWN. A CREATIVELY_STRONG label without the dimensional evidence is rejected. Reviews must identify weaknesses and compare actual consequences and pacing; no audience-performance or A/A+ claim is accepted as proven.

Two small existing integration defects were corrected so this path can work: real STORY/STORY_REVIEW results now carry explicit dispatch provenance and verified token-cost accounting, and real cross-provider generation/review establishes reviewer independence. Fixtures, missing identities and same-provider reviews cannot establish it. Full canonical contexts remain saved; outbound requests remove duplicated nested evidence while retaining finding identity, severity, explanation, classifications and the full-context hash. This avoids the existing 24 KB role-input rejection without inventing evidence. Review output is bounded at 4,000 tokens for the expanded two-candidate evidence contract.

## Smallest prepared real experiment and exact reservation

The provider-free preparation script is [prepare-creative-story-experiment.py](../scripts/prepare-creative-story-experiment.py). Its output is [CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json](CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json), containing the complete original story, exact source/approval/analysis bindings, full effective STORY request preview, model identities, rates, cost calculations and a disabled authorization template.

Resolved Compose configuration and running ML-container configuration agree:

| Request | Actual configured model | Input/output USD per million | Output cap | Maximum calculated USD |
|---|---|---|---|---|
| STORY | DeepSeek `deepseek-chat` | 0.30 / 1.20 | 4,000 | 0.00898230 |
| STORY_REVIEW | OpenAI `gpt-4o-mini-2024-07-18` | 0.15 / 0.60 | 4,000 | 0.00670215 |

STORY uses 9,796 payload bytes, 3,145 system bytes and a 1,000-byte framing margin. Its upper bound is `((9796 + 3145 + 1000) × 0.3 + 4000 × 1.2) / 1,000,000`.

An exact future STORY_REVIEW payload does not exist before generation. Instead of inventing proposed stories, preparation prices the actual enforced maximum 24,000-byte review-input envelope, 3,681 system bytes and the same 1,000-byte margin. Its upper bound is `((24000 + 3681 + 1000) × 0.15 + 4000 × 0.6) / 1,000,000`.

The sum of calculated request upper bounds is **$0.01568445**. The existing durable Story Evolution ledger splits the authorization equally across two requests, so each request reserves **$0.008983** after rounding up. The exact compatible total authorization ceiling is therefore **$0.017966**. This is a newly calculated conservative reservation, not an invoice, a quote of actual future tokens or a reused experiment budget.

Maximum scope: one STORY request, one cross-provider STORY_REVIEW request, one round, 600-second run deadline, 4,000 output tokens per request, no retry/fallback/model substitution. Existing provider adapters use 20-second request timeouts. Provider configuration is present; live availability is **not probed** because inference is not authorized.

The authorization template has `authorizePaidInference=false` and `confirmSourceAuthority=false`; no run was created. Real dispatch remains disabled in the running configuration. Fresh authorization must bind these current models, source and cost envelope; current persisted scope/configuration must be rechecked before dispatch. If the exact saved source is unavailable, stop rather than recreate its IDs or apply it to production. No previous authorization is consumed. Scope mismatch, insufficient reservation, ambiguous dispatch/usage, truncation, invalid review or provider failure stops the run; no automatic second attempt is permitted.

Complete proposed stories, exact source changes, independent assessments and remaining risks are necessarily PENDING until that separately authorized experiment. This task establishes tested implementation readiness, not real-model story improvement or calibrated creative A/A+ quality.

## Git history integrity

The initial branch was `master`, with a clean worktree and HEAD/origin-master at `cf46676a3f4a97a88982173682e2817e6feab8e2`. During this task, an external actor created `378a6c6210762759193a8206d131f1254d9fcc89`, authored by `Auto <auto@mindocean.com>`, with the same unrelated cleanup subject. It included the initial parser fix and regression-test file while this task was still running.

Reflog also contains preceding `commit (amend)` entries. Global Git configuration identifies Auto as the user. No `core.hooksPath` override or enabled local hook was found; the hooks directory contains samples only. A process inventory did not identify the specific writer. The existence of Codex/background processes is not sufficient to attribute the mutations to one of them. No unrelated process was interrupted.

`GIT_HISTORY_MODIFICATIONS: 0` above means **commands performed by this agent**. One external HEAD movement was observed. No commit/amend/push/reset, history rewrite or Git configuration change was performed here. Current task files are reviewable as local changes; external automation must be accounted for before treating HEAD as an untouched baseline.

## Verification results and limits

Final results:

| Verification | Result |
|---|---|
| Twelve focused ML suites: hook stability, adaptive policy, creative validity, story review, reconstruction, profile contracts, missing evidence, Ruleset 1.11, roles, F8, model authoring and contract repair | **207 passed**, exit 0 |
| `StoryEvolutionServiceTest` with disposable PostgreSQL | **5 passed**, no failures/errors/skips |
| `OptimizationLoopTest` with disposable PostgreSQL and actual offline evaluator/compiler | **17 passed**, no failures/errors/skips |
| `StoryReviewIndependenceTest` | **2 passed**, no failures/errors/skips |
| Exact saved real-response replay on temporary evidence copies | OpenAI ACCEPTED; DeepSeek REJECTED; score **93.42708333333334/A**; external dispatches 0 |
| In-memory old-predicate reproduction | Original 93.42708333333334/A; candidate 92.48958333333336/A; expected regression reproduced |
| Preparation script against resolved Compose configuration | Exit 0; two-call reservation **$0.017966**; no provider construction |
| `git diff --check` | Passed |

The ML command ran from `intelligence/ml-service` with `POMPOM_DATA_ROOT` set to the absolute repository `intelligence/data` directory. Backend commands were `mvn -q -Dtest=StoryEvolutionServiceTest,OptimizationLoopTest test` and `mvn -q -Dtest=StoryReviewIndependenceTest test`, both exit 0. This is focused verification, not a claim that the entire repository test suite ran.

Tests use offline responses or disposable PostgreSQL containers, never production database mutations. No deployment was performed; the running service does not yet contain this task's source changes.

Initial test invocation had three configuration failures because `POMPOM_DATA_ROOT` was not set to the repository data directory, plus one obsolete assertion expecting an undiagnosed creative-opportunity state. The invocation was corrected and the assertion updated for the intentional policy behavior. No scoring expectation was relaxed. Existing datetime/Mockito warnings remain unrelated.

No paid call, new story approval, prompt mutation, official creative grading activation, image/video generation or publishing occurred. The next boundary is explicit owner authorization for the prepared story experiment, followed by an authorized deployment/execution in the environment owning the exact saved subject.

## Files delivered

- `ml-service/app/parser/prompt_parser.py`: opening-scoped extraction repair.
- `ml-service/app/workflow/adaptive_optimization.py`: creative-scope stop in the existing authoritative preflight.
- `ml-service/app/workflow/creative_reconstruction.py`: expose that scope decision alongside ranked opportunities.
- `ml-service/app/workflow/creative_roles.py`: effective story/critic instructions, six-dimension evidence validation, compact request projection, exact request preview and bounded accounting/provenance for story roles.
- `backend/src/main/java/com/pompomhills/intelligence/workflow/OptimizationLoopService.java`: retain the creative-scope evidence in the server snapshot.
- `backend/src/main/java/com/pompomhills/intelligence/workflow/StoryEvolutionService.java`: version the merit-review requirement and derive independent-review provenance from actual cross-provider identities.
- `ml-service/tests/test_hook_002_metamorphic_stability.py`, `test_adaptive_optimization_v3.py`, `test_story_review_contract.py` and `backend/src/test/java/com/pompomhills/intelligence/workflow/StoryReviewIndependenceTest.java`: focused regression coverage.
- `scripts/prepare-creative-story-experiment.py` and the three JSON evidence/manifest artifacts linked above.

No frontend redesign, second generator/service, new scoring feature or Ruleset change was introduced.
