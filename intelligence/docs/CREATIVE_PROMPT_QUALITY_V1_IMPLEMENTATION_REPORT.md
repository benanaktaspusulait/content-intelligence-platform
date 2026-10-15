# Creative Prompt Quality V1 implementation report

Date: 2026-10-15  
Status: `CPQ_V1_DEPLOYMENT_BLOCKED` — Docker Desktop's Linux VM stopped after an internal disk-full error; do not deploy until the operator restores the engine.

## Result flags

| Flag | Result | Evidence |
|---|---|---|
| `CPQ_ENGINE_IMPLEMENTED` | **YES, preview contract** | Versioned six-dimension ML endpoint, persisted preview, canonical/source/render separation. No production A/A+ grades. |
| `FIDELITY_EVIDENCE_WORKFLOW_IMPLEMENTED` | **YES, implementation; no current Mimi PASS** | Authenticated `EVIDENCE_REVIEWER`, exact binding, quoted evidence, event mapping and expiry; consumer returns UNKNOWN without matching record. |
| `CALIBRATION_READY` | **TOOLING READY; DATA INCOMPLETE** | Corpus import, blinded packets/judgments, readiness and provisional calibration/held-out analysis are implemented. No CPQ records or reviews have been populated. |
| `CALIBRATION_APPROVED` | **NO** | No approved corpus, thresholds or activation record. |
| `CPQ_GRADING_ACTIVE` | **NO** | Feature state seeded inactive; previews emit no aggregate grade. |
| `B_TO_A_GOLDEN_ACCEPTED` | **NO** | No eligible independently reviewed current-ruleset full-pipeline case is available. |
| `REAL_MODEL_CREATIVE_EFFECTIVENESS_VERIFIED` | **NO** | This task used no providers and makes no effectiveness claim. |

## Contracts and implementation

CPQ V1 uses `SCROLL_STOP_VISUAL_PROMISE`, `CAUSAL_PROGRESSION`, `VISUAL_STORYTELLING`, `PRODUCTION_EXECUTABILITY`, `ENDING_REPLAY`, and `DISTINCTIVE_CREATIVE_VALUE`. The ML preview reports text signals, evidence references, strengths, weaknesses, suggestions, confidence and unknowns without numeric dimensions or A/A+ labels. Verbosity is not a positive input. It marks visual adherence `UNVERIFIED`, audience effect `UNMEASURED`, source fidelity `UNKNOWN` absent matching independent evidence, and render readiness as a separate F8 decision.

Canonical Ruleset 1.11 result is shown separately and never enters a CPQ aggregate. Existing F8 authorization is unchanged. Adaptive V3 preflight now exposes three distinct fields: creative opportunity is `UNKNOWN_REQUIRES_PROMPT_DIAGNOSIS`, canonical A attainability is derived from its existing feasibility ceiling, and CPQ target activation is read from the server-owned inactive policy row. The legacy generation gate and grade contract remain unchanged while CPQ is inactive.

Backend APIs implement saved assessment reads, explicit assessment writes, authenticated fidelity review, capability discovery, corpus creation/import, blind review packets, human judgments, structural readiness, and provisional calibration preview. Source fidelity records bind the current saved analysis, source prompt and candidate fingerprints, approved story revision/fingerprint, intervention, ruleset, production settings, reviewer authority/method, citations, rationale and expiry. The backend derives reviewer identity from the authenticated principal. Calibration review citations must exactly quote the blinded prompt. Evidence records are append-only; a corpus becomes immutable when marked held-out validated or approved. No API currently activates grading.

Migration `V62__creative_prompt_quality_v1.sql` creates the CPQ evidence schema and initializes grading inactive. ML routes are provider-free. The Step 6 UI presents the four independent contracts and requires an explicit operator click to create an assessment preview; loading a saved optimization does not silently write CPQ evidence. Review controls appear only for authenticated fidelity reviewers.

## Calibration and acceptance evidence

The calibration process requires authenticated source-fidelity evidence, exact prompt/story fingerprints, version/profile/generator/duration, held-out split, two distinct blind reviewers, six dimension judgments with cited evidence, an overall anchor and reviewer provenance. Readiness does not approve imported labels. Calibration preview fits diagnostic boundaries only on the calibration split, reports held-out confusion matrix and A/A+ false-positive/false-negative counts, reviewer dimension agreement and missing anchors, and always returns `CALIBRATION_PREVIEW_ONLY`, `aggregateGradesJustified=false`, `activated=false`.

