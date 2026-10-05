# Semantic AI Cost Optimization Plan

## Scope

This plan optimizes the existing V5 -> semantic frame selector -> provider-neutral
vision pipeline. It does not create V6, replace `VisionLanguageModelProvider`,
remove OpenAI, change Platform Lens scoring, or bulk-process the stock library.

## Current baseline audit

- Deterministic V5 remains the first and always-on analysis.
- The semantic pass receives materialized JPEG frames, not the source MP4.
- The previous selector could send up to 14 frames and had no persisted selection
  manifest, so reanalysis repeated frame extraction.
- The existing real smoke tests observed approximately `$0.11` per semantic call.
  This is an observed test value, not a universal price. Exact cost is only
  computed when input/output price configuration is supplied.
- OpenAI usage metadata already arrives as input/output token counts and request ID.
- Semantic evidence is persisted in `creative_analyses.raw_result` under
  `semanticVideoEvidence`; no new provider-specific table is required.
- The current analysis cache is version/asset based at the backend job boundary:
  normal analysis reuses the current analysis; forced reanalysis intentionally
  creates a new call.

## V1 policy

`SEMANTIC_ROUTING_MODE=PRIMARY_WITH_FALLBACK` runs a configurable primary model
first. A fallback is attempted at most once and only when the semantic evidence
quality gate reports `INSUFFICIENT`. A high-confidence weak payoff or weak loop is
valid evidence and does not trigger fallback.

Configuration:

| Variable | Meaning | Default |
| --- | --- | --- |
| `SEMANTIC_PRIMARY_MODEL` | normal semantic VLM | `OPENAI_VLM_MODEL` or `gpt-4o-mini` |
| `SEMANTIC_FALLBACK_MODEL` | stronger escalation VLM | `OPENAI_VLM_MODEL` or `gpt-4o` |
| `SEMANTIC_ROUTING_MODE` | `SINGLE_MODEL` or `PRIMARY_WITH_FALLBACK` | `PRIMARY_WITH_FALLBACK` |
| `SEMANTIC_FALLBACK_ENABLED` | permit one escalation | `true` |
| `POMPOM_SEMANTIC_PROVIDER` | provider boundary selection | `openai` |
| `POMPOM_SEMANTIC_TARGET_FRAMES` | standard frame budget | `8` |
| `POMPOM_SEMANTIC_MAX_FRAMES` | hard selector cap | `14` |
| `SEMANTIC_INPUT_COST_PER_1M` | optional provider input price | unset |
| `SEMANTIC_OUTPUT_COST_PER_1M` | optional provider output price | unset |

## Quality gate

`semantic-evidence-quality-gate-v1` records coverage, opening/character/ending
resolution, beat coverage, payoff/loop resolution, confidence, frame adequacy,
internal consistency, and specific reasons. It measures reliability, not creative
quality. Fallback reasons are observable values such as `SCHEMA_PARTIAL`,
`LOW_COVERAGE`, `PRIMARY_CHARACTER_UNRESOLVED`, `ENDING_UNRESOLVED`, or
`INTERNAL_CONTRADICTION`.

## Frame budget and cache

The standard pass targets eight information-rich frames, capped at fourteen.
Opening anchors, V5 event context, planned beats, and ending anchors remain in the
selection policy. Selection manifests and JPEGs are reused by asset hash, selector
version, and budget. A fallback reuses the extracted selected frames; it does not
run a second FFmpeg/OpenCV extraction.

## Observability

Each semantic result records provider, model, role, reason, frames sent, image
preparation profile, latency, token usage, optional estimated cost, cache status,
quality result, fallback reason, attempts, and final selected role in provenance.
The fields are intentionally provider-neutral even when the adapter is OpenAI.

## Summary and future benchmark

The current repository has structured assessment projections but no separate
semantic LLM summary call in this path. A deterministic template summary should
remain the default when a summary layer is introduced; an optional text-only LLM
summary must be separately cached and must never trigger semantic VLM fallback.

Before changing the production primary model, benchmark a small corpus (Rainy Day,
Broccoli, one strong absurd/growth video, one weak/stock video, and one Opa video)
with the same persisted frames. Compare current versus reduced frame budget first,
then model quality, then routed primary/fallback cost. Do not bulk-analyze legacy
stock until the benchmark and budget guard are complete.

## Rollback and limitations

Set `SEMANTIC_ROUTING_MODE=SINGLE_MODEL` and disable fallback to return to one
configured provider/model. Cost estimates remain unavailable when pricing variables
are unset. The current implementation does not fabricate a price, and it does not
claim savings until a controlled benchmark records both baseline and routed costs.
