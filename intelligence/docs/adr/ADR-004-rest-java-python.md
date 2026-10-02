# ADR-004: Versioned REST Between Java and Python

**Status:** Accepted

Synchronous versioned JSON over local REST is sufficient for initial throughput and is easy to diagnose. PostgreSQL job state provides retry boundaries. Messaging infrastructure is deferred until measured load requires it.
