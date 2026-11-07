# Net-New Generation Diversity Recovery

## Outcome

The completed `net-new-v1-20261102-001` opening is recorded as `DUPLICATE_CREATIVE_TERRITORY`, linked to `mimi-rolling-pin-dough-wall` / **Flat-Pack Dough**. Its provider response, seed, and original opening gate remain unchanged. The new runner now places a bounded, hash-bound historical exclusion in a separate Phase A request message and checks each returned opening against its source-backed opening axes before Phase B eligibility.

Provider calls during this recovery: **0**. Render calls: **0**. Phase B calls: **0**.

## 1. Root cause evidence

The original Phase A request contained only two messages: the accepted system prompt and the user payload containing the canonical cast, prompt version, and requested count. The saved exact request is `intelligence/docs/net-new-generation-v1/runs/net-new-v1-20261102-001/phase-a/request-before-sdk.json`.

The saved system prompt (`semantic-opening-seed-prompt-v1`, SHA-256 `948c3658fa68907d4ee1d6c969a94f55584fe052fcf4cd968f772cfdf889632f`) and the user payload contain no rolling-pin, dough, ridge, wall, or prior-story examples. The mock fixture `intelligence/ml-service/tests/fixtures/semantic_two_stage_v1_mocks.json` also contains no rolling-pin/dough-ridge example. The live request assembly in `semantic_two_stage_v1.request_spec` made no historical lookup and attached no exclusion context. No evidence points to fixture leakage, a default rolling-pin/dough value, or a reused cached generation context. The historical experiments themselves show a repeated cluster: `opening-a/seed.json` is `mimi-rolling-pin-ridge`, `opening-b/seed.json` is `mimi-rolling-pin-dough-wall`, and `opening-c/seed.json` is `mimi-rolling-pin-dough-column`. All three use Mimi, a rolling pin, flattening dough, and pressure-induced upward growth beneath the barrel. The evidence supports a missing historical-diversity input; it does not prove why the model independently selected this premise.

## 2. Historical exclusion

One bounded exclusion is loaded from the canonical source seed:

- Concept ID: `mimi-rolling-pin-dough-wall`
- Source: `intelligence/docs/semantic-two-stage-v1-phase-b-run-001/source-seed.json`
- Source SHA-256: `90feac8225bf9c360a2604913d4c718a5d47b62906a2911a9fb9a2ea9cb62bb8`
- Mechanic: Mimi uses a rolling pin to flatten dough; pressure where the barrel contacts the dough makes that strip rise into a tall ridge or wall, lifting/supporting the barrel above the surrounding flat sheet.
- Reason: the historical seed was expanded into **Flat-Pack Dough**; the same causal opening territory is not acceptable as net-new.
- Context version: `net-new-opening-exclusions-v1`
- Supporting repeated-cluster records: `intelligence/docs/semantic-two-stage-v1-run-001/opening-a/seed.json` (SHA-256 `9bde97bbc49b99198f140031392d6c22f5271abf73a1af5a721fec5db6e9991f`) and `opening-c/seed.json` (SHA-256 `b7732d4b43fc065a8a0205c768d1004a1a5bbe0967be4c19d8c88553779a13ed`). The exclusion’s primary source remains the fully expanded Flat-Pack Dough seed above.
- Context SHA-256: `9903ea21f764c52b2b716d2a26fb8cb6e00c8a6728bbe69db0714e4478e827aa`

The context explicitly does not ban Mimi or rolling pins globally. It asks for a different causal rule and opening silhouette. The context record retains canonical source fields and source hash; the provider message is concise and does not include the complete old story.

## 3. Seed-stage novelty check

`intelligence/ml-service/app/workflow/net_new_novelty.py` uses the stored canonical protagonist, everyday goal, primary object, impossible rule, trigger, and frame-zero description. For the one known exclusion it checks six categorical axes: protagonist, goal, object, core rule response, trigger-response relationship, and first-frame relation. It has no weighted score. Exact categorical match is `DUPLICATE_CREATIVE_TERRITORY`; partial overlap is handled conservatively as `HIGH_SIMILARITY_REVIEW`, `UNKNOWN_SIMILARITY`, or `NO_KNOWN_EQUIVALENT`. Unknown is never converted to a pass. A same character or same object by itself does not block.

