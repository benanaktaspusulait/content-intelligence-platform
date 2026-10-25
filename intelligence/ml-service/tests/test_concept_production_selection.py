from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.workflow.concept_production_selection import select_production, materially_distinct
from app.workflow.creative_distance import creative_distance


@pytest.fixture
def fixture():
    return json.loads((Path(__file__).parent / "fixtures/chair_concentration_v2.json").read_text())


def test_high_scoring_chair_variants_do_not_crowd_out_lid_and_brush(fixture):
    rows = deepcopy(fixture["rankedRows"])
    before = deepcopy(rows)
    selected = select_production(rows, fixture["candidates"])
    assert {r["candidateId"] for r in selected["productionSlate"]} == {"chair-a", "lid", "brush"}
    assert selected["firstRenderCandidate"] == "chair-a"
    assert any(a["code"] == "CREATIVE_DIVERSITY_PROMOTION" for a in selected["diversityAdjustments"])
    assert rows == before
    a, b = fixture["candidates"][:2]
    assert a["structuralFingerprint"]["fullHash"] != b["structuralFingerprint"]["fullHash"]
    assert creative_distance(a, b)["visualSilhouetteSimilarity"] == 1
    assert not materially_distinct(a, b)


@pytest.mark.parametrize(
    "signal", ["payoff", "progress", "frameZero", "duplicateRisk", "productionRisk", "rewatch"]
)
def test_meaningful_tie_signals_precede_candidate_id(fixture, signal):
    a = deepcopy(fixture["candidates"][0])
    b = deepcopy(a)
    a["candidateId"] = "a-low"
    b["candidateId"] = "z-best"
    rows = [deepcopy(fixture["rankedRows"][0]) for _ in range(2)]
    for i, r in enumerate(rows):
        r["candidateId"] = [a, b][i]["candidateId"]
        r["rank"] = i + 1
    if signal == "payoff":
        rows[1]["shortFormEngine"]["payoffScore"] = 101
    elif signal == "progress":
        rows[1]["shortFormEngine"]["progressDensityScore"] = 101
    elif signal == "frameZero":
        rows[1]["shortFormEngine"]["instantPremiseLegibility"]["score"] = 101
    elif signal == "duplicateRisk":
        rows[0]["duplicateRisk"] = "MODERATE"
    elif signal == "productionRisk":
        rows[0]["productionRisk"]["flags"] = ["CONTACT_RISK"]
    elif signal == "rewatch":
        rows[1]["shortFormEngine"]["rewatchScore"] = 100
    assert select_production(rows, [a, b])["productionOrder"][0] == "z-best"


def test_batch_novelty_and_visual_novelty_precede_id(fixture):
    a = deepcopy(fixture["candidates"][0])
    b = deepcopy(a)
    peer = deepcopy(a)
    a["candidateId"] = "a"
    b["candidateId"] = "z"
    peer["candidateId"] = "peer"
    b["composition"]["goalFamily"] = "DIFFERENT_GOAL"
    b["composition"]["objectCategory"] = "DIFFERENT_OBJECT"
    rows = [deepcopy(fixture["rankedRows"][0]) for _ in range(2)]
    for i, r in enumerate(rows):
        r["candidateId"] = [a, b][i]["candidateId"]
        r["rank"] = i + 1
    assert select_production(rows, [a, b, peer])["productionOrder"][0] == "z"
    b["composition"] = deepcopy(a["composition"])
    b["visualFingerprint"]["characterPoseFamily"] = "DIFFERENT_POSE"
    assert select_production(rows, [a, b, peer])["productionOrder"][0] == "z"


def test_id_only_final_fallback_after_all_creative_signals_tie(fixture):
    a = deepcopy(fixture["candidates"][0])
    b = deepcopy(a)
    a["candidateId"] = "z"
    b["candidateId"] = "a"
    rows = [deepcopy(fixture["rankedRows"][0]) for _ in range(2)]
    for i, r in enumerate(rows):
        r["candidateId"] = [a, b][i]["candidateId"]
        r["rank"] = i + 1
    assert select_production(rows, [a, b])["productionOrder"] == ["a", "z"]
    assert select_production(list(reversed(rows)), [b, a])["productionOrder"] == ["a", "z"]


def test_lower_quality_cannot_chain_across_anchored_band(fixture):
    rows = deepcopy(fixture["rankedRows"])
    rows[0]["rankingScore"] = 100
    rows[1]["rankingScore"] = 96
    rows[1]["shortFormEngine"]["payoffScore"] = 1000
    result = select_production(rows, fixture["candidates"])
    first_band = result["tieBands"][0]["candidateIds"]
    assert "chair-b" not in first_band


def test_quality_gap_does_not_force_a_weak_diverse_slate(fixture):
    rows = deepcopy(fixture["rankedRows"])
    for r in rows[2:]:
        r["rankingScore"] = 50
    assert len(select_production(rows, fixture["candidates"])["productionSlate"]) == 1
