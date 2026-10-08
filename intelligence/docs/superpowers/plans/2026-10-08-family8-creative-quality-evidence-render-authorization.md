# Family 8 — Creative Quality vs Evidence Completeness vs Render Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve three independent canonical facts—creative quality, evidence completeness, and render authorization—from ML assessment through the actual render admission boundary without reopening Families 1–7 or redesigning creative/policy semantics.

**Architecture:** Family 8 adds a canonical projection around already-produced Family 1–7 and Family 7 aggregation facts. It does not re-evaluate creative semantics. The projection keeps `creativeScore/creativeGrade`, `evidenceCompleteness/evaluationCoverage`, and `renderAuthorization/authorizationReasons` orthogonal; compatibility `grade/readiness` remain derived legacy fields. The contract is propagated losslessly through ML/API, backend DTO/PDF, frontend, and the final render queue admission policy.

**Tech Stack:** Python 3.14/pytest/PyYAML/FastAPI/Pydantic, Java 21 Spring/OpenPDF/JUnit, Angular/Vitest, existing deterministic Golden comparator and creative-render-service queue policy.

## Global constraints

- Families 1–7 remain frozen; no semantic extraction or aggregation redesign outside the approved Family 8 projection.
- Do not modify parser semantics, RuleEngine evaluator semantics, `RuleOutcome`, rulesets, Gold Truth for Families 1–7, or historical baselines.
- Do not add RULESET 1.8.
- Do not use performance, corpus role, Meta, publishing, or prediction data for creative quality or evidence completeness.
- Do not redesign creative-grade, readiness, or render authorization policy beyond making the approved three-axis facts and reasons explicit.
- `creativeGrade` is the canonical creative-quality projection; generic `grade` is compatibility-only.
- `evidenceCompleteness` and `evaluationCoverage` remain distinct from score and creative grade.
- `renderAuthorization` is the canonical permission-to-render projection; legacy readiness is compatibility-only.
- Null score is preserved as null and may render as an explicit N/A reason; it must never become zero.
- Parser/system failure maps to technical authorization blocking, not pending user evidence.
- Missing required evidence maps to pending-evidence authorization blocking, not creative failure.
- Multiple authorization reasons are preserved; the primary status must not erase them.
- Do not modify unrelated publisher-service-support or Meta working-tree changes.
- Do not commit until all tasks and cross-layer validation are approved.

## Canonical Family 8 contract

```python
@dataclass(frozen=True)
class AuthorizationReason:
    code: str
    source: str
    message: str
    references: tuple[str, ...] = ()

@dataclass(frozen=True)
class CreativeQualityProjection:
    score: float | None
    grade: str | None

@dataclass(frozen=True)
class EvidenceCompletenessProjection:
    status: str
    evaluation_coverage: float | None
    aggregation: dict[str, Any]
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class RenderAuthorizationProjection:
    status: str
    reasons: tuple[AuthorizationReason, ...]

@dataclass(frozen=True)
class Family8Assessment:
    creative_quality: CreativeQualityProjection
    evidence_completeness: EvidenceCompletenessProjection
    render_authorization: RenderAuthorizationProjection
    legacy_grade: str | None
    legacy_readiness: str | None
```

The exact Python placement may follow existing contract patterns, but the serialized keys must be stable:

```text
creativeQuality: { score, grade }
evidenceCompleteness: { status, evaluationCoverage, aggregation, reasons }
renderAuthorization: { status, reasons }
legacy: { grade, readiness }
```

Authorization status compatibility values remain:

```text
AUTHORIZED
BLOCKED_CREATIVE_FAILURE
BLOCKED_TECHNICAL_FAILURE
BLOCKED_PENDING_EVIDENCE
```

Reason codes must distinguish at minimum:

```text
CREATIVE_BLOCKER
CREATIVE_CRITICAL
EVIDENCE_PENDING
PARSER_TIMEOUT
SERVICE_ERROR
VISUAL_EVIDENCE_PENDING
INDEPENDENT_REVALIDATION_PENDING
```

The final admission rule is deterministic:

```text
no blocking reasons → AUTHORIZED
technical/system reason → BLOCKED_TECHNICAL_FAILURE
creative failure reason → BLOCKED_CREATIVE_FAILURE
pending required evidence reason → BLOCKED_PENDING_EVIDENCE
```

If multiple categories exist, retain all reasons and use the existing compatibility precedence only for the primary status string.

---

## Task 1: Synthetic orthogonality and boundary tests

**Files:**
- Create: `intelligence/ml-service/tests/test_family8_orthogonality.py`
- Do not change production code.

