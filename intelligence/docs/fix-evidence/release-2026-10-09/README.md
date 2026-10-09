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
