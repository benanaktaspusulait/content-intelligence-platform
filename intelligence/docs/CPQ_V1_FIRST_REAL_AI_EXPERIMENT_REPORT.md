# First real Mimi AI creative quality experiment

16 October 2026 · OWNER_MACHINE_PILOT_V1 · TEXT_ONLY

## Result

**The experiment stopped after one real SOURCE_FIDELITY inference.** The provider returned finish_reason=length, an empty visible response, and usage showing all 4,000 completion tokens were reasoning tokens. No valid source-fidelity review or creative critique was collected. No repeat, fallback or extra request was issued. Both real-dispatch flags are disabled again.

| Required status | Actual value |
| --- | --- |
| REAL_MACHINE_FIDELITY | INCOMPLETE |
| CRITIC_A | NOT_COLLECTED |
| CRITIC_B | NOT_COLLECTED |
| MATERIAL_IMPROVEMENT | INSUFFICIENT_EVIDENCE |
| CPQ_GRADING | INACTIVE |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED |
| OWNER_DECISION | PENDING |

## 1. Authorization and execution scope

The owner explicitly answered “evet” to SOURCE_FIDELITY OpenAI/gpt-6.1-sol up to $0.30, CRITIC_A DeepSeek/deepseek-v4-pro up to $0.10, CRITIC_B OpenAI/gpt-6.1-sol up to $0.20; total up to $0.60. Each request was limited to 4,000 output tokens, one request per slot, zero retries/fallback/escalation. This authority was used for one source request only. The other two requests were neither persistently authorized nor dispatched after the source failure.

Official owner-authenticated API flow: create pilot → authorize source request → execute source request → inspect saved state. No direct database writes were made. Owner credential/session secrets were used only transiently for local authentication and are excluded from all artifacts.

## 2. Exact bindings

