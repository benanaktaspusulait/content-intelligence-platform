from __future__ import annotations

from pathlib import Path

from app.golden.architecture import assert_engine_input_is_clean, find_forbidden_imports


APP = Path(__file__).resolve().parents[1] / "app"


def test_pre_render_quality_modules_do_not_import_performance_modules() -> None:
    violations = find_forbidden_imports(
        [APP / "parser", APP / "quality", APP / "rules", APP / "assessment", APP / "scoring", APP / "golden"]
    )
    assert violations == []


def test_golden_engine_input_excludes_roles_and_performance_fields() -> None:
    assert_engine_input_is_clean({"prompt": "source prompt text"})
    for bad in (
        {"prompt": "text", "corpusRole": "WINNER"},
        {"prompt": "text", "views": 10},
        {"prompt": "text", "performance": {"reach": 10}},
    ):
        try:
            assert_engine_input_is_clean(bad)
        except AssertionError:
            continue
        raise AssertionError(f"forbidden Golden engine input accepted: {bad}")
