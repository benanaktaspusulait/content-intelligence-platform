# First real AI pilot preflight — 16 October 2026

## Decision

GO for requesting the separately bounded paid-test authorization, not for dispatch. Real Chrome login and logout succeeded previously. A fresh local application HTTP session now independently verified valid credential login (200), authenticated CSRF rejection (403), logout (200), subsequent authenticated=False and write rejection (403). This establishes the configured credential and server authentication are working. The earlier browser re-login failures were 401, rather than CSRF failures; the exact unsuccessful input/clipboard cause is not established and is not reported as an application defect. The browser is currently anonymous; no authenticated browser session is claimed to remain open.

Result: **MIMI_REAL_AI_PILOT_READY_FOR_OWNER_AUTHORIZATION**, limited to the exact envelope below. Live model availability and creative quality remain unverified.

| Status | Value |
| --- | --- |
| DISK_HEADROOM | SAFE for current running stack and bounded read-only preflight; avoid broad builds |
| OWNER_AUTH | CONFIGURED_VERIFIED — live browser login/logout plus fresh local HTTP security verification |
| MIMI_BINDINGS | VERIFIED |
| PROVIDER_PREFLIGHT | READY_UNVERIFIED_LIVE |
| REAL_DISPATCH | DISABLED |
| CPQ_GRADING | INACTIVE |
| REAL_CREATIVE_EVIDENCE | NOT_COLLECTED |
| FIRST_REAL_PILOT | READY_FOR_AUTHORIZATION |

## 1. Disk and deployment health

Host free space: 3.4 GiB on 16 October (previously 4.7–5.0 GiB). This is sufficient for this bounded no-build preflight and small review payloads, but below the desired 10–15 GiB operating headroom. No further build/deployment is authorized by this readiness finding; recheck before dispatch and avoid concurrent disk-heavy work. Backend health UP, frontend HTTP 200, ML/PostgreSQL/render container health healthy. Frontend has no Docker healthcheck in the current compose output. Backend reports roughly 48.8 GiB free inside Docker. Flyway V65 is successful. No deployment, image build, database mutation, prune or cleanup was performed during this preflight continuation. The owner independently ran the official setup/deployment successfully.

Earlier bounded Docker inspection: Docker.raw logical size 128 GiB, allocated approximately 67 GiB; build cache 61.24 GB with 11.43 GB reported reclaimable. These are diagnostics, not deletion permission.

## 2. Cleanup proposals — none executed

Paths below are relative to `/Users/benanaktas/project/video/content-intelligence-platform` unless absolute.

| Exact path | Size / possible recovery | Assessment | Recovery implications / approval |
| --- | --- | --- | --- |
| `intelligence/frontend/.angular` | 26 MiB | Reproducible Angular cache | Slower subsequent build; explicit approval before deletion |
| `intelligence/frontend/dist` | 25 MiB | Reproducible frontend output | Rebuild required for local artifact use; explicit approval |
| `intelligence/backend/target/classes` | 4.9 MiB | Reproducible classes | Recompile required; explicit approval |
| `intelligence/backend/target/surefire-reports` | 4.7 MiB | Audit evidence | Preserve |
| `/Users/benanaktas/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw` | ~67 GiB allocated | Persistent Docker storage | Never delete for this task |

Small reproducible outputs do not recover the desired 10–15 GiB. No unknown user files, volumes, backups or historical evidence were touched.

## 3. Owner helper and authentication

`setup-cpq-owner.sh --check` confirmed configured=True, credential exists=True, owner-only permissions=True. The macOS `/dev/tty` r+ failure was fixed using separate reading/writing streams. Eleven isolated PTY tests passed, including interruption, orphan credential rejection, profile-only resume, unchanged identity/credential reuse, failed deployment resume, noninteractive rejection and read-only check. Syntax and diff checks passed. Test credentials were synthetic, outside the actual owner directory, and deployment was stubbed.

