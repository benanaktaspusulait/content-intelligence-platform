# Owner-managed AI creative quality pilot V1 — implementation report

Date: 2026-10-15. Owner-authorized engineering implementation; **zero real AI calls**. Mocked reviews prove transport/contract readiness, not creative effectiveness. Real owner credentials have deliberately not been created.

## Real Mimi binding repairs

`CreativePromptQualityService` now resolves saved production context from the current authoritative PRODUCTION_SETTINGS event plus the current exact-prompt REVIEW execution binding. Event-owned contentProfile/generator/duration/opening/aspect fields are compared, not overwritten; execution mode/resolution/aspect come from persisted boundRequest. Top-level and nested aspect-ratio conflicts, differing bound prompt, mismatching generator/profile/duration, unsafe metadata and missing settings are rejected. Provenance retains both settings-event UUID and execution-analysis UUID. No execution default or historical AUTO content profile is substituted. Existing records are unchanged.

For Mimi, settings event `2d90c69b-bcec-4871-9c4e-7e029906c974` joins analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18` to produce ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15 seconds / image2video / 480p / 9:16. Existing openingStrategy AUTO is its explicit saved opening setting, separate from the obsolete AUTO content-profile footer in the unchanged prompt.

One verified story resolver serves original and candidate review/import. It supports actual session `storyRecordId` and legacy `sourceStoryRecordId`, rejects contradictory aliases and role/session revisions, and uses existing `WorkflowService.approvedStoryForCpq` to validate current approval and exact candidate revision. Distinct values stay distinct:

- Source story: `bc1cf798-d20b-4b98-8b73-56e1581c3afc`.
- Approval record: `20b77d13-848d-46d0-ab4b-bb9b6efb0836`.
- Text revision: `candidate-2-revision-7c63cc86`.
- Approved story SHA-256: `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`.

Real-saved-input disposable tests now accept authenticated original and three candidate fidelity submissions as **UNKNOWN**, not invented PASS. Original preflight succeeds; all exact prompt hashes and source bindings match. An explicit real-input contradictory-aspect test blocks with PRODUCTION_SETTINGS_CONFLICT. Canonical 88.40625/B and full historical workflow digest remain unchanged. Existing simplified candidate fixture was strengthened to include a genuine disposable story/approval revision rather than bypass the new verified resolver.

## Single-owner authentication

`CpqOwnerAccess` and `CpqOwnerController` implement a narrow local mechanism. Credential is read from an external file, at least 32 characters; only its SHA-256 remains in the access bean, checked with constant-time comparison. It is distinct from rule-governance credentials. Missing identity, missing/short/unreadable credential disables authentication. No production owner or temporary credential was generated.

Owner session uses servlet-managed session identity, rotates ID on login, expires after 30 minutes idle and supports logout. Session cookies are HttpOnly and SameSite=Strict; direct TLS uses the container's Secure-cookie behavior. Local HTTP is published on loopback only. Remote plain HTTP is rejected; forwarded headers cannot impersonate TLS or a principal. Remote deployment requires direct backend TLS or a separately reviewed trusted TLS proxy configuration; current local nginx does not supply such remote trust.

Session-bound CSRF is required for login/logout and owner-authenticated state-changing CPQ requests through `X-CPQ-CSRF`; supplied Origin must match the request origin. CSRF nonce remains in frontend memory. Credential is cleared from the input immediately and never stored in localStorage. Five unsuccessful login attempts within 15 minutes limit an IP; bounded attempt state avoids unlimited memory growth. No raw secret is logged or returned.

The owner receives OWNER, PRODUCTION_OPERATOR, ARCHITECTURE_APPROVER and CREATIVE_QUALITY_ARCHITECTURE_APPROVER capabilities only on the narrowly protected CPQ routes. The owner is **not** assigned EVIDENCE_REVIEWER or CREATIVE_QUALITY_REVIEWER. Existing independent human routes retain those requirements and self-review checks. No authenticated owner can impersonate two humans.

### Private owner setup — performed locally by the actual owner

A small local helper now performs these steps when the actual owner runs it interactively:

```sh
./intelligence/scripts/setup-cpq-owner.sh
```

It asks the owner to choose their own identifier, creates/reuses an external private credential and owner profile, invokes the official backend deployment with real dispatch disabled, and prints only local login/copy instructions. It never prints the credential or overwrites an existing one. Future runs reuse the private identity/configuration, avoiding loss of the owner ID on later deployment. `--check` is read-only. Noninteractive invocation refuses setup before any identity/credential creation. Shell syntax, live read-only check and noninteractive refusal were verified; the actual interactive setup was deliberately not executed by the assistant. This helper changes no runtime artifact until the owner runs it.

The manual equivalent remains below.

Do not paste credentials into this conversation. Keep real dispatch disabled during authentication setup.

```sh
umask 077
mkdir -p "$HOME/.config/pompom-owner"
chmod 700 "$HOME/.config/pompom-owner"
python3 - <<'PY'
from pathlib import Path
import secrets, os
path = Path.home() / '.config/pompom-owner/credential'
# Refuse to overwrite an existing owner credential.
with path.open('x') as handle:
    handle.write(secrets.token_urlsafe(48) + '\n')
