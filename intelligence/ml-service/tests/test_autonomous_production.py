import shutil
from pathlib import Path

from app.workflow.autonomous_production import read_run, start_idempotent


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/creative-shape-v1/experiment-seed-42-count-20.json"


def test_existing_candidate_run_replays_gates_and_stops_before_any_paid_provider(tmp_path, monkeypatch):
    library = tmp_path / "library/01-CHARACTERS/drawings"
    library.mkdir(parents=True)
    shutil.copy2(ROOT.parent.parent / "yuvarlak-dunya/01-CHARACTERS/drawings/opa.png", library / "opa.png")
    monkeypatch.setenv("OPENART_ENABLED", "false")
    monkeypatch.setenv("OPENART_MOCK_ENABLED", "true")
    monkeypatch.delenv("OPENART_TOKEN", raising=False)
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "false")
    monkeypatch.delenv("AUTONOMOUS_MAX_SPEND_USD", raising=False)

    run = start_idempotent("offline-test-run-001", root=tmp_path, source_path=SOURCE)

    assert run["version"] == "autonomous-production-entry-v1"
    assert run["source"]["candidateCount"] == 9
    assert run["selectedCandidateId"] == "bg2-f902cc280181d9eb"
    selected = next(
        row for row in run["candidateEvaluations"] if row["candidateId"] == run["selectedCandidateId"]
    )
    assert selected["ranking"]["eligibility"] == "ELIGIBLE"
    assert selected["ranking"]["shortFormScore"] == 99
    assert selected["ranking"]["rankingScore"] == 97.6
    assert selected["beatGrammar"]["beatGrammarQuality"] == "STRONG"
    assert selected["premiseNaturalness"]["admitted"] is True
    assert selected["creativeShape"]["payoffFamily"] == "CONTROL_REVERSAL"
    assert len(selected["candidate"]["structuredBeatPlan"]) == 5
    assert selected["candidate"]["intendedDurationSeconds"] == 15
    assert run["characterReference"]["status"] == "DISCOVERED_UNREVIEWED"
    assert run["characterReference"]["sha256"]
    assert run["firstFrame"]["status"] == "MISSING"
    assert run["productionHistory"]["status"] == "NOT_EVALUATED"
    assert run["providerRequests"] == run["imageGenerationRequests"] == run["renderRequests"] == 0
    assert run["status"] == "AWAITING_HUMAN_REVIEW"
    assert {row["code"] for row in run["blockers"]} >= {
        "CANONICAL_CHARACTER_REFERENCE_REVIEW_REQUIRED",
        "CREATIVE_REVIEW_RECOMMENDED_HIGH_TEMPLATE_SHAPE_RISK",
        "RUN_LEVEL_SPENDING_AUTHORIZATION_MISSING",
        "RUN_LEVEL_SPENDING_LIMIT_MISSING",
        "LIVE_MODEL_CAPABILITY_UNVERIFIED",
        "OPENART_LIVE_DISPATCH_DISABLED",
        "PRODUCTION_HISTORY_AUTOMATED_LOOKUP_NOT_CONNECTED",
    }
    assert read_run(run["runId"], root=tmp_path) == run


def test_idempotency_key_returns_the_same_persisted_run_without_second_provider_action(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENART_ENABLED", "false")
    monkeypatch.setenv("OPENART_MOCK_ENABLED", "true")
    first = start_idempotent("offline-test-run-idempotent", root=tmp_path, source_path=SOURCE)
    second = start_idempotent("offline-test-run-idempotent", root=tmp_path, source_path=SOURCE)
    assert second["runId"] == first["runId"]
    assert second["providerRequests"] == 0
    assert len(list((tmp_path / "autonomous-production/runs").glob("*.json"))) == 1


def test_run_loader_rejects_traversal(tmp_path):
    try:
        read_run("../anything", root=tmp_path)
    except ValueError as error:
        assert "Invalid production run id" in str(error)
    else:
        raise AssertionError("unsafe run id unexpectedly accepted")
