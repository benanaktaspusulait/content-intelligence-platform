"""
Quality Scoring System

Enhanced scoring with detailed breakdowns, trends, and recommendations.
Builds on top of the canonical :class:`QualityReport` from the rule engine and
produces the canonical :class:`EnhancedQualityReport`.
"""

from dataclasses import dataclass, field
from typing import Any

from ..quality.contracts import (
    EnhancedQualityReport,
    ParserMetadata,
    PriorityFix,
    QualityReport,
    QualityStatus,
    RuleEvaluation,
    RuleOutcome,
    ScoreBreakdown,
    Severity,
)
from ..quality.family_weights import CANONICAL_FAMILY_WEIGHTS

# Re-exported so existing ``from app.scoring.quality_scorer import
# EnhancedQualityReport, PriorityFix`` imports keep resolving to the canonical
# contract types.
__all__ = [
    "EnhancedQualityReport",
    "PriorityFix",
    "ScoreBreakdown",
    "QualityScorer",
    "QualityTrend",
    "create_enhanced_report",
]


@dataclass
class QualityTrend:
    """Track quality changes across versions."""

    version: int
    score: float
    status: str
    timestamp: str

    score_delta: float | None = None
    improved_families: list[str] = field(default_factory=list)
    regressed_families: list[str] = field(default_factory=list)


