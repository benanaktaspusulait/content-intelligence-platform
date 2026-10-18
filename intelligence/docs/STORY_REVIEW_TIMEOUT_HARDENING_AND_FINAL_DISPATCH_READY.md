TASK: STORY_REVIEW_TIMEOUT_HARDENING_AND_FINAL_DISPATCH_PREPARATION

HISTORICAL_REAL_REVIEW_ATTEMPTS: 3
HISTORICAL_REAL_REVIEWS_ACCEPTED: 0

V3_FINAL_STATE: STOPPED / DISPATCH_UNCERTAIN
V3_PROVIDER_USAGE_OBSERVATION: NO_RELEVANT_USAGE_OBSERVED
V3_REQUEST_LEVEL_BILLING: INCONCLUSIVE

ORIGINAL_SDK_EXCEPTION: UNAVAILABLE
EXCEPTION_MASKING_FIX_PRESERVED: YES
CLIENT_REQUEST_ID_SUPPORT_PRESERVED: YES

TIMEOUT_ROOT_CAUSE: SUSPECTED_NOT_PROVEN

OLD_SDK_TIMEOUT: 20s
OLD_BACKEND_TIMEOUT: 25s

NEW_SDK_CONNECT_TIMEOUT: 5s
NEW_SDK_POOL_TIMEOUT: 5s
NEW_SDK_WRITE_TIMEOUT: 10s
NEW_SDK_READ_TIMEOUT: 60s
NEW_BACKEND_HTTP_TIMEOUT: 90s
WORKFLOW_DEADLINE: 600s

TIMEOUT_SCOPE_ISOLATION: VERIFIED
NO_RETRY_BEHAVIOR: VERIFIED
UNKNOWN_SPEND_HANDLING: VERIFIED
PRIMARY_EXCEPTION_PRESERVATION: VERIFIED

STRICT_STORY_REVIEW_CONTRACT_UNCHANGED: YES
EVIDENCE_CATALOG_UNCHANGED: YES
CANDIDATE_A_B_ISOLATION: VERIFIED

ML_TESTS: 369 PASSED; EXIT 0
JAVA_TESTS: 50 PASSED; EXIT 0
DISPOSABLE_HTTP_E2E: 16 regression scenarios plus 3 final-code scenarios PASSED; final verification EXIT 0

HISTORICAL_RECEIPTS_UNCHANGED: YES
HISTORICAL_CSV_EXPORTS_UNCHANGED: YES

NEW_REAL_OPENAI_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0

NEW_STORY_GENERATIONS: 0
NEW_STORY_APPROVALS: 0
BUILD_PROMPT_CALLS: 0
IMAGE_GENERATIONS: 0
VIDEO_RENDERS: 0
PRODUCTION_DB_WRITES: 0

NEW_PREPARED_OPERATION_SHA: d202794af8352aea371a7248be269c2eb045a1f696b61a3920ea58fe4b21f1c0
NEW_IMPLEMENTATION_SHA: 381d3bcddc8eb779b7020b8ab3be123661e09af21e5c072e342b30a10c37edd2
NEW_BACKEND_AUTHORITY_SHA: bd510940b702aded29592782e51464044e78489ffcba7d65835086370d091a72
NEW_CLIENT_REQUEST_ID_POLICY: application-request-uuid-v1

NEW_MAX_RESERVED_USD: 0.006104
NEW_MAX_REAL_PROVIDER_REQUESTS: 1

OWNER_PAID_REVIEW_AUTHORIZATION: NOT_GRANTED

READY_FOR_PAID_AUTHORIZATION: YES
REAL_INDEPENDENT_REVIEW_COMPLETED: NO

## A. Root-cause boundary

The confirmed V3 defect was a primary SDK exception overwritten by a secondary usage/cost error. That completed fix remains intact. The original exception is unavailable, and V3 is not reclassified as a proven timeout. Its 20.222422-second duration, versus earlier successful-response durations 16.612554s and 17.340897s, supports additional prospective headroom without proving the old transport cause.

The separate official CSV reconciliation remains unchanged: two matching prior requests, no relevant V3-window usage, daily project cost USD 0.00313695 equal to the prior two calls. Request-level V3 billing remains INCONCLUSIVE. No billing/admin query or new support workflow was performed here.

