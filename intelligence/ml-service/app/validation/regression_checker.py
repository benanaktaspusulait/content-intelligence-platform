"""
Pompom Creative Quality Engine - Regression Checker
Compares two versions of a prompt (before/after fix) to detect if improvements broke other rules.
"""

from dataclasses import dataclass
from enum import StrEnum

from ..quality.contracts import (
    EnhancedQualityReport,
    QualityReport,
    RegressionDecision,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)


class RegressionSeverity(StrEnum):
    """Severity level for regression issues"""

    CRITICAL = "CRITICAL"  # Fix broke a blocker/critical rule that was passing
    WARNING = "WARNING"  # Fix degraded a passing rule to warning
    CONCERN = "CONCERN"  # Score dropped significantly but no rule failed


@dataclass
class RegressionIssue:
    """Single regression detected between versions"""

    rule_id: str
    rule_name: str
    family: str
    severity: RegressionSeverity
    before_status: str  # "PASS" / "WARNING" / "FAIL"
    after_status: str  # "PASS" / "WARNING" / "FAIL"
    before_value: float | None
    after_value: float | None
    score_delta: float  # negative = degradation
    message: str
    recommendation: str


@dataclass
class RegressionReport:
    """Complete regression analysis between two prompt versions"""

    version_before: str
    version_after: str
    has_regressions: bool

    # Overall metrics
    score_before: float
    score_after: float
    score_delta: float  # positive = improvement

    # Status changes
    status_before: str  # RENDER_READY / NEEDS_REVISION / BLOCKED
    status_after: str
    status_improved: bool

    # Regression analysis
    critical_regressions: list[RegressionIssue]
    warning_regressions: list[RegressionIssue]
    concerns: list[RegressionIssue]

    # Improvements
    fixed_rules: list[str]  # Rules that went from FAIL→PASS or WARNING→PASS
    improved_families: list[str]  # Families with score increase
    degraded_families: list[str]  # Families with score decrease

    # Net outcome
    net_improvement: bool  # True if improvements > regressions
    decision: RegressionDecision  # ACCEPT / REVISE / REJECT (canonical)
    recommendation: str  # String mirror of ``decision`` for the API DTO
    summary: str


