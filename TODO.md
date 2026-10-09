# Pompom Meta Integration TODO

Scope: Meta integration only. Publishing remains disabled until the safety gate is implemented and explicitly enabled later. Do not modify OpenArt, prompt scoring, Meta publishing, or unrelated generated work while executing a Meta task unless the task explicitly requires it.

Publisher migration is now an explicitly authorized companion workstream. It must not modify Family calibration work and must preserve the Meta read/comment scope boundaries. The current publisher inventory and migration plan are recorded in [`docs/superpowers/plans/2026-10-07-publisher-microservices-java-migration-plan.md`](docs/superpowers/plans/2026-10-07-publisher-microservices-java-migration-plan.md).

## Current work list

- [x] Audit `publisher/` Python packages, Java in-process publishers, Compose topology, and bypass/duplicate-ledger risks.
- [x] Confirm the three target publisher services: Meta (Facebook + Instagram), TikTok, and YouTube.
- [x] Record the migration architecture and Python-removal gates in the publisher migration plan.
- [x] Keep the current Python publisher tree intact until Java parity, cutover, and reference-removal gates pass.
- [x] Define the provider-neutral Java publisher contract and normalized request/result/error model.
- [x] Create the Meta publisher microservice for Facebook Page and Instagram Professional/Reels protocols.
- [x] Create the TikTok publisher microservice with chunked upload and status reconciliation.
- [x] Create the YouTube publisher microservice with OAuth refresh and resumable upload.
- [x] Replace render-service in-process publisher bean dispatch with internal publisher-service clients.
- [x] Add Docker/Compose service definitions, internal routing, health checks, credential configuration, and no-browser-secret boundaries.
- [x] Add Java provider contract/parity tests before any Python deletion.
- [x] Verify no runtime or documentation path invokes Python publisher code.
- [x] Remove `publisher/` Python code, SQLite ledgers, Python dependencies, and stale integration docs only after all removal gates pass.
- [x] Re-run backend/render/frontend/package/release checks and update `META_INTEGRATION_READINESS.md`.

## Current baseline

- [x] Backend read-only Meta connection check: `/api/v1/meta/connection`
- [x] Facebook Page content read: `/api/v1/meta/page/content`
- [x] Instagram Reel list/detail/analytics: `/api/v1/meta/instagram/reels*`
- [x] Read-only OAuth entry/callback: `/api/v1/meta/oauth/start`, `/api/v1/meta/oauth/callback`
- [x] Instagram analytics snapshot persistence with exact local matching
- [x] Angular Meta connection, Reel list, and Reel analytics screens
- [ ] Full Meta production safety: current render-service publication paths can still reach Facebook/Instagram publishers
- [ ] Unified durable Meta connection/token lifecycle
- [ ] Facebook read-only insights
- [ ] Comments/messages/replies

## Phase 0 — Fail-closed publishing safety (P0)

- [x] Add server-side `META_PUBLISH_ENABLED=false` default in `creative-render-service`.
- [x] Reject Facebook/Instagram in `PublicationController` queue requests while disabled.
- [x] Reject Facebook/Instagram in `ScheduledPublicationController` while disabled.
- [x] Add the same guard in `PublicationService` so non-HTTP callers cannot bypass it.
- [x] Add the same guard in `PublicationAttemptOrchestrator`/`PublicationWorker` so pre-existing queued jobs cannot publish.
- [x] Keep TikTok/YouTube behavior unchanged unless explicitly configured.
- [x] Hide Facebook/Instagram queue/schedule controls in `frontend/src/app/pages/operations.page.ts` while the provider is disabled.
- [x] Add backend guard regression coverage for disabled Meta platforms.
- [x] Add frontend test proving disabled Meta platforms cannot be submitted.
- [ ] Add an operational status field showing `META_PUBLISH_DISABLED`.

## Phase 1 — OAuth and connection lifecycle

