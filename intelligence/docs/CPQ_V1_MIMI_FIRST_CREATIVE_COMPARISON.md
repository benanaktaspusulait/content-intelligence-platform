# Mimi original versus development draft — diagnostic creative comparison

**Is the draft preferable to the original on the available text evidence? NOT_EVALUATED as an admitted paired machine comparison.** The owner authorized the bounded experiment. DeepSeek returned a complete structured response favoring the draft, but application evidence admission rejected it for two missing opposing-side citations/explanations. OpenAI was **NOT_EXECUTED**, as required by stop-on-first-failure authorization. No comparative machine evidence was admitted, and no verified improvement or grade is claimed. The raw DeepSeek conclusions remain retained separately and are disclosed below, with their limitations.

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

The real experiment used `PAIRWISE_CREATIVE_INSTRUCTIONS_V1` and `PAIRWISE_CREATIVE_RESPONSE_V1`. The response schema and admission rules remain unchanged. A later offline-only instruction clarification is versioned `PAIRWISE_CREATIVE_INSTRUCTIONS_V2`; it is not a replay or recovery of this failed experiment. Each of all six dimensions requires A_BETTER / B_BETTER / EQUIVALENT / INSUFFICIENT_EVIDENCE, correctly attributed literal excerpts, a concrete reason, weaknesses/risks, targeted suggestion when warranted and uncertainty. Empty evidence requires an explicit explanation. Overall judgment includes rationale, strongest difference, unresolved issue and recommendation-blocking regressions. Both ML schema/quotation checks and backend admission checks apply. Valid quotations establish attribution, not correctness. No source sentence mapping, numeric score or third synthesis call is required.

## Actual machine results: retained raw conclusions, NOT admitted evidence

Diagnostic review: `a1b2ce1e-e004-40c5-89e9-230f061554a3`.

- DeepSeek request `c8391e08-501f-4740-a32c-91f9481d13db`; provider response `8d8f1e2a-c1d2-4995-8b36-a039f4e39a36`.
- Provider/model: DeepSeek `deepseek-v4-pro`, configured reasoning none, maximum 6,000 output tokens; finish reason **stop**, API completion **COMPLETED**.
- Actual usage: **2,953 input + 2,175 output = 5,128 tokens**. Complete visible JSON: 10,046 characters. This was not an empty, truncated or reasoning-exhausted output.
- Calculated configured-rate upper cost: **$0.01251096**, using peak/cache-miss rates; actual provider invoice/debit is not exposed. No OpenAI usage or cost occurred. The $0.20 ceiling was a maximum/reservation, not an actual charge; unused authorization is not reused after the failure.
- Application state: **FAILED_OR_AMBIGUOUS**, category `PROVIDER_OR_RESPONSE_CONTRACT_FAILED`. Zero accepted diagnostic MACHINE_REVIEW evidence rows.
- OpenAI request `a781934f-72cc-4ca3-bec0-da5023d541be` remains **AUTHORIZED, NOT_EXECUTED**. This unspent immutable reservation is not permission to retry or resume; first-critic failure and current scope checks block execution, and dispatch is disabled.

A = exact development draft; B = exact original. The following table reports the **unchanged raw rejected response only**, not a validated independent result:

| Dimension | DeepSeek raw conclusion (rejected response) | OpenAI |
|---|---|---|
| SCROLL_STOP_VISUAL_PROMISE | A_BETTER; cites A only, fails two-sided evidence requirement | NOT_EXECUTED |
| CAUSAL_PROGRESSION | A_BETTER; cites A only, fails two-sided evidence requirement | NOT_EXECUTED |
| VISUAL_STORYTELLING | EQUIVALENT | NOT_EXECUTED |
| PRODUCTION_EXECUTABILITY | A_BETTER | NOT_EXECUTED |
| ENDING_REPLAY | EQUIVALENT | NOT_EXECUTED |
| DISTINCTIVE_CREATIVE_VALUE | EQUIVALENT | NOT_EXECUTED |

Raw overall judgment: **A_BETTER**. It attributes its preference to staging/causal clarity, consistent syntax and explicit coverage continuity. The strongest difference it names is readable eyes/mouth and maintaining note coverage through the mirror. It identifies missing verified character reference as unresolved. Its blockingRegressions array identifies no definite blocker, but flags possible static framing in A and mixed syntax in B. These are model opinions, not observed Seedance behavior.

### Exact rejection, responsibility and bounded instruction correction

