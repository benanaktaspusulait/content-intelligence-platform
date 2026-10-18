# STORY_REVIEW V6 — Final Nonbillable Preflight & Reviewer Readiness

**Prepared:** 2026-10-18 (UTC)  
**Scope:** One assessment-only research review operation; preparation only. No provider request was sent.

## Decision

The exact V6 request is prepared and passed the existing ML `assessment-preflight` route. This is a reproducible **nonbillable preparation**, not a paid-dispatch grant and not a finding that the reviewer will produce a correct or useful review.

The existing configured model is retained in the manifest because no alternate model has owner approval. Its current official catalog marks both `gpt-4o-mini` and snapshot `gpt-4o-mini-2024-07-18` **Deprecated**. Its official documentation still lists Chat Completions and Structured Outputs, and the installed SDK's exact request shape passed an offline mocked transport check. These facts do not establish live API availability or better review quality. No model substitution or live model probe was performed. The model recommendation is therefore **UNRESOLVED**; do not execute until the owner decides whether to authorize the pinned deprecated snapshot or select another exact model and request a fresh preflight.

The reviewer contract remains safe but demanding. It requests 18 semantic findings and six creative dimensions for each candidate, in at most 4,000 output tokens. Full-narrative evidence IDs for broad PASS claims and a terminal continuity suffix add some output burden. They do not require copying full text, and UNKNOWN is explicitly permitted. Current evidence does not prove that this burden caused earlier shallow responses; V5's 2,799-token response already gave generic repeated creative descriptions. Keep the evidence safeguards. A future valid response may use UNKNOWN and NO_CREATIVE_WINNER instead of forcing a PASS or winner.

## Repository and implementation verification

The current implementation uses the existing `STORY_REVIEW` role and `/api/v1/workflow/story-experiment/assessment-preflight` route. No endpoint, persistence workflow, scoring feature, or model-as-judge layer was added. The implementation fingerprints are in the preparation manifest.

The V5.1 checks remain present and were exercised by regression tests:

1. Candidate A's final catalog entry is `A10-6f1e177d2eddfff5`; Candidate B's is `B08-bf050df0590b2a67`.
2. Semantic `ending=PASS` must cite the final candidate passage. `ENDING_REPLAY` also requires the final passage.
3. `continuity=PASS` must cite a contiguous candidate suffix reaching the final passage.
4. `protected_events=PASS` and `trigger_conditions=PASS` must cite every candidate narrative span; source-anchor coverage alone is not enough.
5. IDs are validated against the bound catalog and the correct SOURCE/A/B document role. Cross-candidate evidence is rejected.
6. The model supplies individual outcomes; `semantic_summary` and aggregate eligibility are derived by the application.
7. UNKNOWN with empty references remains valid and yields `SEMANTIC_SOURCE_UNKNOWN`, not PASS.
8. `NO_CREATIVE_WINNER` is a valid research preference.
9. Evidence IDs establish catalog coverage and provenance only. They do not prove semantic interpretation, visual execution, or audience effect.
10. Research completion does not authorize source admission, prompt building, rendering, or official A+.

V5.1's coverage checks are deterministic guardrails, not semantic validators. They cannot decide whether an action means “removal,” whether an event is visually legible, or whether a candidate is creatively better.

## Reviewer instruction and creative comparison

The current system instruction now explicitly asks the reviewer to address, for each candidate, opening visual promise, concrete action changes and escalation, object-state continuity, character reactions, ending/payoff and replay motivation, and production executability. It asks for evidence-linked strengths, weaknesses, and risks for all six dimensions, and says to use UNKNOWN where support is absent. It also preserves the following controls:

- Each candidate is assessed independently against the approved source.
- Candidate A evidence may cite only A; Candidate B evidence only B.
- Protected source facts are locks; incidental staging is not.
- PASS requires source and candidate support; FAIL requires contradiction or a substantive omission with adjacent context.
- Full candidate narrative coverage is required for protected-events/rule-trigger PASS, and continuity PASS requires the terminal suffix.
- Material improvement needs a grounded change, visible consequence, addressed weakness, new risk, and materiality reason. Rewording, camera labels, or arbitrary timing changes do not qualify.
- Audience retention, render success, and official A+ cannot be inferred from text.