- [ ] Add fixtures for:
  1. `creativeGrade=A`, `evidenceCompleteness=PARTIAL`, `renderAuthorization=BLOCKED_PENDING_EVIDENCE`.
  2. Creative FAIL with complete evidence → `BLOCKED_CREATIVE_FAILURE`.
  3. Parser timeout/technical error → `BLOCKED_TECHNICAL_FAILURE`.
  4. All facts positive → `AUTHORIZED`.
  5. Null creative score → serialized null plus explicit aggregation reason.
  6. Multiple blocking categories → one primary status plus all reasons preserved.
- [ ] Assert creative grade does not change when only evidence completeness changes.
- [ ] Assert pending/technical evidence does not become creative FAIL.
- [ ] Assert legacy `grade/readiness` are independent compatibility fields, not canonical axis substitutes.
- [ ] Run the focused module and verify RED because the Family 8 projection does not exist yet.

## Task 2: Canonical ML Family 8 projection

**Files:**
- Modify: `intelligence/ml-service/app/assessment/pre_render_assessment.py` or add a focused projection module under `app/assessment/`.
- Reuse: `AggregationSummary`, existing `creative_grade`, `creative_score`, `evidence_completeness`, `render_authorization`.
- Test: Task 1 module plus additive assessment tests.

- [ ] Write a red test proving the projection returns the three canonical axes and legacy compatibility fields.
- [ ] Project creative quality from existing creative score/grade only.
- [ ] Project evidence completeness from Family 7 aggregation and existing completeness reasons without changing Family 7 formulas.
- [ ] Refactor `_render_authorization` only enough to expose additive `authorizationReasons[]`; preserve current status behavior and policy precedence.
- [ ] Classify parser timeout/system/provider failure as technical reason; classify missing visual/evidence gate as pending reason.
- [ ] Ensure `creative_grade`, `grade`, `readiness`, and render authorization values remain unchanged for existing fixtures except for the new additive reasons/projection.
- [ ] Run ML focused tests and existing assessment/Family 1–7 suites.

## Task 3: Nullable score propagation

**Files:**
- Modify: `intelligence/ml-service/app/quality/contracts.py` only where nullable score typing is required.
- Modify: `intelligence/ml-service/app/scoring/quality_scorer.py` only for null-safe score-card/trend handling.
- Modify: `intelligence/ml-service/app/api/quality.py` response types only in the approved API task, not during the canonical task.
- Test: ML score/assessment tests.

- [ ] Add tests for null overall/family scores with `NO_SCORED_ITEMS`, `NOT_APPLICABLE`, and technical-unavailable reasons.
- [ ] Ensure null remains null through scorer projections; no fallback zero.
- [ ] Keep existing PASS/FAIL severity-weighted score math unchanged when scored rows exist.
- [ ] Keep readiness/render policy output behavior unchanged; Family 8 only exposes facts.

## Task 4: Authorization reasons and deterministic derivation

**Files:**
- Modify: `intelligence/ml-service/app/assessment/pre_render_assessment.py`.
- Modify: existing authorization/evidence contract tests.
- Test: new authorization-reason matrix.

- [ ] Add tests for creative, pending-evidence, technical, and authorized cases.
- [ ] Preserve all concurrent reasons, including creative failure plus pending visual evidence.
- [ ] Ensure parser timeout reason carries `PARSER_TIMEOUT` provenance and is technical.
- [ ] Ensure missing required evidence carries `EVIDENCE_PENDING`/`VISUAL_EVIDENCE_PENDING` and is pending, not technical.
- [ ] Keep primary status compatibility exactly within the existing four status values.

## Task 5: ML API contract propagation

**Files:**
- Modify: `intelligence/ml-service/app/api/quality.py`.
- Modify: `tests/test_api_conversions.py` and new Family 8 API tests.

- [ ] Add nullable `overallScore` support where Family 7 permits null.
- [ ] Add serialized `creativeQuality`, `evidenceCompleteness`, `renderAuthorization`, and legacy compatibility fields.
- [ ] Preserve existing outcome lists and Family 7 aggregation fields.
- [ ] Add round-trip tests for null score, partial evidence, technical block, pending block, multiple authorization reasons, and authorized output.
- [ ] Do not alter parser/RuleEngine/scorer evaluator semantics.

