# Pompom Meta Integration TODO

Scope: Meta integration only. Publishing remains disabled until the safety gate is implemented and explicitly enabled later. Do not modify OpenArt, prompt scoring, Meta publishing, or unrelated generated work while executing a Meta task unless the task explicitly requires it.

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
- [ ] Add frontend test proving disabled Meta platforms cannot be submitted.
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
- [ ] Add a real Facebook Graph read client; do not route Facebook analytics through `InstagramMetricsClient`.
- [ ] Add Facebook Page/post/Reel insight endpoints and durable snapshots.
- [ ] Preserve `null`/`PARTIAL`/`UNAVAILABLE` metric semantics; never convert missing provider fields to zero.
- [ ] Add pagination and bounded limits for all account/content reads.
- [ ] Keep exact local matching and provenance for every imported Meta object.
- [ ] Add source key/idempotency to all Meta snapshot writes.
- [ ] Add unified analytics DTOs independent of publication-job identity.
- [ ] Add backend tests for Facebook and Instagram success, partial metrics, provider errors, pagination, and exact matching.
- [ ] Add Angular Facebook/Page/account analytics views and snapshot history.

## Phase 3 — Comments, messages, and replies

- [ ] Decide supported Meta surfaces: Facebook Page comments, Instagram media comments, Instagram DMs, or Messenger conversations.
- [ ] Verify required official scopes before implementation; do not add write scopes to the read-only OAuth flow.
- [ ] Add durable entities for `MetaConversation`, `MetaMessage`, `MetaComment`, `MetaReply`, and delivery attempts.
- [ ] Normalize webhook payloads into typed inbound events with provider event IDs and deduplication.
- [ ] Add comment/message ingestion endpoints and reconciliation jobs.
- [ ] Add moderation state: `RECEIVED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `SENT`, `FAILED`, `RETRYABLE`.
- [ ] Add outbound reply service with idempotency key and provider-safe retry.
- [ ] Keep replies disabled by default behind a separate `META_REPLY_ENABLED=false` guard.
- [ ] Add reviewer approval and audit trail before any outbound reply.
- [ ] Add frontend inbox/thread/comment/reply screens only after the backend state model exists.
- [ ] Add realistic webhook, deduplication, moderation, and reply tests.

## Phase 4 — Webhooks and operations

- [ ] Verify Meta webhook signatures in every environment; fail closed when a configured secret is absent.
- [ ] Separate publication-status webhook parsing from comments/messages/replies event parsing.
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
- No automatic comment/message replies.
- No Meta website scraping.
- No reuse of OpenArt credentials or OpenArt provider abstractions for Meta.
- No changes to prompt scoring, video analysis, OpenArt, or unrelated generated quality-rule work.

## Definition of Done

- [ ] Meta publishing is fail-closed by default at controller, service, worker, and UI layers.
- [ ] Read-only OAuth is durable, refreshable, revocable, and scope-verified.
- [ ] Facebook and Instagram analytics are unified, persisted, provenance-aware, and honest about missing data.
- [ ] Comments/messages/replies have typed persistence, webhook deduplication, moderation, idempotency, and audit trails.
- [ ] Dashboard exposes read-only analytics and approved reply workflows without hidden publish side effects.
- [ ] Backend/frontend/package gates are green except explicitly documented unrelated baseline failures.
- [ ] Live read-only smoke passes with a dedicated Meta test account.
- [ ] No publish/reply live test is run without explicit approval.
