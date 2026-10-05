# Rendered Video Assessment Plan

## 1. Current analysis path

The intelligence backend ingests a video, creates a versioned `CreativeAnalysisEntity`, and exposes the latest sampled analysis through `GET /api/v1/videos/{id}/analysis/status`. The current motion analyzer is `SAMPLED_VISUAL_MOTION` and the current analysis version is `sampled-visual-motion-v3`. Its output is persisted in `rawResult`, including motion, sampling, visual similarity, measurement quality, timeline, and dark-frame candidates.

The creative-render service separately evaluates downloaded render assets through `PostRenderEvaluationService`. It creates an immutable `RenderEvidenceIR`, evaluates the configured post-render YAML rules, persists `post_render_evaluations` and `post_render_rule_results`, and returns a post-render decision to the render worker.

## 2. Current evidence fields

Current evidence includes technical asset metadata, QA helper results, motion evidence, sampling quality, visual similarity, dark-frame candidates, and semantic placeholders. Motion evidence remains motion-only. The frontend currently renders the raw motion and sampling facts directly in the Video Detail overview.

## 3. Current Post-Render Rule Engine

`POST_RENDER_RULESET_1.1` is loaded by `PostRenderRuleEngine`. Rules use a source path, operator, expected value, severity, missing-evidence behavior, and policy effect. Results have PASS, FAIL, UNKNOWN, NOT_APPLICABLE, or SERVICE_ERROR outcomes. `PostRenderDecisionAggregator` currently produces PASS, HUMAN_REVIEW, FAIL, or SYSTEM_ERROR; it does not produce an ordinal assessment grade.

## 4. Current payoff and timeline lineage

Prompt parsing already produces `VideoPlanIR`-style timeline beats and final-payoff fields inside the ML prompt-quality flow, but the rendered-video post-render path does not receive or persist that plan lineage. `RenderEvidenceIR` currently contains only technical, QA, motion, sampling, similarity, dark-frame, and semantic placeholder maps. Therefore payoff resolution cannot currently be reliable for a rendered asset.

## 5. Payoff timestamp reliability

No reliable rendered-asset payoff timestamp is currently available to the post-render evaluator. The implementation must resolve explicit plan lineage first and return `NOT_AVAILABLE` or `AMBIGUOUS` when the plan is absent or cannot be mapped. It must not infer a payoff from a motion spike alone.

## 6. Missing evidence and product capability

Missing capabilities are: payoff-window resolution, bounded dense payoff sampling, before/during/after payoff motion profiles, motion-contrast evidence, intentional-hold evidence, purposeful-hold versus idle classification, canonical human-readable insight translation, structured experiment recommendations, assessment coverage, and a versioned ordinal grade. The frontend has no summary-first post-render assessment view and no technical-details collapse for this assessment.

## 7. Proposed assessment model

Keep the layers separate:

`measurement -> evidence -> rule interpretation -> assessment -> human-readable insight -> optional performance comparison -> learning`.

Add a versioned assessment aggregate over immutable evidence and persisted rule results. The aggregate contains grade, label, verdict, strengths, concerns, coverage, recommendations, ruleset version, aggregator version, evidence version, and analyzer versions. It must not contain expected views, viral probability, or platform-performance predictions.

## 8. Proposed grading model

Grade is derived from rule outcomes and evidence coverage, never from an average of numeric metrics. Required evidence with service errors or insufficient coverage yields `INCOMPLETE`. Blocker failures yield `F`; human-review/high-impact conditions yield `D`; meaningful warnings yield `C`; only minor warnings yield `B`; clean required evidence with no meaningful warnings can yield `A`. The exact severity vocabulary remains the existing `INFO`, `WARNING`, `CRITICAL`, and `BLOCKER` vocabulary.

## 9. Human-readable insight contract

Introduce a canonical insight DTO with: `id`, `category`, `title`, `status`, `summary`, `observed`, `meaning`, `recommendation`, `confidenceLabel`, `evidenceReferences`, `limitation`, and `priority`. Deterministic backend translation should generate text from rule results and structured evidence. Wording must remain observational and non-causal. Raw technical values remain available as secondary details.

## 10. Frontend layout

Video Detail should show a summary-first `POST-RENDER ASSESSMENT` section with grade, verdict, coverage, strengths, main concerns, and suggested experiment. Below it, show evidence cards for visual activity, payoff emphasis, endpoint similarity, continuity, and technical quality. Put raw motion, sampling, decode, and analyzer-version fields under collapsed `Technical details`. Observed performance remains a separate section and must never rewrite the assessment grade.

## 11. Persistence and versioning

Existing immutable `post_render_evaluations` and `post_render_rule_results` are the foundation. Add an assessment snapshot associated with an evaluation, storing the exact `postRenderRulesetVersion`, `assessmentAggregatorVersion`, `renderEvidenceVersion`, and `motionAnalyzerVersion`. Do not overwrite earlier assessments. Human review decision and machine grade remain separate and auditable.

## 12. Implementation order

1. Add payoff-resolution and payoff-evidence structures without changing motion-v3 semantics.
2. Add bounded payoff evidence extraction and the `PAYOFF_VISUAL_EMPHASIS` rule.
3. Add deterministic insight and recommendation translation.
4. Add versioned assessment aggregation, coverage, and persistence/API projection.
5. Integrate Video Detail summary-first UI and collapsed technical details.
6. Add focused tests for resolution, dense sampling, contrast, intentional holds, insights, grading, versioning, and frontend presentation.
7. Add `POST_RENDER_ASSESSMENT_AND_INSIGHTS.md` and update system capabilities only after runtime verification.
