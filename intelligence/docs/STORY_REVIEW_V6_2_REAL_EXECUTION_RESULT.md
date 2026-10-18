# Story Review V6.2 — Real Execution Result


## Latest attempt: isolated runtime aligned; one dispatch timed out with billing unknown

**FINAL_STATUS: STORY_REVIEW_V6_2_FAILED_DISPATCH_UNCERTAIN**

OWNER_AUTHORIZATION: GRANTED for the unchanged V6.1 operation only.
SDK_DISPATCH_ATTEMPTS: 1
PROVIDER_ACCEPTANCE: UNKNOWN
REQUEST_DISPATCH: DISPATCH_UNCERTAIN (`APITimeoutError` / `ReadTimeout` after 60.109 seconds)
PROVIDER_RESPONSE: NONE RECEIVED
RAW_RESPONSE_SHA256: NOT_AVAILABLE
USAGE: UNKNOWN (no usage object returned)
ACTUAL_CALCULATED_COST_USD: UNKNOWN (`billingStatus=USAGE_UNKNOWN`)
CANDIDATE_A_SEMANTIC: NOT_EVALUATED
CANDIDATE_B_SEMANTIC: NOT_EVALUATED
CREATIVE_PREFERENCE: NOT_EVALUATED
PRODUCTION_SOURCE_ADMISSION: NOT_GRANTED
BUILD_PROMPT_CALLS: 0
VIDEO_RENDERS: 0
OFFICIAL_CREATIVE_A_PLUS: INACTIVE
AUTOMATIC_RETRY: NONE

### Runtime alignment and exact request evidence

The stale runtime cause was old running containers continuing to use older images; rebuilding an image would not update those containers automatically. Before alignment, the running backend authority hash was `7f1841d79b27122e509d31459fbf434dc69ee97af51d838281b76b1eac4dcff3`, `StoryEvolutionService` was `96f947ae348884f6454325740aac0972de74a0a8dbe0cf916401a198c90eee8c`, and `QualityMlClient` was `feebfc01ad36a98f7d36e2c0f620e8e8168d158f6ab71cb09136de66cc4722b1`; the old ML container lacked both V6.1 modules. The production Compose backend, ML service, database, volumes, and configuration were left untouched. New isolated containers `pompom-story-review-v62-backend` and `pompom-story-review-v62-ml` ran current V6.1 sources on a separate non-production network. Their PostgreSQL endpoint was a new `story_review_v62` database restored from the prepared disposable snapshot, hosted by the existing stopped disposable PostgreSQL container; only this cloned database migrated from schema v70 to v71. No production database writes or migrations occurred.

Aligned backend image: `sha256:de29210168fb0686ea66b5f72ce9d6c5537920e6cd1a4c58c022ff10ae75acdb`. It became healthy and loaded `StoryEvolutionService` SHA-256 `3a2da4a6cfd24e31dafbb2be0398d0f750eb874a6b6a2fcffa393c9323df5664` and `QualityMlClient` SHA-256 `b8304337f1013c3508527353d1ef9ba6c4a9b15130b2e43e29ee2abd4e2c7b0e`. The actual workflow preflight returned authority SHA-256 `0b81a686ae030c42240b9364337d9215cb4fdf8723abaf6015b0176a33fcd221`, matching the prepared manifest.

Aligned ML image: `sha256:61ef0ed02296fb071c32433a52a0c4fc9cbd023366b81aaa4ec6d3cc928324d8`. Both V6.1 modules imported; the implementation fingerprint was `6ec8423177b7ddeea53b1c6b5940e9a09e4e59b239fcfa59106c3a99e2eebbf0`. The prepared OpenAI SDK `3.32.0` was installed. The ML image also needed `httpx==0.28.1` because `openai_provider.py` imports it for timeout-error classification; that package is declared in the project's development dependencies but is not pulled in by the production install. No application source was changed.

Authenticated owner preflight resolved owner `benan`. The clone had no prior run bound to this exact operation and no active run. Source, Candidate A, Candidate B, source catalog, evidence catalog, scope, authority, full operation and request-body fingerprints all matched the prepared manifest. The independent OpenAI SDK MockTransport check emitted `POST https://api.openai.com/v1/chat/completions`; parsed body matched the manifest exactly, canonical SHA-256 `df12c656bc3d53ed844debd8ac338e75ea2cbc649cc6cd3e408859e4effe3fec`, 24,023 bytes. The full operation binding was `f31b591832c35c64d0c1cf218d1876f60df6efb5b6cd3ced60917b1a73bdc42d`. Model, medium reasoning, 12,000 completion-token ceiling, retry-disabled and fallback-disabled settings matched.

### Budget gate discrepancy and dispatch outcome

