"""Settings data-root path derivation (Slice A Task 4)."""

from pathlib import Path

import pytest

from app.config import Settings


def test_rules_dir_derives_from_data_root_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("POMPOM_DATA_ROOT", str(tmp_path))
    settings = Settings()
    assert settings.data_root == tmp_path
    assert settings.rules_dir == tmp_path / "rules"


def test_derived_dirs_track_data_root(tmp_path: Path) -> None:
    settings = Settings(data_root=tmp_path)
    assert settings.rules_dir == tmp_path / "rules"
    assert settings.golden_sets_dir == tmp_path / "golden_sets"
    assert settings.artifacts_dir == tmp_path / "model-artifacts"
    assert settings.test_cases_dir == tmp_path / "test_cases"


def test_default_data_root_is_absolute_source_derived(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without an env override the default is a source-derived absolute path.
    monkeypatch.delenv("POMPOM_DATA_ROOT", raising=False)
    settings = Settings()
    assert settings.data_root.is_absolute()
    # ml-service/app -> ml-service -> Pompom_Creative_Intelligence/data
    assert settings.data_root.name == "data"
