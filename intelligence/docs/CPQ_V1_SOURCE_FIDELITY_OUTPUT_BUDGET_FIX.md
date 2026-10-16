# SOURCE_FIDELITY reasoning/output budget correction

16 October 2026. Offline correction and deterministic verification only.

| Independent status | Result |
| --- | --- |
| ROOT_CAUSE | CONFIRMED |
| REASONING_CONFIGURATION | CORRECTED in source; not deployed |
| JSON_OUTPUT_CONTRACT | VERIFIED_OFFLINE |
| REAL_MIMI_BINDINGS | VERIFIED |
| REAL_PROVIDER_CALLS_THIS_TASK | 0 |
| REAL_DISPATCH | DISABLED in backend and ML |
| SOURCE_FIDELITY_RETRY_READINESS | READY_FOR_NEW_AUTHORIZATION after the separately authorized deployment/runtime checks below |
| CPQ_GRADING | INACTIVE |

This is implementation readiness for a bounded experiment, not proof of successful real source fidelity or creative quality. The currently deployed containers still use the old implementation. No deployment or new paid authorization was performed.

## 1. Confirmed failure and configuration inheritance

Historical pilot `2485b1a4-a011-4456-aae6-a37badd98245`; source request `3a55b29a-48c6-44c0-a003-da11af0f7069`; provider request `chatcmpl-EZWMfRgFNWEjOnLPLaVesViDKGOFp`.

The source reviewer used `openai-escalation`, a general creative-optimization profile with reasoningEffort=high. There was no source-specific reasoning resolution. `CreativeCapabilityProvider.complete()` passed that configuration directly as `reasoning_effort`, with `max_completion_tokens=4000`, strict json_schema, no tools and SDK max_retries=0.

The saved provider response reports 6,161 input tokens, 4,000 completion tokens, 4,000 reasoning tokens, empty visible content and finish_reason=length. The shared completion allowance was entirely consumed by reasoning. The immediate defect was the use of high reasoning for this tightly bounded, four-subject structured review without a purpose-specific configuration. It was not an observed fidelity failure or malformed quote.

The adapter correctly rejected finish_reason=length after retaining usage/metadata/raw content. The ML failure envelope and backend durable FAILED_OR_AMBIGUOUS record were preserved. One diagnostic/accounting gap remained: the exception path did not calculate cost from the already available usage or distinguish reasoning exhaustion from other failures. That is now corrected for future responses. Historical evidence was not rewritten.

## 2. Exact supported model/API contract

The official [GPT-6.1 Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol) documents low, medium, high, xhigh and max reasoning effort. It explicitly excludes none and minimal. Chat Completions without tools is supported, so an API/model migration is unnecessary.

The [Chat Completions API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) states that max_completion_tokens includes both visible output and reasoning. There is no separate guaranteed visible-output reservation in this contract. The [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning) also explains that a limit may be reached before any visible output. Its broad starting-budget guidance does not establish that every bounded source review needs that budget, and this task does not increase the authorized ceiling.

These public documentation reads were not paid capability probes. No real provider SDK inference was invoked during this task.

## 3. Minimal implemented correction

1. The existing pilot module resolves SOURCE_FIDELITY through a copy of the selected profile, defaulting to reasoningEffort=low. Optional `CPQ_SOURCE_FIDELITY_REASONING_EFFORT` is validated against the exact documented provider/model capability set. Unknown model capability or unsupported values fail before SDK construction; there is no fallback to another model.
2. Capabilities expose the source-specific effective setting separately from the general profile. Both general OpenAI and DeepSeek profiles retain high. CRITIC_A, CRITIC_B and optimization requests continue to use their existing profile settings.
3. The backend validates that source-specific capability and durably records the effective reasoningEffort in each new authorization JSON. An explicit conflicting effort is rejected. Canonicalizing the same setting preserves idempotency; a changed setting cannot silently reuse the old authorization. ML independently requires that the source authorization match the effective effort before provider construction.
4. Source-only system instructions request compact JSON and concise rationale/uncertainty, while explicitly preserving every event, anchor, changed beat, omission/addition and ending. No input prompt, source text or schema field was removed.
5. Future failed envelopes retain effective configuration, raw response, provider metadata, usage, usage completeness and calculated cost when available. REASONING_BUDGET_EXHAUSTED requires finish_reason=length, no visible text and reported reasoning consuming the completion allowance. Truncated visible output, empty completed output, missing accounting and unavailable transport responses are distinguished. Missing usage produces costUsd=null, never an invented zero. Invalid output remains rejected and is not converted into validated evidence.

