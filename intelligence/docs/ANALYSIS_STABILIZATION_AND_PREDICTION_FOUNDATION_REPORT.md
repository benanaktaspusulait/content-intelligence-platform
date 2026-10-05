# Analysis Stabilization and Prediction Foundation Report

Date: 2026-10-06

## 1. What Was Already Working

- V5 motion analysis and persisted semantic VLM evidence were already available.
- `semantic-fusion-v1` now provides the canonical hook, payoff, loop, temporal
  structure, plan availability, and applicable coverage projection.
- Platform readiness is a creative-fit policy lens and explicitly does not use
  views, likes, retention, or prediction output.
- Fusion/backfill and platform switching are local operations; they do not call
  the VLM.

## 2. Analysis Stabilization Result

For video `e2c9e9bb-9d53-43ad-a4ad-6dade3d9e4ef` the persisted result remains:

- Hook: `STRONG`
- Temporal structure: `LIKELY_PURPOSEFUL_HOLD`
- Payoff: `MODERATE`; semantic payoff observed with partial timing
- Loop: strong visual endpoint evidence plus partial semantic continuity
- Local recovery: full
- Final rebound: not established
- Applicable evidence coverage: `100%`

The relative activity dip remains distinct from an absolute low-motion interval.
No detector thresholds were changed.

## 3. Character and Prompt Lineage

The previous `AMBIGUOUS` result was caused by treating every `.md`/`.txt` file
beside a video as a production prompt. The resolver now prefers one canonical
prompt filename (`prompt.md`, `video_prompt.*`, `generation_prompt.*`, or
`openart_prompt.*`) while preserving ambiguity when multiple real prompts exist.

The existing missing-only backfill was run:

- scanned: `41`
- associations created: `12`
- unresolved errors: `0`
- manually/strongly curated associations overwritten: `0`

Current asset result:

- canonical character: `Luca`
- participation: `PRIMARY`
- association source: `PROMPT_FILE_INFERRED`
- confidence: `HIGH`
- prompt source: `.../19_hickiran_kutu/prompt.md`

The VLM semantic descriptor remains separate from canonical identity. An
`UNKNOWN` VLM canonical name must not overwrite the prompt-derived `Luca`
association.

## 4. Plan / Render Fidelity

The current asset has a linked generation prompt, but no structured production
contract or resolved `VideoPlanIR` in the current backend context. Therefore
plan/render fidelity remains `NOT_AVAILABLE` rather than fabricated. This is
honest and compatible with `100%` applicable readiness coverage because plan
fidelity is not an applicable required dimension for this legacy evidence row.

## 5. Platform Profile Audit

All four profiles are active policy hypotheses with criterion-level importance
and explanations. Runtime fingerprints prove the effective configurations differ:

| Platform | Fingerprint | Current grade | Coverage |
|---|---|---|---:|
| Facebook Reels | `d31a98e0eef89c20` | B | 100% |
| Instagram Reels | `c82f5a7aecdc323c` | B | 100% |
| TikTok | `d23cf4eabd30a90c` | B | 100% |
| YouTube Shorts | `2830f51b917b1093` | B | 100% |

The same grade is valid: the profiles use different priorities without adding
invented platform multipliers. The UI continues to label this as creative fit,
not performance prediction.

## 6. Observed Performance Inventory

Current PostgreSQL inventory:

| Entity | Rows |
|---|---:|
| videos | 43 |
| video_publications | 0 |
| performance_observations | 0 |
| model_versions | 0 |
| predictions | 2 |

The append-only observation schema already supports nullable metrics, source,
quality, paid flag, publication timestamp, measurement timestamp, and canonical
video linkage. The current environment has no imported observations to validate
the complete publication linkage against.

## 7. Prediction Foundation Result

- Added immutable `prediction_feature_snapshots` storage. It stores only
  analysis-derived pre-publish features, version lineage, semantic schema, and
  knowledge cutoff; it cannot contain outcomes.
- Pre-publish prediction creation records the snapshot ID in its payload.
- Added platform readiness projection over imported observations.
- Current status for Facebook, Instagram, TikTok, and YouTube Shorts: `NO_DATA`.
- Fewer than three eligible organic observations is explicitly insufficient;
  no numeric forecast is allowed.
- YouTube is accepted by the prediction contract instead of being offered by UI
  while rejected by the ML request schema.

## 8. Existing Prediction Code Status

The existing prediction path remains in place and is not duplicated. Its
`cold-start-baseline-v1` response is evidence-ready with null expected values,
zero comparable sample size, and explicit uncertainty reasons. It must remain a
cold-start response until real observations, leakage-safe feature snapshots,
platform-specific datasets, and chronological validation exist.

## 9. Remaining Gaps

- Import real publication and observation data, including organic/paid/mixed
  context and observation age/horizon.
- Add the complete platform training-example builder over immutable snapshots and
  canonical observations.
- Add chronological validation and calibrated model activation gates.
- Link structured production plans where they actually exist, then evaluate
  character/object/opening/mechanic/action/beat/payoff/ending fidelity.
- Expose the separate VLM visual-confirmation state next to canonical character
  association in the detail read model.
- Surface the canonical post-render assessment prominently in ordinary Video
  Detail; the current canonical post-render workflow remains in Render Dashboard.

## 10. Cost and Leakage Verification

- No new VLM call was caused by this work.
- Existing semantic evidence was reused.
- Platform readiness, prediction readiness, prompt/character backfill, and
  feature snapshot creation are local/database operations.
- Performance metrics are not used by Platform Lens.
- No numeric performance forecast is generated from the current empty dataset.
