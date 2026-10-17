TASK: STORY_REVIEW_DISPATCH_UNCERTAINTY_RECONCILIATION

INCIDENT_RUN:
4c5b5453-6d04-424a-bacd-9575f6f9558d

ORIGINAL_FINAL_STATE:
STOPPED / DISPATCH_UNCERTAIN

APPLICATION_DISPATCH_ATTEMPTS:
1

OPENAI_PROVIDER_ACCEPTANCE:
UNKNOWN

ORIGINAL_SDK_EXCEPTION:
UNAVAILABLE

ERROR_MASKING_ROOT_CAUSE:
The final accounting except block overwrote receipt.error after the SDK exception had already populated it.

ERROR_PRESERVATION_FIX:
VERIFIED

PROVIDER_USAGE_ACCESS:
UNAVAILABLE

PROVIDER_BILLING_ACCESS:
UNAVAILABLE

PROVIDER_USAGE_FINDING:
INCONCLUSIVE

REQUEST_LEVEL_BILLING:
INCONCLUSIVE

ATTRIBUTABLE_CHARGE_USD:
UNKNOWN

ORIGINAL_RESERVED_CAP_USD:
0.006104

ORIGINAL_BILLING_UNCERTAINTY:
PRESERVED

CLIENT_REQUEST_ID_WAS_TRANSMITTED:
NO

FUTURE_CLIENT_REQUEST_ID_SUPPORT:
VERIFIED

TIMEOUT_ROOT_CAUSE:
SUSPECTED

FUTURE_TIMEOUT_RECOMMENDATION:
Proposal only: SDK connect/pool 5s, write 10s, read 60s; backend HTTP 90s; workflow 600s. No settings changed.

ML_TESTS:
361 regression + 20 focused passed (17 overlap; 364 unique cases); exit 0

JAVA_TESTS:
46 passed; exit 0

DISPOSABLE_HTTP_E2E:
13 passed; external provider HTTP mocked; exit 0

NEW_PAID_PROVIDER_REQUESTS:
0

NEW_INFERENCE_SPEND_USD:
0

STORY_GENERATIONS:
0

BUILD_PROMPT_CALLS:
0

VIDEO_RENDERS:
0

PRODUCTION_DB_WRITES:
0

HISTORICAL_RECEIPTS_UNCHANGED:
YES

NEXT_REAL_REVIEW_AUTHORIZATION:
NOT_GRANTED

READY_FOR_NEW_PAID_REVIEW:
NO

## A. Exact dispatch timeline

The original incident remains unchanged. The existing owner-authenticated Java start endpoint created one assessment-only run. Its scheduler committed AUTHORIZED and REQUEST_RESERVED, invoked the genuine ML/OpenAI adapter once, saved a PROVIDER_RECEIPT **uncertainty envelope**, then STOPPED. No provider-generated response was captured; the event name does not prove an OpenAI receipt.

| Observation | Preserved value |
|---|---|
| Start UTC | 2026-10-17T23:16:46.460344Z |
| Receipt finalization UTC | 2026-10-17T23:17:06.682766Z |
| Elapsed | 20.222422 seconds |
| Local request ID | 3e1ad8c7-5bb7-3c0d-8185-4c5725cef8f3 |
| Idempotency key | authentic-assessment-refs-v3-e42412596afab2d39348af2b0ba1d256 |
| Captured SDK responses / usage | 0 / absent |
| Exclusive markers | One reservation, no response checkpoint |
| Final state / billing | STOPPED / DISPATCH_UNCERTAIN / USAGE_UNKNOWN |

Read-only inspection covered the original durable receipt, final run, execution verification, four ledger events, exclusive marker, preflight and network audit. ML log: 0 bytes. Backend log: 8,839 bytes, no original SDK/transport exception. Neither receipt nor checkpoint/log recovers the original exception. No old runtime was restarted or old ledger rewritten.

