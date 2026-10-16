EXPERIMENT: REAL_MODEL_A_CAPABILITY_RESEARCH_V1
OWNER_AUTHORIZATION: YES
MAX_AUTHORIZED_USD: 0.674925
MAX_AUTHORIZED_REQUESTS: 6

REAL_DEEPSEEK_GENERATION: NO
REAL_OPENAI_GENERATION: NO

REAL_PROVIDER_REQUESTS_ATTEMPTED: 0
REAL_PROVIDER_REQUESTS_COMPLETED: 0

ACTUAL_PROVIDER_SPEND_USD: 0.000000
UNRESOLVED_BILLING: NO

SCOPE_FINGERPRINTS_MATCHED: NO
REVIEWER_INDEPENDENCE: FAILED

DEEPSEEK_CANONICAL_SCORE: NOT_AVAILABLE
DEEPSEEK_CANONICAL_GRADE: NOT_AVAILABLE
DEEPSEEK_CREATIVE_VALIDITY: NOT_AVAILABLE

OPENAI_CANONICAL_SCORE: NOT_AVAILABLE
OPENAI_CANONICAL_GRADE: NOT_AVAILABLE
OPENAI_CREATIVE_VALIDITY: NOT_AVAILABLE

REAL_PROVIDER_A_VERIFIED: NO
FULL_CANONICAL_A_ADMITTED: NO

OFFICIAL_CREATIVE_A_PLUS: INACTIVE

PROMPT_APPROVALS: 0
IMAGE_GENERATIONS: 0
VIDEO_RENDERS: 0
PUBLICATIONS: 0
PRODUCTION_DATABASE_WRITES: 0

EXPERIMENT_STATUS: BLOCKED

# Dispatch decision

The explicit owner authorization was accepted as the only authorization for the exact two-run plan. The mandatory non-billable preflight stopped the experiment before reservation or dispatch because the authorized immutable scope cannot be rebound in the current live environment.

The authorization requires this exact prompt fingerprint:

```text
1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5
```

The live production `prompt_versions` table contains only Content 10 / Prompt 10 version 1 with:

```text
0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98
```

No live immutable prompt version matches the authorized P2 prompt SHA. No live workflow event matches the authorized P2 story or prompt SHA. The UUIDs recorded in the P3 readiness report belong to the prior disposable acceptance database and were deliberately not reused.

This is a material scope mismatch. The authorization explicitly says to stop if any material fingerprint changes and forbids silently selecting a replacement prompt. The original Mimi Prompt 10 therefore cannot substitute for the authorized P2 baseline.

# Other pre-dispatch blockers

The current running containers report:

- backend `CPQ_PILOT_REAL_ENABLED=false`;
- ML service `CPQ_PILOT_REAL_ENABLED=false`;
- ML role dispatch is enabled internally, and both provider credentials are configured without exposing their values;
- backend provider dispatch remains governed off, so the official owner-scoped optimization endpoint must reject a run before creating a ledger record.

Enabling the backend flag would require a configuration/deployment change. This authorization explicitly forbids deployment and does not permit a global unrelated inference enablement.

Creating the missing story, prompt version, REVIEW analysis and owner-scoped durable optimization grant in the live database would require production database writes. Those writes are explicitly not authorized. The existing disposable HTTP fixture harness cannot be used as a substitute for this experiment: it supplies deterministic fixture provider responses and denies external egress, while the authorization requires genuine provider adapters for all generation and review calls.

# Preflight evidence

| Check | Result | Evidence |
|---|---|---|
| Owner authorization | PASS | Exact experiment name, request count, cost, output and timeout caps supplied |
| Expected story SHA | NOT REBOUND | Prior P2 story exists only in disposable evidence; no matching live workflow event |
| Expected prompt SHA | FAIL | Expected `1a9a…`; live Content 10 / Prompt 10 is `0fe229…` |
| Production settings SHA | NOT EVALUATED | Prompt mismatch already requires STOP |
| Source scope SHA | NOT EVALUATED | Exact live story/prompt records do not exist |
| Generation instruction SHA | PREVIOUSLY VERIFIED | `91561d…` in P3 readiness; no new request was compiled against a valid live scope |
| Provider profiles | CONFIGURED IN ML | DeepSeek and OpenAI credential presence verified without revealing secrets |
| Backend real dispatch | FAIL | `CPQ_PILOT_REAL_ENABLED=false` |
| Durable run ledger | EMPTY | `optimization_runs=0` |
| Durable request ledger | EMPTY | `optimization_run_requests=0` |
| Reviewer independence | NOT EXECUTED | No candidate or reviewer request was dispatched |
| Billing/accounting | COMPLETE AT ZERO | No reservation, attempt, response or ambiguous liability |

# Provider responses and candidate prompts

No provider request was attempted. There is no DeepSeek or OpenAI response, candidate prompt, source-fidelity review, creative review or model usage to reproduce. Pre-authored fixture responses were not substituted.

# Canonical and creative evaluation

No candidate was generated, so Ruleset 1.11 and `creative-validity-v1` were not run on a real-provider candidate. The P2 fixture baseline remains `93.42708333333334/A` with `CREATIVE_RISK_DETECTED`; it remains fixture evidence and is not reported as a real-model result.

No UNKNOWN was converted to PASS. Missing first-frame and audience evidence remain unresolved. Official A+ remains inactive.

# Cost and safety accounting

| Metric | Actual |
|---|---:|
| Authorized maximum | USD 0.674925 |
| Reserved | USD 0.000000 |
| Verified incurred cost | USD 0.000000 |
| Attempted requests | 0 |
| Completed requests | 0 |
| Ambiguous requests | 0 |
| Remaining authorized requests consumed | 0 |

The unused authorization was not extended or applied to another scope. No connectivity probe, fallback, retry, model substitution, image generation, rendering or publication occurred.

# Root-cause finding

Observed fact: the P3 comparison was prepared and verified against a disposable P2 acceptance record. Its portable hashes were recorded correctly, but the exact evolved story, generated prompt version and Ruleset analysis were never persisted in the current live production database.

Observed fact: the current live Content 10 record is the immutable original Prompt 10, whose prompt hash differs from the authorization.

Observed fact: the production backend real-dispatch gate is off.

Hypothesis not tested: either model's ability to repair the weak hook, repetitive consequences or overloaded ending. No provider inference occurred, so no capability conclusion is possible.

# Recommendation

`EXPERIMENT_INCONCLUSIVE`

The experiment did not reach a provider. No model should be preferred, and no instruction, reconstruction or evaluator limitation can be inferred from this blocked attempt.

To make a future execution legitimate, the owner must separately authorize one coherent environment choice:

1. create/import the exact P2 story, prompt version and Ruleset 1.11 analysis as immutable live records, authorize the required production writes and authorize deployment/configuration that enables only the bounded owner-scoped worker; or
2. authorize a dedicated disposable real-provider execution environment that recreates the exact bindings, uses the durable ledger, allows provider egress, and still preserves all request/budget/idempotency controls.

Either choice requires a fresh preflight and fresh authorization after the new record IDs and recomputed fingerprints are available. The present authorization cannot be reused automatically.
