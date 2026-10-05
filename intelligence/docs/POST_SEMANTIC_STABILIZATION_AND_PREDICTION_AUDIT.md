# Post-Semantic Stabilization and Prediction Audit

Audit date: 2026-10-06
Scope: existing backend, ML service, frontend, PostgreSQL schema, and the current test asset `e2c9e9bb-9d53-43ad-a4ad-6dade3d9e4ef`.

## Executive Summary

The deterministic V5 plus semantic fusion path is working and must remain the
source for creative analysis and platform creative readiness. It is not a
performance predictor. The current database has no canonical publications or
performance observations, so the correct prediction state is insufficient data;
the existing prediction endpoint must not be treated as a trained model.

The most immediate correctness gap is character association. The prompt source
resolver scans all `.md` files in a video folder, including `social.md`,
`youtube.md`, `gate.md`, and `prompt.md`, and marks the folder ambiguous. The
current test asset therefore has a linked semantic prompt in the filesystem but
no persisted canonical character association.

## Capability Matrix

| Capability | Status | Evidence / finding |
|---|---|---|
| V5 motion analysis | COMPLETE | Persisted `sampled-visual-motion-v5` temporal profile. |
| Semantic VLM extraction | COMPLETE | Persisted `SemanticVideoEvidence`; no re-call needed for fusion. |
| Canonical semantic fusion | COMPLETE | `semantic-fusion-v1`; deterministic local endpoint and idempotent backfill. |
| Hook / payoff / loop assessments | COMPLETE | Canonical objects are persisted and consumed by detail/readiness APIs. |
| Temporal semantic context | COMPLETE | Relative dip is joined to overlapping semantic beat; recovery is preserved. |
| Platform creative readiness | PARTIAL | Uses canonical evidence and versioned policy, but profile fingerprint/explanation surface needs explicit audit output. |
| Creative fit vs prediction separation | PARTIAL | Backend wording separates them; prediction UI and old prediction data contracts still need a hard readiness gate. |
| Post-render asset assessment in Video Detail | PARTIAL | Canonical post-render QA exists in render dashboard, not prominently in ordinary Video Detail. |
| Prompt source resolution | PARTIAL | Existing resolver is reused, but metadata files are incorrectly treated as prompt candidates. |
| Canonical character association | PARTIAL | Infrastructure and missing-only backfill exist; current asset remains unresolved due prompt ambiguity. |
| Canonical vs visual character confirmation | MISSING | No persisted first-class VLM visual confirmation field is exposed in the current context response. |
| Plan / render fidelity | PARTIAL | `NOT_AVAILABLE` is honest; existing resolver/parser linkage to a structured plan is not wired into canonical fusion. |
| Relative dip vs absolute low motion | PARTIAL | Detector distinguishes them internally; UI wording/tooltips need explicit terminology. |
| Publication entity | COMPLETE | `video_publications` schema and service exist. |
| Performance observation entity | COMPLETE | Append-only `performance_observations` schema exists with nullable metrics and quality/source fields. |
| Publication-to-observation import linkage | PARTIAL | Import pipeline exists, but current DB has no publications or observations to validate against. |
| Observation horizons | PARTIAL | Timestamp data exists; canonical horizon/readiness projection is not a complete first-class workflow. |
| Paid/organic context | PARTIAL | Publication context supports labels, but observation-level organic/paid/mixed provenance is not fully represented. |
| Immutable prediction feature snapshot | MISSING | Current prediction reads the latest mutable `creative_fingerprints` row directly. |
| Platform-specific training dataset | MISSING | No canonical training-example builder or data-readiness projection found. |
| Prediction data readiness | MISSING | Existing prediction response can be cold-start, but no persisted per-platform readiness contract exists. |
| Prediction model activation gate | PARTIAL | Model registry exists, but prepublish client can return a cold-start payload without a dataset/model readiness gate. |
| Chronological validation | MISSING | No connected chronological training/evaluation workflow found in the current prediction path. |
| Prediction reliability UI | PARTIAL | Model registry/reliability pages exist, but no explicit per-platform data-readiness contract is shown. |
| VLM cost boundary | COMPLETE | Fusion, platform cards, prediction page, and feature reads are local/read-only paths. |

## Current Test Asset

The current asset is persisted with the expected semantic fusion result:

- Hook: `STRONG`
- Temporal structure: `LIKELY_PURPOSEFUL_HOLD`
- Payoff: `MODERATE`
- Semantic payoff: observed with partial timing
- Loop: strong visual evidence plus partial semantic evidence
- Local recovery: full
- Final rebound: not established
- Applicable evidence coverage: `100%`

The source folder contains `prompt.md`, `social.md`, `youtube.md`, `gate.md`,
and the video. The current resolver treats all eligible text/markdown files as
prompt candidates, so the stored status is `AMBIGUOUS` and no association is
persisted for this video.

## Database Inventory at Audit Time

| Table | Rows |
|---|---:|
| videos | 43 |
| creative_analyses | 53 |
| creative_fingerprints | 46 |
| video_prompt_resolutions | 43 |
| video_characters | 2 |
| prompt_versions | 1 |
| video_publications | 0 |
| performance_observations | 0 |
| predictions | 2 |
| model_versions | 0 |

The absence of publications and observations means no platform-specific
historical target can currently be trained or calibrated. No numeric view range
should be presented as a real performance forecast.

## Existing Prediction Path

`PredictionService.generate` reads the latest `CreativeFingerprintEntity` and
calls the ML prepublish endpoint. The feature row is analysis-derived, but it is
not an immutable prediction-time snapshot and does not itself carry the
publication cutoff, semantic schema, ruleset versions, character association,
or plan/fidelity lineage required by the new contract. The ML prediction
fallback is therefore suitable only as an evidence-ready cold-start response,
not as an activated learned model.

## Required Next Implementation Order

1. Make prompt resolution metadata-aware and run the existing missing-only
   character backfill; preserve manually confirmed associations.
2. Expose canonical character source and separate visual confirmation fields.
3. Add explicit profile fingerprints and criterion-level platform explanations
   without changing valid grades or consuming performance outcomes.
4. Make low-motion terminology and canonical post-render assessment visible in
   Video Detail.
5. Add an immutable prediction feature snapshot reusing the existing fingerprint
   data, with publication cutoff and version lineage.
6. Add platform-specific dataset/readiness projections over real observations;
   three or fewer eligible examples must remain `INSUFFICIENT_DATA`.
7. Gate numeric prediction/model activation on readiness and chronological
   validation. Until then, show no numeric forecast.

## Non-Regressions

- No new VLM call is required for any of the above local wiring work.
- Platform readiness remains creative fit, never performance prediction.
- Missing metrics remain unknown, not zero.
- Paid and organic evidence must remain distinguishable.
- No second prompt resolver, character resolver, or prediction subsystem should
  be introduced.