class RegressionChecker:
    """
    Compares two QualityReports (before/after) to detect if fixes introduced new problems.

    Usage:
        checker = RegressionChecker()
        report_v1 = engine.evaluate(ir_v1)
        report_v2 = engine.evaluate(ir_v2)
        regression = checker.check(report_v1, report_v2, "v1", "v2")

        if regression.has_regressions:
            print(f"Critical regressions: {len(regression.critical_regressions)}")
            for issue in regression.critical_regressions:
                print(f"  - {issue.message}")
    """

    # Thresholds
    SCORE_DROP_CONCERN_THRESHOLD = 5.0  # 5+ point drop without rule fail = concern
    FAMILY_SCORE_DROP_THRESHOLD = 10.0  # 10+ point family drop = degraded

    def check(
        self,
        report_before: QualityReport | EnhancedQualityReport,
        report_after: QualityReport | EnhancedQualityReport,
        version_before: str = "before",
        version_after: str = "after",
    ) -> RegressionReport:
        """
        Compare two quality reports and detect regressions.

        Args:
            report_before: QualityReport from original prompt
            report_after: QualityReport from revised prompt
            version_before: Label for original version
            version_after: Label for revised version

        Returns:
            RegressionReport with detected issues and recommendations
        """
        # Extract core reports if Enhanced
        r_before: QualityReport = (
            report_before.base_report if isinstance(report_before, EnhancedQualityReport) else report_before
        )
        r_after: QualityReport = (
            report_after.base_report if isinstance(report_after, EnhancedQualityReport) else report_after
        )

        # Detect regressions by comparing rule evaluations
        critical_regressions = []
        warning_regressions = []
        concerns = []
        fixed_rules = []

        # Build lookup maps
        evals_before = {ev.rule_id: ev for ev in r_before.evaluations}
        evals_after = {ev.rule_id: ev for ev in r_after.evaluations}

        # Compare each rule
        for rule_id in set(evals_before.keys()) | set(evals_after.keys()):
            ev_before = evals_before.get(rule_id)
            ev_after = evals_after.get(rule_id)

            if not ev_before or not ev_after:
                continue  # Rule added/removed (shouldn't happen with same ruleset)

            regression = self._detect_rule_regression(ev_before, ev_after)
            if regression:
                if regression.severity == RegressionSeverity.CRITICAL:
                    critical_regressions.append(regression)
                elif regression.severity == RegressionSeverity.WARNING:
                    warning_regressions.append(regression)
                else:
                    concerns.append(regression)

            # Check if rule was fixed (not passing before, passing after)
            if ev_before.outcome is not RuleOutcome.PASS and ev_after.outcome is RuleOutcome.PASS:
                fixed_rules.append(rule_id)

        # Compare family scores
        improved_families = []
        degraded_families = []

        for family in r_before.family_scores.keys():
            score_before = r_before.family_scores.get(family)
            score_after = r_after.family_scores.get(family)
            # Unknown/not-applicable families have no numeric delta. They are
            # represented by evidence-coverage changes elsewhere, never by 0.
            if score_before is None or score_after is None:
                continue
            delta = score_after - score_before

            if delta >= self.FAMILY_SCORE_DROP_THRESHOLD:
                improved_families.append(family)
            elif delta <= -self.FAMILY_SCORE_DROP_THRESHOLD:
                degraded_families.append(family)

        # Overall score comparison
        score_delta = r_after.overall_score - r_before.overall_score

        # Check for score drop without rule fail (concern)
        if (
            score_delta < -self.SCORE_DROP_CONCERN_THRESHOLD
            and not critical_regressions
            and not warning_regressions
        ):
            concerns.append(
                RegressionIssue(
                    rule_id="OVERALL",
                    rule_name="Overall Quality Score",
                    family="SYSTEM",
                    severity=RegressionSeverity.CONCERN,
                    before_status="PASS",
                    after_status="PASS",
                    before_value=r_before.overall_score,
                    after_value=r_after.overall_score,
                    score_delta=score_delta,
                    message=(
                        f"Overall score dropped {abs(score_delta):.1f} points without specific rule failures"
                    ),
                    recommendation="Review changes for unintended quality degradation",
                )
            )

        # Status comparison
        status_improved = self._is_status_better(r_after.status, r_before.status)

        # Net improvement calculation
        net_improvement = (
            len(fixed_rules) > len(critical_regressions)
            and score_delta > 0
            and (status_improved or r_after.status == r_before.status)
        )

        # Generate decision (canonical enum; recommendation mirrors its value)
        if critical_regressions:
            decision = RegressionDecision.REJECT
            summary = f"Revision broke {len(critical_regressions)} critical rule(s). Reject changes."
        elif len(warning_regressions) > len(fixed_rules):
            decision = RegressionDecision.REVISE
            summary = (
                f"More regressions ({len(warning_regressions)}) than fixes "
                f"({len(fixed_rules)}). Needs revision."
            )
        elif net_improvement:
            decision = RegressionDecision.ACCEPT
            summary = (
                f"Net improvement: {len(fixed_rules)} fixes, {score_delta:+.1f} points, "
                f"status {r_before.status}→{r_after.status}."
            )
        else:
            decision = RegressionDecision.REVISE
            summary = (
                f"Mixed results: {len(fixed_rules)} fixes but "
                f"{len(warning_regressions)} warnings. Consider alternative approach."
            )

        recommendation = decision.value

        return RegressionReport(
            version_before=version_before,
            version_after=version_after,
            has_regressions=(len(critical_regressions) + len(warning_regressions) > 0),
            score_before=r_before.overall_score,
            score_after=r_after.overall_score,
            score_delta=score_delta,
            status_before=r_before.status,
            status_after=r_after.status,
            status_improved=status_improved,
            critical_regressions=critical_regressions,
            warning_regressions=warning_regressions,
            concerns=concerns,
            fixed_rules=fixed_rules,
            improved_families=improved_families,
            degraded_families=degraded_families,
            net_improvement=net_improvement,
            decision=decision,
            recommendation=recommendation,
            summary=summary,
        )

    def _detect_rule_regression(
        self, ev_before: RuleEvaluation, ev_after: RuleEvaluation
    ) -> RegressionIssue | None:
        """
        Compare two rule evaluations and detect regression.

        Returns RegressionIssue if regression found, None otherwise.
        """
        before_pass = ev_before.outcome is RuleOutcome.PASS
        after_pass = ev_after.outcome is RuleOutcome.PASS

        # Both passing or both failing at same severity = no regression
        if (
            ev_before.outcome is ev_after.outcome
            and ev_before.configured_severity is ev_after.configured_severity
        ):
            return None

        # Was passing, now failing = REGRESSION
        if before_pass and not after_pass:
            # Determine severity based on new failure level
            if ev_after.configured_severity in (Severity.BLOCKER, Severity.CRITICAL):
                severity = RegressionSeverity.CRITICAL
            else:
                severity = RegressionSeverity.WARNING

            return RegressionIssue(
                rule_id=ev_after.rule_id,
                rule_name=ev_after.rule_id.replace("_", " ").title(),
                family=ev_after.family,
                severity=severity,
                before_status="PASS",
                after_status="FAIL",
                before_value=getattr(ev_before, "actual_value", None),
                after_value=getattr(ev_after, "actual_value", None),
                score_delta=self._calculate_score_impact(ev_before, ev_after),
                message=(
                    f"Rule {ev_after.rule_id} regressed from PASS to "
                    f"{ev_after.configured_severity.value} FAIL: {ev_after.message}"
                ),
                recommendation=f"Revert changes affecting {ev_after.family} or find alternative fix",
            )

        # Severity escalation while still failing (WARNING -> CRITICAL/BLOCKER)
        if (
            not before_pass
            and not after_pass
            and self._is_severity_worse(ev_after.configured_severity, ev_before.configured_severity)
        ):
            return RegressionIssue(
                rule_id=ev_after.rule_id,
                rule_name=ev_after.rule_id.replace("_", " ").title(),
                family=ev_after.family,
                severity=RegressionSeverity.CRITICAL,
                before_status=f"FAIL ({ev_before.configured_severity.value})",
                after_status=f"FAIL ({ev_after.configured_severity.value})",
                before_value=getattr(ev_before, "actual_value", None),
                after_value=getattr(ev_after, "actual_value", None),
                score_delta=self._calculate_score_impact(ev_before, ev_after),
                message=(
                    f"Rule {ev_after.rule_id} escalated from "
                    f"{ev_before.configured_severity.value} to {ev_after.configured_severity.value}"
                ),
                recommendation=(
                    f"Immediately address {ev_after.configured_severity.value} failure in {ev_after.family}"
                ),
            )

        return None

    def _calculate_score_impact(self, ev_before: RuleEvaluation, ev_after: RuleEvaluation) -> float:
        """Estimate score impact of rule change (rough approximation)"""
        # Simple heuristic: PASS=100, WARNING=70, CRITICAL=40, BLOCKER=0
        score_map = {Severity.BLOCKER: 0, Severity.CRITICAL: 40, Severity.WARNING: 70}

        before_score = (
            100 if ev_before.outcome is RuleOutcome.PASS else score_map.get(ev_before.configured_severity, 0)
        )
        after_score = (
            100 if ev_after.outcome is RuleOutcome.PASS else score_map.get(ev_after.configured_severity, 0)
        )

        return after_score - before_score

    def _is_severity_worse(self, severity_after: Severity, severity_before: Severity) -> bool:
        """Check if severity escalated"""
        severity_order = [Severity.WARNING, Severity.CRITICAL, Severity.BLOCKER]
        try:
            return severity_order.index(severity_after) > severity_order.index(severity_before)
        except ValueError:
            return False

    def _is_status_better(self, status_after: str, status_before: str) -> bool:
        """Check if overall status improved"""
        status_order = ["BLOCKED", "NEEDS_REVISION", "RENDER_READY"]
        try:
            return status_order.index(status_after) > status_order.index(status_before)
        except ValueError:
            return False


