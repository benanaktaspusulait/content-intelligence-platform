# Spreadsheet Ingestion Architecture

`pompom import-performance PATH --preview` inspects CSV, TSV, and every usable XLSX sheet. Committing creates an immutable import record, raw rows, normalised observations, match decisions, and a quality report. Exact file hashes are deduplicated; a reused filename with different bytes is a new source version.

Matching order is exact internal video ID, exact path, exact platform content ID, explicit mapping, then title/time suggestions. Suggestions never become matches without sufficient evidence. Unresolved rows remain queryable and can be reconciled later.

The configured account timezone is `Europe/London`. Raw timestamps, timezone assumptions, UTC values, and account-local values are all retained. Unknown timezone remains explicit.

