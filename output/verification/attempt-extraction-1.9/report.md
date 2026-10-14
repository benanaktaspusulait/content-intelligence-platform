# False character-attempt extraction — completed

**ATTEMPT_EXTRACTION_DEFECT_FIXED**. Ruleset **1.9** deployed and verified through the official backend/ML evaluation workflow and the live Step6 page.

## Exact failure path

Raw candidate prompt → `_parse_timeline_beats` → `_create_beat_from_description` → full beat content (including square-bracket camera directives) → `_resolve_attempt_evidence` → `_NATURAL_ATTEMPT_PHRASES` matches **keep the** → takes capture2 **THE** as primaryVerb → isAttempttrue → `attempt_evidence` count3 rather than2 → ATTEMPT_001 PASS100 rather than FAIL0 → concept family mean61.6667→95 → `100×0.12/(3×0.96)=4.1667` extra overall points. The camera instruction did not describe an extra character action.

## Shared correction

New `actor_attempts.py` implements the versioned actor-source-bound-v2 contract. It identifies actors from source declarations/reference contracts, recognizes physical action predicates and explicit intent/continuation/recovery/control relationships, and binds exact action, actor and verb spans. Positive actor/action grammar excludes articles and camera subjects without a Mimi-specific exception or a stopword-only workaround.

Camera/composition directives are retained as `productionInstructions`; actual actor clauses remain `characterActions`, including inside mixed descriptions and brackets; object outcomes are retained as `physicalConsequences`. Per-attempt evidence includes actor, actor reference/span, action/span, primary verb/token span, relationship, classification and confidence. Missing/unmatched source evidence cannot become an attempt. Repeated descriptions inside one beat remain one attempt; duplicate same-time source events cannot inflate counts. Genuine ongoing pulling, explicit recovery, direct repeated actions and distinct physical attempts remain detectable.

Source actor resolution also avoids reading CHARACTER REFERENCE as the actor name, allowing genuine existing Luca multi-attempt examples to retain their actual source-established actor. This behavior is scoped to the new parser policy; old parser semantics remain explicitly available for1.7/1.8.

## Incorrect and corrected Candidate A opening

Before: actorMimi, isAttempttrue, primaryVerbTHE, attemptSourceNATURAL_LANGUAGE_ATTEMPT; the matched instruction was “keep the cabinet and her finger visible together in the same frame”.

After: opening is a source-observed CHARACTER_ACTION (REACH), not an extra attempt; isAttemptfalse, primaryVerb empty, attemptEvidenceNOT_AN_ATTEMPT. The camera instruction is retained separately with its exact source span. The valid attempts are beat2 **Mimi / PEEL** and beat3 **Mimi / PULL**, each with source-bound proof. See candidate-a-action-camera-proof.json and before-after.json.

## Files modified

- `intelligence/ml-service/app/parser/actor_attempts.py`: shared grammar/classification, source binding and event deduplication.
- `intelligence/ml-service/app/parser/prompt_parser.py`: versioned delegation, exact provenance, declared-actor resolution and versioned read-only source projection.
- `intelligence/ml-service/app/workflow/review.py`, `workflow/api.py`:1.9 selection and version-bound evaluation fingerprint/contracts.
- `intelligence/ml-service/app/api/quality.py`, `autofix/iteration_loop.py`, `golden/deterministic_runner.py`: use the selected ruleset's parser policy consistently. No auto-fix/generation endpoint was run in production.
- `intelligence/ml-service/app/rules/rule_engine.py`: default current ruleset1.9; scoring arithmetic/weights/severities/thresholds unchanged.
- `intelligence/data/rules/RULESET_1.9.yaml`, `versions.yaml`: governed breaking parser policy release, inherited1.8 rule registry; no historical YAML overwrite.
- `intelligence/backend/.../workflow/WorkflowService.java`: candidate source-plan extraction pinned to the same authoritative ruleset as its baseline.
- Parser/registry release tests and backend integration coverage. Frontend application code unchanged in this task.

## Regression coverage

