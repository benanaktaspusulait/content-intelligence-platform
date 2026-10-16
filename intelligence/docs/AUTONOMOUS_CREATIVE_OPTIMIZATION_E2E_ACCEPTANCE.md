# Autonomous Optimization V1 — End-to-End Acceptance

## Operator question

**Can the owner now start one bounded autonomous optimization from Step 6, leave it running without manual prompt editing, and receive a defensible best-candidate result?**

**PARTIALLY.** The deployed backend worker and durable run contract are ready, and the isolated application tests prove multi-round continuation with the actual evaluator. The live Step 6 panel is present and correctly fails closed. The owner profile is mounted and the browser session is authenticated as `benan`; protected-source preflight completed read-only. Real provider dispatch is intentionally disabled, so no paid request was made.

## Deployment

- Flyway migration `V68` is applied (`success=true`).
- Backend: `sha256:b51367255e8543a9aa524059de7cd5673a8f3b67e3b293375a78b0974e2143b4`.
- ML service: `sha256:bcf5371af5d92639474980639ae3ee4a89c016fed279164e09bb4eb1687ebff5`.
- Frontend: `sha256:8616ecf5e35557677318e79d7382305baca66f51596bbed3bc76dd94d76f8be3`.
- Backend health is `UP`; `optimization_runs` contains zero production runs.
- Backend and ML both report `CPQ_PILOT_REAL_ENABLED=false`.

## Exact provider role matrix

| Role | Legal profile | Provider/model | Reasoning | Output cap | Pricing basis |
|---|---|---|---|---:|---|
| Generation (DEEPSEEK_ONLY) | `deepseek-primary` | DeepSeek `deepseek-v4-pro` | `none` | 6,000 | $1.32/M input, $3.96/M output |
| Source fidelity | `openai-escalation` | OpenAI `gpt-6.1-sol` | `low` | 8,000 | $2.50/M input, $10.00/M output |
| Independent critic | `openai-escalation` | OpenAI `gpt-6.1-sol` | `low` | 8,000 | $2.50/M input, $10.00/M output |

This is a legal configuration under the current contract: the source and critic profile differ from the generator profile. The service rejects a grant that omits either review role, changes the model/reasoning binding, enables retries, or exceeds the declared limits. `OPENAI_ONLY` is also structurally legal with DeepSeek as the independent review profile. `ADAPTIVE` requires both generator profiles and therefore six role allowances; it is not needed for the smallest first experiment. CPQ A/A+ is unavailable because no calibrated active contract exists.

For a proposed two-round run, the honest request budget is six calls: two generations, two source reviews and two critics. Using a conservative 32,000 input-token assumption per call and the published caps above gives approximately `$0.77` worst-case provider cost before a small accounting margin. The proposed combined ceiling is **$0.90**, with no retry or fallback and an explicit maximum of 6 requests, 2 rounds and 900 seconds.

## Live browser acceptance

The deployed Chrome tab was reconnected and the actual Step 6 Repair page was inspected. The Creative Optimization panel expands and shows the owner pilot and the new “Automatic prompt optimization” panel. The owner pilot visibly states:

> Owner authentication awaits private configuration. No temporary identity is created.

The automatic panel visibly states:

> Use Owner login above to inspect and authorize a run.

The authenticated owner session exposes the bounded configuration, protected baseline and consent gate. The Start button remains disabled because `realDispatchEnabled=false`; no write request or provider request was sent. Stop cannot be exercised without a running disposable run. This is an explicit dispatch safety block, not a successful real-run click-through.

`BROWSER_START_STOP` is therefore **BLOCKED** by intentionally disabled real dispatch. The owner login and read-only preflight portions were verified in the live deployed UI.

## Autonomous continuation evidence

The isolated disposable backend test suite uses the Python mock transport, the actual ML compiler and the actual Ruleset 1.11 evaluator. `OptimizationLoopTest` passed **11/11** and covers:

- baseline evaluation, generation, source review, critic review and comparison;
- a qualifying second round receiving the current best candidate, prior useful changes, remaining findings and rejected regressions;
- distinct draft fingerprints and durable per-round events;
- a later equivalent/regressing candidate being rejected;
- idempotent Start, cancellation, budget/request/time limits and ambiguous accounting;
- immutable scope and authorization bindings.

This proves the backend continuation contract in isolation. It does not prove real-model creative quality and it is not a production run.

`AUTONOMOUS_MULTI_ROUND` is **VERIFIED (isolated application acceptance)**.

## Mimi regression case

The loop uses the saved Mimi evidence without rewriting it:

- Original Prompt 10 v1: `88.40625 / B`, two parsed attempts.
- V2: `80.25520833333334 / B`, zero parser-recognized attempts and an evaluator-integrity warning.
- V3: `88.40625 / B`, two parsed attempts; body SHA-256 `f362df56f7a54ee37002ee9e6f756edd59eb50fe5d0c484ee80416b4d954498a`.

The loop classifies the V2 loss as parser/evidence unreliability, never invents a third attempt, never treats parser recovery as creative improvement, and does not alter the approved story to chase 92. The original Mimi record remains a B baseline with explicit canonical failures and is not automatically selected for paid generation while the owner/preflight gate is unresolved.

## Eligible real-run subject

The database currently exposes one saved prompt subject: Content 10 / Prompt 10 v1 (Mimi), bound to the approved story and production settings. It is the only possible existing subject, but it is **not yet confirmed eligible** because authenticated preflight cannot run and the subject carries known ATTEMPT_001 and production-risk findings. No fake source or new prompt version was created. If owner preflight reports a legitimate source-faithful improvement path, Mimi can be considered; otherwise the correct result is `NO_ELIGIBLE_REAL_OPTIMIZATION_SUBJECT`.

## Exact authorization request (prepared, not executed)

After the owner credential is configured and preflight returns eligible, the operator must explicitly authorize this exact grant:

- Subject: Content 10, Prompt 10 version 1, approved story SHA and current production settings as returned by preflight.
- Target: `CANONICAL_RULESET_1_11_A`, Ruleset 1.11, threshold 92.
- Mode: `DEEPSEEK_ONLY`.
- Generation: DeepSeek `deepseek-v4-pro`, reasoning `none`, max 6,000 output tokens.
- Source reviewer: OpenAI `gpt-6.1-sol`, reasoning `low`, max 8,000 output tokens.
- Critic: OpenAI `gpt-6.1-sol`, reasoning `low`, max 8,000 output tokens.
- Maximum: 2 rounds, 6 total requests, 32,000 assumed input tokens per call, $0.90 combined ceiling, 900 seconds.
- No retry, no fallback, stop on ambiguity, unknown billing, source failure, regression, no progress, target reached or limit.
- Production effect: append-only run/request/draft/event evidence only; no automatic prompt approval, no new prompt version, no grading activation, no render and no publishing.

This is a request for a future explicit **YES/NO** owner authorization. It is not authorization to dispatch now.

## Final state

```text
BROWSER_START_STOP: BLOCKED
AUTONOMOUS_MULTI_ROUND: VERIFIED
PROVIDER_ROLE_CONFIGURATION: VALID
REAL_RUN_PREFLIGHT: READY
OWNER_PAID_AUTHORIZATION: NOT_RECEIVED
REAL_PROVIDER_RUN: NOT_EXECUTED
CANONICAL_A_ACHIEVED: NOT_EVALUATED
GENUINE_CREATIVE_IMPROVEMENT: UNVERIFIED
CPQ_GRADING: INACTIVE
RENDER_AUTHORIZED: false
REAL_DISPATCH_FINAL: DISABLED
```

The remaining prerequisite is a separate explicit owner authorization for the exact grant above, followed by guarded dispatch enablement. No paid inference should be attempted before that authorization.