## B. Exact timeout implementation

| Layer | Before | Final effective behavior |
|---|---|---|
| Assessment SDK connect / pool | 20 / 20s | 5 / 5s |
| Assessment SDK write / read | 20 / 20s | 10 / 60s |
| Assessment Java → ML HTTP request | 25s | 90s |
| Assessment workflow authorization/deadline | Up to 600s | Up to 600s; new template uses 600s |
| General OpenAI adapter default | Environment setting, 20s in tested configuration | Unchanged |
| Other generic workflow HTTP / CPQ-pilot HTTP | 25s / 130s | Unchanged |
| Canonical validation HTTP | 180s | Unchanged |

[Assessment execution](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/story_assessment.py) constructs the scoped timeout and passes it explicitly to [OpenAIProvider](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/llm/openai_provider.py). The general adapter accepts an optional per-instance override; omitted overrides retain the original environment-based scalar timeout. No shared environment variable or production configuration was increased.

[QualityMlClient](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityMlClient.java) selects 90s only when operation is `creative-role`, role is `STORY_REVIEW`, and context policy equals `ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1`. The policy is also returned in the authoritative assessment scope. Python preflight rejects a mismatched backend timeout policy. Preflight itself retains the normal 25s HTTP timeout.

HTTP phase timeouts are inactivity/phase controls, **not a guaranteed 60-second total deadline**. A 90s outer HTTP wait leaves nominal validation/checkpoint/serialization margin after a slow response; it does not guarantee the provider completes before that boundary. If the backend stops waiting, provider execution may continue. The run remains uncertain and cannot redispatch automatically. The existing workflow deadline remains bounded at 600s and is not treated as provider cancellation.

## C. Scope isolation

Actual built Java HttpRequest objects were captured with durations **90, 25, 25, 25, 25, 130 seconds** for assessment review, ordinary story review, generation, prompt optimization, assessment preflight and CPQ capabilities respectively. The existing canonical validation timeout was not edited. No DeepSeek adapter or generation configuration changed.

The installed default OpenAI client was also constructed offline with a placeholder credential: ordinary adapter had numeric connect/pool/write/read 20/20/20/20; assessment adapter had 5/5/10/60. Only assessment execution passes the new override. Source/profile data, story checks, canonical rules and scoring are unaffected.

## D. Installed SDK and Java verification

Installed versions: **OpenAI 3.32.0, legacy HTTPX 0.28.1, HTTPX2 2.13.1**. Inspection found that the installed SDK's default client uses HTTPX2. Passing a legacy `httpx.Timeout` directly left nested timeout objects in that default client's configuration, although injected legacy-HTTPX mock clients normalized them. This verification caught the compatibility issue before any real call.

Final code uses the SDK's public **`openai.Timeout`** type. Both actual constructed native-client phase values and outbound mocked HTTP `request.extensions.timeout` were verified as numeric 5/5/10/60. This is a prospective compatibility correction; V3 used a scalar 20s timeout, so this finding does not explain or retroactively classify V3.

The real installed SDK serialized an exact **23,690-byte** body. Canonical body digest remains `1a71b03de5462156ee09f6f4f65bd526c29f751f03e84b96f719d5eafd10ea35`. The additionally measured SDK wire-body digest is `ccd7a919df82af8583a9d0d86b68253c48d160a30e1adcb737824c36ef0eb0c9`; canonical sorting and SDK serialization order differ. This is a newly measured wire representation, not an invented change to unaffected source/prompt/schema hashes.

Java tests capture actual built HTTP requests and simulate `HttpTimeoutException` and interruption without waiting 90s. The existing SDK tests simulate connect/read/write/pool timeouts at the external transport boundary. No real availability probe or provider inference occurred.

[Installed SDK/native client and wire-boundary verification](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/installed-sdk-boundary-verification.json); [Actual SDK wire body, no credentials](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/next-actual-sdk-wire-request.json).

## E. Request correlation

