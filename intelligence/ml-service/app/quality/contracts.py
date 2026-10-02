"""Canonical quality-pipeline contracts.

These types are the one authoritative contract shared by every stage of the ML
quality pipeline. They replace the historical mix of stringly-typed ``result``
fields, boolean truthiness checks, and ad-hoc dict payloads that had drifted
apart across the parser, rule engine, scorer, regression checker, auto-fix
loop, and API layer.

Design rules enforced here:

* Rule results are an explicit :class:`RuleOutcome` enum, never a boolean or a
  bare string. ``RuleOutcome.FAIL`` is a distinct value, not falsy truthiness
  masquerading as a boolean.
* A missing/unregistered evaluator yields :class:`RuleOutcome.SERVICE_ERROR`
  (fail-closed) rather than a silent pass.
* Report-level counts (blocker/critical/warning/failed) are *derived*
  accessors over the evaluations, so they can never disagree with the data.
* Value objects are immutable (``frozen=True``) and use tuples for sequences so
  reports cannot be mutated after they are produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RuleOutcome(StrEnum):
    """Explicit outcome of evaluating a single rule.

    UNKNOWN and NOT_APPLICABLE are deliberately distinct: UNKNOWN means the
    rule applies but required evidence is currently missing (e.g. no
    rendered video yet). NOT_APPLICABLE means the rule does not apply to
    this concept at all, by design (e.g. no fake-win beat present, so a
    fake-win-escalation check has nothing to evaluate). Conflating these
    would corrupt rule-coverage and rule-effectiveness measurement.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SERVICE_ERROR = "SERVICE_ERROR"


class Severity(StrEnum):
    """Severity level attached to a rule evaluation."""

    PASS = "PASS"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    BLOCKER = "BLOCKER"


class QualityStatus(StrEnum):
    """Overall readiness status for a video plan."""

    RENDER_READY = "RENDER_READY"
    NEEDS_REVISION = "NEEDS_REVISION"
    BLOCKED = "BLOCKED"
    SERVICE_ERROR = "SERVICE_ERROR"


class FixStrategy(StrEnum):
    """How a priority fix should be approached."""

    CONTROLLED_PATCH = "CONTROLLED_PATCH"
    REPLACE_CONCEPT = "REPLACE_CONCEPT"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RegressionDecision(StrEnum):
    """Accept/revise/reject decision for a before/after comparison."""

    ACCEPT = "ACCEPT"
    REVISE = "REVISE"
    REJECT = "REJECT"


# Rules whose only sound remedy is regenerating the underlying concept rather
# than patching the existing prompt. CONCEPT_006 (insufficient consequence
# capacity) cannot be fixed by string manipulation.
_REPLACE_CONCEPT_RULES = frozenset({"CONCEPT_006"})

# Rules that require a human decision (e.g. accepting render risk, or a
# semantic/visual judgment no deterministic patch can resolve) rather than an
# automated patch.
_HUMAN_REVIEW_RULES = frozenset({"PRODUCIBILITY_001", "PAYOFF_003", "CONSISTENCY_002"})


def strategy_for_rule(rule_id: str) -> FixStrategy:
    """Return the canonical fix strategy for a rule id.

    ``CONCEPT_006`` always maps to :data:`FixStrategy.REPLACE_CONCEPT`.
    """

    if rule_id in _REPLACE_CONCEPT_RULES:
        return FixStrategy.REPLACE_CONCEPT
    if rule_id in _HUMAN_REVIEW_RULES:
        return FixStrategy.HUMAN_REVIEW
    return FixStrategy.CONTROLLED_PATCH


@dataclass(frozen=True)
class ParserMetadata:
    """Confidence and provenance notes emitted by the prompt parser."""

    confidence: float
    ambiguities: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParseResult:
    """Structured result of parsing a prompt into a Video Plan IR."""

    video_plan_ir: dict[str, Any]
    metadata: ParserMetadata


