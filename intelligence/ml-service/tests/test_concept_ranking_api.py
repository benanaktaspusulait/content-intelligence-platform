"""Actual API/CLI boundaries; no providers, model calls, persistence or rendering."""

import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.workflow.concept_ranking import rank_concepts
from test_concept_ranking import CANDIDATES, batch


def test_batch_and_single_api_are_projections_of_the_same_offline_workflow():
    with (
        patch("app.llm.provider.get_provider", side_effect=AssertionError("No providers")),
        patch(
            "app.workflow.review._run_canonical_evaluation",
            side_effect=AssertionError("No canonical regrade"),
        ),
    ):
        client = TestClient(app)
        response = client.post("/api/v1/workflow/concepts/rank", json={"candidates": batch("obvious")})
        assert response.status_code == 200
        assert response.json() == rank_concepts(batch("obvious"))
        single = client.post("/api/v1/workflow/concepts/validate", json=CANDIDATES["lid"])
        assert single.status_code == 200
        assert single.json() == rank_concepts([CANDIDATES["lid"]])
        assert single.json()["providerCalls"] == single.json()["conceptsGenerated"] == 0


def test_api_preserves_exact_output_under_input_permutation():
    client = TestClient(app)
    values = batch("diversity")
    first = client.post("/api/v1/workflow/concepts/rank", json={"candidates": values})
    second = client.post("/api/v1/workflow/concepts/rank", json={"candidates": list(reversed(values))})
    assert first.status_code == second.status_code == 200
    assert first.content == second.content


@pytest.mark.parametrize(
    "payload",
    [
        {"candidates": []},
        {"candidates": [CANDIDATES["lid"]] * 31},
        {"candidates": [CANDIDATES["lid"]] * 2},
        {"candidates": [CANDIDATES["lid"]], "generateConcepts": True},
        {"candidates": [{**CANDIDATES["lid"], "rankingScore": 100}]},
    ],
)
def test_api_rejects_invalid_batch_or_self_awarded_scores(payload):
    assert TestClient(app).post("/api/v1/workflow/concepts/rank", json=payload).status_code == 422


def test_cli_matches_api_and_projects_report_without_a_subprocess(tmp_path, monkeypatch, capsys):
    script = Path(__file__).parents[2] / "scripts/rank-concepts.py"
    spec = importlib.util.spec_from_file_location("rank_concepts_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "supplied.json"
    source.write_text(json.dumps({"candidates": batch("obvious")}))
    monkeypatch.setattr(sys, "argv", [str(script), str(source)])
    assert module.main() == 0
    expected = rank_concepts(batch("obvious"))
    assert json.loads(capsys.readouterr().out) == expected
    monkeypatch.setattr(sys, "argv", [str(script), str(source), "--text-report"])
    assert module.main() == 0
    assert capsys.readouterr().out == "\n".join(expected["reportLines"]) + "\n"


def test_cli_invalid_input_is_nonzero_and_does_not_create_a_ranking(tmp_path, monkeypatch, capsys):
    script = Path(__file__).parents[2] / "scripts/rank-concepts.py"
    spec = importlib.util.spec_from_file_location("rank_concepts_cli_error", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "invalid.json"
    source.write_text('{"candidates": []}')
    monkeypatch.setattr(sys, "argv", [str(script), str(source)])
    assert module.main() == 2
    captured = capsys.readouterr()
    assert not captured.out and "Concept input error" in captured.err
