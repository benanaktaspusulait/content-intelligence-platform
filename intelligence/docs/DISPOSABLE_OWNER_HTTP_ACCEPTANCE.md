DISPOSABLE_BACKEND_STARTED: YES
REAL_HTTP_PORT_OPEN: YES
DISPOSABLE_POSTGRESQL: VERIFIED
FLYWAY_MIGRATIONS: VERIFIED

OWNER_LOGIN_HTTP: VERIFIED
OWNER_SESSION: VERIFIED
CSRF_AND_AUTHORIZATION: VERIFIED

APPROVED_TEST_SOURCE_CREATED: YES
SOURCE_READBACK_HTTP: VERIFIED

ML_FIXTURE_CONNECTED: VERIFIED
NO_EXTERNAL_EGRESS: VERIFIED

HARNESS_EXIT_CODE: 0

PRODUCTION_DATABASE_WRITES: 0
REAL_PROVIDER_CALLS: 0
REAL_IMAGE_CALLS: 0
REAL_RENDER_CALLS: 0

P0_HTTP_ACCEPTANCE: YES

# Disposable owner HTTP acceptance — 2026-10-16

The required P0 checkpoint executed successfully against a real random-port Tomcat application, disposable PostgreSQL and the existing FastAPI fixture transport. The final positive run made **38 actual application HTTP requests**, including rejected security probes. No MockMvc client, mocked Java ML client, fake analysis score or SQL approval insertion was used.

Machine-readable evidence: [acceptance.json](disposable-owner-http-evidence/acceptance.json). Deliberate backend-start failure: [negative-backend-start.json](disposable-owner-http-evidence/negative-backend-start.json).

## Reproduction and actual startup

From the repository root, with Docker running, Java **21**, Maven and the existing ML `.venv`:

```sh
./intelligence/scripts/acceptance-story-firstframe.sh --p0
```

No production secret is needed. The script starts the **existing** FastAPI app on an allocated loopback port and runs:

```sh
mvn -q -Dtest=DisposableOwnerHttpAcceptanceTest \
  -Dpompom.acceptance=true \
  -Dpompom.acceptance.ml-url=http://127.0.0.1:52497 \
  -Dpompom.acceptance.output=<this-run-output>/backend-http.json \
  -DargLine=-Djava.security.manager=allow test
```

The test uses `@SpringBootTest(webEnvironment = RANDOM_PORT)`, actual controllers/servlet filters, `java.net.http.HttpClient`, Testcontainers and real Flyway. `@Testcontainers` is required and is **not** configured to skip when Docker is absent. A component-only invocation is explicitly named `--components`; it does not declare P0 or full E2E success. The default mode is `--p0`.

Final positive execution:

| Item | Observed value |
|---|---|
| Spring HTTP address during the run | `http://127.0.0.1:52521` |
| Health | `GET /actuator/health` → **200**, JSON `status=UP` |
| Disposable PostgreSQL | `jdbc:postgresql://localhost:52508/disposable_owner_http?loggerLevel=OFF` |
| PostgreSQL container | `fbcd256878cc7d5b678be1687a950c807256d31cbe924e4bd24378b1f95d65ff` |
| `SELECT current_database()` | `disposable_owner_http` |
| Latest successful Flyway version | **69** |
| Successful migrations | **67**, queried from the disposable schema history |
| ML base URL injected into the actual `QualityMlClient` | `http://127.0.0.1:52497` |
| ML fixture result | `ISOLATED_FIXTURE`, `providerDispatched=false`, `calls=0`, `actualCostUsd=0` |
| Surefire result | **1 test, 0 failures, 0 errors, 0 skips** |
| Harness exit | **0** |

Ports and UUIDs are per-run values. The application, FastAPI process, credential file, temporary workspace and PostgreSQL container were cleaned up after the run; the addresses above are evidence of the execution, not retained services.

## Root cause and targeted changes

The previous harness never launched an HTTP-capable Spring application. Its successful component tests therefore could not supply an authenticated HTTP session or an approved HTTP-readable source. The first concrete HTTP run also exposed a test-bootstrap error: the STORY endpoint requires a canonical **relative** workspace destination below `library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026`; an absolute `/tmp/...` directory is insufficient. The revised bootstrap creates that destination through the existing workspace API under a temporary data root.

