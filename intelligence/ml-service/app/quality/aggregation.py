"""Family 7 status-aware aggregation primitives.

This module is intentionally not wired into the existing RuleEngine or scorer yet.
It defines the approved contract for distinguishing scored, unknown, unevaluated,
not-applicable, and service-error evidence.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .contracts import EvaluationState, RuleOutcome


@dataclass(frozen=True)
class AggregationRow:
    """One status-bearing row at the Family 7 aggregation boundary."""

    rule_id: str
    outcome: RuleOutcome | None
    evaluation_state: EvaluationState
    family: str
    reason: str = ""

    def __post_init__(self) -> None:
        if self.evaluation_state is EvaluationState.NOT_EVALUATED:
            if self.outcome is not None:
                raise ValueError("NOT_EVALUATED rows must have outcome=None")
            return
        if self.outcome is None:
            raise ValueError("EVALUATED rows must have a RuleOutcome")


@dataclass(frozen=True)
class AggregationSummary:
    """Lossless counts and score/coverage facts for a set of rows."""

    score: float | None
    scored_count: int
    denominator: int
    pass_count: int
    fail_count: int
    unknown_count: int
    not_evaluated_count: int
    not_applicable_count: int
    service_error_count: int
    evaluation_coverage: float | None
    aggregation_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "scoredCount": self.scored_count,
            "denominator": self.denominator,
            "passCount": self.pass_count,
            "failCount": self.fail_count,
            "unknownCount": self.unknown_count,
            "notEvaluatedCount": self.not_evaluated_count,
            "notApplicableCount": self.not_applicable_count,
            "serviceErrorCount": self.service_error_count,
            "evaluationCoverage": self.evaluation_coverage,
            "aggregationState": self.aggregation_state,
        }


def summarize_aggregation(rows: Iterable[AggregationRow]) -> AggregationSummary:
    """Summarize rows without treating missing evidence as creative failure."""

    rows = tuple(rows)
    pass_count = sum(1 for row in rows if row.outcome is RuleOutcome.PASS)
    fail_count = sum(1 for row in rows if row.outcome is RuleOutcome.FAIL)
    unknown_count = sum(1 for row in rows if row.outcome is RuleOutcome.UNKNOWN)
    not_evaluated_count = sum(
        1 for row in rows if row.evaluation_state is EvaluationState.NOT_EVALUATED
    )
    not_applicable_count = sum(
        1 for row in rows if row.outcome is RuleOutcome.NOT_APPLICABLE
    )
    service_error_count = sum(
        1 for row in rows if row.outcome is RuleOutcome.SERVICE_ERROR
    )

    scored_count = pass_count + fail_count
    applicable_count = (
        pass_count
        + fail_count
        + unknown_count
        + not_evaluated_count
        + service_error_count
    )
    semantic_evaluation_count = pass_count + fail_count + unknown_count
    evaluation_coverage = (
        semantic_evaluation_count / applicable_count if applicable_count else None
    )

    # Task 2 intentionally uses a deterministic unweighted pass/fail ratio only
    # to prove score eligibility. Existing production scoring remains untouched.
    score = 100.0 * pass_count / scored_count if scored_count else None

    if service_error_count:
        aggregation_state = "SERVICE_ERROR"
    elif scored_count:
        aggregation_state = (
            "PARTIAL"
            if unknown_count or not_evaluated_count
            else "EVALUATED"
        )
    elif not_evaluated_count and not semantic_evaluation_count:
        aggregation_state = "NO_EVALUATED_ITEMS"
    elif unknown_count:
        aggregation_state = "NO_SCORED_ITEMS"
    elif not_applicable_count and not applicable_count:
        aggregation_state = "NOT_APPLICABLE"
    else:
        aggregation_state = "NO_EVALUATED_ITEMS"

    return AggregationSummary(
        score=score,
        scored_count=scored_count,
        denominator=scored_count,
        pass_count=pass_count,
        fail_count=fail_count,
        unknown_count=unknown_count,
        not_evaluated_count=not_evaluated_count,
        not_applicable_count=not_applicable_count,
        service_error_count=service_error_count,
        evaluation_coverage=evaluation_coverage,
        aggregation_state=aggregation_state,
    )
