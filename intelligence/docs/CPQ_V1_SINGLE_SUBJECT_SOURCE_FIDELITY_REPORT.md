# SOURCE_FIDELITY SINGLE-SUBJECT V1 — offline acceptance

Date: 2026-10-16. **Focused implementation verified offline; not deployed. Zero new paid provider calls.** This is contract readiness, not a successful real source review or proof of creative quality.

## 1. Confirmed bottleneck and measurements

Read the completed real experiment, output-budget correction and owner-pilot implementation reports, both durable real requests, existing schemas/validators, authorization/persistence, state machine, provider adapter and Step 6 component.

The two real four-subject attempts exhausted all 4,000 completion tokens as reasoning and returned no visible JSON: high used 6,161 input tokens; low used 6,245. The latter calculated cost was $0.05561250. Neither produced semantic evidence. No confirmed story conflict explains these failures.

The previous compact data payload is 24,167 UTF-8 bytes. It includes four copies each of the same story and original prompt: three redundant story copies total **1,722 bytes**, and three redundant original copies **5,508 bytes**. Prompt content alone: original 1,836 bytes; candidate 1 2,296; candidate 2 1,907; candidate 3 2,026. Extra copies contribute size; they do not establish the cause of hidden reasoning consumption.

Before changing application contracts, an original/candidate-only offline prototype was measured (`phase1-prototype-sizes.json`). Every prototype was materially smaller, so implementation proceeded. The final schema adds stronger source/event binding and remains materially smaller overall.

Final measurements serialize the actual mocked SDK call arguments (model, messages, strict schema and token settings). Estimates use the existing temporary **tiktoken/o200k_base proxy**, not a claim about the exact model tokenizer or actual provider input billing. The full serialized-request estimate includes schema/wrapper material and differs from the real provider's 6,245-token count.

| Request | Serialized bytes | Estimated input tokens | Representative visible JSON bytes | Representative visible tokens |
| --- | ---: | ---: | ---: | ---: |
| Previous four-subject batch | 27696 | 6637 | 12021 | 3047 |
| Original | 8674 | 2095 | 3640 | 1037 |
| Candidate 1 | 10175 | 2401 | 4555 | 1236 |
| Candidate 2 | 9397 | 2260 | 4166 | 1166 |
| Candidate 3 | 10049 | 2404 | 4643 | 1278 |

Original-only serialized bytes fall approximately **68.7%**, with estimated input falling approximately **68.4%**. Candidate requests are also materially smaller. Response examples are **TEST_FIXTURE**, not actual judgments. They preserve event/anchor evidence and changed execution quotations; output can be larger for real findings.

The old source schema is 1,056 compact bytes; the new single-subject schema is 1,674 bytes. Keeping the full evidence contract adds schema bytes while removing three full prompt packets and unnecessary original copies. No production tokenizer dependency was added.

## 2. Minimal application changes

- `ml-service/app/workflow/owner_machine_pilot.py`: reuse the existing source judgment, schema, adapter and validators with `evaluationUnit=SINGLE_SUBJECT_V1`. One packet only, source-specific low effort, unchanged 4,000 ceiling, retries zero, exact authorized subject/source/settings checks. Historical batch validation remains compatible.
- `backend/.../workflow/CpqOwnerPilotService.java`: new pilots use single-subject source requests. Build the one exact subject from persisted snapshot data; omit full `originalPrompt`. Candidates receive only saved changed-beat original/new execution context, rather than a complete duplicate baseline. Bind authorization to `subjectPromptSha256`; persist normal immutable evidence with exact request/input/output/source/settings bindings. Add a deterministic per-subject aggregate and use it for critic execution and text-acceptance gates.
- `backend/.../db/migration/V66__cpq_single_subject_source_requests.sql`: nullable subject SHA for legacy records, separate partial uniqueness for legacy/critic slots and scoped source slots. Existing pilot/idempotency uniqueness remains. This migration is necessary because V65's unique `(pilot_id,slot)` cannot represent four independent source requests.
- `frontend/.../cpq-owner-pilot.component.ts`: small existing-panel additions for subject selection/status, validated count, missing IDs, conflicts/manual review and aggregate readiness. Show exact subject on each authorization. No writes on open; no automatic authorizations or inference. Stable profile tracking also fixes an option-recreation change-detection loop exposed by the authenticated-panel tests. Loading another pilot clears paid consent and source selection.
- Tests: new `test_single_subject_source_fidelity.py`; extended `OriginalCpqFidelityIntegrationTest`, `CpqV62MigrationTest`, and `cpq-owner-pilot.component.spec.ts`.

