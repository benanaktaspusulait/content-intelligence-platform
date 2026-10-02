"""Canonical ML quality contracts.

This package defines the single source of truth for the quality pipeline's
value types. Every stage (parser, rule engine, scorer, regression checker,
auto-fix, API) converges on the types declared in :mod:`app.quality.contracts`.
"""

from .contracts import (
    EnhancedQualityReport,
    FixStrategy,
    ParseResult,
    ParserMetadata,
    PriorityFix,
    QualityReport,
    QualityStatus,
    RegressionDecision,
    RuleEvaluation,
    RuleOutcome,
    ScoreBreakdown,
    Severity,
)

__all__ = [
    "EnhancedQualityReport",
    "FixStrategy",
    "ParseResult",
    "ParserMetadata",
    "PriorityFix",
    "QualityReport",
    "QualityStatus",
    "RegressionDecision",
    "RuleEvaluation",
    "RuleOutcome",
    "ScoreBreakdown",
    "Severity",
]
