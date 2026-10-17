EXPERIMENT: REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1

EXACT_TWO_CANDIDATES_ENFORCED: YES
SOURCE_FIDELITY_PRE_REVIEW_GATE: VERIFIED
FULL_RESPONSE_DURABILITY: VERIFIED
DISPATCH_FINGERPRINT_ENFORCEMENT: VERIFIED

NEGATIVE_CONTRACT_TESTS: 31 ML contract tests plus 26 backend adversarial/control cases; see case inventory below
BACKEND_TESTS: 34 passed; 0 failures/errors/skips
ML_TESTS: 154 passed; 0 failures
DISPOSABLE_E2E: PASS

SOURCE_STORY_SHA: ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d
SOURCE_SCOPE_SHA: 05a5625b415331d2e625c28fa328bd6c0c9bfec5a93aaa77dbce9f5fc7703276
STORY_INSTRUCTION_SHA: f7e53b14f26b2608e6b075fec79ca63408df83aa759c001081a898e82cbf3d4a
REVIEW_TEMPLATE_SHA: 6cf3cf2c3b49929f7a4093ec07620191786af8357e3583f6cbca2c211cb689bb

STORY_MODEL: deepseek-chat
REVIEW_MODEL: gpt-4o-mini-2024-07-18

MAX_PLANNED_PROVIDER_CALLS: 2
RECOMPUTED_MAX_RESERVED_USD: 0.018914

REAL_PROVIDER_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0

PRODUCTION_DB_WRITES: 0
GIT_HISTORY_MODIFICATIONS_BY_AGENT: 0

OWNER_AUTHORIZATION: NOT_GRANTED
READY_FOR_FRESH_AUTHORIZATION: YES

# Four execution contracts repaired

The existing owner-scoped Story Evolution service, run/event ledger, real provider adapters and six-dimension STORY_REVIEW contract are reused. The strict behavior is enabled only by `experimentVersion=REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1`; legacy STORY generation retains its configured one-to-three-alternative behavior. Unknown experiment versions are rejected. No new service, scheduler, database, scoring framework or production deployment was introduced.

Implementation readiness is verified by the complete non-billable two-call contract integration. Real-model creative effectiveness remains unproven. The full dry-run proof is [REAL_STORY_EXPERIMENT_CONTRACT_DRY_RUN.json](REAL_STORY_EXPERIMENT_CONTRACT_DRY_RUN.json); all model responses and usage in that file are explicitly **mock-adapter contract data**, not real AI evidence or actual spending.

## 1. Exactly two valid candidates

**Root cause:** the generic STORY parser accepted one to three alternatives, while the backend advanced any nonempty filtered list.

**Fix:** the experiment-specific pre-review gate requires exactly two complete objects, distinct stable IDs, the versioned candidate schema, a 15-second duration declaration, cited opening/motivation/progression/ending, proposed changes, weaknesses, production risks and source mappings. Exact and near-identical narratives cannot count as independent candidates. The existing general story-evidence extractor supplies preliminary structural evidence; it does not award a canonical grade.

A result containing one valid and one invalid candidate remains preserved in its original response. The complete generation is insufficient for this experiment and cannot reserve the review request. There is no silent count reduction, regeneration, fallback or third call.

## 2. Protected-source gate without fabricated semantic PASS

**Root cause:** source checks were advisory; an unrelated Rex/Ada narrative could reach review because the backend checked only empty/equal text.

**Fix:** fresh authorization now binds exact approved-source anchor spans for character identity, central premise, physical rule, required continuity and ending. Each candidate must map every protected fact to an affirmative source-supported clause in its own narrative. The source text, offsets and binding identities are validated; absent claims, explicit nearby negation, unknown mappings and malformed declarations do not become supported facts. Unprotected prose and progression may differ materially; the baseline narrative is not frozen wholesale.

The outcomes remain separate:

| Outcome | Treatment |
|---|---|
| `SOURCE_COMPLIANT` | The bounded deterministic protected-text contract is established; candidate may proceed to independent review. |
| `PROTECTED_CHANGE_PROPOSAL` | Precise anchor-targeted change and justification are preserved for later owner consideration; excluded from this pilot's paid review. |
| `SOURCE_VIOLATION` | Silent absent/negated protected facts or invalid story content prevent review. |
| `UNKNOWN` | Unsupported protected mapping remains unresolved and prevents review. |

