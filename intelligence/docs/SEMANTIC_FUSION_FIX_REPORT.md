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

- Targeted ML fusion tests pass (`7 passed` in the semantic routing/fusion test
  module).
- Backend production compilation passes with Maven test compilation skipped;
  the repository still has an unrelated pre-existing test-source constructor
  mismatch in `PlatformIntegrationTest` when test compilation is enabled.
- Containers were rebuilt and restarted successfully. ML, backend, PostgreSQL,
  render service, and frontend are healthy; the frontend route returns HTTP 200.
- Existing video `e2c9e9bb-9d53-43ad-a4ad-6dade3d9e4ef` was backfilled through
  the deterministic `/v1/analysis/semantic-fusion` endpoint. Persisted output
  is `semantic-fusion-v1`, with hook `STRONG`, payoff `MODERATE`, loop
  `MODERATE`, and `100%` applicable coverage.
- ML logs confirm one local fusion request and no new video-analysis/VLM call.

## Known limitations

- Legacy prompt/plan lineage remains `NOT_AVAILABLE` unless the existing prompt
  resolver has already linked a structured source.
- Post-render render-service assessments remain a separate persisted workflow;
  this change makes ordinary video-detail and platform readiness consume the
  canonical fused semantic projection.