Content 10; immutable Prompt 10/version 1; analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`; canonical Ruleset 1.11, 88.40625/B. Approved story SHA-256 `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`.

| Subject | Prompt SHA-256 |
| --- | --- |
| Original | 0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98 |
| Historical 1 | 90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495 |
| Historical 2 | 218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749 |
| Historical 3 | 2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746 |

Historical 1: comparison `e651eb75-b894-477d-ae77-0fe6e05236da`, candidate-a. Historical 2/3: comparison `9275c94b-fc35-4207-8648-dfd8d166e502`, candidate-a/candidate-b. All four saved texts and SHA-256 values were verified before execution. Common production settings remained ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15 seconds / image2video / 480p / 9:16. Complete immutable subject snapshots are in prepared-pilot.json.

## 3. Actual provider and request identities

- Pilot: `2485b1a4-a011-4456-aae6-a37badd98245`.
- Durable source request: `3a55b29a-48c6-44c0-a003-da11af0f7069`.
- Actual provider request: `chatcmpl-EZWMfRgFNWEjOnLPLaVesViDKGOFp`.
- Authorized and returned provider/model: OpenAI / `gpt-6.1-sol`.
- Configured modelVersion: `gpt-6.1-sol`; no more precise provider model revision was returned.
- Profile: openai-escalation, Chat Completions, json_schema, reasoning_effort=high, max_completion_tokens=4000, SDK max_retries=0.
- Durable state: FAILED_OR_AMBIGUOUS. This state is retained even though saved provider usage now confirms one inference occurred; it must not be treated as permission to retry.
- Exact canonical input SHA-256: `bba39f18c7837d8aaf5bd6e1a9743e8e95500ceb67f8a8e5e6dc52c9d13b90c0`.

Source reviewer differs from historical candidate generator OpenAI/gpt-4o-mini-2024-07-18 by exact model; shared OpenAI-family bias remains a limitation. No human independence or calibrated PASS is asserted.

## 4. Stage state and cost

| Stage | Persistent authorization | Actual inference | Result | Cap | Calculated usage cost |
| --- | --- | --- | --- | ---: | ---: |
| SOURCE_FIDELITY | One request | One | FAILED_OR_AMBIGUOUS; finish_reason=length | $0.30 | $0.05540250 |
| CRITIC_A | None | None | NOT_COLLECTED | $0.10 proposed/owner-authorized ceiling | No inference charge incurred by this experiment |
| CRITIC_B | None | None | NOT_COLLECTED | $0.20 proposed/owner-authorized ceiling | No inference charge incurred by this experiment |

Provider-reported usage: **6,161 prompt tokens + 4,000 completion tokens = 10,161 total tokens**. Completion details: **4,000 reasoning tokens**; visible raw response length: **0 characters**. Prompt details: cached_tokens=0, cache_write_tokens=6,158, audio_tokens=0. These details are preserved rather than silently treated as visible creative output.

Calculation using the authorized local catalog's conservative standard rates: 6,161 × $2.50/1M + 4,000 × $10.00/1M = **$0.05540250**. The provider did not report a monetary invoice amount, and the existing failure path did not populate costUsd. This is calculated cost from actual usage, not a verified bill or a success-path cost record. No cache/off-peak discounts are assumed. The original $0.60 envelope was not exceeded by this calculation.

## 5. Exact failure and stopping behavior

The adapter sets max_completion_tokens=4000 and reasoning_effort=high. The provider consumed the full completion allowance as reasoning and returned finish_reason=length before producing visible structured output. CreativeCapabilityProvider.complete records usage/metadata/raw content, then raises because finish_reason is not stop. The ML envelope preserves the failed response metadata; the backend saves that envelope and marks the durable request FAILED_OR_AMBIGUOUS without appending validated evidence.

The immediate failure is **output-budget exhaustion with no visible JSON**, not an observed story-fidelity failure, invalid quote, candidate regression or canonical-rule defect. The experiment does not establish why the model needed that amount of reasoning or whether a different setting would succeed. No provider response was fabricated or repaired after the fact.

The workflow's failed/ambiguous-request admission check blocks subsequent calls. The operator's instruction also requires stopping on incomplete source evidence. Consequently neither critic was authorized or dispatched. There was no automatic retry or model substitution.

## 6. Source fidelity and six creative dimensions

No mappings, source quotes, decisions, omissions, additions or production-risk findings were returned. Source fidelity remains UNKNOWN; machine PASS and human PASS are both absent.

| CPQ dimension | Original and all three candidates |
| --- | --- |
| SCROLL_STOP_VISUAL_PROMISE | NOT_ASSESSED — critics not called |
| CAUSAL_PROGRESSION | NOT_ASSESSED — critics not called |
| VISUAL_STORYTELLING | NOT_ASSESSED — critics not called |
| PRODUCTION_EXECUTABILITY | NOT_ASSESSED — critics not called |
| ENDING_REPLAY | NOT_ASSESSED — critics not called |
| DISTINCTIVE_CREATIVE_VALUE | NOT_ASSESSED — critics not called |

There are no critic agreements, disagreements, strengths, weaknesses, actionable creative suggestions or unsupported claims to compare. Empty output was rejected; it was not accepted as an empty PASS. No actual creative quality ranking can be derived.

## 7. Candidate-by-candidate conclusion

| Subject | Comparative conclusion | Evidence limit |
| --- | --- | --- |
| Historical 1 / e651… candidate-a | INSUFFICIENT_EVIDENCE | No completed source check or critic review |
| Historical 2 / 9275… candidate-a | INSUFFICIENT_EVIDENCE | No completed source check or critic review |
| Historical 3 / 9275… candidate-b | INSUFFICIENT_EVIDENCE | No completed source check or critic review |

Saved staging changes and complete prompt texts are preserved in the pilot snapshot. Their presence is not evidence of improvement. This run cannot establish causal clarity, visual legibility, reduced generator complexity, story preservation, cosmetic equivalence or new production risk. Previous canonical scores and stale historical comparison evidence are not substituted for missing machine reviews.

No candidate is recommended as superior. Original remains the current production prompt because no revision was approved; this is not a newly submitted KEEP_ORIGINAL owner decision.

## 8. Step 6 and owner review

The existing Step 6 panel supports loading the persisted pilot ID above and displaying its durable failed request and lack of evidence. No candidate approval, text acceptance, waiver or owner decision was submitted. The live browser's source/candidate views were verified during preflight; an authenticated browser rendering of this newly failed pilot has not been verified in this run. Do not claim that UI acceptance is complete.

OWNER_DECISION remains PENDING. A keep/revise/accept decision is not requested on nonexistent creative evidence. The immediate operator choice is whether to authorize a later targeted retry after diagnosis; the failed request itself must remain immutable/auditable.

## 9. Safety, deployment and integrity

Both CPQ_PILOT_REAL_ENABLED flags were temporarily enabled only after explicit authorization, then disabled after the failed source attempt. Existing backend/ML/frontend images were recreated using compose --no-build; image digests were verified unchanged. No rebuild, source-code change or new infrastructure was introduced. Owner setup remains configured with private permissions; services returned healthy and frontend HTTP delivery remains available. Disk space was approximately 3.4 GiB; no Docker cleanup was performed.

Post-run read-only checks: one owner pilot, one durable machine request, zero validated pilot evidence rows. Historical workflow events remain **75**. The same serialized payload SHA-256 remains `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`, matching pre-experiment. V65 remains successful; official grading activation=false. No story, prompt version, canonical score, historical record, F8 authorization or render job was changed. No commit/push or publishing occurred.

The source request and raw provider envelope are preserved despite rejection. Reusing its empty output cannot create missing fidelity findings. Do not dispatch this failed request again.

## 10. Remaining calibration and smallest next experiment

The platform has demonstrated one real provider execution and safe incomplete-output handling, not recognition of creative improvement. Independent complete source checking, both independent critics, cross-story golden evidence and explicitly approved calibration/activation policy are still required before authoritative A/A+ grading or real B→A acceptance.

Smallest next step: diagnose the reasoning-versus-visible-output allocation offline using the saved request and the exact provider contract. If a bounded profile-setting adjustment is appropriate, verify it deterministically first and present one fresh source-only request for separate explicit authorization. Do not automatically raise the 4,000-token ceiling, change models, generate new prompts or spend the unused critic budget. A later source-only test must retain all four exact prompt/story/settings bindings and stop on rejection. The current experiment is closed after one inference.

## Evidence files

- execution-journal.json — durable local submission markers and exact paid authorization body; no secrets.
- prepared-pilot.json — complete four-subject source/settings snapshot.
- source-fidelity-actual-input.json — exact persisted blind source request.
- source-fidelity-durable-request.json — durable state, usage and saved failed envelope.
- source-fidelity-provider-envelope.json — provider output metadata and empty raw text.
- source_fidelity-pilot-result.json — normal application view after execution.
- experiment-summary.json — machine-readable outcome and accounting.