500 parser/canonical/legacy-attempt/golden/Step5/Step6/workflow tests passed;13 additional auto-fix/regression-contract tests passed;22 backend tests passed with all real deployed-ML/Testcontainers and mocked-provider cases enabled,0skipped;69 focused frontend tests passed. New parser cases cover cabinet/finger camera directives, genuine keeps-pulling/tries-to-peel/pulls-again, mixed descriptions, moving cameras, bracket actions, invalid THE verbs, distinct attempts, duplicate same-event descriptions, genuine golden multi-attempt structures, markers, Unicode offsets and pronoun actor context.

The previously known unrelated Island Journal escalation test was explicitly deselected in the green scoped run; it was not fixed or represented as passing. Existing unrelated full frontend failures remain outside scope.

Golden1.7 and1.8 were rerun across all nine frozen assets: historical report, dimensions, canonical evidence, aggregation and IR fields match their prior snapshots exactly. New1.9 snapshots are separate and retain their actual per-asset ruleset fingerprints; the legacy baseline harness wrapper label remains hardcoded1.7 and is not used as the actual evaluated-version evidence. No frozen prompt, truth or policy expectation was rewritten. The archived golden discrepancies documented in the prior release were not relabeled as passing.

## Before/after and downstream rules

| Input |1.7 historical|1.8 historical|1.9 official|ATTEMPT_001 under1.9|
|---|---:|---:|---:|---|
|Original PromptID10|85/B|82.80/B|82.80/B|FAIL,2actual attempts|
|Candidate A|85/B|86.97/B|82.80/B|FAIL,2actual attempts|
|Candidate B|85/B|82.80/B|82.80/B|FAIL,2actual attempts|

Scores were computed from saved inputs, not hardcoded to the diagnostic reference. A loses only the unsupported ATTEMPT_001 PASS; Original/B numeric results are unchanged. Remaining45 rule outcomes are unchanged. Attempt count/active ratio, diversity/strategy inputs, dominant-verb ratios, mini-story strategy-change metrics and passive-time/momentum diagnostics now use the corrected upstream evidence. Their classifications remain unchanged for these three prompts: mini-story, beat density and temporal gate stillPASS; semantic diversity/executability remainUNKNOWN; momentum remainsFAIL. No downstream rule was disabled or given a candidate-specific exception.

## Official deployment and immutable records

New saved analysis: **38a57f84-b61a-470c-8342-cd522bdbd38e**. New saved comparison: **1f4ef83c-d665-4c85-8fd1-1657855215c5**. Content10 / immutable PromptID10 / Ruleset1.9 /46 rule records. Official POST `/api/v1/intelligence/workflow/review` saved the current analysis; local-only candidate revalidation reused the original durable source/provider comparison without dispatching Creative Optimization. Candidate reviews are embedded in the new immutable comparison. Their exact prompts were not changed.

ML and backend were rebuilt/deployed using `intelligence/scripts/deploy.sh`; frontend restarted to resolve the backend. Readiness reports1.9; image/HTTP checks passed. Live Step6 shows82.8/B for all three and no false A score delta. Selection and approval are null.1.8 comparison evidence is stale and approval-ineligible.

Checksums for both historical analyses, both previous comparisons, original provider evidence, every Content10 prompt text and total creative-role count match before/after. No paid provider calls, new candidate generation, prompt/story mutation, image/video generation, publishing, direct production SQL updates, automatic approval, commit or push command occurred.

## Remaining opportunities and limits

A's joint cabinet/finger framing remains a plausible source-faithful staging hypothesis; B's continuous peel/consequence view and two/four/eight exposure remain plausible execution hypotheses. Neither is proven superior by these text scores. Preserve the approved event ordering, doubling mechanic and messy-cabinet ending. Do not add attempts solely to satisfy a threshold.

The separate motion substring issue (“no” inside note/notes), visual-state granularity and related legacy diagnostics are not repaired by this attempt-only change and remain review items. F8 is stillBLOCKED_PENDING_EVIDENCE: verified Mimi reference and accepted start frame are absent. Actual visual quality, generator success and audience response remain unverified. No render authorization is granted.
