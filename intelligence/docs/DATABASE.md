# Database

PostgreSQL 17 is the system of record. Flyway owns schema changes; Hibernate runs in `validate` mode.

The initial migration creates relational tables for videos, variants, characters, fingerprints, predictions, experiments, imports, observations, countries, jobs, audits, model versions, research findings, interventions, and audit events. JSONB is limited to evidence, flexible model payloads, raw imported rows, and metrics.

Important invariants:

- video content hashes and paths are unique;
- only one primary character may be assigned to a video;
- only one champion exists per platform/model type;
- a locked prediction and its targets cannot be changed or deleted;
- `LOCKED -> EVALUATED` is the sole allowed locked-row transition;
- each source row produces at most one normalized observation;
- every checkpoint keeps its measurement timestamp.
- platform-state observations are append-only; corrections create a linked observation and audit event;
- Reach Further first-seen time is never substituted when evidence timing is unknown;
- publication context keeps explicit timezone and nullable off-peak status separate from creative quality.
- performance, country, and derived metric observations are append-only after migration V5;
- discovery scores retain their algorithm version and source components;
- missing audience shares stay null and cannot silently become zero.

Migration V2 adds `video_publications`, `platform_content_states`, and `platform_content_state_observations`. Screenshot evidence stays on the local filesystem; PostgreSQL stores its relative reference and verification state.

Create a new `Vn__description.sql` migration after a schema has been used. Never edit a deployed migration.
# Platform data purity

`intervention_events` is append-only from migration V3. Manual engagement interventions
carry a platform and event timestamp; optional before/after view counts and notes are kept
in `details`. Every creation also writes an `audit_events` row. Corrections are represented
as new evidence rather than in-place mutation.

Migration V5 adds source/version metadata, raw payload retention, quality labels, country
observation timestamps, and versioned derived performance metrics. The database prevents
updates and deletes on normalized performance observations, country observations, and
derived metrics; corrections must arrive as newer observations.
