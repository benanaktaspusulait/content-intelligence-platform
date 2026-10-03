"""
Rule Engine Executor

Evaluates Video Plan IR against ruleset and generates quality report.
Integrates parser, analyzers, and rule definitions.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from app.analyzer.consequence_analyzer import analyze_consequences
from app.analyzer.static_state_analyzer import analyze_static_states
from app.llm.semantic_checks import (
    SemanticCheckServiceError,
    check_twist_matches_rule,
    find_duplicate_strategy_pairs,
)
from app.qa.character_verifier import CharacterVerifier
from app.quality.contracts import (
    QualityReport,
    QualityStatus,
    RuleOutcome,
    Severity,
)
from app.quality.contracts import RuleEvaluation as _RuleEvaluation

# Re-export the canonical types so existing ``from app.rules.rule_engine
# import RuleEvaluation, QualityReport`` call sites keep working.
RuleEvaluationType = _RuleEvaluation


def RuleEvaluation(
    rule_id: str,
    rule_name: str,
    family: str,
    severity: str,
    result: str,
    message: str,
    actual_value: Any = None,
    required_value: Any = None,
    threshold_value: Any = None,
    details: dict[str, Any] | None = None,
) -> _RuleEvaluation:
    """Build a canonical :class:`RuleEvaluation`.

    This factory maps the engine's stringly-typed ``severity``/``result`` into
    the canonical :class:`Severity`/:class:`RuleOutcome` enums so the rule
    evaluators below can stay declarative while the stored value stays typed.
    """

    return _RuleEvaluation(
        rule_id=rule_id,
        rule_name=rule_name,
        family=family,
        outcome=RuleOutcome(result),
        configured_severity=Severity(severity),
        message=message,
        actual_value=actual_value,
        required_value=required_value,
        threshold_value=threshold_value,
        details=details or {},
    )


class RuleEngine:
    """
    Main rule engine that evaluates Video Plan IR.

    Architecture:
    1. Load ruleset YAML
    2. For each rule, call appropriate evaluator
    3. Aggregate results into quality report
    4. Calculate scores and determine status
    """

    def __init__(self, ruleset_path: str | None = None) -> None:
        """
        Initialize rule engine.

        Args:
            ruleset_path: Path to ruleset YAML file (defaults to RULESET_1.0.yaml)
        """
        resolved_path: str | Path
        if ruleset_path is None:
            # Default to RULESET_1.0.yaml
            base_path = Path(__file__).parent.parent.parent
            resolved_path = base_path / "data" / "rules" / "RULESET_1.0.yaml"
        else:
            resolved_path = ruleset_path

        self.ruleset_path = Path(resolved_path)
        self.ruleset = self._load_ruleset()

        # Rule evaluator registry
        self.evaluators = {
            "CONCEPT_006": self._evaluate_concept_006,
            "BEAT_004": self._evaluate_beat_004,
            "REPETITION_002": self._evaluate_repetition_002,
            "REPETITION_003": self._evaluate_repetition_003,
            "NOVELTY_001": self._evaluate_novelty_001,
            "PROGRESSION_005": self._evaluate_progression_005,
            "ESCALATION_004": self._evaluate_escalation_004,
            "PAYOFF_001": self._evaluate_payoff_001,
            "PRODUCIBILITY_001": self._evaluate_producibility_001,
            "CONSISTENCY_001": self._evaluate_consistency_001,
            "HOOK_002": self._evaluate_hook_002,
            "HOOK_003": self._evaluate_hook_003,
            "MOTION_001": self._evaluate_motion_001,
            "ATTEMPT_001": self._evaluate_attempt_001,
            "CHAR_002": self._evaluate_char_002,
            "PRODUCIBILITY_002": self._evaluate_producibility_002,
            "PAYOFF_002": self._evaluate_payoff_002,
            "ATTEMPT_002": self._evaluate_attempt_002,
            "PAYOFF_003": self._evaluate_payoff_003,
            "CONSISTENCY_002": self._evaluate_consistency_002,
            "BEAT_005": self._evaluate_beat_005,
            "PAYOFF_004": self._evaluate_payoff_004,
            "REPETITION_004": self._evaluate_repetition_004,
            "PAYOFF_006": self._evaluate_payoff_006,
        }

    def _get_duration_tier(self, duration: float) -> str:
        """Derive the duration tier used by tier-aware rules.

        Tier is always computed at evaluation time from metadata.duration; it
        is never persisted on the Video Plan IR itself.
        """
        return "short" if duration <= 20.0 else "long"

    def _load_ruleset(self) -> dict[str, Any]:
        """Load ruleset from YAML file"""
        with open(self.ruleset_path) as f:
            loaded: dict[str, Any] = yaml.safe_load(f)
            return loaded

    def evaluate(self, video_plan_ir: dict[str, Any]) -> QualityReport:
        """
        Evaluate Video Plan IR against all rules.

        Returns QualityReport with complete analysis.
        """
        evaluations = []

        # Evaluate each rule
        for rule in self.ruleset.get("rules", []):
            rule_id = rule["id"]

            if rule_id in self.evaluators:
                evaluation = self.evaluators[rule_id](video_plan_ir, rule)
                evaluations.append(evaluation)
            else:
                # No registered evaluator: fail closed with SERVICE_ERROR rather
                # than silently passing an unchecked rule. The configured
                # severity escalates to BLOCKER so readiness/validation cannot
                # report RENDER_READY while a rule went unevaluated.
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule_id,
                        rule_name=rule.get("name", rule_id),
                        family=rule.get("family", "unknown"),
                        severity="BLOCKER",
                        result="SERVICE_ERROR",
                        message=f"Rule {rule_id} has no registered evaluator.",
                        details={"missing_evaluator": True},
                    )
                )

        # Aggregate results
        return self._generate_report(evaluations, video_plan_ir)

    def _generate_report(
        self, evaluations: list[RuleEvaluationType], video_plan_ir: dict[str, Any]
    ) -> QualityReport:
        """Generate quality report from evaluations.

        Severity counts are derived accessors on :class:`QualityReport`; this
        method only computes scores and the overall status. A fail-closed
        SERVICE_ERROR forces a SERVICE_ERROR status so the pipeline never
        reports readiness while a rule went unevaluated.
        """

        blocker_count = sum(
            1
            for e in evaluations
            if e.outcome is RuleOutcome.FAIL and e.configured_severity is Severity.BLOCKER
        )
        critical_count = sum(
            1
            for e in evaluations
            if e.outcome is RuleOutcome.FAIL and e.configured_severity is Severity.CRITICAL
        )
        service_error_count = sum(1 for e in evaluations if e.outcome is RuleOutcome.SERVICE_ERROR)

        # Calculate family scores and overall score
        family_scores = self._calculate_family_scores(evaluations)
        overall_score = self._calculate_overall_score(family_scores, evaluations)

        # Determine status (fail closed on service errors)
        if service_error_count > 0:
            status = QualityStatus.SERVICE_ERROR
        elif overall_score >= 92 and blocker_count == 0 and critical_count == 0:
            status = QualityStatus.RENDER_READY
        elif overall_score < 80 or blocker_count > 0:
            status = QualityStatus.BLOCKED
        else:
            status = QualityStatus.NEEDS_REVISION

        return QualityReport(
            overall_score=overall_score,
            status=status,
            family_scores=family_scores,
            evaluations=tuple(evaluations),
            ruleset_version=self.ruleset.get("version", "1.0"),
            evaluated_at=video_plan_ir.get("metadata", {}).get("createdAt", "unknown"),
        )

    def _calculate_family_scores(self, evaluations: list[RuleEvaluationType]) -> dict[str, float]:
        """Calculate score for each quality family"""
        family_scores: dict[str, float] = {}
        family_rules: dict[str, list[RuleEvaluationType]] = {}

        # Group evaluations by family
        for eval in evaluations:
            family = eval.family
            if family not in family_rules:
                family_rules[family] = []
            family_rules[family].append(eval)

        # Calculate score for each family
        for family, rules in family_rules.items():
            total_score = 0
            count = 0

            for rule in rules:
                if rule.outcome is RuleOutcome.PASS:
                    if rule.configured_severity is Severity.PASS:
                        total_score += 100
                    elif rule.configured_severity is Severity.WARNING:
                        total_score += 85
                    count += 1
                elif rule.outcome is RuleOutcome.FAIL:
                    if rule.configured_severity is Severity.BLOCKER:
                        total_score += 0
                    elif rule.configured_severity is Severity.CRITICAL:
                        total_score += 40
                    elif rule.configured_severity is Severity.WARNING:
                        total_score += 70
                    count += 1
                elif rule.outcome is RuleOutcome.SERVICE_ERROR:
                    # Unevaluated rule contributes a zero so the family (and the
                    # overall score) cannot float up on missing coverage.
                    total_score += 0
                    count += 1
                elif rule.outcome is RuleOutcome.NOT_APPLICABLE:
                    # The rule does not apply to this concept by design (e.g. no
                    # fake-win beat present). Excluded from both numerator and
                    # denominator — contributes neither a pass nor a fail signal.
                    pass
                elif rule.outcome is RuleOutcome.UNKNOWN:
                    # Evidence to evaluate this rule is currently missing (e.g. no
                    # rendered video yet). Excluded from scoring for a different
                    # reason than NOT_APPLICABLE — tracked separately via
                    # QualityReport.unknown_count for observability.
                    pass

            family_scores[family] = total_score / count if count > 0 else 0

        return family_scores

    def _calculate_overall_score(
        self, family_scores: dict[str, float], evaluations: list[RuleEvaluationType]
    ) -> float:
        """Calculate weighted overall score"""

        # Family weights from schema
        weights = {
            "concept_strength": 0.12,
            "hook_strength": 0.12,
            "visual_novelty": 0.14,
            "progression": 0.11,
            "escalation": 0.10,
            "motion_quality": 0.09,
            "readability": 0.08,
            "ai_producibility": 0.10,
            "consistency": 0.07,
            "final_payoff": 0.09,
            "render_risk": 0.08,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for family, score in family_scores.items():
            weight = weights.get(family, 0.05)  # Default weight if not found
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    # ========================================
    # RULE EVALUATORS
    # ========================================

    def _evaluate_concept_006(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """CONCEPT_006: Consequence Capacity"""
        metrics = analyze_consequences(video_plan_ir)
        count = metrics.distinct_consequence_count

        if count < 4:
            return RuleEvaluation(
                rule_id="CONCEPT_006",
                rule_name="Consequence Capacity",
                family="concept_strength",
                severity="BLOCKER",
                result="FAIL",
                message=(
                    f"Only {count} distinct visual consequences detected. Minimum: 4. "
                    "Core mechanic insufficient for 15 seconds."
                ),
                actual_value=count,
                required_value=4,
            )
        elif count == 4:
            return RuleEvaluation(
                rule_id="CONCEPT_006",
                rule_name="Consequence Capacity",
                family="concept_strength",
                severity="WARNING",
                result="PASS",
                message="Exactly 4 consequences. Consider adding 1-2 more for stronger engagement.",
                actual_value=count,
                required_value=5,
            )
        else:
            return RuleEvaluation(
                rule_id="CONCEPT_006",
                rule_name="Consequence Capacity",
                family="concept_strength",
                severity="PASS",
                result="PASS",
                message=f"Sufficient consequence variety: {count} distinct consequences.",
                actual_value=count,
                required_value=4,
            )

    def _evaluate_beat_004(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """BEAT_004: Static State Dominance"""
        metrics = analyze_static_states(video_plan_ir)
        percentage = metrics.dominant_state_percentage
        state_id = metrics.dominant_state_id

        if percentage > 35:
            return RuleEvaluation(
                rule_id="BEAT_004",
                rule_name="Static State Dominance",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Visual state '{state_id}' occupies {percentage:.1f}% of video. "
                    "Maximum: 30%. Video feels static."
                ),
                actual_value=percentage,
                threshold_value=30.0,
                details={"state_id": state_id},
            )
        elif percentage > 30:
            return RuleEvaluation(
                rule_id="BEAT_004",
                rule_name="Static State Dominance",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=f"Visual state '{state_id}' occupies {percentage:.1f}% of video. Maximum: 30%.",
                actual_value=percentage,
                threshold_value=30.0,
                details={"state_id": state_id},
            )
        elif percentage > 25:
            return RuleEvaluation(
                rule_id="BEAT_004",
                rule_name="Static State Dominance",
                family="visual_novelty",
                severity="WARNING",
                result="PASS",
                message=(
                    f"Visual state '{state_id}' occupies {percentage:.1f}% of video. "
                    "Consider adding variation."
                ),
                actual_value=percentage,
                threshold_value=25.0,
                details={"state_id": state_id},
            )
        else:
            return RuleEvaluation(
                rule_id="BEAT_004",
                rule_name="Static State Dominance",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message=f"Good visual state distribution. Max state: {percentage:.1f}%.",
                actual_value=percentage,
                threshold_value=30.0,
            )

    def _evaluate_repetition_002(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """REPETITION_002: Visual Beat Repetition"""
        beats = video_plan_ir.get("beats", [])

        # Count action frequencies
        action_counts: dict[str, int] = {}
        for beat in beats:
            # Normalize action for comparison
            action = beat.get("action", "").lower().strip()
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1

        if not action_counts:
            return RuleEvaluation(
                rule_id="REPETITION_002",
                rule_name="Visual Beat Repetition",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message="No actions to evaluate",
            )

        max_action = max(action_counts.keys(), key=lambda k: action_counts[k])
        max_count = action_counts[max_action]

        if max_count > 3:
            return RuleEvaluation(
                rule_id="REPETITION_002",
                rule_name="Visual Beat Repetition",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Action '{max_action}' repeats {max_count} times. "
                    "Maximum: 2-3 with escalation. Video feels repetitive."
                ),
                actual_value=max_count,
                threshold_value=3,
                details={"action": max_action},
            )
        elif max_count == 3:
            # Check if all have different consequences (simplified check)
            similar_beats = [b for b in beats if b.get("action", "").lower().strip() == max_action]
            all_different = all(
                b.get("consequenceType") == "new" or b.get("consequenceType") == "escalation"
                for b in similar_beats[1:]
            )

            if not all_different:
                return RuleEvaluation(
                    rule_id="REPETITION_002",
                    rule_name="Visual Beat Repetition",
                    family="visual_novelty",
                    severity="CRITICAL",
                    result="FAIL",
                    message=(
                        f"Action '{max_action}' repeats 3 times without distinct "
                        "consequences. Add variation or new obstacles."
                    ),
                    actual_value=max_count,
                    threshold_value=2,
                )
            else:
                return RuleEvaluation(
                    rule_id="REPETITION_002",
                    rule_name="Visual Beat Repetition",
                    family="visual_novelty",
                    severity="WARNING",
                    result="PASS",
                    message=(
                        f"Action '{max_action}' appears 3 times but with escalating "
                        "consequences. Consider if more variation possible."
                    ),
                    actual_value=max_count,
                    threshold_value=3,
                )
        else:
            return RuleEvaluation(
                rule_id="REPETITION_002",
                rule_name="Visual Beat Repetition",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message=f"Good action variety. Max repetition: {max_count}.",
                actual_value=max_count,
                threshold_value=2,
            )

    def _evaluate_repetition_003(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """REPETITION_003: Cycle Repetition Limit"""
        beats = video_plan_ir.get("beats", [])

        # Detect cycles (simplified - checks for cycleGroup field)
        cycle_groups: dict[str, int] = {}
        for beat in beats:
            cycle_group = beat.get("cycleGroup")
            if cycle_group:
                cycle_groups[cycle_group] = cycle_groups.get(cycle_group, 0) + 1

        if not cycle_groups:
            # No explicit cycles detected - fallback to pattern detection
            # For now, pass if no cycleGroup marked
            return RuleEvaluation(
                rule_id="REPETITION_003",
                rule_name="Cycle Repetition Limit",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message="No explicit cycles detected.",
                actual_value=0,
                threshold_value=2,
            )

        max_cycle = max(cycle_groups.keys(), key=lambda k: cycle_groups[k])
        max_count = cycle_groups[max_cycle]

        if max_count > 3:
            return RuleEvaluation(
                rule_id="REPETITION_003",
                rule_name="Cycle Repetition Limit",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Cycle '{max_cycle}' repeats {max_count} times. Maximum: 2-3 with "
                    "escalation. Add new obstacles or consequences."
                ),
                actual_value=max_count,
                threshold_value=3,
            )
        elif max_count == 3:
            return RuleEvaluation(
                rule_id="REPETITION_003",
                rule_name="Cycle Repetition Limit",
                family="visual_novelty",
                severity="WARNING",
                result="PASS",
                message=f"Cycle '{max_cycle}' repeats 3 times. Acceptable but consider more variety.",
                actual_value=max_count,
                threshold_value=2,
            )
        else:
            return RuleEvaluation(
                rule_id="REPETITION_003",
                rule_name="Cycle Repetition Limit",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message=f"Good cycle variety. Max iterations: {max_count}.",
                actual_value=max_count,
                threshold_value=2,
            )

    def _evaluate_novelty_001(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """NOVELTY_001: Novelty Timeline Distribution"""
        metrics = analyze_consequences(video_plan_ir)
        gap = metrics.longest_novelty_gap_seconds
        gap_start = metrics.longest_gap_start_time
        gap_end = metrics.longest_gap_end_time

        if gap > 6.0:
            return RuleEvaluation(
                rule_id="NOVELTY_001",
                rule_name="Novelty Timeline Distribution",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Gap of {gap:.1f}s between new consequences "
                    f"(at {gap_start:.1f}s-{gap_end:.1f}s). Video likely loses viewer attention."
                ),
                actual_value=gap,
                threshold_value=4.5,
            )
        elif gap > 4.5:
            return RuleEvaluation(
                rule_id="NOVELTY_001",
                rule_name="Novelty Timeline Distribution",
                family="visual_novelty",
                severity="WARNING",
                result="PASS",
                message=(
                    f"Gap of {gap:.1f}s between new consequences "
                    f"(at {gap_start:.1f}s-{gap_end:.1f}s). Consider adding intermediate beat."
                ),
                actual_value=gap,
                threshold_value=4.5,
            )
        else:
            return RuleEvaluation(
                rule_id="NOVELTY_001",
                rule_name="Novelty Timeline Distribution",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message=f"Good novelty distribution. Max gap: {gap:.1f}s.",
                actual_value=gap,
                threshold_value=4.5,
            )

    def _evaluate_progression_005(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """PROGRESSION_005: Consequence Novelty Timeline"""
        beats = video_plan_ir.get("beats", [])
        total_duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)

        if not beats:
            return RuleEvaluation(
                rule_id="PROGRESSION_005",
                rule_name="Consequence Novelty Timeline",
                family="progression",
                severity="PASS",
                result="PASS",
                message="No beats to evaluate",
            )

        # Calculate time in static pattern (repeat/continuation beats)
        static_duration = sum(
            beat.get("duration", 0)
            for beat in beats
            if beat.get("consequenceType") in ["repeat", "continuation"]
        )

        static_percentage = (static_duration / total_duration) * 100 if total_duration > 0 else 0

        if static_percentage > 65:
            return RuleEvaluation(
                rule_id="PROGRESSION_005",
                rule_name="Consequence Novelty Timeline",
                family="progression",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"{static_percentage:.1f}% of video shows repetitive pattern "
                    "without new consequences. Maximum: 50%."
                ),
                actual_value=static_percentage,
                threshold_value=50.0,
            )
        elif static_percentage > 50:
            return RuleEvaluation(
                rule_id="PROGRESSION_005",
                rule_name="Consequence Novelty Timeline",
                family="progression",
                severity="WARNING",
                result="PASS",
                message=(
                    f"{static_percentage:.1f}% of video shows pattern repetition. "
                    "Consider adding new elements earlier."
                ),
                actual_value=static_percentage,
                threshold_value=50.0,
            )
        else:
            return RuleEvaluation(
                rule_id="PROGRESSION_005",
                rule_name="Consequence Novelty Timeline",
                family="progression",
                severity="PASS",
                result="PASS",
                message=f"Good novelty timeline. Static pattern: {static_percentage:.1f}%.",
                actual_value=static_percentage,
                threshold_value=50.0,
            )

    def _evaluate_escalation_004(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """ESCALATION_004: Delayed Payoff"""
        final_payoff = video_plan_ir.get("finalPayoff", {})
        total_duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)

        payoff_time = final_payoff.get("startsAt", total_duration - 3.0)
        payoff_percentage = (payoff_time / total_duration) * 100 if total_duration > 0 else 0

        # Check middle escalation (simplified)
        beats = video_plan_ir.get("beats", [])
        middle_beats = [b for b in beats if 4.0 <= b.get("startTime", 0) <= 11.0]
        middle_new_consequences = sum(1 for b in middle_beats if b.get("isNewConsequence", False))
        middle_weak = middle_new_consequences < 2

        if payoff_percentage > 80 and middle_weak:
            return RuleEvaluation(
                rule_id="ESCALATION_004",
                rule_name="Delayed Payoff",
                family="escalation",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Final payoff at {payoff_time:.1f}s ({payoff_percentage:.0f}%). "
                    "Repetitive middle + late payoff risks early exits."
                ),
                actual_value=payoff_percentage,
                threshold_value=75.0,
            )
        elif payoff_percentage > 80:
            return RuleEvaluation(
                rule_id="ESCALATION_004",
                rule_name="Delayed Payoff",
                family="escalation",
                severity="WARNING",
                result="PASS",
                message=f"Final payoff at {payoff_time:.1f}s. Late but middle is strong.",
                actual_value=payoff_percentage,
                threshold_value=80.0,
            )
        elif payoff_percentage > 75:
            return RuleEvaluation(
                rule_id="ESCALATION_004",
                rule_name="Delayed Payoff",
                family="escalation",
                severity="WARNING",
                result="PASS",
                message=(
                    f"Final payoff at {payoff_time:.1f}s. Consider moving earlier for stronger retention."
                ),
                actual_value=payoff_percentage,
                threshold_value=75.0,
            )
        else:
            return RuleEvaluation(
                rule_id="ESCALATION_004",
                rule_name="Delayed Payoff",
                family="escalation",
                severity="PASS",
                result="PASS",
                message=f"Good payoff timing at {payoff_time:.1f}s.",
                actual_value=payoff_percentage,
                threshold_value=75.0,
            )

    def _evaluate_payoff_001(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """PAYOFF_001: Not Repeat of Opening"""
        final_payoff = video_plan_ir.get("finalPayoff", {})
        is_repeat = final_payoff.get("isRepeatOfOpening", False)

        if is_repeat:
            return RuleEvaluation(
                rule_id="PAYOFF_001",
                rule_name="Not Repeat of Opening",
                family="final_payoff",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    "Final beat repeats opening action without escalation. Payoff must be unique or bigger."
                ),
                actual_value=True,
                required_value=False,
            )
        else:
            return RuleEvaluation(
                rule_id="PAYOFF_001",
                rule_name="Not Repeat of Opening",
                family="final_payoff",
                severity="PASS",
                result="PASS",
                message="Final payoff is distinct from opening.",
                actual_value=False,
                required_value=False,
            )

    def _evaluate_producibility_001(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """PRODUCIBILITY_001: Very High Complexity Block"""
        producibility = video_plan_ir.get("producibility", {})
        complexity = producibility.get("overallComplexity", "low")

        if complexity == "very_high":
            return RuleEvaluation(
                rule_id="PRODUCIBILITY_001",
                rule_name="Very High Complexity Block",
                family="ai_producibility",
                severity="BLOCKER",
                result="FAIL",
                message=(
                    "Overall complexity: very_high. High risk of render failure. Simplify or accept risk."
                ),
                actual_value=complexity,
                required_value="high or lower",
            )
        elif complexity == "high":
            return RuleEvaluation(
                rule_id="PRODUCIBILITY_001",
                rule_name="Very High Complexity Block",
                family="ai_producibility",
                severity="WARNING",
                result="PASS",
                message="Overall complexity: high. Render uncertain. Consider simplifications.",
                actual_value=complexity,
                required_value="medium or lower",
            )
        else:
            return RuleEvaluation(
                rule_id="PRODUCIBILITY_001",
                rule_name="Very High Complexity Block",
                family="ai_producibility",
                severity="PASS",
                result="PASS",
                message=f"Acceptable complexity: {complexity}.",
                actual_value=complexity,
                required_value="medium or lower",
            )

    def _evaluate_consistency_001(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """CONSISTENCY_001: Physics Rule Consistency"""
        core_mechanic = video_plan_ir.get("coreMechanic", {})
        consistency = core_mechanic.get("consistency", "consistent")

        if consistency == "breaking":
            return RuleEvaluation(
                rule_id="CONSISTENCY_001",
                rule_name="Physics Rule Consistency",
                family="consistency",
                severity="WARNING",
                result="FAIL",
                message=(
                    "Physics rule breaks mid-video without conceptual justification. May confuse viewers."
                ),
                actual_value=consistency,
                required_value="consistent",
            )
        else:
            return RuleEvaluation(
                rule_id="CONSISTENCY_001",
                rule_name="Physics Rule Consistency",
                family="consistency",
                severity="PASS",
                result="PASS",
                message="Physics rule remains consistent.",
                actual_value=consistency,
                required_value="consistent",
            )

    def _evaluate_hook_002(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """HOOK_002: First Frame Anomaly"""
        hook = video_plan_ir.get("hook", {})
        starts_mid_action = hook.get("startsMidAction", False)
        visual_strength = hook.get("visualStrength", 1)

        if not starts_mid_action:
            return RuleEvaluation(
                rule_id="HOOK_002",
                rule_name="First Frame Anomaly",
                family="hook_strength",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    "Hook does not start mid-action. The problem must already be visually "
                    "obvious within the opening second, with no setup or explanation."
                ),
                actual_value=starts_mid_action,
                required_value=True,
            )
        if visual_strength < 4:
            return RuleEvaluation(
                rule_id="HOOK_002",
                rule_name="First Frame Anomaly",
                family="hook_strength",
                severity="WARNING",
                result="FAIL",
                message=(
                    f"Hook starts mid-action but visual strength is only {visual_strength}/5. "
                    "The anomaly should be visually striking, not subtle."
                ),
                actual_value=visual_strength,
                required_value=4,
            )
        return RuleEvaluation(
            rule_id="HOOK_002",
            rule_name="First Frame Anomaly",
            family="hook_strength",
            severity="PASS",
            result="PASS",
            message=f"Hook starts mid-action with visual strength {visual_strength}/5.",
            actual_value=visual_strength,
            required_value=4,
        )

    def _evaluate_hook_003(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """HOOK_003: Sound Independence"""
        hook = video_plan_ir.get("hook", {})
        sound_off_clear = hook.get("soundOffClear", False)

        if not sound_off_clear:
            return RuleEvaluation(
                rule_id="HOOK_003",
                rule_name="Sound Independence",
                family="hook_strength",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    "Hook is not marked sound-off clear. The core problem and physical "
                    "comedy must work with audio muted."
                ),
                actual_value=sound_off_clear,
                required_value=True,
            )
        return RuleEvaluation(
            rule_id="HOOK_003",
            rule_name="Sound Independence",
            family="hook_strength",
            severity="PASS",
            result="PASS",
            message="Hook is understandable without audio.",
            actual_value=sound_off_clear,
            required_value=True,
        )

    def _evaluate_motion_001(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """MOTION_001: No Dead Air"""
        beats = video_plan_ir.get("beats", [])

        longest_dead_air = 0.0
        for beat in beats:
            if beat.get("motionAmount") == "none":
                duration = beat.get("duration", 0.0)
                if duration > longest_dead_air:
                    longest_dead_air = duration

        if longest_dead_air > 1.5:
            return RuleEvaluation(
                rule_id="MOTION_001",
                rule_name="No Dead Air",
                family="motion_quality",
                severity="WARNING",
                result="FAIL",
                message=(
                    f"Longest static (no-motion) beat is {longest_dead_air:.1f}s. Maximum: 1.5s. "
                    "No beat should hold with zero motion for longer than this."
                ),
                actual_value=longest_dead_air,
                threshold_value=1.5,
            )
        return RuleEvaluation(
            rule_id="MOTION_001",
            rule_name="No Dead Air",
            family="motion_quality",
            severity="PASS",
            result="PASS",
            message=f"No excessive dead air. Longest static beat: {longest_dead_air:.1f}s.",
            actual_value=longest_dead_air,
            threshold_value=1.5,
        )

    def _evaluate_attempt_001(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """ATTEMPT_001: Attempt Count"""
        duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)
        tier = self._get_duration_tier(duration)
        minimum = 3 if tier == "short" else 7

        beats = video_plan_ir.get("beats", [])
        attempt_count = sum(1 for beat in beats if beat.get("isAttempt", False))

        if attempt_count < minimum:
            return RuleEvaluation(
                rule_id="ATTEMPT_001",
                rule_name="Attempt Count",
                family="concept_strength",
                severity="BLOCKER",
                result="FAIL",
                message=(
                    f"Only {attempt_count} active attempt(s) detected for a {tier}-tier "
                    f"({duration:.0f}s) video. Minimum: {minimum}."
                ),
                actual_value=attempt_count,
                required_value=minimum,
                details={"tier": tier},
            )
        return RuleEvaluation(
            rule_id="ATTEMPT_001",
            rule_name="Attempt Count",
            family="concept_strength",
            severity="PASS",
            result="PASS",
            message=f"{attempt_count} active attempts detected ({tier} tier, minimum {minimum}).",
            actual_value=attempt_count,
            required_value=minimum,
            details={"tier": tier},
        )

    def _evaluate_char_002(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """CHAR_002: Active Character"""
        duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)
        tier = self._get_duration_tier(duration)
        minimum_ratio = 0.5 if tier == "short" else 0.6

        beats = video_plan_ir.get("beats", [])
        active_duration = sum(beat.get("duration", 0.0) for beat in beats if beat.get("isAttempt", False))
        ratio = active_duration / duration if duration > 0 else 0.0

        if ratio < minimum_ratio:
            return RuleEvaluation(
                rule_id="CHAR_002",
                rule_name="Active Character",
                family="progression",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Character is actively attempting a solution for only {ratio * 100:.0f}% "
                    f"of the video ({tier} tier requires at least {minimum_ratio * 100:.0f}%). "
                    "The character spends too much time watching or reacting instead of trying."
                ),
                actual_value=ratio,
                required_value=minimum_ratio,
                details={"tier": tier},
            )
        return RuleEvaluation(
            rule_id="CHAR_002",
            rule_name="Active Character",
            family="progression",
            severity="PASS",
            result="PASS",
            message=f"Character is actively attempting a solution for {ratio * 100:.0f}% of the video.",
            actual_value=ratio,
            required_value=minimum_ratio,
            details={"tier": tier},
        )

    def _evaluate_producibility_002(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """PRODUCIBILITY_002: Prop Economy"""
        duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)
        tier = self._get_duration_tier(duration)
        maximum = 2 if tier == "short" else 4

        prop_count = len(video_plan_ir.get("setting", {}).get("mainProps", []))

        if prop_count > maximum:
            return RuleEvaluation(
                rule_id="PRODUCIBILITY_002",
                rule_name="Prop Economy",
                family="ai_producibility",
                severity="WARNING",
                result="FAIL",
                message=(
                    f"{prop_count} main props introduced for a {tier}-tier video. Maximum: {maximum}. "
                    "More props increase continuity errors and render risk."
                ),
                actual_value=prop_count,
                required_value=maximum,
                details={"tier": tier},
            )
        return RuleEvaluation(
            rule_id="PRODUCIBILITY_002",
            rule_name="Prop Economy",
            family="ai_producibility",
            severity="PASS",
            result="PASS",
            message=f"{prop_count} main props, within the {tier}-tier budget of {maximum}.",
            actual_value=prop_count,
            required_value=maximum,
            details={"tier": tier},
        )

    def _evaluate_payoff_002(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """PAYOFF_002: Fake Resolution Present (bonus, non-blocking)"""
        beats = video_plan_ir.get("beats", [])
        has_fake_win = any(beat.get("consequenceType") == "fake_win" for beat in beats)

        if has_fake_win:
            return RuleEvaluation(
                rule_id="PAYOFF_002",
                rule_name="Fake Resolution Present",
                family="progression",
                severity="PASS",
                result="PASS",
                message="A fake-resolution beat is present before the final twist.",
                actual_value=True,
                required_value=True,
            )
        return RuleEvaluation(
            rule_id="PAYOFF_002",
            rule_name="Fake Resolution Present",
            family="progression",
            severity="WARNING",
            result="PASS",
            message=(
                "No fake-resolution beat found. This is a bonus, not a requirement — "
                "consider adding a moment where the problem appears solved before the twist."
            ),
            actual_value=False,
            required_value=True,
        )

    def _evaluate_attempt_002(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """ATTEMPT_002: Distinct Attempts (hybrid deterministic + LLM semantic check)"""
        duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)
        tier = self._get_duration_tier(duration)
        minimum = 3 if tier == "short" else 7

        beats = video_plan_ir.get("beats", [])
        attempts = [b for b in beats if b.get("isAttempt", False)]

        # Deduplicate by normalized primaryVerb first — free, deterministic,
        # catches "PULL -> PULL HARDER -> PULL AGAIN" without an LLM call.
        verb_to_first_index: dict[str, int] = {}
        verb_distinct_attempts: list[dict[str, Any]] = []
        for attempt in attempts:
            verb = attempt.get("primaryVerb", "").strip().upper()
            if verb not in verb_to_first_index:
                verb_to_first_index[verb] = len(verb_distinct_attempts)
                verb_distinct_attempts.append(attempt)

        if len(verb_distinct_attempts) >= 2:
            llm_attempts = [
                {
                    "primaryVerb": a.get("primaryVerb", ""),
                    "action": a.get("action", ""),
                    "consequence": a.get("consequence", ""),
                }
                for a in verb_distinct_attempts
            ]
            try:
                duplicate_pairs = find_duplicate_strategy_pairs(llm_attempts)
            except SemanticCheckServiceError as e:
                return RuleEvaluation(
                    rule_id="ATTEMPT_002",
                    rule_name="Distinct Attempts",
                    family="visual_novelty",
                    severity="BLOCKER",
                    result="SERVICE_ERROR",
                    message=f"Semantic duplicate-strategy check failed: {e}",
                    details={"error": str(e)},
                )
        else:
            duplicate_pairs = []

        effective_distinct_count = len(verb_distinct_attempts) - len(duplicate_pairs)

        if effective_distinct_count < minimum:
            return RuleEvaluation(
                rule_id="ATTEMPT_002",
                rule_name="Distinct Attempts",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Only {effective_distinct_count} mechanically distinct attempt(s) "
                    f"detected for a {tier}-tier video. Minimum: {minimum}. Attempts that "
                    "use different wording for the same underlying strategy do not count "
                    "as separate attempts."
                ),
                actual_value=effective_distinct_count,
                required_value=minimum,
                details={"tier": tier, "duplicate_pairs": duplicate_pairs},
            )
        return RuleEvaluation(
            rule_id="ATTEMPT_002",
            rule_name="Distinct Attempts",
            family="visual_novelty",
            severity="PASS",
            result="PASS",
            message=f"{effective_distinct_count} mechanically distinct attempts detected.",
            actual_value=effective_distinct_count,
            required_value=minimum,
            details={"tier": tier, "duplicate_pairs": duplicate_pairs},
        )

    def _evaluate_payoff_003(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """PAYOFF_003: Rule-Consistent Twist (LLM semantic check)"""
        physical_rule = video_plan_ir.get("coreMechanic", {}).get("physicalRule", "")
        final_payoff = video_plan_ir.get("finalPayoff", {})
        payoff_starts_at = final_payoff.get("startsAt", 0.0)

        beats = video_plan_ir.get("beats", [])
        twist_beat = next((b for b in beats if b.get("startTime", 0.0) >= payoff_starts_at), None)
        twist_description = twist_beat.get("consequence", "") if twist_beat else ""

        try:
            matches, reasoning = check_twist_matches_rule(physical_rule, twist_description)
        except SemanticCheckServiceError as e:
            return RuleEvaluation(
                rule_id="PAYOFF_003",
                rule_name="Rule-Consistent Twist",
                family="final_payoff",
                severity="BLOCKER",
                result="SERVICE_ERROR",
                message=f"Twist-consistency check failed: {e}",
                details={"error": str(e)},
            )

        if not matches:
            return RuleEvaluation(
                rule_id="PAYOFF_003",
                rule_name="Rule-Consistent Twist",
                family="final_payoff",
                severity="CRITICAL",
                result="FAIL",
                message=f"Final twist does not derive from the established physical rule: {reasoning}",
                actual_value=False,
                required_value=True,
                details={"reasoning": reasoning},
            )
        return RuleEvaluation(
            rule_id="PAYOFF_003",
            rule_name="Rule-Consistent Twist",
            family="final_payoff",
            severity="PASS",
            result="PASS",
            message=f"Final twist derives from the established physical rule: {reasoning}",
            actual_value=True,
            required_value=True,
            details={"reasoning": reasoning},
        )

    def _evaluate_consistency_002(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """CONSISTENCY_002: Character Continuity Lock.

        This rule necessarily runs post-render, not at the pure-text concept
        stage, since it needs actual rendered frames. video_plan_ir["_renderedVideoPath"]
        is an internal-only key the render pipeline is expected to inject once a
        video exists; it is not part of the public Video Plan IR schema. When
        absent, this evaluator honestly reports UNKNOWN rather than FAIL or a
        silent pass, so a pre-render QualityReport does not claim to have
        checked something it could not check yet.
        """
        rendered_video_path = video_plan_ir.get("_renderedVideoPath")

        if not rendered_video_path:
            return RuleEvaluation(
                rule_id="CONSISTENCY_002",
                rule_name="Character Continuity Lock",
                family="consistency",
                severity="WARNING",
                result="UNKNOWN",
                message=(
                    "No rendered video available yet. Character continuity cannot be "
                    "checked at the concept stage; this rule must be re-evaluated after render."
                ),
            )

        characters = video_plan_ir.get("characters", {})
        expected_character = characters.get("primary", "")
        character_refs = characters.get("characterRefs", [])
        reference_image_path = character_refs[0] if character_refs else None

        if not reference_image_path:
            return RuleEvaluation(
                rule_id="CONSISTENCY_002",
                rule_name="Character Continuity Lock",
                family="consistency",
                severity="WARNING",
                result="SERVICE_ERROR",
                message="No character reference image available to verify continuity against.",
            )

        verifier = CharacterVerifier()
        result = verifier.verify_continuity(
            Path(str(rendered_video_path)), expected_character, Path(str(reference_image_path))
        )

        if not result["character_continuity_verified"]:
            return RuleEvaluation(
                rule_id="CONSISTENCY_002",
                rule_name="Character Continuity Lock",
                family="consistency",
                severity="CRITICAL",
                result="FAIL",
                message=f"Character continuity drift detected: {result['reasoning']}",
                actual_value=result["frame_issues"],
                details={"confidence": result["confidence"]},
            )
        return RuleEvaluation(
            rule_id="CONSISTENCY_002",
            rule_name="Character Continuity Lock",
            family="consistency",
            severity="PASS",
            result="PASS",
            message="Character identity remains consistent across sampled frames.",
            actual_value=result["frame_issues"],
            details={"confidence": result["confidence"]},
        )

    def _evaluate_beat_005(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """BEAT_005: Story Detached Gap.

        Only applies once at least one attempt beat has occurred and before
        the final payoff starts (i.e. while the core problem is actively
        unresolved). Flags a consecutive detached stretch exceeding 0.5s —
        short transitions/reaction beats under that threshold are never
        flagged, only a genuine abandonment of the active problem.
        """
        beats = video_plan_ir.get("beats", [])
        final_payoff_starts_at = video_plan_ir.get("finalPayoff", {}).get("startsAt", float("inf"))

        mid_story_beats = [b for b in beats if b.get("startTime", 0.0) < final_payoff_starts_at]
        has_established_problem = any(b.get("isAttempt", False) for b in mid_story_beats)

        if not has_established_problem:
            return RuleEvaluation(
                rule_id="BEAT_005",
                rule_name="Story Detached Gap",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message="No active problem established yet; story-relevance check does not apply.",
            )

        longest_detached_run = 0.0
        current_run = 0.0
        for beat in mid_story_beats:
            if not beat.get("relatesToCoreProblem", True):
                # A beat that starts before the payoff but keeps playing past
                # final_payoff_starts_at only counts for its pre-payoff portion —
                # detachment that occurs once the payoff has already begun is not
                # "detachment while the core problem is still unresolved."
                beat_start = beat.get("startTime", 0.0)
                beat_end = beat.get("endTime", beat_start + beat.get("duration", 0.0))
                effective_end = min(beat_end, final_payoff_starts_at)
                clipped_duration = max(0.0, effective_end - beat_start)
                current_run += clipped_duration
                longest_detached_run = max(longest_detached_run, current_run)
            else:
                current_run = 0.0

        if longest_detached_run > 0.5:
            return RuleEvaluation(
                rule_id="BEAT_005",
                rule_name="Story Detached Gap",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"Story-detached stretch of {longest_detached_run:.1f}s while the core "
                    "problem is still unresolved. Maximum tolerated: 0.5s (brief transitions "
                    "only). The video cuts away from the active problem for too long."
                ),
                actual_value=longest_detached_run,
                threshold_value=0.5,
            )
        return RuleEvaluation(
            rule_id="BEAT_005",
            rule_name="Story Detached Gap",
            family="visual_novelty",
            severity="PASS",
            result="PASS",
            message=f"Longest detached stretch: {longest_detached_run:.1f}s, within tolerance.",
            actual_value=longest_detached_run,
            threshold_value=0.5,
        )

    def _evaluate_payoff_004(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """PAYOFF_004: Final Peak Intensity.

        The pass/fail verdict is entirely derived from computed beat.intensity
        values. finalPayoff.isPeakIntensity is never read as part of the
        decision — only consulted afterward to surface a producer/evaluator
        disagreement in the message, never to override the computed result.
        """
        beats = video_plan_ir.get("beats", [])
        final_payoff = video_plan_ir.get("finalPayoff", {})
        payoff_starts_at = final_payoff.get("startsAt", 0.0)

        # Partition on a single key (endTime relative to payoff_starts_at) so every
        # beat lands in exactly one bucket. A beat straddling the boundary (started
        # before the payoff but still playing when it starts, or ends exactly as it
        # starts) counts as "final" — it's on screen at/after startsAt, which is what
        # the ending actually looks like to the viewer. Partitioning on startTime for
        # one side and endTime for the other (the original approach) leaves a gap
        # where a straddling beat is excluded from both sides entirely.
        prior_beats = [b for b in beats if b.get("endTime", 0.0) <= payoff_starts_at]
        final_beats = [b for b in beats if b.get("endTime", 0.0) > payoff_starts_at]

        max_prior_intensity = max((b.get("intensity", 0) for b in prior_beats), default=0)
        final_intensity = max((b.get("intensity", 0) for b in final_beats), default=0)

        claimed_peak = final_payoff.get("isPeakIntensity", False)
        computed_is_peak = final_intensity >= max_prior_intensity
        discrepancy_note = ""
        if claimed_peak != computed_is_peak:
            discrepancy_note = (
                f" Note: finalPayoff.isPeakIntensity claims {claimed_peak}, but computed "
                f"intensities disagree (final={final_intensity}, prior max={max_prior_intensity})."
            )

        if final_intensity < max_prior_intensity:
            return RuleEvaluation(
                rule_id="PAYOFF_004",
                rule_name="Final Peak Intensity",
                family="final_payoff",
                severity="WARNING",
                result="FAIL",
                message=(
                    f"Final payoff intensity ({final_intensity}) is lower than an earlier peak "
                    f"({max_prior_intensity}). The ending should be the most intense moment."
                    f"{discrepancy_note}"
                ),
                actual_value=final_intensity,
                required_value=max_prior_intensity,
            )
        elif final_intensity == max_prior_intensity:
            return RuleEvaluation(
                rule_id="PAYOFF_004",
                rule_name="Final Peak Intensity",
                family="final_payoff",
                severity="WARNING",
                result="PASS",
                message=(
                    f"Final payoff intensity ({final_intensity}) ties the earlier peak. "
                    f"Acceptable but not ideal — consider making the ending strictly the peak."
                    f"{discrepancy_note}"
                ),
                actual_value=final_intensity,
                required_value=max_prior_intensity,
            )
        return RuleEvaluation(
            rule_id="PAYOFF_004",
            rule_name="Final Peak Intensity",
            family="final_payoff",
            severity="PASS",
            result="PASS",
            message=f"Final payoff intensity ({final_intensity}) is strictly the peak.{discrepancy_note}",
            actual_value=final_intensity,
            required_value=max_prior_intensity,
        )

    def _evaluate_repetition_004(
        self, video_plan_ir: dict[str, Any], rule: dict[str, Any]
    ) -> RuleEvaluationType:
        """REPETITION_004: Dominant Action Ratio.

        Companion to ATTEMPT_002, not a replacement: ATTEMPT_002 catches
        verb-distinct-but-same-strategy attempts via LLM; this rule catches
        one verb numerically dominating even when every attempt is a
        legitimately distinct strategy. Never a BLOCKER — a dominant verb can
        be valid when it produces genuinely different consequences each time.
        """
        beats = video_plan_ir.get("beats", [])
        attempts = [b for b in beats if b.get("isAttempt", False)]

        if not attempts:
            return RuleEvaluation(
                rule_id="REPETITION_004",
                rule_name="Dominant Action Ratio",
                family="visual_novelty",
                severity="PASS",
                result="PASS",
                message="No attempts to evaluate.",
            )

        verb_counts: dict[str, int] = {}
        for attempt in attempts:
            verb = attempt.get("primaryVerb", "").strip().upper()
            verb_counts[verb] = verb_counts.get(verb, 0) + 1

        dominant_verb = max(verb_counts, key=lambda v: verb_counts[v])
        dominant_ratio = verb_counts[dominant_verb] / len(attempts)

        if dominant_ratio > 0.70:
            return RuleEvaluation(
                rule_id="REPETITION_004",
                rule_name="Dominant Action Ratio",
                family="visual_novelty",
                severity="CRITICAL",
                result="FAIL",
                message=(
                    f"'{dominant_verb}' accounts for {dominant_ratio * 100:.0f}% of all attempts. "
                    "Maximum: 70%. One action dominates too strongly, even allowing for varied "
                    "consequences."
                ),
                actual_value=dominant_ratio,
                threshold_value=0.70,
                details={"dominant_verb": dominant_verb},
            )
        elif dominant_ratio > 0.55:
            return RuleEvaluation(
                rule_id="REPETITION_004",
                rule_name="Dominant Action Ratio",
                family="visual_novelty",
                severity="WARNING",
                result="FAIL",
                message=(
                    f"'{dominant_verb}' accounts for {dominant_ratio * 100:.0f}% of all attempts. "
                    "Consider more variety, though a dominant verb can be valid if it produces "
                    "genuinely different consequences each time."
                ),
                actual_value=dominant_ratio,
                threshold_value=0.55,
                details={"dominant_verb": dominant_verb},
            )
        return RuleEvaluation(
            rule_id="REPETITION_004",
            rule_name="Dominant Action Ratio",
            family="visual_novelty",
            severity="PASS",
            result="PASS",
            message=f"Good action variety. Dominant verb '{dominant_verb}' at {dominant_ratio * 100:.0f}%.",
            actual_value=dominant_ratio,
            threshold_value=0.55,
            details={"dominant_verb": dominant_verb},
        )

    def _evaluate_payoff_006(self, video_plan_ir: dict[str, Any], rule: dict[str, Any]) -> RuleEvaluationType:
        """PAYOFF_006: Loopability.

        Never BLOCKER or CRITICAL — loopability is a retention optimization
        dimension, not a structural requirement. A strong natural loop is a
        bonus; an ordinary hard cut with no loop claim is a fully valid,
        neutral ending; only the specific weak-ending text patterns (fade,
        "the end", walks away) produce a (WARNING) FAIL.
        """
        final_payoff = video_plan_ir.get("finalPayoff", {})
        loops_to_opening = final_payoff.get("loopsToOpening", False)
        loop_quality = final_payoff.get("loopQuality", "none")
        is_hard_cut = final_payoff.get("isHardCut", False)

        if loops_to_opening and loop_quality == "strong":
            return RuleEvaluation(
                rule_id="PAYOFF_006",
                rule_name="Loopability",
                family="final_payoff",
                severity="PASS",
                result="PASS",
                message="Strong natural loop back to the opening — retention bonus.",
                actual_value=loop_quality,
            )
        if loops_to_opening and loop_quality == "weak":
            return RuleEvaluation(
                rule_id="PAYOFF_006",
                rule_name="Loopability",
                family="final_payoff",
                severity="WARNING",
                result="PASS",
                message=(
                    "Weak loop present — acceptable, consider strengthening the connection to the opening."
                ),
                actual_value=loop_quality,
            )
        if is_hard_cut:
            return RuleEvaluation(
                rule_id="PAYOFF_006",
                rule_name="Loopability",
                family="final_payoff",
                severity="PASS",
                result="PASS",
                message="Ordinary hard-cut ending, no loop claimed. Fully valid.",
                actual_value=loop_quality,
            )

        beats = video_plan_ir.get("beats", [])
        last_beat = beats[-1] if beats else {}
        last_text = f"{last_beat.get('action', '')} {last_beat.get('consequence', '')}".lower()
        # Word-boundary regex with a negative lookahead for "of"/"up", not plain
        # substring: a bare `in` check on "the end" or "walks away" false-positives
        # on unrelated phrasing that happens to contain the same words as part of a
        # different idiom, e.g. "reaches the end of the hallway" (not a weak ending,
        # it's "the end of X") or "walks away up the stairs" (not an exit, it's
        # "walks away up X"). The lookahead excludes exactly that "...of/up <noun>"
        # continuation while still matching the real weak-ending idiom regardless of
        # where in the beat text it appears.
        weak_ending_patterns = [
            r"\bfade[sd]?\b",
            r"\bthe end\b(?!\s+of)",
            r"\bwalk(?:s|ed)? away\b(?!\s+(?:up|down|from|to|into|through))",
        ]
        matched_text = None
        for p in weak_ending_patterns:
            match = re.search(p, last_text)
            if match:
                matched_text = match.group(0).strip(" .,!")
                break

        if matched_text:
            return RuleEvaluation(
                rule_id="PAYOFF_006",
                rule_name="Loopability",
                family="final_payoff",
                severity="WARNING",
                result="FAIL",
                message=(
                    f"Ending matches a weak-ending pattern ('{matched_text}'). Consider a "
                    "harder cut or a loop back to the opening for stronger retention."
                ),
                actual_value=matched_text,
            )
        return RuleEvaluation(
            rule_id="PAYOFF_006",
            rule_name="Loopability",
            family="final_payoff",
            severity="PASS",
            result="PASS",
            message="No loop claimed, no hard-cut flag, but no weak-ending pattern detected either.",
            actual_value=loop_quality,
        )


def validate_video_plan(video_plan_ir: dict[str, Any], ruleset_path: str | None = None) -> QualityReport:
    """
    Convenience function to validate a video plan.

    Args:
        video_plan_ir: Video Plan IR to validate
        ruleset_path: Optional path to custom ruleset

    Returns:
        QualityReport with complete evaluation
    """
    engine = RuleEngine(ruleset_path)
    return engine.evaluate(video_plan_ir)
