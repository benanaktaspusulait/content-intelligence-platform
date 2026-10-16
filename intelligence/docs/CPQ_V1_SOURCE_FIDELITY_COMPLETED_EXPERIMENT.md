# SOURCE_FIDELITY — authorized real experiment result

Date: 2026-10-16. **REAL_SOURCE_FIDELITY: INCOMPLETE.** One fresh authorized real inference was executed through the authenticated application workflow. No valid machine source-fidelity assessment was returned. This report records failure, not successful acceptance.

## Authorization and exact execution

The owner replied **“evet”** to the proposed single SOURCE_FIDELITY operation after read-only preflight. Scope: original Mimi Prompt 10 and three historical candidates; OpenAI `gpt-6.1-sol`; Chat Completions; strict `json_schema`; `reasoning_effort=low`; `max_completion_tokens=4000`; SDK retries zero; maximum USD $0.30. No fallback, critics or other model calls were authorized. The fresh pilot's $0.60 accounting ceiling did not authorize critics.

- Pilot: `53e43e2c-8bfa-4798-8fad-30a068d97dac`.
- Durable request: `7beb2327-6f75-4646-90df-c56c295fde20`.
- Idempotency key: `73d7c456-7f19-4951-b221-19e8d415aea0`.
- Provider response identity: `chatcmpl-EZXa0CnrVv672vwJnmZI634WZYxQi`.
- Authorized by authenticated owner `benan`; no credentials included.
- Created: 2026-10-16 08:27:02 UTC; finalized: 08:28:40 UTC.
- Official command: `POST /api/v1/intelligence/workflow/cpq/owner-pilot/{pilotId}/requests/{requestId}/execute`.
- Persisted state: `FAILED_OR_AMBIGUOUS`; provider response metadata: `apiStatus=COMPLETED`, `finishReason=length`.

A durable execution marker was recorded before the single POST. No direct SDK invocation, replay, fallback or retry was performed. Both dispatch flags were disabled in a finally block; subsequent container and application-capability checks confirmed false. Existing images were reused without builds or cleanup.

## Actual response and usage

| Field | Observed value |
| --- | --- |
| Returned model | gpt-6.1-sol |
| Effective reasoning effort | low |
| Prompt tokens | 6,245 |
| Completion tokens | 4,000 |
| Reasoning tokens | 4,000 |
| Total tokens | 10,245 |
| Visible response | Empty string: 0 characters / 0 UTF-8 bytes |
| Validated results | 0 |
| New machine evidence rows | 0 |
| Failure category | REASONING_BUDGET_EXHAUSTED |
| Usage accounting | COMPLETE |
| Calculated cost | **USD $0.05561250** |

Calculation using the configured catalog rates: `6245 × $2.50 / 1,000,000 + 4000 × $10.00 / 1,000,000`. This is calculated usage cost, **not a verified provider invoice**. It is below the $0.30 authorization ceiling.

All reported completion tokens were reasoning tokens. Low effort did not produce visible output within this ceiling in this real attempt. There is no JSON to parse, no exact quotation mapping to validate and no supported semantic conclusion. The evidence supports budget exhaustion; it does not establish a source defect or prove why this model consumed the full allowance. No token increase or model change was made.

## Four exact source bindings and verdicts

Common binding: Content 10, immutable Prompt 10/version 1, analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, Ruleset 1.11, canonical **88.40625/B**. Production context: ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15s / image2video / 480p / 9:16.

Approved-story SHA-256: `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`.

