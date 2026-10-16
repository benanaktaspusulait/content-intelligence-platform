ENVIRONMENT: DEDICATED_DISPOSABLE_REAL_PROVIDER
PREPARATION_ONLY: YES

P2_BASELINE_RECONSTRUCTED: YES
STORY_SHA_MATCH: YES
PROMPT_SHA_MATCH: YES
SETTINGS_SHA_MATCH: YES

REAL_RULESET_VERSION: 1.11
BASELINE_NUMERICAL_SCORE: 93.42708333333334
BASELINE_NUMERICAL_GRADE: A

CREATIVE_VALIDITY_STATUS: CREATIVE_RISK_DETECTED / PROVISIONAL_CREATIVE_VALIDITY_REQUIRED
FINAL_CANONICAL_A_ADMITTED: false

PRODUCTION_DATABASE_ISOLATED: YES
PRODUCTION_DATABASE_WRITES: 0

DEEPSEEK_ADAPTER_READY: YES
OPENAI_ADAPTER_READY: YES
FIXTURE_FALLBACK_DISABLED: YES

GENERATOR_REVIEWER_INDEPENDENCE: VERIFIED
ACTUAL_REVIEW_EXECUTION: NOT_EXECUTED

RESEARCH_ELIGIBILITY: ELIGIBLE_FOR_EXPLICIT_OWNER_AUTHORIZATION
SOURCE_SCOPE_SHA: 962dd2d754dfed207f8f5d5fdee7fdf48fded3b34d08fe7f848a1649614ac613
INSTRUCTION_CONTEXT_SHA: a16599a2f0a0be747185490dd15d7eced8e1d08c6cf0c091f512a0fca06a1a67

MAX_PLANNED_REQUESTS: 6
RECOMPUTED_HARD_CAP_USD: 0.675625

REAL_PROVIDER_REQUESTS: 0
ACTUAL_PROVIDER_SPEND_USD: 0

OWNER_AUTHORIZATION_FOR_EXECUTION: NOT_GRANTED
READY_FOR_AUTHORIZATION: YES

# Prepared environment

The dedicated preparation mode reuses the existing disposable Spring HTTP acceptance application, PostgreSQL Testcontainers schema, authenticated owner workflow, story-evolution worker, BUILD_PROMPT path, Ruleset 1.11 evaluator, creative-validity-v1 projection, optimization ledger and provider adapters. It does not modify Content 10, Prompt 10 or the production database.

The successful run is retained under `intelligence/backend/target/disposable-owner-http/run-oT9HS7`. It contains a PostgreSQL custom-format snapshot, the disposable owner credential with mode `0600`, a separate two-provider credential file with mode `0600`, the redacted execution manifest, the exact-endpoint network policy and all HTTP/no-egress evidence. Secrets are not copied into this report or logs. The snapshot was restored into a second fresh PostgreSQL 17 container: Flyway version 70, one content, two prompt versions, twelve workflow records, the exact story and analysis IDs present, and zero optimization runs or requests.

Baseline construction used `DETERMINISTIC_FIXTURE` only for the historical STORY, STORY_REVIEW and BUILD_PROMPT responses. Those responses went through the normal authenticated HTTP/business workflow and existing validators. The fixture process was terminated after reconstruction. The sealed experiment operations all state `transportOrigin=REAL_PROVIDER_ADAPTER`, `providerAdapter=CreativeCapabilityProvider`, `fixtureFallbackAllowed=false`, and `providerDispatched=false`. The future launcher rejects fixture environment variables before DNS or SDK use.

# Reconstructed immutable evidence

| Binding | Current disposable value |
|---|---|
| Content | `1` |
| Approved story | `ca40c11a-7831-476e-9f50-646a61a1ec9c` |
| Story revision | `candidate-1-revision-04c8c36b` |
| Story approval | `af738239-99c3-4a9e-90b5-a1bee4295cd0` |
| Prompt version | `2` |
| Analysis | `10fc4c38-7cdf-4f71-b8dc-05b14315352a` |
| Production settings | `2f0a8a7b-7372-471e-bb36-0f4b3eaeb9e1` |
| Approved story SHA-256 | `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d` |
| Prompt SHA-256 | `1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5` |
| Settings SHA-256 | `e6aedfab391d7ee0a7e753b3dc8f4e8d57c31d8b2ada4b9f8b130b95b2689937` |

The actual Ruleset 1.11 result is `93.42708333333334/A`. Creative validity remains `CREATIVE_RISK_DETECTED`, with final qualification `PROVISIONAL_CREATIVE_VALIDITY_REQUIRED` and provenance `DETERMINISTIC_FIXTURE`. Numerical A therefore does not establish real-model creative quality or final admission. Independent semantic/visual evidence and all render gates remain unresolved.

# Current request bindings

The generation system SHA remains the historical `41e590871450708bd59f94041efeb6fe8e1253847a8c4e3560db90ce10c0696b`, and the response-schema SHA remains `09678f0396e1c8e8034eb22bd71d9b8bfaf7a87b76f30c44195783b0b7f06a04`. The complete generation instruction-context SHA is now `a16599a2f0a0be747185490dd15d7eced8e1d08c6cf0c091f512a0fca06a1a67`, rather than historical `91561d8983a38b0d247451e8f1d22fc3051145a6b3ca1308a4b196f326959a3f`.

