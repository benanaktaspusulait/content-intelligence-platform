"""One-off script that generates data/rules/RULESET_1.1.yaml from
data/rules/RULESET_1.0.yaml via RuleVersionManager.create_new_version().

Run once: `cd ml-service && POMPOM_DATA_ROOT=$(pwd)/../data python scripts/generate_ruleset_1_1.py`

Safe to re-run only after deleting the previously generated RULESET_1.1.yaml
and removing its entry from versions.yaml — create_new_version() refuses to
overwrite an existing version (raises ValueError: Version 1.1 already exists).
"""

from app.config import settings
from app.rules.rule_versioning import RuleChange, RuleVersionManager

NEW_RULES: list[dict[str, object]] = [
    {
        "id": "HOOK_002",
        "name": "First Frame Anomaly",
        "family": "hook_strength",
        "severity": "CRITICAL",
        "version": "1.1",
        "description": (
            "The problem must already be visually obvious within the opening second, "
            "with no setup, narration, or text explanation required. hook.startsMidAction "
            "must be true and hook.visualStrength must be at least 4/5."
        ),
    },
    {
        "id": "HOOK_003",
        "name": "Sound Independence",
        "family": "hook_strength",
        "severity": "CRITICAL",
        "version": "1.1",
        "description": (
            "The core problem and physical comedy must work with audio muted. "
            "hook.soundOffClear must be true."
        ),
    },
    {
        "id": "MOTION_001",
        "name": "No Dead Air",
        "family": "motion_quality",
        "severity": "WARNING",
        "version": "1.1",
        "description": "No beat may hold with motionAmount == 'none' for longer than 1.5 seconds.",
    },
    {
        "id": "ATTEMPT_001",
        "name": "Attempt Count",
        "family": "concept_strength",
        "severity": "BLOCKER",
        "version": "1.1",
        "description": (
            "Count of beats with isAttempt == true must meet a duration-tier minimum: "
            "3 for videos <= 20s (short tier), 7 for videos > 20s (long tier)."
        ),
    },
    {
        "id": "CHAR_002",
        "name": "Active Character",
        "family": "progression",
        "severity": "CRITICAL",
        "version": "1.1",
        "description": (
            "The character must spend most of the runtime actively trying a solution, "
            "not watching or reacting. Ratio of (duration of isAttempt beats) / "
            "(total duration) must be at least 0.5 for short-tier videos, 0.6 for long-tier."
        ),
    },
    {
        "id": "PRODUCIBILITY_002",
        "name": "Prop Economy",
        "family": "ai_producibility",
        "severity": "WARNING",
        "version": "1.1",
        "description": (
            "Introduce the minimum number of props necessary. setting.mainProps count "
            "must not exceed 2 for short-tier videos, 4 for long-tier videos."
        ),
    },
    {
        "id": "PAYOFF_002",
        "name": "Fake Resolution Present",
        "family": "progression",
        "severity": "WARNING",
        "version": "1.1",
        "description": (
            "Bonus (non-blocking): at least one beat with consequenceType == 'fake_win' "
            "before finalPayoff.startsAt, giving the audience a moment to believe the "
            "problem is solved before the final twist."
        ),
    },
    {
        "id": "ATTEMPT_002",
        "name": "Distinct Attempts",
        "family": "visual_novelty",
        "severity": "CRITICAL",
        "version": "1.1",
        "description": (
            "Attempts must be mechanically distinct, not just differently worded. "
            "Identical primaryVerb across attempts is an automatic deterministic FAIL. "
            "Verb-distinct attempts are checked for semantic duplication via LLM "
            "(e.g. GRAB vs YANK may be the same underlying strategy). Effective "
            "distinct count must meet the same duration-tier minimum as ATTEMPT_001."
        ),
    },
    {
        "id": "PAYOFF_003",
        "name": "Rule-Consistent Twist",
        "family": "final_payoff",
        "severity": "CRITICAL",
        "version": "1.1",
        "description": (
            "The final twist must derive from the same established physical rule "
            "(coreMechanic.physicalRule), applied in a new or bigger way — not an "
            "unrelated, disconnected joke. Checked via LLM semantic judgment."
        ),
    },
    {
        "id": "CONSISTENCY_002",
        "name": "Character Continuity Lock",
        "family": "consistency",
        "severity": "CRITICAL",
        "version": "1.1",
        "description": (
            "Character appearance (face, outfit, colors, proportions) must remain "
            "identical throughout the video, judged by sampling first/middle/last "
            "frames via vision LLM. This rule requires a rendered video "
            "(video_plan_ir['_renderedVideoPath']) and reports UNKNOWN at the "
            "pure-text concept stage, before any video exists."
        ),
    },
]


def main() -> None:
    manager = RuleVersionManager(settings.rules_dir)

    changes = [
        RuleChange(
            rule_id=str(rule["id"]),
            change_type="added",
            old_value=None,
            new_value=rule,
            reason=f"RULESET 1.1: {rule['name']} ({rule['family']} family)",
            breaking_change=False,
        )
        for rule in NEW_RULES
    ]

    new_path = manager.create_new_version(
        new_version="1.1",
        description=(
            "Adds 10 rules covering first-frame anomaly, sound independence, dead-air "
            "detection, active-character ratio, tiered attempt counting, mechanically "
            "distinct attempts, prop economy, fake resolution, rule-consistent twists, "
            "and character continuity lock. Supports both short-tier (<=20s) and "
            "long-tier (>20s) videos via duration-derived thresholds."
        ),
        changes=changes,
        learned_from=[],
        is_breaking=False,
    )
    print(f"Generated: {new_path}")


if __name__ == "__main__":
    main()