No optimizer, ruleset, creative scoring or new evaluation framework was added.

## 3. Source contract and complete evidence

Every packet retains the entire approved source story, exact selected prompt, authoritative production settings, all six protected anchors and all saved changed beats. `sourceBinding` includes exact prompt/story/settings SHA-256, saved source identity, story ID, revision and approval record ID. The response must echo that binding exactly.

All **nine exact approved-story sentence spans** are enumerated with event IDs and Unicode code-point offsets. This generic segmentation preserves literal source coverage, including the note's wording, finger attachment, splitting, doubling, bodily coverage, mirror/scream, overwhelming quantity, sneeze/cabinet return and relief/messy cabinet ending. These spans are not newly invented semantic events or timings. Numeric 2→4→8 instructions remain in the exact production prompt and are compared to the story's doubling rule, not fabricated as literal numeric source text.

The reused subject judgment requires neutralId, decision, rationale, uncertainty, conflict, omissions, additions, mappings, productionRisks and sourceBinding. Each mapping requires anchor, beatId, exact sourceQuote, exact promptQuote, eventId and consistency PASS/FAIL/UNKNOWN. The strict results array contains exactly one subject.

Validation requires all six anchors, every complete source sentence quotation and every changed beat. Each changed beat additionally requires a quotation of its complete saved `newExecution`, so citing an unchanged action with the same beat ID is insufficient. Source/prompt quotations must be literal bound text, source quotes must belong to the identified source span, subject/fingerprints must match, and extra fields/malformed/truncated/empty output are rejected.

A missing prompt quote may be represented as an empty string only with a non-PASS consistency judgment and an overall non-PASS result; absent evidence is not invented. Missing required coverage rejects the new single-subject result. A PASS with conflict, omission, addition, non-PASS mappings or unsupported success/audience claims is rejected. A complete legitimate UNKNOWN or FAIL remains technically completed machine evidence. Backend independently rechecks single-source bindings, citations, coverage, visible output and accounting before persistence and during aggregation.

Instructions retain semantic comparison of event order, causal consequences, timing, character/object continuity, unsupported assumptions, omissions/additions and production risks. Exact hashes, sentence coverage and quotation checks establish provenance/structural coverage; **they cannot independently prove semantic fidelity**. That remains the model's evidence-backed assessment. No MACHINE_REVIEW becomes HUMAN_REVIEW.

## 4. Durable isolation, compatibility and completeness

One immutable story-bound pilot still contains the exact full subject set. Each source authorization must name one valid `subjectPromptSha256`; unknown/missing subjects are refused. There is no authorizing one subject on behalf of the other three.

Each `(pilot, SOURCE_FIDELITY, subject SHA)` has one immutable authorization and independent request ID, idempotency key, model, reservation, usage, response and failure. Repeating the same exact key returns saved authorization; reusing it with another body conflicts. A different key cannot bypass an existing subject authorization. Failed/ambiguous execution is never replayed. Under existing policy, another attempt needs a fresh pilot and fresh explicit authorization, not a silent request reset. Critic A/B retain one slot each.

A running request serializes dispatch. A failed source subject does not prevent a separately authorized other source subject from executing and cannot erase completed source evidence. It remains missing from aggregate completion and blocks downstream critique. Unresolved critic failures retain the existing restriction. CAS persists DISPATCHING before transport; no automatic follow-up is introduced.

Legacy pilots retain their historical snapshot interpretation and batch identity. New create commands always select the single-subject mode; callers cannot opt back into batch by supplying snapshot fields. V66 adds a NULL column for old rows without rewriting their inputs, responses, authorizations or state. Disposable upgrade tests compared both real failed row payloads before/after migration, excluding only that new NULL column: identical. Historic batch/idempotency behavior remains tested.

Per subject, the backend exposes NOT_EXECUTED, AUTHORIZED, RUNNING, COMPLETED_WITH_EVIDENCE, FAILED_OR_AMBIGUOUS or REVIEW_REQUIRED, plus **a separate semanticVerdict only when validated evidence exists**. Transport failure never becomes a machine UNKNOWN judgment.

Aggregate fields: requiredSubjects, validatedSubjects, conflictSubjects, manualAdjudicationSubjects, missingSubjectIds, complete and criticGateSatisfied. Evidence is associated with a completed request belonging to the same pilot and checked against exact input hash, prompt bindings, source revision/binding and production settings. Unrelated pilot/story/revision evidence cannot certify the subject.

