from __future__ import annotations

from pathlib import Path

from app.quality.canonical_evidence import story_density_evidence
from app.parser.prompt_parser import parse_prompt

ROOT = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "prompts"


def parse_asset(name: str) -> dict:
    return parse_prompt((ROOT / name).read_text(encoding="utf-8")).video_plan_ir


def test_sticky_realization_is_available_and_implicit() -> None:
    evidence = story_density_evidence(parse_asset("sticky-ball-01.txt"))
    assert evidence.realization_status == "AVAILABLE"
    assert evidence.realization_mode == "IMPLICIT_BUT_OBSERVABLE"


def test_explicit_realization_role_has_explicit_mode() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"beatRole": "ATTEMPT", "action": "Mimi tests the box", "consequence": "it changes"},
            {"beatRole": "REALIZATION", "action": "Mimi realizes the box is changing", "consequence": "she decides to stop"},
        ],
        "goalEvidence": {"goalExplicitness": "EXPLICIT", "obstruction": "box changes"},
        "finalPayoff": {},
    }
    evidence = story_density_evidence(ir)
    assert evidence.realization_status == "AVAILABLE"
    assert evidence.realization_mode == "EXPLICIT"


def test_missing_realization_does_not_become_available_from_smile_alone() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [{"beatRole": "REACTION", "action": "Mimi smiles", "consequence": "nothing changes"}],
        "goalEvidence": {"goalExplicitness": "UNSUPPORTED"},
        "finalPayoff": {},
    }
    evidence = story_density_evidence(ir)
    assert evidence.realization_status == "UNKNOWN"
    assert evidence.realization_mode is None


def test_goal_dimension_uses_canonical_goal_evidence_without_rule_result() -> None:
    from app.assessment.pre_render_assessment import _goal

    ir = {
        "goalEvidence": {
            "goalExplicitness": "IMPLICIT_BUT_OBSERVABLE",
            "description": "Control the stuck ball",
            "obstruction": "The ball remains stuck",
        }
    }
    result = _goal(ir, ())
    assert result["status"] == "MODERATE"
    assert result["evidence_status"] == "AVAILABLE"
