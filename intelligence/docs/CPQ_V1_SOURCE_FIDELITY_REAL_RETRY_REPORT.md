# Source fidelity fix deployment and fresh real-review readiness

16 October 2026. Deployment and runtime verification completed. **The new paid inference awaits separate explicit owner approval.** No new pilot/request/authorization was created and no real provider call was made in this deployment task.

| Required status | Actual result |
| --- | --- |
| DEPLOYMENT | VERIFIED |
| LIVE_REASONING_CONFIGURATION | LOW_VERIFIED |
| MIMI_BINDINGS | VERIFIED |
| OWNER_AUTH | VERIFIED |
| NEW_SOURCE_AUTHORIZATION | PENDING |
| REAL_SOURCE_FIDELITY | NOT_EXECUTED for the new attempt |
| CRITIC_A | NOT_EXECUTED |
| CRITIC_B | NOT_EXECUTED |
| REAL_DISPATCH | DISABLED in backend and ML |
| CPQ_GRADING | INACTIVE |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED |

## 1. Disk recovery and controlled deployment

Initial host free space was approximately 3.3 GiB; no build was started before the owner approved cleanup. The owner then explicitly approved removal of the 20 exact cache IDs listed in the prior report. Each record was rechecked with an exact-ID filter, reclaimable=True, shared=False and the expected Maven compile-step description before removal.

Only those 20 cache records were removed. The before/after BuildKit inventory comparison found no additional removed IDs; running backend/ML/frontend/PostgreSQL/render image identities were unchanged by cleanup. No image, Docker.raw, volume, database, backup, historical provider evidence or unknown user file was deleted. Exact IDs and per-operation results are in approved-cache-cleanup.json.

Immediate measured host free space increased from 3.308 to 4.472 GiB. Host/VM cache accounting does not guarantee identical immediate host reclamation, and later measurements varied as space was released. The deployment plan was revised to avoid simultaneous ML/backend build peaks: isolated ML build allowance 3 GiB plus 1 GiB operating reserve, then a fresh disk check before the backend-only build. ML was deployed first through `./intelligence/scripts/deploy.sh ml-service`. Host free space subsequently measured about 6.3–6.4 GiB, above the original 5 GiB planning margin, before `./intelligence/scripts/deploy.sh backend` was run. Final verification measured approximately 6.07 GiB free.

Both official deployments succeeded. Required frontend nginx reconnection used the existing script's restart behavior; **the frontend image was not rebuilt**. Only affected ML/backend images were built. Dispatch remained false during cleanup, both builds, deployment and verification. No new database migration was introduced.

## 2. Final running image identities and health

| Service | Final running image ID |
| --- | --- |
| ml-service | `sha256:7efef284319092c680ac1b982a3f88235956dd26354470148f1a82696936363b` |
| backend | `sha256:f6822a402e291a5a98407fe0e0850b90ec21b4b284037431b5edc4656cde8d95` |
| frontend | `sha256:d5191a437f0a7917324a10f8459279a72b79d9655fd196b904cb958b8b8c00c5` |

ML changed from `sha256:734e76e603c5542e1c4d7d2018b4ad89bceb4c260d65e7b1e8795beb2f0da243`; backend changed from `sha256:32888e142e59a3e67d1c798e4f6d21aad5289939ea91a3500d887c7fafdfbb87`. Frontend retains its exact prior image ID.

Official `deploy.sh --check ml-service backend` passed ML /health, backend /actuator/health, frontend / and proxied provider-capabilities HTTP checks. ML/backend/PostgreSQL/render report healthy. Frontend is running and HTTP verified; its compose definition does not provide a container healthcheck. Flyway V65 remains successful.

## 3. Live reasoning/provider/output contract

The deployed application capabilities now expose sourceFidelityConfiguration/openai-escalation:

- provider/model: OpenAI / gpt-6.1-sol;
- effective source reasoning: **low**;
- supported efforts: low, medium, high, xhigh, max;
- strict json_schema retained;
- proposed request ceiling: 4,000 completion tokens, including reasoning and visible output;
- SDK retries: zero; no fallback.

Both general profiles remain unchanged: DeepSeek/deepseek-v4-pro/high and OpenAI/gpt-6.1-sol/high for their existing critic/optimizer uses. Neither critic was authorized or dispatched.

The running backend compiled class contains the source-specific capability and reasoning-authorization binding logic. Compiled class SHA-256: `12b87498b882b929255b10967825ae4f150b237eeb2fa7cb74a52f13435b820f`. Actual durable write-path behavior was verified previously in disposable backend integration tests; no new live authorization was inserted merely to demonstrate it. A future paid source authorization must durably bind low and use a new request/idempotency identity.

## 4. Mock verification inside the deployed ML image

A separate child process inside the new running image executed the real adapter/pilot code against mocked SDK transport and the four exact saved Mimi inputs. The child used a dummy key and patched SDK construction before inference. It did not modify the main service environment, create database evidence, or send any provider request.

Verified in that deployed image:

- low is passed to the SDK; max_completion_tokens=4000; exact authorized model;
- strict json_schema and max_retries=0;
- all four fingerprints remain exact;
- complete representative mock JSON is accepted with UNKNOWN retained;
- none and minimal are rejected before SDK construction;
- a length response with all completion tokens consumed by reasoning is rejected as REASONING_BUDGET_EXHAUSTED;
- failure usage/cost accounting is retained;
- critic and optimizer settings remain high.