The existing application-request UUID mechanism remains the only client-ID mechanism. The UUID is fsynced into the exclusive reservation before dispatch, transmitted as `X-Client-Request-Id`, retained in the receipt, and compared to the durable request identity. Header validation excludes injection characters; different dispatches receive different UUIDs. Provider HTTP `x-request-id` is distinct from both the client UUID and completion-object ID.

Existing tests verify serialization, UUID uniqueness, header validation, and independently captured provider HTTP ID. Java outer-failure receipts now also retain the known local/client UUID. None of this retroactively transmits an ID for historical V3.

## F. Accounting and no-retry safety

The primary SDK error and cause classes remain in `error`; missing/invalid usage is additional `accountingError`, never a replacement. Raw SDK response remains checkpointed before parsing. SDK failure checkpoints retain the first diagnostic and response/usage flags. Unknown usage preserves `actualCostUsd=null` (or absent for an outer uncertainty envelope), `USAGE_UNKNOWN` and non-retryable uncertainty, never a synthetic zero cost.

[StoryEvolutionService](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/StoryEvolutionService.java) now retains the outer exception/cause class chain, elapsed time and safe backend diagnostic. It distinguishes BACKEND_HTTP_TIMEOUT, BACKEND_INTERRUPTED and BACKEND_TRANSPORT_FAILURE while preserving unknown provider/billing outcome. It does not claim an outer cancellation stopped OpenAI.

SDK `max_retries=0`, single request reservation, exclusive marker, atomic run claim and terminal/no-resume behavior remain enforced. Consumed V1/V2/V3 grants are rejected before reservation against changed source/operation bindings. No production approval, BUILD_PROMPT or rendering gate was relaxed.

## G. Regression results

| Verification | Actual result | Exit |
|---|---|---|
| Full relevant ML regression | 369 passed; 343 existing warnings | 0 |
| Java StoryExperimentContractTest | 41 passed | 0 |
| Java StoryEvolutionServiceTest | 5 passed | 0 |
| Java StoryReviewIndependenceTest | 2 passed | 0 |
| Java QualityMlAssessmentTimeoutTest | 2 passed | 0 |
| Initial disposable HTTP regression | 16 scenarios; completed nonmutating verification | 0 after harness correction |
| Final native-timeout disposable HTTP | 3 scenarios | 0 |
| Installed SDK default-client + wire verification | Passed | 0 |
| git diff --check | Passed | 0 |

The initial 16-scenario harness indexed `actualCostUsd` in an outer-disconnect envelope where the amount was intentionally absent/unknown, causing a test-harness KeyError (initial exit 1). The assertion was corrected to use the optional value; all saved runs were verified without repeating dispatches. A separate raw-baseline comparison initially included Flyway startup bookkeeping; verification appropriately excludes `flyway_schema_history` and compares **98 application tables** unchanged against an independently restored baseline. These were verification-harness issues, not accepted provider results or hidden production fixes.

After the SDK-native Timeout correction, the full 369 ML tests and all 50 Java tests were run again. Final positive/read-timeout/outer-disconnect HTTP scenarios use the final code and bindings. No test waited 60/90 real seconds to demonstrate a timer constant. External timeout exceptions and controlled disconnection provide deterministic failure coverage.

[Test summary](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/test-results.json); [ML results](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/ml-results.xml); [ML log](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/ml-regression.log); [Java log](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/java-regression.log).

## H. Disposable application HTTP E2E

Both runs used the real Java backend, FastAPI, PostgreSQL restored from the saved P2 snapshot, original archived A/B narratives, owner login/session/CSRF, HMAC, V71 ledger and installed SDK. Only external OpenAI HTTP was mocked, with an offline placeholder credential and outbound socket denial. No genuine OpenAI key was used for dispatch.

The positive final run completed `ASSESSMENT_COMPLETE_OWNER_DECISION_PENDING`, preserving the full mocked SDK response and resolved original evidence. Story approval remained PENDING, BUILD_PROMPT and approval POSTs were denied, no story draft/version was created, and render authorization remained false. These are **offline integration results**, not an accepted real independent AI review.

