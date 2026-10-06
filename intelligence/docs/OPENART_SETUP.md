# OpenArt integration

The production render path lives in `creative-render-service`. It uses the published OpenArt CLI (pinned to **v0.1.1**) rather than calling an undocumented HTTP API.

## What is implemented

1. Render jobs are queued with an immutable prompt/contract snapshot.
2. The worker submits `openart generate image|video ... --async --json`.
3. The returned OpenArt history ID is persisted in `render_attempts` and `render_jobs`.
4. The worker polls `openart creation get <history-id> --json`.
5. When the creation completes, the result URL is downloaded over HTTPS/HTTP into the configured asset library.
6. Media is probed, recorded, and sent through post-render QA.
7. Provider failures update both the attempt and the render job; unknown/running jobs are bounded by `OPENART_MAX_POLLS`.
8. The worker commits a `SUBMITTING` intent before invoking OpenArt. An uncertain submission becomes `NEEDS_HUMAN_REVIEW` and is excluded from automatic retry, preventing a crash from blindly spending a second generation.
9. Queue-time estimates are reserved in `openart_credit_log` and reconciled in place when the provider history completes. Provider usage is recorded once per OpenArt history ID; a worker retry cannot double-charge the same creation, and `credits_actual` aggregates rerender attempts.

The mock adapter remains the default for local development. Production rejects a mock adapter.

## Install and authenticate the CLI

The CLI uses OAuth credentials, not the old API-key/template contract.

```bash
curl -fsSL https://raw.githubusercontent.com/OpenArt-AI/cli/main/install.sh | sh -s -- --version 0.1.1
openart version
openart login
openart account
```

The login flow stores credentials in `~/.openart/cli-credentials.json`. An OpenArt personal access token can also be supplied through `OPENART_TOKEN`; do not put credentials in source control.

Before spending credits, verify the account and model price:

```bash
openart account --json
openart model list --json
openart model cost --model kling-3-omni --mode text2video --json
```

## Local configuration

Run the service from `intelligence/creative-render-service` with the CLI available on `PATH`:

```bash
export OPENART_ENABLED=true
export OPENART_MOCK_ENABLED=false
export OPENART_CLI_PATH="$(command -v openart)"
export OPENART_CLI_TIMEOUT=300
export OPENART_MAX_POLLS=180
mvn spring-boot:run
```

The active settings are in `src/main/resources/application.yml`:

| Variable | Default | Purpose |
|---|---:|---|
| `OPENART_ENABLED` | `false` | Select the real adapter. |
| `OPENART_MOCK_ENABLED` | `true` | Development fallback; must be `false` in production. |
| `OPENART_CLI_PATH` | `openart` | CLI executable path. |
| `OPENART_TOKEN` | empty | Optional token; OAuth files are preferred. |
| `OPENART_CLI_TIMEOUT` | `300` | Per-command/download timeout in seconds. |
| `OPENART_MAX_POLLS` | `180` | Maximum 10-second provider polls per attempt. |
| `OPENART_MONTHLY_BUDGET` | `1000` | Local monthly budget gate. |
| `OPENART_FIRST_FRAME_COST` | `10` | Queue-time fallback estimate for images. |
| `OPENART_VIDEO_COST` | `100` | Queue-time fallback estimate for videos. |

The queue uses the configured estimate as a durable preflight reservation. Admission and reservation are serialized with a PostgreSQL transaction-scoped advisory lock, so concurrent idempotency keys cannot all pass the same stale budget read. On submission, the adapter also asks `model cost` when the provider does not return a quote, and on completion the provider-reported usage is reconciled into `credits_actual`. If the provider does not expose usage, the persisted estimate is used and marked as an estimate fallback. A reservation is released for a render cancelled before submission; it is deliberately retained when a provider submission is in flight or uncertain and must be reconciled by an operator rather than silently releasing spend.

## Docker Compose

Authenticate on the host first:

```bash
openart login
```

Start the stack with the real provider:

```bash
OPENART_ENABLED=true \
OPENART_MOCK_ENABLED=false \
OPENART_CREDENTIALS_DIR="$HOME/.openart" \
docker compose -f intelligence/docker-compose.yml up --build creative-render-service
```

The render image installs and checksum-verifies the pinned Linux OpenArt CLI binary. The host `~/.openart` directory is mounted at `/root/.openart`, which is the runtime user's credential directory in the image. Set `OPENART_CREDENTIALS_DIR` to another host path when required.

