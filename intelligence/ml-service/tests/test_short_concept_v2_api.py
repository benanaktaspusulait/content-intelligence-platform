import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.workflow.short_concept_generation_v2 import generate_and_rank


def test_v2_api_uses_same_local_pipeline_without_provider():
    with patch("app.llm.provider.get_provider", side_effect=AssertionError("No external providers")):
        response = TestClient(app).post("/api/v1/workflow/concepts/generate", json={"generatorVersion": "v2"})
    assert response.status_code == 200
    assert response.json() == generate_and_rank({"generatorVersion": "v2"})


@pytest.mark.parametrize(
    "payload",
    [
        {"generatorVersion": "v3"},
        {"generatorVersion": "v2", "internalPoolSize": 0},
        {"generatorVersion": "v2", "internalPoolSize": 601},
        {"generatorVersion": "v2", "provider": "openai"},
    ],
)
def test_invalid_config_rejected(payload):
    assert TestClient(app).post("/api/v1/workflow/concepts/generate", json=payload).status_code == 422


def test_v2_api_constraints_and_explicit_alias():
    r = TestClient(app).post(
        "/api/v1/workflow/concepts/generate",
        json={
            "generatorVersion": "short-concept-generator-v2",
            "rank": False,
            "excludeObjectCategories": ["FURNITURE"],
            "canonicalCast": [{"id": "a", "name": "Kiko"}],
        },
    )
    assert r.status_code == 200
    assert "FURNITURE" not in r.json()["objectCategoryDistribution"]
    assert all(c["candidate"]["protagonist"] == "Kiko" for c in r.json()["candidates"])


def test_v2_cli_matches_pipeline_and_human_report(monkeypatch, capsys):
    script = Path(__file__).parents[2] / "scripts/generate-short-concepts.py"
    spec = importlib.util.spec_from_file_location("v2_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        sys, "argv", [str(script), "--generator-version", "v2", "--count", "20", "--seed", "42", "--rank"]
    )
    assert module.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result == generate_and_rank({"generatorVersion": "v2"})
    monkeypatch.setattr(sys, "argv", [str(script), "--generator-version", "v2", "--rank", "--text-report"])
    assert module.main() == 0
    assert capsys.readouterr().out == "\n".join(result["reportLines"]) + "\n"
