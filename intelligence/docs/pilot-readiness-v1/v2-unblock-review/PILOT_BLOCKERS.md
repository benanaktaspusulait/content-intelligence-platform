# V1 Pilot Blockers After Reference/CLI Assessment

Readiness remains **PILOT_BLOCKED**. No approval status was changed. No provider or render call was made.

| Blocker | Evidence | Required action |
|---|---|---|
| `BLOCKED_CHARACTER_REFERENCE` | Canonical Mimi image SHA `7ad3…c59f57` remains `UNREVIEWED` / `NOT_APPROVED`; the existing derivative is also explicitly unapproved. | Human owner reviews and explicitly approves the exact image and hash through the existing character reference review API. |
| `BLOCKED_FIRST_FRAME` | No approved still exists with Mimi pressing the rolling pin onto one connected raised ridge at frame zero. | Produce/review/approve this story-state image through the normal human review process. This task did not generate it. |
| `BLOCKED_ELEMENT2VIDEO_CLI_CONTRACT` | Installed OpenArt CLI 0.1.1 has no element2video selector or separate reference input. Existing project adapter accepts only text prompt and optional first-frame image. | Use a CLI release with documented element2video reference arguments; extend the current adapter only against that published contract and test its outgoing request with mocks. |
| `BLOCKED_BOTH_INPUTS_UNPROVEN` | Saved model form records `visualReferences`, but no first-frame-specific element2video field or precedence. CLI's `--image` means first-frame conditioning only. | Verify the exact API semantics for character reference(s) and first-frame image, and demonstrate both together where required. |
| `BLOCKED_DURATION_GUARANTEE` | 14s request supported by stored form; output ≤15s not guaranteed. Prior 15s request measured 15.041667s video stream. | Keep duration 14s and require measured post-render duration gate; establish an acceptable margin with a separately authorized test before declaring production compatibility. |
| `BLOCKED_AUDIO_CONTROL` | Existing CLI has no audio-disable flag though stored schema includes `generateAudio`. | Use documented mode/control that explicitly sets audio generation off or accept only when post-render audio QA verifies silent output. |

## Website Docker environment

Read-only check only: `/Users/benanaktas/project/video/pompom-website` still contains `Dockerfile`, `docker-compose.yml`, `.env.example` and documented `setup-docker.sh`; `docker compose config --quiet` passes and reports one `app` service. No containers are running. No website image is currently listed. Therefore the documented source/build configuration is present and valid, so the development site is rebuildable in principle, but no image build/start/health check was performed. The setup script also initializes local storage, runs migrations/seeds, and prepares assets; it was not run. No images, containers, volumes, databases, or source files were removed or changed in this task.

## Exact next commands

For the human reference decision, use the authenticated local character-reference review API procedure in `MIMI_REFERENCE_REVIEW.md`; do not use an approval call until a human reviewer has visually decided. No safe render command currently exists. After all blockers are closed, the first render command must come from the existing project adapter updated to a documented reference-capable CLI contract and remain behind the project's explicit render authorization gate.

## Verification results

- Java focused integration path: **25 passed** (`CliRealOpenArtAdapterTest`, `OpenArtReferenceResolverTest`, `RenderAttemptOrchestratorTest`, `RenderAutomaticFirstFrameTest`). Tests use local fake processes/mocks; provider/render calls: 0.
- Python OpenArt wrapper: **12 passed** when run under the existing ML-service virtual environment. Initial system-Python collection failed only because Pydantic was absent there.
- No code was changed: the installed CLI lacks the required mode and request shape, so a guessed flag would not be a valid integration.
- Docker Compose configuration validation passed; no build, container start, image removal, volume removal, or production operation occurred.
