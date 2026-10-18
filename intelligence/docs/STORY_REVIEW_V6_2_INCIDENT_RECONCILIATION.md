# STORY_REVIEW V6.2 Incident Reconciliation

**Recorded:** 2026-10-18  
**Scope:** Reconcile the consumed one-shot request; repair monetary authorization and timeout controls offline. No production database, production deployment, prompt/story/evidence, or provider request was changed or created.

## Provider outcome and evidence

The one authorized SDK attempt used OpenAI Chat Completions `POST /v1/chat/completions`, model `gpt-6.1-sol`, reasoning `medium`, and `max_completion_tokens=12000`. The isolated runtime used OpenAI Python SDK `3.32.0` with HTTPX `0.28.1`. The SDK call began at `2026-10-18T12:21:29.866348Z` and ended with `APITimeoutError` / `ReadTimeout` after `60.108996` seconds. The local receipt records a terminal timestamp of `2026-10-18T12:22:30.013701Z`, client request ID `7e7ec2e7-6c58-3e6b-a477-79724ae4e153`, `providerDispatched=true`, no HTTP status, no OpenAI `x-request-id`, no completion ID, no response bytes, and no usage object. The sanitized failure checkpoint independently records the same client ID and error classification.

The preserved request body SHA-256 is `df12c656bc3d53ed844debd8ac338e75ea2cbc649cc6cd3e408859e4effe3fec`. The saved receipt does not contain the OpenAI project or organization ID or an API-key ID. The current local environment has no organization admin-key variable; the configured project API key value was not inspected. OpenAI documents `X-Client-Request-Id` as a way to ask Support whether a timed-out request reached the service and when; the exact ID above is retained for that purpose. No Support case or provider-side lookup was available in this environment.

The official Organization Completions Usage and Costs APIs are read-only options, but their documented examples require an `OPENAI_ADMIN_KEY`. No such credential was available, so neither endpoint was queried. Aggregated usage/cost buckets would in any case be corroborating evidence rather than unique request attribution unless a uniquely matching bucket/key/project can be established. OpenAI's Chat Completions `store` parameter defaults to `false`; the captured request body omitted `store`, and no completion identifier was returned. There is therefore no valid stored-completion retrieval path.

**Conclusion:** provider receipt, inference completion, and billing remain unknown. The timeout does not establish non-receipt. No usage or cost has been fabricated, and the original `DISPATCH_UNCERTAIN` / `USAGE_UNKNOWN` state remains authoritative. The original authorization is consumed and must not be replayed.