| Subject | Saved selector | Prompt SHA-256 | Report verdict |
| --- | --- | --- | --- |
| Original | Prompt 10/version 1 | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` | UNKNOWN — no validated response |
| Candidate 1 | e651eb75-b894-477d-ae77-0fe6e05236da / candidate-a | `90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495` | UNKNOWN — no validated response |
| Candidate 2 | 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-a | `218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749` | UNKNOWN — no validated response |
| Candidate 3 | 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-b | `2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746` | UNKNOWN — no validated response |

These UNKNOWN labels are reporting placeholders for an incomplete review, **not model-authored UNKNOWN judgments**. Conflicts, omissions, additions, uncertainty statements, six-anchor coverage and source-event/changed-beat mappings are unavailable for every subject. Absence of findings cannot be interpreted as absence of problems.

The source checker model differs from the historical generator `gpt-4o-mini-2024-07-18`, satisfying exact-model separation. Both are OpenAI models, which remains a provider-family independence limitation. No HUMAN_REVIEW claim is made.

## Integrity and operational verification

- All four prompt SHA-256 values recomputed successfully. Full prompt text, approved story and production settings match the previous pilot exactly.
- Historical failed request `3a55b29a-48c6-44c0-a003-da11af0f7069` compared field-for-field with its existing archive: unchanged, never replayed.
- Historical workflow event inventory: 75; ordered payload digest unchanged: `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`.
- Database request inventory: two SOURCE_FIDELITY requests, both FAILED_OR_AMBIGUOUS; zero critic requests; zero validated pilot evidence rows.
- Flyway V65 success remains true. CPQ policy activation remains false.
- Backend, ML and PostgreSQL healthy after closing the dispatch window; frontend serves capabilities successfully.
- Backend `CPQ_PILOT_REAL_ENABLED=false`; ML `CPQ_PILOT_REAL_ENABLED=false`; application `realDispatchEnabled=false`, `realEnabled=false`.
- No prompt/story edits, new prompt version, score changes, candidate generation, approval, F8 authorization, rendering, publication, historical overwrite, commit or push.

Earlier offline tests remain implementation evidence only. This task performed a real operational experiment and read-only integrity checks; no new development or regression suite was necessary. The real attempt demonstrates that the deployed low-effort change did **not** resolve output exhaustion at this fixed budget.

## Next business decision

The pilot cannot proceed to critics under this task's sequence: a completed validated source review is still missing. No source conflict can be adjudicated from this empty response. Neither critic was authorized or executed. No candidate-superiority, A/A+ or B→A conclusion is supported.

Stop at this boundary. Any further paid source experiment requires fresh authorization after considering the observed usage; there is no automatic retry, model substitution or token increase. Independent DeepSeek/OpenAI creative reviews remain a later, separately authorized step after the source-evidence gate is met.

## Final statuses

- REAL_SOURCE_FIDELITY: **INCOMPLETE**
- ORIGINAL_SOURCE_VERDICT: **UNKNOWN**
- CANDIDATE_1_SOURCE_VERDICT: **UNKNOWN**
- CANDIDATE_2_SOURCE_VERDICT: **UNKNOWN**
- CANDIDATE_3_SOURCE_VERDICT: **UNKNOWN**
- CRITIC_A: **NOT_EXECUTED**
- CRITIC_B: **NOT_EXECUTED**
- CPQ_GRADING: **INACTIVE**
- REAL_B_TO_A_ACCEPTANCE: **NOT_VERIFIED**
- REAL_DISPATCH: **DISABLED**

## Evidence files

All paths below are relative to this report:

- [Durable request, full input, raw response and usage](cpq-source-fidelity-completed-experiment-evidence/source-fidelity-durable-request.json)
- [Prepared four-subject pilot](cpq-source-fidelity-completed-experiment-evidence/prepared-pilot.json)
- [Returned application result](cpq-source-fidelity-completed-experiment-evidence/source_fidelity-pilot-result.json)
- [Authorization and one-submission journal](cpq-source-fidelity-completed-experiment-evidence/execution-journal.json)
- [Dispatch-window exit results](cpq-source-fidelity-completed-experiment-evidence/dispatch-window.json)
- [Dispatch closure verification log](cpq-source-fidelity-completed-experiment-evidence/dispatch-disable.log)
- [Post-execution runtime/history verification](cpq-source-fidelity-completed-experiment-evidence/post-execution-verification.json)
- [Four-subject source-binding integrity](cpq-source-fidelity-completed-experiment-evidence/source-binding-integrity.json)