Offline diagnosis of the byte-identical retained output confirms strict JSON Schema **PASS** and every provided quote's literal attribution **PASS**. Admission fails with:

`Comparative preference requires both sides or explicit missing-evidence explanation`

In SCROLL_STOP_VISUAL_PROMISE and CAUSAL_PROGRESSION, the model selects A_BETTER but supplies only A quotations and an empty absentEvidenceExplanation. References to B inside its prose reason do not replace supporting B excerpts. The other four dimensions contain both labels. This is not a source-citation range failure, an API completion failure or a budget failure.

The developer-authored V1 instructions requested A/B attribution but did not explicitly spell out this exact per-preference admission requirement. That instruction/validator mismatch contributed to the failure; it is not attributed solely to the model. The validator was not weakened and missing B citations were not invented or appended to the response.

The only correction is a shared reviewer-instruction paragraph, version **PAIRWISE_CREATIVE_INSTRUCTIONS_V2**, explicitly requiring a short literal excerpt from each side for a preference, or a concrete absent-evidence explanation; mentioning a side in prose does not substitute for quoting it. It also requires checking the full supplied text before asserting absence. The exact paragraph is persisted in future bound request inputs. The old V1 record, original raw response and its failure remain unchanged. Neither reviewed prompt nor the prepared blind packet was edited. No response was promoted or resubmitted, and no further inference is authorized by this correction.

### What the raw response does and does not support

- **Opening staging hypothesis:** it quotes A's “Make Mimi, the sticky note, and the toy cabinet easy to read together at the opening.” It contrasts B's hand close-up in prose, but omits a B supporting excerpt in that dimension. Therefore its preference is incomplete evidence, not a verified material improvement.
- **Causal finding contains an important factual weakness:** it recommends adding two-to-four-to-eight to B even though B already says “notes multiply from two to four to eight as she pulls”. Both prompts also use the same five timing windows. Its claims of uniquely explicit counts/temporal segmentation in A are not defensible differences.
- **Source repair versus staging:** A's unchanged coverage through mirror-to-sneeze implements the recorded owner meaning; it is primarily a fidelity/continuity clarification. Showing Mimi/note/cabinet together is a separate staging hypothesis. A machine preference for those instructions does not prove the source issue resolved independently or prove a better rendered opening.
- **Equivalent content:** the model calls storytelling, ending and distinctive value equivalent. Both retain the same mechanism and ending. There is no second critic, so agreement/disagreement between reviewers is **NOT_EVALUATED**.
- **Suggestions outside scope are rejected:** a note peeling from the cabinet after the ending would add an event, and a laugh-triggered multiplication rule would change the protected mechanism. Neither is adopted. Missing a new twist, gag or loop is not itself a failure of this task.
- **Longer versus clearer:** the unchanged draft has 342 whitespace-delimited words / 2,131 characters; the original has 301 words / 1,836 characters. The draft is longer. The model's “concise”/“simpler to parse” preference is an unverified format/clarity hypothesis, not evidence that Seedance will execute it better. Contact geometry, counts, mirror matching and the three-second ending remain unverified.
- **Unresolved contradiction:** the raw critique does not address whether “do not add another attempt” suppresses the pulls necessary for 2→4→8. No independent resolution is inferred from this omission.

**One targeted next creative change:** in a future explicitly requested revision, clarify that the existing 5–10s pulling escalation is permitted, while no additional attempt or doubling occurs after eight or during the mirror reaction. Do not add an event or timing window. Neither compared prompt was changed here.

Raw conclusions are at `cpq-draft-comparison-evidence/CRITIC_A-raw-visible-response.txt`; immutable durable rows, usage, application outcome and offline rejection diagnostic are separate files. Paid authorization was actually received; no creative-preference OWNER_DECISION was submitted in this experiment. The earlier owner interpretations and original source FAIL remain separate and unchanged.

## Purpose-specific model configuration, sizing and cost (authorized V1 experiment)

Official documentation was checked on 2026-10-16:

- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) supports `deepseek-v4-pro`, reasoning_effort `none` disabling thinking, JSON-object output and max_tokens.
- [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/) lists DeepSeek-V4-Pro-0813 and peak cache-miss $1.32/M input, $3.96/M output; these upper rates are retained even outside peak hours.
- [OpenAI GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) supports low reasoning, Chat Completions without tools and structured output. Configured rates retain the conservative $2.50/M cache-write input upper rate and $10/M output. No model switch or special processing tier is used.

