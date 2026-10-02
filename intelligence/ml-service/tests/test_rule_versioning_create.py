"""Test for the create_new_version() list/dict handling fix.

RULESET YAML's top-level `rules` key is a list of dicts keyed by "id", not a
dict keyed by rule_id. create_new_version() must append/update/remove entries
in that list correctly.
"""

import shutil
from pathlib import Path

import pytest
import yaml

from app.rules.rule_versioning import RuleChange, RuleVersionManager


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    """Copy only RULESET_1.0.yaml (and its versions.yaml entry) into a tmp
    path so this test never mutates the real files on disk, and stays
    isolated from whatever later versions (e.g. RULESET_1.1.yaml) may exist
    in the real data/rules directory. Copying the whole real directory would
    make create_new_version("1.1", ...) collide with an already-existing
    1.1 release once one exists on disk."""
    from app.config import settings

    dest = tmp_path / "rules"
    dest.mkdir(parents=True)
    shutil.copy2(settings.rules_dir / "RULESET_1.0.yaml", dest / "RULESET_1.0.yaml")

    with open(settings.rules_dir / "versions.yaml", encoding="utf-8") as f:
        versions_data = yaml.safe_load(f)
    versions_data["versions"] = [v for v in versions_data["versions"] if v["version"] == "1.0"]
    with open(dest / "versions.yaml", "w", encoding="utf-8") as f:
        yaml.dump(versions_data, f, default_flow_style=False, allow_unicode=True)

    return dest