All required subjects must have validated evidence. Complete UNKNOWN/FAIL evidence counts technically, but remains REVIEW_REQUIRED. For new single-subject pilots, unresolved UNKNOWN/FAIL, conflict, omission/addition, validation notices or unsupported claims keep the critic gate closed. This is intentionally conservative; no automatic owner-adjudication override was added. Historical batch interpretation is retained. Completing only the original leaves three missing reviews and cannot enable critics. Text acceptance still additionally requires both independent critic results; none of this authorizes render or official grading.

## 5. Exact Mimi data and integrity

Content 10, immutable Prompt 10/version 1; authoritative analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`; Ruleset 1.11; **88.40625/B unchanged**. Common approved-story SHA: `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`. Settings: ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15s / image2video / 480p / 9:16.

| Subject | Exact saved reference | SHA-256 |
| --- | --- | --- |
| Original / Q04 | Content 10, Prompt 10/version 1 | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` |
| Candidate 1 / Q01 | e651eb75-b894-477d-ae77-0fe6e05236da / candidate-a | `90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495` |
| Candidate 2 / Q02 | 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-a | `218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749` |
| Candidate 3 / Q03 | same comparison / candidate-b | `2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746` |

Hashes were recomputed from saved full text; none was reconstructed. Java builds each exact single packet from the disposable real saved workflow data and tests compare its output with the measured prototype packet. ML tests independently recompute prompt/story/settings hashes and validate the same packets.

Read-only production verification: both previous failed durable rows equal their archives; request count remains 2, validated evidence count 0, workflow event count 75 and ordered payload digest `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8` unchanged. Production remains V65, both dispatch capability flags false, CPQ activated=false. No new production pilot/request or credentials were created.

## 6. Tests and limitations

- **ML: 106 passed** across single-subject, prior output-budget, owner-machine pilot, Adaptive V3 and CPQ V1 suites; mocked SDK transports only, 244 existing datetime.utcnow warnings.
- **Backend: 31 passed**, zero skipped/errors/failures: 24 original/pilot integration tests, five owner-auth tests, two migration tests. Disposable PostgreSQL containers, no production writes; ML mocked. V65→V66 preserves both archived real failed batches. V61→V66 preserves append-only calibration history.
- **Step 6 frontend: 118 passed** across quality-validator specs, including eight owner-pilot tests. Opening remains read-only; exact subject authorization, no implicit execute, missing candidate gate and duplicate-subject controls verified. No live UI claim: deployment is prohibited in this task.
- **Broader frontend: 343 passed, seven failed, eight uncaught errors**, all failures in untouched `video-detail.page.spec.ts`, including a missing mocked `getCaptionVersionsByVideo` service method and page expectation mismatches; baseline pre-existence was not established. This is not a clean full-frontend regression result. These failures were not repaired as part of source review scope.
- `git diff --check` passed. No Docker rebuild, deployment, prune, volume deletion, backup removal, provider calls, story edits, approval, generation, grading activation, commit or push was performed by this task.

Acceptance covers original/candidate-only construction, six anchors, full source/event/changed-execution evidence, exact bindings, complete UNKNOWN evidence, unsupported PASS/missing coverage/invented quotes/events/wrong IDs/hashes rejected, malformed/empty/length/reasoning exhaustion retained, per-subject idempotency/replay denial, failed-candidate isolation, incomplete and complete aggregates, unresolved review gate, historical migration compatibility, owner/security boundaries and unchanged canonical/grading/render state.

All mocked responses are labelled **TEST_FIXTURE** in filenames and rationale. Fixture PASS in the mechanics-only aggregate test is not a real Mimi judgment. A successful mock pipeline proves implementation readiness only. It neither proves lower hidden reasoning consumption nor makes any candidate better/source-faithful.

## 7. Deployment review boundary

Required services after separate approval: **ML, backend and frontend**, plus **Flyway V66** on backend startup. Production currently still uses the deployed batch implementation/V65. New UI/requests must not be used against the old schema; deploy as a coordinated release while keeping both real-dispatch flags false.

Offline checks build only necessary test artifacts, using existing dependencies and disposable database images; no production Docker build occurred. Final observed host free space is approximately 5.1 GiB. No cleanup was performed. Review the broader frontend failures above before authorizing release.

The instruction explicitly says **“Do not initiate a Docker rebuild or production deployment until the completed offline evidence is reviewed.”** Therefore this report is the reviewable boundary, not a deployment-success claim. Deployment requires separate owner authorization, and paid inference requires another separate authorization afterward.

## 8. Exactly one proposed original-only experiment — not authorized

