"""Versioned registry, source-domain, history and provider-free regressions."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from test_ruleset_1_7_stubborn_return import spoon_ir

from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import return_loop_applicability
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager
from app.workflow.review import _run_canonical_evaluation

INPUTS = json.loads(
    (
        Path(__file__).resolve().parents[3] / "output/verification/step6-score-forensics/inputs.json"
    ).read_text()
)


def engine(version="1.8"):
    return RuleEngine(str(settings.rules_dir / f"RULESET_{version}.yaml"))


def test_registry_preserves_declared_severities_and_stage():
    assert len(engine("1.7").ruleset["rules"]) == 8
    e = engine()
    assert len(e.ruleset["rules"]) == 46
    ancestor = yaml.safe_load((settings.rules_dir / "RULESET_1.5.yaml").read_text())
    registered = {r["id"]: r for r in e.ruleset["rules"]}
    for r in ancestor["rules"]:
        assert r["id"] in e.evaluators
        assert registered[r["id"]]["severity"] == r["severity"]
        assert registered[r["id"]].get("evaluation_stage", "PRE_RENDER") == r.get(
            "evaluation_stage", "PRE_RENDER"
        )
    assert RuleVersionManager(settings.rules_dir).get_latest_version() == "1.10"


@pytest.mark.parametrize("name", list(INPUTS))
def test_saved_sources_history_and_no_provider(name):
    s = INPUTS[name]
    q = {**s["boundRequest"], "prompt": s["originalPrompt"]}
    old = _run_canonical_evaluation({**q, "canonicalRulesetVersion": "1.7"})
    assert old["score"] == 85 and old["grade"] == "B" and old["rulesEvaluated"] == 8
    with patch("app.llm.semantic_checks.get_provider", side_effect=AssertionError("Forbidden paid call")):
        new = _run_canonical_evaluation({**q, "canonicalRulesetVersion": "1.8"})
    assert new["status"] == "EVALUATED" and new["rulesEvaluated"] == 46 and new["rulesetVersion"] == "1.8"
    rows = {
        r["ruleId"]: r["outcome"]
        for k in ("passedRules", "failedRules", "unknownRules", "notApplicableRules")
        for r in new[k]
    }
    assert rows["STUBBORN_RETURN_LOOP"] == "NOT_APPLICABLE"
    assert rows["CONSISTENCY_002"] == "NOT_APPLICABLE"
    assert rows["GOAL_001"] == "UNKNOWN"
    assert (
        "each pull doubles the number of sticky notes" in new["videoPlanIR"]["coreMechanic"]["physicalRule"]
    )


@pytest.mark.parametrize(
    "mechanic",
    ["Each pull doubles the cards.", "The paint persists on the wall.", "The stamp sticks to every surface."],
)
def test_non_return_mechanics(mechanic):
    ir = {
        "coreMechanic": {"physicalRule": mechanic, "recurrence": True},
        "beats": [
            {"action": "Zed pulls", "isAttempt": True},
            {"action": "Zed pulls again", "isAttempt": True},
        ],
    }
    assert return_loop_applicability(ir) == "NOT_APPLICABLE"
    assert engine()._evaluate_stubborn_return_loop(ir, {}).outcome is RuleOutcome.NOT_APPLICABLE


def test_actual_return_and_uncertain_evidence():
    assert return_loop_applicability(spoon_ir()) == "APPLICABLE"
    assert engine()._evaluate_stubborn_return_loop(spoon_ir(), {}).outcome is RuleOutcome.PASS
    for ir in (spoon_ir(weak=True), spoon_ir(explicit=True, weak=True), {}):
        assert return_loop_applicability(ir) == "UNKNOWN"
        assert engine()._evaluate_stubborn_return_loop(ir, {}).outcome is RuleOutcome.UNKNOWN
    assert engine()._evaluate_stubborn_return_hook({}, {}).outcome is RuleOutcome.UNKNOWN


def test_profile_stage_and_retirement():
    ir = parse_prompt(INPUTS["baseline"]["originalPrompt"]).video_plan_ir
    ir["metadata"]["contentProfile"] = "EDUCATIONAL"
    rows = {r.rule_id: r for r in engine().evaluate(ir).evaluations}
    assert rows["ATTEMPT_002"].outcome is RuleOutcome.NOT_APPLICABLE
    assert rows["CONSISTENCY_002"].outcome is RuleOutcome.NOT_APPLICABLE
    assert rows["MINI_STORY_LOCK"].outcome is RuleOutcome.PASS
    assert not RuleEngine._rule_applies({"scopeType": "CONTENT_FAMILY", "scopeId": "other"}, ir)
    assert not RuleEngine._rule_applies({"retired": True}, ir)


def test_hook_and_temporal_sensitivity():
    ir = parse_prompt(INPUTS["baseline"]["originalPrompt"]).video_plan_ir
    e = engine()
    assert e._evaluate_goal_visible_early(ir, {}).outcome is RuleOutcome.PASS
    late = deepcopy(ir)
    late["beats"][0]["startTime"] = 3
    late["goalEvidence"]["startsAt"] = 3
    assert e._evaluate_goal_visible_early(late, {}).outcome is RuleOutcome.FAIL
    overload = deepcopy(ir)
    overload["beats"] += [
        dict(
            overload["beats"][1],
            id=f"extra-{n}",
            majorBeat=True,
            visualStateId=f"extra-{n}",
            action=f"new event {n}",
            consequence=f"new consequence {n}",
        )
        for n in range(4)
    ]
    assert e._evaluate_temporal_complexity_split_gate(overload, {}).outcome is RuleOutcome.FAIL


def test_loader_validation(tmp_path):
    def write(n, x):
        (tmp_path / n).write_text(yaml.safe_dump(x))

    write("a.yaml", {"version": "1.8", "inheritancePolicy": "RECURSIVE_V1", "extends": "b.yaml", "rules": []})
    write("b.yaml", {"extends": "a.yaml", "rules": []})
    with pytest.raises(ValueError, match="cycle"):
        RuleEngine(str(tmp_path / "a.yaml"))
    write("b.yaml", {"rules": [{"id": "X"}]})
    write(
        "a.yaml",
        {"version": "1.8", "inheritancePolicy": "RECURSIVE_V1", "extends": "b.yaml", "rules": [{"id": "X"}]},
    )
    with pytest.raises(ValueError, match="explicit overrides"):
        RuleEngine(str(tmp_path / "a.yaml"))
    write(
        "a.yaml",
        {"version": "1.8", "inheritancePolicy": "RECURSIVE_V1", "extends": "missing.yaml", "rules": []},
    )
    with pytest.raises(FileNotFoundError):
        RuleEngine(str(tmp_path / "a.yaml"))
    write(
        "a.yaml", {"version": "1.8", "inheritancePolicy": "RECURSIVE_V1", "rules": [{"id": "X"}, {"id": "X"}]}
    )
    with pytest.raises(ValueError, match="Duplicate"):
        RuleEngine(str(tmp_path / "a.yaml"))