Another contract detail was respected without changing application semantics: existing story revision/approval IDs use the application's FNV revision fingerprint. The test supplies that exact revision fingerprint and separately computes and verifies the complete story's **SHA-256**. It does not substitute a SHA-256 for the existing revision identifier or weaken approval validation.

Implementation files:

- `backend/src/test/java/com/pompomhills/intelligence/DisposableOwnerHttpAcceptanceTest.java`: random-port Spring application, temporary strong owner credential, real HTTP trace, security assertions, business API source bootstrap, actual Ruleset 1.11 evaluation and read-back.
- `scripts/acceptance-story-firstframe.sh`: starts the FastAPI fixture transport and required backend HTTP test; keeps per-run machine evidence; returns nonzero on absent Docker, startup, login, source, network-policy or assertion failures. It accepts a separately labelled component mode.
- `scripts/acceptance-ml-http.py`: launches the existing FastAPI app with a process-local socket/DNS egress guard. It adds no application route and does not implement a second provider fixture.

No production controller, authentication code, evaluator, engine, migration or deployment configuration changed.

## Owner/security proof through real HTTP

A fresh 48-byte cryptographically random credential was created for `disposable-owner`, with a `0700` temporary directory and `0600` credential file. The normal `CpqOwnerAccess` and `CpqOwnerController` read this isolated configuration. Credentials, CSRF values, session IDs and authentication response bodies are omitted from evidence.

The trace verifies:

- Protected owner read without login → **403**.
- Wrong credential with valid bootstrap CSRF → **401**.
- Login without CSRF or with hostile Origin → **403**.
- Correct credential with current CSRF and matching Origin → **200**, `authenticated=true`, actual HttpOnly `JSESSIONID` returned.
- Login rotates the session ID and CSRF token.
- Protected owner read with the cookie → **200**.
- Owner remains denied independent `EVIDENCE_REVIEWER` access → **403**.
- Owner policy action missing CSRF or using hostile Origin → **403**.
- The same owner policy action with proper cookie/CSRF reaches the actual backend source policy → **200**, `READY_FOR_SOURCE_BINDING`, no blockers.
- Logout without CSRF → **403**; valid logout → **200**; the previously authorized owner read then returns **403** and owner state is unauthenticated.
- Five failed logins followed by the correct credential still return **401**, proving the real rate limiter enforces its lockout.

No authentication bypass, test login endpoint or replacement filter was introduced. Existing source creation/revision/approval APIs execute in that same logged-in client; their existing candidate/revision/fingerprint validation remains intact. A deliberately stale approval fingerprint returns **409** before the correct exact candidate is approved.

## Legitimate disposable source and exact read-back

A synthetic **Pip** test source was used. It is neither the original Mimi story nor a persisted production revision. Normal application HTTP APIs created content, a STORY fixture response, an operator source revision, its exact story approval, an immutable prompt version, studio-session provenance, authoritative production settings and a persisted REVIEW analysis.

| Record | Actual disposable identifier |
|---|---|
| Content ID | `1` |
| Generated STORY record | `38150813-0f87-4b74-b6b8-f47a3f110a72` |
| Approved STORY/revision record | `315611aa-c796-446d-808c-2b32cdaf6d4a` |
| Story revision ID | `candidate-1-revision-7d6e06a4` |
| Story approval record | `fae32caa-fb3e-47eb-bb95-cbc879cd9bbf` |
| Story revision fingerprint (existing FNV contract) | `7d6e06a4` |
| Approved story SHA-256 | `b9a62583fde3b21ed26b89e32bfe9029d53773b340fdb1d21cbcec206f19068a` |
| Prompt version ID | `1` (version 1 in the isolated database) |
| Exact prompt SHA-256 | `7d1a88d2db57a2061ad2e890fffa7f1917f1a171d769d4fa21f675da3bdd56bf` |
| Studio-session record | `28aa2e21-dbec-43fe-ac09-c5f2678f9fdc` |
| Production-settings record | `dad5956a-f201-4a70-8667-910be4d137d6` |
| Actual REVIEW analysis | `f89fb891-2f7b-402f-b607-a9a56ecfadb8` |