After deployment approval and read-only live preflight, propose **one fresh source request for original Mimi Prompt 10 only**, using OpenAI/gpt-6.1-sol, low effort, strict single-subject schema, max_completion_tokens=4000, max_retries=0, no fallback, maximum **USD $0.10** for that inference. Recheck current catalog/model/budget admission before requesting approval. A total pilot reservation is accounting only and must not authorize additional subjects or critics.

The 1,037-token representative visible JSON leaves approximately 2,963 completion tokens for reasoning/extra findings under this shared 4,000-token limit. This is a defensible bounded first experiment, **not evidence that actual reasoning will fit**; either real failure remains possible. No limit/model change is implicit. A successful original-only review establishes only original review capability and leaves candidate reviews explicitly incomplete. Examine its actual output before proposing individually authorized candidate reviews; critics require all applicable source evidence and separate approval. No A/A+ grading or render permission follows.

## 9. Required result flags

- SINGLE_SUBJECT_CONTRACT: **VERIFIED_OFFLINE**
- ORIGINAL_ONLY_BINDING: **VERIFIED**
- CANDIDATE_BINDINGS: **VERIFIED**
- SOURCE_EVIDENCE_COMPLETENESS: **PRESERVED**
- DURABLE_REQUEST_ISOLATION: **VERIFIED**
- REAL_AI_CALLS: **0**
- REAL_DISPATCH: **DISABLED**
- CPQ_GRADING: **INACTIVE**
- READY_FOR_DEPLOYMENT_REVIEW: **YES** — focused checks pass; broader frontend failures disclosed, no release authorization inferred.

## Evidence and reproducibility

`cpq-single-subject-source-fidelity-evidence/` contains phase-1 sizes/prototype inputs, exact final mocked SDK requests and strict representative response JSON, final size comparison, schema summary, test results/logs and read-only production integrity checks. No credentials/cookies/API keys are included. The responses are test fixtures only.

Focused commands:

```sh
POMPOM_DATA_ROOT="$PWD/intelligence/data" PYTHONPATH=/tmp/cpq-output-tokenizer PYTHONDONTWRITEBYTECODE=1   intelligence/ml-service/.venv/bin/python -m pytest -q -p no:cacheprovider   intelligence/ml-service/tests/test_single_subject_source_fidelity.py   intelligence/ml-service/tests/test_source_fidelity_output_budget.py   intelligence/ml-service/tests/test_owner_machine_pilot.py   intelligence/ml-service/tests/test_adaptive_optimization_v3.py   intelligence/ml-service/tests/test_creative_prompt_quality_v1.py
# In intelligence/backend:
MAVEN_OPTS=-Xmx512m mvn -o -q -Dtest=OriginalCpqFidelityIntegrationTest,CpqOwnerAccessTest,CpqV62MigrationTest test
# In intelligence/frontend:
npm test -- --watch=false --include='src/app/pages/quality-validator/*.spec.ts'
```

The optional diagnostic tokenizer remains outside the application; no production tokenizer dependency was added. Current focused source tests must run before backend tests when regenerating fixture artifacts. Broader frontend command `npm test -- --watch=false` produces the disclosed unrelated failures.


# Deployment / original-only authorization addendum — 2026-10-16

**Overall result: DEPLOYMENT_VERIFIED_AWAITING_SOURCE_ONLY_AUTHORIZATION.** The earlier “not deployed” sections above describe the offline boundary; this addendum supersedes deployment status. Engineering deployment was explicitly authorized by the delivery instruction. Its paid-approval boundary remains in force. The later “devam” continued engineering verification; it was not treated as the required fresh $0.10 inference approval.

## Release and backup evidence

ML, backend and frontend were deployed sequentially using the official `deploy.sh`, one service per invocation, with `COMPOSE_PARALLEL_LIMIT=1`. Existing owner identity/private mount and internal service authentication were preserved. Both dispatch flags stayed false throughout. No applied migration was edited or repaired, and no rollback was attempted.

- Initial host free space: 5,498,875,904 bytes (approximately 5.1 GiB).
- Docker filesystem initially had 49.8 GiB free; build contexts were small (backend source 4.7 MiB, frontend source 1.9 MiB, ML app 3.4 MiB), existing dependency/base layers available. Source/test/build output and ML dependency installation were the expected incremental work. Each build started only after the preceding service completed; the script checked a minimum 1,500 MiB before each build.
- Observed free space after ML: 4,716,621,824 bytes; backend: 4,523,945,984; frontend: 4,473,352,192. Later test/browser memory pressure reduced final observed host free space to approximately 1.15 GiB. No further build or cleanup is authorized/needed for this release; recheck headroom before the later execution window.
- All 63 previously applied migration checksums matched local files before release. Flyway applied **V66 successfully** through normal backend startup. All 64 applied checksums matched afterward; V66 checksum: **-1797319927**. V65 remains unchanged.

