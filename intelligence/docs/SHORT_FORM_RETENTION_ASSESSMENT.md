# Short-Form Retention Assessment

The ML service exposes `POST /v1/analysis/retention` for a deterministic, evidence-based
assessment of short-form kids animation. It is separate from `sampled-visual-motion-v3` and
does not use views, likes, follows, reach, or any platform outcome.

The request supplies sampled storyboard measurements, timestamped transcript segments, audio
silence gaps, and the existing motion components. The response is strict JSON containing
independent descriptive evidence plus `assessment_scope: EXPERIMENT_ONLY` and
`policy_decision: NOT_APPLICABLE`.

The analyzer does not claim to detect faces, eye-line, text, punchlines, or audio directly from
pixels. Those are input measurements. Missing evidence is reported conservatively rather than
invented. It does not calculate a combined creative score, platform view prediction, or
publication decision. First/last visual similarity, transcript sequel words, silence gaps,
brightness, text, and gaze are returned as independent experiment evidence only.

This endpoint must not feed render authorization or post-render QA. Any experiment hypothesis
must be evaluated with observed performance metrics and promoted only through the governed rule
evolution workflow.
