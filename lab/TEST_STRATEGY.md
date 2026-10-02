# Test Strategy

Tests cover migration repeatability, source-file deduplication, CSV/XLSX parsing, metric aliasing, nullable metrics, timezone conversion, exact and unresolved matching, cumulative-versus-increment semantics, trajectory rebuilding, prediction locking, leakage cutoffs, calibration, and character shrinkage.

Golden fixtures remain tiny and synthetic. Integration tests use temporary databases and never touch original media. Every regression must preserve the existing Action DNA and Stock Creative Rescue workflows.