Pre-migration custom-format PostgreSQL backup:

- Location: `/Users/benanaktas/Library/Application Support/Pompom Hills/Recovery Backups/cpq-single-v66-20261016T085445Z/pompom-before-v66.dump`.
- Size: 1484447 bytes; permission 0600.
- SHA-256: `a8aa436ee316a14bd80dea2db7c8abefbcde61699312b6e119812f31c96bccd1`.
- Verification: full `pg_restore --file=/dev/null` decoding and TOC listing (1,086 entries).
- Subsequent **actual restore** into a task-owned disposable tmpfs PostgreSQL succeeded using `pg_restore --exit-on-error`. The released backend then migrated that restored V65 database to V66 and passed the positive API/UI smoke checks. This is a disposable operational restore verification, not a claim about production recovery time or every table's independent restored-row fingerprint.
- Backup is retained outside the repository. No backups, Docker volumes, images or unrelated files were deleted. Only the three task-owned disposable smoke containers/network were removed after verification; no production container/data was removed.

Running release images match the official deployment outputs:

| Service | Running image |
| --- | --- |
| ml-service | `sha256:e183985d3d18fd3f1601d258829491160ef21e437df091106c91151a8eebab28` |
| backend | `sha256:2affe1ee131b4e3462cfedb20f5e6d291116e799416ec55951c79ec32002a22f` |
| frontend | `sha256:a795fb833441e29fca32450e6406832ae85213388d0592ce27b85952d1dd5b36` |

Backend/ML are healthy; frontend root and proxied API HTTP checks pass. Release file SHA-256 values remained identical across tests/build/deployment. The running ML source file also matches its tested host source hash. New ML image contains OpenAI SDK 3.31.0, jsonschema 4.26.0 and pydantic 2.14.1; mocked transport tests were run inside that actual image to check its request contract. SDK presence is not a real inference success claim.

## Final release tests and runtime path

Repeated in ML-before-backend order against final release files:

- **106 ML tests passed**.
- **31 backend/auth/migration tests passed**, zero skipped/failures/errors, using disposable PostgreSQL.
- **118 focused frontend tests passed**.
- The broader frontend result remains **343 passed / seven failed / eight uncaught errors**, all in `video-detail.page.spec.ts`. These are unresolved and outside this delivery's changes; no baseline comparison was performed, so this report does **not** claim they are proven pre-existing. The full frontend suite is not described as green.

Running backend/frontend images were then exercised using the restored disposable database. The actual application API created two single-subject-mode pilots only there; four distinct source authorizations (one per exact SHA) each persisted exactly one packet, `evaluationUnit=SINGLE_SUBJECT_V1`, all nine source sentence spans and no full duplicate original prompt. Missing subject SHA returned 409, identical authorization replay reused its durable row, and execute returned 403 with real dispatch disabled. No provider transport ran. Zero validated source evidence; critic gate stayed false. These are **TEST_FIXTURE_DISPOSABLE_STORAGE** records, not production paid authorizations.

The actual running ML image accepted all four representative TEST_FIXTURE UNKNOWN responses via intercepted/mock SDK transport, preserving exact bindings, six anchors, full source-event and changed-execution coverage. Captured request arguments verify OpenAI/gpt-6.1-sol, low effort, strict json_schema, 4,000 max_completion_tokens and SDK max_retries=0. No real inference occurred.

Live PostgreSQL indexes preserve unique pilot/idempotency, one CRITIC_A/CRITIC_B slot each, legacy NULL-subject batch identity and scoped per-subject source uniqueness. Historical batch rows retain their old input and interpretation; they were not silently converted into single-subject reviews.

## Actual browser verification

Used the agent-browser skill with `npx --no-install agent-browser`, normal owner login and the existing private credential read only into transient process memory. No credentials/cookies were placed in artifacts or chat; no owner identity/credential was changed.

