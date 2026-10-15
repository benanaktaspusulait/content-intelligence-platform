# ADR — CREATIVE_PROMPT_QUALITY_V1

Status: **APPROVED FOR IMPLEMENTATION — GRADING INACTIVE PENDING CALIBRATION AND ACTIVATION EVIDENCE**  
Decision owners: Product Architecture and Creative Quality Architecture  
Date: 2026-10-15

## Context

Ruleset 1.11 is the canonical rule-compliance evaluator. Its A threshold is 92; its weighted score reflects applicable, evaluable canonical rules under the canonical severity/aggregation contract. It is not calibrated to measure intrinsic pre-render prompt creativity. The separate `pre_render_assessment.creative_grade` is a severity-derived summary of canonical findings, not an independent or calibrated creative-quality measure. Ruleset 1.11 has no A+.

The six dimensions in `intelligence/data/workflow/creative-quality-v2.json` currently have `QUALITATIVE_TEXT_EVIDENCE_ONLY` authority. The contract reserves `MATERIAL_IMPROVEMENT_SUPPORTED`; it never emits that outcome. Semantic source fidelity stays UNKNOWN without independent evidence, visual benefit remains unverified absent visual evidence, and audience benefit remains unmeasured absent audience evidence.

The architecture direction is approved for implementation. That approval does not authorize fabricated governance signatures, production grade activation without calibration, paid provider calls, candidate approval, story or prompt changes, canonical scoring changes, or rendering.

## Decision

Implement a versioned assessment contract named `CREATIVE_PROMPT_QUALITY_V1`, separate from Ruleset 1.11 and F8/render authorization. It produces a transparent text-evidence profile for a complete production prompt and keeps canonical score, canonical grade, rule severity/outcomes, and render admission independent.

The contract may assign A or A+ only after the calibration and evidence conditions below are approved. It must not promote existing B prompts automatically. Until a versioned calibration set and thresholds are approved, report dimensions and evidence status without an aggregate letter.

## Proposed dimension contract

| Dimension | Text-evaluable evidence | Independent / visual evidence needed for a full judgment | Do not infer |
|---|---|---|---|
| `SCROLL_STOP_VISUAL_PROMISE` | Explicit opening subject, anomaly, composition intent and immediate visual question | Blinded human review of the produced frame for legibility; if actual viewer capture is used, instrumented audience evidence | Retention, audience curiosity, or actual anomaly visibility from prose alone |
| `CAUSAL_PROGRESSION` | Explicit ordered actions, physical state changes and observable consequences | Independent plan/story review; rendered continuity/readability review for claims about the video | Successful visual causality from a model-authored explanation |
| `VISUAL_STORYTELLING` | Character/object spatial relation, state presentation, motivated action and information conveyed without exposition | Independent review of rendered frames/video for state legibility, continuity and identity adherence | Render adherence or emotional effect from prompt text |
| `PRODUCTION_EXECUTABILITY` | Duration budget, action count, transitions, continuity burden, named constraints and generator fit | Independent execution critic on exact prompt; output review to assess actual adherence and artifact rate | Reliable generation or lower failure probability without validated data |
| `ENDING_REPLAY` | Explicit ending image, relation to opening, transition/loop construction | Blinded visual review for loop coherence; audience study for replay behavior | That viewers will replay or share |
| `DISTINCTIVE_CREATIVE_VALUE` | Specificity and non-generic execution choices, judged against approved exemplars without violating protected source | Independent blinded reviewers; rendered comparison if the claim depends on visual distinctiveness | Novelty or superiority from word count, adjectives, camera labels, model rationale or score delta |

Source fidelity is a mandatory independent qualification dimension across all six; it is not a seventh creative benefit score. Production feasibility is reported separately from intrinsic creativity. Canonical compliance remains a linked but separate report. `UNKNOWN`, `UNVERIFIED`, `UNMEASURED`, and `NOT_APPLICABLE` are explicit non-passing evidence states and never become favorable values by imputation.

## A and A+ criteria (proposed; thresholds not yet calibrated)

**A — high-quality production prompt:** Every mandatory text-evaluable dimension meets a calibrated minimum; no dimension has a material unresolved defect; exact source fidelity passes an independent verifier; production feasibility has no unresolved critical risk; evidence coverage meets the approved minimum; and blinded reviewers reach the approved agreement level. Any visual-dependent claim is explicitly bounded to text-only evidence until actual visual evidence exists. A does not imply canonical A, render authorization or audience success.

**A+ — exceptional production prompt:** Meets all A criteria and shows independently judged, unusually strong execution across the dimensions most relevant to its approved story, with a material advantage over approved strong exemplars under blinded comparison. Its evidence must include the evidence type needed for each asserted distinction. A+ cannot be awarded by raising a numeric cutoff alone, by a provider’s self-assessment, or by an unverified prediction of audience response.

No numeric thresholds, dimension weights, reviewer counts, coverage percentages, or agreement cutoffs are fixed in this draft. Calibration must establish them from the approved corpus before activation; inventing numbers now would create an ungrounded grade.

## Source-fidelity evidence contract

An independent evidence record must be produced by an authenticated reviewer/verifier separate from candidate generation and bound immutably to:

- approved original story ID and revision/fingerprint;
- exact original prompt and candidate prompt fingerprint;
- candidate intervention/plan fingerprint and source-event mapping;
- analysis ID, canonical ruleset, creative-quality contract version and relevant production settings;
- verifier identity, role/authority, method/version, decision, cited evidence and rationale;
- created-at time, expiry or revalidation conditions, and supersession history.

