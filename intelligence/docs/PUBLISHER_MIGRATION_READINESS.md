# Publisher Migration Readiness

## Scope

The repository contains three logical publisher boundaries that are being migrated from the standalone Python package to Java microservices:

1. **Meta Publisher** — Facebook Page and Instagram Professional/Reels.
2. **TikTok Publisher** — TikTok Content Posting API.
3. **YouTube Publisher** — YouTube Data API / Shorts.

The migration must preserve the existing render control plane. `creative-render-service` remains responsible for asset/QA admission, publication jobs, attempts, leases, idempotency, kill-switches, canonical provider outcomes, and reconciliation state. Publisher services must never become a second queue or a second source of truth.

## Repository evidence

### Python publisher package

- `publisher/pompom_meta_publisher/` contains real Facebook and Instagram implementations, including Facebook `video_reels` upload phases, Instagram public URL storage, container polling, publishing, permalink lookup, retry, secret scrubbing, and a SQLite ledger.
- `publisher/pompom_tiktok_publisher/` contains chunked upload, `Content-Range`, publish status polling, and terminal status handling.
- `publisher/pompom_youtube_publisher/` contains OAuth refresh, resumable upload, Shorts metadata, file-size validation, and share URL creation.
- `publisher/batch_publish.py` directly invokes all three Python package boundaries and bypasses the Java publication queue, QA/asset gates, Meta publication guard, PostgreSQL publication attempts, and Java reconciliation.
- Python uses independent SQLite ledgers. Those ledgers must not be copied into Java; PostgreSQL publication jobs/attempts remain authoritative.
- No Java-to-Python runtime bridge or deployed Python publisher service was found. The Python integration guide contains historical `ProcessBuilder`/cron examples, but repository/runtime evidence did not show an active application caller.
- The Python package has no production-grade provider integration test suite equivalent to the required Java mock contract tests.

### Java publisher package

- `intelligence/creative-render-service/src/main/java/com/pompom/creative/publisher/` contains four in-process Spring beans: Facebook, Instagram Reels, TikTok, and YouTube Shorts.
- `PublicationAttemptOrchestrator` is the current durable execution seam. It claims the attempt, applies `MetaPublicationGuard`, calls a `PlatformPublisher`, persists provider IDs/permalink, and reconciles expired attempts where an adapter supports it.
- Java Facebook currently uses a different Graph upload shape from the Python Facebook `video_reels` implementation.
- Java Instagram expects a public video URL, while the normal render queue provides a local canonical asset path; hosting/public URL creation is not integrated into the Java publication path.
- Java TikTok does not poll the provider status endpoint before treating the result as successful and has no provider reconciliation implementation.
- Java YouTube has resumable upload code but does not preserve the complete Python validation/share URL behavior.
- Java render OAuth/credentials are separate from the backend Meta read-only connection. The backend Meta read token must not be reused for publishing.

### Runtime topology

- `intelligence/docker-compose.yml` currently contains PostgreSQL, ML service, backend, creative-render-service, and frontend.
- There are no `meta-publisher-service`, `tiktok-publisher-service`, or `youtube-publisher-service` containers.
- The frontend gateway routes publication APIs to creative-render-service, but publisher services do not yet exist as internal destinations.

## Target architecture

```text
Frontend / API caller
        |
        v
creative-render-service  (control plane; PostgreSQL source of truth)
        |
        +-- internal publisher contract/auth
        |
        +--> meta-publisher-service
        |       +-- Facebook Page
        |       +-- Instagram Professional/Reels
        |
        +--> tiktok-publisher-service
        |
        +--> youtube-publisher-service
```

The services will be Java Spring Boot applications. A small shared `publisher-contract` module will contain only normalized request/result/error DTOs. Shared support may contain validation, redaction, retry classification, and provider-operation persistence, but no provider-specific logic.

## Capability status

| Capability | Current status | Migration status | Blocking evidence |
|---|---|---|---|
| Python Meta publisher | `IMPLEMENTED` as standalone Python code | Must be ported before deletion | No Java parity suite yet |
| Python TikTok publisher | `IMPLEMENTED` as standalone Python code | Must be ported before deletion | No Java service/reconciliation yet |
| Python YouTube publisher | `IMPLEMENTED` as standalone Python code | Must be ported before deletion | No Java service/parity suite yet |
| Java in-process publishers | `PARTIAL` | Replace with internal clients after service parity | Provider behavior differs from Python |
| Three Java publisher services | `NOT_IMPLEMENTED` | Planned in Tasks 3–5 | No Compose services or internal contract |
| Control-plane integration | `PARTIAL` | Planned in Task 6 | Current bean lookup remains in-process |
| Shared duplicate protection | `PARTIAL` | Planned in Tasks 1–2/6 | Python SQLite and Java PostgreSQL are separate |
| Meta write safety | `FAIL_CLOSED` | Must remain so throughout | `META_PUBLISH_ENABLED=false` |
| Python deletion | `NOT_STARTED` | Final Task 9 only | No deletion before parity/cutover gates |

## Non-goals

- No direct frontend-to-provider calls.
- No Python and Java dual-live publishing for the same publication attempt.
- No SQLite ledger migration as a second source of truth.
- No automatic enabling of Meta publishing.
- No Instagram DM, Messenger, private conversations, unsolicited messaging, or automatic AI replies.
- No Family calibration changes.

## Readiness decision

**Current result: NOT READY for Python removal.**

The Python package contains provider behavior that is richer than the current Java adapters, especially for Meta Facebook Reels, TikTok status polling, and YouTube validation/share URLs. The next implementation step is the shared Java contract and provider-operation model, followed by the three service ports. Python remains intact until the explicit removal gates in `docs/superpowers/plans/2026-10-07-publisher-microservices-java-migration-plan.md` pass.
