"""Canonical beat/attempt evidence semantics (parser + shared accessor + attempt rules)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import UNSPECIFIED_VERB, attempt_evidence, is_unspecified_verb
from app.rules.rule_engine import RuleEngine


def _beats(timeline: str) -> list[dict[str, Any]]:
    prompt = f"Title: Label Semantics\n\n15-second video\n\n## Timeline\n{timeline}\n"
    beats: list[dict[str, Any]] = parse_prompt(prompt).video_plan_ir["beats"]
    return beats


def test_label_on_the_timestamp_line_is_split_from_the_action() -> None:
    (beat,) = _beats("0.0-15.0 SEC — FIRST ATTEMPT\nMimi pulls the rope.\nThe rope stretches.")
    assert beat["beatLabel"] == "FIRST ATTEMPT"
    assert beat["beatRole"] == "ATTEMPT"
    assert beat["action"] == "Mimi pulls the rope."
    assert beat["isAttempt"] is True
    assert beat["primaryVerb"] == "PULLS"
    assert beat["attemptSource"] == "STRUCTURED_PLAN_ROLE"


def test_label_followed_by_text_on_the_same_line() -> None:
    (beat,) = _beats("0.0-15.0 SEC: REACTION: Kiko stares at the ball.")
    assert beat["beatLabel"] == "REACTION"
    assert beat["action"] == "Kiko stares at the ball."


def test_ordinary_first_line_is_never_mistaken_for_a_label() -> None:
    (beat,) = _beats("0.0-15.0 SEC: Kiko — spots a shiny box")
    assert beat["beatLabel"] == ""
    assert beat["beatRole"] == ""
    assert beat["action"] == "Kiko — spots a shiny box"
    assert beat["attemptSource"] == "NONE"


def test_declared_non_attempt_role_is_not_inferred_as_attempt() -> None:
    (beat,) = _beats("0.0-15.0 SEC — REACTION\nMimi pulls the rope.")
    assert beat["beatRole"] == "REACTION"
    assert beat["isAttempt"] is False


def test_explicit_attempt_marker_outranks_a_non_attempt_role() -> None:
    (beat,) = _beats("0.0-15.0 SEC — REACTION\nMimi tugs the rope. [ATTEMPT: TUG]")
    assert beat["isAttempt"] is True
    assert beat["primaryVerb"] == "TUG"
    assert beat["attemptSource"] == "EXPLICIT_ATTEMPT_LABEL"


def test_labelled_attempt_without_whitelisted_verb_uses_the_acting_characters_verb() -> None:
    (beat,) = _beats("0.0-15.0 SEC — SECOND ATTEMPT\nMimi squeezes the cup.")
    assert beat["isAttempt"] is True
    assert beat["primaryVerb"] == "SQUEEZES"


def test_labelled_attempt_with_no_identifiable_verb_is_explicitly_unspecified() -> None:
    timeline = "0.0-15.0 SEC — THIRD ATTEMPT\nThe cup wobbles."
    result = parse_prompt(f"Title: Label Semantics\n\n15-second video\n\n## Timeline\n{timeline}\n")
    (beat,) = result.video_plan_ir["beats"]
    assert beat["isAttempt"] is True
    assert beat["primaryVerb"] == UNSPECIFIED_VERB
    assert is_unspecified_verb(beat["primaryVerb"])
    assert any("no action verb" in item for item in result.metadata.ambiguities)


def test_catch_reaction_is_not_the_intended_test_strategy() -> None:
    (beat,) = _beats(
        "0.0-15.0 SEC — SECOND ATTEMPT\n"
        "Mimi catches the cup.\n"
        "She squeezes it gently. It behaves normally and she smiles."
    )
    evidence = attempt_evidence({"metadata": {"duration": 15.0}, "beats": [beat]})
    assert beat["actionStrategyFamily"] == "CATCH"
    assert beat["intendedStrategyFamily"] == "SQUEEZE"
    assert evidence.strategy_families == ("SQUEEZE",)
    assert evidence.attempts[0]["reactiveActionFamily"] == "CATCH"


def test_target_and_intended_effect_are_not_strategy_families() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "goalEvidence": {"targetObject": "red ball", "intendedEffect": "restore_or_control_normal_object_use"},
        "beats": [{
            "id": "b1", "isAttempt": True, "primaryVerb": "PULLS",
            "action": "Mimi pulls the red ball", "consequence": "the ball moves",
            "targetObject": "red ball", "intendedEffect": "restore_or_control_normal_object_use",
            "duration": 5.0, "attemptSource": "STRUCTURED_PLAN_ROLE",
        }],
    }
    assert attempt_evidence(ir).strategy_families == ("PULL",)


def test_legacy_strategy_fields_cannot_override_physical_action() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [{
            "id": "b1", "isAttempt": True, "primaryVerb": "PULL",
            "action": "Mimi pulls the red ball", "consequence": "the ball moves",
            "strategyFamily": "red ball",
            "intendedStrategyFamily": "restore_or_control_normal_object_use",
            "targetObject": "red ball", "intendedEffect": "restore_or_control_normal_object_use",
            "duration": 5.0, "attemptSource": "STRUCTURED_PLAN_ROLE",
        }],
    }
    evidence = attempt_evidence(ir)
    assert evidence.strategy_families == ("PULL",)
    assert evidence.attempts[0]["intendedStrategyFamily"] == "PULL"


def test_consequence_contains_result_lines_not_the_action_line() -> None:
    (beat,) = _beats(
        "0.0-15.0 SEC — FIRST ATTEMPT\n"
        "Mimi pulls the rope.\n"
        "The rope stretches toward her.\n"
        "She lets go."
    )
    assert beat["action"] == "Mimi pulls the rope."
    assert beat["consequence"].startswith("The rope stretches")
    assert not beat["consequence"].startswith(beat["action"])


def test_attempt_evidence_summary_counts_sources_and_ratio() -> None:
    ir = parse_prompt(
        "Title: Label Semantics\n\n15-second video\n\n## Timeline\n"
        "0.0-5.0 SEC — FIRST ATTEMPT\nMimi pulls the rope.\n"
        "5.0-10.0 SEC: Mimi blocks the door\n"
        "10.0-15.0 SEC — FAKE RESOLUTION\nMimi relaxes.\n"
    ).video_plan_ir
    evidence = attempt_evidence(ir)
    assert evidence.count == 1
    assert evidence.sources == {"STRUCTURED_PLAN_ROLE": 1}
    assert evidence.active_ratio == 5.0 / 15.0


def test_attempt_002_does_not_collapse_unspecified_verbs_into_one_strategy() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.5.yaml"))
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [
            {
                "isAttempt": True,
                "primaryVerb": UNSPECIFIED_VERB,
                "action": "a",
                "consequence": "x",
                "duration": 5,
            },
            {
                "isAttempt": True,
                "primaryVerb": UNSPECIFIED_VERB,
                "action": "b",
                "consequence": "y",
                "duration": 5,
            },
            {
                "isAttempt": True,
                "primaryVerb": UNSPECIFIED_VERB,
                "action": "c",
                "consequence": "z",
                "duration": 5,
            },
        ],
    }
    with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]) as judge:
        result = engine._evaluate_attempt_002(ir, {})
    assert result.actual_value == 3
    assert len(judge.call_args.args[0]) == 3


def test_markdown_attempt_sections_become_canonical_attempts_without_source_rewrite() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "prompts"
    box_cat = parse_prompt((root / "box-cat-01.md").read_text(encoding="utf-8")).video_plan_ir
    spot_cat = parse_prompt((root / "spot-cat-01.md").read_text(encoding="utf-8")).video_plan_ir

    box_evidence = attempt_evidence(box_cat)
    spot_evidence = attempt_evidence(spot_cat)
    assert box_evidence.active_attempt_count == 3
    assert box_evidence.distinct_strategy_count == 3
    assert spot_evidence.active_attempt_count == 3
    assert spot_evidence.distinct_strategy_count == 1
    assert spot_evidence.strategy_families == ("COMMIT_TO_TARGET",) * 3


def test_reactive_look_smile_wait_beats_do_not_become_attempts() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"id": "look", "beatRole": "REACTION", "action": "Mimi looks at the box", "isAttempt": False},
            {"id": "smile", "beatRole": "REACTION", "action": "Mimi smiles", "isAttempt": False},
            {"id": "wait", "beatRole": "REACTION", "action": "Mimi waits", "isAttempt": False},
        ],
    }
    evidence = attempt_evidence(ir)
    assert evidence.active_attempt_count == 0
    assert evidence.distinct_strategy_count == 0
