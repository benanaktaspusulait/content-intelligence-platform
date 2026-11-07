# Phase A Last-Mile Request Assembly Repair

**Status: `PHASE_A_REQUEST_ASSEMBLY_READY`**

The previously authorized execution is still `PHASE_A_EXECUTION_FAILED`; its run and authorization remain consumed. This repair was verified entirely offline. No fresh live authorization was created, and no OpenAI, Phase B, or render request was made.

## 1. Root cause and exact locations

The diversity-aware `request_spec` in `intelligence/ml-service/app/workflow/semantic_two_stage_v1.py` assembles the full request in `spec["arguments"]`, including three ordered messages. The runner appends the hash-bound exclusion as message 3. The last-mile guard in `intelligence/ml-service/app/workflow/semantic_compact_1_probe_v1.py:80-82` correctly hashes the full `spec["arguments"]` and blocks any mismatch.

The drop occurred in `CreativeCapabilityProvider.complete()` at `intelligence/ml-service/app/workflow/creative_provider_profiles.py:58-78`: its legacy path rebuilt `messages` from only `system` and `prompt` at lines 69-70. The worker calls that method at `semantic_compact_1_probe_v1.py:86`, so the adapter discarded the prepared third message before the unchanged exact guard compared SDK kwargs.

## 2. Minimal repair

The runner now copies the already-authorized `spec["arguments"]` into a private provider-configuration field in `intelligence/scripts/run-net-new-two-stage-v1.py:89-95`. For requests carrying that field, `CreativeCapabilityProvider.complete()` forwards a deep copy of that exact argument object directly to the SDK at `creative_provider_profiles.py:61-78`. It does not rebuild, filter, deduplicate, reorder, or rewrite messages. The legacy two-message builder remains the fallback for callers without an authorized request payload.

The existing exact guard in `semantic_compact_1_probe_v1.py:80-82`, native schema guard, request hashing, retry limit, timeout, and HTTP body check were not weakened or bypassed. The frozen worker source remains unchanged.

The repository's active-code integrity policy was extended with one explicit historical-to-approved hash transition for `creative_provider_profiles.py`. Its old hash remains recorded; additive before/after approval evidence is under this report directory. The historical source manifests and run evidence were not rewritten.

## 3. Prepared and last-mile request comparison

Prepared request: `intelligence/docs/net-new-generation-v1/prepared-phase-a-request-preview.json`

- Prepared request arguments SHA-256: `e0a93c0f3e56612cd051b434f001dd9b29e794bf91195ed39f54e35f61864bce`
- Offline end-to-end SDK request SHA-256: `e0a93c0f3e56612cd051b434f001dd9b29e794bf91195ed39f54e35f61864bce`
- Offline fake HTTP body SHA-256: same
- Canonical request equality: PASS (the test compares the complete Python request objects and their canonical digests)

Message-by-message comparison at SDK and fake HTTP boundaries:

| Index | Role | Content | Result |
|---|---|---|---|
| 0 | system | Accepted `semantic-opening-seed-prompt-v1` | Exact match |
| 1 | user | Accepted one-seed canonical-cast payload | Exact match |
| 2 | user | `net-new-opening-exclusions-v1` context message | Exact match |

The accepted prompt hash remains `948c3658fa68907d4ee1d6c969a94f55584fe052fcf4cd968f772cfdf889632f`. Schema is `semantic_opening_seed_v1`, hash `9fcb201118e45ebb75233a02b8f3f917ba01fc6033c46d3edd9e115e2842f06c`. Model/reasoning, 8,192 token cap, and 90-second timeout remain unchanged.

## 4. Exclusion integrity

- Source concept ID: `mimi-rolling-pin-dough-wall`
- Context version: `net-new-opening-exclusions-v1`
- Exclusion context SHA-256: `9903ea21f764c52b2b716d2a26fb8cb6e00c8a6728bbe69db0714e4478e827aa`
- Primary source seed SHA-256: `90feac8225bf9c360a2604913d4c718a5d47b62906a2911a9fb9a2ea9cb62bb8`

The context message delivered to the fake SDK transport preserved the exact prepared exclusion and context hash. The source concept identifies Mimi, a rolling pin, dough flattening, and pressure-induced vertical growth of dough under the barrel. The exclusion’s source path/hash and supporting seed provenance remain bound inside the versioned context record.

## 5. Offline end-to-end and negative test results

`test_runner_authorization_to_fake_http_transport_preserves_three_messages` ran the real Phase A runner through authorization verification, request construction, provider adapter, SDK method, unchanged exact-request guard, native schema guard, HTTP event hook, and a local `httpx.MockTransport`. The fake transport received exactly one request with exactly the authorized three messages. No socket or external network was used. The fixture response was a previously stored response; no concept was generated.

Negative cases all blocked before the fake transport:

- Third message omitted
- Third message changed
- Messages reordered
- Exclusion duplicated
- Context hash changed
- Unexpected extra message added

Authorization-boundary tests also blocked missing authorization, mismatched run ID, disabled external provider authorization, and an already-claimed/consumed run ID. The existing text authorization format has no separate wall-clock expiry field; its one-shot lifecycle is enforced by the unique claimed run directory. No new expiry scheme was introduced.

The legacy adapter test confirms a caller without `_authorizedRequestArguments` still sends the original two messages.

## 6. Focused and full regression

Focused command covered the new assembly tests, native schema guard tests, provider adapter tests, TWO_STAGE_V1 Phase A/Phase B tests, and protected-integrity policy tests:

```text
131 passed, 1 warning in 6.73s
```

Full ML-service regression:

```text
3514 passed, 36 failed, 2 skipped in 223.36s
```

The accepted pre-repair baseline records 36 known failures and 2 skips; the current run also reported 36 failures and 2 skips. All 36 accepted baseline node IDs remain present in pytest's failure cache. The 12 added assembly tests passed in the focused run and the full run. No new unexplained failure was observed. The one warning is the existing deprecated `google.generativeai` import warning.

## 7. Request and safety counts

- OpenAI/provider calls during repair/tests: **0**
- External HTTP requests: **0**
- Local fake HTTP requests in positive E2E test: **1**
- Negative-case transport requests: **0**
- Phase B calls: **0**
- Render calls: **0**
- Retries/fallbacks: **0 / 0**
- Prior failed execution authorization reused: **No**
- Fresh live authorization created: **No**

The old exhausted authorization file still contains `AUTHORIZE_PHASE_A:net-new-v1-diversity-e0a93c0f3e56612cd051b434f001dd9b:MAX_PROVIDER_REQUESTS=1` and retains SHA-256 `3d9d833f51c1138de29c2518ba269cda55941bd12c2d6e0b11ae0139a6a2a937`. It was not used by these tests. The prior failed run evidence remains under its original run directory.

## 8. Proof of unchanged creative assets and source evidence

No prompt version, schema, creative validator, scoring threshold, or historical seed was changed. The exact request preview remains unchanged. Historical seed files match the hashes bound in the exclusion context. The failed prior response/gate and exhausted authorization artifacts were not overwritten. The only integrity-policy update is the explicit adapter source hash approval described above; the previous historical hash and manifests remain present.

## 9. Exact next operator action

Review this report and the prepared request preview. If you choose to run a live request, issue a **new explicit authorization** for a fresh run ID and the exact prepared request hash. Do not reuse `net-new-v1-diversity-e0a93c0f3e56612cd051b434f001dd9b` or its authorization. This repair authorizes no provider request. Phase B and rendering remain unauthorized.
