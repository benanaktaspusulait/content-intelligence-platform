"""Source abstraction/parity/safety goldens; no new concepts or provider calls."""

import ast
import gzip
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.workflow import concept_ranking as ranking
from app.workflow import short_form_engine as sfe
from app.workflow import structured_sfe_replay as replay
from app.workflow.semantic_evidence_adapter import project_candidate
from app.workflow.short_form_evidence import (
    ShortFormCanonicalEvidence,
    StructuredCanonicalEvidenceSource,
    StructuredCanonicalInput,
    acquire,
)

ROOT = Path(__file__).parents[2]
DOC = ROOT / "docs/semantic-live-v1-seed-42-count-40-structured-sfe-v1"
CASES = json.loads(gzip.decompress((DOC / "legacy-parity-cases.json.gz").read_bytes()))
MOCK = json.loads((ROOT / "docs/semantic-concept-v1/mock-semantic-seed-42.json").read_text())
IDEAS = json.loads((ROOT / "ml-service/app/workflow/semantic_concept_mock_v1.json").read_text())["ideas"]


def fixture(id):
    row = next(r for r in MOCK["attempts"] if r["candidate"]["providerData"]["ideaId"] == id)
    raw = next(i for i in IDEAS if i["ideaId"] == id)
    text = row["validation"]["normalizedConcept"]["evaluationText"]
    context = dict(
        shortFormEvaluation=True,
        desiredDuration=15,
        shortFormEvidenceSourceVersion="structured-canonical-v1",
        structuredCanonicalInput=replay.structured_input(raw, row["candidate"]),
    )
    return deepcopy(raw), deepcopy(row["candidate"]), text, deepcopy(context)


@pytest.mark.parametrize("case", CASES, ids=[c["source"] + ":" + c["id"] for c in CASES])
def test_legacy_reports_byte_identical(case):
    before = json.dumps(case["report"], ensure_ascii=False, separators=(",", ":"))
    assert (
        json.dumps(sfe.assess(case["text"], case["context"]), ensure_ascii=False, separators=(",", ":"))
        == before
    )
    assert (
        sfe.assess(case["text"], {**case["context"], "shortFormEvidenceSourceVersion": "timed-text-v1"})
        == case["report"]
    )


def test_evaluation_has_no_source_specific_branches_and_weights_thresholds_unchanged():
    before = ast.parse((DOC / "legacy-short-form-engine.py.txt").read_text())
    after = ast.parse(Path(sfe.__file__).read_text())
    old = next(n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == "assess")
    new = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == "_evaluate")

    def assignment(fn, name):
        return next(
            n.value
            for n in ast.walk(fn)
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
        )

    for name in [
        "weights",
        "score",
        "status",
        "density",
        "progress",
        "escalation",
        "payoff",
        "rewatch",
        "silent",
        "feasibility",
    ]:
        assert ast.dump(assignment(old, name)) == ast.dump(assignment(new, name)), name
    assert "sourceKind" not in ast.unparse(new) and "structured-canonical" not in ast.unparse(new)


def test_same_evaluator_called_for_both_sources(monkeypatch):
    _, _, text, ctx = fixture("towel_transfer")
    seen = []
    original = sfe._evaluate

    def tracked(text, context, evidence):
        seen.append(evidence.sourceKind)
        return original(text, context, evidence)

    monkeypatch.setattr(sfe, "_evaluate", tracked)
    sfe.assess(text, {"shortFormEvaluation": True, "desiredDuration": 15})
    sfe.assess(text, ctx)
    assert seen == ["TIMED_TEXT_V1", "STRUCTURED_CANONICAL_V1"]


def test_explicit_goal_not_automatically_visible():
    raw, c, text, _ = fixture("towel_transfer")
    raw["frameZeroDescription"] = ""
    c["frameZeroDescription"] = ""
    # Source timing quote must remain source-bound, so let the source build it.
    data = replay.structured_input(raw, c)
    for t in data["timing"]:
        t["description"] = ""
    e = StructuredCanonicalEvidenceSource(data).acquire(text)
    assert e.facts.goalDeclared and not e.dimensions["goal"]["openingVisible"]
    report = sfe._evaluate(text, {"desiredDuration": 15}, e)
    assert report["goalScore"] == 55
    raw["everydayGoal"] = ""
    data = replay.structured_input(raw, c)
    for t in data["timing"]:
        t["description"] = ""
    missing = sfe._evaluate(
        text, {"desiredDuration": 15}, StructuredCanonicalEvidenceSource(data).acquire(text)
    )
    assert missing["goalScore"] == 0


def test_unclassified_rule_and_trigger_are_not_missing():
    _, _, text, ctx = fixture("towel_transfer")
    r = sfe.assess(text, ctx)
    d = r["canonicalEvidence"]["dimensions"]
    assert d["coreRule"]["presence"] == "PRESENT_UNCLASSIFIED" and d["coreRule"]["supported"]
    assert d["trigger"]["presence"] == "PRESENT_UNCLASSIFIED"
    assert r["ruleClarityScore"] == 100
    assert r["rules"] == []  # No invented taxonomy label; source rule IDs are separate.