This is runtime contract verification with mocks, not a real source-fidelity result. Previous offline focused evidence remains 81 ML tests and 26 backend tests; no new full-suite pass is claimed.

## 5. Authentication/security

The deployed helper still confirms configured owner authentication, credential existence and private permissions. Fresh normal local application login succeeded for owner benan, labelled OWNER_DECISION and independentHumanReviewer=False. A logged-in logout POST with incorrect CSRF returned 403; valid logout returned 200 and revoked authentication. Fresh anonymous POSTs to pilot creation, paid authorization and owner decisions all returned 403.

Internal backend/ML dispatch-signing configuration is present and matches; only that boolean was recorded. No secret, cookie, CSRF value or API key was placed in reports or evidence. No independent human role or assessment was created. Session secrets used for local protocol verification remained transient in memory.

## 6. Exact four live source bindings

Content 10, immutable Prompt 10/version 1, analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`. Each fingerprint was recomputed from actual persisted prompt text returned by the deployed application, with no binding blockers.

| Subject | Exact SHA-256 | New semantic source review |
| --- | --- | --- |
| Original | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` | NOT_EXECUTED |
| Historical candidate 1 | `90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495` | NOT_EXECUTED |
| Historical candidate 2 | `218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749` | NOT_EXECUTED |
| Historical candidate 3 | `2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746` | NOT_EXECUTED |

Historical candidate 1 is comparison `e651eb75-b894-477d-ae77-0fe6e05236da` / candidate-a. Candidates 2/3 are comparison `9275c94b-fc35-4207-8648-dfd8d166e502` / candidate-a and candidate-b. The empty latest comparison was not substituted for these three saved candidates.

Approved-story SHA-256 was recomputed as `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`. Common authoritative settings remain ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15 seconds / image2video / 480p / 9:16. Canonical Ruleset 1.11 remains 88.40625/B; serialized floating-point representation may contain the equivalent trailing precision 88.40625000000001, checked with numerical tolerance rather than score alteration.

## 7. Historical records and request inventory

The entire historical request row was compared to its preexisting archive and remains exactly unchanged:

- Old pilot: `2485b1a4-a011-4456-aae6-a37badd98245`.
- Old durable request: `3a55b29a-48c6-44c0-a003-da11af0f7069`.
- Old provider request: `chatcmpl-EZWMfRgFNWEjOnLPLaVesViDKGOFp`.
- State: FAILED_OR_AMBIGUOUS; no replay was attempted.

Database inventory is still one pilot, one machine request and zero validated pilot evidence rows. No new or equivalent fresh attempt already exists. Historical workflow events remain 75, with unchanged ordered payload digest `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`. Grading activation remains false.

No story, prompt version, historical candidate, canonical ruleset/score, approval, F8 authorization, render or publication was changed. The assistant issued no commit or push.

## 8. Fresh paid experiment — pending, not executed

The current user approval authorized only the listed cache cleanup. The attachment authorizes deployment but explicitly requires a **new separate paid approval after runtime verification**. Earlier experiment approval cannot be reused.

Proposed exact next operation:

| Item | Bound |
| --- | --- |
| Purpose | One new SOURCE_FIDELITY review of the exact four prompts above |
| Provider/model | OpenAI / gpt-6.1-sol |
| API/output | Chat Completions / strict json_schema |
| Reasoning | low |
| Completion ceiling | 4,000 total tokens |
| Maximum authorized inference cost | **USD $0.30** |
| Requests | One; fresh pilot, durable request ID and idempotency key |
| Automatic retry/fallback | None |
| Critic execution | None |
| Optional pilot accounting ceiling | $0.60, reservation only; no permission for critic requests |

The offline representative response requires approximately 3,047 visible tokens using a documented tokenizer proxy. Low reasoning and compact instructions reduce the verified risk but do not guarantee a valid real response within the shared 4,000-token allowance. No token limit or model will be changed during a future approved execution.

If approved, recheck health/free space/bindings, create the exact fresh pilot through authenticated application APIs, persist an explicit low source authorization, enable guarded dispatch only for that one execution, preserve the real result, and disable both flags again even on failure. Stop on ambiguity or rejection. UNKNOWN/FAIL may be legitimate completed machine judgments; do not force PASS.

## 9. Real outcome fields at this stopping boundary

- New pilot/request/provider IDs: **not created**.
- New input/completion/reasoning usage: **none available; inference not executed**.
- New visible output length / finish reason: **not applicable**.
- New JSON/citation validation: **not performed on a real response**.
- New source-fidelity judgments, omissions, conflicts and uncertainties: **not collected for any of the four subjects**.
- New real request cost: **no new inference made; no usage/cost result exists**.
- Previous calculated ~$0.0554 remains historical evidence, not new spending authority.
- Post-verification dispatch: **disabled in both services**.
- Critic A/B eligibility: **not yet eligible for execution authorization under this task's sequence**; a completed new source review is required first, then critics require their own explicit approval.

## Evidence

`cpq-source-fidelity-deployment-evidence/` contains the exact approved cache list and cleanup results, initial blocked report, revised sequential-build plan, official ML/backend deployment logs, deployed-image mock results, live capabilities, four live source contexts, final deployment/security verification and historical integrity comparison. No credentials or session tokens are included.