**Scope limitation:** this gate establishes exact protected textual facts, not unrestricted semantic fidelity. It never emits semantic PASS. Its `semanticFidelity` remains `UNKNOWN_REQUIRES_INDEPENDENT_REVIEW`; the independent reviewer must assess the complete narrative's meaning and contradictions. An unsupported model claim of compliance cannot bypass the deterministic gate. Conservative uncertainty about a paraphrased protected clause blocks this strict pilot rather than declaring that creative phrasing inherently invalid. The positive tests change unprotected wording and progression while retaining the short protected facts.

The preserved constraints and exact spans are visible in the repaired manifest, so the owner can examine the actual contract before authorization. The supplied source is the same P2 Pip story, not production Mimi Content 10.

## 3. Complete durable receipts and bounded recovery

**Root cause:** the full generation response lived in a local variable; durable events contained only completion summaries. A later parsing/review/worker failure could lose the authentic first response and usage. Generic HTTP errors could also incorrectly describe a local post-response rejection as pre-dispatch failure.

**Fix:** the strict role adapter returns a complete receipt after any possible provider dispatch. It records request/run/role identity, exact request binding, raw model text, available full SDK response object, parsed response when possible, provider/model metadata, finish reason, token usage, response SHA, timestamps, processing status, error details and billing classification. Received malformed or truncated text is preserved unchanged. Missing usage is not invented.

The backend commits a full `PROVIDER_RECEIPT` event and its progress projection in an independent `REQUIRES_NEW` transaction before another role may run. Before review it rereads the actual durable generation receipt and checks that its progress projection has not changed. Review candidates are built only from that receipt, with no generator-selected winner or self-assessment in the review payload. The complete response is retained even when no candidate is eligible.

Migration `V71__story_pilot_immutable_receipts.sql` extends the **existing** ledger with pilot-only immutability triggers and unique request/state keys. It adds no tables and updates no historical rows. Pilot authorization/source/deadline cannot be rewritten; receipt/reservation events cannot be updated/deleted. Historical non-pilot contracts remain unchanged. This migration ran only in disposable test databases during this task.

Billing/transport states distinguish never dispatched, uncertain transport, response received with known incurred cost, locally rejected received response, accepted candidates and completed independent review. Known cost is retained even after local rejection. Unknown usage or ambiguous transport remains unresolved and cannot release budget for an automatic replacement.

A worker exit after durable receipt leaves a non-READY run; restart does not replay generation or automatically issue review. Receipt hashes, current scope, budget and a fresh explicit authorization remain necessary for any later recovery/execution. The provider-free validation endpoint can inspect saved alternatives without constructing a provider or incurring charges. This task implements no automatic paid resume path.

## 4. Authorization and dispatch-time bindings

**Root cause:** preparation hashes did not constrain the actual role dispatch.

**Fix:** the authenticated-owner preflight compiles the current source scope and both role bindings. The source hash covers the story ID/revision/text, owner approval, analysis, production settings, protected anchors and canonical diagnosis. The exact grant binds two ordered roles, providers/models, current configured prices, instruction hashes, schema versions, output/input bounds, reservations, retry/fallback settings and implementation checksum. `POST` independently recomputes the preflight; altered scope or limits cannot create a run or reserve budget.

Before each reservation the worker rechecks persisted source/analysis/settings, current role preflight, request order, remaining budget, cancellation and deadline. The ML boundary checks the same binding again before provider construction and rejects fixture fallback. Pilot inference requires the backend's HMAC signature. Unexpected provider/model/transport receipts cannot authorize review.

The exact future reviewer payload is **not invented at preparation**. Authorization binds its fixed template/model/schema and the 24,000-byte input envelope. After authentic generation is durably saved, the worker builds the two-candidate review request, computes its final payload SHA, records it with the specific durable reservation and revalidates the candidates before dispatch.

