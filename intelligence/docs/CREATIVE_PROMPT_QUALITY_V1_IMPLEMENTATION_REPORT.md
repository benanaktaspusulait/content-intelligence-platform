# Creative Prompt Quality V1 implementation report

Date: 2026-10-15  
Status: `CPQ_ENGINE_IMPLEMENTED_PREVIEW_ONLY`; deployment and live UI verification pending.

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
- Backend Spring integration startup previously applied Flyway migration through V62 in a disposable Testcontainers PostgreSQL (two integration tests passed in that run). A later full `mvn test` run did not complete: its ephemeral database became unavailable during the suite. The last small migration change removing a uniqueness restriction to preserve append-only reassessments has not been replayed against PostgreSQL.
- Frontend Step 6 suite: **72 passed**, including opt-in/no-write behavior. Frontend full suite could not complete because the host ran out of temporary filesystem space (`ENOSPC`); unrelated `video-detail` failures also appeared in the first partial full-suite run. No full-suite pass is claimed.
- ML full run (excluding the separate import blocker) executed **1,122 passed / 5 failed**. The failures were existing fixture-path, escalation, or story-quality contract issues outside CPQ; the full unfiltered suite also has an existing collection error in `tests/test_family10_freeze_gate.py` (`ModuleNotFoundError: scripts`).
- `deploy.sh` deployment and actual browser inspection have not yet been completed. Docker Desktop's CLI endpoint stopped responding during Testcontainers use; `docker info`/`docker ps` timed out and local app endpoints stopped accepting connections. `deploy.sh --dry-run` produced the intended ml-service/backend/frontend plan; the real deploy was deliberately not attempted while the Docker engine was unresponsive.
- No provider inference, candidate generation, prompt/story mutation, render, publishing, approval, or production database write was run during implementation.

## Remaining activation and product requirements

Before activating any grade, collect authorized diverse prompt examples and independent reviews; adjudicate disagreements; freeze the corpus; approve and validate thresholds with held-out error and profile/generator analysis; record a legitimate full-pipeline B-to-A golden acceptance; and obtain an authorized activation record. The current CPQ evaluator is a deterministic textual evidence preview, not a validated semantic quality judge. Human blind judgments provide calibration evidence; no real semantic model evaluator or real creative effectiveness has been demonstrated. No claim is made that Mimi currently has independent PASS fidelity evidence or qualifies for A/A+.

The next smallest product step is to deploy the inactive, backward-compatible implementation, inspect the actual Step 6 interface, and then collect independently authorized calibration examples through the implemented workflow. Grading remains off until all activation evidence is present.