Official references: [OpenAI API request-ID guidance](https://developers.openai.com/api/reference/overview), [Organization Completions Usage API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/completions), [Organization Costs API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs), [Chat Completions create/retrieve and `store` behavior](https://developers.openai.com/api/reference/resources/chat), [HTTPX timeout semantics](https://www.python-httpx.org/advanced/timeouts/).

## Budget control defect and correction

The prepared ceiling and computed request envelope were both USD `0.170046`. With 24,023 serialized request bytes plus the 1,000-byte framing allowance, the conservative input allowance is 25,023 units: `25,023 × $2 / 1,000,000 = $0.050046`. The completion limit contributes `12,000 × $10 / 1,000,000 = $0.120000`. The total is exactly `$0.170046`.

Java previously calculated `ceil((maximumCalculatedUsd + 1e-12) * 1e6) / 1e6`. The epsilon pushed the exact `$0.170046` value to `$0.170047`, so the application preflight authorized and durably reserved one micro-dollar above the grant. The violation is confirmed; the historical `$0.170047` reservation and run evidence were not changed.

The correction now uses decimal pricing in the assessment adapter, rounds conservatively to integer USD micro-units, returns `maximumCalculatedUsdMicros`, and binds the integer amount to the backend authorization. The assessment preflight/start/worker and the related story-pilot reservation path compare micro-units without floating-point epsilon. A one-micro-dollar excess, missing micro-unit grant, changed model/token/pricing binding, prior reservation, or failed durable reservation blocks before provider transport. The pre-dispatch claim remains conditional on `READY`; the immutable `REQUEST_RESERVED` evidence and reserved progress are committed together using the existing `REQUIRES_NEW` ledger transaction before `ml.workflow` is called. The ML adapter independently checks the integer cap before creating the SDK client. A durable exclusive ML marker and one-attempt run state continue to prohibit retry after uncertain dispatch.

The new correction is linked append-only in this report; no historic authorization or ledger row was rewritten.

## Timeout hierarchy

The old assessment-specific chain was SDK connect/pool/write/read `5/5/10/60` seconds, backend-to-ML HTTP `90` seconds, and run deadline `600` seconds. There was no reverse proxy between the isolated backend and ML container. The installed OpenAI SDK used HTTPX with retries disabled. HTTPX's read timeout is the maximum wait for a response-body data chunk (network inactivity), not a whole-request wall-clock deadline. The exact failure was at the 60-second read timeout. The run deadline is checked before the synchronous call; it does not cancel provider-side work. A lost backend connection also cannot prove the remote inference stopped.

The STORY_REVIEW-only policy is now versioned `assessment-story-review-timeouts-v2`: SDK connect/pool/write/read `5/5/10/240` seconds, backend-to-ML request deadline `300` seconds, and run deadline `600` seconds. This gives the reasoning request up to four times the prior read-inactivity window and leaves the backend a further 60 seconds to receive/persist the ML receipt. Automatic retries remain disabled. The model request body is unchanged; the timeout and executable implementation policy are fingerprint-covered, so the former V6.1 grant is invalid for any future operation.

The offline exact-source recomputation produced:

- New source/timeout scope SHA-256: `ca622e9dd475d9499f55dcdcd7ac7ceae76cfbb2a009c67c62080945b2431406`
- New backend authority implementation SHA-256: `7eb12dfac881f5ae9c69caea7365ca2aebceac8f9da441cec237c54a5659abb2` (includes `StoryEvolutionService` class `06b98cd316966340090b4dd17f8db8f477831d17f434e646b33040947e825c11`)
- New ML implementation SHA-256: `da1980e74a3c121d0366b98483137aeeacad3da06f9f7ff31446e79374391c82`
- New request-body SHA-256 (unchanged): `df12c656bc3d53ed844debd8ac338e75ea2cbc649cc6cd3e408859e4effe3fec`
- New conservative envelope: USD `0.170046` / `170046` micro-dollars
- New timeout-bound full operation SHA-256: `ad0c623c1aac36bce4e7964e9696feb63543ea15ef9f3bd8e6e0853fe2de2308`

The new authority scope includes the corrected backend bytecode fingerprint and timeout policy; a separately authorized operation would need to use fresh preflight output from the deployed corrected build. These fingerprints document the offline recomputation and are not an authorization to dispatch.

## Focused verification

The changed Python assessment tests use the installed OpenAI SDK with mocked HTTP transport only. They verify exact Decimal pricing and micro-dollar ceilings, refusal at `$0.170047` when the grant is `$0.170046`, request body stability, the `5/5/10/240` SDK configuration, zero retries, marker-before-dispatch behavior, and unknown billing on timeout.

The focused Java tests use disposable Testcontainers PostgreSQL and mocked ML/provider transport. They verify exact/below/over boundary arithmetic, required authorization micros, model/token/pricing drift rejection, durable reservation before transport, prior-reservation rejection, failed reservation transaction rejection, no re-dispatch, and the backend timeout hierarchy. No real provider call occurred.

## Current status

ORIGINAL_DISPATCH_ATTEMPTS: 1  
ORIGINAL_AUTHORIZATION: CONSUMED  
ORIGINAL_REQUEST_STATE: DISPATCH_UNCERTAIN  
ORIGINAL_BILLING_STATE: UNKNOWN  
BUDGET_CONTROL_VIOLATION: CONFIRMED  
BUDGET_GATE_FIX: PASS  
TIMEOUT_POLICY_FIX: PASS  
REAL_NEW_PROVIDER_CALLS: 0  
NEW_PAID_DISPATCH_AUTHORIZED: NO  
REAL_INDEPENDENT_REVIEW_ACCEPTED: NO  
PRODUCTION_SOURCE_ADMISSION: NOT_GRANTED  
BUILD_PROMPT_CALLS: 0  
VIDEO_RENDERS: 0  
OFFICIAL_CREATIVE_A_PLUS: INACTIVE
