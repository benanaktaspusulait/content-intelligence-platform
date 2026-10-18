# STORY_REVIEW V6.1 — Stronger Reviewer Migration Preflight

Prepared 2026-10-18. This is a nonbillable, assessment-only technical preflight. It does not authorize or reserve spending.

## Decision

`gpt-6.1-sol` is technically compatible with the existing STORY_REVIEW Chat Completions path when called with `reasoning_effort=medium`, `max_completion_tokens=12000`, no `temperature`, and the existing strict JSON Schema `response_format`. The prepared operation passed the local preflight route and actual installed OpenAI SDK serialization through an offline `httpx.MockTransport`. No provider network request was made. Real semantic performance remains unverified.

The V6 report and manifest remain unchanged and historical. V6.1 uses exactly the same approved source, candidate texts, candidate provenance, evidence catalog, production settings, and protected scope. The matching scope SHA is expected: it fingerprints the source and assessment scope. System instructions, model, parameters, schema, exact request and cost ceiling belong to the separate full operation binding and have their own fingerprints.

## Official compatibility evidence

The current official OpenAI model page identifies the exact model as `gpt-6.1-sol`, lists reasoning efforts `low`, `medium`, `high`, `xhigh`, and `max`, and explicitly says `none` and `minimal` are unsupported. It lists Chat Completions as supported when tool calling is not used. The model comparison page lists both `v1/chat/completions` and Structured Outputs. The official Chat Completions reference defines `reasoning_effort`, `response_format` with `json_schema`, and `max_completion_tokens`; the latter caps all generated completion tokens, including visible output and hidden reasoning tokens. The model page lists a 128,000-token maximum output.