This difference is explicit and requires fresh authorization. The new context contains fresh disposable record IDs and now binds the target-aware research-eligibility snapshot into the saved source scope. The worker recompiles and compares this scope plus every system, user-payload, schema, instruction-context, model, effort, token and cost field before it can reserve a request. The source-scope SHA consequently changed from the historical P3 value to `962dd2d754dfed207f8f5d5fdee7fdf48fded3b34d08fe7f848a1649614ac613`. No previous authorization is reusable.

# Provider plan and cost ceiling

Both credentials are present in the private experiment-scoped file. This establishes configuration readiness only. Live provider availability remains `UNVERIFIED_NO_PROVIDER_CALL`; no connectivity probe or inference was made.

| Run / role | Profile and model | Reasoning | Output cap | Conservative input bound | Hard cap USD |
|---|---|---:|---:|---:|---:|
| A generation | `deepseek-primary / deepseek-v4-pro` | none | 4,000 | 55,217 | 0.088727 |
| A source fidelity | `openai-escalation / gpt-6.1-sol` | low | 4,000 | 37,272 | 0.133180 |
| A critic | `openai-escalation / gpt-6.1-sol` | low | 4,000 | 40,522 | 0.141305 |
| B generation | `openai-escalation / gpt-6.1-sol` | low | 4,000 | 55,217 | 0.178043 |
| B source fidelity | `deepseek-primary / deepseek-v4-pro` | none | 4,000 | 37,272 | 0.065040 |
| B critic | `deepseek-primary / deepseek-v4-pro` | none | 4,000 | 40,522 | 0.069330 |

Run A is capped at USD `0.363212`; Run B at USD `0.312413`; total at USD `0.675625`. There are at most six requests and 24,000 aggregate output tokens, one generation plus two cross-model reviews per run, 120 seconds per request and 600 seconds per run. Retries and fallback are disabled. The increase of USD `0.000700` over P3 follows from the newly bound generation context and current serialization; the old ceiling was not reused or silently increased.

DeepSeek uses the checked-in `https://api.deepseek.com` JSON-object profile and OpenAI uses `https://api.openai.com/v1` strict JSON-schema profile. The execution launcher derives these exact origins from the reviewed catalog, rejects a changed catalog, resolves only those names, permits only their port 443 addresses and loopback bind, and denies every other outbound DNS/socket target. The preparation HTTP run separately proved external `:443` and production-loopback `:5432` denial with no unexpected attempts. No production DB or production API credential is present in the experiment artifacts.

# Non-billable verification

- ML optimization/provider contract: **42 passed**. The preview proves identical generator context across providers, no dispatch, real adapter origin and no fixture fallback.
- Backend bounded ledger: **17 passed** on disposable PostgreSQL. This covers missing/incomplete grants, current target eligibility, changed scope/prompt binding, changed model, changed instruction context, changed transport origin, changed cost ceiling, request budgets, idempotency, cancellation, uncertain accounting and no research prompt approval.
- Real disposable HTTP `--real-provider-preflight`: **passed**. It recreated and approved the exact source, persisted the prompt, ran Ruleset 1.11 and creative-validity-v1, produced the two-run plan, denied unauthorized dispatch and recorded zero provider/image/render calls and zero production writes.
- Snapshot restore: **passed** in a second isolated PostgreSQL container. Exact story and analysis IDs were present; optimization run/request counts remained zero.
- Syntax/static checks: shell syntax, Python compilation and `git diff --check` passed.

The preparation command is `./intelligence/scripts/prepare-disposable-real-provider-experiment.sh`. Its default path reruns both focused suites and the HTTP acceptance before producing a new sealed scope. The original fixture-only acceptance modes remain unchanged.

# Fresh execution authorization required

Execution may proceed only after the owner explicitly authorizes `REAL_MODEL_A_CAPABILITY_RESEARCH_V1` in this dedicated disposable environment against the exact current IDs and SHA-256 values above:

- Run A: DeepSeek generation and OpenAI source-fidelity/critic review, maximum USD `0.363212`.
- Run B: OpenAI generation and DeepSeek source-fidelity/critic review, maximum USD `0.312413`.
- Combined maximum: six calls and USD `0.675625`.
- 4,000 output tokens per request, 120-second request timeout, 600-second run deadline.
- Stop the affected run on failure, ambiguity, incomplete accounting, binding change, contract failure or review failure; no retry, fallback or replacement call.
- No production database write, prompt approval/version creation, image generation, video rendering, publishing, Ruleset change or A+ activation.

Authorization must name source-scope SHA `962dd2d754dfed207f8f5d5fdee7fdf48fded3b34d08fe7f848a1649614ac613` and generation instruction-context SHA `a16599a2f0a0be747185490dd15d7eced8e1d08c6cf0c091f512a0fca06a1a67`. Any reconstruction or code change that produces different IDs, SHA values, profiles or costs invalidates this request before reservation.

Preparation stops here. No real generator or reviewer executed, and no model-quality conclusion is reported.