The real owner created the production credential and chose benan. The assistant subsequently transferred the existing credential only for local sign-in at the owner's explicit request; it was not printed, reported or saved in the repository. The OS clipboard was cleared. Browser password saving was declined. No cookie or CSRF token was extracted for reporting.

## 4. Security evidence and limits

- Real deployed login succeeded and displayed OWNER_DECISION authority, explicitly not an independent human reviewer.
- Real logout removed owner write controls; reopening displayed the login form.
- Fresh anonymous POSTs to pilot creation, request authorization and owner decision paths returned 403. The authorization probe used a nonexistent all-zero pilot and invoked no execution endpoint.
- Anonymous logout without CSRF returned 403.
- Existing focused CpqOwnerAccessTest report: 5 passed, 0 failed. It covers missing credentials, rate limits, role scoping, logout revocation, 1800-second idle timeout configuration, CSRF/origin and remote HTTP denial. This report is existing evidence, not a new full-suite run.
- A 30-minute live idle-expiry write attempt was not performed. Servlet timeout configuration and logout are verified; do not label live expiry behavior tested.
- Source inspection shows no credential localStorage/sessionStorage writes; the form value is cleared before the request. No broad browser-storage or log secret dump was made.
- The panel retains its old “Owner session established” message after logout; the visible login form and absent owner controls correctly show anonymous state. This stale status text is a UI limitation, not evidence of an active session.
- Follow-up live local HTTP acceptance: login 200, independentHumanReviewer=False, authenticated write with incorrect CSRF 403, logout 200, authenticatedAfterLogout=False, writeAfterLogout 403. Tokens/cookies existed only in the transient client protocol state and were not reported or persisted. See owner-runtime-security.json. No credential rotation, identity change or security weakening was attempted.

## 5. Exact Mimi bindings

