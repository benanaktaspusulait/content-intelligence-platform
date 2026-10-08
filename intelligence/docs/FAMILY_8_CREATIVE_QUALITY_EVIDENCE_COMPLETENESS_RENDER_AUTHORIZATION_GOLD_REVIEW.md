# FAMILY 8 — CREATIVE QUALITY vs EVIDENCE COMPLETENESS vs RENDER AUTHORIZATION
## Read-only Gold Review

**Review status:** READ-ONLY AUDIT — IMPLEMENTATION NOT STARTED  
**Current calibration state:** Families 1–7 frozen/approved; Family 8 not started  
**Scope:** Determine whether creative quality, evidence completeness, readiness, and render authorization remain semantically independent and lossless across ML, API, backend/PDF, frontend, Golden, and render-queue boundaries.

No production behavior, parser, RuleEngine evaluator, scorer, ruleset, policy, Gold Truth, baseline, Family 1–7, Meta, or publisher code was changed by this audit. This report is the only requested Family 8 artifact.

## Executive summary

The system already has three visibly separate projections:

```text
Creative quality
  QualityReport.overall_score
  family_scores
  creative_grade

Evidence completeness
  assessment_coverage_percent
  evidence_completeness
  UNKNOWN / SERVICE_ERROR gaps

Render authorization
  render_authorization
  first-frame/silhouette/independent-revalidation gates
  final validation evidence policy
```

That separation is real but incomplete:

- Creative grade intentionally excludes evidence gaps, while the general `grade` and readiness path considers coverage and service errors.
- Render authorization independently checks creative failures, technical failures, pending visual evidence, report readiness, independent revalidation, identity/hash/version/expiry, and visual gates.
- Therefore a plan can be creative grade `A` / readiness `READY_TO_RENDER` while final render authorization is `BLOCKED_PENDING_EVIDENCE`; Sticky Ball is the current concrete example. This is an expected divergence, not automatically a contradiction.
- Family 7 aggregation now exposes explicit score/coverage/count facts, but current API/backend/frontend contracts still have older nullable/typed assumptions. `QualityReportResponse.overall_score` remains non-nullable while zero-scored aggregation can now be null internally.
- Backend DTO null-to-empty normalization and PDF family-score filtering can hide “no score” versus “zero score” and “missing row” versus “empty list” unless Family 8 makes the representation contract explicit.
- Golden comparator policy projection compares creative grade, creative score, coverage, render authorization, and severity counts separately from structural Gold Truth. That is the right boundary, but historical reports and newer Family 5/6 dimensions are not yet uniformly regenerated under one representation version.
- Family 8 should not redesign grade, readiness, or render policy until the facts and relationships are explicitly modeled and human-approved.

## 1. Authoritative runtime surfaces

### Creative quality

The ML pre-render path derives:

- `QualityReport.overall_score` from weighted non-null family scores;
- `QualityReport.family_scores` and `family_assessments` from RuleEngine aggregation;
- `assessment.creative_score` as a rounded projection of `report.overall_score`;
- `assessment.creative_grade` from evaluated creative judgments only;
- `assessment.grade` from coverage, service errors, blockers, criticals, failures, and warnings.

Relevant code:

```text
intelligence/ml-service/app/rules/rule_engine.py
  _calculate_family_scores()
  _calculate_family_assessments()
  _calculate_overall_score()
  _generate_report()

intelligence/ml-service/app/assessment/pre_render_assessment.py
  _creative_grade()
  _grade()
  build_pre_render_assessment()
```

`_creative_grade()` excludes `UNKNOWN`, `SERVICE_ERROR`, evidence-gap FAILs, and `NOT_APPLICABLE`. This prevents “we could not tell” from becoming a creative failure.

`_grade()` and readiness use coverage/service-error/blocker/critical signals. Thus `grade` and `creative_grade` are intentionally different concepts.

### Evidence completeness

The current top-level assessment computes:

```text
applicable = evaluations excluding NOT_APPLICABLE
evaluated = applicable excluding evidence gaps
assessment_coverage_percent = evaluated / applicable * 100
```

Family 7 adds a separate aggregation object with explicit:

```text
scoredCount
coverage denominator
semantic evaluation coverage
UNKNOWN
NOT_EVALUATED
NOT_APPLICABLE
SERVICE_ERROR counts
aggregationState
```

The two coverage concepts are not identical:

- existing assessment coverage is a policy/readiness-oriented percentage;
- Family 7 `evaluationCoverage` is a status-aware semantic aggregation fact.

Family 8 must not silently rename or merge them.

### Render authorization

`pre_render_assessment._render_authorization()` distinguishes:

```text
BLOCKED_TECHNICAL_FAILURE
BLOCKED_CREATIVE_FAILURE
BLOCKED_PENDING_EVIDENCE
AUTHORIZED
```

It considers:

- evaluated creative FAILs that are not evidence gaps;
- SERVICE_ERROR technical failures;
- pending first-frame visual verification;
- pending silhouette verification;
- independent validation revalidation;
- final report status/blocker/critical policy readiness.

The creative failure list excludes evidence gaps, so missing evidence normally enters pending evidence rather than creative failure.

The final render queue has a second authoritative policy boundary in:

```text
intelligence/creative-render-service/src/main/java/com/pompom/creative/queue/ValidationEvidencePolicy.java
```

For final-video jobs it requires:

- validation status `RENDER_READY`;
- zero blockers;
- zero criticals;
- independent revalidation;
- content/prompt identity match;
- valid prompt SHA-256 and optional request hash match;
- required ruleset/semantic version identities;
- unexpired evidence;
- final visual evidence with matching first-frame/silhouette asset and evidence-set identities.

This policy does not simply consume `creative_grade`. It is a technical/evidence authorization gate.

## 2. Current independence and leakage findings

### Correct separation already present

1. `creative_grade` excludes UNKNOWN/SERVICE_ERROR evidence gaps.
2. `evidence_completeness` reports gaps separately.
3. `render_authorization` has separate creative, technical, pending-evidence, and visual-gate paths.
4. RuleEngine `SERVICE_ERROR` is separate from FAIL and forces overall technical status.
5. Family 7 aggregation exposes score and coverage separately.
6. Golden comparator policy projection is separate from structural Gold Truth.
7. The render queue validates immutable evidence identity/version/expiry independently from prompt creative labels.

### Leakage or ambiguity requiring Family 8 calibration

1. **Grade versus coverage:** `grade` can become `INCOMPLETE` from coverage below 80 or service error, while `creative_grade` remains a creative-only judgment. Both are exposed but their relationship is not a versioned contract.
2. **Readiness versus render authorization:** Sticky Ball currently demonstrates `creative_grade=A` and `readiness=READY_TO_RENDER` while `render_authorization=BLOCKED_PENDING_EVIDENCE`. This is documented as a valid three-outcome state, but the user-facing contract does not name the precedence/relationship explicitly.
3. **Null score versus zero score:** Family 7 can produce `overall_score=None` for zero scored items, while API `QualityReportResponse.overall_score` is typed as a non-null `float`, backend entity/report fields historically assume a numeric score, and frontend score consumers expect a number. This is a representation risk, not yet a policy decision.
4. **Assessment coverage versus Family 7 evaluation coverage:** both facts may appear in a report with different denominators. Without labels and provenance, consumers may interpret them as the same percentage.
5. **PDF family score omission:** `QualityReportPdfService.addFamilyScores()` filters null family scores. A family with no scored evidence can disappear instead of being shown as `N/A`/`NO_SCORED_ITEMS`.
6. **Backend null normalization:** `QualityReportDto` converts null rule lists/maps to empty collections/maps. This protects old consumers but loses absent-vs-empty provenance unless the aggregation summary carries explicit state.
7. **Frontend taxonomy:** the quality validator types the five Python outcomes but has no explicit `NOT_EVALUATED` row/state. Some unscored family presentation groups UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR under generic “not evaluated” language.
8. **Golden history:** committed v1.7 reports predate Family 5 per-rule and Family 6 canonical dimensions. The comparator now supports non-gating historical absence, but committed report artifacts do not uniformly expose the newer aggregation facts.

## 3. Sticky Ball divergence audit

Observed baseline/current assessment facts for Sticky Ball:

```text
creative score:        85.0
creative grade:        A
readiness:              READY_TO_RENDER
evidence completeness: PARTIAL
assessment coverage:   80%
render authorization:  BLOCKED_PENDING_EVIDENCE
```

The render authorization is blocked by pending visual/independent evidence gates, not by an evaluated creative FAIL. This is the canonical Family 8 boundary case:

```text
creative quality = acceptable/strong
semantic evidence coverage = incomplete/partial
render authorization = blocked pending technical/visual evidence
```

Family 8 must decide how this is represented and explained, not silently collapse the three facts into one status.

## 4. Nine Golden asset policy facts

Available baseline/current artifacts show the following representative pattern:

| Asset | Creative score/grade | Evidence coverage | Render authorization | Family 8 relevance |
|---|---|---|---|---|
| Sticky Ball | 85.0 / A | 80%, PARTIAL | BLOCKED_PENDING_EVIDENCE | Quality strong while authorization remains blocked. |
| Ball-Multiplying Crocodile | 61.818 / F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Creative failure and incomplete evidence coexist. |
| Upside-Down Chair | null / no assessment | no coverage | no authorization object | Parser timeout is not creative failure or zero score. |
| Lamp | 49.545 / F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Explicit creative failures plus evidence gaps. |
| Snack Box | 49.545 / F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Same separation requirement as Lamp. |
| Box Cat | 38.295 baseline / 61.818 current, F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Generic baseline drift is policy-visible but Family 8 must not hide provenance. |
| Spot Cat | 38.295 baseline / 61.818 current, F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Same parser/provenance drift boundary. |
| Sneaky Door | 38.295 / F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Multi-clip evidence gap and creative failure are separate. |
| Island Journal | 20.909 / F | 80%, PARTIAL | BLOCKED_CREATIVE_FAILURE | Long-form/semantic gaps must not be silently treated as score zero. |

Corpus role and performance data were not used for these observations.

## 5. Cross-layer representation audit

### ML/API

`QualityReportResponse` exposes:

```text
overall_score
status
family_scores
family_assessments
passed_rules
failed_rules
unknown_rules
not_applicable_rules
service_errors
pre_render_assessment
```

`PreRenderAssessmentResponse` now also exposes Family 7 aggregation facts. However, the top-level `overall_score` type remains non-nullable while zero-scored Family 7 aggregation can be null internally. This is a known cross-layer boundary for a later approved representation task.

### Backend DTO

`QualityReportDto` preserves `preRenderAssessment` as a generic map and separately exposes rule lists, family scores, family assessments, and provenance. Null collections normalize to empty collections. This is backward-compatible but not fully lossless for absence without an explicit aggregation object.

### PDF

The current PDF shows:

- score/status card;
- pre-render grade/readiness/coverage/verdict;
- Family 7 evaluation aggregation summary;
- PASS/FAIL/UNKNOWN/NOT EVALUATED/NOT APPLICABLE/SERVICE ERROR counts;
- family scores only when non-null;
- failed rules and validation evidence.

Null family scores are currently filtered from the family score table. Family 8 must decide whether `NO_SCORED_ITEMS` families should render explicit `N/A` rows.

### Frontend

The quality validator now displays the Family 7 aggregation object separately from creative grade, evidence completeness, and render authorization. It still has older typed rule outcome unions and no broad platform-wide `NOT_EVALUATED` contract.

## 6. Current Golden comparator boundary

`app/golden/comparator.py::_policy_projection()` compares policy outputs independently:

```text
creativeGrade
creativeScore
evidenceCompleteness
renderAuthorization
blockers
criticals
warnings
unknowns
notApplicable
baselineStatus
```

This is the correct structural/policy separation direction. Family 8 must not turn those policy fields into Gold Truth creative semantics. It should instead define whether the three dimensions are displayed and compared as independent facts, and how null/partial states are classified.

## 7. Family 8 semantic boundary hypothesis

Family 8 owns the relationship contract between three already-produced facts:

```text
Creative Quality
  What validly evaluated creative rules say about the plan.

Evidence Completeness
  How much relevant evidence was available/evaluated and what remains unknown,
  unevaluated, unavailable, or technically failed.

Render Authorization
  Whether the current evidence/policy/visual gates permit a render operation.
```

