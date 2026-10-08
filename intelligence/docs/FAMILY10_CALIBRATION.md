# FAMILY 10: APPROVED / FROZEN

Validated 2026-10-08. Scope: generator-agnostic General Producibility. Comparison base: `79c369b` (the checkout before Family 10). Family 1–9 contracts remain frozen.

The read-only audit found existing `PRODUCIBILITY_001/002/003` RuleEngine evaluators and parser complexity/risk-factor evidence. Those approved rules and their authorization effects remain unchanged. Family 10 is an additional structured projection; legacy keyword complexity is not promoted into a canonical feasibility verdict.

## Canonical contract

| Status | Meaning |
| --- | --- |
| PRODUCIBLE | A sufficiently tracked visual plan has no detected material structural risk. |
| RISKY | At least one material production dependency or duration-relative dependent-state burden exists. |
| NOT_PRODUCIBLE | An essential HIGH dependency explicitly requires structural redesign. |
| UNKNOWN | Required tracked entities, actions, duration or applicable continuity evidence are insufficient. |
| NOT_APPLICABLE | The artifact explicitly requires no generative video. |

Risk levels are `LOW`, `MODERATE`, `HIGH`, `UNKNOWN`, `NOT_APPLICABLE`. Each dimension retains its reason, evidence references, materiality and redesign requirement. The projection also carries overall reasons, material risks, unknown dimensions, duration/source, duration-relative load and provenance. Missing historical projections display UNKNOWN; no missing value becomes zero or FAIL.

The 15 independent dimensions are:

1. ENTITY_LOAD
2. OBJECT_IDENTITY_CONTINUITY
3. CHARACTER_IDENTITY_CONTINUITY
4. FINE_MOTOR_PRECISION
5. CONTACT_PHYSICS_COMPLEXITY
6. OCCLUSION_HIDDEN_STATE
7. EXACT_COUNT_DEPENDENCY
8. MULTI_ENTITY_CONCURRENCY
9. TRANSFORMATION_COMPLEXITY
10. LIQUID_CLOTH_PARTICLE
11. SPATIAL_RELATIONSHIP_COMPLEXITY
12. CAMERA_ACTION_COUPLING
13. MULTI_SCENE_CONTINUITY
14. TEXT_LIP_SYNC_SYMBOL
15. SEGMENT_CONTINUITY

The evaluator uses structured dependencies, not legacy keyword complexity or historical performance class. Requirements may be supplied at plan or beat level through `objectContinuity`, `characterContinuity`, `fineMotorRequirement`, `contactPhysicsRequirement`, `occlusionRequirement`, `exactCountDependency`, `transformationRequirement`, `simulationRequirement`, `spatialRequirement`, `sceneContinuityRequirement`, `textRequirement`, `dialogueRequirement`, `symbolRequirement` and `segmentContinuityRequirement`. Optional requirements do not create material precision risks. Explicit independently moving entities, visibility/reappearance identity, exact stage quantities and camera/action synchronization supply additional evidence.

HIGH precision alone warns; blocking additionally requires `essential=true` and `requiresRedesign=true`. Nonmaterial moderate risks do not accumulate into automatic failure. Broad impossible physics, broad transformations, ordinary visible hand interaction, optional dialogue, simple camera movement and independent segments do not inherently fail.

Duration comes from a positive finite declared duration or valid beat-end inference. A frozen parser assumption is reported as unavailable evidence rather than reused as declared duration. Only explicitly dependent state changes contribute to density: more than 1 change/second is HIGH, more than 0.5 is MODERATE, otherwise LOW. These thresholds are duration-relative production heuristics, not beat-count or creative pacing rules. Tests cover 5, 6, 8, 12, 18, 25, 28, 30 and 65 seconds. Family 6 evidence is retained verbatim; only its severe action-concurrency evidence contributes a production consequence. Family 6 HIGH alone does not determine Family 10 status.

The evaluator is pure. It does not change creative scores/grades, completeness, render authorization, rule results or admission precedence. Existing required-rule authorization remains authoritative; Family 10 introduces no new authorization policy.

## Nine frozen Golden assets

**Two evidence paths are reported separately.** Actual frozen-parser production outputs are UNKNOWN for all nine assets because independent actor/object evidence is incomplete, with the existing Upside-Down Chair parser timeout also preserved. The following source-reviewed calibration results use explicit structured fixtures grounded in the original prompt hashes and quoted line ranges. They are not presented as automatic parser results and do not replace historical Gold Truth or baseline.

