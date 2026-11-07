# Local-First Pilot Runbook

Default mode is offline, read-only, no provider calls and no render requests.

## Inspect the completed local pilot

From the repository root:

```bash
cat intelligence/docs/pilot-readiness-v1/LOCAL_PROMPT_INVENTORY.md
cat intelligence/docs/pilot-readiness-v1/PILOT_VALIDATION_REPORT.md
cat intelligence/docs/pilot-readiness-v1/pilot-manifest.json
```

The source is the existing structured record at `intelligence/docs/semantic-two-stage-v1-phase-b-run-001/complete-story.json`; its immutable story audit and render evidence are in the same run directory. The separate V2 production prompt is in `human-creative-review-v1/production-render-v2/V2_PRODUCTION_PROMPT.md`.

## Offline validation and status

The existing Phase B executable is single-run guarded and has distinct preflight/live modes. Do not use `--execute-live` for a local-first validation. Its historical run has already been claimed, so do not rerun or mutate that run directory. Read the stored `analysis.json`, `story-audit.json`, `REPORT.txt`, V2 preflight JSON and post-render QA instead. The current readiness classification is recorded in `pilot-manifest.json`.

For the applicable existing regression suites:

```bash
cd intelligence/ml-service && .venv/bin/python -m pytest -q
cd ../.. && cd intelligence && mvn -pl creative-render-service -am test
```

## Render gate

There is no valid render command for this candidate today. `PILOT_BLOCKED` is deliberate. The wrapper's `--dry-run` only checks its own current prompt format and does not prove character reference support, duration compliance or that the request is unpaid. Do not run a paid generation command. Do not retry.

After tickets P1–P4 are resolved and human review approves the production prompt, the first controlled operator command must be newly added/verified in the existing render integration and explicitly supplied with render authorization. Until then, exact next command is: `open intelligence/docs/pilot-readiness-v1/PILOT_FIXES.md` and resolve P1–P4; no render command is safe to issue.

Post-render QA is already connected and has consumed the failed V1 fixture. After exactly one authorized render, ingest that single video into the existing post-render QA and human inspection; stop on failure, with no automatic retry.