Both the effective sent JSON and its fingerprint use the same canonical object-key ordering. PostgreSQL JSONB key reordering therefore cannot create a false scope mismatch; a dedicated metamorphic test verifies this. Real content/instruction changes still stop execution as `SCOPE_OR_INSTRUCTION_MISMATCH`.

## Integrated evidence and adversarial cases

The test uses disposable PostgreSQL, the actual `StoryEvolutionService`/owner checks/ledger transactions, current schema migration and actual FastAPI role/preflight/validation routes with signed in-process HTTP. Only the provider adapters are mocked. Owner principals use Spring mock requests; this is not a claim that a production browser login or real provider was exercised. Source-reader fixtures use the saved P2 story/approval/analysis inputs and exact production settings.

The positive trace is:

```text
Authenticated owner-scoped exact grant
→ source/model/instruction preflight
→ immutable authorization
→ STORY reservation + final request binding
→ mocked SDK response through the real parsing/accounting boundary
→ durable complete STORY receipt: CANDIDATES_ACCEPTED
→ reread durable candidates + deterministic protected-source gate
→ final STORY_REVIEW payload SHA + bounded reservation
→ mocked independent reviewer through the real review validator
→ durable complete review receipt: INDEPENDENT_REVIEW_COMPLETED
→ RESEARCH_COMPLETE_OWNER_REVIEW_REQUIRED
→ ownerStoryApproval=PENDING; no prompt creation or BUILD_PROMPT
```

The mock reviewer returns `NO_CREATIVE_WINNER`; the integration preserves that answer instead of selecting the least bad candidate. The trace's synthetic token/cost figures test accounting only. Actual new provider calls and spending are both zero.

The 27 backend pilot cases cover the complete positive path and 26 adversarial/control cases: zero/one/three alternatives, duplicate IDs/text, incomplete fields, unrelated source, unknown fidelity, explicit protected-change proposal, malformed first response, missing usage, over-budget usage, unexpected fixture transport, reviewer timeout/connection error/malformed response, exception after durable receipt, actual interrupted RUNNING worker followed by restart, uncertain first dispatch followed by attempted reprocessing, cancellation, candidate mutation after persistence, immutable receipts/grant and denied third call, changed instruction/model before reservation, missing owner/excessive request count, and stale source or modified budget.

The focused ML suite additionally tests near-identical narratives, both Rex and Ada examples, exact count handling, supported creative variation, protected-change classification, negation, model/price/source/instruction drift, fixture fallback, unsigned pilot HTTP traffic, truncated response and JSONB-order invariance. These are contract tests, never evidence that AI generated a creatively superior story.

Verification commands and final results:

- `mvn -q -Dtest=StoryExperimentContractTest,StoryEvolutionServiceTest,StoryReviewIndependenceTest test`: **34 passed, 0 failures/errors/skips**. Pilot integration: 27; existing Story Evolution: 5; independence: 2.
- Focused ML suites (pilot contract, story review, creative roles, adaptive policy, creative validity, F8, hook stability and provider adapters): **154 passed**.
- Existing datetime/Gemini deprecation and JVM instrumentation warnings remain unrelated.
- `git diff --check`: passed.

Earlier failures were corrected rather than skipped: noncanonical JSON ordering caused a genuine false fingerprint mismatch; the test evidence writer needed Java-time serialization; the test bridge repeatedly importing the application made the first broad run unnecessarily slow. The final bridge reuses one imported application process. One intermediate run observed deliberate implementation-file changes while tests were active and correctly stopped those grants; the final frozen-code run passed completely in seconds.

## Recomputed scope and cost

The exact current output is [REAL_STORY_EXPERIMENT_REPAIRED_MANIFEST.json](REAL_STORY_EXPERIMENT_REPAIRED_MANIFEST.json). It contains the complete source scope, protected spans, effective generation request, reviewer template and an **unsigned/disabled authorization template**.

| Role | Provider/model | Input / output USD per million | Output bound | Calculated request upper bound | Reservation |
|---|---|---|---|---|---|
| STORY | DeepSeek `deepseek-chat` | 0.30 / 1.20 | 4,000 | $0.00945660 | $0.009457 |
| STORY_REVIEW | OpenAI `gpt-4o-mini-2024-07-18` | 0.15 / 0.60 | 4,000 | $0.00679005 | $0.009457 |