def test_create_new_version_adds_new_rule_as_list_entry(rules_dir: Path) -> None:
    manager = RuleVersionManager(rules_dir)

    new_rule_change = RuleChange(
        rule_id="TEST_NEW_001",
        change_type="added",
        old_value=None,
        new_value={
            "id": "TEST_NEW_001",
            "name": "Test New Rule",
            "family": "concept_strength",
            "severity": "WARNING",
            "version": "1.1",
        },
        reason="Testing the fix",
        breaking_change=False,
    )

    new_path = manager.create_new_version(
        new_version="1.1",
        description="Test version",
        changes=[new_rule_change],
        learned_from=[],
        is_breaking=False,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    assert isinstance(new_ruleset["rules"], list)
    rule_ids = [r["id"] for r in new_ruleset["rules"]]
    assert "TEST_NEW_001" in rule_ids
    # All 10 original rules from RULESET_1.0.yaml must still be present.
    assert "CONCEPT_006" in rule_ids
    assert len(rule_ids) == len(set(rule_ids)), "no duplicate rule ids"


def test_create_new_version_removed_rule_removes_list_entry(rules_dir: Path) -> None:
    manager = RuleVersionManager(rules_dir)

    remove_change = RuleChange(
        rule_id="CONSISTENCY_001",
        change_type="removed",
        old_value=None,
        new_value=None,
        reason="Testing removal",
        breaking_change=True,
    )

    new_path = manager.create_new_version(
        new_version="1.1",
        description="Test removal",
        changes=[remove_change],
        learned_from=[],
        is_breaking=True,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    rule_ids = [r["id"] for r in new_ruleset["rules"]]
    assert "CONSISTENCY_001" not in rule_ids


def test_create_new_version_added_with_existing_rule_id_overwrites_entry(rules_dir: Path) -> None:
    """An "added" change whose rule_id already exists must replace the
    existing list entry in place (full replacement), not append a duplicate."""
    manager = RuleVersionManager(rules_dir)

    overwrite_change = RuleChange(
        rule_id="CONCEPT_006",
        change_type="added",
        old_value=None,
        new_value={
            "id": "CONCEPT_006",
            "name": "Replaced Consequence Capacity",
            "family": "concept_strength",
            "severity": "WARNING",
            "version": "1.2",
        },
        reason="Testing overwrite-on-add for an existing rule_id",
        breaking_change=False,
    )

    new_path = manager.create_new_version(
        new_version="1.2",
        description="Test overwrite on add",
        changes=[overwrite_change],
        learned_from=[],
        is_breaking=False,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    rule_ids = [r["id"] for r in new_ruleset["rules"]]
    assert rule_ids.count("CONCEPT_006") == 1, "no duplicate entry for the existing rule_id"
    concept_006 = next(r for r in new_ruleset["rules"] if r["id"] == "CONCEPT_006")
    assert concept_006 == overwrite_change.new_value, "existing entry fully replaced, not merged"


def test_create_new_version_removed_nonexistent_rule_id_is_noop(rules_dir: Path) -> None:
    """A "removed" change for a rule_id absent from the source ruleset must
    not raise and must leave the rule list unchanged."""
    manager = RuleVersionManager(rules_dir)

    original_rules = yaml.safe_load((rules_dir / "RULESET_1.0.yaml").read_text(encoding="utf-8"))
    original_ids = {r["id"] for r in original_rules["rules"]}

    remove_change = RuleChange(
        rule_id="DOES_NOT_EXIST_001",
        change_type="removed",
        old_value=None,
        new_value=None,
        reason="Testing no-op removal for a missing rule_id",
        breaking_change=False,
    )

    new_path = manager.create_new_version(
        new_version="1.3",
        description="Test no-op removal",
        changes=[remove_change],
        learned_from=[],
        is_breaking=False,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    new_ids = {r["id"] for r in new_ruleset["rules"]}
    assert new_ids == original_ids, "rule list must be unchanged when removing a missing rule_id"


def test_create_new_version_modified_nonexistent_rule_id_is_noop(rules_dir: Path) -> None:
    """A "modified" change for a rule_id absent from the source ruleset must
    not raise and must leave the rule list unchanged."""
    manager = RuleVersionManager(rules_dir)

    original_rules = yaml.safe_load((rules_dir / "RULESET_1.0.yaml").read_text(encoding="utf-8"))
    original_ids = {r["id"] for r in original_rules["rules"]}

    modify_change = RuleChange(
        rule_id="DOES_NOT_EXIST_002",
        change_type="modified",
        old_value={"severity": "BLOCKER"},
        new_value={"severity": "WARNING"},
        reason="Testing no-op modification for a missing rule_id",
        breaking_change=False,
    )

    new_path = manager.create_new_version(
        new_version="1.4",
        description="Test no-op modification",
        changes=[modify_change],
        learned_from=[],
        is_breaking=False,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    new_ids = {r["id"] for r in new_ruleset["rules"]}
    assert new_ids == original_ids, "rule list must be unchanged when modifying a missing rule_id"


def test_create_new_version_is_loadable_by_rule_engine(rules_dir: Path) -> None:
    """The generated ruleset file must be a valid RuleEngine ruleset, not just valid YAML."""
    manager = RuleVersionManager(rules_dir)

    new_rule_change = RuleChange(
        rule_id="CONCEPT_006",
        change_type="modified",
        old_value={"severity": "BLOCKER"},
        new_value={"severity": "WARNING"},
        reason="Testing modification",
        breaking_change=False,
    )

    manager.create_new_version(
        new_version="1.1",
        description="Test modification",
        changes=[new_rule_change],
        learned_from=[],
        is_breaking=False,
    )

    engine = manager.load_version("1.1")
    rule_ids = {rule["id"] for rule in engine.ruleset["rules"]}
    assert "CONCEPT_006" in rule_ids
    modified_rule = next(r for r in engine.ruleset["rules"] if r["id"] == "CONCEPT_006")
    assert modified_rule["severity"] == "WARNING"


def test_create_new_version_recomputes_ruleset_summary_total(rules_dir: Path) -> None:
    """The generated version's ruleset_summary.total_rules must match the
    actual number of entries in its rules list, not a stale copy from the
    source ruleset."""
    manager = RuleVersionManager(rules_dir)
    with open(rules_dir / "RULESET_1.0.yaml", encoding="utf-8") as f:
        original_rule_count = len(yaml.safe_load(f)["rules"])

    new_rule_change = RuleChange(
        rule_id="TEST_NEW_001",
        change_type="added",
        old_value=None,
        new_value={
            "id": "TEST_NEW_001",
            "name": "Test New Rule",
            "family": "concept_strength",
            "severity": "WARNING",
            "version": "1.1",
        },
        reason="Testing summary recomputation",
        breaking_change=False,
    )

    new_path = manager.create_new_version(
        new_version="1.1",
        description="Test summary recomputation",
        changes=[new_rule_change],
        learned_from=[],
        is_breaking=False,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    assert len(new_ruleset["rules"]) == original_rule_count + 1
    assert new_ruleset["ruleset_summary"]["total_rules"] == original_rule_count + 1


def test_create_new_version_recomputes_severity_counts(rules_dir: Path) -> None:
    """blockers/criticals/warnings in ruleset_summary must match the actual
    severity distribution of the generated rules list, not a stale copy."""
    manager = RuleVersionManager(rules_dir)

    new_rule_change = RuleChange(
        rule_id="TEST_NEW_BLOCKER",
        change_type="added",
        old_value=None,
        new_value={
            "id": "TEST_NEW_BLOCKER",
            "name": "Test New Blocker Rule",
            "family": "concept_strength",
            "severity": "BLOCKER",
            "version": "1.1",
        },
        reason="Testing severity count recomputation",
        breaking_change=False,
    )

    new_path = manager.create_new_version(
        new_version="1.1",
        description="Test severity recomputation",
        changes=[new_rule_change],
        learned_from=[],
        is_breaking=False,
    )

    with open(new_path, encoding="utf-8") as f:
        new_ruleset = yaml.safe_load(f)

    rules = new_ruleset["rules"]
    expected_blockers = sum(1 for r in rules if r.get("severity") == "BLOCKER")
    expected_criticals = sum(1 for r in rules if r.get("severity") == "CRITICAL")
    expected_warnings = sum(1 for r in rules if r.get("severity") == "WARNING")

    summary = new_ruleset["ruleset_summary"]
    assert summary["blockers"] == expected_blockers
    assert summary["criticals"] == expected_criticals
    assert summary["warnings"] == expected_warnings