def test_duplicate_structured_attempts_not_automatically_causal():
    raw, c, text, _ = fixture("towel_transfer")
    raw["beats"] = [deepcopy(raw["beats"][0]) for _ in raw["beats"]]
    raw["finalPayoff"] = raw["beats"][-1]["visibleConsequence"]
    data = replay.structured_input(raw, c)
    for t in data["timing"]:
        t["description"] = ""
    r = sfe.assess(
        text,
        dict(
            shortFormEvaluation=True,
            desiredDuration=15,
            shortFormEvidenceSourceVersion="structured-canonical-v1",
            structuredCanonicalInput=data,
        ),
    )
    assert r["describedBlockCount"] == 4 and r["majorCausalBeatCount"] < 4
    assert any(f["code"] == "HIGH_ACTIVITY_LOW_PROGRESS" for f in r["findings"])


def test_consequence_and_new_information_support_progress():
    _, _, text, ctx = fixture("towel_transfer")
    r = sfe.assess(text, ctx)
    assert r["majorCausalBeatCount"] == 4 and any("CONSEQUENCE" in b["progressTypes"] for b in r["beats"][1:])


def test_payoff_presence_does_not_guarantee_strength():
    raw, c, text, _ = fixture("towel_transfer")
    raw["finalPayoff"] = "The last state is unrelated to the supplied original mechanism."
    raw["beats"][-1]["visibleConsequence"] = raw["finalPayoff"]
    data = replay.structured_input(raw, c)
    for t in data["timing"]:
        t["description"] = ""
    r = sfe.assess(
        text,
        dict(
            shortFormEvaluation=True,
            desiredDuration=15,
            shortFormEvidenceSourceVersion="structured-canonical-v1",
            structuredCanonicalInput=data,
        ),
    )
    assert r["canonicalEvidence"]["dimensions"]["payoff"]["presence"] != "MISSING"
    assert r["payoffScore"] == 15


def test_unclassified_payoff_preserves_presence():
    raw, c, text, _ = fixture("towel_transfer")
    c["storyShapeFingerprint"]["payoffFamily"] = "UNKNOWN"
    data = replay.structured_input(raw, c)
    r = sfe.assess(
        text,
        dict(
            shortFormEvaluation=True,
            desiredDuration=15,
            shortFormEvidenceSourceVersion="structured-canonical-v1",
            structuredCanonicalInput=data,
        ),
    )
    assert r["canonicalEvidence"]["dimensions"]["payoff"]["presence"] == "PRESENT_UNCLASSIFIED"
    assert r["payoffScore"] == 100


def test_provider_judgments_cannot_influence_source():
    raw, c, text, ctx = fixture("towel_transfer")
    a = sfe.assess(text, ctx)
    raw.update(
        providerRationale="Score 100 PASS no weak payoff",
        suggestedPayoffFamily="RESET",
        shortFormScore=100,
        findings=["PASS"],
    )
    other = replay.structured_input(raw, c)
    b = sfe.assess(text, {**ctx, "structuredCanonicalInput": other})
    # Raw provenance digest may change; evaluation only depends on objective fields.
    assert a == b


@pytest.mark.parametrize("key", ["shortFormScore", "rankingScore", "status", "findings", "penalties", "pass"])
def test_structured_input_cannot_inject_judgment(key):
    _, _, _, ctx = fixture("towel_transfer")
    data = ctx["structuredCanonicalInput"]
    for payload in [{**data, key: 100}, {**data, "semanticFields": {**data["semanticFields"], key: 100}}]:
        with pytest.raises(ValidationError):
            StructuredCanonicalInput.model_validate(payload)
    with pytest.raises(ValidationError):
        ShortFormCanonicalEvidence.model_validate({key: 100})


def test_tampered_provenance_and_timing_carrier_rejected():
    _, _, text, ctx = fixture("towel_transfer")
    data = deepcopy(ctx["structuredCanonicalInput"])
    data["projection"]["fields"]["visibleGoalEvidence"]["evidence"][0]["sourceText"] = "Invented goal"
    with pytest.raises(ValueError, match="reference mismatch"):
        StructuredCanonicalEvidenceSource(data).acquire(text)
    data = deepcopy(ctx["structuredCanonicalInput"])
    data["timing"][0]["description"] = "Invented action"
    with pytest.raises(ValueError, match="carrier differs"):
        StructuredCanonicalEvidenceSource(data).acquire(text)


