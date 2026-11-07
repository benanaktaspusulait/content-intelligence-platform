import hashlib
import json
from pathlib import Path

from app.workflow.net_new_novelty import (
    SOURCE, compare_opening, context_record, load_exclusions, request_message,
)

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "intelligence/docs/net-new-generation-v1/runs/net-new-v1-20261102-001"


def current_seed():
    return json.loads((RUN / "phase-a/seed.json").read_text())


def test_historical_dough_ridge_paraphrase_is_confirmed_duplicate():
    result = compare_opening(current_seed())
    assert result["disposition"] == "DUPLICATE_CREATIVE_TERRITORY"
    assert result["results"][0]["matchingAxes"] == [
        "protagonist", "goal", "object", "coreRuleResponse", "triggerResponse", "firstFrameRelation"
    ]


def test_identical_mechanic_different_wording_is_detected():
    seed = current_seed()
    seed.update(
        impossibleRule="Whenever she bears down with the dough roller, the touched pastry rises into a standing rib instead of thinning.",
        visibleTrigger="The roller is applying downward force along the pastry strip.",
        frameZeroDescription="Mimi presses a dough roller; its narrow crest carries the tool above the sheet, with flat pastry on either side.",
    )
    result = compare_opening(seed)
    assert result["disposition"] == "DUPLICATE_CREATIVE_TERRITORY"


def test_same_character_with_different_object_and_rule_is_not_blocked():
    seed = current_seed()
    seed.update(primaryObject="Umbrella", everydayGoal="Open an umbrella before going outside.",
                impossibleRule="WHEN Mimi pulls the handle, the canopy folds inward.",
                visibleTrigger="Mimi pulls the umbrella handle.",
                frameZeroDescription="Mimi holds a folded umbrella beside a doorway.")
    assert compare_opening(seed)["disposition"] == "NO_KNOWN_EQUIVALENT"


def test_same_object_with_different_causal_rule_is_not_automatically_blocked():
    seed = current_seed()
    seed.update(impossibleRule="WHEN the rolling pin touches the dough, it whistles loudly.",
                visibleTrigger="The rolling pin touches dough.",
                frameZeroDescription="Mimi holds a rolling pin above flat dough.")
    assert compare_opening(seed)["disposition"] == "NO_KNOWN_EQUIVALENT"


def test_unrelated_opening_can_proceed_to_existing_quality_gate():
    seed = current_seed()
    seed.update(protagonistSuggestion="Kiko", primaryObject="Toothbrush",
                everydayGoal="Brush teeth before bed.",
                impossibleRule="WHEN Kiko brushes a tooth, the bristles turn into soft feathers.",
                visibleTrigger="Kiko presses the toothbrush to a tooth.",
                frameZeroDescription="Kiko brushes teeth with feathers covering the brush head.")
    assert compare_opening(seed)["disposition"] == "NO_KNOWN_EQUIVALENT"


def test_unknown_is_not_a_pass():
    seed = current_seed()
    seed["frameZeroDescription"] = "Mimi stands at a kitchen counter beside a bowl."
    result = compare_opening(seed)
    assert result["disposition"] != "NO_KNOWN_EQUIVALENT"
    assert result["unknownIsPass"] is False


def test_source_evidence_remains_immutable_and_context_is_hash_bound():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    record = context_record()
    message = request_message(record)
    parsed = json.loads(message["content"])
    assert parsed["contextVersion"] == record["version"]
    assert parsed["contextSha256"] == record["contextSha256"]
    assert load_exclusions()[0]["sourceSha256"] == before
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before


def test_accepted_prompt_unchanged_and_live_request_had_no_historical_leakage():
    prompt = ROOT / "intelligence/ml-service/app/workflow/semantic_opening_seed_prompt_v1.txt"
    saved = RUN / "phase-a/prompt.json"
    accepted = json.loads(saved.read_text())
    assert accepted["system"] == prompt.read_text().strip()
    assert "rolling" not in accepted["system"].casefold()
    assert "dough" not in accepted["system"].casefold()
    assert "rolling" not in accepted["prompt"].casefold()
    assert "dough" not in accepted["prompt"].casefold()


def test_explicit_authorization_and_no_retry_contract_remain():
    script = (ROOT / "intelligence/scripts/run-net-new-two-stage-v1.py").read_text()
    assert "AUTHORIZE_PHASE_A:{run_id}:MAX_PROVIDER_REQUESTS=1" in script
    assert "retries=0, sdkRetries=0, replacements=0" in script
    assert "PHASE_A_NOVELTY_NOT_CLEARED_NO_PHASE_B_REQUEST" in script

