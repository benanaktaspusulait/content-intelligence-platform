"""
Pompom Creative Quality Engine - Rule Versioning System
Tracks ruleset evolution, maintains backward compatibility, and manages rule changes over time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from app.rules.rule_engine import RuleEngine


class RulesetConfigurationError(RuntimeError):
    """Raised when the configured ruleset directory or metadata is missing.

    Reading ruleset metadata is a side-effect-free operation: when the
    configured directory or ``versions.yaml`` is absent, the manager raises
    this error instead of provisioning files on disk.
    """


@dataclass
class RuleChange:
    """Single rule change in a version"""

    rule_id: str
    change_type: str  # "added", "modified", "removed", "deprecated"
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    reason: str = ""
    breaking_change: bool = False


@dataclass
class RulesetVersion:
    """Complete ruleset version with metadata"""

    version: str  # "1.0", "1.1", "2.0"
    release_date: str
    description: str
    ruleset_path: str
    changes: list[RuleChange] = field(default_factory=list)
    learned_from: list[str] = field(default_factory=list)  # FAIL_001, FAIL_002, etc.
    deprecated_rules: set[str] = field(default_factory=set)
    is_breaking: bool = False
    changelog: str = ""


@dataclass
class VersionComparisonReport:
    """Comparison between two ruleset versions"""

    version_from: str
    version_to: str
    is_backward_compatible: bool
    breaking_changes: list[RuleChange]
    new_rules: list[str]
    removed_rules: list[str]
    modified_rules: list[str]
    migration_notes: str


class RuleVersionManager:
    """
    Manages multiple ruleset versions and provides version comparison/migration.

    Directory structure:
        data/rules/
            RULESET_1.0.yaml
            RULESET_1.1.yaml
            RULESET_2.0.yaml
            versions.yaml       # Version metadata and changelog

    Usage:
        manager = RuleVersionManager("data/rules")

        # Load specific version
        engine = manager.load_version("1.0")

        # Get latest version
        engine = manager.load_latest()

        # Compare versions
        comparison = manager.compare_versions("1.0", "1.1")
        if not comparison.is_backward_compatible:
            print(comparison.migration_notes)
    """

    def __init__(self, rules_dir: str | Path = "data/rules"):
        self.rules_dir = Path(rules_dir)
        self.versions_file = self.rules_dir / "versions.yaml"
        self.versions: dict[str, RulesetVersion] = {}
        self._load_version_metadata()

    def _load_version_metadata(self) -> None:
        """Load version metadata from versions.yaml.

        This is a read-only operation. If the configured directory or the
        ``versions.yaml`` metadata file is absent, raise a typed configuration
        error rather than creating files on disk.
        """
        if not self.rules_dir.exists():
            raise RulesetConfigurationError(f"Ruleset directory not found: {self.rules_dir}")
        if not self.versions_file.exists():
            raise RulesetConfigurationError(f"Ruleset metadata not found: {self.versions_file}")

        with open(self.versions_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for version_data in data.get("versions", []):
            changes = [RuleChange(**change) for change in version_data.get("changes", [])]

            version = RulesetVersion(
                version=version_data["version"],
                release_date=version_data["release_date"],
                description=version_data["description"],
                ruleset_path=version_data["ruleset_path"],
                changes=changes,
                learned_from=version_data.get("learned_from", []),
                deprecated_rules=set(version_data.get("deprecated_rules", [])),
                is_breaking=version_data.get("is_breaking", False),
                changelog=version_data.get("changelog", ""),
            )

            self.versions[version.version] = version

    def load_version(self, version: str) -> "RuleEngine":
        """
        Load RuleEngine with specific ruleset version.

        Args:
            version: Version string like "1.0", "1.1"

        Returns:
            RuleEngine instance
        """
        if version not in self.versions:
            available = ", ".join(self.versions.keys())
            raise ValueError(f"Version {version} not found. Available: {available}")

        version_info = self.versions[version]
        ruleset_path = self.rules_dir / version_info.ruleset_path

        if not ruleset_path.exists():
            raise FileNotFoundError(f"Ruleset file not found: {ruleset_path}")

        # Import here to avoid circular dependency
        from .rule_engine import RuleEngine

        return RuleEngine(str(ruleset_path))

    def load_latest(self) -> "RuleEngine":
        """Load RuleEngine with latest ruleset version"""
        latest_version = self.get_latest_version()
        return self.load_version(latest_version)

    def get_latest_version(self) -> str:
        """Get latest version string"""
        if not self.versions:
            raise ValueError("No versions available")

        # Sort by semantic version
        versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")], reverse=True)
        return versions[0]

    def get_version_info(self, version: str) -> RulesetVersion:
        """Get metadata for specific version"""
        if version not in self.versions:
            raise ValueError(f"Version {version} not found")
        return self.versions[version]

    def list_versions(self) -> list[RulesetVersion]:
        """Get all versions sorted by release date"""
        return sorted(self.versions.values(), key=lambda v: v.release_date, reverse=True)

    def compare_versions(self, version_from: str, version_to: str) -> VersionComparisonReport:
        """
        Compare two ruleset versions and generate migration report.

        Args:
            version_from: Starting version
            version_to: Target version

        Returns:
            VersionComparisonReport with breaking changes and migration notes
        """
        if version_from not in self.versions:
            raise ValueError(f"Version {version_from} not found")
        if version_to not in self.versions:
            raise ValueError(f"Version {version_to} not found")

        v_to = self.versions[version_to]

        # Load both rulesets to compare
        engine_from = self.load_version(version_from)
        engine_to = self.load_version(version_to)

        rules_from_by_id = {rule["id"]: rule for rule in engine_from.ruleset.get("rules", [])}
        rules_to_by_id = {rule["id"]: rule for rule in engine_to.ruleset.get("rules", [])}

        rules_from = set(rules_from_by_id.keys())
        rules_to = set(rules_to_by_id.keys())

        new_rules = list(rules_to - rules_from)
        removed_rules = list(rules_from - rules_to)
        common_rules = rules_from & rules_to

        # Check for modified rules
        modified_rules = []
        for rule_id in common_rules:
            rule_from = rules_from_by_id[rule_id]
            rule_to = rules_to_by_id[rule_id]

            # Compare thresholds and severity
            if rule_from.get("threshold") != rule_to.get("threshold") or rule_from.get(
                "severity"
            ) != rule_to.get("severity"):
                modified_rules.append(rule_id)

        # Extract breaking changes from version_to
        breaking_changes = [change for change in v_to.changes if change.breaking_change]

        is_backward_compatible = not breaking_changes and not removed_rules and not v_to.is_breaking

        # Generate migration notes
        migration_notes = self._generate_migration_notes(
            version_from, version_to, new_rules, removed_rules, modified_rules, breaking_changes
        )

        return VersionComparisonReport(
            version_from=version_from,
            version_to=version_to,
            is_backward_compatible=is_backward_compatible,
            breaking_changes=breaking_changes,
            new_rules=new_rules,
            removed_rules=removed_rules,
            modified_rules=modified_rules,
            migration_notes=migration_notes,
        )

    def _generate_migration_notes(
        self,
        version_from: str,
        version_to: str,
        new_rules: list[str],
        removed_rules: list[str],
        modified_rules: list[str],
        breaking_changes: list[RuleChange],
    ) -> str:
        """Generate human-readable migration notes"""
        lines = [f"# Migration Guide: {version_from} → {version_to}", ""]

        if breaking_changes:
            lines.append("## ⚠️  BREAKING CHANGES")
            for change in breaking_changes:
                lines.append(f"- **{change.rule_id}**: {change.reason}")
            lines.append("")

        if new_rules:
            lines.append(f"## ➕ New Rules ({len(new_rules)})")
            for rule_id in new_rules:
                lines.append(f"- {rule_id}")
            lines.append("")

        if removed_rules:
            lines.append(f"## ➖ Removed Rules ({len(removed_rules)})")
            for rule_id in removed_rules:
                lines.append(f"- {rule_id}")
            lines.append("")

        if modified_rules:
            lines.append(f"## 🔧 Modified Rules ({len(modified_rules)})")
            for rule_id in modified_rules:
                lines.append(f"- {rule_id} (threshold or severity changed)")
            lines.append("")

        lines.append("## Action Required")
        if breaking_changes or removed_rules:
            lines.append("- Re-validate all existing prompts with new ruleset")
            lines.append("- Update any hardcoded rule references in application code")
            lines.append("- Review deprecated rules and plan removal")
        else:
            lines.append("- No breaking changes, safe to upgrade")
            lines.append("- New rules will automatically apply to new validations")

        return "\n".join(lines)

    def create_new_version(
        self,
        new_version: str,
        description: str,
        changes: list[RuleChange],
        learned_from: list[str] | None = None,
        is_breaking: bool = False,
    ) -> str:
        """
        Create a new ruleset version (for future use).

        Args:
            new_version: Version string like "1.1", "2.0"
            description: Human-readable description
            changes: List of RuleChange objects
            learned_from: List of case IDs (e.g., ["FAIL_004"])
            is_breaking: Whether this is a breaking change

        Returns:
            Path to new ruleset file
        """
        if new_version in self.versions:
            raise ValueError(f"Version {new_version} already exists")

        # Copy latest ruleset as starting point
        latest_version = self.get_latest_version()
        latest_ruleset = self.rules_dir / self.versions[latest_version].ruleset_path
        new_ruleset_path = self.rules_dir / f"RULESET_{new_version}.yaml"

        # Load and modify ruleset based on changes
        with open(latest_ruleset, encoding="utf-8") as f:
            ruleset_data = yaml.safe_load(f)

        # Ruleset YAML's "rules" key is a list of rule dicts keyed by "id",
        # not a dict keyed by rule_id — index into it by position, not by
        # subscripting with the rule_id string.
        rules_list: list[dict[str, Any]] = ruleset_data.setdefault("rules", [])
        rules_by_id = {rule["id"]: idx for idx, rule in enumerate(rules_list)}

        for change in changes:
            if change.change_type == "added" and change.new_value:
                if change.rule_id in rules_by_id:
                    rules_list[rules_by_id[change.rule_id]] = change.new_value
                else:
                    rules_list.append(change.new_value)
                    rules_by_id[change.rule_id] = len(rules_list) - 1
            elif change.change_type == "removed":
                if change.rule_id in rules_by_id:
                    idx = rules_by_id.pop(change.rule_id)
                    rules_list.pop(idx)
                    # Shift indices of entries after the removed one.
                    rules_by_id = {rid: (i if i < idx else i - 1) for rid, i in rules_by_id.items()}
            elif change.change_type == "modified" and change.new_value:
                if change.rule_id in rules_by_id:
                    rules_list[rules_by_id[change.rule_id]].update(change.new_value)

        # Update version in ruleset
        ruleset_data["version"] = new_version

        # Recompute ruleset_summary from the actual final rules list rather
        # than carrying over the source ruleset's (potentially stale) copy —
        # a generated artifact's own summary must reflect what it actually
        # contains.
        severity_counts = {"BLOCKER": 0, "CRITICAL": 0, "WARNING": 0}
        for rule in rules_list:
            severity = rule.get("severity")
            if severity in severity_counts:
                severity_counts[severity] += 1

        existing_summary = ruleset_data.get("ruleset_summary", {})
        ruleset_data["ruleset_summary"] = {
            **existing_summary,
            "total_rules": len(rules_list),
            "blockers": severity_counts["BLOCKER"],
            "criticals": severity_counts["CRITICAL"],
            "warnings": severity_counts["WARNING"],
        }

        # Save new ruleset
        with open(new_ruleset_path, "w", encoding="utf-8") as f:
            yaml.dump(ruleset_data, f, default_flow_style=False, allow_unicode=True)

        # Generate changelog
        changelog = self._generate_changelog(new_version, description, changes)

        # Add to versions.yaml
        new_version_data = {
            "version": new_version,
            "release_date": datetime.now().strftime("%Y-%m-%d"),
            "description": description,
            "ruleset_path": f"RULESET_{new_version}.yaml",
            "learned_from": learned_from or [],
            "is_breaking": is_breaking,
            "changelog": changelog,
            "changes": [
                {
                    "rule_id": c.rule_id,
                    "change_type": c.change_type,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "reason": c.reason,
                    "breaking_change": c.breaking_change,
                }
                for c in changes
            ],
        }

        # Load existing versions.yaml
        with open(self.versions_file, encoding="utf-8") as f:
            versions_data = yaml.safe_load(f)

        versions_data["versions"].append(new_version_data)

        # Save updated versions.yaml
        with open(self.versions_file, "w", encoding="utf-8") as f:
            yaml.dump(versions_data, f, default_flow_style=False, allow_unicode=True)

        # Reload metadata
        self._load_version_metadata()

        return str(new_ruleset_path)

    def _generate_changelog(self, version: str, description: str, changes: list[RuleChange]) -> str:
        """Generate formatted changelog text"""
        lines = [f"# Ruleset {version}", "", description, ""]

        added = [c for c in changes if c.change_type == "added"]
        modified = [c for c in changes if c.change_type == "modified"]
        removed = [c for c in changes if c.change_type == "removed"]

        if added:
            lines.append(f"## New Rules ({len(added)})")
            for change in added:
                lines.append(f"- {change.rule_id}: {change.reason}")
            lines.append("")

        if modified:
            lines.append(f"## Modified Rules ({len(modified)})")
            for change in modified:
                lines.append(f"- {change.rule_id}: {change.reason}")
            lines.append("")

        if removed:
            lines.append(f"## Removed Rules ({len(removed)})")
            for change in removed:
                lines.append(f"- {change.rule_id}: {change.reason}")
            lines.append("")

        return "\n".join(lines)


def format_version_list(versions: list[RulesetVersion]) -> str:
    """Format version list as human-readable text"""
    lines = ["=" * 60, "AVAILABLE RULESET VERSIONS", "=" * 60, ""]

    for version in versions:
        breaking_marker = " ⚠️  BREAKING" if version.is_breaking else ""
        lines.append(f"Version {version.version}{breaking_marker}")
        lines.append(f"Released: {version.release_date}")
        lines.append(f"Description: {version.description}")

        if version.learned_from:
            lines.append(f"Learned from: {', '.join(version.learned_from)}")

        if version.deprecated_rules:
            lines.append(f"Deprecated: {', '.join(version.deprecated_rules)}")

        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
