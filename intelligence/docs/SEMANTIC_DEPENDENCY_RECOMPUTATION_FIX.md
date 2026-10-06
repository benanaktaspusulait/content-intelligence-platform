# Semantic Dependency Recomputation Fix

## What changed

- Added a shared backend availability predicate for `COMPLETED`, `PARTIAL`, and `CACHE_HIT`.
- Removed the stale short-circuit that trusted any existing canonical snapshot.
- Recompute canonical assessments when persisted semantic evidence is available and only save
  when the derived object actually changes.
- Added a stable semantic evidence identity to the canonical result for provenance and future
  snapshot compatibility checks.
- Canonical payoff now preserves semantic `COMPLETED` evidence even when deterministic motion
  rebound is `NOT_ESTABLISHED`; the two signals are shown separately.
- Canonical loop now preserves semantic `CONSISTENT` evidence while combining it with visual
  endpoint strength.
- Coverage now measures evidence availability, not whether an available result is labelled
  strong. Weak or moderate evidence remains visible as evidence.

## Runtime verification

The benchmark was verified through the deployed backend without re-running analysis:

- semantic status: `CACHE_HIT`
- semantic provider calls: `0`
- payoff: `STRONG`, semantic status `COMPLETED`, motion rebound `NOT_ESTABLISHED`
- loop: `MODERATE`, semantic evidence `CONSISTENT`, evidence status `AVAILABLE`
- canonical coverage: `100%`, missing: none
- Facebook, Instagram, TikTok, and YouTube readiness: all consumed `semantic-fusion-v1` with
  `100%` evidence coverage

No new VLM call, prompt change, frame-selection change, platform policy change, or prediction
logic was added.
