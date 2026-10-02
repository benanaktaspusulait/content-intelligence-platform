# ADR-005: Immutable Locked Predictions

**Status:** Accepted

Publication-time forecasts are evidence records. A PostgreSQL trigger blocks update/delete of locked content and targets. Evaluation writes a separate audit and permits only the lifecycle transition from `LOCKED` to `EVALUATED`.