No new optimization framework, database table, scoring rule, frontend flow or calibration system was introduced.

## 4. Schema and visible-output size

The source JSON Schema is unchanged, as are the critic schema and critic system instructions. Canonical source schema SHA-256: `3831729b71f66a5d60b7d5e655dd8b471e5ecd62b105f7e045344a2db1281dee`.

Each subject still has nine required properties: neutralId, decision, rationale, uncertainty, conflict, omissions, additions, mappings and productionRisks. Each mapping retains four required properties: anchor, beatId, sourceQuote and promptQuote. Strict JSON additionalProperties=false remains in place. Validator behavior still checks exact citations, all six anchors and changed-beat coverage; missing evidence/conflict/omissions/additions cannot yield semantic PASS.

A representative **MOCK** response was constructed solely for output sizing and contract tests from the four real saved inputs. It uses UNKNOWN, explicitly labels mock rationale and uncertainty, retains an omission rather than pretending fidelity is established, and includes:

- Four subject-level results and 36 required subject-property occurrences.
- All six source anchors for every subject and coverage of all five beats.
- 48 mappings: 44 event/anchor mappings plus four additional changed-beat staging mappings quoting the actual saved production changes.
- 48 exact approved-source citations and 48 exact prompt citations; 192 mapping-property occurrences.
- Per-subject omissions, uncertainty, concrete rationale and production risks.

| Offline size measurement | Estimate |
| --- | ---: |
| Compact JSON UTF-8 size | 12,021 bytes |
| Compact JSON visible tokens | 3,047 |
| Pretty JSON visible tokens | 3,954 |
| Remaining allowance with compact output at 4,000 total | 953 tokens |
| Remaining allowance with pretty output at 4,000 total | 46 tokens |

Token estimates use tiktoken 0.14.0 / o200k_base as an explicit proxy; the exact model tokenizer mapping and future provider counts are not asserted. These are not actual inference usage. The tokenizer was installed only in a temporary diagnostic directory, not added to production dependencies. The sizing test is optional when that diagnostic tokenizer is unavailable; it was present and executed in this task's passing run.

The 3,047-token example demonstrates a useful complete response shape can fit, including changed staging. It is not a mathematical minimum, a real semantic review, or a prediction that low reasoning will use fewer than 953 tokens. Longer quotes, findings, whitespace or reasoning can still exhaust 4,000. Compact instructions and low effort reduce the identified risk; they cannot guarantee allocation or fidelity quality.

**4,000 remains an appropriate bounded next experiment, not a proven reliable production budget.** No ceiling increase, response-field deletion or additional billable split was implemented. If the next attempt exhausts the limit, stop again and use its actual evidence before proposing a different envelope.

## 5. Input duplication

The saved request repeats the same approved story four times and the original prompt four times, once per independently reviewable packet. There is one unique story and one unique original. Three extra copies account for 7,230 UTF-8 bytes. This redundancy contributes input size but does not prove the cause of the exhausted reasoning budget.

The packet contract was deliberately retained: deduplicating it would require coordinated backend/ML contract changes without evidence that this is necessary to fix the visible-output failure. Input/schema admission already fits the context and monetary cap. No source or changed-beat material was removed.

## 6. Real Mimi binding integrity

All four exact prompt hashes were rechecked against saved full text and the immutable pilot snapshot:

| Subject | SHA-256 |
| --- | --- |
| Original Prompt 10/version 1 | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` |
| e651eb75-b894-477d-ae77-0fe6e05236da / candidate-a | `90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495` |
| 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-a | `218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749` |
| Same comparison / candidate-b | `2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746` |

Approved-story SHA-256 remains `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`. Source text, changedBeats and authoritative settings match the saved snapshot. No production prompt or story was edited. Canonical Ruleset 1.11 remains 88.40625/B.

Read-only database comparison established that the entire historical failed-request row exactly equals the previously archived row. Production still has one failed machine request, no completed machine evidence and inactive grading. The 75 historical workflow events retain payload digest `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`.

## 7. Focused tests and regressions

**81 ML tests passed**, zero failures/skips in this run. Suites: test_source_fidelity_output_budget.py, test_owner_machine_pilot.py, test_adaptive_optimization_v3.py and test_creative_prompt_quality_v1.py.

**26 backend tests passed**: 21 OriginalCpqFidelityIntegrationTest cases and five CpqOwnerAccessTest cases. Two authorization/replay workflow cases were then rerun successfully after refining assertions; these are repeats, not two additional unique tests. The integration suite uses a disposable Testcontainers PostgreSQL instance with mocked ML, not the production database.

| Required safety/contract evidence | Verified |
| --- | --- |
| Source-specific low, exact supported efforts, unsupported/unknown model rejection | Mock SDK arguments and pre-construction failures |
| Four real fingerprints, source/settings and full mappings | Saved-input assertions and complete MOCK response |
| Complete JSON accepted; all six anchors and changed beats retained | COMPLETED machine-contract result with UNKNOWN semantic decisions |
| Empty output, length termination, partial JSON rejected | Exactly one mocked transport call; no validated results |
| Reasoning exhaustion versus missing transport/accounting | Exact failure categories; raw metadata retained; unknown cost stays null |
| Missing anchors/changed beats, conflicts, additions/omissions | PASS downgraded to UNKNOWN |
| Unsupported source/prompt citations | Rejected |
| Reported completion usage above 4,000 | Rejected |
| Failed durable request replay | Second execute returns saved state; one mocked dispatch total |
| Fresh authorization/idempotency identity | New slot on failed pilot denied; fresh authorized pilot gets a new request ID |
| Critic/optimization configuration | Both profiles remain high; critic authorizations are not rewritten with source effort |
| No retry/fallback, grading/approval/render isolation | SDK max_retries=0, same exact model, inactive grading and renderAuthorized=false |

Commands used:

```bash
PYTHONPATH=/tmp/cpq-output-tokenizer PYTHONDONTWRITEBYTECODE=1 \
  POMPOM_DATA_ROOT="$PWD/intelligence/data" \
  intelligence/ml-service/.venv/bin/python -m pytest -q -p no:cacheprovider \
  intelligence/ml-service/tests/test_source_fidelity_output_budget.py \
  intelligence/ml-service/tests/test_owner_machine_pilot.py \
  intelligence/ml-service/tests/test_adaptive_optimization_v3.py \
  intelligence/ml-service/tests/test_creative_prompt_quality_v1.py

# From intelligence/backend; disposable test DB, no image build:
DOCKER_HOST=unix:///Users/benanaktas/.docker/run/docker.sock \
  mvn -o -q -Dtest=CpqOwnerAccessTest,OriginalCpqFidelityIntegrationTest test
```

Regression notes: 244 existing parser datetime.utcnow deprecation warnings in ML; Java/Mockito agent warnings. No relevant regression failures. This is focused verification, not a claimed clean full-suite baseline. No frontend source changed, so no frontend build/test cycle was introduced. `git diff --check` passed.

## 8. Changed files

- `intelligence/ml-service/app/workflow/creative_provider_profiles.py`: exact-model reasoning validation before SDK construction.
- `intelligence/ml-service/app/workflow/owner_machine_pilot.py`: source-specific configuration/capabilities, compact source instructions, authorization binding, failure classification and accounting.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/CpqOwnerPilotService.java`: persist and validate the effective source reasoning setting using existing authorization JSON/idempotency flow.
- `intelligence/ml-service/tests/test_owner_machine_pilot.py`: fixture contract updated for explicit source reasoning.
- `intelligence/ml-service/tests/test_source_fidelity_output_budget.py`: saved-Mimi mocked-transport and budget regressions.
- `intelligence/backend/src/test/java/com/pompomhills/intelligence/OriginalCpqFidelityIntegrationTest.java`: purpose-specific authorization and failed-request replay safety coverage.
- This report and `intelligence/docs/cpq-source-fidelity-output-budget-evidence/`: labeled sizing fixture, measured analysis, focused results and integrity/runtime-boundary evidence.

