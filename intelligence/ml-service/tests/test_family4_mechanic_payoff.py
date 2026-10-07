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
