# Data Quality

Each import reports parsed sheets, row counts, mapped and unmapped columns, matched/unresolved/rejected rows, duplicate files, conflicts, timezone assumptions, missing identifiers, and metric-semantic uncertainty.

Severity levels are `INFO`, `WARNING`, and `ERROR`. Errors prevent affected rows from entering the normalised layer but do not discard raw evidence. A file may commit with warnings; the report makes every assumption visible.
