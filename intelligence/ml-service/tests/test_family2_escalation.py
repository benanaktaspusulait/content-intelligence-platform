from __future__ import annotations

from pathlib import Path

from app.assessment.pre_render_assessment import _escalation
from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import escalation_evidence

ROOT = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "prompts"


def parse_asset(name: str) -> dict:
    return parse_prompt((ROOT / name).read_text(encoding="utf-8")).video_plan_ir


def test_sticky_wall_flex_is_strong_escalation_without_new_strategy() -> None:
    evidence = escalation_evidence(parse_asset("sticky-ball-01.txt"))
    assert evidence.strength == "STRONG"
    assert evidence.wall_flex is True
    assert evidence.deformation is True
    assert evidence.scope_expansion is True
    assert evidence.persistence is True


def test_crocodile_quantity_growth_is_strong_escalation() -> None:
    evidence = escalation_evidence(parse_asset("ball-crocodile-01.txt"))
    assert evidence.strength == "STRONG"
    assert evidence.quantity_growth is True
    assert evidence.consequence_expansion is True


def test_repeated_visibility_interaction_is_not_strong_escalation() -> None:
    evidence = escalation_evidence(parse_asset("lamp-01.md"))
    assert evidence.strength == "MODERATE"
    assert evidence.force_rise is False
    assert evidence.quantity_growth is False


def test_repeated_spot_claims_are_weak_escalation() -> None:
    evidence = escalation_evidence(parse_asset("spot-cat-01.md"))
    assert evidence.strength == "WEAK"
    assert evidence.scope_expansion is False
    assert evidence.quantity_growth is False


def test_island_journal_escalation_is_not_applicable() -> None:
    ir = parse_asset("island-journal-01.txt")
    evidence = escalation_evidence(ir)
    assert evidence.applicability == "NOT_APPLICABLE"


def test_assessment_uses_canonical_escalation_without_attempt_intensity() -> None:
    ir = parse_asset("ball-crocodile-01.txt")
    dimension = _escalation(ir, ())
    assert dimension["status"] in {"STRONG", "MODERATE"}
    assert dimension["status"] != "UNKNOWN"