| Reviewer | Exact profile/model | Effective configuration | Conservative calculated upper cost | Owner-authorized V1 ceiling |
|---|---|---|---|---|
| Critic A | deepseek-primary / DeepSeek `deepseek-v4-pro` | reasoning none; max_tokens 6,000; JSON object plus transmitted schema; zero SDK retries | $0.04149552 | $0.06 |
| Critic B | openai-escalation / OpenAI `gpt-6.1-sol` | reasoning low; max_completion_tokens 8,000, shared reasoning/visible budget; JSON Schema; zero SDK retries | $0.11359 | $0.14 |
| Combined | Maximum two requests, one per reviewer | No fallback, retry or synthesis; stop remaining calls on failure | $0.15508552 | **$0.20 total** |

Actual full request byte bound including schema and safety allowance: 13,436 input tokens per call under the conservative UTF-8-byte bound. Optional o200k estimates are approximately 2,796 DeepSeek-message and 3,183 OpenAI-message/schema tokens; this is not a verified tokenizer for those exact models. A concise complete six-dimension TEST_FIXTURE response measures 3,294 UTF-8 bytes / 826 o200k tokens; it tests shape and sizing, not creative quality. More detailed real responses and reasoning can be larger. No text was trimmed. Non-thinking DeepSeek and low-reasoning OpenAI with enlarged output allowance avoid copying the failed high-reasoning/4,000-token configuration, but completion remains unguaranteed.

Configured model/key availability is checked read-only before authorization; live inference availability remains UNVERIFIED_NO_PROVIDER_CALL. The former $0.12 estimate is superseded, not used as authorization. Actual experiment usage: **one DeepSeek request, 5,128 tokens, $0.01251096 configured-rate calculated upper cost**; no OpenAI dispatch.

## Tests, deployment and integrity

Focused implementation tests: 79 ML tests, 40 backend tests (including three diagnostic integration cases with disposable PostgreSQL) and 12 frontend tests passed. After the bounded V2 instruction clarification, all 80 focused ML tests and the three affected backend integration tests passed; frontend code was unchanged by that clarification. Three additional final diagnostic backend tests passed after strengthening actual-accounting/effective-configuration admission. Tests use exact two saved texts and clearly labelled TEST_FIXTURE judgments. They exercise exact binding, consent/auth rejection, no approved prompt/candidate creation, production-purpose isolation, reverse order mapping, all pairwise outcomes, absent evidence, bad quotations, failure retention, stop-on-failure and one-charge idempotency. Provider adapter tests intercept SDK calls entirely and verify exact effective reasoning/token parameters, schema mode, no tools and max_retries=0. The final disposable-DB run logged a scheduled-worker PostgreSQL EOF as the test database shut down; its three test methods had zero failures/errors and the process exited 0. This log is retained, not labelled a pre-existing failure. No full repository regression suite is claimed.

Deployment: **VERIFIED** via official deploy.sh, sequential frontend/backend/ML builds with disk checks. The owner explicitly authorized five exact old cache IDs: three publisher cache records (553.5 MB) were removed; two dependent npm records were not reclaimable by the targeted prune and remain. No other cache, image, volume, backup or user file was deleted. Host free space rose to approximately 1.8 GiB before release; each actual build began above 1.5 GiB. Docker also reported 48.6 GiB internal free space. The fresh pre-V67 dump was permission-protected and fully decoded before migration.

Docker engine became unavailable after frontend/backend release, before the ML build. Ordinary restart did not recover the stalled engine; Docker Desktop's normal `stop --force` and `start --detach` recovered it without a reset or data deletion. Only the five services that had previously been running were started with `--no-build --no-recreate`; previously stopped publishers remained stopped. The ML-only deployment then completed. No inference or diagnostic record existed during this interruption. Final host headroom is approximately 5.93 GiB.

Flyway V67 is applied; all 65 applied migration checksums were verified. Backend, ML, PostgreSQL and render-service are healthy; frontend is running with HTTP checks passed. Both real-dispatch flags remain false. Full historical pilot/request/evidence digests, Prompt 10, approved story and all compared artifacts are unchanged. Production source coverage is still 1/4 with the original FAIL; its critic gate remains blocked.