| Asset | Duration | Source-reviewed result | Material source requirement |
| --- | --- | --- | --- |
| Luca Sticky Ball | 15s | RISKY | Catch, hand transfer, cheek contact; reversible ball/wall deformation. |
| Luca Ball-Multiplying Crocodile | 15s | RISKY | Exact 1/3/6 stages, repeated catching/throwing, concurrent balls. Approximate final quantity is not an exact-count requirement. |
| Upside-Down Chair | 17s | RISKY | Chair/body contact and flip, large pose change, required lip synchronization. |
| Kiko And The Lamp That Hates Being Watched | 15s | RISKY | Mirror spatial relationship, mandatory lip synchronization. |
| Mimi And The Snack Box That Keeps Changing | 15s | RISKY | Mandatory lip synchronization, coordinated lid/reach. Hidden contents may change; unchanged hidden contents are not required. |
| Luca And The Box Cat | 15s | PRODUCIBLE | Broad sequential gestures and lift, short cat motion, stable camera. |
| Kiko And The Spot-Stealing Cat | 15s | RISKY | Exact target preemption and contact timing. |
| Mimi Vs. The Sneaky Door | 15s, three independent clips | RISKY | Character, environment, door state and camera continuity across explicit segments. |
| Luca And The Island Journal | 25.5s | RISKY | Same journal across scene changes; character continuity. Runtime/story quality does not determine production feasibility. |

All nine results are expected. Winners were not forced to PRODUCIBLE; negative historical labels were not forced to NOT_PRODUCIBLE. Every applicable dimension, moderate/high risk, source reference and expected-result check is recorded in `../data/golden/pompom-golden-v1/reports/family10/family10-review.json`.

## Production files changed

All paths below are relative to `intelligence/`.

| File | Change |
| --- | --- |
| `ml-service/app/quality/general_producibility.py` | Pure Family 10 evaluator and parser-evidence wrapper. |
| `ml-service/app/assessment/pre_render_assessment.py` | Additive canonical assessment projection. |
| `ml-service/app/api/quality.py` | Nullable API projection field with lossless nested payload. |
| `ml-service/app/golden/deterministic_runner.py` | Additive production canonical snapshot evidence, including unavailable-parser UNKNOWN. |
| `ml-service/app/golden/family10.py` | Whole-projection comparator for status, dimensions, reasons, nulls and provenance. |
| `ml-service/scripts/run_family10_golden_review.py` | Source/hash verification, nine-asset review and conjunction with the existing release gate. |
| `backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportPdfService.java` | Separate canonical status and material-first dimensions, duration and source provenance; keep each risk with its reason/references. |
| `frontend/src/app/pages/quality-validator/family10-representation.ts` | Canonical types and material-first ordering without mutation. |
| `frontend/src/app/pages/quality-validator/general-producibility.component.ts` | Separate status, visible material risks and expandable complete evidence. |
| `frontend/src/app/pages/quality-validator/quality-validator.component.ts` | Additive typed input/import. |
| `frontend/src/app/pages/quality-validator/quality-validator.component.html` | Dedicated Family 10 panel adjacent to existing axes. |

Existing backend `QualityReportDto.preRenderAssessment` and snapshot serialization already preserve arbitrary nested evidence. They required no production schema change. `frontend/tsconfig.spec.json` enables JSON fixture imports only for tests.

`frozen-semantic/family10/requirements.json` contains source-reviewed fixtures. `api-contract.json` contains nine actual ML API conversions used by Java DTO/snapshot/PDF and Angular tests. ML tests check that these saved API assessment payloads still equal current conversion output. These artifacts are explicitly scoped to Family 10 and separate from frozen Family 1–9 truth.

## Tests and validation

Synthetic contracts were run RED before evaluator implementation (missing evaluator module), and PDF/UI transport contracts were run RED before corresponding representations. Additional RED regressions covered character/object occlusion identity and independent segments.

| Added test file | Tests |
| --- | ---: |
| `ml-service/tests/test_family10_general_producibility.py` | 16 |
| `ml-service/tests/test_family10_risk_contract.py` | 30 |
| `ml-service/tests/test_family10_representation.py` | 9 |
| `ml-service/tests/test_family10_golden_review.py` | 10 |
| `ml-service/tests/test_family10_freeze_gate.py` | 4 |
| `backend/src/test/java/com/pompomhills/intelligence/quality/Family10RepresentationTest.java` | 5 |
| `backend/src/test/java/com/pompomhills/intelligence/quality/Family10GoldenTransportTest.java` | 9 |
| `frontend/src/app/pages/quality-validator/family10-representation.spec.ts` | 16 |

