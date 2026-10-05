"""Direct evaluator coverage for the RULESET_1.4 creative-quality gates."""

from typing import Any

from app.config import settings
from app.quality.contracts import RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine


def _engine() -> RuleEngine:
    return RuleEngine(str(settings.rules_dir / "RULESET_1.4.yaml"))


def _base_ir(**overrides: Any) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "hook": {
            "staticWrongness": True,
            "noHistoryRequired": True,
            "noMicroComparison": True,
            "largeVisualSignal": True,
            "characterAlreadyEngaged": True,
        },
        "beats": [],
        "finalPayoff": {},
        "creativeFingerprint": {
            "visualEngineFamily": "single_object_reversal",
            "knownWinnerEngineFamilies": ["spill_and_fill"],
            "silhouetteSimilarity": 0.2,
        },
    }
    ir.update(overrides)
    return ir


def _chained_attempts() -> list[dict[str, Any]]:
    return [
        {
            "startTime": 0.0,
            "endTime": 3.0,
            "duration": 3.0,
            "isAttempt": True,
            "action": "steps left and catches the box",
            "consequence": "box slips right",
            "motionAmount": "high",
        },
        {
            "startTime": 3.2,
            "endTime": 7.0,
            "duration": 3.8,
            "isAttempt": True,
            "action": "pivots and reaches across",
            "consequence": "box turns back",
            "motionAmount": "high",
        },
        {
            "startTime": 7.1,
            "endTime": 12.0,
            "duration": 4.9,
            "isAttempt": True,
            "action": "runs and pulls the box close",
            "consequence": "the rule finally breaks",
            "motionAmount": "high",
        },
    ]


def test_continuous_action_momentum_passes_when_attempts_chain() -> None:
    evaluation = _engine()._evaluate_continuous_action_momentum(
        _base_ir(beats=_chained_attempts(), finalPayoff={"startsAt": 12.0}), {},
    )
    assert evaluation.outcome is RuleOutcome.PASS


def test_continuous_action_momentum_blocks_passive_reaction_and_reset() -> None:
    attempts = _chained_attempts()
    evaluation = _engine()._evaluate_continuous_action_momentum(
        _base_ir(
            beats=[
                attempts[0],
                {
                    "startTime": 3.0,
                    "endTime": 7.0,
                    "duration": 4.0,
                    "action": "stops, looks puzzled, and resets to neutral",
                    "motionAmount": "none",
                },
                attempts[1],
                {
                    "startTime": 7.0,
                    "endTime": 10.0,
                    "duration": 3.0,
                    "action": "stands still and smiles",
                    "motionAmount": "none",
                },
                attempts[2],
            ],
            finalPayoff={"startsAt": 10.0},
        ),
        {},
    )
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.CRITICAL
    assert evaluation.details["standaloneReactionCount"] == 2


def test_instant_visual_absurdity_gate_passes_with_all_required_signals() -> None:
    evaluation = _engine()._evaluate_instant_visual_absurdity_gate(_base_ir(), {})
    assert evaluation.outcome is RuleOutcome.PASS


def test_instant_visual_absurdity_gate_blocks_missing_evidence() -> None:
    evaluation = _engine()._evaluate_instant_visual_absurdity_gate(
        _base_ir(hook={"staticWrongness": True}), {},
    )
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.BLOCKER
    assert "noHistoryRequired" in evaluation.details["missingEvidence"]


def test_instant_visual_absurdity_gate_blocks_counting_hook() -> None:
    evaluation = _engine()._evaluate_instant_visual_absurdity_gate(
        _base_ir(hook={"staticWrongness": True, "description": "count 1 vs 3 objects"}), {},
    )
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.BLOCKER


def test_engine_silhouette_duplicate_blocks_known_winner_family() -> None:
    evaluation = _engine()._evaluate_engine_silhouette_duplicate(
        _base_ir(
            creativeFingerprint={
                "visualEngineFamily": "spill_and_fill",
                "knownWinnerEngineFamilies": ["spill_and_fill"],
                "silhouetteSimilarity": 0.2,
            }
        ),
        {},
    )
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.BLOCKER


def test_engine_silhouette_duplicate_blocks_missing_comparison() -> None:
    evaluation = _engine()._evaluate_engine_silhouette_duplicate(
        _base_ir(creativeFingerprint={}), {},
    )
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.BLOCKER


def test_engine_silhouette_duplicate_passes_distinct_family_and_low_similarity() -> None:
    evaluation = _engine()._evaluate_engine_silhouette_duplicate(_base_ir(), {})
    assert evaluation.outcome is RuleOutcome.PASS