Read timeout retained primary SDK error plus secondary accounting uncertainty. The outer-disconnect case ended only the isolated test ML process after its mock transport recorded the request; real Java caught the broken connection, committed a safe uncertainty receipt, stopped and did not issue another request. Unit tests separately verify an actual wrapped HttpTimeoutException's classification. Idempotent terminal replays and subsequent scheduler intervals did not increase SDK dispatch counts. All three consumed real grants were rejected.

Final persisted deadlines and dump readability were checked with read-only queries against only the task's disposable DB. Both application runtimes and their own DB containers are stopped; unrelated services are untouched. Final dump retained with owner-only permissions. No production deployment or production DB write occurred.

[16-scenario regression proof](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/http-e2e-results.json); [Final-code 3-scenario proof](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/final-native-sdk-http/http-e2e-results.json); [Final positive run](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/final-native-sdk-http/http-positive-proof.json); [Final request/timeout trace](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/final-native-sdk-http/actual-serialized-sdk-requests.jsonl); [Persisted deadline and dump verification](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/final-native-sdk-http/deadline-and-dump-verification.json); [Final runtime shutdown](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/final-native-sdk-http/runtime-shutdown.json).

## I. Historical preservation

All **190 protected preexisting evidence files** matched their baseline hashes, including all three real execution directories, original source/candidate archives, provider CSV exports and the old manifest. All three old DB dumps separately match the hashes in their immutable execution-verification records.

V1 remains STOPPED; V2 remains STOPPED; V3 remains STOPPED / DISPATCH_UNCERTAIN with original masked error and unknown usage/billing. DeepSeek requested/returned identity qualifications and old invalid citations remain unchanged. Neither source approval nor any historical financial ledger was rewritten.

[Historical verification, including old DB dumps](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/historical-integrity.json); [Pre-task hash inventory](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/historical-before-sha256.json). No commit, amend, reset, push or production deployment was performed by this task.

## J. Newly prepared single-review scope

Manifest: [STORY_REVIEW_TIMEOUT_HARDENED_REVIEW_MANIFEST.json](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/STORY_REVIEW_TIMEOUT_HARDENED_REVIEW_MANIFEST.json). It uses the existing application authorization schema and actual authenticated **nonbillable** preflight; it is not a spending grant.

Fresh idempotency key: `authentic-assessment-timeout-v4-3ec2ec356d6693039eadee73`.

Owner paid authorization: NOT_GRANTED. `authorizePaidInference=false`, `confirmAssessmentOnly=false`. Maximum requests 1, rounds 1, workflow 600s, output 4,000 tokens, retries/fallback 0. The application must reproduce the final exact scope, code and compiled authority before any separately authorized dispatch. Prepared runtime requirements identify SDK versions and native timeout behavior; no model substitution is permitted.

The complete final operation bindings are:

```json
{
  "policy": "ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1",
  "role": "STORY_REVIEW",
  "provider": "openai",
  "model": "gpt-4o-mini-2024-07-18",
  "sourceStorySha256": "ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d",
  "scopeSha256": "e843b45debd07250f25ef68e7cc61ff2d488d429f71135c502ec12cd090d37d6",
  "evidenceCatalogSha256": "5b15086899fc5c80f5de99a749fa3b70d47d32175a6a0ee0bcfdd8ab6f2273d7",
  "evidenceDocumentBindings": {
    "SOURCE": "ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d",
    "CANDIDATE_A": "50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088",
    "CANDIDATE_B": "4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739"
  },
  "evidenceExtractionVersion": "story-review-exact-spans-v1",
  "systemSha256": "8cef6972c1ec478f7fbdc04cfec4789a9f3e5757f0f2f2e020e9fc6d98f50cef",
  "effectiveRequestSha256": "139783279debb6bb96565dae71b484f864d3a7c3695b7e84a0fb013faa4ccaf3",
  "responseSchemaSha256": "2d40c450d6e011db93b7a3add1545ccce24100555c44c965ffb015aef55ebff6",
  "responseFormatSha256": "f2c4e0311b3a7acc8092dec6d2d2458e7dc3e3122ec2cd45d8a392342f834179",
  "serializedRequestSha256": "1a71b03de5462156ee09f6f4f65bd526c29f751f03e84b96f719d5eafd10ea35",
  "responseFormatType": "json_schema",
  "strictStructuredOutput": true,
  "schemaVersion": "assessment-only-story-review-v3-evidence-refs",
  "maxRequests": 1,
  "maximumInputBytes": 24000,
  "payloadBytes": 12721,
  "systemBytes": 2645,
  "serializedRequestBytes": 23690,
  "schemaBytes": 7273,
  "maxOutputTokens": 4000,
  "inputUsdPerMillion": 0.15,
  "outputUsdPerMillion": 0.6,
  "maximumCalculatedUsd": 0.0061035,
  "automaticRetries": false,
  "fallback": false,
  "assessmentOnly": true,
  "clientRequestIdPolicy": "application-request-uuid-v1",
  "timeoutPolicy": {
    "version": "assessment-story-review-timeouts-v1",
    "connectSeconds": 5,
    "poolSeconds": 5,
    "writeSeconds": 10,
    "readSeconds": 60,
    "backendHttpSeconds": 90,
    "workflowDeadlineSeconds": 600
  },
  "outboundTransportMetadataSha256": "fa89454b6228afad847fbbee39a173a329887a707191548760547e70791ea615",
  "requestFramingAllowanceBytes": 1000,
  "clientRequestIdHeaderBytes": 59,
  "implementationSha256": "381d3bcddc8eb779b7020b8ab3be123661e09af21e5c072e342b30a10c37edd2",
  "maxCostUsd": 0.006104
}
```

