# Mimi original versus development draft — diagnostic creative comparison

**Is the draft preferable to the original on the available text evidence? NOT_EVALUATED.** Neither of the two diagnostic machine critics has run. No comparison winner, calibrated grade or independently verified improvement is reported. The diagnostic path is deployed and verified through the live authenticated API and actual Step 6 browser. A single consolidated paid authorization is now being requested; none has been received for this experiment.

Date: 2026-10-16. This report supersedes the earlier preparation-only blocker description. The two compared texts, existing blind packet and supervisor mapping are unchanged.

## Exact subjects and live binding

| Subject (supervisor only) | SHA-256 | Provenance |
|---|---|---|
| Original | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` | Content 10, immutable Prompt 10/version 1, analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18` |
| Development draft | `82a2d896798076cb3fd3cf88482c5709167d88034a8b6702149f000bc690abef` | Exact body of `CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V1.txt`, after `PROMPT BODY` and its blank separator, excluding the external settings wrapper and final file newline; DRAFT_ONLY |
| Approved story (provenance only) | `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b` | Persisted approved story, unchanged |

The original was read directly from live PostgreSQL `prompt_versions.id=10`, its version checked as 1 and its complete text compared byte-for-byte with the prepared packet. This no longer relies only on the earlier fixture projection. Backend preflight independently resolves the existing `CreativePromptQualityService.pilotSubject` against persisted analysis/story/settings and verifies the expected original/draft/story fingerprints. It never removes the original's AUTO footer or normalizes prompt text. The packaged draft resource is a fixed exact copy of the prepared artifact; there is no caller-controlled file path.

Shared authoritative context: ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15 seconds / image2video / 480p / 9:16. Both critics receive this same external context, explicitly authoritative over embedded historical metadata. Draft authorship is the development workflow in this Codex conversation; its exact authoring model is not recorded. No production optimizer execution or provider request is invented for it.

## Diagnostic purpose and boundaries

`DRAFT_COMPARATIVE_REVIEW_V1` asks only which of two exact production specifications is clearer/stronger on paper and what trade-offs remain. Original source fidelity remains the separately recorded FAIL; draft fidelity remains UNKNOWN. Those results do not prevent a diagnostic textual critique and are not disclosed to critics. Diagnostic evidence cannot satisfy sourceGate, qualification, approval, calibration or F8.

The implementation reuses owner sessions/CSRF, `cpq_owner_pilots`, `cpq_machine_requests`, `cpq_pilot_evidence`, `QualityMlClient`, the existing signed CPQ ML execute transport, `CreativeCapabilityProvider` and existing usage accounting. Flyway V67 only extends the existing pilot policy CHECK to admit this second exact purpose. Immutable historical records/triggers are unchanged. Production pilot access explicitly selects its original policy; diagnostic routes explicitly select the new policy. A caller's label cannot switch purposes or bypass production gates.

Read-only GET `/api/v1/intelligence/workflow/cpq/draft-review/preflight` authenticates the owner, validates exact bindings, estimates actual request costs and returns no persisted record. Explicit authenticated POST creation requires exact scope digest and record-creation consent; creation is reserved for the later authorized experiment. Authorizations bind exact scope, slot/profile/model/reasoning/tokens/cost, diagnostic-only consent and durable idempotency key. Execution uses durable CAS before transport, at most one request per fixed reviewer, no retries or fallback. Critic B requires a completed Critic A; any failed/ambiguous call stops remaining dispatch. A successful first review remains immutable if the second fails. Raw outputs, usage and failures remain retained even when no machine evidence is accepted.

A small diagnostic section is added to the existing Step 6 owner pilot component. Inspection is read-only, creation/authorization/execution are distinct explicit actions, and production pilot state is separate. Navigation does not create records, authorizations or inference.

## Blind request and response contract

The prepared two complete prompt bodies are reused verbatim. A remains the draft, B the original, in supervisor metadata only. Critic A receives A then B; Critic B receives B then A. Per-reviewer input snapshots and the label-to-hash mapping are persisted separately from provider messages. There is no other critic output, score, source verdict, owner interpretation, author review, popularity data, desired grade or intended winner in provider input. Prompt wording can reveal likely provenance; perfect blindness is not claimed.

