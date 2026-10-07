from __future__ import annotations

from pathlib import Path

from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import mechanic_payoff_evidence

ROOT = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "prompts"


def parse_asset(name: str) -> dict:
    return parse_prompt((ROOT / name).read_text(encoding="utf-8")).video_plan_ir


def test_sticky_is_same_rule_fake_resolution_and_payoff() -> None:
    evidence = mechanic_payoff_evidence(parse_asset("sticky-ball-01.txt"))
    assert evidence.central_mechanic_status == "ESTABLISHED"
    assert evidence.fake_resolution_status == "PRESENT"
    assert evidence.recurrence_status == "PRESENT"
    assert evidence.same_rule_relation == "SAME_RULE"
    assert evidence.payoff_status == "STRONG"


def test_crocodile_quantity_payoff_is_same_rule() -> None:
    evidence = mechanic_payoff_evidence(parse_asset("ball-crocodile-01.txt"))
    assert evidence.central_mechanic_status == "ESTABLISHED"
    assert evidence.fake_resolution_status == "PRESENT"
    assert evidence.recurrence_status == "PRESENT"
    assert evidence.same_rule_relation == "SAME_RULE"
    assert evidence.payoff_status == "STRONG"


def test_island_journal_has_no_mechanic_payoff_dimension() -> None:
    evidence = mechanic_payoff_evidence(parse_asset("island-journal-01.txt"))
    assert evidence.central_mechanic_status == "NOT_ESTABLISHED"
    assert evidence.fake_resolution_status == "NOT_ESTABLISHED"
    assert evidence.recurrence_status == "NOT_ESTABLISHED"
    assert evidence.same_rule_relation == "NOT_ESTABLISHED"
    assert evidence.payoff_status == "NOT_ESTABLISHED"


def test_fake_resolution_does_not_become_mechanic_inconsistency() -> None:
    ir = {
        "coreMechanic": {"physicalRule": "The rope sticks to surfaces."},
        "beats": [
            {"beatRole": "ATTEMPT", "action": "Mimi pulls the rope", "consequence": "rope stretches", "consequenceType": "new"},
            {"beatRole": "FAKE_RESOLUTION", "action": "Mimi relaxes", "consequence": "rope behaves normally", "consequenceType": "fake_win"},
            {"beatRole": "TWIST", "action": "rope returns to the wall", "consequence": "rope sticks again", "consequenceType": "new"},
        ],
        "finalPayoff": {"description": "The rope sticks again."},
    }
    evidence = mechanic_payoff_evidence(ir)
    assert evidence.fake_resolution_status == "PRESENT"
    assert evidence.same_rule_relation == "SAME_RULE"
    assert evidence.payoff_status in {"MODERATE", "STRONG"}


def test_unrelated_final_twist_is_not_same_rule_payoff() -> None:
    ir = {
        "coreMechanic": {"physicalRule": "The rope sticks to surfaces."},
        "beats": [
            {"beatRole": "ATTEMPT", "action": "Mimi pulls the rope", "consequence": "rope stretches", "consequenceType": "new"},
            {"beatRole": "TWIST", "action": "an elephant appears", "consequence": "the scene changes", "consequenceType": "new"},
        ],
        "finalPayoff": {"description": "An elephant appears."},
    }
    evidence = mechanic_payoff_evidence(ir)
    assert evidence.same_rule_relation == "NOT_ESTABLISHED"
    assert evidence.payoff_status == "NOT_ESTABLISHED"


def test_assessment_projects_mechanic_fake_recurrence_and_same_rule_evidence() -> None:
    from app.assessment.pre_render_assessment import build_pre_render_assessment
    from app.quality.contracts import ParserMetadata, QualityReport, QualityStatus

    parsed = parse_prompt((ROOT / "sticky-ball-01.txt").read_text(encoding="utf-8"))
    report = QualityReport(
        overall_score=85.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={},
        evaluations=(),
        ruleset_version="1.7",
        evaluated_at="GOLDEN_DETERMINISTIC",
    )
    assessment = build_pre_render_assessment(parsed.video_plan_ir, parsed.metadata, report, "1.7")
    story = assessment["story_structure"]
    assert story["central_mechanic"] == "ESTABLISHED"
    assert story["fake_resolution"] == "PRESENT"
    assert story["recurrence"] == "PRESENT"
    assert story["payoff_relation"] == "SAME_RULE"


def test_recurrence_is_present_when_an_established_mechanic_reasserts_without_fake_resolution() -> None:
    ir = {
        "coreMechanic": {"physicalRule": "The sticky ball sticks to surfaces."},
        "beats": [
            {
                "beatRole": "ATTEMPT",
                "action": "Mimi pulls the sticky ball",
                "consequence": "it sticks to the table",
                "consequenceType": "new",
            },
            {
                "beatRole": "TWIST",
                "action": "the sticky ball sticks again",
                "consequence": "it sticks to the wall",
                "consequenceType": "new",
            },
        ],
        "finalPayoff": {"description": "The sticky ball sticks again to the wall."},
    }

    evidence = mechanic_payoff_evidence(ir)

    assert evidence.fake_resolution_status == "NOT_ESTABLISHED"
    assert evidence.recurrence_status == "PRESENT"


def test_quantity_mechanic_does_not_turn_an_unrelated_twist_into_recurrence_or_payoff() -> None:
    ir = {
        "coreMechanic": {"physicalRule": "Every ball entering the mouth produces more balls."},
        "beats": [
            {
                "beatRole": "ATTEMPT",
                "action": "Mimi feeds one ball",
                "consequence": "the crocodile spits three balls",
                "consequenceType": "new",
            },
            {
                "beatRole": "FAKE_RESOLUTION",
                "action": "Mimi relaxes",
                "consequence": "the crocodile returns one ball",
                "consequenceType": "fake_win",
            },
            {
                "beatRole": "TWIST",
                "action": "an elephant appears",
                "consequence": "the scene changes",
                "consequenceType": "new",
            },
        ],
        "finalPayoff": {"type": "twist", "description": "An elephant appears."},
    }

    evidence = mechanic_payoff_evidence(ir)

    assert evidence.recurrence_status == "NOT_ESTABLISHED"
    assert evidence.same_rule_relation == "NOT_ESTABLISHED"
    assert evidence.payoff_status == "NOT_ESTABLISHED"


def test_generic_return_word_does_not_establish_recurrence_for_an_unrelated_twist() -> None:
    ir = {
        "coreMechanic": {"physicalRule": "The sticky ball sticks to surfaces."},
        "beats": [
            {
                "beatRole": "ATTEMPT",
                "action": "Mimi pulls the sticky ball",
                "consequence": "it sticks to the table",
                "consequenceType": "new",
            },
            {
                "beatRole": "TWIST",
                "action": "an elephant returns",
                "consequence": "the scene changes",
                "consequenceType": "new",
            },
        ],
        "finalPayoff": {"description": "An elephant returns."},
    }

    evidence = mechanic_payoff_evidence(ir)

    assert evidence.recurrence_status == "NOT_ESTABLISHED"
    assert evidence.same_rule_relation == "NOT_ESTABLISHED"
    assert evidence.payoff_status == "NOT_ESTABLISHED"