class QualityScorer:
    """
    Enhanced scoring system that provides detailed analysis
    and actionable recommendations.
    """

    # Family weights (from QUALITY_FAMILY_SCHEMAS)
    FAMILY_WEIGHTS = CANONICAL_FAMILY_WEIGHTS

    # Score thresholds
    EXCELLENT_THRESHOLD = 90
    GOOD_THRESHOLD = 80
    ACCEPTABLE_THRESHOLD = 70
    WEAK_THRESHOLD = 60

    def __init__(self) -> None:
        self.version_history: list[QualityTrend] = []

    def create_enhanced_report(
        self,
        quality_report: QualityReport,
        video_plan_ir: dict[str, Any],
        parser_metadata: ParserMetadata,
    ) -> EnhancedQualityReport:
        """Create the canonical enhanced report.

        This is the single scorer signature: it always takes the quality
        report, the originating video plan IR (for timeline data), and the
        parser metadata. It returns an :class:`EnhancedQualityReport` that
        wraps the ``base_report`` rather than copying its scalar fields.
        """

        score_breakdowns = tuple(
            self._create_score_breakdowns(
                quality_report.evaluations,
                quality_report.family_scores,
            )
        )

        return EnhancedQualityReport(
            base_report=quality_report,
            score_breakdowns=score_breakdowns,
            score_card=self._create_score_card(quality_report),
            timeline_data=self._create_timeline_data(video_plan_ir),
            family_radar=self._create_family_radar(quality_report.family_scores),
            top_3_strengths=tuple(self._identify_top_strengths(score_breakdowns)[:3]),
            top_3_weaknesses=tuple(self._identify_top_weaknesses(score_breakdowns)[:3]),
            priority_fixes=tuple(
                self._generate_priority_fixes(
                    quality_report.failed_rules,
                    quality_report.status,
                )
            ),
            parser_metadata=parser_metadata,
        )

    def _create_score_breakdowns(
        self,
        evaluations: tuple[RuleEvaluation, ...],
        family_scores: dict[str, float],
    ) -> list[ScoreBreakdown]:
        """Create detailed breakdown for each family."""

        family_evals: dict[str, list[RuleEvaluation]] = {}
        for ev in evaluations:
            family_evals.setdefault(ev.family, []).append(ev)

        breakdowns: list[ScoreBreakdown] = []
        for family, score in family_scores.items():
            evals = family_evals.get(family, [])

            passed = sum(
                1 for e in evals if e.outcome is RuleOutcome.PASS and e.configured_severity is Severity.PASS
            )
            failed = sum(1 for e in evals if e.outcome is RuleOutcome.FAIL)
            warning = sum(1 for e in evals if e.configured_severity is Severity.WARNING)

            strengths = tuple(
                e.message
                for e in evals
                if e.outcome is RuleOutcome.PASS and e.configured_severity is Severity.PASS
            )
            weaknesses = tuple(f"{e.rule_name}: {e.message}" for e in evals if e.outcome is RuleOutcome.FAIL)
            recommendations = tuple(self._generate_family_recommendations(family, evals))

            weight = self.FAMILY_WEIGHTS.get(family, 0.05)
            contribution = score * weight

            breakdowns.append(
                ScoreBreakdown(
                    family=family,
                    score=score,
                    weight=weight,
                    weighted_contribution=contribution,
                    rules_passed=passed,
                    rules_failed=failed,
                    rules_warning=warning,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    recommendations=recommendations,
                )
            )

        breakdowns.sort(key=lambda b: b.weighted_contribution, reverse=True)
        return breakdowns

    def _generate_family_recommendations(self, family: str, evaluations: list[RuleEvaluation]) -> list[str]:
        """Generate actionable recommendations for a family."""

        recommendations: list[str] = []
        for ev in evaluations:
            if ev.outcome is RuleOutcome.FAIL:
                rec = self._get_rule_recommendation(ev.rule_id, ev)
                if rec:
                    recommendations.append(rec)
        return recommendations

    def _get_rule_recommendation(self, rule_id: str, evaluation: RuleEvaluation) -> str | None:
        """Get specific recommendation for a failed rule."""
        # Keep rule-specific formatting lazy. Evaluation values are deliberately
        # heterogeneous (for example, producibility diagnostics may be a list),
        # so building every f-string up front can crash on an unrelated rule.
        if rule_id == "CONCEPT_006":
            count = evaluation.actual_value if isinstance(evaluation.actual_value, (int, float)) else 0
            return (
                f"Add {max(0, 4 - count)} more visually distinct consequences. "
                "Consider introducing new obstacles or props."
            )
        if rule_id == "BEAT_004":
            percentage = evaluation.actual_value if isinstance(evaluation.actual_value, (int, float)) else 0
            return (
                f"Reduce time in '{evaluation.details.get('state_id', 'dominant state')}' by "
                f"~{percentage - 25:.0f}%. Add transitions or new visual states."
            )
        if rule_id == "REPETITION_002":
            return (
                f"Reduce '{evaluation.details.get('action', 'repeated action')}' from "
                f"{evaluation.actual_value} to 2-3 occurrences with escalation."
            )
        if rule_id == "REPETITION_003":
            return "Break the cycle after 2 iterations. Introduce new physical element (break, obstacle, or character intervention)."
        if rule_id == "NOVELTY_001":
            return (
                f"Add 1-2 new consequences between {evaluation.details.get('gap_start', '?')}s "
                f"and {evaluation.details.get('gap_end', '?')}s."
            )
        if rule_id == "PROGRESSION_005":
            return "Add new physical consequences in middle section (4-11s). Avoid pure dialogue variations."
        if rule_id == "ESCALATION_004":
            if evaluation.threshold_value is not None:
                return f"Move final escalation earlier (before {evaluation.threshold_value:.0f}%) or strengthen middle section."
            return "Move final escalation earlier."
        if rule_id == "PAYOFF_001":
            return "Change final beat. Make it bigger, add twist, or introduce new element. Don't repeat opening."
        if rule_id == "PRODUCIBILITY_001":
            return "Simplify complex operations. Reduce simultaneous hand-object interactions or morphing effects."
        if rule_id == "CONSISTENCY_001":
            return "Maintain consistent physics rule throughout, or justify rule change as part of concept."

        configured = evaluation.details.get("recommendation")
        return str(configured).strip() if configured else None

    def _identify_top_strengths(self, breakdowns: tuple[ScoreBreakdown, ...]) -> list[str]:
        """Identify top strengths across all families."""

        strengths: list[str] = []
        for breakdown in breakdowns:
            if breakdown.score >= self.EXCELLENT_THRESHOLD:
                strengths.append(f"{breakdown.family.replace('_', ' ').title()}: {breakdown.score:.0f}/100")
        return strengths

    def _identify_top_weaknesses(self, breakdowns: tuple[ScoreBreakdown, ...]) -> list[str]:
        """Identify top weaknesses that need attention."""

        weaknesses: list[str] = []
        sorted_breakdowns = sorted(breakdowns, key=lambda b: (b.score, -b.weight))
        for breakdown in sorted_breakdowns:
            if breakdown.score < self.ACCEPTABLE_THRESHOLD:
                weakness_str = f"{breakdown.family.replace('_', ' ').title()}: {breakdown.score:.0f}/100"
                if breakdown.weaknesses:
                    weakness_str += f" - {breakdown.weaknesses[0][:60]}"
                weaknesses.append(weakness_str)
        return weaknesses

    def _generate_priority_fixes(
        self,
        failed_rules: tuple[RuleEvaluation, ...],
        status: QualityStatus,
    ) -> list[PriorityFix]:
        """Generate a prioritized list of typed fixes."""

        severity_order = {Severity.BLOCKER: 0, Severity.CRITICAL: 1, Severity.WARNING: 2}
        sorted_failures = sorted(
            failed_rules,
            key=lambda r: severity_order.get(r.configured_severity, 3),
        )

        priority_fixes: list[PriorityFix] = []
        for i, rule in enumerate(sorted_failures[:5], 1):
            priority_fixes.append(
                PriorityFix.from_evaluation(
                    priority=i,
                    evaluation=rule,
                    recommendation=self._get_rule_recommendation(rule.rule_id, rule) or "",
                    impact=self._estimate_fix_impact(rule.configured_severity),
                )
            )
        return priority_fixes

    def _estimate_fix_impact(self, severity: Severity) -> str:
        """Estimate impact of fixing a rule."""

        impact_map = {
            Severity.BLOCKER: "Critical - Required for render",
            Severity.CRITICAL: "High - Major score improvement",
            Severity.WARNING: "Medium - Incremental improvement",
        }
        return impact_map.get(severity, "Low")

    def _create_score_card(self, quality_report: QualityReport) -> dict[str, Any]:
        """Create summary card data for UI."""

        score = quality_report.overall_score
        if score >= 92:
            color, label = "green", "Excellent"
        elif score >= 80:
            color, label = "blue", "Good"
        elif score >= 70:
            color, label = "yellow", "Acceptable"
        elif score >= 60:
            color, label = "orange", "Weak"
        else:
            color, label = "red", "Poor"

        return {
            "score": score,
            "label": label,
            "color": color,
            "status": quality_report.status.value,
            "blockers": quality_report.blocker_count,
            "criticals": quality_report.critical_count,
            "warnings": quality_report.warning_count,
            "passes": quality_report.pass_count,
            "is_render_ready": quality_report.is_render_ready,
        }

    def _create_timeline_data(self, video_plan_ir: dict[str, Any]) -> dict[str, Any]:
        """Create timeline visualization data with DTO-aligned keys.

        The keys here match :class:`app.api.quality.TimelineDataResponse`
        exactly so the API conversion is a single, mechanical mapping layer.
        """

        beats = video_plan_ir.get("beats", [])
        total_duration = video_plan_ir.get("metadata", {}).get("duration", 15.0) or 15.0

        beat_dtos: list[dict[str, Any]] = []
        consequence_markers: list[dict[str, Any]] = []
        for beat in beats:
            beat_dtos.append(
                {
                    "start_time": beat.get("startTime", 0.0),
                    "end_time": beat.get("endTime", 0.0),
                    "action": beat.get("action", ""),
                    "consequence": beat.get("consequence", ""),
                    "intensity": beat.get("intensity", 5),
                    "is_new_consequence": beat.get("isNewConsequence", False),
                }
            )
            if beat.get("isNewConsequence"):
                consequence_markers.append(
                    {
                        "time": beat.get("startTime", 0.0),
                        "consequence": beat.get("consequence", ""),
                        "type": beat.get("consequenceType", "new"),
                    }
                )

        state_segments: list[dict[str, Any]] = []
        current_segment: dict[str, Any] | None = None
        for beat in beats:
            state_id = beat.get("visualStateId")
            if current_segment is None or current_segment["state_id"] != state_id:
                if current_segment is not None:
                    state_segments.append(current_segment)
                current_segment = {
                    "state_id": state_id,
                    "start_time": beat.get("startTime", 0.0),
                    "end_time": beat.get("endTime", 0.0),
                }
            else:
                current_segment["end_time"] = beat.get("endTime", 0.0)
        if current_segment is not None:
            state_segments.append(current_segment)

        for segment in state_segments:
            duration = segment["end_time"] - segment["start_time"]
            segment["percentage"] = (duration / total_duration) * 100 if total_duration else 0.0

        return {
            "duration": total_duration,
            "beats": beat_dtos,
            "consequence_markers": consequence_markers,
            "state_segments": state_segments,
        }

    def _create_family_radar(self, family_scores: dict[str, float]) -> dict[str, Any]:
        """Create radar chart data."""

        ordered_families = [
            "concept_strength",
            "hook_strength",
            "visual_novelty",
            "progression",
            "escalation",
            "motion_quality",
            "readability",
            "ai_producibility",
            "consistency",
            "final_payoff",
            "render_risk",
        ]

        scores = [family_scores.get(family, 0) for family in ordered_families]
        labels = [family.replace("_", " ").title() for family in ordered_families]

        return {
            "labels": labels,
            "scores": scores,
            "thresholds": {"excellent": 90, "good": 80, "acceptable": 70},
        }

    def track_version(
        self,
        enhanced_report: EnhancedQualityReport,
        previous_report: EnhancedQualityReport | None = None,
    ) -> QualityTrend:
        """Track quality trend across versions."""

        version = int(enhanced_report.base_report.evaluated_at != "unknown") + len(self.version_history)
        trend = QualityTrend(
            version=version,
            score=enhanced_report.overall_score,
            status=enhanced_report.status.value,
            timestamp=enhanced_report.evaluated_at,
        )

        if previous_report:
            trend.score_delta = enhanced_report.overall_score - previous_report.overall_score
            current_families = {b.family: b.score for b in enhanced_report.score_breakdowns}
            previous_families = {b.family: b.score for b in previous_report.score_breakdowns}
            for family in current_families:
                if family in previous_families:
                    delta = current_families[family] - previous_families[family]
                    if delta > 5:
                        trend.improved_families.append(family)
                    elif delta < -5:
                        trend.regressed_families.append(family)

        self.version_history.append(trend)
        return trend

    def get_version_history(self) -> list[QualityTrend]:
        """Get complete version history."""

        return self.version_history


def create_enhanced_report(
    quality_report: QualityReport,
    video_plan_ir: dict[str, Any],
    parser_metadata: ParserMetadata,
) -> EnhancedQualityReport:
    """Convenience function to create an enhanced report."""

    scorer = QualityScorer()
    return scorer.create_enhanced_report(quality_report, video_plan_ir, parser_metadata)
