# Short-Form Retention Assessment

The ML service exposes `POST /v1/analysis/retention` for a deterministic, evidence-based
assessment of short-form kids animation. It is separate from `sampled-visual-motion-v3` and
does not use views, likes, follows, reach, or any platform outcome.

The request supplies sampled storyboard measurements, timestamped transcript segments, audio
silence gaps, and the existing motion components. The response is strict JSON with the eight
component scores requested by the short-form retention rubric, the weighted `final_score`, a
coarse heuristic prediction band, and two evidence-based fixes.

The analyzer does not claim to detect faces, eye-line, text, punchlines, or audio directly from
pixels. Those are input measurements. Missing evidence is reported conservatively rather than
invented. `motion_score` uses the supplied four motion components and applies the requested
10-point penalty when motion density is exactly `1.0`, because continuous activity provides no
measured stillness for a punchline.

The prediction bands are descriptive heuristics, not platform forecasts. A high score is not a
publication decision and is not calibrated from platform performance.
