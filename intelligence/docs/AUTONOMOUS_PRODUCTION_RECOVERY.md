# Autonomous Production Recovery

**Result: `AUTONOMOUS_PRODUCTION_BLOCKED`**

This change adds an application entry point that reruns existing story evaluators, selects an existing structured candidate, discovers and hash-binds a possible character reference, records a durable run, and stops before paid work when prerequisites are unresolved. It does not produce an MP4 and is not an end-to-end production verification.

## Existing capability reuse

| Capability | Status in this run |
| --- | --- |
| Structured candidate slate and Concept Ranking | Implemented and connected; nine ELIGIBLE source candidates were re-evaluated |
| Beat Grammar, Premise Naturalness and Creative Shape | Implemented and connected; existing evaluators reran on each candidate |
| Historical Territory | Implemented and connected against the existing frozen comparison set only; not a complete production archive lookup |
| Production/publication/rejection history lookup | Missing integration; explicitly `NOT_EVALUATED` in new runs |
| Canonical character image discovery | Implemented and connected as discovery only; a discovered file is not a reviewed/approved character record |
| First-frame generation and validation | Existing separately callable workflow, but not connected to this run; no matching first frame exists |
| Prompt generation and binding | Existing prompt/render contracts are available, but not connected to this run; no production prompt was created |
| Creative Render Service admission and queue | Existing guarded render path; not reached by this run |
| OpenArt/Seedance | Cached schema describes image-to-video 9:16 up to 15 seconds; live model capability is unverified and live dispatch is disabled in this environment |
| Automated video QA | Existing video-analysis endpoints are available, but no MP4 exists to analyse |
| Resumable in-app approval/authorization | Missing integration; the new page can start and inspect a run, but cannot approve/resume one |

## Implemented changes