For normal local development, omit those variables; the mock adapter is used and no OpenArt account is contacted.

## CLI contract used by the adapter

The adapter intentionally uses only commands documented by OpenArt CLI v0.1.1:

| Render operation | CLI command |
|---|---|
| Image submit | `openart generate image "<prompt>" --model <model> --async --json --no-input` |
| Video submit | `openart generate video "<prompt>" --model <model> --image <path-or-url> --duration <seconds> --async --json --no-input` |
| Status | `openart creation get <history-id> --json --no-input` |
| Account credits | `openart account --json --no-input` |
| Model quote | `openart model cost --model <model> --mode text2image\|text2video --json --no-input` |

The image command uses the selected model's defaults. The v0.1.1 image CLI does not expose generic `style` or `aspect-ratio` flags, so those choices must be expressed in the approved prompt rather than silently persisted as unused provider parameters. The video request field currently named `firstFrameImageId` is a local image path or an HTTPS CDN URL. The old `--first-frame` option is not used. The adapter downloads the result URL because v0.1.1 has no separate `openart download` command.

## Render lifecycle and status

`RenderAttempt` stages are durable and processed one stage per worker claim:

`QUEUED → SUBMITTING → PROVIDER_QUEUED → DOWNLOADING → POST_RENDER_QA → COMPLETE`

`SUBMITTING` is intentionally unclaimable. If a process dies around the external call, the attempt is held for human reconciliation rather than submitted twice. The corresponding render job status is updated to `GENERATING`, `POLLING`, `DOWNLOADING`, and finally `COMPLETE`. A provider failure/cancellation sets both records to `FAILED`. A worker crash during a poll or download can safely retry that stage; provider usage is protected by the unique `(openart_job_id, operation)` index from migration `V16`.

The default worker lease is ten minutes, longer than a bounded provider/download operation. If the provider remains ambiguous until `OPENART_MAX_POLLS`, the attempt is failed with `PROVIDER_TIMEOUT` instead of polling forever.

## Reconciling an uncertain submission

If the process dies while the attempt is `SUBMITTING`, the worker will not submit it again automatically. An operator must first inspect OpenArt history, then either attach the observed ID:

```bash
curl -X POST http://localhost:8081/api/v1/render-jobs/<job-id>/reconcile-submission \
  -H 'Content-Type: application/json' \
  -d '{"providerJobId":"<openart-history-id>"}'
```

or explicitly close the uncertain attempt while retaining its conservative budget reservation:

```bash
curl -X POST http://localhost:8081/api/v1/render-jobs/<job-id>/reconcile-submission \
  -H 'Content-Type: application/json' \
  -d '{"action":"ABANDON","reason":"No matching OpenArt history found"}'
```

The regular retry endpoint rejects non-terminal/uncertain provider histories; it never blindly submits a second generation.

## Verification

Run the real-adapter fixture test and the render/credit tests:

```bash
cd intelligence
mvn -B -ntp -pl creative-render-service \
  -Dtest='CliRealOpenArtAdapterTest,RenderAttemptOrchestratorTest,CreditTrackingServiceTest,CliMockOpenArtAdapterTest' test
```

The fixture asserts the actual command vocabulary, JSON/stdout separation, history polling, failure normalization, credit parsing, and result download without spending credits.

## Troubleshooting

- **`OpenArt CLI is not available`**: run `openart version`, check `OPENART_CLI_PATH`, and ensure the container image was rebuilt.
- **`not logged in`**: run `openart login` on the same host whose `~/.openart` directory is mounted into the container, or set `OPENART_TOKEN`.
- **`model ... does not support ...`**: omit model-specific duration/aspect settings or use `openart model form <model> text2video` to inspect supported parameters.
- **Job stays queued**: inspect `render_attempts.provider_job_id`, `provider_job_state`, `poll_count`, and the service log. `PROVIDER_TIMEOUT` is the bounded terminal error.
- **Budget blocks a render**: inspect `GET /api/v1/budget/status`; the local budget gate is independent from the provider's account balance.

## Security notes

- Never commit `OPENART_TOKEN` or `~/.openart/cli-credentials.json`.
- Keep the credentials mount scoped to the render service.
- Production requires `OPENART_ENABLED=true` and `OPENART_MOCK_ENABLED=false`; startup checks both the binary and authenticated account access.
