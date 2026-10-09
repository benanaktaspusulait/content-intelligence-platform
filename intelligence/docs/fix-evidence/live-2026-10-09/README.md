# Docker deployment and live text-role verification — 2026-10-09

The user authorized deployment to the existing Docker environment, then authorized paid calls after supplying the DeepSeek key. This supersedes the earlier no-paid-test restriction for the bounded text tests below. All changes remain on `master`; no new worktree was created.

## Deployment

Backend, ML, creative render and frontend images were rebuilt and deployed through the existing `intelligence/docker-compose.yml`. The existing PostgreSQL volume was retained. Backend, ML, render and PostgreSQL report healthy; nginx serves the frontend successfully. Nine gateway HTTP checks returned 200. Backend migrations advanced from V43 to V55 with no failed migration. Counts remained 49 videos, 3 prompt versions and 3 contents. No synthetic rows were inserted into the real database.

The application is available at [localhost:4200](http://localhost:4200). Browser checks loaded Overview, Prompt Quality, the exact existing content 1 / prompt version 1 detail, Video Library and Render. The detail screenshot was visually inspected. See [deployment-smoke.json](deployment-smoke.json) for container image identities, readiness and HTTP checks.

Database backup and tagged previous images are retained in `/Users/benanaktas/.codex/deploy-backups/pompom-20261009`. The dump listing was verified. No database restore or migration repair was performed.

## Changes required by deployment/live testing

- Compose loads optional `ml-service/.env` after `backend/.env`. Secrets remain ignored by Git and outside the image. The private ML env configures the three text roles and verified price ceilings.
- Angular routes load components on demand. The initial production bundle fell from 1.03 MB to 505.11 KB, resolving the 1 MB build error. Existing warning thresholds still report initial/style size warnings; production builds succeed. All 71 frontend tests pass.
- A real OpenAI minimal-repair response initially failed JSON parsing. Creative roles now explicitly request JSON object output at the OpenAI SDK boundary while retaining the 2,000-token limit and independent source-span validation. All 19 focused provider/role/semantic-boundary regression tests pass, including the new request-contract regression. The repaired role passed both before redeploy and through the final deployed ML endpoint.

## Paid evidence

| Role | Provider/model | Result |
|---|---|---|
| STORY | DeepSeek `deepseek-flash` | Valid alternatives through the application adapter and deployed ML HTTP endpoint. |
| BUILD_PROMPT | OpenAI `gpt-4o-mini-2024-07-18` | Valid prompt generated from the live DeepSeek story through deployed ML HTTP. |
| MINIMAL_REPAIR | OpenAI `gpt-4o-mini-2024-07-18` | Valid exact source-span patch after enforcing JSON, including final deployed ML HTTP. |

Each request had a $0.01 local ceiling and no automatic retry. Seven paid attempts were made, with five verified successful outputs. The first attempt lost its result because the evidence directory did not yet exist; its provider outcome/usage cannot be recovered. The pre-fix non-JSON repair also lacks returned usage. These attempts are preserved as unmeasured, not counted as verified success. Known successful-call token estimates total approximately $0.00195; this is not a verified invoice total. The total configured test ceiling was $0.07. Details are in [live-call-summary.json](live-call-summary.json) and the per-call JSON files.

Price configuration used the verified official [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/) peak cache-miss rates and [OpenAI GPT-4o Mini pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini). Model/configuration readiness is not automatically relabeled live acceptance; the API's general `liveVerified` flag remains false, with specific live evidence recorded here.

## Remaining acceptance boundary

This verifies paid text-role transport and output contracts. B14's broader vision/critic/generated-video acceptance remains incomplete. OpenArt stays mock/disabled, semantic video calls stay disabled and publishing switches stay disabled. No video generation, social publication, production statistical model fitting or promotion occurred. The production registry remains empty; B17 still needs genuine verified mature data. A generated story, prompt or patch remains NOT_VALIDATED until the separate review workflow approves it.
