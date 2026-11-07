# Pompom V1 — First Net-New Content Generation Runbook

**Status: `NET_NEW_GENERATION_READY`** — the bounded generation request and run command are prepared. No new concept has been generated and this is not `PILOT_READY`. This task made **0 provider calls and 0 render calls**, as required.

## Scope and selected architecture

Use the existing `TWO_STAGE_V1` opening-seed and story-expansion flow, existing `semantic-opening-seed-prompt-v1` / `semantic-story-expansion-prompt-v1`, current `gpt-6.1-sol` low-reasoning profile, existing opening evaluator, and existing downstream validators. The saved Phase A request and exact system prompt are in `intelligence/docs/net-new-generation-v1/phase-a-request.json` and `phase-a-system-prompt.txt`; its response schema is in `phase-a-schema-validation.json`.

The plan authorizes at most **one Phase A provider request** and, only after that opening passes its existing gate, at most **one separately authorized Phase B request**. Total maximum: **2 provider requests**. Each invocation also requires its own exact authorization file. No retry, replacement, fallback, DeepSeek call, automatic Phase B call, or render is permitted.

| Request setting | Bound |
|---|---|
| Provider / model / reasoning | OpenAI / `gpt-6.1-sol` / `low` |
| Prompt versions | Existing Phase A v1 and Phase B v1; no new prompt version |
| Candidate count | One seed; one story only if Phase A passes |
| Output / timeout | 8,192 completion tokens / 90 seconds |
| Streaming / structured output | Non-streaming / existing strict schema validation |
| SDK retries / transport retries | 0 / 0; one observed HTTP request maximum per phase |
| Total budget | Phase A ≤1, Phase B ≤1 conditional, total ≤2 |

Phase B's existing instruction allows an approximately 15-second story up to 20 seconds. This run's production contract is stricter: **do not advance any story over 15 seconds**; reject it as blocked and do not trim it. Four meaningful causal beats, sound-off comprehension, one protagonist/object/rule, active frame-zero conflict, simple staging, and a strong payoff remain human and deterministic review requirements. Prefer a 14-second plan when the actual story supports it.

## New-candidate lifecycle policy

Historical content remains reference/duplicate evidence. Its `UNKNOWN` publication state remains unknown; it is not converted into unused or new content. The 228 unresolved historical tracker rows are not part of this task's work.

A generation result is a new concept only when it has a unique run-scoped `candidateId`, a durable TWO_STAGE_V1 creation record with timestamp and request/response provenance, and an exact source SHA-256. When the final production prompt is saved, bind its exact hash and content/prompt IDs to that creation record. Confirm no render is linked to the candidate. Search for exact hash and published-story matches with existing evidence; classify with existing Creative Shape and Historical Territory capabilities. A positive exact or story-equivalent published match blocks normal production. Any unresolved high-similarity result requires explicit human clearance. A new name, filename, or ID does not erase a match.

The production registry record required before render must bind:

```json
{
  "candidateId": "<run-id>-opening-a-<seedId>",
  "candidateOrigin": "NEW_CONCEPT",
  "contentId": 12345,
  "promptVersionId": 1,
  "promptSha256": "<exact-final-source-prompt-sha256>",
  "lifecycleStatus": "NEW_CONCEPT",
  "renderStatus": "NOT_RENDERED_CONFIRMED",
  "linkedRenderCount": 0,
  "publicationStatus": "NO_RENDER_LINKED",
  "duplicateClassification": "DISTINCT",
  "creationRecord": {
    "generationArchitecture": "TWO_STAGE_V1",
    "generationRunId": "<run-id>",
    "phaseARequestId": "opening-a",
    "createdAt": "<UTC timestamp>",
    "provider": "openai",
    "model": "gpt-6.1-sol",
    "reasoningEffort": "low",
    "sourceSha256": "<exact-final-source-prompt-sha256>",
    "contentId": 12345,
    "promptVersionId": 1
  },
  "noveltyReview": {
    "disposition": "NO_POSITIVE_MATCH",
    "checkedAt": "<UTC timestamp>",
    "reviewEvidenceSha256": "<64-character-hash-of-saved-review-evidence>"
  },
  "evidence": [
    {"kind": "LOCAL_PROMPT", "path": "<library-relative-final-prompt-path>", "sha256": "<exact-final-source-prompt-sha256>"},
    {"kind": "NOVELTY_REVIEW", "path": "<library-relative-novelty-review-path>", "sha256": "<64-character-hash-of-saved-review-evidence>"}
  ]
}
```