The provider catalog file was not changed. No DB migration, historical backfill, prompt version, canonical ruleset or scoring change is needed.

## 9. Future cost envelope

Using the actual saved four-subject input, new source system and unchanged schema:

- ML conservative input bound: 28,064.
- Backend conservative input bound: 36,167.
- Admission uses the more conservative bound with 4,000 completion tokens.
- At the existing configured conservative $2.50/M input and $10/M output rates, maximum estimated admitted cost is **$0.13041750**, within a proposed **$0.30** source-only cap.

This is a pre-dispatch bound using configured rates, not a future bill. Cached reasoning/visible-output usage and model behavior remain unknown until a separately authorized real run. The mock's usage numbers are transport fixtures and must never be reported as new actual provider usage.

## 10. Deployment boundary and migration concerns

No Docker image build, deployment, restart, dispatch flag change or production write occurred in this task. Current deployed capabilities still show the general OpenAI high setting and do not yet expose sourceFidelityConfiguration. Both real-dispatch flags are false. Do not describe the live service as fixed yet.

Next authorized deployment scope: **ML and backend only**, with the existing frontend nginx restart required by backend container address changes. No frontend image rebuild or database migration is needed. Recheck limited host disk headroom first; do not run broad cleanup or a full-stack rebuild. Deploy ML before/with backend: an old ML service lacking verified source-specific capabilities makes the new backend fail closed for new source authorizations.

Runtime verification before any paid execution: source capability shows low and the exact allowed list; critic/optimization profiles remain high; both flags remain false; owner authorization binding persists low; schemas/subject hashes match; historical row remains unchanged. Do not use the historical failed request as a smoke test. Use deterministic tests for writes until the next fresh paid test is explicitly authorized.

The existing unique (pilot_id, slot) constraint intentionally prevents replacing the failed source slot. A future source attempt therefore needs a fresh pilot/request, explicit source binding and new authorization/idempotency identity. The old row and response stay preserved. Any preexisting source authorization without the new explicit effective setting cannot be silently repurposed.

## 11. Exact proposed future owner authorization

After separately authorized deployment and runtime verification, present this bounded source-only request:

> Prepare a fresh immutable OWNER_MACHINE_PILOT_V1 pilot with the same four Mimi prompt fingerprints, approved-story hash, analysis and production settings. A total pilot accounting ceiling of $0.60 may be reserved to permit later stages only if separately authorized; this grants no critic spending permission. Authorize **only one new SOURCE_FIDELITY inference**, OpenAI / **gpt-6.1-sol**, Chat Completions strict json_schema, **reasoning_effort=low**, **max_completion_tokens=4000**, **maximum cost $0.30**, a fresh durable request and fresh idempotency key. No automatic retries, model fallback, critic calls, prompt generation, grading activation, approval or render. Stop on any rejection, truncation, conflict or ambiguity, preserve raw evidence and disable real dispatch afterward.

This proposal is not a new authorization and reserves/spends nothing now. The previous request consumed its own authorization; neither its identity nor the unused original experiment budget provides permission for a retry.

## 12. Limits and next milestone

The correction removes the verified high-effort inheritance problem and makes exhaustion/accounting failures diagnosable. It does not prove that low effort leaves enough visible output, performs adequate semantic review, recognizes an improved prompt, or satisfies independent human calibration. The full four-prompt payload may legitimately produce UNKNOWN/FAIL for source issues; no PASS is forced.

Next milestone remains one valid real source-fidelity review, then separately authorized independent critics under the existing stop rules. No additional architecture work is proposed.
