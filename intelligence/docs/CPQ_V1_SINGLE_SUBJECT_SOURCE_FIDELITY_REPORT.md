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
- **Broader frontend: 343 passed, seven failed, eight uncaught errors**, all failures in untouched `video-detail.page.spec.ts`, including a missing mocked `getCaptionVersionsByVideo` service method and existing page expectation mismatches. This is not a clean full-frontend regression result. These failures were not repaired as part of source review scope.
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
