"""Rule versioning contract (Slice A Task 7).

``RuleVersionManager.compare_versions`` must read actual rule ids from the
engine's loaded ruleset (``RuleEngine.ruleset["rules"]``, a list of rule
dicts keyed by ``"id"``) rather than a nonexistent ``RuleEngine.rules`` dict
attribute. This pins the corrected behavior so the comparison can run end to
end instead of raising ``AttributeError``.
"""

from pathlib import Path

import pytest
import yaml

from app.rules.rule_versioning import RuleVersionManager

RULESET_V1 = {
    "version": "1.0",
    "created": "2026-09-09",
    "description": "v1",
    "rules": [
        {
            "id": "CONCEPT_006",
            "name": "Consequence Capacity",
            "family": "concept_strength",
            "severity": "BLOCKER",
            "version": "1.0",
        },
        {
            "id": "BEAT_004",
            "name": "Static State Dominance",
            "family": "visual_novelty",
            "severity": "CRITICAL",
            "version": "1.0",
        },
    ],
}

RULESET_V2 = {
    "version": "1.1",
    "created": "2026-09-20",
    "description": "v2",
    "rules": [
        {
            "id": "CONCEPT_006",
            "name": "Consequence Capacity",
            "family": "concept_strength",
            "severity": "WARNING",
            "version": "1.1",
        },
        {
            "id": "NOVELTY_001",
            "name": "Novelty Timeline Distribution",
            "family": "visual_novelty",
            "severity": "WARNING",
            "version": "1.1",
        },
    ],
}

VERSIONS_METADATA = {
    "versions": [
        {
            "version": "1.0",
            "release_date": "2026-09-09",
            "description": "Initial ruleset",
            "ruleset_path": "RULESET_1.0.yaml",
            "learned_from": [],
            "deprecated_rules": [],
            "is_breaking": False,
            "changelog": "",
            "changes": [],
        },
        {
            "version": "1.1",
            "release_date": "2026-09-20",
            "description": "Second ruleset",
            "ruleset_path": "RULESET_1.1.yaml",
            "learned_from": [],
            "deprecated_rules": [],
            "is_breaking": False,
            "changelog": "",
            "changes": [],
        },
    ]
}


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    (tmp_path / "RULESET_1.0.yaml").write_text(yaml.dump(RULESET_V1), encoding="utf-8")
    (tmp_path / "RULESET_1.1.yaml").write_text(yaml.dump(RULESET_V2), encoding="utf-8")
    (tmp_path / "versions.yaml").write_text(yaml.dump(VERSIONS_METADATA), encoding="utf-8")
    return tmp_path


def test_compare_versions_detects_new_and_removed_rules(rules_dir: Path) -> None:
    manager = RuleVersionManager(rules_dir)
    report = manager.compare_versions("1.0", "1.1")

    assert report.new_rules == ["NOVELTY_001"]
    assert report.removed_rules == ["BEAT_004"]


def test_compare_versions_detects_modified_severity(rules_dir: Path) -> None:
    manager = RuleVersionManager(rules_dir)
    report = manager.compare_versions("1.0", "1.1")

    # CONCEPT_006 kept its id but changed severity BLOCKER -> WARNING.
    assert report.modified_rules == ["CONCEPT_006"]


def test_compare_versions_migration_notes_mention_both_versions(rules_dir: Path) -> None:
    manager = RuleVersionManager(rules_dir)
    report = manager.compare_versions("1.0", "1.1")

    assert "1.0" in report.migration_notes
    assert "1.1" in report.migration_notes
