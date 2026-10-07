from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import yaml


MANIFEST = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "manifest.yaml"
PINNED_HASHES = MANIFEST.with_name("approved_hashes.yaml")


def test_manifest_has_exact_approved_corpus_without_role_in_prompt_bytes() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assets = manifest["assets"]
    expected_ids = {
        "sticky-ball-01",
        "ball-crocodile-01",
        "upside-chair-01",
        "lamp-01",
        "snack-box-01",
        "box-cat-01",
        "spot-cat-01",
        "sneaky-door-01",
        "island-journal-01",
    }
    assert manifest["goldenSetVersion"] == "POMPOM_GOLDEN_V1"
    assert {item["goldenId"] for item in assets} == expected_ids
    pinned = yaml.safe_load(PINNED_HASHES.read_text(encoding="utf-8"))["approvedPromptHashes"]
    assert {item["goldenId"]: item["promptHash"] for item in assets} == pinned
    assert len(assets) == 9
    assert Counter(item["corpusRole"] for item in assets) == {
        "WINNER": 3,
        "MIDDLE": 3,
        "NEGATIVE": 3,
    }
    for item in assets:
        prompt = MANIFEST.parent / item["promptFile"]
        data = prompt.read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["promptHash"]
        text = prompt.read_text(encoding="utf-8")
        assert "corpusRole:" not in text
        assert "corpus_role:" not in text


def test_manifest_marks_source_lineage_and_known_parser_issues_explicitly() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    by_id = {item["goldenId"]: item for item in manifest["assets"]}
    assert all(item["sourceType"].startswith("REAL_PRODUCTION_PROMPT") for item in by_id.values())
    assert all(item["sourceLineageConfidence"] in {"HIGH", "MEDIUM", "LOW"} for item in by_id.values())
    assert "TIMELINE_PARSE_INCOMPATIBLE" in by_id["box-cat-01"]["knownIssues"]
    assert "TIMELINE_PARSE_INCOMPATIBLE" in by_id["spot-cat-01"]["knownIssues"]
