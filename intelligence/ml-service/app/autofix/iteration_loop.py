"""
Auto-Fix Iteration Loop: Orchestrates multi-iteration prompt improvement.
Uses RegressionChecker to validate fixes don't introduce new problems.
"""

from dataclasses import dataclass, field

from ..parser.prompt_parser import parse_prompt
from ..quality.contracts import (
    EnhancedQualityReport,
    QualityReport,
    RegressionDecision,
)
from ..rules.rule_engine import RuleEngine
from ..scoring.quality_scorer import QualityScorer
from ..validation.regression_checker import RegressionChecker
from .prompt_fixer import FixResult, PromptFixer


@dataclass
class IterationResult:
    """Result of a single iteration"""

    iteration: int
    original_prompt: str
    modified_prompt: str
    fix_applied: FixResult
    report: QualityReport
    enhanced_report: EnhancedQualityReport
    regression_decision: RegressionDecision | None
    accepted: bool
    reason: str


@dataclass
class AutoFixResult:
    """Final result of auto-fix loop"""

    success: bool
    final_prompt: str
    final_report: QualityReport
    final_enhanced_report: EnhancedQualityReport
    initial_score: float
    final_score: float
    score_delta: float
    initial_status: str
    final_status: str
    iteration_count: int
    applied_fixes: list[IterationResult] = field(default_factory=list)
    rejected_fixes: list[IterationResult] = field(default_factory=list)
    improvement_history: list[float] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    early_stop_reason: str | None = None