- `intelligence/ml-service/app/workflow/autonomous_production.py` reruns the existing ranking and creative evaluators against the stored structured slate, applies the requested selection safeguards without changing scores or thresholds, resolves a candidate character drawing, computes its SHA-256, records preflight findings, and persists an idempotent run. No provider transport is called. New run records explicitly mark automated production-history lookup `NOT_EVALUATED` and block on that missing integration.
- `intelligence/ml-service/app/workflow/api.py` exposes idempotent POST and read-only GET run endpoints.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/AutonomousProductionController.java` exposes the application API; `QualityMlClient.java` proxies the bounded operations.
- `intelligence/frontend/src/app/pages/autonomous-production.page.ts`, `app.routes.ts`, and `app.ts` add a “Generate a new video” start action and run view. The action only starts the offline evaluation/preflight; it does not make provider calls.
- `intelligence/docker-compose.yml` mounts the accepted candidate source and character library read-only for the ML service.
- Focused tests were added for the Python run, idempotency and safe run lookup, plus frontend start/read display behavior.

The user’s pre-existing modifications to `canonical_evidence_propagation.py` and `test_canonical_creative_evidence.py` were present before this task and were preserved.

## End-to-end execution evidence

The actual in-process FastAPI application route was exercised offline:

1. `POST /api/v1/workflow/autonomous-production/runs` returned HTTP 200 and durable run `c7ddbef1-e8fd-4e82-955f-743d24921c09`, status `AWAITING_HUMAN_REVIEW`, with `providerRequests: 0`.
2. `GET /api/v1/workflow/autonomous-production/runs/c7ddbef1-e8fd-4e82-955f-743d24921c09` returned HTTP 200 and the persisted run, including `productionHistory.status: NOT_EVALUATED`.
3. A prior app-route run is retained at `intelligence/data/autonomous-production/runs/0c6b0200-aff1-4712-905b-6fda01772e97.json`. Its source, evaluator outputs, selected candidate, image discovery hash, and zero-provider counts are preserved. That earlier record predates the explicit production-history field; it must not be treated as proof that archive lookup ran.

No first frame, production prompt, Render Service job, provider request, or MP4 was created. Accordingly there is no render ID, video duration, spend, or post-render QA result.

## Selected existing story and actual validation

The highest available shoe example (`bg2-c815450f2d7ca346`, “Shoe / Reset To Start / Goal Distance Reversal”) was not sent to production because its final state recreates the opening. The selection was `bg2-f902cc280181d9eb`, **“Snack Box Lid / Reversal / Control Transfer”**, an existing Opa candidate from `intelligence/docs/creative-shape-v1/experiment-seed-42-count-20.json`.

Actual rerun results:

- Concept Ranking: **ELIGIBLE**, Short Form **99**, Ranking **97.6**.
- Beat Grammar: **STRONG**; four unique strategy families, four consequence types, body progression 100, near-duplicate rate 0, payoff distance 0.75.
- Premise Naturalness: **STRONG / admitted**.
- Creative Shape: **CONTROL_REVERSAL**, object-controls-character, final state differs from the opening.
- Historical Territory: **LOW** against the limited frozen reference set; closest listed comparison was `upside-chair-01` at similarity 0.35. This does not establish archive-wide novelty.
- Existing batch diagnostic: `templateShapeRisk: HIGH`, retained as a human review signal.
- Story Premise / Premise Admission: **NOT_EVALUATED** for production; the source is a structured concept candidate and there is no canonical story-review record bound to a production prompt.
- Prompt validation, first-frame validation, and production admission: **NOT_EVALUATED / BLOCKED** because those bound artifacts do not exist.
- Intended duration: **15 seconds**, the hard maximum.

The source contains five 3-second typed beats. The rule is: “The snack box lid flips its usable surface away from the character whenever pressure is applied to it.” The everyday goal is to close the lid.

1. **0–3s:** Opa presses the lid toward its rim; it flips its usable surface away, leaving it facing away from the intended contact.
2. **3–6s:** Opa switches to the opposite broad contact surface and presses; the lid flips again and Opa shifts into the remaining working space.
3. **6–9s:** Opa braces and holds the lid at arm’s length; pressure flips it and pulls Opa off balance.
4. **9–12s:** Opa holds the lid still and moves toward the working point; without pressure the lid remains unchanged, so Opa moves into its space.
5. **12–15s:** Opa resumes closing; the lid flips upside down while held, and Opa must follow it, leaving the object controlling the final pose.

These are the stored source beats, not a production prompt or an approval. The high template-shape risk and lack of production-history lookup remain material review limitations.

## Asset and prompt status

The run discovered `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/opa.png`, SHA-256 `550d14866ef5e64a6d04ac09d2ba80f220eabe11507dbfe2ed198fbdb83ecb75`. It is marked `DISCOVERED_UNREVIEWED`; there is no approved Character Lab reference record for this file. The candidate-specific first frame is **MISSING**. No prompt path/hash exists because a prompt has not been generated. Thus the found canonical drawing cannot be represented as a matching first frame.

## Authorization, rendering and QA

The current environment has OpenArt disabled/mock-configured, no OpenArt token, `POMPOM_EXTERNAL_AI_AUTHORIZED=false`, no explicit maximum spend, and no run-scoped approval/resume action. The cached Seedance capability record is not live-verified. All of these block a live run. The existing Render Service's own admission checks remain in place, but this new start endpoint does not yet connect approved run evidence to a render job.

No MP4 exists for this run. Duration, continuity, action, causality, payoff, and video QA are therefore **NOT_EVALUATED**. The existing human video-review checkpoint cannot yet be populated with an artifact.

## Operator experience and verification

The application now exposes the start action at `/autonomous-production`; its POST creates one durable idempotent run and displays story scores, reference hash, blockers, and run status. It is not yet the requested one-action end-to-end production flow: there is no UI action to resolve review, approve a bounded budget, resume asset generation, or reach the Render Service.

Verification performed:

- Python: `tests/test_autonomous_production.py` — **3 passed**.
- Frontend: autonomous production page and app tests — **4 passed**.
- FastAPI in-process route: POST and GET — **both HTTP 200**, run persisted and zero provider calls.
- Backend Maven test was attempted but could not compile the existing backend; compilation reports missing getters across existing quality/entity classes (for example `ValidationVisualEvidenceProjection` and `RuleGovernanceService`). The new controller test did not execute.
- Ruff was unavailable in the active Python environment (`ruff` command and `python3 -m ruff` are unavailable).

## Exact remaining blockers and next step

The run cannot continue until the application connects production-history lookup and a resumable human review/budget approval action, an operator approves a registry-bound Opa reference and the exact story, and the workflow creates/validates a matching first frame and story-bound prompt. Live execution additionally requires verified Seedance support, configured OpenArt credentials, and one explicit run-scoped spend ceiling/authorization. Then the approved evidence must enter the existing Render Service admission and job queue, followed by actual MP4 QA and a persisted final decision.

Until those integrations and gates are satisfied, the safe current result is **`AUTONOMOUS_PRODUCTION_BLOCKED`**. No paid calls or renders were made.
