# Semantic Fusion Fix Report

## Current bugs

- V5 hook/payoff/loop projections were motion-only and retained “semantic not
  configured” explanations after semantic evidence existed.
- The platform lens read raw temporal fields instead of a canonical fused result.
- Temporal dips had no semantic-beat overlap join.
- Historical rows had semantic evidence but no current fusion projection.

## Fixes

- Added `semantic-fusion-v1` as the single local canonical projection for hook,
  payoff, loop, temporal structure, plan availability, and applicable coverage.
- Fusion consumes persisted V5 and semantic evidence and never calls OpenAI.
- Added a local `/v1/analysis/semantic-fusion` endpoint for idempotent historical
  recomputation. Backend status reads backfill the projection once and persist it.
- Platform readiness now consumes canonical hook/payoff/loop/temporal values.
- Video detail uses canonical strength/summary fields; raw semantic details remain
  inspectable separately.
- Added an audit table at `docs/SEMANTIC_FUSION_WIRING_AUDIT.md`.

## Versioning

- `semantic-fusion-v1`
- `hook-assessment-v1`
- `payoff-assessment-v1`
- `loop-assessment-v1`
- `temporal-structure-assessment-v1`

## Verification

The fusion endpoint is deterministic and provider-neutral. Existing persisted
semantic evidence can be rewired with zero additional VLM calls. Full test and
runtime verification should be run after the backend/ml containers are rebuilt.

## Known limitations

- Legacy prompt/plan lineage remains `NOT_AVAILABLE` unless the existing prompt
  resolver has already linked a structured source.
- Post-render render-service assessments remain a separate persisted workflow;
  this change makes ordinary video-detail and platform readiness consume the
  canonical fused semantic projection.