1. **Actual production Step 6** (`127.0.0.1:4200`): expanded Creative Optimization (optional), opened the existing owner panel and loaded the saved historical pilot. All four neutral IDs and full prompt SHA values are visible separately. Source evidence is **0/4**, missing IDs are explicit, semantic findings remain NOT_ASSESSED, and critics are BLOCKED. Old requests remain historical FAILED_OR_AMBIGUOUS; no false semantic UNKNOWN/PASS was created. Dispatch-disabled and CPQ INACTIVE messages are visible. Production inventory before/after opening and inspection stayed **2 pilots / 2 requests / 0 evidence**.
2. **Same released frontend/backend image with disposable storage**: loaded a fresh-mode pilot, selected Q04 and verified the exact original SHA in the dropdown. Four subjects remained NOT_EXECUTED. Changing selection made no write or inference. Checked only the disposable UI's local consent, then loaded another disposable pilot: both consent and subject selection cleared. Critic gate remained BLOCKED; request inventory did not change from the prepared smoke records. No authorization/execute button was submitted in the browser.
3. Viewed both saved screenshots: individual full SHA/status list and Q04 selection are readable. The disposable check is explicitly distinguished from production: no fresh production pilot was created just to prove the selector exists.

## Persisted source bindings and integrity

Live read-only context APIs resolve the exact original and three specified historical candidates; all four prompt SHA values and the full approved-story hash recompute correctly from actual saved text. Canonical Ruleset 1.11 remains **88.40625/B** for all four. Source identity fields are distinct:

- Story ID: `bc1cf798-d20b-4b98-8b73-56e1581c3afc`.
- Approval record ID: `20b77d13-848d-46d0-ab4b-bb9b6efb0836`.
- Approved text revision: `candidate-2-revision-7c63cc86`.

Effective production context remains ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15s / image2video / 480p / 9:16. Neither prompt nor source text was reconstructed or shortened.

Both historical durable requests compare equal to their archived full rows after excluding only the newly added NULL subject column. Prompt 10 remains version 1 with SHA `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`. Historical workflow count/digest remains 75 / `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`. CPQ activation remains false.

## Required owner-facing result at this boundary

| Question | Actual result |
| --- | --- |
| V66 deployed and live single-subject path verified? | YES; production deployment plus same-running-image disposable positive path and browser checks |
| New paid original-only call explicitly authorized/executed? | NO / NO; fresh consolidated approval is required next |
| Visible valid real JSON arrived? | NOT_EXECUTED; no new provider response exists |
| Original actual semantic verdict? | **NOT_EVALUATED** |
| Concrete source discrepancies? | None established by this delivery; fixture opinions are not real source findings |
| Input/completion/reasoning/visible usage? | NOT_AVAILABLE — no new real inference; offline proxy measurements remain in the main report |
| Calculated usage cost vs ceiling? | No new inference cost; proposed maximum **$0.10**, not yet authorized |
| Both dispatch flags disabled? | YES; container env and live capability checks agree |
| Historical records/Prompt 10 preserved? | YES, exact comparisons above |
| ONE next product action? | Obtain fresh approval and execute exactly one original-only source review, then examine its actual result before anything else |

## Accounting reservation — separate from spending permission

For a later fresh four-subject pilot, propose a **$0.70 total accounting ceiling**, without reserving or authorizing other requests. Only Q04 would receive a **$0.10 request reservation** if the owner approves the single call. A larger immutable pilot accounting ceiling prevents the one original result from being stranded by a pilot budget that cannot later support separately approved reviews. It does **not** authorize candidate/critic calls, which remain unreserved and unexecuted. No pilot or paid authorization has been created in production at this boundary.

The exact proposed inference is one fresh SOURCE_FIDELITY request for original Q04 only, OpenAI/gpt-6.1-sol, low effort, strict JSON, 4,000 completion tokens, cap $0.10, retries zero, no fallback. The released admission path accepted this cap in disposable storage; recheck it immediately before any paid execution. Candidate and critic requests remain zero. If the call is approved, continue this same task; do not require another development prompt.

## Overall and separate statuses

- **DEPLOYMENT_VERIFIED_AWAITING_SOURCE_ONLY_AUTHORIZATION**
- semanticVerdict: **NOT_EVALUATED**
- validatedSubjects: **0/4**
- newPaidRequests: **0**
- candidateRequests: **0** (production, this delivery)
- criticRequests: **0**
- cpqGrading: **INACTIVE**
- renderAuthorized: **false**
- realDispatch: **DISABLED** in backend and ML

All new detailed artifacts are in `cpq-single-subject-delivery-evidence/`: preflight, backup/restore smoke record, release file hashes, final test logs/summary, sequential official deploy logs/image identities, running-image mock validation, real browser snapshots/screenshots/checks, request identity indexes, live four-source contexts, final service and historical integrity checks. No provider calls, candidate generation, grading/approval/render actions, publishing, commit or push occurred.


# Real original-only execution addendum — 2026-10-16

**Overall result: SOURCE_SINGLE_SUBJECT_EXECUTION_FAILED.** This supersedes the preceding awaiting-authorization status. Exactly one fresh original-only real inference was authorized by the owner's **“evet”** and executed. The provider returned nonempty, parseable, strict-schema-valid JSON within the token budget. The existing evidence validator rejected a source-event citation binding, so no validated source review was persisted. No second inference or implementation change followed.

