# Semantic Evidence Reproducibility Report

Version: `semantic-reproducibility-v1`  
Scope: Hıçkıran Kutu (`e2c9e9bb-9d53-43ad-a4ad-6dade3d9e4ef`)

## Executive Result

The current PostgreSQL database contains **one persisted semantic VLM run** for the
audited asset. The earlier and later semantic summaries therefore cannot be proven to
be same-input model variance from the database alone. The defensible classification is:

> `HISTORICAL_COMPARISON_UNAVAILABLE`

The new runtime records the exact semantic request fingerprint and frame manifest. A
normal production analysis remains one VLM call and reuses evidence only when the
fingerprint matches. Exact replay is test-only, asset-scoped, and disabled by default.

## Historical Audit

| Analysis ID | Created | Analysis version | Semantic status | Provider/model | Frame selector | Frames | Prompt version |
|---|---|---|---|---|---|---:|---|
| `b8379891-429b-42dd-a721-a95a9f23de54` | 2026-10-05 19:55:34 UTC | `sampled-visual-motion-v3` | no semantic evidence | n/a | n/a | 0 | n/a |
| `94fc8225-38f4-4663-806b-2ec6e1265059` | 2026-10-05 20:04:15 UTC | `sampled-visual-motion-v4` | no semantic evidence | n/a | n/a | 0 | n/a |
| `c264b465-5281-41c0-8a86-6cd9fee9d91c` | 2026-10-05 23:01:14 UTC | `sampled-visual-motion-v5` | `COMPLETED` | `openai / gpt-4o-mini` | `semantic-frame-selection-v2` | 8 | legacy run did not persist a prompt version |

Asset hash for the persisted semantic run:
`fcba5934179363b02b063083dd075a3b7c2d66db69e9167773fbf704cd5e9816`.

The persisted run used the `STANDARD` image preparation profile, 8 frames, 295,380
input tokens, 1,134 output tokens, and one provider call. The exact timestamps were:
`0.000, 0.500, 1.000, 1.500, 7.302, 13.604, 14.104, 14.604` seconds.

Because no earlier semantic result with a fingerprint, frame hashes, prompt version,
or raw semantic payload exists in PostgreSQL, the historical hook/payoff/loop change
cannot be attributed to stochastic model behaviour. It remains an unresolved historical
comparison, not a proven nondeterminism finding.

## Reproducibility Contract

Every new semantic result stores:

- immutable `semanticRequestFingerprint`
- ordered `semanticFrameManifest` with timestamp, selection reason, source event/beat,
  frame hash, prepared image hash, dimensions, and availability
- prompt, schema, normalizer, canonical beat, hook, payoff, loop, context, and image
  preparation versions
- provider/model, routing policy, context hashes, provider call count, latency, token
  usage, and cache state
- raw provider beat observations plus deterministic `canonicalBeats`
- deterministic consistency validation with `VALID`, `QUESTIONABLE`, or `INVALID`

Volatile request IDs, timestamps, and database IDs are deliberately excluded from the
fingerprint. Frame order and bytes are included, so either change invalidates reuse.

## Semantic Interpretation Boundary

The semantic layer extracts visible evidence only. Unsupported conclusions remain
`UNKNOWN`; it does not convert motion rebound into semantic payoff or pixel similarity
into semantic loop continuity. Canonical `Child` is kept as a separate registry entry
from named Pompom characters. Hook, payoff, loop, object, character, and beat fields
carry frame support and confidence where the provider can support them.

## Replay Policy

`POST /v1/test/semantic-replay` is disabled unless `SEMANTIC_REPLAY_ENABLED=true`.
It accepts the persisted frame manifest, bypasses the result cache, makes one provider
call per replay, and rejects every asset except the audited Hıçkıran Kutu hash. The
request accepts replay indices `1..3`, so the audit cannot accidentally turn into an
unbounded production fan-out. No production endpoint calls this route.

## Controlled Replay Result

The persisted 8-frame manifest was replayed exactly three times after deployment of
the reproducibility code. All three requests produced the same fingerprint:
`50a2980b689e043244ca642de39833a637dfad83944145ebac8aeb4d1f442eef`.

| Replay | Status | Provider call count | Canonical beats | Hook | Payoff | Loop |
|---:|---|---:|---:|---|---|---|
| 1 | `COMPLETED` | 1 | 1 | `false` | `ongoing` | `potential for ongoing engagement` |
| 2 | `COMPLETED` | 1 | 1 | `true` | `null` | `ongoing` |
| 3 | `SERVICE_ERROR` | unavailable | 0 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |

The first two successful calls prove that output variability exists even when the
effective fingerprint is identical. The third result is a provider/service failure,
not semantic evidence, and is retained as `UNKNOWN`. This is the first reproducible
same-input variance finding; it is not merged or averaged into production evidence.

## Runtime Decision

Production defaults are now `SINGLE_MODEL` with fallback disabled. Fallback routing is
still available only through explicit configuration for controlled evaluation. This
keeps ordinary analysis to one VLM call and preserves cache reuse for an identical
fingerprint.

## Verification

- Reproducibility unit tests: 9 passed.
- Python AST validation: passed for modified ML modules.
- Angular production build to an isolated output directory: passed; existing bundle
  budget warnings remain, and the repository `dist` directory has an ownership lock.
- Docker services were healthy before the source-only changes. Container rebuild and
  replay calls must be performed after the final image build.