The authentic narratives provide the actual choreography to compare. Candidate A uses shake → clap/transfer → grab → sit/fold arms → sneeze. Candidate B uses pinch/peel → slap/transfer → shake arms → freeze/realize → stand still → sneeze. Those differences establish changed staging, not material creative improvement by themselves. The reviewer must explain consequences and risks relative to the original or report no material advantage/UNKNOWN.

A provenance caveat remains visible: both frozen candidates come from STOPPED historical generation runs. Candidate A's request identity was `deepseek-chat`, while the returned identity was `deepseek-flash`; that historical mismatch remains in the evidence. Candidate B's requested and returned identity were both `deepseek-flash`. Neither run is rewritten or promoted by this review preparation.

## Exact V6 bindings and request

The machine-readable manifest contains the full source, candidates, protected anchors, source/catalog provenance, exact wire payload, strict schema, canonical request, actual mocked SDK body, timeout policy, and calculated operation binding:

[STORY_REVIEW_V6_PREPARATION_MANIFEST.json](STORY_REVIEW_V6_PREPARATION_MANIFEST.json)

| Binding | SHA-256 |
|---|---|
| Original source story | `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d` |
| Candidate A | `50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088` |
| Candidate B | `4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739` |
| Exact-span evidence catalog | `5b15086899fc5c80f5de99a749fa3b70d47d32175a6a0ee0bcfdd8ab6f2273d7` |
| Protected-fact scope | `3c1440524dab311d2d25d5477ea87db3ddd4325e77c3c81367a8e9a1ac462d56` |
| System prompt | `23777f23fc982c82f27ba768c09328f07dda51d64bee44c5d3dc62ff1f9d2486` |
| User payload | `45d36b2d88f1e351d1bdf8cbe40439d44ee903d8b047c58e469e9c9be1c5c530` |
| Strict JSON schema | `b214f3c0047417f7ed8c06986dc1bc08446b33757d1c82dc8ffb2738f8f23467` |
| Canonical SDK request object | `396ac6fd5fd8f6161ab9a01c89f00d191764e260f517c785fa8dc3a6f694ee48` |
| Serialized body captured from SDK over mock transport | `de12941cdc7add9a55fd24193adf18d1aacabc805387844a8c6f261ce56d7258` |
| Full operation scope | `64f9755b9f75536c35fa30fe86d2a36bd9b6fe566d58b294d58efa884938476f` |

Candidate A's final passage is A10 (“Pip is relieved, but the cabinet remains messy.”); Candidate B's final passage is B08 (same final state). The 25-record catalog binds SOURCE, A, and B independently. Its source catalog file hash and current compiled Java authority hashes are also recorded in the manifest.

## Cost and token envelope

The configured model/rates were resolved from the current Compose configuration without printing configuration secrets. Those rates match OpenAI's published GPT-4o mini standard text pricing: **$0.15 per million input tokens and $0.60 per million output tokens**. The model documentation marks the pinned model and snapshot deprecated and lists Chat Completions, Structured Outputs, and a 128K context window. [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4o-mini), [OpenAI API pricing](https://developers.openai.com/api/docs/pricing).

- Exact serialized SDK body: **23,944 bytes**, within the existing 24,000-byte request cap by 56 bytes.
- Conservative input allowance used by the existing estimator: **24,944 tokens** (body bytes plus its 1,000-byte framing allowance). This is an upper-bound estimate, not actual tokenization.
- Maximum output: **4,000 tokens**.
- Estimated upper cost: **$0.0061416**.
- Rounded ceiling required by the existing reservation contract if separately authorized: **$0.006142**.
- Actual reservation/spend in this task: **$0.00**.

The old V5 cost ceiling was not reused. Any byte, model, prompt, catalog, schema, or scope change invalidates this exact preparation and requires a new preflight. The small 56-byte request margin makes scope changes particularly likely to exceed the envelope.

