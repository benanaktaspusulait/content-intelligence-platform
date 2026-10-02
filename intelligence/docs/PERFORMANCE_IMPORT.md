# Performance Import

The canonical workflow accepts CSV, TSV, and XLSX in Spring Boot. Files are SHA-256 deduplicated and stored unchanged under `data/imports/raw/`.

The three layers are:

1. Raw: exact source filename and row JSON.
2. Normalized: nullable canonical metrics and timestamps.
3. Derived: velocity, acceleration, thresholds, trajectories, and prediction errors.

Preview uses exact video UUID or a unique exact filename. Fuzzy matches remain unresolved. An operator may explicitly match an unresolved row to a video; that decision updates preview counts and creates an audit event. Commit is blocked while unresolved rows exist. Empty or invalid metric cells remain null. Reimporting the same source hash returns the original batch instead of duplicating observations.

Reach Further is imported only from a compatible explicit status field. It is never inferred from views, reach, or velocity. Missing state-observation time stays unknown.

Audience discovery fields are imported only when they are present in the source export. Supported canonical headings include `non_follower_share`, `us_audience_share`, `country_code`, and `country_percentage`; underscore-free export variants remain compatible. Country percentages are stored as observations linked to the same performance checkpoint. An estimated country count may be derived from reported views and percentage, and is labelled as an estimate.

When both non-follower share and US audience share are reported, the importer records `new_audience_quality_score` with algorithm version `new-audience-quality-v1`:

`0.65 * non_follower_share + 0.35 * min(100, us_audience_share / 20 * 100)`

The score describes discovery profile, not creative quality or follower conversion. It remains unavailable when either component is missing; the system never substitutes a default audience share.

The API is `POST /api/v1/imports/preview`, `GET /api/v1/imports/{id}`, `GET /api/v1/imports/{id}/rows`, `POST /api/v1/imports/{id}/rows/{rowId}/match`, and `POST /api/v1/imports/{id}/commit`.

The latest cutoff-safe discovery profile is available from `GET /api/v1/performance/video/{videoId}/discovery-profile?platform=facebook`. These features are added only to live prediction inputs and remain excluded from pre-publish prediction inputs.
