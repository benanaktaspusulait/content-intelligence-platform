"""Task 4–5 Family 8 ML assessment/API integration contracts."""

from __future__ import annotations

from pathlib import Path

from app.api.quality import convert_quality_report
from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

RULESET = str(settings.rules_dir / "RULESET_1.7.yaml")
FIXTURE = Path(__file__).parent / "fixtures" / "luca_sticky_ball_prompt.txt"


def test_pre_render_assessment_exposes_three_orthogonal_family8_axes() -> None:
    parsed = parse_prompt(FIXTURE.read_text(encoding="utf-8"))
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    assessment = build_pre_render_assessment(
        parsed.video_plan_ir,
        parsed.metadata,
        report,
        "1.7",
    )

    family8 = assessment["family8"]
    assert set(family8) == {
        "creativeQuality",
        "evidenceCompleteness",
        "renderAuthorization",
        "legacy",
    }
    assert "creativeGrade" in family8["creativeQuality"]
    assert "evaluationCoverage" in family8["evidenceCompleteness"]
    assert "status" in family8["renderAuthorization"]
    assert "reasons" in family8["renderAuthorization"]
    assert family8["legacy"]["readiness"] == assessment["readiness"]


def test_quality_api_preserves_family8_axes_and_reasons() -> None:
    parsed = parse_prompt(FIXTURE.read_text(encoding="utf-8"))
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.7", video_plan_ir=parsed.video_plan_ir)

    family8 = response.pre_render_assessment.family8
    assert family8 is not None
    assert set(family8) == {
        "creativeQuality",
        "evidenceCompleteness",
        "renderAuthorization",
        "legacy",
    }
    assert family8["renderAuthorization"]["reasons"] is not None