The gate mutation tests reject canonical/API drift, changed source-reviewed expectations and an existing policy regression even when other Family 10 checks pass. Representation tests exercise all five statuses, null duration/scores, UNKNOWN/N/A, unchanged creative Grade A and authorization, source hashes and all 15 dimensions. Nine source-reviewed API payloads pass through actual Java DTO/snapshot/PDF and Angular rendering. PDF text is checked programmatically; the generated Sticky Ball PDF was also rendered and inspected visually, including continuation pages.

| Validation | Result |
| --- | --- |
| Focused Family 10 ML | 69 passed |
| Family 6 | 19 passed |
| Family 7 | 24 passed |
| Family 8 | 16 passed |
| Family 9 ML | 11 passed |
| Combined Family 6–10 focused run | 139 passed |
| Full ML suite | 641 passed, 154 existing dependency/deprecation warnings |
| Relevant backend DTO/snapshot/PDF/validation tests | 47 passed |
| Angular Family 9/10 representation | 21 passed |
| Full frontend | 44 passed, 9 pre-existing unrelated failures |
| Frontend production build | PASS; existing bundle/style budget warnings |
| Render authorization regression | 29 passed (`ValidationEvidencePolicyTest`, `HttpIntelligenceValidationEvidenceClientTest`) |
| Ruff, new Family 10 Python surfaces/tests | PASS |
| Ruff, touched existing Python | API clean; unchanged 61 assessment + 10 deterministic-runner issues, zero new issues versus comparison base |
| Strict mypy, three Family 10 source surfaces, `--follow-imports=silent` | PASS |
| Strict mypy with imported legacy code followed | Same 28 inherited errors in six files as comparison-base imports; zero new errors |
| Targeted Spotless apply/check | PASS for the PDF service and two Family 10 Java tests |
| `git diff --check`, including comparison-base diff | PASS |
| Protected semantic surface diff | Empty |

Backend totals are the explicitly requested relevant subset, not a claim that every repository backend test was executed. Frontend failures remain in `creative-intelligence.service.spec.ts` (2) and `video-detail.page.spec.ts` (7). The same nine failed before implementation. Existing global analysis status/HTTP mock debt was not repaired. Build warnings include 929.79 kB initial bundle, existing 19.97 kB validator styles and 5.79 kB render-dashboard styles.

## Freeze gate

| Gate evidence | Result |
| --- | ---: |
| Golden assets processed | 9 |
| Existing Golden assertions | 323 |
| Additional Family 10 assertions | 248 |
| Family 10 failed assertions | 0 |
| New semantic regressions | 0 |
| Unexpected policy regressions | 0 |
| Family 9 representation mismatches | 0 |
| Family 10 representation mismatches | 0 |
| Golden release gate | PASS |
| Family 10 release gate | PASS |

Existing Golden debt remains explicitly visible: 5 semantic failures, 61 review-required assertions, 52 unchanged known issues and 4 expected approved policy changes; 28 assertions improve against the historical baseline. The approved existing gate distinguishes this debt from new regressions. Family 10 does not alter that policy.

Reproduction from `intelligence/ml-service`:

```sh
.venv/bin/python -m pytest -q tests/test_family10*.py tests/test_family[6789]*.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_pompom_golden_ci.py --manifest ../data/golden/pompom-golden-v1/manifest.yaml --baseline ../data/golden/pompom-golden-v1/baselines/v1.7/baseline.json --ruleset ../data/rules/RULESET_1.7.yaml --truth ../data/golden/pompom-golden-v1/truth/gold_truth.yaml --policy ../data/golden/pompom-golden-v1/policy/policy_expectations_v1.7.yaml --reports ../data/golden/pompom-golden-v1/reports/family10
.venv/bin/python scripts/run_family10_golden_review.py --golden-root ../data/golden/pompom-golden-v1 --reports ../data/golden/pompom-golden-v1/reports/family10
.venv/bin/ruff check app/quality/general_producibility.py app/golden/family10.py scripts/run_family10_golden_review.py tests/test_family10*.py
.venv/bin/mypy --strict --follow-imports=silent app/quality/general_producibility.py app/golden/family10.py scripts/run_family10_golden_review.py
```

The optional review CLI `--api-contract` regenerates only the scoped cross-stack test fixture. Normal validation leaves it untouched.

Family 1–9 were not reopened. Parser behavior, RuleEngine mathematics, creative-grade policy, authorization precedence, Family 9 representation semantics, rulesets, historical labels/baselines and provider/publisher integrations are unchanged. Fifteen seconds was not reintroduced as a universal rule. No Seedance 2.5 behavior, performance or virality logic was added. Work stops at Family 10 freeze; no post-Family work was started.
