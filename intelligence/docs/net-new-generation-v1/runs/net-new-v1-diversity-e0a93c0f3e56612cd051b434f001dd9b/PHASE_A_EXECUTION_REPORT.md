# Phase A Execution Report — Request Failed Before Provider Forwarding

**Final classification: `PHASE_A_EXECUTION_FAILED`**

The accepted runner was invoked once under the explicit authorization for run `net-new-v1-diversity-e0a93c0f3e56612cd051b434f001dd9b`. Its exact-request guard rejected the request before forwarding it to the OpenAI SDK/HTTP transport. The one authorized execution attempt is consumed. Per instruction, there was no retry, repair, model switch, Phase B request, or render.

## 1. Execution configuration

- Architecture/phase: `TWO_STAGE_V1` / A
- Provider/model/reasoning: OpenAI / `gpt-6.1-sol` / LOW
- Candidate count: 1
- Accepted Phase A prompt SHA-256: `948c3658fa68907d4ee1d6c969a94f55584fe052fcf4cd968f772cfdf889632f`
- Schema: `semantic_opening_seed_v1`; existing native schema SHA-256 `9fcb201118e45ebb75233a02b8f3f917ba01fc6033c46d3edd9e115e2842f06c`
- Maximum output: 8,192 tokens; timeout: 90 seconds; SDK retries: 0
- Request argument SHA-256: `e0a93c0f3e56612cd051b434f001dd9b29e794bf91195ed39f54e35f61864bce`
- Prepared preview request arguments and the assembled runner request matched exactly in preflight.

## 2. Authorization evidence

- Authorization: `AUTHORIZE_PHASE_A:net-new-v1-diversity-e0a93c0f3e56612cd051b434f001dd9b:MAX_PROVIDER_REQUESTS=1`
- Authorization file: `intelligence/docs/net-new-generation-v1/authorization/phase-a-net-new-v1-diversity-e0a93c0f3e56612cd051b434f001dd9b.txt`
- Bound request hash and exclusion context hash are recorded in the sibling `.authorization.json` file.
- The run ID is fresh and includes the request-argument hash prefix. The output directory was absent before invocation.
- Preflight verified: exact accepted prompt, schema, model, reasoning, one candidate, max tokens, timeout, retry policy, exclusion payload/context hash, historical source hashes, credential availability, and unused run ID.

## 3. Historical exclusion

The exact versioned context was `net-new-opening-exclusions-v1`, SHA-256 `9903ea21f764c52b2b716d2a26fb8cb6e00c8a6728bbe69db0714e4478e827aa`.

It excluded concept `mimi-rolling-pin-dough-wall`: Mimi presses a rolling pin to flatten dough, but the dough beneath its barrel grows into a vertical ridge/wall that raises or supports the barrel above the surrounding flat sheet. It explicitly did not ban Mimi or rolling pins independently. The primary source hash and two supporting historical-seed hashes are preserved in `historical-exclusion-context.json`.

## 4. Provider result and exact failure

The runner produced `phaseAStatus=FAILED`, no candidate, no response bytes, and no opening evaluation. The recorded error was:

```text
ValueError: Last-mile SDK request differs from accepted exact request
```

The accepted worker's last-mile guard compares the SDK arguments against the request built by `CreativeCapabilityProvider.complete`. The runner's new exclusion was appended as a third message to `request_spec.arguments`, while that provider adapter rebuilds its request with only the original system message and original user prompt. The guard detected the mismatch and stopped before SDK forwarding. This is the exact transport integration failure; it is not a provider timeout or malformed response.

Evidence: `phase-a/result.json` and `phase-a/worker-result.json` record `SDKRequestsForwarded=0`, `HTTPRequestsObserved=0`, no provider/HTTP request ID, no usage, and a safe trace through `exact_guard`. `phase-a/request-before-sdk.json` retains the rejected assembled arguments.

## 5. Complete seed and opening evaluation

No seed was returned. There is no seed ID or candidate ID, and no complete opening fields to provide. Offline opening validation, coverage repair, premise naturalness, admission, and seed-stage novelty comparison did not run because parsing requires a provider response. Opening score, goal visibility, abnormal-state visibility, goal interference, rule clarity, gate disposition, and novelty are therefore **NOT EVALUATED**. Phase B eligibility is false.

No creative-review claims about beats, payoff, frame comprehensibility, or novelty can be made without a seed.

## 6. Provider usage and request counts

- Runner Phase A invocation/logical attempt: **1**
- SDK requests forwarded: **0**
- HTTP requests observed: **0**
- Duration until guard failure: **0.713 seconds**
- Response bytes: **0**
- Input/output/reasoning tokens: unavailable; no provider response
- Provider-reported cost: unavailable; no provider response (not estimated)
- Retries / replacements / fallback providers: **0 / 0 / 0**
- Phase B calls: **0**
- Render calls: **0**

The single authorized attempt is exhausted. This report does not authorize another attempt.

## 7. Prompt, validator, and historical evidence integrity

No prompt, schema, validator, threshold, historical seed, or production asset was edited during this execution. The actual saved prompt and schema match the prepared preview. Historical evidence bytes matched their source hashes during preflight and are retained unchanged. The failed request, authorization, context, and result artifacts are additive under this run directory and the authorization directory.

## 8. Required stop

Stop at this failure. Do not retry this run, create another run, alter the adapter, rebuild the request, make a second authorization, execute Phase B, or render under this task. Any future live request requires a new user instruction/authorization after the request-assembly integration is separately addressed and reviewed.