- [ ] Choose one canonical Meta connection owner: backend read-only Meta connection; do not silently reuse render-service write credentials.
- [ ] Persist backend read-only OAuth state/tokens securely instead of process-local `MetaOAuthTokenStore`.
- [ ] Store token expiry, refresh state, scopes, user identity, Page ID, and Instagram account ID.
- [ ] Add refresh-before-expiry behavior and explicit revoke/disconnect endpoint.
- [ ] Add connection status for `CONNECTED`, `DEGRADED`, `EXPIRED`, `REVOKED`, and `NOT_CONFIGURED`.
- [ ] Remove write scopes from the read-only OAuth flow permanently.
- [ ] Keep render-service write OAuth routes disabled while `META_PUBLISH_ENABLED=false`.
- [ ] Stop putting Meta tokens in URL query parameters where the provider/client contract permits Authorization headers.
- [ ] Normalize Graph API version configuration; remove the current v18/v26 split for read versus render clients.
- [ ] Add OAuth callback, expiry, refresh, revoke, and scope regression tests.

## Phase 2 — Unified read-only analytics

- [ ] Create a provider-neutral `MetaAnalyticsProvider` interface for Page, post, Reel, account, and media insights.
- [x] Add a real Facebook Graph read client; do not route Facebook analytics through `InstagramMetricsClient`.
- [ ] Add Facebook Page/post/Reel insight endpoints and durable snapshots.
- [ ] Preserve `null`/`PARTIAL`/`UNAVAILABLE` metric semantics; never convert missing provider fields to zero.
- [ ] Add pagination and bounded limits for all account/content reads.
- [ ] Keep exact local matching and provenance for every imported Meta object.
- [ ] Add source key/idempotency to all Meta snapshot writes.
- [ ] Add unified analytics DTOs independent of publication-job identity.
- [ ] Add backend tests for Facebook and Instagram success, partial metrics, provider errors, pagination, and exact matching.
- [ ] Add Angular Facebook/Page/account analytics views and snapshot history.

## Phase 3 — Public comment engagement (Facebook + Instagram only)

**Product decision:** Implement Facebook Page comments/replies and Instagram post/Reel comments/replies together. Instagram DM, Messenger, private conversations, unsolicited outbound messages, and automatic AI replies are explicitly out of scope.