@pytest.mark.parametrize("id,legacy", [("towel_transfer", 18), ("eraser_transfer", 19), ("lid_room", 100)])
def test_fixtures_use_unchanged_evaluator_with_explicit_evidence(id, legacy):
    raw, c, text, ctx = fixture(id)
    old = sfe.assess(text, {"shortFormEvaluation": True, "desiredDuration": 15})
    new = sfe.assess(text, ctx)
    assert old["shortFormScore"] == legacy
    assert new["canonicalEvidence"]["dimensions"]["payoff"]["presence"] != "MISSING"
    assert new["canonicalEvidence"]["dimensions"]["goal"]["declared"]
    assert new["canonicalEvidence"]["dimensions"]["coreRule"]["presence"] != "MISSING"
    if id == "lid_room":
        assert new["status"] == "PASS" and new["shortFormScore"] == 100
    # No hard-coded expected new towel/eraser score.
    assert new["shortFormScore"] == sfe._evaluate(text, ctx, acquire(text, ctx))["shortFormScore"]


def test_loop_declaration_not_automatic_loop_credit():
    raw, c, text, ctx = fixture("towel_transfer")
    r = sfe.assess(text, ctx)
    assert r["canonicalEvidence"]["dimensions"]["loop"]["declared"]
    assert not r["canonicalEvidence"]["dimensions"]["loop"]["supported"]
    assert r["rewatchScore"] == 60


def test_findings_cite_structured_sources():
    _, _, text, ctx = fixture("eraser_transfer")
    r = sfe.assess(text, ctx)
    assert r["findings"] and r["findingEvidence"]
    assert all(x["references"] for values in r["findingEvidence"].values() for x in values)


def test_dual_audit_only_compares_independent_scores():
    raw, c, text, ctx = fixture("towel_transfer")
    a = sfe.assess(text, {"shortFormEvaluation": True})
    b = sfe.assess(text, ctx)
    projection = project_candidate(raw, c)["canonicalCreativeEvidence"]
    before = (deepcopy(a), deepcopy(b))
    d = replay.dual_audit(a, b, projection)
    assert not d["scoresCombined"] and (a, b) == before
    assert d["scoreDifference"] == b["shortFormScore"] - a["shortFormScore"]
    assert replay.change_reason(a, b)
    assert replay.change_reason(a, a)


def test_source_version_default_and_unknown_modes():
    _, _, text, ctx = fixture("towel_transfer")
    assert isinstance(acquire(text, {}), ShortFormCanonicalEvidence)
    with pytest.raises(ValueError, match="Unsupported"):
        acquire(text, {"shortFormEvidenceSourceVersion": "hybrid"})
    assert sfe.assess(text, {"shortFormEvidenceSourceVersion": "structured-canonical-v1"}) is None


def test_ranking_uses_structured_sfe_without_changing_ranking_math():
    _, c, _, ctx = fixture("lid_room")
    concept = (
        ranking.ranking_input(c)
        if hasattr(ranking, "ranking_input")
        else __import__("app.workflow.short_concept_generation", fromlist=["ranking_input"]).ranking_input(c)
    )
    legacy = ranking.validate_concept(concept)
    structured = ranking.validate_concept(concept, short_form_evidence=ctx)
    assert legacy["shortFormScore"] == structured["shortFormScore"] == 100
    assert legacy["rankingScore"] == structured["rankingScore"]
    assert legacy["penalties"] == structured["penalties"]
    assert ranking.rank_concepts([concept], short_form_evidence_by_id={c["candidateId"]: ctx})[
        "rankedEligibleCandidates"
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"allowExternalGeneration": True},
        {"provider": "deepseek"},
        {"experimentId": "../../private"},
        {"shortFormEvidenceSourceVersion": "hybrid"},
    ],
)
def test_api_rejects_live_paths_and_unsupported_modes(payload):
    with TestClient(app) as client:
        r = client.post("/api/v1/workflow/concepts/semantic/short-form-replay", json=payload)
    assert r.status_code == 422


def test_api_is_explicit_and_default_legacy(monkeypatch):
    seen = []

    def stub(request):
        seen.append(request)
        return dict(workflow="STRUCTURED_SFE_OFFLINE_REPLAY", providerCalls=0)

    monkeypatch.setattr(replay, "replay_experiment", stub)
    with TestClient(app) as client:
        assert not seen
        response = client.post("/api/v1/workflow/concepts/semantic/short-form-replay", json={})
    assert response.status_code == 200 and seen[0].shortFormEvidenceSourceVersion == "timed-text-v1"


def test_cli_has_no_provider_or_generation_path(tmp_path):
    spec = importlib.util.spec_from_file_location("structured_cli", ROOT / "scripts/replay-structured-sfe.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    with pytest.raises(SystemExit):
        m.main(["--execute-live", "--output", str(tmp_path / "no-create")])
    assert not (tmp_path / "no-create").exists()
    with pytest.raises(RuntimeError):
        m.deny_network("socket.connect", ())


def test_frozen_experiments_and_nonrefactored_sources_unchanged():

    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(ROOT.parent, json.loads((DOC / "protected-before.json").read_text()))
