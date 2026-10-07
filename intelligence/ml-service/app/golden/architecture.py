from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable


_FORBIDDEN_MODULE_ROOTS = (
    "app.performance",
    "app.prediction",
    "app.retention",
    "lab",
)
_FORBIDDEN_KEYS = {
    "corpusrole",
    "views",
    "reach",
    "likes",
    "shares",
    "watchtime",
    "watch_time",
    "completion",
    "followersgained",
    "performance",
    "performanceobservation",
    "prediction",
}


def _module_name(node: ast.AST) -> str:
    if isinstance(node, ast.Import):
        return ",".join(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return ""


def find_forbidden_imports(paths: Iterable[Path]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for root in paths:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                module = _module_name(node)
                if any(module == root_name or module.startswith(root_name + ".") for root_name in _FORBIDDEN_MODULE_ROOTS):
                    violations.append({"path": str(path), "line": node.lineno, "module": module})
    return violations


def assert_engine_input_is_clean(value: Any) -> None:
    def walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = "".join(character for character in str(key).lower() if character.isalnum() or character == "_")
                assert normalized not in _FORBIDDEN_KEYS, f"forbidden Golden engine input key at {path}.{key}"
                walk(child, f"{path}.{key}")
        elif isinstance(item, (list, tuple)):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")
        elif isinstance(item, str):
            lowered = item.lower()
            assert "corpusrole:" not in lowered
            assert "winner_corpus" not in lowered
            assert "middle_corpus" not in lowered
            assert "negative_corpus" not in lowered

    walk(value, "input")