os.chmod(path, 0o600)
PY
printf 'Choose your local owner identifier: '
IFS= read -r CPQ_OWNER_ID
export CPQ_OWNER_ID
export CPQ_OWNER_CONFIG_DIR="$HOME/.config/pompom-owner"
export CPQ_PILOT_REAL_ENABLED=false
./intelligence/scripts/deploy.sh backend
```

Keep the owner ID/config-directory variables in private local deployment configuration for later runs. Compose mounts the directory read-only **only into backend** at `/run/pompom-owner`; CPQ_OWNER_SECRET_FILE points to its `credential`. ML/render/frontend do not receive that file. On the Mac, the owner may locally copy the credential with `pbcopy < "$HOME/.config/pompom-owner/credential"`, paste it into the local login field and clear their clipboard afterwards; never expose it in screenshots/reports or send it to the assistant. This is a setup instruction, not an action executed by this task. Missing configured credentials remain an explicit pending operator action.

## Ungraded evidence and persistence

V65 adds three narrowly scoped tables; V62–V64 remain unchanged:

- `cpq_owner_pilots`: immutable owner-confirmed exact snapshot, policy, source/settings/prompt bindings and total budget ceiling.
- `cpq_machine_requests`: durable authorization, slot, exact input/hash, request/idempotency identity, reserved ceiling, execution state, raw response/failure and timestamps.
- `cpq_pilot_evidence`: append-only MACHINE_REVIEW or OWNER_DECISION. Machine entries reference a unique request; owner decisions cannot masquerade as requests or independent human reviews.

No pilot row is inserted into existing human fidelity/judgment/calibration tables. Existing calibration importer remains strict; machine-only pilot material is stored in this explicitly ungraded path and excluded from authoritative activation. All existing canonical/F8/render services remain unchanged.

Policy is exactly `OWNER_MACHINE_PILOT_V1`. Creation requires authenticated owner, current verified source/settings, selected real saved candidates, explicit source-authority confirmation and a bounded total budget. Creation makes **no provider call** and is not a semantic fidelity decision. Every later write revalidates current persisted bindings and owner. Stale snapshot, source, prompt, production context or analysis blocks further action.

Machine evidence includes purpose/slot, provider/model/version, policy/rubric, exact request and input/output fingerprints, complete response, cited dimension/source judgments, uncertainty, usage/cost, execution/failure and authorization. Request input contains exact prompt fingerprints and authoritative production settings; pilot snapshot holds source SHA/revision/settings fingerprint. Raw rejected received responses are retained on the request; ambiguous failures block automatic retry and subsequent stages. No generated rationale is treated as independent human evidence.

## Three independent machine stages

Existing `CreativeCapabilityProvider` and configured Adaptive V3 profile catalog are reused; no model-name fallback or separate provider framework was introduced. ML module: `app/workflow/owner_machine_pilot.py`.

1. SOURCE_FIDELITY receives approved story, exact original and four selected variants with exact changed-beat evidence. Where older structured changeContract is empty, deterministic matching timeline-line differences supply quoted changes, explicitly not semantic proof. It checks six anchors, additions/omissions, timing/order/ending and changed beats. Exact quote mismatches reject output. Missing anchors/changed-beat coverage or conflicts/additions/omissions prevent PASS and preserve UNKNOWN/REVIEW_REQUIRED. Its configured provider/model cannot equal any known candidate-generating identity; missing generator identity blocks authorization.
2. CRITIC_A independently receives full neutral prompt packets and effective production settings.
3. CRITIC_B independently receives the same review objective and prompt set in its own saved reproducible presentation order. Neither critic sees the other response, source judgment, optimizer rationale, provider ranking, canonical score, intended grade or popularity.

Each critic must return all six dimensions with allowed level, concrete strengths/weaknesses, exact prompt citations, actionable suggestions, production constraints, rationale and uncertainty. Strict JSON Schema is validated for schema-capable and JSON-only adapters alike. Missing/malformed fields, wrong quotes/subjects and extra grade fields reject output. Unsupported verified audience/render claims are explicitly surfaced. Source checker PASS remains machine-supported fidelity only; it cannot produce existing human-qualified PASS or satisfy F8.

Comparison preserves dimension-level agreements/disagreements, exact shared weakness strings, individual risk/hypothesis/unsupported-claim evidence and both positions. Disagreements are not averaged. “Material improvement” remains INSUFFICIENT_EVIDENCE until an owner examines defensible evidence; there is no artificial algorithmic promotion from two positive reviews. Same-provider/model-family bias is disclosed. Two machine executions are not two independent humans.

## Exact Mimi wiring and Step 6

Original and all three existing candidates remain byte-identical:

| Neutral ID from existing prepared pilot | Saved subject | SHA-256 |
|---|---|---|
| Q01 | e651eb75-b894-477d-ae77-0fe6e05236da / candidate-a | 90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495 |
| Q02 | 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-a | 218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749 |
| Q03 | 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-b | 2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746 |
| Q04 | Content10 / Prompt10 / version1 original | 0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98 |

`data/workflow/cpq-pilot-blind-manifests-v1.json` preserves the prior prepared supervisor mapping and reproducible orders: Critic A Q04,Q01,Q02,Q03; Critic B Q02,Q03,Q01,Q04. The generic service verifies hashes against current saved subjects and contains no Mimi-specific parsing/score rules. Other source groups can use deterministic hash-based ordering; all variants in a pilot share the same story/settings and remain outside human calibration partitions.

`CpqOwnerPilotComponent` is inside the existing Step 6 Creative Optimization area, including the latest empty-comparison state. It shows separate official grading, canonical context, machine/human/source status and render limits. “Inspect owner pilot” performs read-only inspection. It includes source/settings/exact original/candidate disclosures, explicit owner login, pilot creation/load, model/budget/consent authorization, a separate one-request execute control, machine results/disagreement/risk details, and explicit KEEP_ORIGINAL / REQUEST_REVISION / ACCEPT_TEXT_FOR_PREPARATION decisions. Acceptance for preparation is not candidate/prompt approval and requires all stages completed, exact chosen subject and explicit limitations/no-render acknowledgement.

Opening Step 6 does not create pilot evidence, issue authorization or run inference. A live check caught candidate-array input identity repeatedly clearing/reloading the resolved context; ngOnChanges now reacts only to actual analysis/comparison/candidate identity changes, with a regression test.

## API and cost boundaries

Prefix `/api/v1/intelligence/workflow`:

| Route | Action |
|---|---|
| GET `/owner-auth`; POST `/owner-auth/login`; POST `/owner-auth/logout` | Session state, CSRF-protected owner login/logout |
| GET `/cpq/owner-pilot/capabilities` | Safe configured model identities/limits; no SDK/inference |
| GET `/cpq/owner-pilot/context?analysisId=...&comparisonId=...&candidateId=...` | Read-only exact persisted context |
| POST `/cpq/owner-pilot` | Explicit owner preparation; no inference |
| GET `/cpq/owner-pilot/{id}` | Owner's saved evidence and comparison |
| POST `/{id}/authorizations` under owner-pilot | Exact slot/provider/model, maxOutputTokens/maxCostUsd, idempotencyKey, authorizePaidInference=true and automaticRetries=false |
| POST `/{id}/requests/{requestId}/execute` | Separate explicit execution of one durable authorized request |
| POST `/{id}/decisions` | Append OWNER_DECISION with rationale, exact subject where required and no-render confirmation |

Default `CPQ_PILOT_REAL_ENABLED=false` gates **both backend and ML**. Configured API keys never bypass this. ML additionally requires the existing internal Adaptive-dispatch HMAC key and an exact signed request body; it does not accept owner credentials. Backend requests transition to DISPATCHING durably before transport with atomic claim/advisory serialization; replay returns existing state. Unresolved dispatch/failure prevents subsequent calls. Each slot has one immutable authorization and no automatic retry, fallback or escalation. Reservation is serialized against the total pilot ceiling. Preflight budget/context limits use conservative byte/schema/output token bounds and verified local profile pricing; real usage/model/cost are checked after response. Costs missing or above the authorized ceiling stop the pipeline rather than claiming success. No historical provider authorization is reused.

## Smallest subsequent real experiment — proposed, not executed

After private owner configuration, separately authorize one SOURCE_FIDELITY batch, one CRITIC_A batch and one CRITIC_B batch over the four exact prompts: **at most three inference requests total, one per slot, zero retries**. Prefer source OpenAI configured profile, Critic A DeepSeek configured profile, Critic B OpenAI configured profile, after checking generator separation and live readiness. Source and Critic B are separately executed but may share a model family; this limitation remains visible.

Proposed total cap **USD0.60**: SOURCE_FIDELITY at most0.30; CRITIC_A at most0.10; CRITIC_B at most0.20; at most4,000 output tokens per request. These are owner ceilings, not promised actual costs. Current source/settings/schema token bounds must fit each reservation before dispatch. If a configured model is unavailable, cost/model/contract fails, or dispatch is ambiguous, stop; no second attempt without fresh review/authorization. Configuration/catalog presence does not establish live model availability or quality. This report grants no paid authorization.

## Verification, deployment and remaining boundaries

Focused tests and live verification are recorded in `cpq-owner-machine-pilot-v1-evidence/` and the deployment addendum below. Write-path tests use disposable PostgreSQL and mocked machine transport. Fixture outputs are explicitly labelled TEST_FIXTURE. No result is described as a real quality improvement or human review.

Earlier implementation/test iterations caught and fixed a reserved SQL column name in new V65 before production migration, an obsolete migration-version assertion, a simplistic legacy test approval fixture, and a malformed test-provider counter. Existing acceptance assertions were preserved/strengthened. Known earlier broader-suite failures remain as documented in the prior intake report; this focused work does not establish a clean full-suite baseline.

No paid providers, real machine evidence, human review, owner credential, story approval, candidate/prompt approval, new prompt version, A/A+ activation, image/video generation, publication, F8 authorization, direct production SQL mutation, historical overwrite, Docker prune, commit or push was performed. Flyway schema changes are the authorized production database writes.


## Final verification and deployment addendum

Focused results: **52 distinct backend tests passed** (20 real/original/pilot integration, five auth/filter security, 26 platform integration, one V61→V65 backward-compatibility migration). The exact neutral-order and final explicit fingerprint envelope changes were additionally rerun against disposable real saved Mimi inputs and passed. **77 frontend tests passed**, including no automatic dispatch/write, fail-closed unconfigured state, in-memory CSRF/credential clearing and the live-found candidate-array reload regression. **47 ML CPQ/Adaptive/pilot tests passed**. Actual real inference count: **0**, actual spend: **USD0.00**.

ML fixtures validate separate source/critic execution, exact six-dimensional/schema/citation contracts, rejected extra grade fields, malformed response retention, missing anchors/conflict/omission UNKNOWN, blind metadata/hash rejection, exact authorization/model/budget/output limits and unsigned/direct paid dispatch refusal. Backend real-data tests validate four authenticated fidelity requests without invented semantic PASS, exact source revisions/fingerprints, contradictory settings, distinct mocked slots/request IDs, repeat prevention/idempotency, early owner acceptance refusal, explicit owner decisions, no averaging and no human calibration writes/activation. Fixture opinions are labelled TEST_FIXTURE; no real creative-quality conclusion follows. Security tests cover missing/invalid credentials, rate limiting, session owner roles/timeout/logout, CSRF/origin checks and remote HTTP denial. Live cookie flags and anonymous denial were checked separately; authenticated live use awaits actual owner configuration. No test weakens human calibration policy.

Warnings/limits: ML has 244 existing datetime.utcnow deprecations; frontend reports existing unused-import warnings; backend reports existing Mockito/JDK attachment and SpringDoc/default diagnostic warnings. Prior broader-suite failures recorded in the intake report remain unresolved and were not relabelled unrelated. A green focused suite is not a clean full-suite or real-provider effectiveness claim.

Deployed changed services through official `./intelligence/scripts/deploy.sh ml-service backend frontend`; final backend fingerprint-envelope update through `./intelligence/scripts/deploy.sh backend`. Flyway is now **65**. Runtime identities:

| Service | Final image | Verification |
|---|---|---|
| Backend | sha256:32888e142e59a3e67d1c798e4f6d21aad5289939ea91a3500d887c7fafdfbb87 | Docker healthy; actuator/database UP |
| ML | sha256:734e76e603c5542e1c4d7d2018b4ad89bceb4c260d65e7b1e8795beb2f0da243 | Docker healthy; /health UP |
| Frontend | sha256:d5191a437f0a7917324a10f8459279a72b79d9655fd196b904cb958b8b8c00c5 | Root/API HTTP checks passed; real Chrome inspected |

All three HTTP ports publish only on 127.0.0.1. Owner credential mount exists only in backend; no credential file or owner identity was created. Backend and ML real-dispatch feature gates remain false. Safe capability API confirms locally configured keys for `deepseek-primary` → `deepseek/deepseek-v4-pro` (documented DeepSeek-V4-Pro-0813), and `openai-escalation` → `openai/gpt-6.1-sol`. Configured input/output prices are respectively1.32/3.96 and2.50/10.00 USD per million tokens; live availability is UNVERIFIED_NO_PROVIDER_CALL. These are actual local catalog/configuration values, not an inference test or permission to spend.

Live nginx API checks: original plus all three saved candidate contexts resolve with no blockers; missing CSRF login403; unconfigured login with valid anonymous session CSRF401; anonymous pilot creation403; unsigned/disabled ML dispatch403. Session cookie is HttpOnly, SameSite=Strict; local HTTP correctly has no Secure flag. No cookie/CSRF/secret values are stored in the report or evidence JSON.

Actual final Chrome Step6 inspection showed the pilot in the latest empty-comparison state, opened its read-only context, and visibly confirmed original hash, distinct story/approval/revision and effective settings. Selected historical comparison9275... and CandidateB only for CPQ inspection; the pilot visibly switched to exact hash2151ed... with the same approved source/settings. Official canonical score remained88.40625/B, CPQ grading inactive, independent human evidence UNKNOWN, machine NOT_EXECUTED and render readiness BLOCKED_PENDING_EVIDENCE. A screenshot was visually inspected inline in the tool transcript. No authenticated owner write was attempted. Initial browser offline/closed surfaces were recovered by reopening the project Chrome profile without restoring unrelated tabs. No credential, paid-consent checkbox, candidate approval or render control was used.

Before V65, a custom-format PostgreSQL backup was taken at `/Users/benanaktas/Library/Application Support/Pompom Hills/Recovery Backups/cpq-owner-v65-20261015/pompom-before-v65.dump`; SHA-256 `0ec6d1c24486496f75b997107b2f18a7b3f01109cdfce86f3f210ff60911f17f`. Host headroom was inspected throughout. It reached211MiB during build/application memory pressure; only this task's reproducible85MiB host target JAR was removed. No Docker data/cache/volume prune occurred. Final observed host headroom recovered to2.3GiB. Disk remains constrained; no unrelated cleanup was performed.

Production integrity after final browser/API verification: Prompt10/version1 hash unchanged;75 workflow events/eight optimization comparisons unchanged; ordered full historical payload digest remains `e7e55725c68f7c27d61183b854b4b1b7799b410814acde27ca2db69fa3190275`. All preexisting CPQ assessment/fidelity/corpus/example/judgment/original-subject counts remain0; new ownerPilots/machineRequests/pilotEvidence are also0. Existing policy activated=false. Only schema changed64→65. Canonical Ruleset1.11, provider responses, story/production settings and F8 gates were not changed.

## Independent result flags

| Flag | Result |
|---|---|
| REAL_MIMI_BINDINGS | VERIFIED |
| OWNER_AUTH | IMPLEMENTED_AWAITING_CONFIGURATION |
| MACHINE_REVIEW | IMPLEMENTED_MOCK_VERIFIED |
| SOURCE_FIDELITY_MACHINE_STAGE | IMPLEMENTED_MOCK_VERIFIED |
| OWNER_MACHINE_PILOT | READY_FOR_AUTHORIZED_REAL_RUN |
| REAL_MACHINE_CREATIVE_EVIDENCE | NOT_COLLECTED |
| CPQ_GRADING | INACTIVE |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED |

READY_FOR_AUTHORIZED_REAL_RUN means implementation/mock/live-readiness is complete; the actual owner must privately configure authentication, then provide separate exact three-operation provider/budget authorization and enable the guarded dispatch configuration. No real result or creative superiority has been established, and no run is silently authorized by this report.


### Continuation: private setup handoff

Live read-only recheck still returns owner configured=false/authenticated=false; backend and ML real dispatch remain disabled and official grading INACTIVE. Added `intelligence/scripts/setup-cpq-owner.sh` for the owner's local interactive setup. No production credential, owner identity, pilot evidence or model call was created during preparation. No application source changed and no additional deployment was necessary for this helper/documentation-only continuation.