@dataclass(frozen=True)
class RuleEvaluation:
    """Result of evaluating a single rule against a Video Plan IR."""

    rule_id: str
    rule_name: str
    family: str
    outcome: RuleOutcome
    configured_severity: Severity
    message: str

    actual_value: Any = None
    required_value: Any = None
    threshold_value: Any = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True only when the rule explicitly passed."""

        return self.outcome is RuleOutcome.PASS

    @property
    def effective_severity(self) -> Severity:
        """Severity that actually applies given the outcome.

        A service error fails closed at BLOCKER. A clean pass collapses to
        PASS. A soft pass (configured WARNING) keeps its WARNING weight, and a
        failure keeps its configured severity.
        """

        if self.outcome is RuleOutcome.SERVICE_ERROR:
            return Severity.BLOCKER
        if self.outcome is RuleOutcome.PASS and self.configured_severity is Severity.PASS:
            return Severity.PASS
        return self.configured_severity


@dataclass(frozen=True)
class QualityReport:
    """Complete rule-engine evaluation of a Video Plan IR.

    Counts are derived accessors so they can never contradict ``evaluations``.
    """

    overall_score: float
    status: QualityStatus
    family_scores: dict[str, float]
    evaluations: tuple[RuleEvaluation, ...]
    ruleset_version: str
    evaluated_at: str

    @property
    def failed_rules(self) -> tuple[RuleEvaluation, ...]:
        return tuple(e for e in self.evaluations if e.outcome is RuleOutcome.FAIL)

    @property
    def service_errors(self) -> tuple[RuleEvaluation, ...]:
        return tuple(e for e in self.evaluations if e.outcome is RuleOutcome.SERVICE_ERROR)

    @property
    def not_applicable_rules(self) -> tuple[RuleEvaluation, ...]:
        return tuple(e for e in self.evaluations if e.outcome is RuleOutcome.NOT_APPLICABLE)

    @property
    def unknown_rules(self) -> tuple[RuleEvaluation, ...]:
        return tuple(e for e in self.evaluations if e.outcome is RuleOutcome.UNKNOWN)

    @property
    def blocker_count(self) -> int:
        return sum(
            1
            for e in self.evaluations
            if e.outcome is RuleOutcome.FAIL and e.configured_severity is Severity.BLOCKER
        )

    @property
    def critical_count(self) -> int:
        return sum(
            1
            for e in self.evaluations
            if e.outcome is RuleOutcome.FAIL and e.configured_severity is Severity.CRITICAL
        )

    @property
    def warning_count(self) -> int:
        # A WARNING-configured rule contributes a warning whether it is a soft
        # pass or a soft fail (matches the historical counting semantics).
        return sum(1 for e in self.evaluations if e.configured_severity is Severity.WARNING)

    @property
    def pass_count(self) -> int:
        return sum(
            1
            for e in self.evaluations
            if e.outcome is RuleOutcome.PASS and e.configured_severity is Severity.PASS
        )

    @property
    def service_error_count(self) -> int:
        return len(self.service_errors)

    @property
    def not_applicable_count(self) -> int:
        return len(self.not_applicable_rules)

    @property
    def unknown_count(self) -> int:
        return len(self.unknown_rules)

    @property
    def is_render_ready(self) -> bool:
        return (
            self.overall_score >= 92
            and self.blocker_count == 0
            and self.critical_count == 0
            and self.service_error_count == 0
        )

    @property
    def needs_redesign(self) -> bool:
        return self.overall_score < 80 or self.blocker_count > 0


@dataclass(frozen=True)
class ScoreBreakdown:
    """Detailed per-family score breakdown."""

    family: str
    score: float
    weight: float
    weighted_contribution: float
    rules_passed: int
    rules_failed: int
    rules_warning: int
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriorityFix:
    """A single prioritized, actionable fix recommendation.

    ``strategy`` declares how the fix must be approached. ``CONCEPT_006`` is
    always a :data:`FixStrategy.REPLACE_CONCEPT` because its remedy is a new
    concept, not a controlled patch.
    """

    priority: int
    rule_id: str
    rule_name: str
    family: str
    severity: Severity
    issue: str
    recommendation: str
    impact: str
    strategy: FixStrategy

    @classmethod
    def from_evaluation(
        cls,
        *,
        priority: int,
        evaluation: RuleEvaluation,
        recommendation: str,
        impact: str,
    ) -> PriorityFix:
        return cls(
            priority=priority,
            rule_id=evaluation.rule_id,
            rule_name=evaluation.rule_name,
            family=evaluation.family,
            severity=evaluation.configured_severity,
            issue=evaluation.message,
            recommendation=recommendation,
            impact=impact,
            strategy=strategy_for_rule(evaluation.rule_id),
        )


@dataclass(frozen=True)
class EnhancedQualityReport:
    """Rich report wrapping a :class:`QualityReport` with scoring detail."""

    base_report: QualityReport
    score_breakdowns: tuple[ScoreBreakdown, ...]
    score_card: dict[str, Any]
    timeline_data: dict[str, Any]
    family_radar: dict[str, Any]
    top_3_strengths: tuple[str, ...]
    top_3_weaknesses: tuple[str, ...]
    priority_fixes: tuple[PriorityFix, ...]
    parser_metadata: ParserMetadata

    @property
    def overall_score(self) -> float:
        return self.base_report.overall_score

    @property
    def status(self) -> QualityStatus:
        return self.base_report.status

    @property
    def ruleset_version(self) -> str:
        return self.base_report.ruleset_version

    @property
    def evaluated_at(self) -> str:
        return self.base_report.evaluated_at
