# Post-Render Creative Assessment Plan

## Inventory

The motion analyzer is `sampled-visual-motion-v3`. It measures sampled grayscale visual change,
opening/overall/ending motion, interval density, low-motion intervals, endpoint pixel similarity,
decode coverage, and measurement confidence. Its motion score remains motion-only and does not
claim story, character intent, humor, payoff quality, semantic looping, or audience response.

The ML prompt parser already has VideoPlanIR-style beats, timeline ranges, `finalPayoff`, mechanic,
characters, object, and opening/ending structure. Render jobs persist an immutable prompt snapshot
and validation lineage. A complete structured VideoPlanIR snapshot is not currently present in the
render-service validation DTO, so payoff resolution must remain conservative until that lineage is
made available.

The render service already owns immutable `RenderEvidenceIR`, the YAML post-render rule engine,
human review, rule-result persistence, and versioned evaluation records. `render-evidence-v2` now
adds a separately versioned rendered-creative evidence layer. Assessment snapshots are stored in
`post_render_assessments` and never overwrite prior evaluations.

## Evidence design

The motion service now persists a duration-aware local temporal profile, timestamped activity-drop
candidates, motion variation, and presentation measurements. These are descriptive evidence, not a
creative score. When a single explicit timestamped payoff marker can be resolved from the immutable
prompt snapshot, the render service derives bounded pre/payoff/post motion windows, contrast
direction/magnitude, and an intentional-hold candidate. A low-motion interval alone is never
classified as an intentional hold.

Opening causal legibility, semantic loop continuity, and primary-character identity continuity are
represented as independent evidence fields and remain `NOT_EVALUATED` until a versioned semantic
analyzer supplies reliable evidence. First/last visual similarity remains endpoint evidence only.

## Rule and grade flow

`measurement -> immutable evidence -> YAML rule results -> assessment aggregator -> insights`.

The rules include payoff visual emphasis and unmapped visual idle as review-oriented warnings, plus
independent opening, semantic-loop, and character-continuity rule slots. They do not penalize missing
face, text, or a fixed hold duration. The grade is derived from rule outcomes and evidence coverage,
never from averaging metric values or imported platform performance.

`A` is a clean, well-covered result; `B` has minor issues; `C` has meaningful review-oriented
warnings; `D` has major unresolved issues; `F` has a critical blocker; `INCOMPLETE` means important
evidence could not be evaluated. `NOT_APPLICABLE` is not counted as missing coverage.

## UI plan

Video Detail and Render Dashboard should lead with a human-readable assessment: grade, coverage,
verdict, strengths, concerns, insights, recommendation, and evidence limitations. Raw motion,
sampling, temporal segments, payoff windows, and analyzer versions remain available under Technical
Details. Observed performance remains a separate panel and can never rewrite a historical grade.

## Versioning and tests

Persist `renderedCreativeEvidenceVersion`, `postRenderRulesetVersion`, `assessmentAggregatorVersion`,
and motion analyzer version independently. Add duration-aware temporal-profile tests, payoff contrast
tests, hold-vs-idle tests, grade/coverage tests, and performance-separation tests as each evidence
source becomes available. No external platform integration is required for this assessment layer.
