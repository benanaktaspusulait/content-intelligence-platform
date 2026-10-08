"""Task 3 nullable-score propagation contracts."""

from __future__ import annotations

from app.assessment.family8_projection import project_family8
from app.config import settings
from app.quality.contracts import QualityReport, QualityStatus, RuleEvaluation, RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

RULESET = str(settings.rules_dir / "RULESET_1.7.yaml")
FAMILY = "family8_score_test"


def evaluation(rule_id: str, outcome: RuleOutcome, severity: Severity) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=rule_id,
        family=FAMILY,
        outcome=outcome,
        configured_severity=severity,
        message="Task 3 fixture",
    )


def test_valid_pass_fail_score_math_remains_unchanged() -> None:
    engine = RuleEngine(RULESET)
    rows = [
        evaluation("pass", RuleOutcome.PASS, Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, Severity.CRITICAL),
    ]
    family_scores = engine._calculate_family_scores(rows)
    overall = engine._calculate_overall_score(family_scores, rows)
    assert family_scores[FAMILY] == 70.0
    assert overall == 70.0


def test_unknown_only_family_and_overall_score_are_null() -> None:
    engine = RuleEngine(RULESET)
    rows = [evaluation("unknown", RuleOutcome.UNKNOWN, Severity.WARNING)]
    family_scores = engine._calculate_family_scores(rows)
    overall = engine._calculate_overall_score(family_scores, rows)
    assert family_scores[FAMILY] is None
    assert overall is None
    assert overall != 0


def test_quality_scorer_score_card_preserves_null_score() -> None:
    report = QualityReport(
        overall_score=None,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={FAMILY: None},
        evaluations=(evaluation("unknown", RuleOutcome.UNKNOWN, Severity.WARNING),),
        ruleset_version="1.7",
        evaluated_at="TASK3",
    )
    card = QualityScorer()._create_score_card(report)
    assert card["score"] is None
    assert card["label"] == "Not evaluated"


def test_family8_projection_preserves_null_creative_and_family_scores() -> None:
    result = project_family8({
        "creativeQuality": {
            "creativeScore": None,
            "creativeGrade": None,
            "familyScores": {"family7_score_test": None},
        },
        "evidenceCompleteness": {
            "status": "INCOMPLETE",
            "evaluationCoverage": 0.0,
            "aggregation": {
                "scoredCount": 0,
                "aggregationState": "NO_SCORED_ITEMS",
            },
        },
        "authorizationReasons": [{
            "code": "REQUIRED_EVIDENCE_MISSING",
            "source": "AGGREGATION",
            "message": "No scored items",
        }],
    })
    assert result["creativeQuality"]["creativeScore"] is None
    assert result["creativeQuality"]["familyScores"]["family7_score_test"] is None
    assert result["renderAuthorization"]["status"] == "BLOCKED_PENDING_EVIDENCE"