class AutoFixIterationLoop:
    """
    Orchestrates iterative prompt improvement with regression checking.

    Workflow:
    1. Validate initial prompt
    2. If not RENDER_READY:
       a. Pick top priority fix
       b. Apply fix
       c. Re-validate
       d. Check regression
       e. Accept/Revise/Reject based on regression
    3. Repeat until RENDER_READY or max iterations

    Safety:
    - Regression checking prevents quality degradation
    - Iteration limits prevent infinite loops
    - Content preservation rules (character/world consistency)
    """

    def __init__(
        self,
        ruleset_version: str = "1.0",
        max_iterations: int = 5,
        min_improvement_threshold: float = 2.0,
        allow_score_plateau: bool = True,
    ):
        """
        Args:
            ruleset_version: Version of ruleset to use
            max_iterations: Maximum fix iterations (default 5)
            min_improvement_threshold: Minimum score increase to accept fix (default 2.0)
            allow_score_plateau: Accept fix if score stable but fixes critical (default True)
        """
        self.ruleset_version = ruleset_version
        self.max_iterations = max_iterations
        self.min_improvement_threshold = min_improvement_threshold
        self.allow_score_plateau = allow_score_plateau

        from ..config import settings

        self.engine = RuleEngine(str(settings.rules_dir / f"RULESET_{ruleset_version}.yaml"))
        self.scorer = QualityScorer()
        self.fixer = PromptFixer()
        self.regression_checker = RegressionChecker()

    def run(self, initial_prompt: str) -> AutoFixResult:
        """
        Run auto-fix iteration loop on prompt.

        Args:
            initial_prompt: Original prompt text

        Returns:
            AutoFixResult with final prompt and improvement history
        """
        # Initial validation
        parse_result = parse_prompt(initial_prompt)
        initial_ir = parse_result.video_plan_ir
        initial_metadata = parse_result.metadata
        initial_report = self.engine.evaluate(initial_ir)
        initial_enhanced = self.scorer.create_enhanced_report(initial_report, initial_ir, initial_metadata)

        initial_score = initial_report.overall_score
        initial_status = initial_report.status

        # Track state
        current_prompt = initial_prompt
        current_ir = initial_ir
        current_report = initial_report
        current_enhanced = initial_enhanced

        applied_fixes: list[IterationResult] = []
        rejected_fixes: list[IterationResult] = []
        improvement_history = [initial_score]
        warnings = []
        early_stop_reason = None
        attempted_rule_ids: set[str] = set()

        # If already RENDER_READY, done
        if initial_status == "RENDER_READY":
            return AutoFixResult(
                success=True,
                final_prompt=initial_prompt,
                final_report=initial_report,
                final_enhanced_report=initial_enhanced,
                initial_score=initial_score,
                final_score=initial_score,
                score_delta=0.0,
                initial_status=initial_status,
                final_status=initial_status,
                iteration_count=0,
                applied_fixes=[],
                rejected_fixes=[],
                improvement_history=[initial_score],
                warnings=["Prompt already RENDER_READY, no fixes needed"],
                early_stop_reason="Already optimal",
            )

        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            # Get top priority fix
            if not current_enhanced.priority_fixes:
                early_stop_reason = "No more fixes available"
                break

            top_fix = next(
                (fix for fix in current_enhanced.priority_fixes if fix.rule_id not in attempted_rule_ids),
                None,
            )
            if top_fix is None:
                early_stop_reason = "No untried fixes available"
                break
            attempted_rule_ids.add(top_fix.rule_id)

            # Apply fix
            fix_result = self.fixer.apply_fix(current_prompt, top_fix, current_ir)

            if not fix_result.success:
                warnings.append(
                    f"Iteration {iteration}: Fix {top_fix.rule_id} failed: {fix_result.fix_description}"
                )
                continue

            # Validate fixed prompt
            try:
                parse_result_fixed = parse_prompt(fix_result.modified_prompt)
                fixed_ir = parse_result_fixed.video_plan_ir
                fixed_metadata = parse_result_fixed.metadata
                fixed_report = self.engine.evaluate(fixed_ir)
                fixed_enhanced = self.scorer.create_enhanced_report(fixed_report, fixed_ir, fixed_metadata)
            except Exception as e:
                warnings.append(f"Iteration {iteration}: Parsing failed after fix: {str(e)}")
                rejected_fixes.append(
                    IterationResult(
                        iteration=iteration,
                        original_prompt=current_prompt,
                        modified_prompt=fix_result.modified_prompt,
                        fix_applied=fix_result,
                        report=current_report,
                        enhanced_report=current_enhanced,
                        regression_decision=None,
                        accepted=False,
                        reason=f"Parse failed: {str(e)}",
                    )
                )
                continue

            # Check regression (single canonical entry point)
            regression_report = self.regression_checker.check(current_report, fixed_report)

            decision = regression_report.decision

            # Decision logic
            accepted = False
            reason = ""

            if decision == RegressionDecision.REJECT:
                reason = "Critical regression detected"
                rejected_fixes.append(
                    IterationResult(
                        iteration=iteration,
                        original_prompt=current_prompt,
                        modified_prompt=fix_result.modified_prompt,
                        fix_applied=fix_result,
                        report=fixed_report,
                        enhanced_report=fixed_enhanced,
                        regression_decision=decision,
                        accepted=False,
                        reason=reason,
                    )
                )

            elif decision == RegressionDecision.REVISE:
                # Check if score improvement justifies warning regressions
                score_delta = fixed_report.overall_score - current_report.overall_score

                if score_delta >= self.min_improvement_threshold:
                    accepted = True
                    reason = f"Score improved by {score_delta:.1f}pts despite warnings"
                else:
                    reason = f"Insufficient improvement ({score_delta:.1f}pts) to justify warnings"
                    rejected_fixes.append(
                        IterationResult(
                            iteration=iteration,
                            original_prompt=current_prompt,
                            modified_prompt=fix_result.modified_prompt,
                            fix_applied=fix_result,
                            report=fixed_report,
                            enhanced_report=fixed_enhanced,
                            regression_decision=decision,
                            accepted=False,
                            reason=reason,
                        )
                    )

            elif decision == RegressionDecision.ACCEPT:
                # Check score delta
                score_delta = fixed_report.overall_score - current_report.overall_score

                # Accept if improvement OR plateau with critical fix
                if score_delta >= self.min_improvement_threshold:
                    accepted = True
                    reason = f"Score improved by {score_delta:.1f}pts"
                elif (
                    self.allow_score_plateau
                    and score_delta >= -1.0
                    and len(regression_report.fixed_rules) > 0
                ):
                    accepted = True
                    reason = (
                        f"Score plateau ({score_delta:+.1f}pts) but "
                        f"{len(regression_report.fixed_rules)} rules fixed"
                    )
                else:
                    reason = f"Insufficient improvement ({score_delta:.1f}pts)"
                    rejected_fixes.append(
                        IterationResult(
                            iteration=iteration,
                            original_prompt=current_prompt,
                            modified_prompt=fix_result.modified_prompt,
                            fix_applied=fix_result,
                            report=fixed_report,
                            enhanced_report=fixed_enhanced,
                            regression_decision=decision,
                            accepted=False,
                            reason=reason,
                        )
                    )

            # Commit if accepted
            if accepted:
                applied_fixes.append(
                    IterationResult(
                        iteration=iteration,
                        original_prompt=current_prompt,
                        modified_prompt=fix_result.modified_prompt,
                        fix_applied=fix_result,
                        report=fixed_report,
                        enhanced_report=fixed_enhanced,
                        regression_decision=decision,
                        accepted=True,
                        reason=reason,
                    )
                )

                # Update current state
                current_prompt = fix_result.modified_prompt
                current_ir = fixed_ir
                current_report = fixed_report
                current_enhanced = fixed_enhanced

                improvement_history.append(current_report.overall_score)

                # Check if RENDER_READY
                if current_report.status == "RENDER_READY":
                    early_stop_reason = "RENDER_READY achieved"
                    break

            # Diminishing returns check
            if len(improvement_history) >= 4:
                recent_improvements = [
                    improvement_history[i] - improvement_history[i - 1] for i in range(-3, 0)
                ]
                if all(imp < 1.0 for imp in recent_improvements):
                    early_stop_reason = "Diminishing returns (3 consecutive improvements <1pt)"
                    break

        # Final result
        final_score = current_report.overall_score
        final_status = current_report.status
        score_delta = final_score - initial_score

        success = final_status == "RENDER_READY" or score_delta >= 10.0 or len(applied_fixes) > 0

        return AutoFixResult(
            success=success,
            final_prompt=current_prompt,
            final_report=current_report,
            final_enhanced_report=current_enhanced,
            initial_score=initial_score,
            final_score=final_score,
            score_delta=score_delta,
            initial_status=initial_status,
            final_status=final_status,
            iteration_count=len(applied_fixes),
            applied_fixes=applied_fixes,
            rejected_fixes=rejected_fixes,
            improvement_history=improvement_history,
            warnings=warnings,
            early_stop_reason=early_stop_reason,
        )

    def format_result(self, result: AutoFixResult) -> str:
        """Format AutoFixResult as human-readable text"""
        lines = []

        lines.append("=" * 80)
        lines.append("AUTO-FIX ITERATION LOOP RESULT")
        lines.append("=" * 80)

        lines.append("\n📊 SUMMARY")
        lines.append(f"  Success: {'✅ Yes' if result.success else '❌ No'}")
        lines.append(f"  Initial: {result.initial_score:.1f}/100 ({result.initial_status})")
        lines.append(f"  Final: {result.final_score:.1f}/100 ({result.final_status})")
        lines.append(f"  Delta: {result.score_delta:+.1f}pts")
        lines.append(f"  Iterations: {result.iteration_count}/{self.max_iterations}")

        if result.early_stop_reason:
            lines.append(f"  Stop Reason: {result.early_stop_reason}")

        lines.append(f"\n✅ APPLIED FIXES ({len(result.applied_fixes)})")
        for fix_iter in result.applied_fixes:
            lines.append(f"  Iteration {fix_iter.iteration}: {fix_iter.fix_applied.rule_id}")
            lines.append(f"    {fix_iter.fix_applied.fix_description}")
            lines.append(f"    Result: {fix_iter.reason}")
            lines.append(f"    Score: {fix_iter.report.overall_score:.1f}/100")

        if result.rejected_fixes:
            lines.append(f"\n❌ REJECTED FIXES ({len(result.rejected_fixes)})")
            for fix_iter in result.rejected_fixes:
                lines.append(f"  Iteration {fix_iter.iteration}: {fix_iter.fix_applied.rule_id}")
                lines.append(f"    Reason: {fix_iter.reason}")

        if result.warnings:
            lines.append(f"\n⚠️  WARNINGS ({len(result.warnings)})")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        lines.append("\n📈 IMPROVEMENT TRAJECTORY")
        lines.append(f"  {' → '.join(f'{score:.1f}' for score in result.improvement_history)}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)