The comparison of the new seed matched all six axes and returned `DUPLICATE_CREATIVE_TERRITORY`. Evidence is in `intelligence/docs/net-new-generation-v1/runs/net-new-v1-20261102-001/creative-territory-review.json`. It binds the historical source, candidate seed, exact provider response, and original gate by hashes. Original evidence hashes recorded there:

- Response: `dc0efa713ca37c0d0d7c5a27c7aad13492ad700fe7f2373eff5d148da44c7b04`
- Seed: `0c1cccf299b18a9a6c3f46239fce3c1e4c89597fa7368f898e7961199d09435b`
- Opening gate: `fcfa62175bc4e0d7a889490d092c625e5218c8a49f4bfcc5f1ca25e3b923ab57`

This is an opening-only check. It does not synthesize beats, payoff, or a complete-story Creative Shape fingerprint. The existing Creative Shape/Historical Territory full-story functions are not used to fabricate absent Phase A structure.

The runner writes a novelty disposition for future Phase A results and refuses Phase B unless the existing opening gate passes and novelty is `NO_KNOWN_EQUIVALENT`. Duplicate, high-similarity, or unknown cases therefore cannot proceed automatically to Phase B. Existing admission logic and thresholds are untouched.

## 4. Request audit and prompt preservation

The accepted TWO_STAGE_V1 prompts were not edited. The new exclusion is attached as a separately versioned third user message after `request_spec` constructs the existing system and user messages. The existing model (`gpt-6.1-sol`), LOW reasoning, Phase A schema, one-seed count, and explicit one-request authorization remain required.

The exact sanitized next request is prepared at `intelligence/docs/net-new-generation-v1/prepared-phase-a-request-preview.json`. It contains the unchanged prompt, schema, new exclusion message, and context hash. Its required authorization is shown as a placeholder only; no authorization file was created. It is a preview and has not been sent.

## 5. Admission diagnostic kept separate

The duplicate opening scored **90** but had `RULE_UNCLEAR`; the prior equivalent seed had opening score **90** and was accepted for expansion under its earlier gate evidence. This is a separate evaluator/admission inconsistency worth investigating later. Admission code, validators, and thresholds were not changed here, and this duplicate was not made eligible.

## 6. Code changes

- Added `intelligence/ml-service/app/workflow/net_new_novelty.py` for loading one source-backed exclusion, constructing its versioned hash, and classifying seed openings using the six canonical axes.
- Updated `intelligence/scripts/run-net-new-two-stage-v1.py` to append the separately versioned exclusion message, save its context, write the seed-stage novelty result, and require a clean novelty disposition before Phase B.
- Added `intelligence/ml-service/tests/test_net_new_novelty.py` for paraphrases, distinct-character/object/rule cases, unknown handling, source immutability, prompt isolation, and explicit authorization/no-retry invariants.
- Added the additive historical duplicate record and exact request preview.
- No prompt, schema, validator, scoring threshold, historical source, or production asset was modified.

## 7. Test results

Focused run:

```text
69 passed in 2.93s
```

This included the new tests and TWO_STAGE_V1 Phase A/Phase B focused tests.

Full ML-service regression:

```text
3502 passed, 36 failed, 2 skipped in 224.68s
```

The repository's accepted full-suite baseline records 36 known failures. The current run also reported 36 failures, and all 36 baseline failure IDs remain present in the pytest failure cache; this supports the baseline count, though the full run did not emit a separately archived node-ID comparison. The full-suite run had one initial collection failure when run without the service scripts directory on `PYTHONPATH`; it was rerun with the correct path and completed as reported above.

## 8. Exact next operator action

Review `intelligence/docs/net-new-generation-v1/prepared-phase-a-request-preview.json`. If it is accepted, choose a fresh run ID and create the documented exact authorization file yourself:

```text
AUTHORIZE_PHASE_A:<new-unique-run-id>:MAX_PROVIDER_REQUESTS=1
```

Then run exactly one Phase A request through `intelligence/scripts/run-net-new-two-stage-v1.py` with that run ID and authorization file. The runner will apply the exclusion context and offline seed-stage check. Do not reuse the already-claimed `net-new-v1-20261102-001` run ID. No future provider call is authorized by this report.
