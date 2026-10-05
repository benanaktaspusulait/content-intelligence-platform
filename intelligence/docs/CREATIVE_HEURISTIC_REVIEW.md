# Creative Heuristic Review

Updated 2026-10-05. This document records how the eight proposed short-video heuristics map to the platform. The platform keeps measurement, creative policy, post-render QA, observed performance, and learning separate.

## Classification

| Proposal | Classification | Current implementation | Boundary |
|---|---|---|---|
| `HOOK_FACE_1.5S` | MODIFIED | `HOOK_002`, `HOOK_004`, and `INSTANT_VISUAL_ABSURDITY_GATE` evaluate early visual anomaly and causal legibility. | The primary subject/object relationship must read early when needed; direct camera gaze is never required. |
| `TEXT_HOOK_2S` | EXPERIMENT_ONLY | No production rule. The retention endpoint may measure supplied text evidence, but it is not render policy. | Text is off by default for the visual-first Pompom growth format. Any text variant must be evaluated through observed experiment metrics. |
| `PUNCHLINE_STILLNESS` | MODIFIED | Existing payoff, escalation, and momentum rules cover structure. A brief contrast may be represented as optional evidence when reliable timing exists. | No fixed motion range, exact hold duration, or blocker is used. |
| `EYE_LINE` | REJECTED AS FIXED POLICY | No eye-line ratio rule exists. | Gaze is a content-level choice and may support object/cause readability without camera contact. |
| `SILENCE_TRAP` | MODIFIED TO `VISUAL_IDLE_TRAP` | `MOTION_001` and `CONTINUOUS_ACTION_MOMENTUM` inspect planned progression, passive gaps, reactions, consequences, and aftermath. | Audio silence alone never fails a video; low pixel motion alone is not creative failure. |
| `BRIGHTNESS_KIDS` | MODIFIED TO VISIBILITY/EXPOSURE PROFILE | Post-render sampled evidence carries dark-frame candidates and the `EXPECTED_VISIBILITY_PROFILE` review rule. | The rule only requests human review when every decoded sample is a dark candidate. It does not declare a universal brightness or saturation target. |
| `LOOP_SCORE` | REJECTED AS COMPOSITE | `firstLastVisualSimilarity` remains independent sampled evidence; pre-render `PAYOFF_006` uses explicit structural loop claims. | Transcript words such as “again” or “tomorrow” never add loop points. |
| `CHARACTER_PERSISTENCE` | MODIFIED TO CHARACTER CONTINUITY | `CONSISTENCY_002` and post-render identity evidence handle continuity when real evidence exists. | No arbitrary 80% frame-presence threshold. Missing semantic evidence stays unknown/reviewable. |

## Layer rules

### Pre-render creative validation

The active immutable pre-render ruleset is `RULESET_1.5.yaml`. It already contains the useful structural gates: consequence capacity, static-state dominance, action/cycle repetition, opening anomaly/problem legibility, continuous action momentum, and the scoped single-agent object mechanic for `social_reel`.

These rules operate on `VideoPlanIR`. They do not consume views, likes, retention, or platform distribution. Existing rules are intentionally retained instead of adding duplicate aliases for the same concepts.

### Post-render evidence and QA

The post-render ruleset is independently versioned as `POST_RENDER_RULESET_1.1`. The visual analyzer remains measurement-only. It reports motion, low-motion intervals, first/last visual similarity, and dark-frame candidates. Low motion remains informational. A full dark sampled profile produces `HUMAN_REVIEW`, not an automatic creative failure, because night scenes and intentional dark compositions need context.

### Experiment-only retention endpoint

`POST /v1/analysis/retention` is a supplied-evidence experiment endpoint. It is not the pre-render rule engine, not post-render QA, and not a platform-performance predictor. Its component outputs must not authorize a render or replace rule outcomes. Text, camera gaze, eye-line distributions, audio gaps, and any retention relationship remain hypotheses until observed performance supports promotion through governance.

### Observed performance and learning

Platform metrics remain evidence about published content, not proof that a render passed creative QA. They may be used by the existing feedback and rule-candidate workflow, with human review and a future immutable ruleset required before a hypothesis becomes policy.

## Explicit non-rules

- No universal “face + text + stillness + motion” creative score.
- No expected view-range mapping from a heuristic score.
- No direct-camera-gaze requirement.
- No text-overlay requirement.
- No silence-duration failure rule.
- No fixed brightness/saturation target for all preschool scenes.
- No semantic loop bonus from CTA/sequel words.
- No arbitrary character-presence percentage.
