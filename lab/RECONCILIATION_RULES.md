# Reconciliation Rules

1. Preserve every raw row and source hash.
2. Prefer stable platform IDs over titles.
3. Never silently replace a non-null observation with a conflicting value.
4. Identical values from overlapping exports are corroboration, not new increments.
5. Cumulative values use the latest measurement timestamp; daily increments aggregate by local date.
6. Snapshot rows remain separate unless their timestamp and metric semantics are compatible.
7. Paid activity and manual interventions are recorded and excluded from organic comparisons by default.
8. Ambiguity creates an unresolved item or conflict requiring a human decision.

