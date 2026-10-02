# ADR-002: PostgreSQL Is Authoritative

**Status:** Accepted

PostgreSQL stores domain state, raw row metadata, observations, jobs, and immutable prediction records. JSONB is used only for evidence and versioned flexible payloads. Database constraints defend invariants even when callers bypass Java.