- [GPT-6.1 Sol model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
- [Official model endpoint and feature comparison](https://developers.openai.com/api/docs/models/compare?model=gpt-6-sol)
- [Chat Completions API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [Reasoning guide](https://developers.openai.com/api/docs/guides/reasoning?api-mode=chat)
- [Token counting and completion-token semantics](https://developers.openai.com/api/docs/guides/token-counting)
- [Official pricing](https://developers.openai.com/api/docs/pricing)

The installed `openai-python` SDK is version **3.32.0**. Its real `chat.completions.create` serializer accepted the exact model-specific fields and emitted the prepared JSON request through `httpx.MockTransport`. The transport asserted the `https://api.openai.com/v1/chat/completions` URL. The SDK is configured with `max_retries=0`; no model fallback or tool calling is configured. Actual returned-model verification remains exact: `response.model` must equal `gpt-6.1-sol`, and existing `model_identity` rejects aliases or mismatches.

## Minimal model-specific changes

Only the assessment-only STORY_REVIEW path selects the new profile. Existing `gpt-4o-mini-2024-07-18` behavior remains intact for historical and other configured operations; DeepSeek and other OpenAI workflows do not select these attributes.

- The V6.1 profile omits `temperature` because reasoning models at non-`none` effort should omit sampling parameters.
- It uses `reasoning_effort=medium`; `none` is not sent.
- It uses `max_completion_tokens=12000`, not the old `max_tokens=4000` parameter.
- The V6.1 system instruction removes the former 4,000-token concision cap and directs the reviewer not to omit required assessment fields. The 18 semantic checks, 12 creative-dimension assessments, evidence isolation, protected facts, UNKNOWN behavior, final-passage and continuity coverage, application-derived verdicts, NO_CREATIVE_WINNER path, and owner eligibility rules remain unchanged. The schema SHA remains V6's `b214f3c0047417f7ed8c06986dc1bc08446b33757d1c82dc8ffb2738f8f23467`.
- Usage accounting prices all `completion_tokens`, which include reasoning tokens. When the provider supplies `completion_tokens_details.reasoning_tokens`, the V6.1 path validates that it is a nonnegative integer no greater than total completion tokens. A `length` finish reason is rejected as incomplete; usage is still accounted and the request is never retried.
- The existing `max_retries=0`, one-request limit, pre-dispatch exact-grant check, durable reservation marker, response checkpoint, refusal/finish-reason checks, exact model check, UNKNOWN-on-uncertainty, and assessment-only gates remain in effect.

The 12,000-token ceiling was evaluated first and retained. It allows three times V5's actual 2,799 completion tokens while providing headroom for 18 semantic findings, 12 dimension assessments and comparisons. A deterministic complete-schema fixture is about 1,682 characters/roughly 1,682/4 tokens by a coarse character estimate; it is synthetic, deliberately concise, and is not evidence of reviewer quality. Because reasoning tokens share the 12,000 ceiling with the visible JSON, sufficiency cannot be guaranteed offline. The preparation preserves every required field; any real `length`-limited response must remain incomplete and stop without retry. The model's documented 128,000 maximum output permits a later, separately authorized cap change if empirical evidence shows this envelope is insufficient.

## Exact operation and scope

The exact request used the existing authentic source and both authentic, immutable candidates. Their frozen provenance remains visible: Candidate A's original generation requested `deepseek-chat`, received `deepseek-flash`, and remains `STOPPED`; Candidate B requested and received `deepseek-flash` and remains `STOPPED`. V6.1 neither upgrades nor rewrites those records.

| Binding | SHA-256 |
|---|---|
| Source | `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d` |
| Candidate A | `50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088` |
| Candidate B | `4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739` |
| Evidence catalog | `5b15086899fc5c80f5de99a749fa3b70d47d32175a6a0ee0bcfdd8ab6f2273d7` |
| Assessment/source scope (same as V6) | `64f9755b9f75536c35fa30fe86d2a36bd9b6fe566d58b294d58efa884938476f` |
| V6.1 system instructions | `f89193b16ea709342714d0632a66658aa54ab2f5b1df515c5c7fa87c6c9a7571` |
| User payload | `45d36b2d88f1e351d1bdf8cbe40439d44ee903d8b047c58e469e9c9be1c5c530` |
| Strict response schema | `b214f3c0047417f7ed8c06986dc1bc08446b33757d1c82dc8ffb2738f8f23467` |
| Full canonical request / actual mocked SDK body | `df12c656bc3d53ed844debd8ac338e75ea2cbc649cc6cd3e408859e4effe3fec` |
| Full executable operation binding | `f31b591832c35c64d0c1cf218d1876f60df6efb5b6cd3ced60917b1a73bdc42d` |

The request body is **24,023 bytes**. The previous 24,000-byte input envelope would reject it by 23 bytes. The only boundary adjustment is a STORY_REVIEW/gpt-6.1-sol-specific 64-byte increment to **24,064 bytes**. No narrative, candidate, evidence, schema or instruction was truncated. The manifest includes the full wire payload, schema, canonical request, actual SDK-serialized body and all corresponding fingerprints.

### Cost ceiling (estimate, not authorization or charge)

Official standard global-endpoint text pricing is **$2.00 / million input tokens** and **$10.00 / million output tokens**. No cached-input discount is assumed. Regional data-residency processing is not selected; the documented 10% premium would apply if a regional endpoint were selected. No tools or separately priced modalities are used.

The existing conservative estimator treats serialized body bytes plus a 1,000-token framing allowance as input: 24,023 + 1,000 = **25,023 estimated input tokens**. The 12,000 `max_completion_tokens` cap includes reasoning. The resulting upper estimate is **$0.170046** (input $0.050046 + output $0.120000). The actual reservation and spend are **$0.00**. This amount is only a ceiling calculation; it is not approved or reserved.

## Timeout and retry policy

The current policy remains bounded and unchanged: SDK connect 5s, pool 5s, write 10s, read 60s; backend HTTP 90s; workflow deadline 600s. The SDK read timeout leaves 30 seconds for the backend to capture and return a terminal receipt. There is no offline evidence that extending the timeout prevents model latency failures, so no broader timeout change is justified. A read timeout is an ambiguous dispatch, not permission to replay. Retries and fallback remain disabled.

## Offline verification

- Existing assessment-preflight route, with the exact V6 source scope and V6.1 model configuration: **HTTP 200**. This was a local in-process test route, not the production service.
- Actual installed SDK request serialization through a mocked HTTP transport: **PASS**. The body matched the prepared request byte-for-byte after canonical serialization; asserted model, endpoint, medium reasoning, 12,000 completion-token cap, omitted temperature/max_tokens, strict schema and bounded timeout.
- Mocked full execution: **PASS** for one request, exact returned model, structured response parsing, reasoning-token usage, cost accounting, immutable receipt, and retry disabled. A mocked `finish_reason=length` response was rejected while its observed usage was accounted. These test responses are synthetic fixtures and prove adapter/contract behavior only.
- Existing focused review, semantic, evidence, transport, and story-experiment ML tests plus V6.1 tests: **230 passed**.
- Focused Java workflow/authority/timeout suite: **50 passed** (`StoryEvolutionServiceTest`, `StoryExperimentContractTest`, `StoryReviewIndependenceTest`, `QualityMlAssessmentTimeoutTest`). Testcontainers used disposable PostgreSQL; dispatch signing used a test-only token. No production database was written.
- Full ML suite, with its expected provider-profile fixture copied to the temporary `/tmp/pompom-test-data` directory: **1,581 passed, 2 skipped, 1 failed**. The only failure is the previously observed unrelated `test_family2_escalation.py::test_island_journal_escalation_is_not_applicable` (`APPLICABLE` returned where the test expects `NOT_APPLICABLE`). The suite is not green; this parser/applicability defect is outside this migration and was left unchanged.
- Historical integrity manifests were independently rechecked: **275/275** and **164/164** files match, with zero mismatches. V6 manifest and report hashes are unchanged.

Offline mocks do not prove real model availability, semantic accuracy, complete reviewer reasoning, or that an owner would accept the result. The review stays `MACHINE_REVIEW`; UNKNOWN and NO_CREATIVE_WINNER remain valid outcomes.

## Required owner authorization before any real request

This preparation grants no paid dispatch. A future owner authorization must be a separate, exact-scope authorization for at most one real OpenAI request and must bind: provider OpenAI; exact model `gpt-6.1-sol`; exact Chat Completions endpoint; source, Candidate A and Candidate B hashes above; unchanged scope hash; V6.1 system and user payload hashes; strict schema hash; canonical and full operation-binding fingerprints above; `reasoning_effort=medium`; `max_completion_tokens=12000`; omission of temperature and `max_tokens`; standard pricing assumptions; a maximum spend no greater than **$0.170046**; one fresh request/idempotency UUID; timeout policy; no retry/fallback/model substitution; and assessment-only consequences. If any binding differs or dispatch becomes ambiguous, stop. Authorization would not approve the story/candidates, grant source admission, invoke BUILD_PROMPT, activate A+, permit rendering, or publish anything.

## Final status

- `V6_1_PREPARATION: READY`
- `REVIEWER_MODEL: gpt-6.1-sol`
- `MODEL_COMPATIBILITY: VERIFIED`
- `NONBILLABLE_PREFLIGHT: PASS`
- `REAL_PROVIDER_CALLS: 0`
- `PAID_DISPATCH_AUTHORIZED: NO`
- `HISTORICAL_V5: STOPPED`
- `REAL_INDEPENDENT_REVIEW_ACCEPTED: NO`
- `PRODUCTION_SOURCE_ADMISSION: NOT_GRANTED`
- `BUILD_PROMPT_CALLS: 0`
- `VIDEO_RENDERS: 0`
- `OFFICIAL_CREATIVE_A_PLUS: INACTIVE`
