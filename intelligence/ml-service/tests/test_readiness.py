"""Dependency-aware readiness probe (Slice A Task 4)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import Settings


def test_readiness_down_when_ruleset_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Point the service at an empty data root with no rules/versions.yaml.
    monkeypatch.setattr(main, "settings", Settings(data_root=tmp_path))
    client = TestClient(main.app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "DOWN"


def test_readiness_probe_creates_no_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "settings", Settings(data_root=tmp_path))
    client = TestClient(main.app)

    client.get("/health/ready")

    # Fail-closed read must not provision the missing rules directory.
    assert not (tmp_path / "rules").exists()
    assert list(tmp_path.iterdir()) == []


def test_readiness_up_with_real_ruleset() -> None:
    # Default data root points at the shared data/ dir which has rules/versions.yaml.
    client = TestClient(main.app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"
