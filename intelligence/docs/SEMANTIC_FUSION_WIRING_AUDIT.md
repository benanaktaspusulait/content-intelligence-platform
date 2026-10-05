# Semantic Evidence Fusion Wiring Audit

This audit traces the current V5/semantic path before the fusion fix. The source
of truth is the persisted `creative_analyses.raw_result` JSONB row selected by
`VideoController` for the requested analysis version.

| Field | Deterministic source | Semantic source | Canonical evaluator | Persisted output | API field | UI field | Current bug |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Opening Hook | V5 `temporalProfile.hook` | `semanticVideoEvidence.opening` | V5 motion-only hook | `temporalProfile.hook` | `temporalProfile` | `v5HookSummary()` | Semantic readability was not consumed; reason said it was unavailable. |
| Payoff | V5 rebound/trend | `semanticVideoEvidence.payoff` | V5 motion-only payoff object | `temporalProfile.payoff` | `temporalProfile` | `v5ReboundSummary()` | Main card was named “Payoff rebound”; semantic payoff was only a peer detail. |
| Loop | V5 first/last similarity | `semanticVideoEvidence.loop` | V5 visual loop object | `temporalProfile.loop` | `temporalProfile` | `v5LoopSummary()` | UI hard-coded `semantic unknown`; backend readiness read only V5 loop. |
| Temporal emphasis | V5 local dips/recovery | semantic beat timestamps | V5 temporal trend | `temporalProfile.temporalEmphasis` | `temporalProfile` | `v5HoldSummary()` | No semantic beat/event join existed, so contextual dips stayed unevaluated. |
| Plan/render fidelity | V5 default `NOT_AVAILABLE` | none directly | no shared fusion evaluator | `temporalProfile.planRenderFidelity` | `temporalProfile` | `v4Dimension()` / `v5CoverageReason()` | Prompt/plan lineage was not connected to the V5 result. |
| Readiness coverage | V5 criteria | semantic fields not included | `PlatformCreativeReadinessService` | computed on request | `/platform-readiness` | platform strip | Criteria read raw V5 fields and treated semantic availability as unknown. |
| Asset grade | render-service post-render rules | semantic evidence available in intelligence DB | render-service post-render aggregator | post-render tables | post-render API | render dashboard | Separate render-service flow; ordinary video detail had no fused asset read model. |
| Platform lens | V5 temporal profile | semantic evidence indirect | `PlatformCreativeReadinessService` | response projection | `/platform-readiness` | platform strip | Platform lens read raw temporal evidence rather than canonical fused dimensions. |

## Ordering finding

V5 and semantic evidence are produced in the same ML response and persisted
together by `VideoService.persistCreativeAnalysis`. Therefore fusion can be a
local deterministic step after semantic completion; it must not call the VLM
again. Existing historical rows require reanalysis or a local backfill before
they contain the new fused projection.