Live owner-authenticated preflight returned the exact two bound texts, reverse A/B versus B/A order, purpose-specific limits and calculated costs. Unauthenticated preflight returned 403. The actual browser Step 6 flow was tested: owner login, open diagnostic section and click “Inspect exact diagnostic pair (read only)”. Correct hashes/models appeared. Creation consent stayed unchecked and Create diagnostic record stayed disabled. At that pre-experiment browser checkpoint, database inventory remained three historical pilots, three historical requests and two historical evidence records; zero diagnostic reviews/authorizations/evidence were created. Browser inspection triggered no checkbox, reservation or execution. The later explicitly authorized API experiment is separately reported above. The screenshot is `cpq-draft-comparison-evidence/live-step6-diagnostic.png`.

Evidence: `cpq-draft-comparison-evidence/` holds focused logs, TEST_FIXTURE schema examples and offline sizing. The prepared blind packet, supervisor mapping and draft artifact remain unchanged. One explicitly authorized diagnostic record and two durable request authorizations were created. One provider execution occurred; zero accepted diagnostic evidence rows were created. The second authorization remained unexecuted.

## Final release verification after the real attempt

The minimal instruction V2 correction changed only the shared reviewer paragraph and its ML/backend instruction-version constants. Response schema, quote validator, reviewed prompt texts, production gate logic and Flyway schema did not change. No new framework, recovery operation or machine-evidence promotion was added. ML/backend were redeployed through deploy.sh with dispatch false, with no frontend rebuild for this correction.

Final live preflight reports `PAIRWISE_CREATIVE_INSTRUCTIONS_V2` and scope `269222e51b2de5ff3335863b6be24d8e5f77580c32ba5ef30329098f4e8d10b1`. The old experiment still reports instruction V1, the first request FAILED_OR_AMBIGUOUS, the second AUTHORIZED/NOT_EXECUTED and zero evidence rows. Full current pilot/request/evidence digests were compared before/after correction and remained equal. Historical original/source/owner evidence and all compared artifacts remain unchanged.

Final service checks: backend, ML, PostgreSQL and creative-render-service healthy; frontend running with HTTP checks passed. Both dispatch flags false; grading inactive; no render permission. Final host free space approximately 5.09 GiB. No more cleanup, inference or execution is performed.

Authoritative result: `cpq-draft-comparison-evidence/real-experiment-verification.json`. Failed-output diagnosis: `real-rejection-diagnostic.json`. Exact original durable responses/authorizations: `real-durable-requests.json`. Current instruction release verification: `instruction-v2-live-verification.json`. The screenshot `live-step6-diagnostic.png` documents the **pre-experiment** live Step 6 preflight, not successful machine evidence.

## Authorization, final readiness and limits

The owner explicitly authorized this exact V1 experiment with both prompt hashes, the two exact models/configurations, $0.06/$0.14 per-call ceilings and $0.20 total, maximum two requests, no retries/fallback/synthesis and stop-on-first-failure. The first real inference was executed through the official authenticated API and durable reservation/CAS; the second was stopped. Backend and ML dispatch were closed and verified false after the first response. There was no direct SDK experiment script or untracked charge.

The diagnostic path is VERIFIED for exact live binding, owner authorization, durable reservation, single dispatch, raw failure retention and safe rejection. This is **not a successful two-critic creative comparison**. The failed first real V1 review is not turned into accepted evidence. V2 instruction clarification is deployed and its live read-only preflight was verified; no real V2 inference or creative effectiveness is claimed for it. Its new scope digest differs from the preserved V1 experiment, so the failed history is not silently rebound to the revised instructions. No remaining budget or pending request is used automatically. Any later real V2 experiment needs fresh bounded human authorization.

- DIAGNOSTIC_PAIR_REVIEW_PATH: **VERIFIED** (deployed; failed real response safely retained; no successful pair claimed)
- CRITIC_A: **FAILED** (provider completed; application comparative-evidence contract rejected)
- CRITIC_B: **NOT_EXECUTED**
- COMPARATIVE_MACHINE_EVIDENCE: **NONE**
- OFFICIAL_CPQ_GRADING: **INACTIVE**
- RENDER_AUTHORIZED: **false**
- Original score: **88.40625/B_UNCHANGED**
- Source status: **original historical FAIL retained; draft UNKNOWN**
- Real provider requests: **1**, no retries/fallback/third synthesis.
- Calculated cost: **$0.01251096**; maximum authorization $0.20; actual invoice unobserved.
- REAL_DISPATCH: **DISABLED**
- No prompt rewrite, optimizer candidate, historical pilot mutation, source approval, creative-preference approval, grade activation, rendering, publication, commit or push.
