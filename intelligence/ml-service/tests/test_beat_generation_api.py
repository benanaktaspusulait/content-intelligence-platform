import importlib.util
import json
from pathlib import Path
import sys
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.workflow.beat_generation import generate_and_rank


def test_enabled_api_matches_shared_pipeline():
    payload = {"generatorVersion": "v2", "beatGrammarVersion": "v2"}
    response = TestClient(app).post("/api/v1/workflow/concepts/generate", json=payload)
    assert response.status_code == 200 and response.json() == generate_and_rank(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"generatorVersion": "v1", "beatGrammarVersion": "v2"},
        {"generatorVersion": "v2", "beatGrammarVersion": "v3"},
        {"generatorVersion": "v2", "beatGrammarVersion": "v2", "provider": "openai"},
    ],
)
def test_invalid_feature_configs_are_rejected(payload):
    assert TestClient(app).post("/api/v1/workflow/concepts/generate", json=payload).status_code == 422


def test_cli_records_version_and_supports_human_report(monkeypatch, capsys):
    script = Path(__file__).parents[2] / "scripts/generate-short-concepts.py"
    spec = importlib.util.spec_from_file_location("beat_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = [
        str(script),
        "--generator-version",
        "v2",
        "--beat-grammar-version",
        "v2",
        "--seed",
        "42",
        "--count",
        "20",
        "--rank",
    ]
    monkeypatch.setattr(sys, "argv", args)
    assert module.main() == 0
    r = json.loads(capsys.readouterr().out)
    assert r["beatGrammarVersion"] == "beat-grammar-v2"
    monkeypatch.setattr(sys, "argv", args + ["--text-report"])
    assert module.main() == 0
    assert capsys.readouterr().out == "\n".join(r["reportLines"]) + "\n"
