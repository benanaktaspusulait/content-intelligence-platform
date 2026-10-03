"""One-off script that generates data/rules/RULESET_1.3.yaml from
data/rules/RULESET_1.2.yaml via RuleVersionManager.create_new_version().

Run once: `cd ml-service && POMPOM_DATA_ROOT=$(pwd)/../data python scripts/generate_ruleset_1_3.py`

Safe to re-run only after deleting the previously generated RULESET_1.3.yaml
and removing its entry from versions.yaml — create_new_version() refuses to
overwrite an existing version (raises ValueError: Version 1.3 already exists).

Note: the 9 existing-rule semantic corrections (MOTION_001 rename, PAYOFF_004
rename, HOOK_002 tolerance window, PRODUCIBILITY_002 timeline-aware check,
ATTEMPT_002 prompt strengthening, REPETITION_002/003/004 correlation tagging)
are NOT re-applied here as RuleChange entries — they were already applied
directly to data/rules/RULESET_1.2.yaml in place (RULESET 1.3 part 1), so
create_new_version()'s copy-the-latest-version-as-starting-point behavior
carries them forward automatically. This script only adds the 7 new rules
(RULESET 1.3 part 2).
"""

from app.config import settings
from app.rules.rule_versioning import RuleChange, RuleVersionManager