The prepared manifest's maximum calculated cost and the owner's exact ceiling are both USD `0.170046`. The live application preflight returned `maxTotalUsd=0.170047`, because `StoryEvolutionService.inspectAssessment` rounds with `ceil((maximumCalculatedUsd + 1e-12) * 1e6) / 1e6` (`StoryEvolutionService.java`, line 436). The one-micro-dollar mismatch should have stopped execution before the authorization record was started. I failed to catch it before starting the run. The application then durably reserved USD `0.170047`, one micro-dollar above the authorized ceiling, and invoked the single SDK request. This is a budget-boundary failure; I am recording it plainly rather than treating the manifest's lower calculated amount as proof that the ceiling was enforced.

The application created run `9a71d6c3-f0e2-49b0-bcc1-e8cf3bf94ffc`, request ID `7e7ec2e7-6c58-3e6b-a477-79724ae4e153`, and recorded one `REQUEST_RESERVED` and one `PROVIDER_RECEIPT`. The receipt has `providerDispatched=true`, but no provider HTTP request ID, response, raw response, or token usage; after the 60-second read timeout it terminated `STOPPED` / `DISPATCH_UNCERTAIN`, `billingStatus=USAGE_UNKNOWN`. Provider-side acceptance and actual charge cannot be established from the available receipt. No retry, fallback, model substitution, second run, or other provider call was made.

Because no structured review arrived, none of the 18 semantic findings, 12 creative dimensions, candidate verdicts, or preference can be assessed. They remain unevaluated; no candidate was selected or promoted.

### Evidence and preservation

The run, reservation, timeout receipt, preflight, SDK serialization check, runtime fingerprint summary and final application record are retained under the ignored disposable workspace `intelligence/backend/target/story-review-v62-runtime/`. The disposable database container is stopped after preserving its V6.2 cloned database. The temporary app containers and their OpenAI-key environment were removed. Temporary credential copies were deleted. The original V6.1 manifest, source, candidates and both prior stopped V6.2 report attempts remain intact. Production containers, database, volumes, source admission and deployment were not changed.

The actual outcome is incomplete and terminal: one request attempt timed out, billing is unknown, the authorized ceiling was exceeded by the application's reservation rounding, and the authorized one-shot operation must not be retried.

## Historical attempt 2: authorized, stopped before dispatch (stale runtime)

### Previous attempt details: authorized, stopped before dispatch

OWNER_AUTHORIZATION: GRANTED

REAL_PROVIDER_REQUESTS: 0
REQUEST_DISPATCH: FAILED (PRE-DISPATCH RUNTIME BINDING GATE; no request sent)
REAL_INDEPENDENT_REVIEW_ACCEPTED: NO
CANDIDATE_A_SEMANTIC: NOT_EVALUATED
CANDIDATE_B_SEMANTIC: NOT_EVALUATED
CREATIVE_PREFERENCE: NOT_EVALUATED
ACTUAL_CALCULATED_COST_USD: 0.00 (no request sent; invoice not queried)
PRODUCTION_SOURCE_ADMISSION: NOT_GRANTED
BUILD_PROMPT_CALLS: 0
VIDEO_RENDERS: 0
OFFICIAL_CREATIVE_A_PLUS: INACTIVE

The owner authorized exactly one assessment-only OpenAI request: `gpt-6.1-sol`, Chat Completions, reasoning `medium`, maximum 12,000 completion tokens, calculated maximum USD 0.170046, with retries/fallback/model substitution disabled. The request was not dispatched because the running application does not match the prepared V6.1 execution authority. The authorization is preserved and consumed no provider request or budget reservation.

### Exact binding verification

Using the repository's current source, saved V6.1 assessment catalog, and deterministic request compiler, these all matched the prepared manifest: original and candidate fingerprints, evidence catalog, system instructions, user payload, strict schema, response format, canonical/serialized request body, ML implementation fingerprint, model parameters, 24,023-byte request body, and USD 0.170046 maximum-cost calculation. The exact prepared request hash remains `df12c656bc3d53ed844debd8ac338e75ea2cbc649cc6cd3e408859e4effe3fec`; full operation binding remains `f31b591832c35c64d0c1cf218d1876f60df6efb5b6cd3ced60917b1a73bdc42d`.

The live Java backend fails the required authority fingerprint:

- Manifest/source authority SHA-256: `0b81a686ae030c42240b9364337d9215cb4fdf8723abaf6015b0176a33fcd221`.
- Running backend authority SHA-256, recomputed from its loaded class files: `7f1841d79b27122e509d31459fbf434dc69ee97af51d838281b76b1eac4dcff3`.
- Running `StoryEvolutionService` class SHA-256: `96f947ae348884f6454325740aac0972de74a0a8dbe0cf916401a198c90eee8c`; current prepared source class SHA-256: `3a2da4a6cfd24e31dafbb2be0398d0f750eb874a6b6a2fcffa393c9323df5664`.
- Running `QualityMlClient` class SHA-256: `feebfc01ad36a98f7d36e2c0f620e8e8168d158f6ab71cb09136de66cc4722b1`; current prepared source class SHA-256: `b8304337f1013c3508527353d1ef9ba6c4a9b15130b2e43e29ee2abd4e2c7b0e`.

