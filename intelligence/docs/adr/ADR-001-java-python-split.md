# ADR-001: Java Workflow, Python Computation

**Status:** Accepted

Spring Boot owns transactions, lifecycle, imports, experiments, locking, and audit. FastAPI owns video, statistics, and ML computation. This keeps business invariants in the primary Java system while preserving Python's media/ML ecosystem.