Family 8 must not:

- reinterpret Family 1–7 semantic evidence;
- change scorer severity math;
- turn evidence gaps into creative failures;
- make authorization equal to creative grade;
- make high creative quality imply render authorization;
- use performance/corpus role as creative evidence;
- redesign render policy before the facts are represented and approved.

## 8. Human decisions required before implementation

1. Should `creative_grade`, `grade`, `readiness`, `evidence_completeness`, and `render_authorization` remain separate fields with a documented relationship matrix?
2. Should Sticky Ball’s `A / READY_TO_RENDER / BLOCKED_PENDING_EVIDENCE` remain a valid final state, and what user-facing aggregate label should accompany it?
3. Should a null overall score be allowed through API/backend/PDF as `N/A`, or should only the Family 7 aggregation object be nullable while legacy score fields remain absent?
4. Should null family scores render as explicit `N/A / NO_SCORED_ITEMS` in PDF/UI rather than disappearing?
5. Should Family 8 define a finite state matrix such as:

```text
CREATIVE_PASS + EVIDENCE_COMPLETE + AUTHORIZED
CREATIVE_PASS + EVIDENCE_PARTIAL + BLOCKED_PENDING_EVIDENCE
CREATIVE_FAIL + EVIDENCE_PARTIAL + BLOCKED_CREATIVE_FAILURE
CREATIVE_UNKNOWN + EVIDENCE_INCOMPLETE + BLOCKED_PENDING_EVIDENCE
SERVICE_ERROR + EVIDENCE_INCOMPLETE + BLOCKED_TECHNICAL_FAILURE
```

or should it remain three independent facts without an aggregate state?
6. Should Golden comparator policy assertions include explicit independent assertions for creative quality, evidence completeness, readiness, and authorization, without combining them into one creative label?
7. Should a parser timeout remain a separate `NOT_EVALUATED`/unavailable authorization fact and never produce a numeric creative score?
8. Which downstream consumers must be lossless before Family 8 is frozen: ML/API only, or API + backend/PDF + frontend + render queue?

## 9. Stop condition

Family 8 audit is complete; implementation has not started. Family 1–7 remain frozen. Family 8 design, Gold Truth shape, state matrix, and cross-layer null/authorization decisions require human approval before any runtime or representation change.


## 10. Approved Family 8 human design lock

Human review approved the following decisions. These decisions supersede any earlier option language in this report.

### 10.1 Three orthogonal canonical axes

Family 8 has exactly three authoritative axes:

```text
CREATIVE QUALITY
  creativeScore
  creativeGrade

EVIDENCE COMPLETENESS
  evidenceCompleteness
  evaluationCoverage
  Family 7 aggregation counts/states
  explicit missing/unavailable reasons

RENDER AUTHORIZATION
  renderAuthorization
  authorizationReasons[]
```

Generic `grade` and `readiness` are legacy/compatibility projections only. They are not additional authoritative truths and must not become independent sources of state.

### 10.2 Valid Sticky Ball divergence

This combination is semantically valid:

```text
creativeGrade = A
evidenceCompleteness = PARTIAL
renderAuthorization = BLOCKED_PENDING_EVIDENCE
```

Meaning: the concept is creatively strong based on evaluated evidence, but required evidence is incomplete, so rendering is not authorized.

The UI must not present generic `READY_TO_RENDER` and `BLOCKED_PENDING_EVIDENCE` as if they were one contradictory status. The primary user-facing state is the render authorization; creative quality and evidence completeness are separate cards/facts.

### 10.3 Nullable scores

`overallScore` and family scores may be null. API, backend, frontend, PDF, and Golden representations must preserve null. Presentation may render:

```text
N/A — NO_SCORED_ITEMS
N/A — NOT_APPLICABLE
N/A — EVALUATION_UNAVAILABLE
```

Null must never become numeric zero.

Null family score rows must remain visible; filtering a null family score is not an acceptable representation.

### 10.4 No mega-state enum

Do not create a combinatorial state such as `A_PARTIAL_READY_BLOCKED`. Creative quality, evidence completeness, and render authorization remain orthogonal facts. Family 8 defines derivation/invariant rules between them, not a cross-product taxonomy.