The running ML container also lacks both `app/workflow/story_assessment.py` and `app/workflow/story_experiment.py`; its image predates the prepared V6.1 implementation. Therefore it cannot compile or enforce the exact prepared review through the official application workflow. Sending directly through the SDK or bypassing the backend ledger would violate the prepared operation's authority, exact-scope and durable-spending controls. No direct provider call, preflight with a different runtime, deployment, rebuild, or database mutation was performed.

### Preservation and next action

No V1–V6.1 evidence, request manifest, source, candidate, or previous V6.2 pending-authorization record was overwritten. There are no response IDs, usage tokens, semantic findings, or candidate preference because no inference occurred. The next safe step is to make the existing application runtime match the already-prepared V6.1 fingerprints, then repeat only the nonbillable exact pre-dispatch gates before using the still-unconsumed one-request authorization. This result does not authorize any changed request or additional call.

## Historical attempt 1: prior pending-authorization stop

The following records the earlier V6.2 state before the owner supplied fresh authorization; it is retained for audit and is superseded only as the current execution status:

OWNER_AUTHORIZATION: PENDING
REAL_PROVIDER_REQUESTS: 0
REQUEST_DISPATCH: NOT_AUTHORIZED
REAL_INDEPENDENT_REVIEW_ACCEPTED: NO
CANDIDATE_A_SEMANTIC: NOT_EVALUATED
CANDIDATE_B_SEMANTIC: NOT_EVALUATED
CREATIVE_PREFERENCE: NOT_EVALUATED
ACTUAL_CALCULATED_COST_USD: 0.00 (no request dispatched; no provider usage or incurred cost)
PRODUCTION_SOURCE_ADMISSION: NOT_GRANTED
BUILD_PROMPT_CALLS: 0
VIDEO_RENDERS: 0
OFFICIAL_CREATIVE_A_PLUS: INACTIVE

### Historical pending-authorization note from attempt 1

Execution stopped at the first required gate. The V6.2 request explicitly sets `OWNER_AUTHORIZATION: PENDING` and requires fresh, explicit approval before any provider request. No request was sent, and no model output, semantic review, creative preference, or billable usage was produced.

The prepared operation's stated maximum allowance is USD 0.170046 for exactly one OpenAI request using `gpt-6.1-sol`, reasoning `medium`, and at most 12,000 completion tokens, for assessment-only STORY_REVIEW. This is an unspent ceiling, not an incurred or invoice-confirmed cost. No retry, fallback, probe, or model substitution occurred.

## Prepared scope recorded in the original V6.2 instruction

These are the bindings supplied by the request; because authorization was pending, no pre-dispatch execution validation was performed:

- Operation binding SHA-256: `f31b591832c35c64d0c1cf218d1876f60df6efb5b6cd3ced60917b1a73bdc42d`
- Canonical request and serialized SDK body SHA-256: `df12c656bc3d53ed844debd8ac338e75ea2cbc649cc6cd3e408859e4effe3fec`
- Original SHA-256: `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d`
- Candidate A SHA-256: `50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088`
- Candidate B SHA-256: `4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739`

## Historical preservation note from attempt 1

No V1–V6.1 artifact, manifest, source, candidate, or saved result was modified. No historical STOPPED run was promoted. The only file created by this V6.2 attempt is this execution-result report.

At the end of attempt 1, the next action was fresh owner authorization. That authorization was subsequently provided and is recorded in historical attempt 2 above. Attempt 1 itself did not authorize any later request.

## Chronological addendum — 2026-10-18 incident reconciliation

The timeout remains `DISPATCH_UNCERTAIN` and billing remains `USAGE_UNKNOWN`: the saved request has a client request ID but no provider request ID, response, completion ID, usage, project/key identity, or uniquely attributable charge evidence. The captured Chat Completions request omitted `store`; no stored response can be retrieved without a valid completion ID. Organization Usage/Costs APIs were not called because an admin API credential was not available. No inference was retried.

The confirmed reservation defect was `ceil((maximumCalculatedUsd + 1e-12) * 1e6) / 1e6`, which transformed the exact `$0.170046` envelope into `$0.170047`. The historical reservation remains unchanged. The current assessment and story-pilot budget gates now use conservative integer micro-dollars, exact grant binding, prior-reservation rejection, and atomic durable reservation before transport. STORY_REVIEW timeout policy is v2 (`read=240s`, backend HTTP `300s`, workflow deadline `600s`); its full operation binding differs from the consumed V6.1 grant. Details, provider evidence, and computed future binding are recorded in [STORY_REVIEW_V6_2_INCIDENT_RECONCILIATION.md](STORY_REVIEW_V6_2_INCIDENT_RECONCILIATION.md).

Focused mocked-transport ML tests passed: 169. Focused Java tests passed: `StoryExperimentContractTest` 47 and `QualityMlAssessmentTimeoutTest` 2. The tests used a disposable PostgreSQL container. No production database or service was changed or deployed. New provider calls: 0; new paid authorization: none.