The manifest preserves full source and genuine candidate provenance, including hashes:

| Protected input | SHA-256 |
|---|---|
| Source | ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d |
| Candidate A | 50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088 |
| A original raw response | 34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1 |
| Candidate B | 4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739 |
| B original raw response | 10dc1482d66514e153835b6e3cd90f4e8b58ff1e1d61f51fa99e42424f15fef3 |

Source, candidate, catalog, system/user, strict-schema, response-format and canonical SDK-body hashes remain unchanged because their bytes remain unchanged. Runtime scope, ML implementation, compiled Java authority and prepared-operation fingerprints are fresh. The outbound metadata fingerprint binds timeout and client-ID policy. Complete exact request/schema/catalog artifacts are linked below.

### Recomputed reservation

Actual canonical and SDK wire body: 23,690 bytes. Existing conservative framing allowance: 1,000 bytes, including the 59-byte client-ID header representation; it is not an additional billable prompt. Maximum output: 4,000. Configured standard rates: USD 0.15 input / 0.60 output per million, no assumed cache discounts.

```text
((23690 + 1000) × 0.15 + 4000 × 0.60) / 1,000,000
= 0.0061035
ROUND_UP_TO_6_DECIMALS = USD 0.006104
```

The numerical ceiling is unchanged after recomputation; authorization is new and ungranted. The published [model pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini) matches those standard rates. The snapshot is deprecated with [scheduled shutdown 14 January 2027](https://developers.openai.com/api/docs/deprecations). Its exact identity is retained; account-specific availability was not probed and cannot be guaranteed by documentation. No billable health check or fallback was attempted.

[Fresh binding and budget verification](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/prepared-scope-verification.json); [Final actual application preflight](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/final-native-sdk-http/actual-http-preflight.json); [Complete exact SDK request](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/next-exact-sdk-request.json); [System](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/next-system.txt); [User](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/next-user.txt); [Strict schema](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/strict-response-schema.json); [Evidence catalog](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-timeout-hardening-evidence/evidence-catalog.json).

## K. Final limitations and stop boundary

**READY_FOR_PAID_AUTHORIZATION: YES.** This means the scoped implementation and bounded single-call preparation are verified offline. It does not authorize execution or prove real OpenAI reliability, valid independent judgment, production-source admission or creative quality. Longer timeouts cannot guarantee success; valid evidence IDs prove provenance, not semantic correctness. V3 request-level billing remains INCONCLUSIVE.

A fresh explicit owner spending authorization is still required. No genuine STORY_REVIEW was started, no new real review was accepted, and no story/prompt approval, BUILD_PROMPT, image/video, publishing or official A+ activation occurred. The task stops with this prepared operation and report.