def format_regression_report(report: RegressionReport) -> str:
    """
    Format regression report as human-readable text.

    Returns:
        Multi-line formatted report
    """
    lines = [
        "=" * 60,
        f"REGRESSION CHECK: {report.version_before} → {report.version_after}",
        "=" * 60,
        "",
        f"Overall Score:  {report.score_before:.1f} → {report.score_after:.1f} ({report.score_delta:+.1f})",
        f"Status:         {report.status_before} → {report.status_after}",
        f"Recommendation: {report.recommendation}",
        "",
        report.summary,
        "",
    ]

    # Critical regressions
    if report.critical_regressions:
        lines.append(f"⚠️  CRITICAL REGRESSIONS ({len(report.critical_regressions)}):")
        for issue in report.critical_regressions:
            lines.append(f"  • {issue.message}")
            lines.append(f"    → {issue.recommendation}")
        lines.append("")

    # Warning regressions
    if report.warning_regressions:
        lines.append(f"⚡ WARNING REGRESSIONS ({len(report.warning_regressions)}):")
        for issue in report.warning_regressions:
            lines.append(f"  • {issue.message}")
        lines.append("")

    # Concerns
    if report.concerns:
        lines.append(f"ℹ️  CONCERNS ({len(report.concerns)}):")
        for issue in report.concerns:
            lines.append(f"  • {issue.message}")
        lines.append("")

    # Improvements
    if report.fixed_rules:
        lines.append(f"✅ FIXED RULES ({len(report.fixed_rules)}):")
        for rule_id in report.fixed_rules:
            lines.append(f"  • {rule_id}")
        lines.append("")

    if report.improved_families:
        lines.append(f"📈 IMPROVED FAMILIES: {', '.join(report.improved_families)}")
    if report.degraded_families:
        lines.append(f"📉 DEGRADED FAMILIES: {', '.join(report.degraded_families)}")

    lines.append("=" * 60)
    return "\n".join(lines)