[Incident/log/SDK inspection](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/incident-investigation.json). The original [execution report](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/REAL_EVIDENCE_REFERENCE_STORY_REVIEW_RESULT.md) and its evidence remain authoritative for what was captured then.

## B. Provider-side reconciliation

**Billing remains unresolved.** No authorized organization-admin credential or organization/project/API-key identifiers were configured in the current process environment, configured ML service environment, or the existing local `intelligence/.env`. Known `.env` / `.env.local` locations were checked by variable name only. The existing inference credential was not exported, printed or used as an admin probe. No new credential was created, and no settings or key permissions were changed.

No provider administrative query was sent: without the authorized admin access and correct account filters, neither account-wide access nor request attribution would be justified. No dashboard session or provider-generated request ID was available through the inspected incident configuration. This is **access unavailable**, not a provider 401/403 and not evidence of zero usage.

Official [Usage API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/completions) offers aggregated usage, while [Costs API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs) offers cost records. Administration uses an Admin API key, distinct from application credentials, as documented in the [API overview](https://developers.openai.com/api/reference/overview).

| Read-only source | Intended exact window/filter | Actual query/result |
|---|---|---|
| GET /v1/organization/usage/completions | 23:10–23:25 UTC, 2026-10-17; 1m buckets, correct project/key + gpt-4o-mini-2024-07-18 | NOT_EXECUTED; authorized access/identifiers unavailable |
| GET /v1/organization/costs | UTC day 2026-10-17; correct project/line item | NOT_EXECUTED; authorized access/identifiers unavailable |

The bounded usage start/end epoch values would be `1792278600` / `1792279500`. This is a proposed query window, not fabricated queried data. The relevant 23:16 and 23:17 minute buckets have **not** been observed. The previous two successful SDK responses remain local control observations; without account identifiers/provider usage access they cannot establish a same-project billing control. Aggregate requests or daily cost changes alone would not prove this incident was billed.

Evidence classification: INCONCLUSIVE. Request-level billing: INCONCLUSIVE. Attributable charge: UNKNOWN. No reservation release or financial reconciliation was written into the old database.

[Access investigation](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/billing-access.json); [Owner-ready support case, not submitted](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/openai-support-case-draft.md). The draft includes timestamps, model, clearly labelled local ID and uncertainty, without prompts or secrets.

## C. Exact exception-masking path

1. `StoryEvolutionService` reserves through the immutable V71 ledger and calls `QualityMlClient.workflow("creative-role", ...)` over authenticated HMAC HTTP. The existing 25-second Java HTTP bound applies to this operation.
2. `story_assessment.execute` invokes `OpenAIProvider.complete`. The installed SDK calls chat/completions with `max_retries=0` and client-level timeout 20.
3. If the SDK raises before returning, adapter response/usage metadata is absent. Previously the assessment's first `except` saved only `{category, detail}` in `receipt.error`; the adapter did not persist a structured SDK diagnostic.
4. `_optimization_cost(None, ...)` then necessarily raises the missing-usage ValueError. The final accounting `except` unconditionally assigned **the same `receipt.error` field**, replacing the original exception.
5. Java received this already-masked ML receipt, preserved it, marked unresolved billing and stopped. The incident's Java HTTP request itself returned the ML receipt; there is no evidence its 25-second timeout fired.

Confirmed defect: secondary accounting overwrite. Original SDK failure: UNAVAILABLE. Approximately 20 seconds suggests timeout, but no preserved exception supports a definitive timeout diagnosis. A connection failure, upstream failure or failure while reading the complete response cannot be excluded. A response may have reached the HTTP layer without the SDK returning a complete object; historical records cannot determine this.

## D. Minimal prospective code fix

Only the existing adapter and assessment execution path changed; no schema, story, evaluator, scheduler, migration or backend policy was redesigned.

- [OpenAI adapter](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/llm/openai_provider.py:19): catch and re-raise the actual SDK exception unchanged; retain exception class, allowlisted safe message, up to four cause-class names, HTTP status, validated provider HTTP request ID and monotonic elapsed seconds. Raw HTTP error strings/bodies may contain credentials/private input, so only standard SDK timeout/connection messages are retained verbatim; other message text is explicitly withheld. No authorization headers, prompt body or arbitrary cause text is logged.
- [Assessment execution](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/story_assessment.py:259): retain the first error as primary; fsync an exclusive owner-only failure checkpoint before accounting. Later accounting failures populate `accountingError` instead of replacing the primary error. Complete SDK response/usage flags and elapsed time are retained separately. No usage still means `USAGE_UNKNOWN` and `DISPATCH_UNCERTAIN`, with no assumed zero charge.
- Distinguish SDK_TIMEOUT, NETWORK_CONNECTION_FAILURE, HTTP_STATUS_ERROR, PROVIDER_REFUSAL, INCOMPLETE_RESPONSE, MISSING_USAGE_AFTER_RESPONSE and UNKNOWN_TRANSPORT_FAILURE. Invalid token values remain ACCOUNTING_VALIDATION_FAILED. Schema/evidence rejection remains RESPONSE_VALIDATION_FAILED. No unsupported transport certainty is invented.
- Existing raw-before-parsing response checkpoint, model verification, budget ceiling, exclusive reservation, no-retry rules and render/approval gates remain enforced.

Files changed: those two application files, `tests/test_story_assessment_transport.py`, and the existing `tests/story_assessment_http_sdk.py` external-transport test helper. No Java production file changed. The support draft and this linked evidence are separate forensic records; historical receipts are untouched.

## E. Future request correlation

The old request did **not** set X-Client-Request-Id: the original adapter used no `extra_headers`, the launcher provided no custom SDK default headers, and this header is not automatically added by the SDK. Its local UUID was therefore not a provider-correlatable client ID. SDK-generated idempotency headers, if any, are a different concept and were not captured. No new header can retroactively identify the old request.

For future assessments, the existing application request UUID is durably included in the exclusive pre-dispatch marker and receipt, then sent using `extra_headers={"X-Client-Request-Id": request_id}`. The UUID is non-secret, unique per dispatch and 36 ASCII characters. Adapter validation limits optional IDs to 1–512 printable non-space ASCII characters and rejects header injection before sending. Successful HTTP `x-request-id` is stored separately from the completion object ID. Error HTTP IDs are preserved where available.

The [official request-ID documentation](https://developers.openai.com/api/reference/overview#supplying-your-own-request-id-with-x-client-request-id) describes ASCII, maximum 512 characters, uniqueness and support troubleshooting. Mocked outbound HTTP tests confirm actual serialization and durable identity equality; unrelated dispatches receive different UUIDs.

The operation preview now declares `clientRequestIdPolicy=application-request-uuid-v1`; the implementation fingerprint changes. The original prompt-body/schema/SDK JSON body remain unchanged, but old grants cannot authorize the changed execution behavior. Refreshed bindings and explicit owner spending authorization are required for any future real review. No new paid manifest/grant was issued.

## F. Timeout findings and bounded recommendation

Installed OpenAI SDK: 3.32.0; HTTPX: 0.28.1. The actual configured client timeout is 20 seconds for connect/read/write/pool. It is phase/inactivity configuration, not a guaranteed total wall-clock deadline. `complete` does not override it per request. Installed SDK source wraps HTTP timeout exceptions in APITimeoutError and other request failures in APIConnectionError, retaining the original exception in `__cause__`. Those distinctions are now tested and preserved.

The historical successful-response latencies were **16.612554s** and **17.340897s**; the larger reference-based strict request finalized without a response at **20.222422s**. Thus a 20s read budget has limited headroom, and the 25s backend budget leaves only five nominal seconds for serialization, local validation, checkpointing and return. Body size alone cannot establish the required generation latency or prove the timeout cause.

**Proposal, not implemented or authorized:** SDK connect/pool 5s, write 10s, read 60s; backend-to-ML total HTTP bound 90s; existing workflow deadline 600s. This offers more room for a slow response plus return/checkpoint margin while bounding the outer HTTP wait. Phase timers do not add up to a strict total deadline and a trickling response can outlast a phase expectation; the backend can still stop waiting before provider work ends. Any such cancellation remains ambiguous/billable-unknown and must not retry. Longer timeouts would prolong reservations and cannot guarantee success. The values are an engineering proposal informed by stored latencies, not measured proof that 60s will succeed.

No SDK, backend, workflow, output-token or spending limit was changed. A future timeout change requires explicit revised operation binding/approval; the current task does not authorize dispatch.

## G. Actual offline verification

| Verification | Result | Exit |
|---|---|---|
| Existing relevant ML regression plus initial transport cases | 361 passed; 343 existing warnings | 0 |
| Final focused transport/correlation suite | 20 passed, 17 overlap with above; 364 unique cases overall | 0 |
| Java StoryExperimentContract / StoryEvolutionService / StoryReviewIndependence | 39 + 5 + 2 = 46 passed, no failures/errors/skips | 0 |
| Actual Java + FastAPI + disposable PostgreSQL HTTP E2E | 13 scenarios passed | 0 |
| git diff --check | No whitespace errors | 0 |

Required scenarios cover direct SDK timeout; connect/read timeout; reset/DNS-connect failure; 429/503/400 with provider HTTP IDs; valid usage and strict evidence IDs; absent/negative usage; refusal/incomplete output; unknown transport failure; primary error survival through secondary usage failure; nonzero-unknown billing; exclusive duplicate rejection; unique/stored/serialized client IDs; invalid IDs rejected before send; stale consumed grants denied; and unchanged approval/BUILD_PROMPT/render restrictions.

E2E used the genuine saved P2 snapshot and actual owner session/CSRF/HMAC/ledger, with **only external OpenAI HTTP mocked**. The ML test process had an offline placeholder credential and denied external sockets. Every scenario made exactly one mocked SDK request; idempotent terminal replay and additional scheduler intervals did not redispatch. HTTP start/approve/handoff checks retained assessment-only restrictions. Non-ledger table counts stayed unchanged. Raw responses and primary failure checkpoints were verified where applicable. All synthetic results are labelled offline test evidence, not genuine AI reviews.

[Test summary](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/test-results.json); [ML results](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/ml-results.xml); [Focused transport results](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/transport-results.xml); [Actual mocked-transport HTTP results](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/http-e2e-results.json); [Serialized mock SDK requests and client IDs](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/actual-serialized-sdk-requests.jsonl). The disposable E2E dump was saved and only its own runtime stopped.

## H. Historical preservation

All 101 protected files matched the pre-investigation hashes, including each of the three real execution directories, prior responses/receipts/events, original narrative archives, source catalog and prepared manifest. States remain:

- 59f47fec-59fb-42e3-b3a4-c9f7d83c7ffc: STOPPED.
- 4b59d668-814c-4f9a-ab50-8e288b5df4df: STOPPED.
- 4c5b5453-6d04-424a-bacd-9575f6f9558d: STOPPED / DISPATCH_UNCERTAIN, original masked error and unknown usage retained.

No old database was restored for mutation, no old financial record changed, and no model result was retroactively repaired. Candidate A's historical DeepSeek identity mismatch and B's invalid historical citation remain intact.

[Historical hash verification](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/historical-integrity.json); [Pre-investigation inventory](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-dispatch-uncertainty-evidence/historical-before-sha256.json). No production database writes, production deployment, real inference, approval, story generation, BUILD_PROMPT, rendering, publishing, commit or push occurred.

## I. Remaining blocker

Request-level receipt/usage/billing cannot be established with available access. The original exception cannot be reconstructed. The prospective diagnostic fix is verified offline, but it does not resolve the old financial uncertainty, prove real-provider success or authorize another paid review. **READY_FOR_NEW_PAID_REVIEW: NO.**

## J. Owner action

Use the prepared support case or the correct account's authorized usage/billing view to reconcile the incident. Do not send credentials to chat. Any eventual provider finding should be appended as a new investigation record without overwriting historical uncertainty. Only after reconciliation and a separate decision on revised bindings/timeouts may a newly scoped paid review be considered. No support ticket was submitted and no new approval is requested or assumed by this task.


## K. Provider-side follow-up — 18 October 2026 (current finding)

This append-only follow-up updates the earlier access limitation above: an **existing authenticated Chrome OpenAI Platform session was available**. No new login, admin credential, permission, API key or inference was created. Official usage and cost CSVs were downloaded through the site's normal UI, read-only. Direct administrative APIs were not called. The earlier access statement records the initial environment/configuration investigation; the current provider evidence is below.

| Provider observation | Actual |
|---|---|
| Organization | Personal / `org-ynjQLG10AxTjfhD3UHAd4xM6` |
| Project | Default project / `proj_RlAUUtPBGI1apCLjeXGcbmAu` |
| Model filter | gpt-4o-mini-2024-07-18 |
| UTC usage day / granularity | 2026-10-17 / 1 minute, 1,440 buckets |
| Matched prior control key identifier | `key_CcUCyotObOyH8IlY` (identifier, not a secret) |
| 21:22 UTC control | 1 request, 3,556 input / 1,737 output tokens |
| 21:43 UTC control | 1 request, 3,117 input / 1,823 output tokens |
| Daily model usage | 2 requests, 6,673 input / 3,560 output tokens |
| 23:10–23:25 UTC incident window | No request/usage entries in all 15 minute buckets |
| 23:16 and 23:17 UTC | Empty buckets, no reported requests/tokens |
| Daily project cost | USD 0.00313695 |
| Calculated cost of the two prior known calls | USD 0.00313695 |
| Observed excess over those controls | USD 0 |

Both prior real reviews match the provider export in exact model, UTC minute and token counts, establishing relevant project/key context. The daily project cost equals their combined configured-rate cost exactly. **No additional usage or charge attributable to the uncertain third request is visible in these exports.** These are actual provider-side exports, not inferred application usage or synthetic responses.

Classification: **NO_RELEVANT_USAGE_OBSERVED**. Request-level billing remains **INCONCLUSIVE**, because no client/provider request identifier was captured for the third call and absence/aggregate totals cannot conclusively establish that it was never processed or billed. The zero observed excess is not a verified zero incident charge or invoice certification. Original reservation USD 0.006104 and historical uncertainty remain unchanged; no financial ledger correction was made.

Current access: usage AVAILABLE via browser, daily project costs AVAILABLE via browser. Exact request-level confirmation is still unavailable. The downloaded activity CSV was scoped to the selected project and model; cost CSV to the selected project and UTC day. No unrelated project was exported. No key value, cookie, token, private story or prompt was exported or sent to support.

[Official minute usage CSV](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-provider-usage-followup/completions_usage_2026-10-17_2026-10-17.csv); [official daily project cost CSV](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-provider-usage-followup/cost_2026-10-17_2026-10-17.csv); [machine-readable verification](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-provider-usage-followup/reconciliation.json).

The original investigation report is preserved byte-for-byte in [initial-investigation-report.md](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-provider-usage-followup/initial-investigation-report.md). All three historical real-review receipt/ledger directories remain unchanged. No further implementation, inference, retry, deployment, approval or generation was performed during this follow-up.

The accessible provider records have now been reconciled as far as they support. A definitive incident charge would require provider confirmation; the prepared support draft can be supplemented with the organization/project/key identifiers above. The ticket was not submitted. The technical repair remains verified offline; this research follow-up does not grant another paid review.
