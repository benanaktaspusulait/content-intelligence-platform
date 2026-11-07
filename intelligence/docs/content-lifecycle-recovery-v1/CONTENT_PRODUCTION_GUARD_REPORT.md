# Content Production Lifecycle Guard Report

Date: 2026-11-02

## Change

A narrow fail-closed guard now runs at the existing `RenderJobQueueService` boundary before a render job is persisted. It requires an exact `(contentId, promptVersionId, promptSha256)` registry match, supported registry schema, and evidence file paths confined to the configured library whose SHA-256 values still match. It verifies the exact source prompt hash, lifecycle, render/publication status, duplicate classification, and candidate review fields. It rejects missing/unknown evidence; published or exact/story-equivalent published content without a separately scoped remake authorization; rendered content pending reuse review; and high-similarity/insufficient-evidence content. A remake authorization must be `REMAKE_ONLY`, human-reviewed, exact-binding scoped, and explicitly supplied in render settings.

Registry: `intelligence/data/workflow/production-lifecycle-registry.json`. Kiko — Runaway Toothbrush is recorded as a historical operator-attested published workflow with local prompt/render/tracker hashes and null publication identifiers/date. The source records and bytes were not changed.

## Tests

Focused Java 21 suite: **24 passed, 0 failed, 0 errors** (9 `ProductionLifecycleGuardTest`, 15 `RenderJobQueueServiceTest`). Coverage includes published candidate, exact duplicate, story-equivalent, same character/different story allowed, rendered-unpublished hold, unknown status, exact remake authorization, new reviewed candidate eligible, prompt/evidence binding failures, and denial before queue persistence.

Full Maven regression: **456 tests, 454 passed, 2 errors, 0 failures, 0 skipped**. Both errors are the existing source-bound admission rejection in `RenderJobIdempotencyPostgresTest`: `secondRequestWithSameKeyDifferentPayloadIsRejectedAfterFirstSucceeds` and `concurrentRequestsWithTheSameIdempotencyKeyProduceExactlyOneJob`. This matches the two known idempotency integration errors recorded by the earlier full-suite report; the current run had no extra errors. The earlier report's aggregate test/pass totals differ (457/445); the current exact Surefire XML aggregate is authoritative for this run.

## Scope limitation

The guard is a hard stop when the exact lifecycle record is absent, malformed, unresolved, or not eligible. It does not autonomously infer semantic story equivalence from arbitrary prompt prose; the registry's reviewed duplicate classification must be populated from existing evidence/review. Until lifecycle records cover a candidate, the guard blocks it. This is deliberate fail-closed behavior and not a claim that every historical story has been semantically indexed.

Provider calls: 0. Render calls: 0.
