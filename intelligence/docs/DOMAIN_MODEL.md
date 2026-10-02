# Domain Model

The aggregate roots are `Video`, `Character`, `Experiment`, `Prediction`, `ImportBatch`, and `ModelVersion`.

- A `Video` points to an immutable original file. `VideoVariant` records derived media and an ordered JSON edit recipe.
- `CreativeAnalysis` is a versioned analysis run. Its one-to-one `CreativeFingerprint` contains feature values, confidence, evidence, and timestamp ranges.
- `VideoCharacter` records participation, role, and optional measured shares. Absence of a measurement is `null`, never zero.
- A `Prediction` is either pre-publish or live. Locking freezes its model, dataset, features, cutoff, payload, and targets. Evaluation creates a separate audit.
- `Experiment` preregisters a hypothesis, treatment, platform, and publish window.
- `ImportBatch` owns append-only source rows. `PerformanceObservation` is normalized and timestamped; derived trajectories are recalculable.
- `ResearchFinding` records an observation with scope and limitations. It is not a causal claim.
- `PlatformContentState` groups append-only `PlatformContentStateObservation` evidence for a video, variant, platform, and state type. Corrections supersede rather than edit evidence.
- `VideoPublication` stores explicit publication timing and nullable off-peak context independently from creative quality.

IDs are UUIDs. Mutable aggregate roots use optimistic versions and audit timestamps. Flexible evidence is JSONB; identity, lifecycle, and relationships remain relational.
