# Database

SQLite migrations live under `migrations/`. Tables separate media identity, analysis runs,
scores, timeline events, issues, fix plans, edits, human reviews, tags, and observed platform
performance. Performance never changes creative scores. Human overrides preserve the AI
result and appear separately.

`rescue_runs`, `rescue_reviews`, and `rescue_edits` keep the second creative-research mode
separate. Approximate performance observations store provenance and an explicit approximation
flag.

Back up `.lab_data/library.sqlite3` and `.lab_data/output/` together. SQLite uses WAL mode;
stop the dashboard before copying if a strictly point-in-time backup is required.