### 10.5 Independent Golden assertions

Family 8 structural/policy assertions are independent:

```text
CREATIVE_GRADE
EVIDENCE_COMPLETENESS
RENDER_AUTHORIZATION
```

Legacy readiness may have a separate compatibility assertion. A mismatch in one axis must not overwrite or automatically fail another axis. Generic legacy `grade` remains compatibility coverage, not a fourth canonical Family 8 truth.

### 10.6 Runtime failure versus missing evidence

Family 7 runtime semantics remain authoritative:

```text
evaluationState = NOT_EVALUATED
outcome = null
reason = PARSER_TIMEOUT / provider or system failure
```

Family 8 authorization derives different causes:

```text
missing required evidence
  → BLOCKED_PENDING_EVIDENCE

parser/provider/system failure preventing assessment
  → BLOCKED_TECHNICAL_FAILURE
```

A system failure must not be presented as a request for the user to supply creative evidence.

### 10.7 Lossless authorization reasons

The smallest additive authorization representation is:

```text
renderAuthorization:
  status:
    AUTHORIZED
    BLOCKED_CREATIVE_FAILURE
    BLOCKED_TECHNICAL_FAILURE
    BLOCKED_PENDING_EVIDENCE
  reasons:
    - code
    - source
    - message/reference
```

Multiple reasons may coexist. `AUTHORIZED` is valid only when no blocking reason remains. Existing primary status compatibility may remain, but `authorizationReasons[]` is the lossless source for explanation.

### 10.8 End-to-end freeze boundary

Family 8 is not complete at the ML boundary. The contract must remain lossless through:

```text
ML assessment
  → ML API
  → backend DTO
  → PDF
  → frontend
  → actual render queue/admission boundary
```

The final render admission point must honor canonical `renderAuthorization`. OpenArt/provider behavior, render-worker architecture, publishing, Meta, and performance logic remain outside scope.

## 11. Approved implementation sequencing

The approved TDD plan is stored at:

```text
intelligence/docs/superpowers/plans/2026-10-08-family8-creative-quality-evidence-render-authorization.md
```

Implementation must stop before runtime changes until that plan is reviewed in the current session. Family 1–7 semantics, Gold Truth, rulesets, baselines, Meta, and publisher code remain protected.


## 13. Final contract locks before Task 1

### 13.1 `NOT_EVALUATED` is not an authorization cause

`evaluationState=NOT_EVALUATED` and `outcome=null` only state that no semantic evaluation result exists. Authorization cause must come from explicit reason/provenance:

```text
NOT_EVALUATED + REQUIRED_EVIDENCE_MISSING
  → BLOCKED_PENDING_EVIDENCE

NOT_EVALUATED + PARSER_TIMEOUT
  → BLOCKED_TECHNICAL_FAILURE

NOT_EVALUATED + REQUIRED_SERVICE_FAILURE
  → BLOCKED_TECHNICAL_FAILURE
```

The contract is:

```text
evaluationState != authorizationCause
```

### 13.2 Authorization reasons are authoritative

`authorizationReasons[]` is the lossless source of truth. Multiple categories may coexist:

```text
CREATIVE_BLOCKER
REQUIRED_EVIDENCE_MISSING
ASSESSMENT_TECHNICAL_FAILURE
```

The single `renderAuthorization.status` is only a compatibility projection. Its deterministic precedence is:

```text
BLOCKED_TECHNICAL_FAILURE
  > BLOCKED_CREATIVE_FAILURE
  > BLOCKED_PENDING_EVIDENCE
  > AUTHORIZED
```

`AUTHORIZED` is valid only when no blocking authorization reason remains.

### 13.3 Actual render admission is fail-closed

At the actual render queue/admission boundary, only:

```text
renderAuthorization.status == AUTHORIZED
```

may permit rendering. Blocked, null, missing, unknown, or unavailable authorization must deny admission. Legacy `readiness=READY_TO_RENDER` can never authorize rendering by itself.

The Sticky Ball boundary therefore remains:

```text
creativeGrade = A
readiness = READY_TO_RENDER
 evidenceCompleteness = PARTIAL
renderAuthorization = BLOCKED_PENDING_EVIDENCE
```

with render admission denied.