Versions: `PAIRWISE_CREATIVE_INSTRUCTIONS_V1` and `PAIRWISE_CREATIVE_RESPONSE_V1`. Each of all six dimensions requires A_BETTER / B_BETTER / EQUIVALENT / INSUFFICIENT_EVIDENCE, correctly attributed literal excerpts, a concrete reason, weaknesses/risks, targeted suggestion when warranted and uncertainty. Empty evidence requires an explicit explanation. Overall judgment includes rationale, strongest difference, unresolved issue and recommendation-blocking regressions. Both ML schema/quotation checks and backend admission checks apply. Valid quotations establish attribution, not correctness. No source sentence mapping, numeric score or third synthesis call is required.

## Actual machine results

| Dimension | Critic A: DeepSeek | Critic B: OpenAI |
|---|---|---|
| SCROLL_STOP_VISUAL_PROMISE | NOT_EVALUATED | NOT_EVALUATED |
| CAUSAL_PROGRESSION | NOT_EVALUATED | NOT_EVALUATED |
| VISUAL_STORYTELLING | NOT_EVALUATED | NOT_EVALUATED |
| PRODUCTION_EXECUTABILITY | NOT_EVALUATED | NOT_EVALUATED |
| ENDING_REPLAY | NOT_EVALUATED | NOT_EVALUATED |
| DISTINCTIVE_CREATIVE_VALUE | NOT_EVALUATED | NOT_EVALUATED |

Raw comparative conclusions, agreement/disagreement, supporting excerpts, preferred text, regressions and whether extra length buys actual clarity: **NOT_EVALUATED**. These cells are not filled with author-side judgments or TEST_FIXTURE conclusions.

Review focus, not a machine conclusion: distinguish the owner's continuity clarification from genuinely improved opening staging; unchanged mechanism/ending from stronger execution; unnecessary verbosity from useful constraints. One targeted creative issue to inspect after real evidence: whether “do not add another attempt” conflicts with the pulls necessary for 2→4→8. Neither prompt is edited in this task.

## Purpose-specific model configuration, sizing and cost

Official documentation was checked on 2026-10-16:

- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) supports `deepseek-v4-pro`, reasoning_effort `none` disabling thinking, JSON-object output and max_tokens.
- [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/) lists DeepSeek-V4-Pro-0813 and peak cache-miss $1.32/M input, $3.96/M output; these upper rates are retained even outside peak hours.
- [OpenAI GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) supports low reasoning, Chat Completions without tools and structured output. Configured rates retain the conservative $2.50/M cache-write input upper rate and $10/M output. No model switch or special processing tier is used.

| Reviewer | Exact profile/model | Effective configuration | Conservative calculated upper cost | Proposed authorization ceiling (NOT authorized) |
|---|---|---|---|---|
| Critic A | deepseek-primary / DeepSeek `deepseek-v4-pro` | reasoning none; max_tokens 6,000; JSON object plus transmitted schema; zero SDK retries | $0.04149552 | $0.06 |
| Critic B | openai-escalation / OpenAI `gpt-6.1-sol` | reasoning low; max_completion_tokens 8,000, shared reasoning/visible budget; JSON Schema; zero SDK retries | $0.11359 | $0.14 |
| Combined | Maximum two requests, one per reviewer | No fallback, retry or synthesis; stop remaining calls on failure | $0.15508552 | **$0.20 total** |

Actual full request byte bound including schema and safety allowance: 13,436 input tokens per call under the conservative UTF-8-byte bound. Optional o200k estimates are approximately 2,796 DeepSeek-message and 3,183 OpenAI-message/schema tokens; this is not a verified tokenizer for those exact models. A concise complete six-dimension TEST_FIXTURE response measures 3,294 UTF-8 bytes / 826 o200k tokens; it tests shape and sizing, not creative quality. More detailed real responses and reasoning can be larger. No text was trimmed. Non-thinking DeepSeek and low-reasoning OpenAI with enlarged output allowance avoid copying the failed high-reasoning/4,000-token configuration, but completion remains unguaranteed.

Configured model/key availability is checked read-only before authorization; live inference availability remains UNVERIFIED_NO_PROVIDER_CALL. The former $0.12 estimate is superseded, not used as authorization. Actual provider usage/cost so far: **0 / $0.00**.

