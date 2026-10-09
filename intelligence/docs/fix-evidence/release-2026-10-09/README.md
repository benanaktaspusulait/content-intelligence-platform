# Continued daily-use acceptance — 2026-10-09

Primary master checkout; no worktree, manual commit, production mutation, paid call, generated media or training in this batch. Backend 8086, current-source Angular 4216, ML fixture 8016; disposable database pompom_release_20261009. Render 8087 is isolated, worker off and OpenArt disabled/mock. The existing audit remains unchanged.

## Repair/browser correction

J2 now automatically advances the existing durable repair service for at most two independently reviewed attempts. It stops on plateau and retains the earlier best candidate. Original and best findings are fetched through read endpoints and shown together. Cancellation, source change and component destruction invalidate late callbacks.

Browser acceptance discovered that Angular Router did not see repairSessionId added by history.replaceState, so merging query parameters on acceptance dropped the session. The accepted-version event now carries the session ID explicitly to route navigation. Reload restores version 2 and the ACCEPTED session, including original/best reviews. Versions 1 (CUT), 2 (Hold.), and 3 (Wait. plateau) remain stored. Only two fixture MINIMAL_REPAIR calls were made. No refresh initiated another provider call or render.

Evidence: j2-session.json, j2-calls.json, j2-versions.txt, j2-reopened.txt and j2-reopened.png. LOCAL_MOCK provider/critic grades are synthetic contract evidence. Source-span/protected-intent patch verification uses the actual local ML functions. Fixture PASS is not a judgement about a real video and does not establish live render authorization.

## Story/builder

Browser idea → STORY → choose and edit → BUILD_PROMPT → use draft → save version 4 → reload completed. b11-calls.json records the edited story and exact sourceStoryRecordId. b11-reopened.txt shows the persisted builder/model/story provenance and NOT_VALIDATED label. b11-version.json records immutable prompt bytes. A short initial fixture was correctly prevented from saving by the existing 100-character requirement; the final valid fixture exceeds it.

## Fresh checks

75 frontend tests across 15 files pass, including automatic progression/cancellation/destroy and explicit accepted-session route coverage. Production build passes with existing initial/style warning thresholds. Logs are frontend-tests.log and frontend-build.log. No backend source changed; the isolated backend runs a copy of the deployed aligned jar. Backend migrations V1–V55 ran only against disposable data.

The render runtime initially found pgcrypto in public because the disposable backend was initialized first, whereas render V1 expects the extension in creative_render. Only this disposable database's extension was moved to creative_render; render migrations then completed and the service started. No historical migration or production extension was changed. This initialization-order limitation remains recorded for a future fresh-install fix; it is not evidence that the production render service failed.

## Honest model registry

Read-only real backend registry returns [] (`b13-models-api.json`). Browser capture shows 0 versions, no model registered and explicit cold-start (`b13-models-ui.txt`, visually inspected `b13-models.png`). No training/promotion request was sent.

## Remaining acceptance

The single ledger POMPOM_FIX_PROGRESS.md lists remaining combined J5 queue/browser admission, full lesson/recovery browser proof and wider B14 live acceptance. Earlier service tests and paid text checks remain separate evidence. B17 actual fitting remains deferred. This new frontend has not been deployed to production.


## J5 queue acceptance and real persistence fixes

Real browser immutable handoff for content 2/prompt 6 → authorized source-bound queue → saved job `1c08d6e8-2929-4e6f-9630-573588901536` → reload → resubmit same handoff → one job, one attempt and one ESTIMATE reservation. Parameters retain exact parent video/hash, null original variant, 6-second duration, Mini API model, 9:16, reviewed frame and workflow binding. Worker disabled; provider job ID and actual spend remain absent. This demonstrates local queue acceptance, not generated-media acceptance.

The actual PostgreSQL run exposed missing JSON JDBC binding on RenderJob.creativeContractSnapshot, RenderJob.compiledGenerationConstraints and OpenArtCreditLog.operationMetadata. These fields now use the same Hibernate JSON binding as openartParams. No SQL migration or historical data rewriting is needed. A fresh PostgreSQL 17 Testcontainers test migrates the schema, persists/reloads nested contract and constraint objects, queries their JSON fields and persists both non-null and null credit metadata. Nineteen focused queue/admission/persistence tests passed. Fresh packaged source ran on isolated 8087 after the fix. Initial failed attempts rolled back all job/attempt/credit rows.

Evidence: j5-canonical-evidence.json, j5-source.json, j5-review.json, j5-handoff.json, j5-handoff-ui.txt, j5-persisted-lineage.txt, j5-queue.json, j5-replay-queue.json, j5-reopened-ui.txt. Seed-j5.py creates synthetic grade/provenance fixtures only in the named disposable DB. Actual local copied media/frame bytes are hashed. The original and descendant prompt lineage are real persisted data. Negative pending authorization UI previously created zero rows.

## B08 browser consumption and revocation

Existing accepted repair session → PROMPT_FIX lesson candidate → explicit fixture review/approval in browser → later BUILD_PROMPT request with exact profile/generator/model version/duration/settings → backend resolves approved lesson and sends it in provider context → browser revocation → same later request has no lesson. Actual captured context lesson counts are [1, 0], and the persisted latest learning-review is REVOKED. Counterexamples and typed source repair evidence remain recorded. This is synthetic outcome evidence, not audience or causal proof. Refresh/history remains read-only.

Evidence: b08-approved-ui.txt, b08-consumed-ui.txt, b08-reviewed.json, b08-calls-approved.json, b08-calls-revoked.json, b08-revoked-records.json, b08-revoked-request-ui.txt.

## B14 controlled live procedure (prepared, not executed)

Use the actual request path and immutable source IDs from the locally accepted role/repair/queue contracts. Before any new live test, record explicit authorized roles/media scope, maximum calls, per-request ceiling, total budget and stop policy. Keep publishing off. Use a copied fixture and disposable content history. Separate text roles, independent critic/vision and generated-media checks; earlier text success does not authorize or verify the others.

Record requested model/duration/aspect/frame hashes/reference IDs, the normalized adapter command/request, actual returned model/usage/job ID, output file hash and measured duration. Verify final artifacts against the approved source intent with an independent reviewer. Unsupported settings, stale binding, timeout or uncertain submission must stop without fallback or automatic paid retry. Reopening must fetch saved results without a new call. Do not mark capability cache, a mock CLI command, a recommendation or a prompt change as live generation proof. Mini remains the user preference; full 2.0 and 2.5 choices still require supported request contracts and source justification. B17 fitting remains deferred.
