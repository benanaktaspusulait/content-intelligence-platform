# Data Model V2

The database is append-oriented and provenance-first.

- `creative_fingerprints`: versioned feature snapshots with evidence and confidence.
- `creative_variants`, `experiments`, `experiment_arms`: test identity and assignment.
- `performance_imports`, `raw_import_rows`: immutable source evidence.
- `normalised_performance`: nullable canonical observations linked to source rows.
- `performance_trajectories`: rebuildable derived checkpoint metrics.
- `model_versions`, `dataset_snapshots`: reproducible learning inputs.
- `predictions` and child tables: pre-publish or early-live forecasts.
- `prediction_audits`: forecast-versus-reality evaluation.
- `characters`, `video_characters`: explicit participation and roles.

Raw, normalised, and derived records never share a table. Source rows are not overwritten. Missing metrics remain `NULL`. Derived tables may be rebuilt from normalised evidence.