## Tests, deployment and integrity

Focused local tests: 79 ML tests, 40 backend tests (including three diagnostic integration cases with disposable PostgreSQL) and 12 frontend tests passed. Three additional final diagnostic backend tests passed after strengthening actual-accounting/effective-configuration admission. Tests use exact two saved texts and clearly labelled TEST_FIXTURE judgments. They exercise exact binding, consent/auth rejection, no approved prompt/candidate creation, production-purpose isolation, reverse order mapping, all pairwise outcomes, absent evidence, bad quotations, failure retention, stop-on-failure and one-charge idempotency. Provider adapter tests intercept SDK calls entirely and verify exact effective reasoning/token parameters, schema mode, no tools and max_retries=0.

Deployment: **VERIFIED** via official deploy.sh, sequential frontend/backend/ML builds with disk checks. The owner explicitly authorized five exact old cache IDs: three publisher cache records (553.5 MB) were removed; two dependent npm records were not reclaimable by the targeted prune and remain. No other cache, image, volume, backup or user file was deleted. Host free space rose to approximately 1.8 GiB before release; each actual build began above 1.5 GiB. Docker also reported 48.6 GiB internal free space. The fresh pre-V67 dump was permission-protected and fully decoded before migration.

Docker engine became unavailable after frontend/backend release, before the ML build. Ordinary restart did not recover the stalled engine; Docker Desktop's normal `stop --force` and `start --detach` recovered it without a reset or data deletion. Only the five services that had previously been running were started with `--no-build --no-recreate`; previously stopped publishers remained stopped. The ML-only deployment then completed. No inference or diagnostic record existed during this interruption. Final host headroom is approximately 5.93 GiB.

Flyway V67 is applied; all 65 applied migration checksums were verified. Backend, ML, PostgreSQL and render-service are healthy; frontend is running with HTTP checks passed. Both real-dispatch flags remain false. Full historical pilot/request/evidence digests, Prompt 10, approved story and all compared artifacts are unchanged. Production source coverage is still 1/4 with the original FAIL; its critic gate remains blocked.

Live owner-authenticated preflight returned the exact two bound texts, reverse A/B versus B/A order, purpose-specific limits and calculated costs. Unauthenticated preflight returned 403. The actual browser Step 6 flow was tested: owner login, open diagnostic section and click “Inspect exact diagnostic pair (read only)”. Correct hashes/models appeared. Creation consent stayed unchecked and Create diagnostic record stayed disabled. Database inventory remained three historical pilots, three historical requests and two historical evidence records; zero diagnostic reviews/authorizations/evidence were created. No checkbox, reserve or execute action was triggered. The screenshot is `cpq-draft-comparison-evidence/live-step6-diagnostic.png`.

Evidence: `cpq-draft-comparison-evidence/` holds focused logs, TEST_FIXTURE schema examples and offline sizing. The prepared blind packet, supervisor mapping and draft artifact remain unchanged. No production diagnostic record, authorization or evidence has been created.

## Authorization boundary and current status

Deployment/live verification is complete. Request one consolidated human authorization binding these exact subject fingerprints, diagnostic-only purpose, record creation, the two exact providers/configurations, $0.06/$0.14 ceilings, $0.20 combined, maximum two calls, zero retries/fallback/synthesis and no source PASS, prompt approval, grading or render permission. This implementation instruction is not paid authorization. Continue this same task if that approval is supplied; do not ask for another development prompt.

- DIAGNOSTIC_PAIR_REVIEW_PATH: **VERIFIED** (paid execution awaiting explicit authorization)
- CRITIC_A: **NOT_EXECUTED**
- CRITIC_B: **NOT_EXECUTED**
- COMPARATIVE_MACHINE_EVIDENCE: **NONE**
- OFFICIAL_CPQ_GRADING: **INACTIVE**
- RENDER_AUTHORIZED: **false**
- Original score: **88.40625/B_UNCHANGED**
- Source status: **original historical FAIL retained; draft UNKNOWN**
- No prompt rewrite, optimizer candidate, historical pilot mutation, provider inference, production approval, grade activation, rendering, publication, commit or push.
