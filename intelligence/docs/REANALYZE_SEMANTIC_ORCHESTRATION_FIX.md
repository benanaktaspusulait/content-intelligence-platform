# Reanalyze Semantic Orchestration Fix

## Root cause

The Video Detail `Reanalyze` button calls `VideoDetailPage.triggerAnalysis()`, which invokes
`CreativeIntelligenceService.triggerAnalysis()` and `POST /api/v1/videos/{id}/analysis?force=true`.
`VideoController` enqueues the normal `AnalysisJobService` job and the worker calls
`VideoService.analyse()`, which calls `MlVideoClient` and the ML `/v1/analysis/video` endpoint.

The V5 analyzer always constructed the semantic frame selection, but
`analyse_semantic_video()` returned unavailable evidence unless the ML process-level semantic
flag was enabled. The normal job did not declare that semantic analysis was requested, so it
completed deterministic V5 and persisted `NOT_REQUESTED`. The backend also discarded any prior
semantic evidence when making the next ML request, so there was no cache-aware decision.

## Fix

The existing V5 entry point now receives two optional request fields:

- `semanticRequested`: set only by the normal backend analysis job; ingest remains unchanged.
- `cachedSemanticVideoEvidence`: the latest persisted semantic evidence for the same video and
  analysis version.

The ML semantic layer first validates cache identity using the asset hash, semantic schema
version, frame-selection version, and persisted provenance. A valid row returns `CACHE_HIT` with
`providerCallCount: 0`. Missing or invalid evidence performs the existing single structured
semantic request. No model, prompt, routing, fallback, or Platform Lens policy changed.

Provider/configuration failures now use `NOT_CONFIGURED`; provider runtime failures use
`SERVICE_ERROR`. The frontend no longer reports a generic successful completion when semantic
analysis is unavailable and displays cache-hit evidence as evaluated semantic evidence.

## Runtime verification

Regression video: `07_luca_ball_spitting_crocodile_hd.mp4`

First normal analysis run:

- job: `5464b9f6-b463-41ee-85a0-407bcc01f86b`
- V5: `COMPLETED`
- semantic cache: `MISS`
- provider: `openai`
- model: `gpt-4o-mini`
- selected frames: `8`
- primary calls: `1`
- fallback calls: `0`
- retry calls: `0`
- summary calls: `0`
- total billable AI calls: `1`
- semantic result: `COMPLETED`, `FULL`
- fusion: recomputed locally

The provider response reported 295,386 input tokens and 1,167 output tokens. Estimated cost was
not configured, so no cost is claimed.

Second identical normal analysis run:

- semantic: `CACHE_HIT`
- new semantic provider calls: `0`
- fusion: local recomputation only

Page reload, tab switching, and Platform Lens reads consume the persisted analysis/read model;
they do not enter the ML semantic provider path. The current UI status polling observes the
completed job and the persisted semantic status without requiring a second click.

## Tests

`ml-service/tests/test_semantic_orchestration.py` locks the two critical paths: valid evidence
reuse with zero provider calls and explicit `NOT_CONFIGURED` when a requested provider cannot be
created. The existing local fusion remains provider-free.
