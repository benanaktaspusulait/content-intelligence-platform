"""
Prompt Fixer: Applies rule-specific transformations to improve quality.
Phase 1: Template-based string manipulation fixes.
Phase 2 (future): LLM-powered semantic fixes.
"""

import re
from dataclasses import dataclass
from typing import Any

from ..parser.prompt_parser import parse_prompt
from ..quality.contracts import FixStrategy, PriorityFix


@dataclass
class FixResult:
    """Result of a single fix application"""

    success: bool
    modified_prompt: str
    fix_description: str
    rule_id: str
    changes_made: list[str]
    warnings: list[str]


class PromptFixer:
    """
    Applies rule-specific fixes to prompts based on quality report feedback.

    Phase 1 Implementation:
    - Template-based string manipulation
    - Pattern matching and replacement
    - Duration adjustment
    - Beat insertion/modification

    Limitations:
    - No deep semantic understanding (needs LLM)
    - Fixed templates (not creative)
    - Simple heuristics
    """

    def __init__(self) -> None:
        self.fix_strategies = {
            "CONCEPT_006": self.fix_concept_006,
            "BEAT_004": self.fix_beat_004,
            "REPETITION_002": self.fix_repetition_002,
            "REPETITION_003": self.fix_repetition_003,
            "NOVELTY_001": self.fix_novelty_001,
            "PROGRESSION_005": self.fix_progression_005,
            "ATTEMPT_001": self.fix_attempt_001,
            "ATTEMPT_002": self.fix_attempt_002,
            "CHAR_002": self.fix_char_002,
            "MOTION_001": self.fix_motion_001,
            "PRODUCIBILITY_002": self.fix_producibility_002,
        }

    def apply_fix(
        self, prompt: str, priority_fix: PriorityFix, video_plan_ir: dict[str, Any] | None = None
    ) -> FixResult:
        """
        Apply a single fix to the prompt.

        Args:
            prompt: Original prompt text
            priority_fix: Fix recommendation from QualityScorer
            video_plan_ir: Parsed Video Plan IR (optional, for context)

        Returns:
            FixResult with success status and modified prompt
        """
        rule_id = priority_fix.rule_id

        # A REPLACE_CONCEPT fix cannot be addressed by controlled string
        # patching: the core mechanic itself is insufficient and must be
        # regenerated. The patch-based fixer refuses it rather than producing a
        # misleading "fixed" prompt. (New-concept generation is Slice C Task 4.)
        if priority_fix.strategy is FixStrategy.REPLACE_CONCEPT:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description=(f"{rule_id} requires concept replacement, not a controlled patch."),
                rule_id=rule_id,
                changes_made=[],
                warnings=[
                    "REPLACE_CONCEPT is out of scope for the patch-based fixer; "
                    "the concept must be regenerated (not implemented here)."
                ],
            )

        # A HUMAN_REVIEW fix needs a human decision (e.g. accepting render risk).
        if priority_fix.strategy is FixStrategy.HUMAN_REVIEW:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description=f"{rule_id} requires human review before proceeding.",
                rule_id=rule_id,
                changes_made=[],
                warnings=["HUMAN_REVIEW strategy cannot be auto-applied."],
            )

        if rule_id not in self.fix_strategies:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description=f"No fix strategy for {rule_id}",
                rule_id=rule_id,
                changes_made=[],
                warnings=[f"Rule {rule_id} not implemented in Phase 1"],
            )

        # Parse if IR not provided
        if video_plan_ir is None:
            video_plan_ir = parse_prompt(prompt).video_plan_ir

        # Apply rule-specific fix
        try:
            strategy = self.fix_strategies[rule_id]
            return strategy(prompt, priority_fix, video_plan_ir)
        except Exception as e:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description=f"Fix failed: {str(e)}",
                rule_id=rule_id,
                changes_made=[],
                warnings=[f"Exception during fix: {str(e)}"],
            )

    def fix_concept_006(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix CONCEPT_006: Insufficient distinct consequences.
        Strategy: Add new beats with novel consequences.
        """
        # Extract current consequence count from recommendation
        # Format: "Add N more consequences to reach minimum of 4"
        match = re.search(r"Add (\d+) more consequence", fix.recommendation)
        if not match:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Could not parse consequence count",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=["Failed to extract needed consequence count"],
            )

        needed = int(match.group(1))
        timeline = ir["timeline"]
        character = ir["characters"][0]["name"] if ir.get("characters") else "Character"

        # Strategy: Insert new consequence-bearing beats
        # Find gaps in timeline (beats without new consequences)
        changes = []
        new_beats = []

        # Simple template-based consequence generation
        consequence_templates = [
            f"{character} discovers something unexpected",
            f"The environment changes around {character}",
            f"{character} notices a surprising detail",
            "Something new appears in the scene",
        ]

        # Find insertion points (prefer middle of timeline)
        total_duration = ir["metadata"]["duration"]
        insertion_points = []

        for i, beat in enumerate(timeline):
            if not beat.get("isNewConsequence", False):
                insertion_points.append((i, beat["timing"]["start"]))

        # If not enough non-consequence beats, insert at regular intervals
        if len(insertion_points) < needed:
            interval = total_duration / (needed + 1)
            insertion_points = [(i, i * interval) for i in range(1, needed + 1)]

        # Add new beats
        for idx in range(min(needed, len(consequence_templates))):
            if idx < len(insertion_points):
                pos, time = insertion_points[idx]
                new_beat = (
                    f"\n{time:.1f}-{time + 1.5:.1f} SEC: {character} — "
                    f"{consequence_templates[idx]} (NEW CONSEQUENCE)"
                )
                new_beats.append(new_beat)
                changes.append(f"Added consequence at {time:.1f}s: {consequence_templates[idx]}")

        # Insert new beats into prompt
        # Find timeline section
        timeline_match = re.search(r"(##\s*Timeline\s*\n)(.*?)(?=\n##|\Z)", prompt, re.DOTALL | re.IGNORECASE)

        if not timeline_match:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Could not locate timeline section",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=["Timeline section not found in prompt"],
            )

        original_timeline = timeline_match.group(2)
        modified_timeline = original_timeline + "\n".join(new_beats)

        modified_prompt = prompt.replace(timeline_match.group(0), timeline_match.group(1) + modified_timeline)

        return FixResult(
            success=True,
            modified_prompt=modified_prompt,
            fix_description=f"Added {len(new_beats)} new consequence-bearing beats",
            rule_id=fix.rule_id,
            changes_made=changes,
            warnings=[
                "Phase 1: Template-based consequences (Phase 2 will use LLM for context-aware generation)"
            ],
        )

    def fix_beat_004(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix BEAT_004: Static state dominance >30%.
        Strategy: Split dominant state into sub-states with micro-actions.
        """
        # Extract dominant state from recommendation
        # Format: "Reduce 'sitting on mat' state duration from 42% to <30%"
        match = re.search(r"Reduce '([^']+)' state duration from (\d+)% to <(\d+)%", fix.recommendation)
        if not match:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Could not parse static state info",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=["Failed to extract state name and percentage"],
            )

        dominant_state = match.group(1)
        current_pct = int(match.group(2))
        target_pct = int(match.group(3))

        # Find beats with dominant state
        dominant_beats = [b for b in ir["timeline"] if dominant_state.lower() in b["visualState"].lower()]

        if not dominant_beats:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Could not find dominant state beats",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=[f"No beats found matching state '{dominant_state}'"],
            )

        # Strategy: Split longest static beat into 2 sub-actions
        # Sort by duration
        dominant_beats.sort(key=lambda b: b["timing"]["duration"], reverse=True)
        longest_beat = dominant_beats[0]

        # Create two micro-actions from one static beat
        character = ir["characters"][0]["name"] if ir.get("characters") else "Character"
        start = longest_beat["timing"]["start"]
        duration = longest_beat["timing"]["duration"]
        mid = start + duration / 2

        # Micro-action templates that add visual variety
        sub_actions = [
            f"{character} shifts position slightly",
            f"{character} looks around with curiosity",
        ]

        # Find beat in prompt and split it
        # This is simplified - in production would need more robust beat matching
        original_beat_pattern = re.escape(f"{start:.1f}-{start + duration:.1f} SEC")

        split_beats = f"""{start:.1f}-{mid:.1f} SEC: {character} — {sub_actions[0]}
{mid:.1f}-{start + duration:.1f} SEC: {character} — {sub_actions[1]}"""

        # Replace in prompt
        beat_match = re.search(f"{original_beat_pattern}[^\n]*\n", prompt)

        if beat_match:
            modified_prompt = prompt.replace(beat_match.group(0), split_beats + "\n")

            changes = [
                f"Split {duration:.1f}s static beat at {start:.1f}s into 2 micro-actions",
                f"Reduced '{dominant_state}' dominance",
            ]

            return FixResult(
                success=True,
                modified_prompt=modified_prompt,
                fix_description=(
                    f"Split dominant state beat to reduce from {current_pct}% toward {target_pct}%"
                ),
                rule_id=fix.rule_id,
                changes_made=changes,
                warnings=["Phase 1: Simple split (Phase 2 will use context-aware action generation)"],
            )

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="Could not locate beat to split",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=["Beat pattern matching failed"],
        )

    def fix_repetition_002(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix REPETITION_002: Action repeats 3+ times without escalation.
        Strategy: Replace 3rd occurrence with contrasting action.
        """
        # Extract repeated action from recommendation
        match = re.search(r"Break '([^']+)' repetition after 2nd occurrence", fix.recommendation)
        if not match:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Could not parse repeated action",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=["Failed to extract action name"],
            )

        repeated_action = match.group(1)

        # Find beats with similar actions (using simple substring matching)
        similar_beats = [
            (i, b) for i, b in enumerate(ir["timeline"]) if repeated_action.lower() in b["action"].lower()
        ]

        if len(similar_beats) < 3:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Less than 3 repetitions found",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=[f"Only {len(similar_beats)} occurrences found"],
            )

        # Replace 3rd occurrence with contrasting action
        third_beat_idx, third_beat = similar_beats[2]
        character = ir["characters"][0]["name"] if ir.get("characters") else "Character"

        # Contrasting action template
        contrast_action = f"{character} tries a completely different approach"

        # Find beat in prompt
        start = third_beat["timing"]["start"]
        duration = third_beat["timing"]["duration"]
        original_beat_pattern = re.escape(f"{start:.1f}-{start + duration:.1f} SEC")

        beat_match = re.search(f"{original_beat_pattern}[^\n]*", prompt)

        if beat_match:
            replacement = f"{start:.1f}-{start + duration:.1f} SEC: {contrast_action} (BREAKS REPETITION)"
            modified_prompt = prompt.replace(beat_match.group(0), replacement)

            return FixResult(
                success=True,
                modified_prompt=modified_prompt,
                fix_description=f"Replaced 3rd occurrence of '{repeated_action}' with contrasting action",
                rule_id=fix.rule_id,
                changes_made=[f"Beat at {start:.1f}s: {repeated_action} → different approach"],
                warnings=["Phase 1: Template contrast (Phase 2 will generate contextual alternatives)"],
            )

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="Could not locate 3rd repetition beat",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=["Beat matching failed"],
        )

    def fix_repetition_003(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix REPETITION_003: A-B-C cycle repeats 3x.
        Strategy: Break cycle on 3rd iteration with unexpected outcome.
        """
        # Simplified for Phase 1 - similar to REPETITION_002
        # Phase 2 will implement full cycle detection

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="REPETITION_003 fix not fully implemented in Phase 1",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                "Cycle detection requires advanced pattern recognition",
                "Phase 2 will implement with LLM-based semantic analysis",
                "Current workaround: CONCEPT_006 catches symptom (insufficient consequences)",
            ],
        )

    def fix_novelty_001(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix NOVELTY_001: Long gap between new consequences.
        Strategy: Insert mid-gap consequence.
        """
        # Extract gap info
        match = re.search(r"Longest gap is ([\d.]+)s \(max ([\d.]+)s\)", fix.recommendation)
        if not match:
            return FixResult(
                success=False,
                modified_prompt=prompt,
                fix_description="Could not parse gap duration",
                rule_id=fix.rule_id,
                changes_made=[],
                warnings=["Failed to extract gap timing"],
            )

        gap_duration = float(match.group(1))

        # Find the gap (beats without isNewConsequence)
        # Simplified: Insert consequence in middle of timeline
        total_duration = ir["metadata"]["duration"]
        mid_point = total_duration / 2
        character = ir["characters"][0]["name"] if ir.get("characters") else "Character"

        # Insert new beat at gap midpoint
        new_beat = (
            f"\n{mid_point:.1f}-{mid_point + 1.5:.1f} SEC: {character} — "
            "notices something intriguing (NEW CONSEQUENCE)"
        )

        # Find timeline section
        timeline_match = re.search(r"(##\s*Timeline\s*\n)(.*?)(?=\n##|\Z)", prompt, re.DOTALL | re.IGNORECASE)

        if timeline_match:
            modified_timeline = timeline_match.group(2) + new_beat
            modified_prompt = prompt.replace(
                timeline_match.group(0), timeline_match.group(1) + modified_timeline
            )

            return FixResult(
                success=True,
                modified_prompt=modified_prompt,
                fix_description=(
                    f"Added consequence at {mid_point:.1f}s to reduce gap from {gap_duration:.1f}s"
                ),
                rule_id=fix.rule_id,
                changes_made=[f"Inserted beat to break {gap_duration:.1f}s novelty gap"],
                warnings=["Phase 1: Simple insertion (Phase 2 will analyze actual gap location)"],
            )

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="Could not locate timeline section",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=["Timeline section not found"],
        )

    def fix_progression_005(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix PROGRESSION_005: Static pattern (low intensity variance).
        Strategy: Add intensity peaks.
        """
        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="PROGRESSION_005 fix not implemented in Phase 1",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                "Intensity adjustment requires semantic understanding",
                "Phase 2 will implement with LLM",
            ],
        )

    def fix_attempt_001(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix ATTEMPT_001: Insufficient attempt count.
        Cannot be auto-fixed: adding a genuinely new problem-solving strategy
        requires creative judgment the fixer cannot safely fabricate.
        """
        beats = ir.get("beats", [])
        attempt_count = sum(1 for b in beats if b.get("isAttempt", False))
        duration = ir.get("metadata", {}).get("duration", 15.0)

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description=(
                f"ATTEMPT_001 requires adding genuinely new problem-solving attempts "
                f"({attempt_count} found for a {duration:.0f}s video)."
            ),
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                "Attempt-count fixes require inventing a new, mechanically distinct "
                "strategy — this cannot be safely auto-generated. Add beats marked "
                "`[ATTEMPT: VERB]` with a new primaryVerb not already used.",
            ],
        )

    def fix_attempt_002(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix ATTEMPT_002: Attempts are not mechanically distinct.
        Cannot be auto-fixed: replacing a duplicate-strategy attempt with a
        genuinely different one requires creative judgment.
        """
        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="ATTEMPT_002 requires replacing duplicate-strategy attempts with distinct ones.",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                "Two or more attempts share the same underlying strategy despite "
                "different wording. Review the flagged attempt pairs and replace one "
                "of each pair with a mechanically different approach.",
            ],
        )

    def fix_char_002(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix CHAR_002: Character is passive for too much of the runtime.
        Cannot be auto-fixed: deciding which passive beats to convert into
        active attempts requires creative judgment.
        """
        beats = ir.get("beats", [])
        passive_beats = [b for b in beats if not b.get("isAttempt", False)]

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="CHAR_002 requires converting passive beats into active attempts.",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                f"{len(passive_beats)} beat(s) have the character watching or reacting "
                "rather than actively trying a solution. Mark more beats with "
                "`[ATTEMPT: VERB]` or rewrite passive beats as active attempts.",
            ],
        )

    def fix_motion_001(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix MOTION_001: Dead air exceeds 1.5s.
        Cannot be auto-fixed: deciding what motion to add during a static beat
        requires creative judgment.
        """
        beats = ir.get("beats", [])
        dead_beats = [b for b in beats if b.get("motionAmount") == "none" and b.get("duration", 0.0) > 1.5]

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description="MOTION_001 requires adding motion to the identified dead-air beat(s).",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                f"{len(dead_beats)} beat(s) exceed 1.5s with no motion. Add a small "
                "meaningful action to each (not a cosmetic twitch) that advances the problem.",
            ],
        )

    def fix_producibility_002(self, prompt: str, fix: PriorityFix, ir: dict[str, Any]) -> FixResult:
        """
        Fix PRODUCIBILITY_002: Too many main props for the duration tier.
        Cannot be auto-fixed: deciding which prop to cut requires creative
        judgment about which is least essential to the mechanic.
        """
        props = ir.get("setting", {}).get("mainProps", [])

        return FixResult(
            success=False,
            modified_prompt=prompt,
            fix_description=f"PRODUCIBILITY_002 requires reducing the prop count (currently {len(props)}).",
            rule_id=fix.rule_id,
            changes_made=[],
            warnings=[
                f"Props currently listed: {', '.join(props) if props else '(none)'}. "
                "Remove the prop(s) least essential to the core physical rule.",
            ],
        )