The verifier must assess identity, physical rule, approved events/order, ending and any claimed source-supported staging changes. Generator/compiler output and generator self-assertions cannot be the independent verifier. If authority, evidence or binding is absent or stale, source fidelity is UNKNOWN and the candidate cannot receive A/A+.

## Calibration and validation required before activation

1. Obtain architecture-approved, source-authorized good and weak original production prompts spanning relevant profiles and generator settings, with independent story fidelity and review provenance. Include B→A capable and genuinely non-improvable controls; do not derive acceptance labels from synthetic scores.
2. Have multiple qualified reviewers score de-identified prompts independently against a written rubric, without canonical grade, candidate identity, provider, or intended result visible. Record disagreements and evidence citations.
3. Freeze train/calibration and held-out sets with content hashes, story/prompt provenance, version bindings and authorization. Avoid leakage between candidates and exemplars.
4. Calibrate dimension thresholds and aggregate decision from reviewer judgments; test repeatability, inter-rater disagreement, false positive and false negative rates, source-fidelity rejection, and profile/generator slices. Report confidence intervals and uncertainty.
5. Set a minimum evidence coverage policy; missing visual/audience evidence remains UNKNOWN/UNVERIFIED/UNMEASURED and limits only claims that require it. It must not be treated as proof of either quality or defect.
6. Version the rubric, calibration corpus, thresholds and producer/consumer interfaces. Require regression tests, revalidation on expiry/version mismatch, audit provenance and explicit architecture activation.
7. Validate the complete application pipeline on an eligible approved B case with a no-egress mock provider before any separately authorized real-provider experiment. Do not inject final grades or bypass normal persistence and routing.

When reviewers disagree beyond the calibrated tolerance, report `REVIEW_DISAGREEMENT` and withhold aggregate A/A+ pending adjudication by a separately authorized reviewer. Do not average away a source-fidelity conflict or a mandatory blocker.

## Relationship to other decisions

- Canonical Ruleset 1.11 score and grade remain unchanged and visible alongside this profile.
- Rule exceptions can affect only their governed admission scope and never alter canonical FAIL/score or this quality assessment.
- Text acceptance, production-risk acknowledgement, source-fidelity validation, visual evidence preparation and render authorization remain independent operations.
- A/A+ must never imply F8 authorization or satisfy missing verified-character references, accepted start frames, visual evidence, risk acknowledgement or other hard render gates.
- Optimizer preflight should report creative opportunity separately from canonical A attainability; neither status itself authorizes generation.

## Consequences

This proposal addresses the category error between canonical compliance and creative prompt quality while preserving current canonical and render safety. It introduces no active grade today. Until evidence, independent verification, calibration and approval exist, product status remains incomplete for source-fidelity readiness, B→A golden acceptance and real-model creative effectiveness.

## Implemented API and persistence boundary

- `POST /records/{analysisId}/comparisons/{comparisonId}/candidates/{candidateId}/creative-prompt-quality/assess` creates a text-only assessment preview for the current saved analysis and candidate comparison. It never returns an uncalibrated letter grade.
- `POST /records/{analysisId}/comparisons/{comparisonId}/candidates/{candidateId}/fidelity-review` stores an authenticated, exact-binding source-fidelity judgment (`PASS`, `FAIL`, `UNKNOWN`) as append-only evidence.
- `GET /cpq/reviewer-capabilities` exposes capabilities derived from the authenticated principal, never from client role claims.
- `/cpq/calibration/corpora`, `/examples`, blinded review packets/judgments, readiness and preview APIs implement the governed calibration workflow. Provisional thresholds and held-out error reports remain diagnostic only.
- `cpq_*` tables store versioned corpora, immutable examples/reviews/judgments/assessments/reports and an inactive singleton policy state. A frozen corpus cannot be changed.
- Adaptive V3 reports creative opportunity uncertainty, canonical-A attainability and CPQ target activation separately; CPQ target integration remains gated off until the activation requirements below are evidenced.

## Approval record

Architecture implementation direction: **approved by the user in the implementation authorization dated 2026-10-15**. This is not a substitute for the formal governed activation record. **Do not activate grading until every activation requirement is met and authorized.**


## Original-subject implementation extension — 2026-10-15

Implemented and deployed V64 in the existing CPQ service. ORIGINAL_PROMPT subjects bind exact repository/saved prompt bytes to real approved story/revision and production-setting authority. They do not require fabricated optimization comparisons. `/cpq/original-prompts/preflight`, `/bindings` and `/{subjectId}/fidelity-review` provide read-only resolution, authenticated architecture binding and independent append-only review. Candidate scope remains separate and backward compatible. Explicit immutable same-subject supersession does not overwrite history. Import and readiness revalidate current exact evidence; blind packets omit identity/quality labels and preserve production context. New human submissions use cpq-human-blind-review-v2 with exact citations, specific strength/weakness, production constraint and UNKNOWN uncertainty across six dimensions. Historical method records remain intact.

Engineering verification is not source approval, independent human review or grade activation. Missing actual source approval/settings retains blockers. Production grading remains INACTIVE; no thresholds, aggregation policy or canonical Ruleset1.11 changes were made. See the original fidelity and calibration report for deployed verification and remaining evidence requirements.