The exact generation payload is 10,221 UTF-8 bytes. The calculation also includes its actual system bytes, a 1,000-byte framing margin and 4,000 output tokens. Review is conservatively priced at the enforced 24,000-byte maximum because authentic candidates do not yet exist. The sum of calculated request upper bounds is $0.01624665. The existing equal-split ledger needs two rounded reservations of $0.009457, giving **$0.018914** total.

The former $0.017966 is historical preparation evidence. The new difference, **$0.000948**, is not authorized and was not applied to a production budget. The new manifest explicitly marks the changed envelope as requiring owner approval. Rates are current configured role rates, not a claim of an invoice or a provider-availability test.

Fingerprints:

- Source story: `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d`.
- Full source scope: `05a5625b415331d2e625c28fa328bd6c0c9bfec5a93aaa77dbce9f5fc7703276`.
- STORY instructions: `f7e53b14f26b2608e6b075fec79ca63408df83aa759c001081a898e82cbf3d4a`.
- STORY serialized effective request: `9911fb57fc276c6631bcb1aea4378024a55cf00388509fd63b0dc83cb77813e1`.
- STORY_REVIEW instructions: `6174f28d352b98d084ffa6cac3112f8282596a25b0e5a10168f30984785c4606`.
- STORY_REVIEW fixed template: `6cf3cf2c3b49929f7a4093ec07620191786af8357e3583f6cbca2c211cb689bb`.
- Implementation: `5e0dd06481c8c1bc1f0cd1515b489d578178517bafe0d85dbffe9421645e4535`.
- Actual future review-payload fingerprint: **NOT_CREATED_UNTIL_DURABLE_STORY_RECEIPT**.

The existing preparation script now supports `--repaired-contract`. It recomputes the bindings from current configured roles and the exact tested source scope, checks them against the complete integration evidence and stops on mismatch. It does not construct a provider, authorize a run or modify a database. The historical manifest was retained.

## Precise fresh authorization required

A future owner authorization must explicitly approve `REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1`, the source and instruction/template/implementation fingerprints above, one DeepSeek `deepseek-chat` STORY call and one independent OpenAI `gpt-4o-mini-2024-07-18` STORY_REVIEW call, at most 4,000 output tokens and **$0.009457 per call / $0.018914 total**, one round and 600 seconds, with no retry, fallback, model substitution or third call. It must acknowledge the exact protected-anchor contract and keep story approval, BUILD_PROMPT, image/video generation, publishing and official A+ activation outside scope.

No paid confirmation is inferred from this repair request. No previous inference authorization may be reused. Any changed fingerprint, configured rate, model, source binding or cost requires a fresh exact preflight and authorization. Provider live availability remains unprobed. The current production service was not deployed or enabled; any later execution must use an explicitly authorized environment containing this repaired code and the existing saved subject.

## Files and integrity

Primary changes: `ml-service/app/workflow/story_experiment.py` (helper inside the existing role flow), `creative_roles.py`, `api.py`, the two existing text-provider adapters, `backend/.../StoryEvolutionService.java`, `WorkflowController.java`, `QualityMlClient.java` and the pilot-only V71 ledger migration. Tests are `test_story_experiment_contract.py`, the mock adapter bridge/fixture helpers and `StoryExperimentContractTest.java`. No scoring or creative-evaluator implementation changed.

Initial observed HEAD: `2a6196469b7267ef6f299c932bc4de63e2c80268`; later external HEADs included `0a8568af56f36ddcb445471b0dced6b7c9e60411`; final observed HEAD before this report: `03a5faeb5904f2644f86d9555b211e79fa0e74f0`. The external Auto process committed working changes while the task ran. This agent issued no commit, amend, reset or push and did not alter or stop unrelated processes. No production database, historical analysis, original source, Prompt v10, render gate or canonical Ruleset 1.11 record was modified.

There are no remaining blockers to requesting fresh authorization for this exact tested contract. This does not establish creative success, semantic source approval, visual feasibility, an A/A+ grade or permission to render. The task stops here with zero paid calls and owner authorization **NOT_GRANTED**.
