# POMPOM Golden Calibration V1 Architecture

## Data Flow

```text
Frozen prompt bytes
        ↓
Manifest/hash verification
        ↓
PromptParser (existing)
        ↓
Canonical evidence (existing)
        ↓
RuleEngine + immutable RULESET 1.7 (existing)
        ↓
Assessment + scorer/API report (existing)
        ↓
Golden snapshot + full-stack fingerprint
        ↓
Gold Truth / baseline / current comparator
        ↓
Markdown + JSON report
        ↓
NEW SEMANTIC REGRESSIONS = 0
AND
UNEXPECTED POLICY REGRESSIONS = 0
```

## Input Contract

The engine receives only:

```json
{"prompt": "exact frozen prompt text"}
```

The following remain outside engine input:

- `corpusRole`
- winner/middle/negative labels
- views, reach, likes, shares, watch time, completion
- publication outcomes
- prediction outputs
- platform metrics

## Artifact Layers

| Layer | Location | Meaning |
|---|---|---|
| Frozen source | `intelligence/data/golden/pompom-golden-v1/prompts/` | Exact copied bytes from mounted production source |
| Manifest | `.../manifest.yaml` | Identity, hash, lineage, corpus metadata |
| Gold Truth | `.../truth/gold_truth.yaml` | Human-reviewed structural observations |
| Policy Expectation | `.../policy/policy_expectations_v1.7.yaml` | Ruleset/assessment/scoring-dependent outputs |
| Frozen semantic mode | `.../frozen-semantic/` | Local deterministic semantic boundary; no live provider in CI |
| Baseline | `.../baselines/v1.7/` | Current behavior before calibration fixes |
| Reports | `.../reports/` | Comparator JSON/Markdown and representation contracts |

## Classification Model

The comparator keeps these independent:

1. **Semantic/canonical result** — agreement between prompt evidence and Gold Truth.
2. **Policy result** — agreement with ruleset-scoped Policy Expectations.
3. **Baseline movement** — unchanged, improved, or regressed relative to v1.7.
4. **Release gate** — new semantic regressions and unexpected policy regressions.

A prompt may be structurally strong while having a blocked render authorization because visual evidence is pending. That is an expected three-outcome state, not a contradiction.

## Determinism

- Prompt hashes are checked before every run.
- Parser-created timestamps are normalized to `GOLDEN_DETERMINISTIC` in the harness snapshot only; source prompt bytes and production parser behavior are not changed.
- Semantic-check call sites use frozen deterministic decisions in `FROZEN_DETERMINISTIC` mode.
- Live providers are prohibited in CI mode.
- Parser timeouts become explicit baseline statuses and do not mutate source artifacts.

## Persistence Decision

V1 uses versioned tracked artifacts rather than a new database table. Existing prompt hashes, report snapshots, and validation lineage remain reusable. A calibration-run database entity should be added only when operators need historical run querying beyond the versioned JSON/Markdown artifacts.