In this example, replace the numeric content and prompt-version IDs with the actual API response values.

For `HIGH_SIMILARITY_REVIEW`, retain that classification and set the separate human disposition to `CLEARED_DISTINCT` with reviewer and timestamp. Do not use that disposition to override an exact or confirmed story-equivalent published match. A candidate creation record is not render authorization: current validation evidence and the separate render-request authorization remain mandatory.

The guard now uses this explicit new-concept branch instead of demanding historical proof of “never published.” Historical records still need their known status; a `NEW_CONCEPT` label alone is insufficient. Registry source evidence must have valid paths and matching hashes. Exact matches to any known historical prompt/video/lineage block; positive published/story-equivalent status blocks; unresolved lifecycle/high similarity is held for review.

## Bounded Phase A and conditional Phase B commands

Run from the repository root. The authorization files below are deliberately absent. **Do not create them for this task**; no provider call was authorized. When the operator later approves one Phase A request, create the exact authorization file first:

```sh
mkdir -p intelligence/docs/net-new-generation-v1/authorization
printf '%s\n' 'AUTHORIZE_PHASE_A:net-new-v1-20261102-001:MAX_PROVIDER_REQUESTS=1' \
  > intelligence/docs/net-new-generation-v1/authorization/phase-a.txt
POMPOM_OFFLINE_MODE=false POMPOM_EXTERNAL_AI_AUTHORIZED=true \
PYTHONPATH=intelligence/ml-service intelligence/ml-service/.venv/bin/python \
  intelligence/scripts/run-net-new-two-stage-v1.py \
  --phase A --run-id net-new-v1-20261102-001 \
  --authorization-file intelligence/docs/net-new-generation-v1/authorization/phase-a.txt
```

The command refuses to run if offline mode is enabled, external AI is not explicitly enabled, the authorization file text differs, credentials are unavailable, or the run ID/output directory has already been claimed. It makes one Phase A request. It stores the immutable request/response, candidate creation record, and `opening-gate.json`. Inspect the full gate output. If score is below 60 or any blocker exists, **stop; do not run Phase B**.

If and only if `phaseBEligible` is true, inspect and approve the opening for expansion, then separately authorize one Phase B request. The candidate ID is stored in `candidate-creation-record.json`:

```sh
CANDIDATE_ID=$(intelligence/ml-service/.venv/bin/python -c \
  'import json; print(json.load(open("intelligence/docs/net-new-generation-v1/runs/net-new-v1-20261102-001/candidate-creation-record.json"))["candidate"]["candidateId"])')
printf 'AUTHORIZE_PHASE_B:net-new-v1-20261102-001:CANDIDATE_ID=%s:MAX_PROVIDER_REQUESTS=1\n' "$CANDIDATE_ID" \
  > intelligence/docs/net-new-generation-v1/authorization/phase-b.txt
POMPOM_OFFLINE_MODE=false POMPOM_EXTERNAL_AI_AUTHORIZED=true \
PYTHONPATH=intelligence/ml-service intelligence/ml-service/.venv/bin/python \
  intelligence/scripts/run-net-new-two-stage-v1.py \
  --phase B --run-id net-new-v1-20261102-001 \
  --authorization-file intelligence/docs/net-new-generation-v1/authorization/phase-b.txt
```

For the recovered Kiko watering-can run, the runner additionally requires the
explicit conversation clearance and resolves eligibility from the hash-pinned
accepted replay while preserving the original rejected Phase A record. The
operator must create a fresh `phase-b.txt` using the exact candidate-bound
authorization below; the runner does not create it:

```sh
printf '%s\n' 'AUTHORIZE_PHASE_B:net-new-v1-20261102-v2-e0a93c0f3e56612cd051b434f001dd9b:CANDIDATE_ID=net-new-v1-20261102-v2-e0a93c0f3e56612cd051b434f001dd9b-opening-a-kiko-watering-can-return-loop:MAX_PROVIDER_REQUESTS=1' \
  > intelligence/docs/net-new-generation-v1/authorization/phase-b.txt
POMPOM_OFFLINE_MODE=false POMPOM_EXTERNAL_AI_AUTHORIZED=true \
PYTHONPATH=intelligence/ml-service intelligence/ml-service/.venv/bin/python \
  intelligence/scripts/run-net-new-two-stage-v1.py \
  --phase B --run-id net-new-v1-20261102-v2-e0a93c0f3e56612cd051b434f001dd9b \
  --authorization-file intelligence/docs/net-new-generation-v1/authorization/phase-b.txt \
  --novelty-clearance 'CLEAR controlled experiment'
```

The runner refuses Phase B unless the stored Phase A run is complete, the source hash still matches, the opening passed, and a separate authorization names the exact candidate. The Phase B output is evaluated by the existing expansion seed-drift/coherence and full analysis path; inspect `phase-b-analysis.json`. No automatic retries or new output directory for the same run ID are allowed.

## Existing validation and novelty procedure

Phase A uses `stage.gate_seed`: existing canonical projection/evidence, premise naturalness, opening score and existing admission evidence. Expansion is allowed only at opening score **≥60** with no disqualifying gate finding.

Phase B uses the frozen opening seed and existing `stage.analyze_expansion` pipeline. Require preserved opening/goal/object/rule/trigger, no rule inconsistency, an accepted full pipeline result, and the existing quality gates. Do not interpret unavailable output as PASS. Compare the full candidate—not just title or object—using existing Creative Shape and Historical Territory results and available exact/story fingerprints. Record matched source paths and hashes. Human-review every unresolved high-similarity case and the final story.

The project has an existing content creation API; after the actual story passes creative and novelty review, use it to create the content and prompt version (do not create a prompt-optimization candidate):

```sh
curl -fsS -X POST "$POMPOM_API_BASE/api/v1/intelligence/contents" \
  -H 'Content-Type: application/json' \
  --data '{"title":"<human-reviewed title>","description":"TWO_STAGE_V1 run net-new-v1-20261102-001","type":"SHORT"}'

curl -fsS -X POST "$POMPOM_API_BASE/api/v1/intelligence/contents/<contentId>/prompt-versions" \
  -H 'Content-Type: application/json' \
  --data-binary @<approved-production-prompt-request.json>
```

`approved-production-prompt-request.json` contains the exact human-approved prompt in `rawText`, its parsed IR in `parsedIr`, and `parentPromptVersionId: null`; leave optimization-only fields unset. Save the response IDs, canonical prompt hash and exact source file/hash in the lifecycle registry. The content/prompt create endpoints are existing `ContentWorkspaceController` routes; they create a DRAFT content and immutable prompt-version record.

If the story is kept at approximately 14 seconds, its actual `durationSeconds` must still be ≤15. The plan must contain four causal beats, no later trimming, and no extra cast/location changes without story evidence. Existing deterministic Opening Evaluation, Canonical Evidence, Premise Admission, Beat Grammar, `SHORT_FORM_ENGINE`, Creative Shape, Historical Territory, Ranking and Pre-Render QA outputs are recorded as returned; do not change thresholds or fill missing values. Stop on a genuine blocker.

## Human review and asset preparation

Only after a real candidate exists:

1. Review the premise and four-beat story; record approve/reject with reviewer and UTC time.
2. Use the existing character registry/reference for the actual generated protagonist. Verify its approval record and file hash; do not infer approval from file presence.
3. Specify the exact frame-zero visual state from the accepted seed. Prepare a candidate-specific vertical first frame through the existing visual-reference workflow. Do not generate, edit, replace, or approve it automatically.
4. Obtain separate human approval for the actual first-frame asset and bind its exact SHA-256, dimensions, aspect ratio, character reference, and visual plan ID.
5. Run existing image2video model/duration/aspect-ratio support preflight. Confirm the approved image is actually bound and there is no text-to-video fallback. If the currently configured integration cannot run image2video, stop and report that technical blocker.
6. Write the lifecycle/novelty review record described above; keep render authorization separate.
7. Run normal validation/pre-render QA and obtain a separate explicit render authorization. A passing new-concept guard is not itself render authorization.

No concept has been generated yet, so character identity, reference approval, first-frame content/approval, image2video compatibility and final duration are currently **not evaluated**. Do not mark the pilot ready until each is evidenced.

## Guard and idempotency repair

`ProductionLifecycleGuard` now distinguishes historical `UNKNOWN`, published, rendered, and explicitly recorded `NEW_CONCEPT` entries. New candidates bind the request's candidate ID to a unique registry ID, TWO_STAGE_V1 creation metadata, exact prompt SHA-256, UTC time, `NOT_RENDERED_CONFIRMED` plus `linkedRenderCount=0`, and hash-verified novelty-review evidence. Exact matches to historical records block even when publication status is unknown; confirmed published/exact/story-equivalent matches block normal production; high similarity requires human clearance. Reusing the same character alone remains eligible. Candidate creation does not issue render authorization.

The two prior Postgres idempotency failures were not caused by `ProductionLifecycleGuard`. They stopped earlier because the test fixture lacked the existing source-bound `PostFamilyAdmissionClient` and valid first-frame plan inputs. The Postgres test now mocks those upstream admission services and the lifecycle guard so it can isolate the idempotency contract, while guard behavior is separately covered by its real unit tests. The video request fixture includes a first-frame and plan binding. Production policy was not weakened.

## Focused and full verification

Focused Java command:

```sh
cd intelligence/creative-render-service
export JAVA_HOME='/Users/benanaktas/Library/Java/JavaVirtualMachines/corretto-21.0.9/Contents/Home'
export PATH="$JAVA_HOME/bin:$PATH"
mvn -q -Dtest=ProductionLifecycleGuardTest,RenderJobQueueServiceTest,RenderJobIdempotencyPostgresTest test
```

This run passed **32 tests**: 15 guard, 15 queue-boundary, and 2 real-Postgres idempotency tests; zero failures/errors/skips. Full Maven regression then passed **462/462 tests**, with zero failures/errors/skips.

Focused existing ML regression:

```sh
cd intelligence/ml-service
POMPOM_OFFLINE_MODE=true POMPOM_EXTERNAL_AI_AUTHORIZED=false PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_semantic_two_stage_v1.py tests/test_semantic_two_stage_phase_b_v1.py
```

Focused TWO_STAGE_V1 tests passed **60/60**. The new runner also passed Python byte compilation, `--help`, exact prepared-request/schema JSON parsing, and a missing-authorization check that exited before creating a run directory or sending a request.

Full offline ML regression: **3,493 passed, 36 failed, 2 skipped** (226.75s). This matches the accepted baseline exactly by identity: comparing the 36 current failure IDs with `semantic-two-stage-v1/verification.json` produced **0 new failures and 0 resolved baseline failures**. The full run added no provider or render calls. The ML scoring/generation modules and validator thresholds were not modified in this task; the new one-runner is an additive command and passed its focused checks.

The earlier lifecycle-run full Java result (456 tests, 2 known Postgres idempotency errors) was superseded by this run: both tests now pass once their fixtures supply the existing post-family and visual-reference admission dependencies. No historical evidence, prompt version, validator threshold or character registry was edited.

## Operator next action

The only action needed to start the bounded generation experiment is an explicit operator approval for **one Phase A call**. Create the exact `phase-a.txt` authorization shown above and run the Phase A command. Inspect the result before deciding whether to authorize Phase B. Until then, the candidate remains uncreated, and no content is production-ready.