## 1. Exact authorization and durable execution

The fresh approval covered only original Mimi Q04: OpenAI/gpt-6.1-sol, Chat Completions, strict json_schema, reasoning_effort=low, max_completion_tokens=4000, maximum $0.10, max_retries=0, no fallback, candidates or critics. Prior approvals were not reused.

- Fresh pilot: `770e8477-f352-499e-aabd-b7418435e70b`.
- Fresh durable request: `6f078994-3385-4910-8423-47a46ad9999a`.
- Fresh idempotency key: `81ebe72f-2b48-4d12-9a5c-fbef7b400b95`.
- Provider response ID: `chatcmpl-EZYRV5i8EXPUfeq0yBX2PRYE6EM5R`.
- Created: `2026-10-16T09:22:27.975766+00:00`; finalized: `2026-10-16T09:23:34.722221+00:00`.
- Owner authentication: normal local owner API, authenticated benan; credential/cookie/CSRF kept out of artifacts.
- Pilot accounting ceiling $0.70; **only one $0.10 Q04 reservation** exists. Other three subjects and both critics have no request/authorization.
- Official application command: `POST /api/v1/intelligence/workflow/cpq/owner-pilot/{pilotId}/requests/{requestId}/execute`.

Before dispatch, health/V66/inactive grading/disabled flags/current inventory and exact four saved prompt/story/settings bindings were rechecked. Full original and story text matched persisted data; story ID, approval ID and revision remained distinct. The authorized stored request contained exactly one packet, neutral ID Q04, exact prompt SHA, approved source SHA/settings binding, all nine approved-source spans and no candidate prompt or duplicated original. All six anchors remain required by the deployed schema/validator.

Authorization/pilot creation did not trigger inference. The local journal recorded executeSubmissionStarted before POST; backend durable CAS protected the official request. Exactly one application submission was made, with no direct SDK invocation, duplicate/replay, fallback or retry. The running images were preserved; no build occurred in this execution window.

## 2. Provider response, actual usage and cost

| Measurement | Actual observed value |
| --- | --- |
| Provider / returned model | OpenAI / gpt-6.1-sol |
| Effective effort / completion ceiling | low / 4,000 |
| Provider API status / finish_reason | COMPLETED / **stop** |
| Input tokens | **1,883** |
| Completion tokens | **1,673** |
| Provider-reported reasoning tokens | **0** |
| Total tokens | 3,556 |
| Visible output | **6,581 characters / 6,690 UTF-8 bytes** |
| JSON parsing | PASS |
| Existing strict single-subject JSON Schema | PASS |
| Semantic/evidence contract | REJECTED |
| Usage accounting | COMPLETE |
| Calculated cost | **USD $0.02143750** |
| Authorized ceiling | USD $0.10 |

Calculation from reported usage and configured rates: `1883 × $2.50 / 1,000,000 + 1673 × $10.00 / 1,000,000`. This is calculated usage cost, **not a verified provider invoice**. It consumed approximately 21.4% of the authorized ceiling. The shared 4,000-token budget was not exhausted; the provider reported zero reasoning tokens, which is a usage field, not proof about unreported internal model processes.

This real attempt demonstrates that the single-subject request can return visible structured output under the fixed envelope. It does not prove reliable completion or semantic assessment quality, and does not establish request size as the sole cause of the previous failures.

## 3. Exact contract rejection — no source quotation was fabricated

Durable state: **FAILED_OR_AMBIGUOUS**. ML envelope failure category: **PROVIDER_OR_RESPONSE_CONTRACT_FAILED**. No machine-evidence row was appended.

An offline, read-only invocation of the **running deployed validator** against the saved input/raw output reproduced:

`ValueError: Exact required source-event citation required`

The invalid binding is mapping index 11 (zero-based), anchor **EVENT_ORDER**, eventId **event_07**. The submitted source quote spans three consecutive source sentences (events 06–08):

> Mimi aynada kendini görünce çığlık atar. Notlar o kadar çoğalır ki Mimi boğulacak gibi olur. Sonunda hapşırır ve tüm notlar uçuşarak dolabın üzerine yapışır.

But event_07 is bound only to:

> Notlar o kadar çoğalır ki Mimi boğulacak gibi olur.

