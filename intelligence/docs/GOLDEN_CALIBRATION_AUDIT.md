# Golden Calibration Infrastructure Audit

**Audit status:** COMPLETED

**Scope:** Existing prompt-quality golden tests, parser/canonical evidence, immutable rulesets, persistence, reports, frontend/PDF representation, CI, and performance isolation.

## Status Matrix

| Area | Status | Evidence / decision |
|---|---|---|
| Luca deterministic golden path | EXISTS | `ml-service/tests/test_prompt_quality_consistency_golden.py` and `tests/fixtures/luca_sticky_ball_prompt.txt` |
| Parser → canonical evidence → RuleEngine → assessment → scorer/API | EXISTS | Existing production pipeline and 432-test ML suite |
| Immutable RULESET 1.5/1.6/1.7 | EXISTS | YAML `extends` chain and ruleset-version tests |
| Nine-asset authoritative cohort | EXISTS | Frozen in `data/golden/pompom-golden-v1/manifest.yaml` |
| Independent Gold Truth | EXISTS | `data/golden/pompom-golden-v1/truth/gold_truth.yaml` |
| Policy expectation separation | EXISTS | `policy/policy_expectations_v1.7.yaml` |
| v1.7 baseline snapshot | EXISTS | `baselines/v1.7/baseline.json` |
| Semantic/policy comparator | EXISTS | `app/golden/comparator.py` and generated regression report |
| Full-stack fingerprint | PARTIAL | Existing parser/canonical/ruleset/assessment/scoring identities captured; semantic prompt/schema, renderer, and frontend identities are explicit `UNKNOWN` until versioned |
| Performance isolation architecture test | EXISTS | `tests/test_golden_architecture_boundary.py`; forbidden imports and input fields are guarded |
| Cross-layer representation contract | EXISTS | Shared fixture plus existing scorer/PDF/frontend percent tests |
| Source-controlled CI gate | EXISTS | `.github/workflows/pompom-golden.yml` runs the deterministic gate without provider credentials |
| Calibration persistence | PARTIAL | Baseline/report artifacts are durable; a database calibration-run entity is intentionally deferred until run-history requirements exist |
| Root `/docs` tracking | STALE/RISK | Root `/docs` is ignored; critical calibration docs are stored under tracked `intelligence/docs` |

## Hard Boundaries

- Corpus roles are manifest metadata and are never passed into the prompt engine.
- Prompt files are copied byte-for-byte and identified by SHA-256.
- Performance tables and platform outcomes are not read by the Golden runner.
- Gold Truth is authored from source evidence, not current engine output.
- Policy Expectations are ruleset/version scoped and can change independently of structural truth.
- The baseline preserves parser incompatibilities and current policy defects rather than silently repairing them.

## Current Gaps Kept Explicit

- Database `contents`/`prompt_versions` IDs are not available for the mounted cohort in the current local environment; mounted path + hash is the canonical source identity for V1.
- The bounded parser discovery probe used a 12-second limit per file. Four candidate sources in the broader curation pool exceeded that limit: Giant Spoon, Upside-Down Chair, Wrong Shoes, and Running Backpack. Of the frozen nine, only Upside-Down Chair carries `PARSER_DISCOVERY_TIMEOUT` in the v1.7 baseline; the other three are alternates and are not baseline assets.
- Box Cat and Spot Cat contain complete prose prompts but do not match the current timestamp-labelled parser format.
- Semantic prompt/schema, report-renderer, and frontend representation versions do not currently exist as dedicated runtime identities and are recorded as `UNKNOWN`.

## Future Prediction Boundary

The calibrated pre-render output remains a canonical creative feature snapshot. Historical platform outcomes may be joined only after creative feature generation, in a separate prediction dataset. No prediction model is part of Golden Calibration V1.
