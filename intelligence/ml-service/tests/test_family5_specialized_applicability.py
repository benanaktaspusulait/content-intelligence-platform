"""Focused tests for the rule-id keyed Family 5 applicability projection."""

from __future__ import annotations

from pathlib import Path

from test_ruleset_1_7_stubborn_return import RULESET, spoon_ir

from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import (
    SPECIALIZED_RULE_IDS,
    SpecializedApplicabilityEvidence,
    specialized_applicability_evidence,
)
from app.quality.contracts import RuleEvaluation, RuleOutcome
from app.rules.rule_engine import RuleEngine

ROOT = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "prompts"


def parse_asset(name: str) -> dict:
    return parse_prompt((ROOT / name).read_text(encoding="utf-8")).video_plan_ir


def test_box_cat_is_applicable_for_loop_and_payoff_but_unknown_for_hook() -> None:
    evidence = specialized_applicability_evidence(parse_asset("box-cat-01.md"))

    assert evidence["STUBBORN_RETURN_LOOP"].status == "APPLICABLE"
    assert evidence["STUBBORN_RETURN_HOOK"].status == "UNKNOWN"
    assert evidence["STUBBORN_RETURN_PAYOFF"].status == "APPLICABLE"
    assert all(item.evidence_references for item in evidence.values() if item.status != "UNKNOWN")


def test_spot_cat_is_outside_the_stubborn_return_domain() -> None:
    evidence = specialized_applicability_evidence(parse_asset("spot-cat-01.md"))

    assert {item.status for item in evidence.values()} == {"NOT_APPLICABLE"}


def test_family5_negative_boundaries_are_not_applicable() -> None:
    for prompt in (
        "sticky-ball-01.txt",
        "ball-crocodile-01.txt",
        "lamp-01.md",
        "snack-box-01.md",
        "sneaky-door-01.md",
        "island-journal-01.txt",
    ):
        evidence = specialized_applicability_evidence(parse_asset(prompt))
        assert {item.status for item in evidence.values()} == {"NOT_APPLICABLE"}


def test_missing_ir_is_unknown_without_inventing_not_applicable() -> None:
    evidence = specialized_applicability_evidence(None)

    assert set(evidence) == set(SPECIALIZED_RULE_IDS)
    assert {item.status for item in evidence.values()} == {"UNKNOWN"}
    assert all(item.evidence_references == () for item in evidence.values())
    assert all("unavailable" in item.reason.lower() for item in evidence.values())


def test_projection_uses_canonical_statuses_without_entering_ruleset_outcomes() -> None:
    ir = spoon_ir()
    evidence = specialized_applicability_evidence(ir)
    assert set(evidence) == set(SPECIALIZED_RULE_IDS)

    engine = RuleEngine(RULESET)
    attempt = engine._evaluate_attempt_002(ir, {})
    payoff = engine._evaluate_stubborn_return_payoff(ir, {})
    assert attempt.outcome is RuleOutcome.PASS
    assert payoff.outcome is RuleOutcome.PASS

    report = engine.evaluate(ir)
    assert all(isinstance(item, RuleEvaluation) for item in report.evaluations)
    assert not any(isinstance(item, SpecializedApplicabilityEvidence) for item in report.evaluations)
    outcomes = {item.rule_id: item.outcome for item in report.evaluations}
    assert outcomes["STUBBORN_RETURN_LOOP"] is RuleOutcome.PASS
    assert outcomes["STUBBORN_RETURN_PAYOFF"] is RuleOutcome.PASS


def test_projection_serializes_canonical_camel_case_fields() -> None:
    evidence = specialized_applicability_evidence(parse_asset("box-cat-01.md"))

    assert set(evidence["STUBBORN_RETURN_LOOP"].to_dict()) == {
        "status",
        "confidence",
        "evidenceReferences",
        "reason",
    }