The complete submitted quotation **does exist verbatim in the approved story**. It is rejected because it extends outside the single event_07 span; this is a multi-sentence EVENT_ORDER quotation attached to one sentence ID. The model did not obey that per-span mapping restriction. The same preserved raw response also uses empty beatId strings; these are permitted by the current string schema for this original-only request and are not the reproduced rejection reason.

The response contains all six anchor kinds and all nine source-event IDs across 14 mappings, but that does not override the citation restriction. No mappings were rewritten/split, no validator was relaxed, and the raw FAIL was not promoted into accepted evidence. Offline diagnosis made **zero additional provider calls**.

## 4. Model findings — preserved, but not accepted semantic evidence

The raw model decision is **FAIL**. The application-accepted semantic verdict remains **NOT_EVALUATED** because the full evidence contract failed. This is not a completed semantic FAIL, not a model-authored UNKNOWN, and not canonical scoring evidence.

Two raw model omission findings are preserved:

| Model finding | Exact saved source | Relevant original prompt evidence | Interpretation limit |
| --- | --- | --- | --- |
| Note lettering omitted | `Mimi, oyuncak dolabına 'Topla!' yazan bir yapışkan not yapıştırmak ister.` | `0-2s: Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger` | Literal `Topla!` is present in source and absent from the full original prompt. This textual absence can be checked directly; the failed response is still not formal machine fidelity evidence. |
| Post-mirror near-suffocation escalation absent | `Mimi aynada kendini görünce çığlık atar. Notlar o kadar çoğalır ki Mimi boğulacak gibi olur.` | `10-12s: Mimi sees herself in a mirror and screams`; next beat begins `12-15s: Mimi sneezes and the sticky notes fly off` | The original earlier says `Mimi is overwhelmed by notes` in 5–10s; whether that adequately preserves the later source event/order needs adjudication. Do not treat the model's stronger claim as independently validated. |

The model listed bright/colorful style, music, sound effects and negative constraints as production additions, and explicitly described 2→4→8 counts as a noncontradictory operationalization of doubling. Their presence in an additions array does **not by itself establish an unauthorized narrative deviation**. Raw production risks include note-text legibility at 480p, mirror/face readability, coverage staging, final-three-second action density and missing visual/image2video input evidence. These are unvalidated text-only observations, not rendered defects or successful visual evidence.

If these omission claims are later accepted, only the affected note lettering and post-mirror escalation/order would warrant targeted clarification/repair. No story, Prompt 10, candidate, setting, score or rule was edited here.

## 5. Final closure, integrity and next action

The execution driver disabled backend and ML dispatch in its finally path. Enable/execute/disable exit codes were all zero; the execute exit means the official workflow returned its saved failed result, **not** that the review passed. Both container env flags and live capabilities were verified false afterward.

Production now has **3 pilots / 3 source requests / 0 validated machine-evidence rows**. This fresh pilot has only the Q04 source request; candidates Q01/Q02/Q03 remain NOT_EXECUTED, both critics remain NOT_EXECUTED. Aggregate validated coverage remains **0/4**, all four subjects are missing accepted evidence and the critic gate is false.

Both older failed durable rows remain byte-equivalent at the JSON-field level, excluding V66's added NULL column. Prompt 10 remains version 1 with its exact SHA. Full story/settings bindings, canonical Ruleset 1.11 and **88.40625/B** are unchanged. Historical workflow count/digest remains 75 / `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`. CPQ grading remains inactive; renderAuthorized=false.

**ONE next product action:** review the narrowly identified EVENT_ORDER multi-sentence citation versus single-event binding mismatch for a targeted contract correction, using this saved response rather than another paid inference. This task stops here: no automatic implementation cycle, response salvage/promotion, prompt repair, candidate/critic call or new paid attempt. The two raw omission findings remain available for later source-specific adjudication.

Final fields:

- overallResult: **SOURCE_SINGLE_SUBJECT_EXECUTION_FAILED**
- semanticVerdict: **NOT_EVALUATED**
- rawModelDecision: **FAIL — unvalidated**
- validatedSubjects: **0/4**
- realProviderRequestsSubmitted: **1**
- candidateRequests: **0**
- criticRequests: **0**
- automaticRetries: **0**
- cpqGrading: **INACTIVE**
- renderAuthorized: **false**
- realDispatch: **DISABLED** in both services

Detailed real-run artifacts remain in the same `cpq-single-subject-delivery-evidence/` directory: `real-original-only-journal.json`, prepared pilot and authorized request, complete durable result, exact visible response, explicitly unvalidated model judgment, reproduced contract diagnostic, verified summary, guarded-window outcome and enable/disable logs. No secrets are included. No further code change, rebuild, paid call, approval, rendering, publication, commit or push occurred after this attempt.