The approved text returned by HTTP was:

> Pip the rabbit wants to place a sticky note on a toy cabinet. The note sticks to Pip's finger instead. Pip peels with the other hand and it splits into two notes, one per hand. Each pull doubles the sticky notes from two to four to eight, covering Pip's arms and face. Pip sees the note-covered reflection in a mirror and gasps. Pip remains covered until a sneeze scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy.

`GET /api/v1/intelligence/workflow/cpq/story-evolution-source?analysisId=f89fb891-2f7b-402f-b607-a9a56ecfadb8` returned **200**, with the exact story, approval ID, content/prompt IDs, canonical analysis and production settings. Its `storySha256` matched an independently recomputed SHA-256 of the returned approved text. Separate HTTP requests read back the approved STORY, approval record, exact immutable prompt and persisted canonical result.

The complete timed prompt was authored as **test input**, saved through normal prompt versioning and evaluated through the actual `/workflow/review` → FastAPI → Ruleset 1.11 path. Its actual result was **82.54166666666669/B**. This is a new disposable evaluation, not an optimization result or A-generation proof. It was not assigned or copied from the original Mimi `88.40625/B`. The full canonical response is retained in the machine evidence. Missing independent visual/semantic evidence was not supplied as fabricated PASS evidence.

## Full HTTP trace

All requests below use the actual Spring HTTP socket at `http://127.0.0.1:52521`. The fixture's own health/transport checks are additional FastAPI HTTP requests.

| # | Method | Request path | Actual status |
|---|---|---|---|
| 1 | `GET` | `/actuator/health` | 200 |
| 2 | `GET` | `/api/v1/intelligence/workflow/cpq/optimization-runs/latest?analysisId=6bfa6034-acac-4add-9986-5b572f80d71e` | 403 |
| 3 | `GET` | `/api/v1/intelligence/workflow/owner-auth` | 200 |
| 4 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |
| 5 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 403 |
| 6 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 403 |
| 7 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 200 |
| 8 | `GET` | `/api/v1/intelligence/workflow/cpq/optimization-runs/latest?analysisId=6bfa6034-acac-4add-9986-5b572f80d71e` | 200 |
| 9 | `GET` | `/api/v1/intelligence/workflow/cpq/original-prompts/e71759ca-ed22-4f08-a33b-640a5b900498/fidelity-review` | 403 |
| 10 | `POST` | `/api/v1/intelligence/workflow/cpq/original-prompts/preflight` | 403 |
| 11 | `POST` | `/api/v1/intelligence/workflow/cpq/original-prompts/preflight` | 403 |
| 12 | `POST` | `/api/v1/videos/prompt-workspaces/folders` | 200 |
| 13 | `POST` | `/api/v1/intelligence/contents` | 200 |
| 14 | `POST` | `/api/v1/intelligence/workflow/creative-role` | 200 |
| 15 | `POST` | `/api/v1/intelligence/workflow/records/38150813-0f87-4b74-b6b8-f47a3f110a72/story-revisions` | 200 |
| 16 | `POST` | `/api/v1/intelligence/workflow/creative-role/315611aa-c796-446d-808c-2b32cdaf6d4a/approve-story` | 409 |
| 17 | `POST` | `/api/v1/intelligence/workflow/creative-role/315611aa-c796-446d-808c-2b32cdaf6d4a/approve-story` | 200 |
| 18 | `POST` | `/api/v1/intelligence/contents/1/prompt-versions` | 201 |
| 19 | `POST` | `/api/v1/intelligence/workflow/studio-sessions` | 200 |
| 20 | `POST` | `/api/v1/intelligence/workflow/production-settings` | 200 |
| 21 | `POST` | `/api/v1/intelligence/workflow/cpq/original-prompts/preflight` | 200 |
| 22 | `POST` | `/api/v1/intelligence/workflow/review` | 200 |
| 23 | `GET` | `/api/v1/intelligence/workflow/records/fae32caa-fb3e-47eb-bb95-cbc879cd9bbf` | 200 |
| 24 | `GET` | `/api/v1/intelligence/workflow/records/315611aa-c796-446d-808c-2b32cdaf6d4a` | 200 |
| 25 | `GET` | `/api/v1/intelligence/contents/1/prompt-versions` | 200 |
| 26 | `GET` | `/api/v1/intelligence/workflow/records/f89fb891-2f7b-402f-b607-a9a56ecfadb8` | 200 |
| 27 | `GET` | `/api/v1/intelligence/workflow/cpq/story-evolution-source?analysisId=f89fb891-2f7b-402f-b607-a9a56ecfadb8` | 200 |
| 28 | `POST` | `/api/v1/intelligence/workflow/owner-auth/logout` | 403 |
| 29 | `POST` | `/api/v1/intelligence/workflow/owner-auth/logout` | 200 |
| 30 | `GET` | `/api/v1/intelligence/workflow/cpq/optimization-runs/latest?analysisId=6bfa6034-acac-4add-9986-5b572f80d71e` | 403 |
| 31 | `GET` | `/api/v1/intelligence/workflow/owner-auth` | 200 |
| 32 | `GET` | `/api/v1/intelligence/workflow/owner-auth` | 200 |
| 33 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |
| 34 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |
| 35 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |
| 36 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |
| 37 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |
| 38 | `POST` | `/api/v1/intelligence/workflow/owner-auth/login` | 401 |

