# ADR-003: Local Filesystem Media

**Status:** Accepted

Original video and derived artifacts remain beneath a configured local data root. PostgreSQL stores relative paths and hashes. This avoids database bloat and cloud dependence; backups must include both stores.
