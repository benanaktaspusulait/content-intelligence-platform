# Post-Render Creative Assessment

## Boundary

`sampled-visual-motion-v3` is a measurement analyzer. It reports sampled visual change and decode
quality; it does not evaluate story quality, character intent, humor, audience retention, or causal
relationships. The post-render creative layer interprets immutable measured evidence through the
versioned rule engine. It does not create an arbitrary weighted creative score.

## Local temporal evidence

The analyzer persists duration-aware temporal segments with average motion, motion density,
relative-to-previous, and relative-to-overall values. Activity-drop candidates retain start/end
timestamps, magnitude, surrounding activity, and an initial `UNMAPPED_DROP` classification. A drop
is not automatically bad; beat lineage can later classify it as a planned reaction, payoff, or
transition.

## Payoff and hold evidence

Payoff timing is resolved only from explicit timestamped prompt lineage currently available in the
immutable render snapshot. Missing or conflicting timing is `NOT_AVAILABLE` or `AMBIGUOUS`.
Resolved windows receive bounded pre/payoff/post motion measurements. Contrast can be `REDUCTION`,
`INCREASE`, `NONE`, or `UNKNOWN`; neither increase nor reduction is inherently good. An intentional
hold is a candidate supported by payoff alignment and reduced motion, not a synonym for low motion or
technical decode freeze. No fixed 0.6-second rule is applied.

## Rules

Post-render rules include technical integrity, visual visibility, payoff emphasis, unmapped visual
idle, opening causal legibility, semantic loop continuity, and primary character continuity. Missing
semantic evidence stays unknown or not evaluated. Endpoint pixel similarity is not semantic loop
continuity. Text overlay and direct camera gaze are evidence/experiment inputs, not mandatory rules.

## Human-readable insight contract

Each assessment explains what was observed, what it may mean, whether attention is needed, what to
try next, evidence status, and what the evidence cannot claim. Recommendations use experiment
language such as “test”, “try”, and “consider”; they do not promise retention or view uplift.

## Grade and coverage

`post-render-assessment-v1` derives `A`, `B`, `C`, `D`, `F`, or `INCOMPLETE` from rule results,
severity, review state, and applicable evidence coverage. It does not average motion, brightness,
loop similarity, text, or face values. `NOT_APPLICABLE` is excluded from missing coverage, while
`UNKNOWN`, `NOT_EVALUATED`, and `SERVICE_ERROR` remain distinguishable.

## Performance separation

Observed platform performance can be displayed beside the assessment when available. Views, watch
time, completion, retention, and follower data never change a historical post-render grade. Any
future relationship between a creative insight and performance is a governed learning hypothesis,
not an automatic rule.

## Known limitations

The current render boundary does not yet receive the full persisted VideoPlanIR or a semantic vision
analyzer for opening causality, semantic looping, or character identity. Those fields therefore stay
explicitly unavailable rather than being fabricated from motion or keywords.
