import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.workflow.short_concept_generation import generate_and_rank


def test_local_generation_api_is_exactly_the_shared_pipeline_without_a_provider():
    with (
        patch("app.llm.provider.get_provider", side_effect=AssertionError("No external providers")),
        patch(
            "app.workflow.review._run_canonical_evaluation",
            side_effect=AssertionError("No canonical regrade"),
        ),
    ):
        response = TestClient(app).post("/api/v1/workflow/concepts/generate", json={"count": 20, "seed": 42})
    assert response.status_code == 200
    assert response.json() == generate_and_rank({"count": 20, "seed": 42})
    assert response.json()["providerCalls"] == 0 and not response.json()["renderAuthorized"]


def test_api_canonical_snapshot_and_constraints_are_deterministic():
    config = {
        "count": 10,
        "seed": 7,
        "canonicalCast": [{"id": "registered-a", "name": "Kiko"}, {"id": "registered-b", "name": "Mimi"}],
        "characterIds": ["registered-b"],
        "excludeObjects": ["chair", "shoe"],
    }
    client = TestClient(app)
    first = client.post("/api/v1/workflow/concepts/generate", json=config)
    second = client.post(
        "/api/v1/workflow/concepts/generate",
        json={
            **config,
            "canonicalCast": list(reversed(config["canonicalCast"])),
            "excludeObjects": ["SHOE", "chair"],
        },
    )
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    assert all(row["candidate"]["protagonist"] == "Mimi" for row in first.json()["candidates"])


@pytest.mark.parametrize(
    "payload",
    [
        {"count": 9},
        {"count": 101},
        {"seed": -1},
        {"seed": True},
        {"duration": 60},
        {"provider": "openai"},
        {"canonicalCast": []},
        {"characterIds": ["unregistered"]},
    ],
)
def test_api_invalid_inputs_or_external_provider_selection_are_rejected(payload):
    response = TestClient(app).post("/api/v1/workflow/concepts/generate", json=payload)
    assert response.status_code == 422


def load_cli():
    script = Path(__file__).parents[2] / "scripts/generate-short-concepts.py"
    spec = importlib.util.spec_from_file_location("local_concept_generation_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return script, module


def test_cli_json_and_human_report_match_api_pipeline_in_process(monkeypatch, capsys):
    script, module = load_cli()
    monkeypatch.setattr(sys, "argv", [str(script), "--count", "20", "--seed", "42", "--rank"])
    assert module.main() == 0
    expected = generate_and_rank({"count": 20, "seed": 42})
    assert json.loads(capsys.readouterr().out) == expected
    monkeypatch.setattr(
        sys, "argv", [str(script), "--count", "20", "--seed", "42", "--rank", "--text-report"]
    )
    assert module.main() == 0
    assert capsys.readouterr().out == "\n".join(expected["reportLines"]) + "\n"


def test_cli_generation_only_and_config_errors_do_not_start_renders(monkeypatch, capsys):
    script, module = load_cli()
    monkeypatch.setattr(sys, "argv", [str(script), "--seed", "42", "--count", "10"])
    assert module.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["rankingResult"] is None and result["generationSummary"]["notEvaluatedCount"] == 10
    monkeypatch.setattr(sys, "argv", [str(script), "--count", "101"])
    assert module.main() == 2
    captured = capsys.readouterr()
    assert not captured.out and "Generation input error" in captured.err


def test_cli_supports_canonical_snapshot_and_exclusion_flags(tmp_path, monkeypatch, capsys):
    script, module = load_cli()
    registry = tmp_path / "cast.json"
    registry.write_text(json.dumps([{"id": "configured-a", "name": "Kiko"}]))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script),
            "--count",
            "10",
            "--cast-file",
            str(registry),
            "--character-id",
            "configured-a",
            "--exclude-engine-family",
            "progressive_growth",
            "--exclude-object-category",
            "grooming_tool",
            "--rank",
        ],
    )
    assert module.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert all(row["candidate"]["protagonistCharacterId"] == "configured-a" for row in result["candidates"])
    assert "progressive_growth" not in result["engineDistribution"]