## Nonbillable preflight and regression evidence

- The existing ML assessment-preflight route returned HTTP 200. Its full result matched `story_assessment.preview` exactly before the planning-only rounded ceiling was attached.
- The actual installed OpenAI SDK serialized the full request through an explicit `httpx.MockTransport`. The mock asserted the Chat Completions URL, strict response schema, model, temperature, 4,000-token cap, timeout phases (5/5/10/60 seconds), and `max_retries=0`. No network transport to OpenAI was available in that test.
- The scope carries one fresh non-authorizing idempotency-scope identifier. No owner grant, spend reservation, paid run, or dispatch record was created.
- Focused ML review/contract/derived/transport tests: **182 passed**. These include mocked UNKNOWN, supported NO_CREATIVE_WINNER, schema, role isolation, evidence boundaries, aggregate derivation, refusal, timeout, retry-disabled, and authority-gate cases. Mock fixtures are tests only; this does not establish real reviewer quality.
- Java workflow, experiment contract, reviewer independence, and timeout tests: **50 passed** using disposable Testcontainers databases and a test-only in-process token.
- The complete ML suite previously reported **1,578 passed, 2 skipped, 1 failed** on this same V5.1 codebase. In this task, the single failure was rerun directly and reproduced: `test_family2_escalation.py::test_island_journal_escalation_is_not_applicable` returns `APPLICABLE` instead of the expected `NOT_APPLICABLE`. The failing test/parser files are outside this task's changes, and the prior full-suite result contains the same failure; classify it as a **reproducible pre-existing unrelated failure**, not a green suite. The full suite was rerun after the final instruction edit: **1,578 passed, 2 skipped, 1 failed**; the only failure is the same reproduced escalation applicability test.
- No source story, candidate text, historical finding, or canonical score changed.

## Historical and production integrity

- V5 remains `STOPPED`, one request, not accepted. Its raw response SHA remains `797732d070321ad5f50b35503bfab0d6ff073eae2aeb864d7722fb469649ea81`; preserved usage/cost remains 6,119 input tokens, 2,799 output tokens, **$0.00259725**.
- The historical SHA manifests still match: **275/275** and **164/164**, zero mismatches.
- No V1–V5 historical receipt, raw response, accounting, or verdict was rewritten. No production source admission, BUILD_PROMPT, image/video render, publication, grade activation, or official A+ activation was created.
- This task used a local in-process preflight route and a mocked SDK transport only. **Real provider calls: 0.**

## Remaining risks and next owner decision

A valid semantic PASS remains machine opinion, even when citation coverage passes. A valid creative verdict may be `MINOR_VARIATION`, `NO_MATERIAL_IMPROVEMENT`, `UNKNOWN`, or `NO_CREATIVE_WINNER`. The text review cannot validate 480p visual legibility, Seedance motion execution, or actual audience response. The 4,000-token output cap may encourage terse analysis or a length stop; UNKNOWN is an acceptable research result and must not be coerced to PASS.

**Recommendation:** do not dispatch this prepared request until the owner resolves the deprecated pinned-model choice. If retaining the pinned snapshot, separately authorize exactly one assessment-only request at a maximum **$0.006142**, with no retry/fallback. If choosing another model, request a new exact compatibility, pricing, and scope preflight first. This report and manifest create neither authorization.

## Required final statuses

- `V6_PREPARATION: READY`
- `NONBILLABLE_PREFLIGHT: PASS`
- `REVIEWER_MODEL_RECOMMENDATION: UNRESOLVED`
- `REAL_PROVIDER_CALLS: 0`
- `PAID_DISPATCH_AUTHORIZED: NO`
- `HISTORICAL_V5: STOPPED`
- `REAL_INDEPENDENT_REVIEW_ACCEPTED: NO`
- `PRODUCTION_SOURCE_ADMISSION: NOT_GRANTED`
- `BUILD_PROMPT_CALLS: 0`
- `VIDEO_RENDERS: 0`
- `OFFICIAL_CREATIVE_A_PLUS: INACTIVE`
