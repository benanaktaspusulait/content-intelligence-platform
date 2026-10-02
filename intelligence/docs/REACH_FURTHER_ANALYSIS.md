# Reach Further Analysis

## Status Of Knowledge

`META_REACH_FURTHER` is an observed Meta user-interface state. Its official internal algorithmic meaning is not known and is not assumed by this system.

Known:

- the state was explicitly observed, when evidence includes it;
- when the state was first and last observed, when timestamps are available;
- the video's measured performance before and after that evidence time;
- whether a screenshot was manually verified.

Derived:

- video age at first observation;
- early, mid, late, or unknown-timing cohort;
- view/reach deltas, velocity, acceleration, trajectory, and descriptive performance band;
- observational comparisons with videos that have no recorded Reach Further evidence.

Not known:

- the actual activation time when evidence was first collected later;
- Meta's internal eligibility or distribution logic;
- whether the state caused a performance or country-mix change;
- whether a video will become a winner or viral.

Allowed language: "After Reach Further was first observed, three-hour view velocity increased."

Forbidden language: "Reach Further caused Meta to push the video."

## Evidence Model

`platform_content_states` identifies a video, optional variant, platform, and state type. `platform_content_state_observations` is the append-only evidence timeline. An observation contains value, optional observed timestamp, source, confidence, notes, evidence file reference, OCR output, verification, recorder, and an optional correction link.

Updates and deletes are blocked by a PostgreSQL trigger. A correction is a new observation referencing the superseded row and creates an audit event. OCR is stored as supporting text and never sets `manually_verified` by itself.

Manual and screenshot observations require `observed_at`. CSV/API evidence may have unknown timing; the system does not replace a missing time with publication or import time.

## Publication Context

`video_publications` stores the explicit publication timestamp, timezone, and nullable `off_peak_publish`. When off-peak is explicitly true, the descriptive context label is `LOW-SIGNAL / OFF-PEAK TEST`. This separates audience availability from creative assessment. It does not excuse weak performance or predict later recovery.

## Cohorts

Thresholds are configuration properties:

- `REACH_FURTHER_EARLY`: video age at first observation is at most 3 hours;
- `REACH_FURTHER_MID`: more than 3 and at most 12 hours;
- `REACH_FURTHER_LATE`: more than 12 hours;
- `UNKNOWN_TIMING`: first observation or publication time is unavailable.

The 3h and 12h boundaries are configured as `pompom.reach-further-early-hours` and `pompom.reach-further-mid-hours`.

## Performance Windows

The summary API reports the latest known cumulative checkpoint at or before first observation and the first checkpoint at or after 1h, 3h, 6h, 12h, 24h, 48h, and 7d. Missing checkpoints stay null. No interpolation is presented as an observation.

Velocity before the state uses available checkpoints in the preceding three-hour window. Velocity after uses the following three-hour window. Acceleration is the descriptive difference between those velocities.

## Prediction Leakage Guard

Reach Further is forbidden in `PRE_PUBLISH`. The live-feature endpoint returns no features and `PRE_PUBLISH_LEAKAGE_GUARD` for that request type.

For `LIVE`, a Reach Further feature is eligible only if `firstObservedAt <= knowledgeCutoff`. A later observation is unavailable to that forecast and is not backfilled. Live predictions preserve the knowledge cutoff and include a non-causal uncertainty notice.

The Python ablation contract compares model A without Reach Further and model B with it under temporal walk-forward validation. It returns `INSUFFICIENT_SAMPLE` below 30 rows and never fabricates evaluation metrics. The feature should be retained only if it improves out-of-time error, band accuracy, or calibration.

## Import Rule

CSV/Excel import creates a state observation only from an explicit field named `reach_further`, `reachfurther`, or `meta_reach_further`. Accepted explicit values map to ACTIVE, INACTIVE, or UNKNOWN. Views, reach, velocity, likes, and thresholds never infer the state.

An explicit `reach_further_observed_at` may supply timing. Without it, timing remains unknown.

## API

- `POST /api/v1/videos/{videoId}/platform-states`
- `POST /api/v1/videos/{videoId}/platform-states/reach-further/screenshot`
- `GET /api/v1/videos/{videoId}/platform-states`
- `GET /api/v1/videos/{videoId}/platform-states/reach-further`
- `GET /api/v1/videos/{videoId}/platform-states/live-features`
- `POST /api/v1/videos/{videoId}/publication-context`
- `GET /api/v1/research/reach-further`
- `GET /api/v1/research/reach-further/comparison`
- `POST /api/v1/predictions/live`

## UI

Video Detail provides manual status entry, screenshot evidence, publication context, an evidence ledger, and a first-observed marker on the performance timeline. The research page reports medians, distributions, sample sizes, matched-pair eligibility, and individual cases. It does not display a winner badge for Reach Further.
