"""One-off script that generates data/rules/RULESET_1.2.yaml from
data/rules/RULESET_1.1.yaml via RuleVersionManager.create_new_version().

Run once: `cd ml-service && POMPOM_DATA_ROOT=$(pwd)/../data python scripts/generate_ruleset_1_2.py`

Safe to re-run only after deleting the previously generated RULESET_1.2.yaml
and removing its entry from versions.yaml — create_new_version() refuses to
overwrite an existing version (raises ValueError: Version 1.2 already exists).
"""

from app.config import settings
from app.rules.rule_versioning import RuleChange, RuleVersionManager

NEW_RULES: list[dict[str, object]] = [
    {
        "id": "CONCEPT_007",
        "name": "Single Dominant Mechanic",
        "family": "concept_strength",
        # Top-level severity reflects the evaluator's maximum possible ceiling
        # (BLOCKER at 3+ independent mechanics), not its minimum FAIL severity
        # (CRITICAL at exactly 2) -- the evaluator computes its own per-case
        # severity at runtime; this field is informational/summary-only.
        "severity": "BLOCKER",
        "version": "1.2",
        "description": (
            "The concept must exhibit exactly one independent physical/magical rule. "
            "Same mechanic applied with escalating/varied consequences is fine (PASS); "
            "a second, genuinely independent rule introduced partway through is not "
            "(CRITICAL at 2 mechanics, BLOCKER at 3+). coreMechanic.mechanicCount is an "
            "author claim, verified (not trusted) via LLM semantic judgment against the "
            "beat-by-beat consequences."
        ),
    },
    {
        "id": "BEAT_005",
        "name": "Story Detached Gap",
        "family": "visual_novelty",
        "severity": "CRITICAL",
        "version": "1.2",
        "description": (
            "While the core problem is actively unresolved (at least one attempt beat "
            "has occurred, final payoff not yet started), no consecutive stretch of "
            "beats.relatesToCoreProblem == false may exceed 0.5 seconds. Brief "
            "transitions/reaction beats under that threshold are not flagged; only a "
            "genuine abandonment of the active problem fails."
        ),
    },
    {
        "id": "PAYOFF_004",
        "name": "Final Peak Intensity",
        "family": "final_payoff",
        "severity": "WARNING",
        "version": "1.2",
        "description": (
            "The final payoff's beat.intensity should be at least as high as the "
            "highest intensity seen earlier in the video. Computed independently from "
            "beat.intensity values; finalPayoff.isPeakIntensity is never trusted as the "
            "verdict, only cross-checked for discrepancy reporting. Optimization-level "
            "(WARNING), never a blocker."
        ),
    },
    {
        "id": "PAYOFF_005",
        "name": "Fake Win Escalation",
        "family": "progression",
        "severity": "WARNING",
        "version": "1.2",
        "description": (
            "If a beat with consequenceType == 'fake_win' is present, the intensity "
            "after it must exceed the intensity at the fake win (the problem must "
            "escalate, not repeat or weaken, after a fake resolution). Reports "
            "NOT_APPLICABLE (not FAIL, not UNKNOWN) when no fake-win beat exists — this "
            "check simply does not apply to a concept that doesn't use the fake-"
            "resolution structure."
        ),
    },
    {
        "id": "REPETITION_004",
        "name": "Dominant Action Ratio",
        "family": "visual_novelty",
        # Top-level severity reflects the evaluator's maximum possible ceiling
        # (CRITICAL above 70% dominance), not its minimum FAIL severity
        # (WARNING above 55%) -- never BLOCKER, per this rule's explicit
        # design constraint (see description below).
        "severity": "CRITICAL",
        "version": "1.2",
        "description": (
            "Companion to ATTEMPT_002, not a replacement: catches one primaryVerb "
            "numerically dominating the attempt list even when every attempt is "
            "legitimately distinct in ATTEMPT_002's semantic judgment. WARNING above "
            "55% dominance, CRITICAL above 70%. Never a BLOCKER, since a dominant verb "
            "can be valid if it produces genuinely different consequences each time."
        ),
    },
    {
        "id": "PAYOFF_006",
        "name": "Loopability",
        "family": "final_payoff",
        "severity": "WARNING",
        "version": "1.2",
        "description": (
            "A retention-optimization dimension, never a hard blocker. A strong "
            "natural loop back to the opening (finalPayoff.loopsToOpening + "
            "loopQuality == 'strong') is a bonus. An ordinary hard cut with no loop "
            "claim is fully valid (neutral PASS). Only specific weak-ending text "
            "patterns (fade-out, 'the end', walks away) with neither a loop nor a hard "
            "cut produce a WARNING-severity FAIL."
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
            reason=f"RULESET 1.2: {rule['name']} ({rule['family']} family)",
            breaking_change=False,
        )
        for rule in NEW_RULES
    ]

    new_path = manager.create_new_version(
        new_version="1.2",
        description=(
            "Adds 6 rules closing genuine gaps identified by comparing against the "
            "ruleset-engine Java project: single dominant mechanic (semantically "
            "verified, not just author-claimed), story-detached gap, final peak "
            "intensity, fake-win escalation, dominant action ratio, and loopability. "
            "Uses RuleOutcome.NOT_APPLICABLE (added in an earlier RULESET 1.2 commit, "
            "distinct from UNKNOWN) for PAYOFF_005's not-applicable case. All new IR "
            "fields are optional with backward-compatible defaults; no 1.0/1.1-shaped "
            "IR is broken by this version."
        ),
        changes=changes,
        learned_from=[],
        is_breaking=False,
    )
    print(f"Generated: {new_path}")


if __name__ == "__main__":
    main()