Actual CPQ calibration example count and reviewer count are **zero** at implementation time; no CPQ history was rewritten or populated. The prior acceptance-gap audit records zero quality validations and no valid current Ruleset 1.11 B-to-A golden pair. Frozen historical examples are not being re-labelled. Thresholds are therefore **not justified**, and full-pipeline B-to-A acceptance remains open.

## Tests and deployment

- ML focused Adaptive V3 + CPQ tests: **30 passed**, including all five CPQ-specific tests.
- Backend `mvn -DskipTests compile`: **passed** after final code edits.
- Backend Spring integration previously applied Flyway through V62 in disposable Testcontainers PostgreSQL and two tests passed. After the final V62 change removing the assessment uniqueness restriction, Docker's VM had stopped, so a fresh migration and upgrade test of that exact final migration could not run. `mvn -DskipTests compile` passes.
- Frontend Step 6 suite: **72 passed**, including opt-in/no-write behavior. Full frontend suite now runs without `ENOSPC`: **334 passed, 7 failed, 8 errors**. The failures/errors are all in the untouched `video-detail.page.spec.ts` fixture path (`getCaptionVersionsByVideo` missing); the CPQ/Step 6 test module passes.
- ML full suite with explicit repository paths (`POMPOM_DATA_ROOT=../data PYTHONPATH=.`) runs without the collection error: **1,129 passed, 2 failed**. Three earlier failures were test environment path configuration and disappeared with the explicit data root. The remaining failures are in untouched `test_family2_escalation.py` (test expects `NOT_APPLICABLE`, evaluator returns `APPLICABLE`) and `test_story_quality.py` (expected `NEAR_DUPLICATE`, classifier returns `PARTIALLY_DISTINCT`). They do not exercise CPQ or the Adaptive V3 edits; these are unrelated existing failures, not changed in this task.
- Docker diagnosis: host filesystem currently has **7.2 GiB available**; Docker VM data directory consumes **64 GiB**. Docker Desktop backend log records `write .../log/vm/init.log: no space left on device`, Linux VM engine shutdown and recovery failure, followed by recovery action `Quit`. Docker context is `desktop-linux`; CLI `docker info` and `docker ps` time out, and local app endpoints refuse connections. This identifies Docker VM internal disk exhaustion rather than current host temp-space exhaustion. `open -a Docker` did not restore the engine. `deploy.sh --dry-run ml-service backend frontend` is valid, but the real deploy was not attempted.
- Actual deployed Step 6 browser verification, final database schema V62, runtime image identities, API persistence, production record integrity, and provider configuration cannot be verified while the engine is stopped. The existing browser tab only reflects the prior app page and was not treated as post-deployment evidence.
- No provider inference, candidate generation, prompt/story mutation, render, publishing, approval, or production database write was run during implementation.

## Remaining activation and product requirements

Before activating any grade, collect authorized diverse prompt examples and independent reviews; adjudicate disagreements; freeze the corpus; approve and validate thresholds with held-out error and profile/generator analysis; record a legitimate full-pipeline B-to-A golden acceptance; and obtain an authorized activation record. The current CPQ evaluator is a deterministic textual evidence preview, not a validated semantic quality judge. Human blind judgments provide calibration evidence; no real semantic model evaluator or real creative effectiveness has been demonstrated. No claim is made that Mimi currently has independent PASS fidelity evidence or qualifies for A/A+.

**Manual action required:** open Docker Desktop and resolve its stopped-engine disk-full recovery state. Preserve Docker volumes and databases; do not use Purge data or broad prune. Once the engine starts, inspect Docker's disk usage and recover only clearly unused build cache/images without removing volumes. Then rerun final V62 disposable migration/upgrade tests, backend integration tests, `./intelligence/scripts/deploy.sh ml-service backend frontend`, read-only runtime checks, and actual Step 6 browser acceptance. No operator action is taken here because Docker's recovery UI stopped the engine and storage cleanup may affect unrelated local images/build data.

The next calibration step, after deployment, is to obtain authorized, independently source-fidelity-reviewed prompt examples and blind quality judgments, then freeze held-out data and validate thresholds. Grading stays inactive until every activation condition is evidenced.