Content 10, immutable prompt 10/version 1; authoritative analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`. Approved story SHA-256 `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`, story `bc1cf798-d20b-4b98-8b73-56e1581c3afc`, approval `20b77d13-848d-46d0-ab4b-bb9b6efb0836`, text revision `candidate-2-revision-7c63cc86`.

| Subject (0 = original) | Exact prompt SHA-256 | Canonical score |
| --- | --- | --- |
| 0 | 0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98 | 88.40625000000001/B |
| 1 | 90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495 | 88.40625000000001/B |
| 2 | 218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749 | 88.40625000000001/B |
| 3 | 2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746 | 88.40625000000001/B |

Subject 1: comparison `e651eb75-b894-477d-ae77-0fe6e05236da`, candidate-a. Subjects 2/3: comparison `9275c94b-fc35-4207-8648-dfd8d166e502`, candidate-a/candidate-b. All four live API responses returned no binding blockers; hashes were recomputed from complete persisted text. Common settings: ABSURD_PHYSICS, SEEDANCE_2_0_MINI, 15 seconds, image2video, 480p, 9:16. Ruleset 1.11. Exact texts and source context are preserved in verified-live-contexts.json; no fixture substitution.

## 6. Models, independence and capabilities

Local configured profiles: source checker and Critic B `openai-escalation`, OpenAI/gpt-6.1-sol; Critic A `deepseek-primary`, DeepSeek/deepseek-v4-pro (documented version DeepSeek-V4-Pro-0813). Both keys are configured; no key was displayed. Live model availability remains unverified. No network provider probe was made.

All three historical candidates record OpenAI/gpt-4o-mini-2024-07-18 generation. The source-checker exact provider/model pair differs and passes the existing local separation policy. It shares the OpenAI provider family with generation; this limitation remains explicit. Critics use different provider families, separate requests, independently blinded saved orders, and do not receive each other's results. All outputs must be MACHINE_REVIEW, never HUMAN_REVIEW.

Local contract: DeepSeek json_object/context 1,000,000; OpenAI json_schema/context 1,050,000. The proposed 4,000 output tokens fit both configured limits. These are local capability contracts, not live availability proof.

## 7. Proposed authorization envelope — NOT AUTHORIZED

| Slot | Exact provider/model | Conservative input bound | Max output | Calculated upper cost | Proposed cap |
| --- | --- | ---: | ---: | ---: | ---: |
| SOURCE_FIDELITY | OpenAI / gpt-6.1-sol | 36,167 | 4,000 | $0.13041750 | $0.30 |
| CRITIC_A | DeepSeek / deepseek-v4-pro | 21,672 | 4,000 | $0.04444704 | $0.10 |
| CRITIC_B | OpenAI / gpt-6.1-sol | 21,672 | 4,000 | $0.09418000 | $0.20 |

Maximum three requests, one per slot, zero automatic retries, fallback or escalation; proposed total cap $0.60. Conservative calculated total $0.26904454. These are byte-based conservative admission bounds using the real system/schema and all four complete saved prompts; not actual token usage. Actual usage/cost remain unknown.

Critic A saved order Q04,Q01,Q02,Q03; Critic B Q02,Q03,Q01,Q04. SOURCE_FIDELITY offline order is illustrative for byte counting; its actual order is derived by the backend from the final immutable pilot snapshot. The request artifact explicitly labels this distinction.

## 8. Real UI and record integrity

Step 6 Repair and Creative Optimization were opened in the existing deployed Chrome tab. The owner panel showed exact context, inactive grading, unexecuted machine fidelity and independent human evidence UNKNOWN. The current selected comparison contains zero candidates; historical comparisons remain separately selectable. Actual browser selection of comparison 9275c94b-fc35-4207-8648-dfd8d166e502 displayed Candidate A and B, 88.41/B each, CURRENT VALIDATION REQUIRED, independent fidelity UNKNOWN, CPQ grading inactive and render BLOCKED_PENDING_EVIDENCE. Historical evidence remains stale. API verification includes all three actual historical candidates. No source-attestation checkbox, pilot preparation, paid consent, candidate approval or owner decision was submitted.

The UI pilot-preparation input uses the currently supplied candidate selection, not automatically all historical comparisons. A four-subject pilot must bind the exact three selectors listed above; do not mistakenly prepare only the current empty comparison. No four-subject persisted pilot has yet been created.

Read-only database checks: 75 historical workflow events, including 8 CREATIVE_OPTIMIZATION records; zero owner pilots, zero machine requests, zero pilot evidence. Policy activation remains false. Current ordered payload snapshot SHA-256 (PostgreSQL payload::text, ordered by id) `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`. This is a new baseline using this exact serialization, not claimed equal to differently serialized prior digests. No historical update/delete was issued.

Backend and ML CPQ_PILOT_REAL_ENABLED are both false. No real-request authorization exists. No inference, candidate generation, prompt version, story change, scoring change, rendering, publishing, commit or push occurred.

## 9. Remaining gates and next action

1. Obtain the owner's separate explicit authorization for the exact four-subject source binding and three-request envelope: SOURCE_FIDELITY OpenAI/gpt-6.1-sol up to $0.30, CRITIC_A DeepSeek/deepseek-v4-pro up to $0.10, CRITIC_B OpenAI/gpt-6.1-sol up to $0.20; total $0.60; 4,000 output tokens per request; no retries/fallback/escalation.
2. After that authorization, prepare the exact four-subject pilot through the official application contract with the three historical selectors above, explicit source confirmation and $0.60 total reservation. Do not prepare only the currently selected comparison or treat saved historical comparison evidence as current.
3. Recheck free space/health, exact bindings, model configuration, idempotency and existing request state before enabling dispatch. Keep both feature flags false and create no paid-request authorizations until separately authorized. The configured but live-unverified models must not be substituted automatically.
4. Verified Mimi character reference and accepted start frame remain independent Step 7/F8 requirements. Text evaluation does not authorize rendering.

No creative A/A+ success is claimed. This report establishes bounded operational, source-binding, authentication and budget readiness; live idle-expiry timing was not exercised. No full-suite pass or real-model effectiveness is claimed.
