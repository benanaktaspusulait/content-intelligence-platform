# Angular UI

The Angular 21 application is a responsive operational workstation, not a marketing site. Standalone components provide Overview, Video Library, Video Detail, Predictions, Import Data, Character Lab, and Reach Further Research; remaining routes have explicit evidence-aware empty states.

API calls target `/api/v1` through the development or Nginx proxy. Video and prediction pages adapt canonical backend DTOs. When the API is unavailable, the affected screen shows an explicit error state.

The interface uses compact tables, segmented controls, strong focus states, fixed navigation dimensions, and horizontal table scrolling on narrow screens. No value is represented as observed when the backend returns it as absent.

Video Detail records manual or screenshot-backed Meta state evidence, explicit publication context, and the first-observed timeline marker. Reach Further Research uses medians, distributions, sample sizes, and matched-analysis eligibility rather than winner labeling.

Video Detail also displays the selected platform's audience discovery profile when imported evidence exists: non-follower share, US audience share, follows per thousand views, and the versioned new-audience quality score. Missing components remain visibly unavailable.
## Data integrity

- Production screens never render demo, sample, or fabricated performance records.
- API failures render an explicit error state; they never activate a sample-data fallback.
- Empty persisted datasets render an honest empty state.
- Unknown metrics render as `—`, not zero. Zero is shown only when the persisted count is actually zero.
- Character coverage is computed from imported performance observations joined to assigned videos and creative analyses.
- Canonical character names are metadata, not performance evidence; newly seeded characters therefore begin at `0 / No Data`.