## Isolation, egress and cleanup

The shell re-executes with a minimal environment preserving runtime locations while excluding production DB/owner configuration and provider credentials. The test asserts that production DB URLs/passwords, owner secret-file environment and OpenAI/DeepSeek/OpenArt keys are absent. All Spring data/owner/ML properties are set from disposable resources.

The Java **21 test JVM only** installs a network allowlist permitting exactly the disposable PostgreSQL port, the fixture ML port and the allocated application port, all on loopback. It rejects other hosts, external DNS and production loopback ports. Actual negative socket probes verified denial of an external address and `127.0.0.1:5432`. The Python FastAPI process has an audit hook that denies outgoing socket connections and external DNS before network dispatch. Its negative probe was `DENIED_BEFORE_DISPATCH`; both runtime audits recorded **zero unexpected attempts**. This does not rely on an unattached Docker network being called no-egress.

The socket guard is confined to test sources/the acceptance launcher and requires Java 21's explicit test-JVM compatibility flag. Production security, servlet CSRF and owner checks are unchanged. This is not intended as a production SecurityManager design.

Cleanup stops this run's FastAPI process, cancels only this disposable application's background workers, shuts its Spring context/pool, deletes only this run's temporary owner/workspace files and lets Testcontainers remove its own PostgreSQL container. Logs/evidence remain under the run's `backend/target/disposable-owner-http/` directory. No global Docker cleanup was performed.

## Strict failure-exit proof

A separate isolated run put a temporary `mvn` shim first on PATH; it deliberately failed the backend startup command with exit 17. The harness returned **1**, persisted `p0HttpAcceptance=false` / `harnessExitCode=1`, and cleaned up its own ML runtime. It could not reuse a previous backend evidence file because each run has a fresh output directory. See the retained negative result. No production service was stopped to perform this probe.

Earlier real failures (invalid workspace bootstrap and the test-JVM HTTP permission boundary) also returned nonzero and were corrected in the harness/test only. No failed or skipped assertion was reclassified as a passing P0 result.

## Immediately executable next operation

**`STORY_EVOLUTION_HTTP_START`** is the next operation against this same disposable source/session setup. It was deliberately left unexecuted in this P0 scope. The harness currently keeps the real-dispatch gate false; a later fixture-only continuation must explicitly enable that gate only inside the disposable, no-egress test configuration and supply the existing STORY/STORY_REVIEW fixtures. No production grant is inferred.

The fixture source and real evaluator now execute through HTTP. Autonomous prompt generation, a new canonical **A**, real-provider A repeatability, calibrated **A+**, first-frame generation and visual QA remain outside this successful checkpoint. CPQ grading is inactive, render authorization is false, real provider/image/render calls and production writes are zero. No deployment, commit or push was performed.