## Task 6: Backend DTO and PDF propagation

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java` only for additive nullable/canonical fields.
- Modify: `QualityReportPdfService.java` for visible three-axis representation, null family rows, and authorization reasons.
- Modify: corresponding DTO/PDF tests.

- [ ] Preserve null overall/family scores through Jackson DTO round-trip.
- [ ] Render separate sections:
  - Creative quality: score/grade.
  - Evidence completeness: status/coverage/aggregation counts/reasons.
  - Render authorization: status and all reasons.
- [ ] Render null family score rows as explicit N/A with state/reason.
- [ ] Add DTO/PDF tests for Sticky Ball divergence and parser technical block.
- [ ] Keep existing five RuleOutcome lists lossless.

## Task 7: Frontend representation

**Files:**
- Modify: `intelligence/frontend/src/app/pages/quality-validator/quality-validator.component.ts`.
- Modify: `quality-validator.component.html`.
- Add/update focused representation specs.

- [ ] Add typed interfaces for the three canonical axes and authorization reasons.
- [ ] Render Creative Quality, Evidence Completeness, and Render Authorization as separate cards/sections.
- [ ] Make render authorization the primary render CTA/status.
- [ ] Scope legacy readiness explicitly as compatibility/creative readiness, or demote it from the primary status.
- [ ] Render null score as N/A plus aggregation reason.
- [ ] Preserve all status counts/reasons without collapsing UNKNOWN, NOT_EVALUATED, NOT_APPLICABLE, and SERVICE_ERROR.
- [ ] Run focused Angular tests and production build.

## Task 8: Actual render queue/admission enforcement

**Files:**
- Inspect/modify only the canonical validation evidence DTO and `ValidationEvidencePolicy.java` plus targeted queue tests.
- Do not modify render worker architecture or provider behavior.

- [ ] Add tests proving final-video admission honors canonical `renderAuthorization` and blocking reasons.
- [ ] Ensure technical failure, pending evidence, and creative failure are not silently treated as authorized.
- [ ] Ensure `AUTHORIZED` requires no blocking authorization reason and still satisfies existing identity/hash/version/expiry/visual gates.
- [ ] Preserve FIRST_FRAME-specific policy behavior.
- [ ] Run targeted creative-render-service queue tests.

## Task 9: Golden comparator and Family 8 Gold Review

**Files:**
- Modify: `intelligence/ml-service/app/golden/comparator.py` only for independent Family 8 policy assertions.
- Add/update Family 8 comparator tests and a read-only nine-asset Gold Review artifact.
- Do not alter Family 1–7 Gold Truth or baseline artifacts.

- [ ] Add independent assertions for `CREATIVE_GRADE`, `EVIDENCE_COMPLETENESS`, `RENDER_AUTHORIZATION`, and optional legacy readiness compatibility.
- [ ] Ensure mismatch in one axis does not overwrite or fail another axis automatically.
- [ ] Treat historical missing dimensions with provenance-verified `BASELINE_NOT_CAPTURED`; do not use it for runtime failures/corruption.
- [ ] Audit all nine frozen assets for the three-axis relationship, including Sticky Ball and parser-timeout Chair.
- [ ] Keep corpus role/performance out of all assertions.

## Task 10: Full regression and Family 1–7 freeze gate

- [ ] Run ML focused/full suites.
- [ ] Run backend DTO/PDF and render-queue tests.
- [ ] Run frontend focused tests/build.
- [ ] Run deterministic Golden gate.
- [ ] Verify no Family 1–7 semantic/policy regressions.
- [ ] Verify no parser/RuleEngine evaluator/ruleset/baseline/Meta/publisher changes.
- [ ] Stop for final human approval before declaring Family 8 frozen.

## Deferred and protected scope

- No Family 1–7 semantic changes.
- No parser semantic redesign.
- No RuleOutcome expansion for NOT_EVALUATED.
- No ruleset changes or RULESET 1.8.
- No creative-grade redesign.
- No readiness/render authorization policy redesign beyond the approved additive reasons/three-axis representation.
- No performance, Meta, public-comment, publisher, OpenArt, or render-worker redesign.
- No Family 9/10 work.


## Final approved locks before Task 1

- `evaluationState=NOT_EVALUATED` is not an authorization cause; explicit provenance/reason determines pending versus technical blocking.
- `authorizationReasons[]` is authoritative and retains all concurrent causes.
- Primary status precedence is `BLOCKED_TECHNICAL_FAILURE > BLOCKED_CREATIVE_FAILURE > BLOCKED_PENDING_EVIDENCE > AUTHORIZED`.
- Only `renderAuthorization.status == AUTHORIZED` may permit actual rendering; readiness never authorizes alone.
- Task 1 must establish these locks before any production projection or queue policy change.
