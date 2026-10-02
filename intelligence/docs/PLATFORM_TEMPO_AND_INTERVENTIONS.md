# Platform Tempo and Intervention Evidence

Instagram and Facebook are evaluated with different post-publish clocks. These are
descriptive profiles, not universal causal rules.

## Derived metrics

- `instagram_burst_ratio = observed_views_at_or_before_6h / observed_views_at_or_before_24h`
- `facebook_views_after_24h = latest_observed_views - observed_views_at_or_before_24h`
- `facebook_tail_ratio = facebook_views_after_24h / observed_views_at_or_before_24h`

The service never interpolates or invents a checkpoint. A ratio stays `null` when the
required observations are missing or the denominator is zero. Every returned checkpoint
includes its actual measurement timestamp.

Instagram research emphasizes 1h, 3h, 6h, second-wave, and early-burst behavior. Facebook
research emphasizes 24h, 48h, 7d, Reach Further, persistent growth, and long-tail behavior.

## Manual engagement intervention

An intervention is explicit evidence that personal or related accounts liked, commented,
shared, or otherwise stimulated distribution. It is stored as an append-only
`MANUAL_ENGAGEMENT` event with its timestamp, optional before/after view counts, notes, and
an audit event.

Trajectory points at or after the first event are marked `intervened=true`. Research cohort
medians and clean-organic comparisons exclude the affected video/platform trajectory.
Cutoff-safe live predictions can see an intervention only when its timestamp is not after
the prediction cutoff. Pre-publish predictions never receive this feature.

## APIs

- `GET /api/v1/performance/video/{videoId}/platform-profile?platform=facebook`
- `GET /api/v1/research/platform-tempo`
- `POST /api/v1/videos/{videoId}/interventions`
- `GET /api/v1/videos/{videoId}/interventions?platform=facebook`
- `GET /api/v1/performance/video/{videoId}/trajectory?platform=facebook`

The research view reports ratio-eligible sample sizes and the number of intervened
trajectories excluded. A small sample must remain visibly labeled as such.