NEW_RULES: list[dict[str, object]] = [
    {
        "id": "GOAL_001",
        "name": "Goal-Obstruction Clarity",
        "family": "concept_strength",
        "severity": "BLOCKER",
        "version": "1.3",
        "description": (
            "The character must have an immediately understandable, natural physical "
            "goal, and the established abnormal rule must genuinely obstruct that goal. "
            "Distinguishes a believable reason to keep trying from an arbitrary or "
            "magic-demo setup invented only to showcase the mechanic (the character "
            "could simply walk away with no believable reason to continue). Verified "
            "via LLM semantic judgment (check_goal_is_natural), fail-closed to "
            "SERVICE_ERROR."
        ),
    },
    {
        "id": "CONCEPT_008",
        "name": "Rule Readability / Predictability",
        "family": "concept_strength",
        "severity": "CRITICAL",
        "version": "1.3",
        "description": (
            "Distinct from CONCEPT_007: a single, internally consistent mechanic is "
            "not automatically a legible one. A rule that depends on a combination of "
            "exact position, angle, and speed is technically one mechanic but "
            "unlearnable by a child audience watching once. Asks whether a viewer "
            "could learn the pattern from the first 1-2 occurrences and predict what "
            "happens next. Verified via LLM semantic judgment "
            "(check_rule_is_predictable), fail-closed to SERVICE_ERROR."
        ),
    },
    {
        "id": "PROGRESSION_006",
        "name": "Activity Is Not Progression",
        "family": "progression",
        "severity": "CRITICAL",
        "version": "1.3",
        "description": (
            "Deterministic companion to ATTEMPT_002: flags a dominant primaryVerb "
            "ROOT across attempts (e.g. PUSH / PUSH_HARDER / PUSH_FROM_LEFT all share "
            "the root PUSH) even when full verb labels are distinct and ATTEMPT_002's "
            "LLM duplicate-strategy check already passed. Catches 'more activity, not "
            "a new strategy' in the gray area between CHAR_002 (time-active) and "
            "ATTEMPT_002 (label/semantic distinctness). No LLM call."
        ),
    },
    {
        "id": "ESCALATION_005",
        "name": "Meaningful Attempt Escalation",
        "family": "escalation",
        "severity": "WARNING",
        "version": "1.3",
        "description": (
            "Companion to ESCALATION_004 (payoff timing): checks whether attempt-beat "
            "intensity rises across the timeline rather than staying flat or "
            "declining. Deterministic, keyed off beats[].intensity on isAttempt "
            "beats in timeline order. Capped at WARNING — deadpan-comedy concepts can "
            "deliberately keep escalation small."
        ),
    },
    {
        "id": "HOOK_004",
        "name": "Opening Problem Legibility",
        "family": "hook_strength",
        "severity": "CRITICAL",
        "version": "1.3",
        "description": (
            "Stricter than HOOK_002: HOOK_002 confirms something visually unusual "
            "happens immediately; this asks whether the opening ALSO makes clear what "
            "the character wants and why they can't get it yet, not just that "
            "something odd is occurring. Verified via LLM semantic judgment "
            "(check_opening_problem_legible), fail-closed to SERVICE_ERROR."
        ),
    },
    {
        "id": "PERFORMANCE_001",
        "name": "Cute Emotional Readability",
        "family": "character_performance",
        "severity": "WARNING",
        "version": "1.3",
        "description": (
            "New character_performance family (RULESET 1.3). CHAR_002 confirms the "
            "character is active for enough of the runtime; this asks whether that "
            "activity reads as emotionally engaged and sympathetic rather than blank, "
            "robotic, aggressive, or stuck in prolonged panic. Verified via LLM "
            "semantic judgment (check_character_performance_readable), fail-closed to "
            "SERVICE_ERROR. Capped at WARNING — a performance-quality nudge, not a "
            "structural requirement."
        ),
    },
    {
        "id": "PRODUCIBILITY_003",
        "name": "Fragile Interaction Risk",
        "family": "ai_producibility",
        "severity": "CRITICAL",
        "version": "1.3",
        "description": (
            "Fills the gap between PRODUCIBILITY_001 (very-high-complexity hard "
            "block) and PRODUCIBILITY_002 (prop count budget): a middle tier of "
            "AI-generation risks (precision alignment, cloth/rope simulation, "
            "liquids, thin dangling objects, face/hair contact, multi-object "
            "stacking). Uses a tag-based diagnostic model (riskTags in evaluation "
            "details) rather than one rule per risk type. Deterministic substring "
            "match against setting.mainProps and beat action/consequence text, no "
            "LLM call. Always CRITICAL when any tag is found — a human-review "
            "trigger, not an outright render block."
        ),
    },
    {
        "id": "GENERATION_EXECUTABLE_ATTEMPTS",
        "name": "Generation Executable Attempts",
        "family": "generation_executability",
        # Top-level severity reflects the evaluator's maximum ceiling (BLOCKER
        # when zero attempts are judged executable at all), not its minimum
        # FAIL severity (WARNING for vague magnitude/beat-budget pressure
        # alone) -- the evaluator computes its own per-case severity at
        # runtime; this field is informational/summary-only.
        "severity": "BLOCKER",
        "version": "1.3",
        "description": (
            "Distinct from ATTEMPT_002 (semantic strategy diversity): ATTEMPT_002 "
            "asks whether the character is genuinely trying a different strategy; "
            "this asks whether that different strategy will actually LOOK different "
            "and be reliably executable by an image-to-video generation model (e.g. "
            "Seedance). A deterministic keyword pre-filter flags abstract-intent "
            "language ('blocks the escape route', 'tries to outsmart') and vague "
            "movement-magnitude phrasing ('slightly moves') on attempt beats, plus a "
            "beat-budget estimate (too many attempts for the available duration). An "
            "LLM semantic check (check_attempts_are_generation_executable) judges "
            "each attempt for a concrete action-result pair and flags attempts that "
            "would visually collapse into the same choreography despite different "
            "wording. BLOCKER only when NO attempt is judged executable at all or "
            "the LLM is unreachable (SERVICE_ERROR); CRITICAL when some attempts are "
            "unexecutable or abstract-intent language is matched; WARNING for vague "
            "magnitude phrasing or beat-budget pressure alone."
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
            reason=f"RULESET 1.3: {rule['name']} ({rule['family']} family)",
            breaking_change=False,
        )
        for rule in NEW_RULES
    ]

    new_path = manager.create_new_version(
        new_version="1.3",
        description=(
            "Adds 8 rules closing gaps identified in a session-end review of "
            "RULESET 1.2 and a real-generation failure analysis: goal-obstruction "
            "clarity, rule readability/predictability, activity-vs-progression "
            "(verb-root repetition), meaningful attempt escalation, opening problem "
            "legibility, cute emotional readability (new character_performance "
            "family), mid-tier fragile-interaction AI-production risk, and "
            "generation executability (new generation_executability family) -- "
            "whether semantically-distinct attempts will actually render as "
            "visually distinct, reliably executable physical actions, not just "
            "whether they're conceptually different strategies. Also carries "
            "forward 9 existing-rule semantic corrections applied directly to "
            "RULESET_1.2.yaml ahead of this generation: MOTION_001 and PAYOFF_004 "
            "renamed (logic unchanged), HOOK_002 gained a 0.8s tolerance window, "
            "PRODUCIBILITY_002 gained a timeline-aware mid-concept-prop check, "
            "ATTEMPT_002's duplicate-strategy prompt was strengthened for "
            "intensity/angle variants, and REPETITION_002/003/004 + ATTEMPT_002 "
            "gained correlation_group tagging for cross-rule-overlap observability. "
            "All new IR fields/behavior are additive; no 1.0/1.1/1.2-shaped IR is "
            "broken by this version."
        ),
        changes=changes,
        learned_from=[],
        is_breaking=False,
    )
    print(f"Generated: {new_path}")


if __name__ == "__main__":
    main()
