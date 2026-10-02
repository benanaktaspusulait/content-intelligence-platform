"""Canonical API conversion contract (Slice A Task 5).

The quality API conversion layer consumes the canonical contracts
(``enhanced.base_report`` + typed ``priority_fixes`` + DTO-aligned timeline)
and the ``/validate`` endpoint returns a well-formed report. The ``/auto-fix``
module imports cleanly now that the scorer/contract drift is repaired.
"""

from fastapi.testclient import TestClient

from app.api.quality import convert_quality_report
from app.config import settings
from app.main import app
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

RULESET = str(settings.rules_dir / "RULESET_1.0.yaml")

STATIC_PROMPT = (
    "Title: Static Hero\n\n15-second video\n\n## Characters\n- Hero: Brave\n\n"
    "## Timeline\n0.0-5.0 SEC: Hero — stands still\n5.0-10.0 SEC: Hero — keeps standing\n"
    "10.0-15.0 SEC: Hero — still standing\n"
)


def test_autofix_module_imports_without_lazy_hack() -> None:
    # The contract drift is gone, so a normal module-level import must succeed.
    from app.autofix.iteration_loop import AutoFixIterationLoop

    assert AutoFixIterationLoop is not None


def test_convert_quality_report_uses_base_report_and_typed_fixes() -> None:
    parsed = parse_prompt(STATIC_PROMPT)
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    assert response.overall_score == report.overall_score
    assert response.ruleset_version == "1.0"
    # Failed rules are rendered with an explicit boolean result == False.
    assert all(fr.result is False for fr in response.failed_rules)
    # Timeline beats carried through the DTO-aligned conversion layer.
    assert len(response.timeline_data.beats) == len(parsed.video_plan_ir["beats"])


def test_validate_endpoint_returns_report() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/quality/validate",
        json={"prompt": STATIC_PROMPT, "ruleset_version": "latest"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"RENDER_READY", "NEEDS_REVISION", "BLOCKED", "SERVICE_ERROR"}
    assert "priority_fixes" in body
    assert "timeline_data" in body


def test_validate_unknown_ruleset_is_404_not_500() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/quality/validate",
        json={"prompt": STATIC_PROMPT, "ruleset_version": "nope-9.9"},
    )
    assert response.status_code == 404
