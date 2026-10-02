from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json()["status"] == "UP"


def test_cold_start_prediction_is_explicitly_uncertain() -> None:
    response = client.post(
        "/v1/prediction/prepublish",
        json={
            "contractVersion": "v1",
            "platform": "instagram",
            "fingerprint": {},
            "knowledgeCutoff": "2026-09-28T10:00:00Z",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "LOW"
    assert body["comparableSampleSize"] == 0
    assert body["payload"]["targets"][0]["expectedValue"] is None
    assert "reachFurtherUsed" not in body["payload"]


def test_live_prediction_can_use_explicit_cutoff_safe_signal() -> None:
    response = client.post(
        "/v1/prediction/live",
        json={
            "contractVersion": "v1",
            "platform": "facebook",
            "fingerprint": {},
            "knowledgeCutoff": "2026-09-28T10:00:00Z",
            "liveFeatures": {"reachFurtherObserved": True, "timeSinceReachFurtherFirstSeenSeconds": 900},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["payload"]["reachFurtherUsed"] is True
    assert "causal" in body["payload"]["uncertaintyReasons"][-1]


def test_reach_further_model_experiment_refuses_small_sample_conclusions() -> None:
    response = client.post(
        "/v1/evaluation/reach-further-ablation",
        json={"contractVersion": "v1", "platform": "facebook", "rows": []},
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "INSUFFICIENT_SAMPLE"
    assert response.json()["modelA"]["metrics"] is None


def test_video_path_traversal_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import video

    monkeypatch.setattr(video.settings, "data_root", tmp_path)
    response = client.post(
        "/v1/analysis/video", json={"contractVersion": "v1", "relativePath": "../secret.mp4"}
    )
    assert response.status_code == 400
