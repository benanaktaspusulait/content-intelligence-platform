# Data Reconciliation

Normalisation is idempotent per source row. Overlapping exports are reconciled by platform, content/video identity, measurement time/date, semantic type, and metric name. Conflicting non-null values generate a conflict record; no winner is silently selected.

Manual resolutions record actor, timestamp, decision, and note. Rebuilding derived data reads resolved canonical observations and leaves raw evidence untouched.