- [x] Add `META_COMMENT_REPLY_ENABLED=false` with a server-side fail-closed guard; `META_PUBLISH_ENABLED` remains separate and unchanged.
- [ ] Verify required official comment-read/reply scopes; never add them to the read-only analytics OAuth flow.
- [x] Add durable canonical models for `MetaComment`, `MetaCommentReply`, `MetaCommentThread`, and delivery attempts; keep the shape extensible for future private conversations without implementing them.
- [x] Normalize Facebook Page and Instagram post/Reel comment/reply webhook payloads with provider event IDs and deduplication.
- [x] Add comment ingestion through the existing Facebook/Instagram webhook endpoints.
- [ ] Add comment/reply polling and reconciliation for missed events.
- [x] Add moderation state: `RECEIVED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `SENT`, `FAILED`, `RETRYABLE`.
- [ ] Add optional AI reply-draft generation; drafts never send automatically.
- [x] Require human approval before every outbound public comment reply.
- [x] Add provider-specific Facebook and Instagram comment-reply adapters behind one canonical service.
- [x] Enforce `META_COMMENT_REPLY_ENABLED` immediately before every provider write.
- [ ] Add frontend public-comment review, draft approval, reply status, and audit views; do not add DM/Messenger UI.
- [ ] Add realistic webhook, deduplication, moderation, approval, idempotency, and reply tests.

## Phase 4 — Webhooks and operations

- [x] Verify Meta webhook signatures in every environment; fail closed when a configured secret is absent.
- [x] Separate publication-status webhook parsing from public-comment event parsing; DM/Messenger event parsing remains out of scope.
- [ ] Persist raw event identity safely without storing unnecessary personal data.
- [ ] Add replay/reconciliation endpoint for failed or ambiguous inbound events.
- [ ] Add operational dashboards for token health, API errors, rate limits, webhook lag, and reply delivery.
- [ ] Add alerting without including tokens, message bodies, or sensitive user data in logs.

## Phase 5 — Verification and release gate

- [ ] Add mock Graph API contract tests for every GET/POST route.
- [ ] Add tests that prove all Meta publish routes remain blocked by default.
- [ ] Add tests that prove read-only Meta OAuth never requests publish scopes.
- [ ] Run backend tests and record unrelated baseline failures separately.
- [ ] Run creative-render-service tests and package.
- [ ] Run frontend tests and production build.
- [ ] Add an opt-in read-only Meta smoke test requiring `META_LIVE_TEST=true`.
- [ ] Do not run a live publish/reply test until explicit confirmation and a dedicated test Page/account are provided.

## Explicit non-goals

- No automatic Meta publishing.
- No automatic AI comment replies; every public reply requires human approval.
- No Instagram DM or Messenger implementation in this phase.
- No new outbound private conversations.
- No Meta website scraping.
- No reuse of OpenArt credentials or OpenArt provider abstractions for Meta.
- No changes to prompt scoring, video analysis, OpenArt, or unrelated generated quality-rule work.

## Definition of Done

- [ ] Meta publishing is fail-closed by default at controller, service, worker, and UI layers.
- [ ] Read-only OAuth is durable, refreshable, revocable, and scope-verified.
- [ ] Facebook and Instagram analytics are unified, persisted, provenance-aware, and honest about missing data.
- [ ] Public Facebook/Instagram comments have typed persistence, webhook deduplication, moderation, approval, idempotency, and audited replies.
- [ ] Dashboard exposes read-only analytics and human-approved public comment replies without hidden publish side effects.
- [ ] Backend/frontend/package gates are green except explicitly documented unrelated baseline failures.
- [ ] Live read-only smoke passes with a dedicated Meta test account.
- [ ] No publish/reply live test is run without explicit approval.

---

# Intelligent Visual Reference Engine — TODO

Implementation follows the approved visual-reference prompt and stays inside the existing seven-stage workflow. No paid image-generation, vision, OpenArt rendering, publishing, or production-media mutation is allowed during local implementation.

## Slice A — Reconcile existing contracts

- [x] Read current audit/backlog/progress docs and Render-stage implementation.
- [x] Inventory existing image assets, first-frame bindings, evidence records, authorization checks, and provider adapters.
- [x] Inventory OpenArt capability snapshots, request schemas, model IDs, and worker serialization.
- [x] Map reusable contracts and document gaps without duplicating render/validation pipelines.

## Slice B — Versioned visual-reference state

- [x] Add or reuse explicit roles: `CHARACTER_REFERENCE`, `SCENE_REFERENCE`, `FIRST_FRAME`, `CRITICAL_SCENE`, `END_FRAME`, `TRANSITION_REFERENCE`.
- [x] Persist immutable reference-plan, asset provenance, hashes, prompt/version lineage, beat/state, validation, and operator acceptance.
- [x] Preserve historical one-image records and prevent prompt revisions from silently inheriting incompatible evidence.

## Slice C — First-frame inspection and proposal

- [x] Inspect exact accepted prompt, story revision, characters, authoritative references, opening state, existing bindings, and file evidence without paid calls.
- [x] Implement statuses: `AVAILABLE_AND_COMPATIBLE`, `AVAILABLE_REVIEW_REQUIRED`, `MISMATCH_CONFIRMED`, `MISSING`, `STALE`, `UNKNOWN`.
- [x] Handle missing/empty/unsaved prompts without speculative generation.
- [x] Prepare bounded first-frame generation requests using the exact opening scene, references, framing, dimensions, and authorized cost.

## Slice D — Prompt/image consistency

- [x] Reuse visual/evidence infrastructure for identity, object, setting, spatial, opening-promise, physical-state, continuity, and technical checks.
- [x] Distinguish match, material mismatch, warning, insufficient evidence, service failure, and not applicable.
- [x] Keep metadata verification separate from semantic/identity verification.
- [x] Expose grounded mismatch findings and minimum correction options.

## Slice E — Critical-scene intelligence

- [x] Select conservative visual anchors from structured timeline, beat evidence, producibility, and generator risk.
- [x] Recommend a second image only when benefit is material and provider support is evidenced.
- [x] Persist beat/state and narrative position; never label ordinary references as time-controlled keyframes.

## Slice F — Optional additional references

- [x] Prepare bounded critical-scene requests with shared identity, costume, environment, object state, and prompt lineage.
- [x] Validate cross-image identity, environment, object counts, state changes, and intended transformations.
- [x] Classify `INTENDED_STATE_CHANGE`, `INCONSISTENT_REFERENCE`, and `INSUFFICIENT_EVIDENCE`.

## Slice G — Capability-aware OpenArt transport

- [x] Verify Seedance 2.0 Mini, 2.0, and 2.5 through the actual configured adapter/request path.
- [x] Record `SUPPORTED`, `UNSUPPORTED`, or `UNVERIFIED` for start/end, multi-reference, character, storyboard, segment, duration, aspect, resolution, and ordering semantics.
- [x] Serialize only real provider payload fields and assert exact role/order/hash transport in mock tests.
- [x] Reject unsupported combinations before paid submission; never fabricate intermediate-frame controls.

## Slice H — Render-stage UI

- [x] Integrate Visual Reference Planning inside the existing Render stage; do not add an eighth stage.
- [x] Add English-only sections for First Frame, Critical Scene Reference, Cross-Reference Validation, Generation Strategy, and Cost/Readiness.
- [x] Support inspect, select, upload, replace, bounded proposal review, keep, and validation actions with explicit authorization.
- [x] Keep advanced provider details collapsible and preserve refresh/reload/version restoration.

## Slice I — Canonical admission and queue

- [x] Bind accepted prompt version/hash, role-specific image hashes, supported provider settings, fresh evidence, and paid-render consent to the existing admission authority when a visual-reference plan is supplied.
- [x] Invalidate stale bindings when prompt or references change.
- [x] Prove UI → API → persistence → queue snapshot → worker → provider payload transport.
- [x] Preserve idempotent replay and prevent side effects when admission fails.

## Slice J — Safety, learning, and verification

- [x] Validate uploads by content, size, dimensions, decoding, path safety, hash, and provenance.
- [x] Keep prompt, image, vision, and video budgets separate; prevent hidden calls and unbounded retries.
- [x] Persist post-render reference strategy and actual QA evidence without claiming causality.
- [x] Add V01–V35 regression coverage plus newly discovered integration-boundary tests.
- [x] Run browser journeys for missing, mismatched, critical-reference, unsupported-model, and existing-image paths on desktop/mobile.
- [x] Update implementation progress docs and deploy only locally verified changes.

## Final acceptance checklist

- [x] Approved prompt shows first-frame availability, compatibility, source, version, and evidence.
- [x] Missing, stale, mismatched, uploaded, selected, and generated image paths are actionable and bounded.
- [x] Critical-scene recommendations are conservative and capability-aware.
- [x] Existing canonical render authorization receives exact supported reference bindings.
- [x] Historical assets remain readable and no paid live-provider tests were run without explicit later authorization.
# Quality Engine UX Consolidation & Workflow Integration — TODO

## Slice A — Route and bundle identity
- [x] Identify the served Quality route, source component, shared shell, and deployed bundle.
- [x] Read current audit, backlog, fix progress, and Creative Studio implementation docs.

## Slice B — Truthful analysis status presentation
- [x] Map persisted analysis statuses and score/report contracts.
- [x] Render NOT_ANALYZED, RUNNING/PENDING, COMPLETED, PARTIAL, SERVICE_ERROR, VALIDATION_FAILED, and STALE distinctly.
- [x] Preserve historical partial/error scores without presenting them as verified final grades.
- [x] Keep retry bounded, authorized, budget-aware, and idempotent.

## Slice C — Remove duplicate AI form
- [x] Remove the legacy story/prompt-generation form from Quality without removing backend roles or saved data.
- [x] Add compact Create New Video and I Have an Existing Prompt actions.

## Slice D — Consolidated navigation and identity
- [x] Reuse shared sidebar and preserve deep links.
- [x] Route new ideas to Creative Studio Idea.
- [x] Route existing prompts to exact prompt/version analysis or relevant Studio stage.
- [x] Preserve content, prompt, source, video, validation, review, and repair-session identity across navigation.

## Slice E — Prompt Library
- [x] Replace raw folder discovery with searchable workspace/prompt browser and real status metadata.
- [x] Keep prompt-only and empty folders discoverable with clear empty/loading/error states.
- [x] Make folder creation secondary, secure, Unicode-safe, and refresh-stable.
- [x] Preserve ambiguity for multiple prompt candidates and expose source identity.

## Slice F — English, design, accessibility, responsive layout
- [x] Remove developer-authored Turkish copy and standardise en-GB UI terms.
- [x] Align Quality with shared layout, typography, navigation, cards, focus, labels, and responsive breakpoints.
- [x] Keep advanced technical settings contextual and collapsible.

## Slice G — Regression and browser acceptance
- [x] Add Q01–Q30 behavioural regression coverage.
- [x] Run aligned local browser journeys for desktop, tablet, and mobile with mock providers.
- [x] Verify no paid calls or historical-data mutations during navigation/refresh.
- [x] Build, test, deploy only after all checks pass and document limitations honestly.

# Story Quality & Alternative Diversity Engine — TODO

## Slice A — Story modes and constraints
- [x] Add explicit Explore Different Stories and Improve My Existing Story modes.
- [x] Add locked requirements, preferences, open creative choices, and mode-aware request payloads.
- [x] Preserve existing B11 STORY, approvals, budgets, persistence, and BUILD_PROMPT lineage.

## Slice B — Structural evidence and diversity
- [x] Add candidate structural evidence extraction without fabricating unsupported fields.
- [x] Add evidence-backed DISTINCT / PARTIALLY_DISTINCT / NEAR_DUPLICATE / INSUFFICIENT_EVIDENCE classification.
- [x] Add contextual story preflight for opening, progression, mechanism, agency, ending, and production risk.
- [x] Handle Mimi sticky-note multiplication and occlusion fixtures conservatively.

## Slice C — Recommendation and bounded correction
- [x] Add explainable comparison and advisory recommendation.
- [x] Add bounded Generate More Distinct Alternatives and Refine Selected Story actions.
- [x] Preserve immutable candidate history and explicit approval provenance.

## Slice D — Creative Studio UI
- [x] Add English story mode and creative freedom controls.
- [x] Add complete candidate cards, comparison evidence, and expandable technical evidence.
- [x] Keep selection, edit, approval, refinement, and existing prompt flows clear.

## Slice E — Integration and persistence
- [x] Ensure BUILD_PROMPT receives only the exact approved story revision.
- [x] Persist mode, constraints, candidate evidence, diversity/preflight results, and lineage using existing entities.
- [x] Ensure reload/reopen does not repeat provider calls or mutate historical data.

## Slice F — Verification and delivery
- [x] Add required structural, fixture, budget, lineage, and regression tests.
- [x] Run short-idea and detailed-story browser journeys with mock providers.
- [x] Update progress documentation, build, test, and deploy only after all checks pass.

# OpenAI Story Review & Iterative Revision Validation — TODO

## Slice A — Optional STORY_REVIEW role
- [x] Add a separate STORY_REVIEW role routed to OpenAI through the existing provider abstraction.
- [x] Define validated collection review input/output contracts with candidate IDs, fingerprints, provenance, findings, recommendation, cost and limitations.
- [x] Enforce explicit consent, positive budget, one bounded collection call, no automatic retry, and LOCAL_MOCK/live provenance.

## Slice B — Story review analysis
- [x] Review all candidates together for opening, coherence, progression, ending, generator risk and source fidelity.
- [x] Reuse story-structure diversity evidence and distinguish DISTINCT/PARTIALLY_DISTINCT/NEAR_DUPLICATES/INSUFFICIENT_EVIDENCE.
- [x] Support CONFIRMED_ISSUE, POTENTIAL_RISK, NOT_DETECTED, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE and SERVICE_ERROR semantics.

## Slice C — Review UI and recommendation
- [x] Add Review Stories with OpenAI controls with model, count, budget, consent and status.
- [x] Show compact per-card review status and a full OpenAI Story Comparison report.
- [x] Keep recommendation advisory and allow human override.

## Slice D — Revision lifecycle
- [x] Add exact candidate/revision fingerprints and immutable review history.
- [x] Mark edited stories and affected reviews stale without erasing historical evidence.
- [x] Add Review Updated Story, resolved/remaining/new findings, and bounded iterative review.
- [x] Preserve locked requirements and invalidate incompatible downstream prompt readiness.

## Slice E — BUILD_PROMPT lineage
- [x] Pass only the exact approved current story revision plus bounded selected concerns to BUILD_PROMPT.
- [x] Preserve source story, candidate, revision, review, approval and prompt lineage across refresh/reopen.
- [x] Ensure optional review failure never becomes render authorization failure.

## Slice F — Verification
- [x] Add provider-role, schema, budget, fingerprint, staleness, finding-diff, idempotency and lineage tests.
- [x] Run mock desktop/mobile browser journeys for initial and updated story review.
- [x] Update progress documentation and deploy only after every checkbox is complete.
