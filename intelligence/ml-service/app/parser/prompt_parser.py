"""
Prompt to Video Plan IR Parser

Converts freeform text prompts into structured Video Plan IR JSON.
Uses LLM-assisted parsing for accurate extraction of beats, timing, and metadata.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..quality.contracts import ParseResult, ParserMetadata


@dataclass
class ParserConfig:
    """Configuration for parser behavior"""

    default_duration: float = 15.0
    minimum_beat_duration: float = 0.4
    intensity_keywords_high: list[str] | None = None
    intensity_keywords_low: list[str] | None = None

    def __post_init__(self) -> None:
        if self.intensity_keywords_high is None:
            self.intensity_keywords_high = [
                "suddenly",
                "immediately",
                "quickly",
                "fast",
                "rapid",
                "slams",
                "jumps",
                "bursts",
                "explodes",
                "escalates",
            ]
        if self.intensity_keywords_low is None:
            self.intensity_keywords_low = [
                "gently",
                "slowly",
                "carefully",
                "softly",
                "subtle",
                "tiny",
                "small",
                "minimal",
                "slight",
            ]


class PromptParser:
    """
    Parses text prompts into Video Plan IR.

    Strategy:
    1. Extract metadata (title, character, duration, format)
    2. Parse timeline beats (timestamp ranges, actions, consequences)
    3. Identify hook and final payoff
    4. Infer visual states and consequences
    5. Calculate intensities and readability
    6. Detect repetitions and similarities
    """

    def __init__(self, config: ParserConfig | None = None):
        self.config = config or ParserConfig()
        self.warnings: list[str] = []
        self.assumptions: list[str] = []
        self.ambiguities: list[str] = []

    def parse(self, prompt_text: str) -> dict[str, Any]:
        """
        Main parsing entry point.

        Returns:
        {
            "videoPlanIR": {...},
            "parserMetadata": {
                "confidence": 0.85,
                "ambiguities": [...],
                "assumptions": [...],
                "warnings": [...]
            }
        }
        """
        self._reset_parser_state()

        # Step 1: Extract metadata
        metadata = self._extract_metadata(prompt_text)

        # Step 2: Extract characters and setting
        characters = self._extract_characters(prompt_text)
        setting = self._extract_setting(prompt_text)

        # Step 3: Extract learning objective (if applicable)
        learning_objective = self._extract_learning_objective(prompt_text)

        # Step 4: Extract core mechanic
        core_mechanic = self._extract_core_mechanic(prompt_text)

        # Step 5: Parse timeline beats (most complex step)
        beats = self._parse_timeline_beats(prompt_text, metadata["duration"])

        # Step 6: Identify hook
        hook = self._identify_hook(prompt_text, beats)

        # Step 7: Identify final payoff
        final_payoff = self._identify_final_payoff(prompt_text, beats, metadata["duration"])

        # Step 8: Assess AI producibility
        producibility = self._assess_producibility(prompt_text, beats)

        # Step 9: Enrich beats with analysis
        beats = self._enrich_beats(beats)

        # Construct IR
        video_plan_ir = {
            "metadata": metadata,
            "characters": characters,
            "setting": setting,
            "learningObjective": learning_objective,
            "coreMechanic": core_mechanic,
            "hook": hook,
            "beats": beats,
            "finalPayoff": final_payoff,
            "producibility": producibility,
        }

        # Calculate confidence
        confidence = self._calculate_confidence()

        return {
            "videoPlanIR": video_plan_ir,
            "parserMetadata": {
                "confidence": confidence,
                "ambiguities": self.ambiguities,
                "assumptions": self.assumptions,
                "warnings": self.warnings,
            },
        }

    def _reset_parser_state(self) -> None:
        """Clear warnings/assumptions/ambiguities for new parse"""
        self.warnings = []
        self.assumptions = []
        self.ambiguities = []

    def _extract_metadata(self, text: str) -> dict[str, Any]:
        """Extract title, duration, format, series type"""
        metadata = {
            "title": self._extract_title(text),
            "duration": self._extract_duration(text),
            "format": self._extract_format(text),
            "seriesType": self._extract_series_type(text),
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "version": 1,
        }
        return metadata

    def _extract_title(self, text: str) -> str:
        """Extract title from prompt"""
        # Look for TITLE: or title lines
        title_match = re.search(r"(?:TITLE|Title):\s*\n?\s*(.+)", text, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()

        # Look for character — concept pattern
        pattern_match = re.search(r"([A-Z]+)\s*[—-]\s*([A-Z\s/]+)", text)
        if pattern_match:
            return f"{pattern_match.group(1)} — {pattern_match.group(2)}"

        self.assumptions.append("Title not explicitly found, generated from content")
        return "Untitled Video"

    def _extract_duration(self, text: str) -> float:
        """Extract video duration"""
        # Prefer an explicit duration declaration, e.g. "[DURATION] 15 seconds"
        # or "Duration: 15s". Only accept a strictly positive value.
        labeled = re.search(r"duration[^\d]{0,12}(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if labeled:
            value = float(labeled.group(1))
            if value > 0:
                return value

        # General integer "<n> second(s)/sec(s)/s" or "<n>-second" mention.
        # Matching an integer only (no decimals) plus the leading negative
        # lookbehind keeps this from latching onto a fractional timeline token
        # such as the "3.0" / "11.0" in "11.0 SEC" (which previously yielded
        # duration 0.0/3.0 and a downstream divide-by-zero or wrong duration).
        # "[\s-]*" allows both "15 seconds" and the hyphenated "15-second".
        duration_match = re.search(r"(?<![\d.])(\d+)[\s-]*(?:seconds?|secs?|s)\b", text, re.IGNORECASE)
        if duration_match:
            value = float(duration_match.group(1))
            if value > 0:
                return value

        self.assumptions.append(f"Duration not explicit, using default: {self.config.default_duration}s")
        return self.config.default_duration

    def _extract_format(self, text: str) -> str:
        """Extract aspect ratio"""
        if re.search(r"9:16|vertical", text, re.IGNORECASE):
            return "9:16"
        elif re.search(r"16:9|horizontal", text, re.IGNORECASE):
            return "16:9"

        self.assumptions.append("Format not explicit, assuming 9:16 vertical")
        return "9:16"

    def _extract_series_type(self, text: str) -> str:
        """Determine series type from content"""
        text_lower = text.lower()

        if "what's wrong" in text_lower or "whats wrong" in text_lower:
            return "whats_wrong"
        elif "opposite" in text_lower or "slippery" in text_lower and "rough" in text_lower:
            return "opposites"
        elif "discovery" in text_lower:
            return "discovery"
        elif "feeling" in text_lower:
            return "feelings"
        elif "music" in text_lower or "rhythm" in text_lower:
            return "music"
        elif "story" in text_lower or "arda" in text_lower:
            return "stories"
        else:
            return "social_reel"

    def _extract_characters(self, text: str) -> dict[str, Any]:
        """Extract character information"""
        # Look for MAIN CHARACTER or CHARACTER sections
        primary = self._find_primary_character(text)
        secondary = self._find_secondary_characters(text)
        refs = self._find_character_refs(text)

        return {"primary": primary, "secondary": secondary if secondary else None, "characterRefs": refs}

    def _find_primary_character(self, text: str) -> str:
        """Find main character name"""
        # Look for explicit markers
        main_match = re.search(r"(?:MAIN CHARACTER|CHARACTER):\s*\n?\s*([A-Z][a-z]+)", text, re.IGNORECASE)
        if main_match:
            return main_match.group(1).capitalize()

        # Look for character names in title or early text
        for name in ["Kiko", "Mimi", "Opa", "Arda", "Luca", "Noah", "Aiko", "Amara", "Sofia", "Freya"]:
            if re.search(rf"\b{name}\b", text, re.IGNORECASE):
                return name

        self.warnings.append("Primary character not clearly identified")
        return "Unknown"

    def _find_secondary_characters(self, text: str) -> list[str] | None:
        """Find secondary characters if mentioned"""
        # This is simplistic; could be enhanced
        return None

    def _find_character_refs(self, text: str) -> list[str]:
        """Find file references to character sheets"""
        refs = re.findall(r"01-CHARACTERS/[a-z-_/]+\.png", text, re.IGNORECASE)
        return refs if refs else []

    def _extract_setting(self, text: str) -> dict[str, Any]:
        """Extract location and props"""
        location = self._find_location(text)
        props = self._find_main_props(text)

        return {
            "location": location,
            "locationRef": None,  # Could be enhanced to find file refs
            "mainProps": props,
            "visualEnvironment": location,  # Simplified for now
        }

    def _find_location(self, text: str) -> str:
        """Find location description"""
        # Look for SETTING: or LOCATION: sections
        setting_match = re.search(
            r"(?:SETTING|LOCATION):\s*\n?\s*(.+?)(?:\n\n|\n[A-Z])", text, re.IGNORECASE | re.DOTALL
        )
        if setting_match:
            return setting_match.group(1).strip()[:100]  # First 100 chars

        self.ambiguities.append("Location description unclear")
        return "Pompom Hills location"

    def _find_main_props(self, text: str) -> list[str]:
        """Find main props/objects"""
        # Look for MAIN OBJECTS: or similar
        props_match = re.search(
            r"(?:MAIN OBJECTS?|PROPS?):\s*\n((?:.*\n?)+?)(?:\n\n|[A-Z]{2,})", text, re.IGNORECASE
        )
        if props_match:
            props_text = props_match.group(1)
            # Extract numbered or bulleted items
            props = re.findall(r"(?:\d+\.|[-*])\s*(.+)", props_text)
            return [p.strip() for p in props if p.strip()]

        return []

    def _extract_learning_objective(self, text: str) -> dict[str, Any] | None:
        """Extract learning objective if educational video"""
        # Look for CORE ENGLISH or learning words
        concepts_match = re.search(
            r"(?:CORE ENGLISH|LEARNING WORDS?):\s*\n((?:.*\n?)+?)(?:\n\n|={3,})", text, re.IGNORECASE
        )
        if concepts_match:
            concepts_text = concepts_match.group(1)
            concepts = [
                c.strip().upper()
                for c in re.findall(r"([A-Z]+(?:\s+[A-Z]+)?)", concepts_text)
                if len(c.strip()) > 1
            ]

            if concepts:
                return {
                    "concepts": concepts,
                    "pedagogicalGoal": f"Teach {' / '.join(concepts)} contrast",
                    "soundOffReadable": True,  # Assumed for opposites videos
                }

        return None

    def _extract_core_mechanic(self, text: str) -> dict[str, Any]:
        """Extract the core physical rule.

        consistency is only populated from explicit evidence ("breaking",
        "evolving", or an explicit "stays consistent"/"consistent throughout"
        statement). Absent evidence leaves consistency as None rather than
        defaulting to the passing value "consistent" — CONSISTENCY_001 has
        no semantic re-verification of this field, so a fabricated default
        would manufacture a guaranteed PASS.
        """
        rule_match = re.search(
            r"(?:ONE SIMPLE|CORE|MAIN)\s+(?:RULE|MECHANIC|CONCEPT):\s*\n((?:.*\n?)+?)(?:\n\n|={3,})",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        consistency = self._extract_mechanic_consistency(text)
        if consistency is None:
            self.warnings.append("coreMechanic.consistency not explicitly stated in prompt; evidence missing")

        if rule_match:
            rule_text = rule_match.group(1).strip()[:200]
            return {
                "physicalRule": rule_text,
                "causeEffect": "Extracted from prompt",
                "consistency": consistency,
                "mechanicCount": 1,  # Default assumption; author/parser does not
                # currently detect multiple mechanics from
                # text — CONCEPT_007 verifies this claim
                # semantically rather than trusting it.
            }

        self.ambiguities.append("Core mechanic not explicitly stated")
        return {
            "physicalRule": "Inferred from beat actions",
            "causeEffect": "Action-based consequence",
            "consistency": consistency,
            "mechanicCount": 1,
        }

    def _extract_mechanic_consistency(self, text: str) -> str | None:
        """Extract an explicit rule-consistency statement. Returns one of
        "breaking", "evolving", "consistent", or None if the prompt makes
        no explicit claim either way.

        Deliberately requires the claim to be stated near the word "rule"
        or "mechanic" (within the same ~25-character window, with no
        sentence-separating punctuation in between), not just anywhere in
        the prompt — a bare "breaks" elsewhere in the text (e.g. "pencil
        breaks" describing a physical prop event, not the physics rule
        itself) must not be misread as a rule-consistency statement. The
        window is intentionally short and the punctuation boundary
        intentionally includes commas/semicolons (not just periods) so that
        two unrelated clauses sharing one sentence -- e.g. "the core rule is
        simple, but the pencil tip breaks off" -- don't false-positive just
        because "rule" and "breaks" both appear somewhere in the sentence.
        """
        # Window size and clause-boundary characters shared by every
        # keyword-proximity check below -- tune in one place.
        proximity_window = r"[^.,;]{0,25}"

        text_lower = text.lower()
        if re.search(rf"(?:rule|mechanic){proximity_window}\bbreak(?:s|ing)?\b", text_lower) or re.search(
            rf"\bbreak(?:s|ing)?\b{proximity_window}(?:rule|mechanic)", text_lower
        ):
            return "breaking"
        if re.search(rf"(?:rule|mechanic){proximity_window}\bevolv(?:es|ing)\b", text_lower) or re.search(
            rf"\bevolv(?:es|ing)\b{proximity_window}(?:rule|mechanic)", text_lower
        ):
            return "evolving"
        if "stays consistent" in text_lower or "consistent throughout" in text_lower:
            return "consistent"
        return None

    def _parse_timeline_beats(self, text: str, duration: float) -> list[dict[str, Any]]:
        """
        Parse timeline beats from prompt.

        This is the most complex part. Looks for timestamp ranges like:
        0.0-1.0 SEC
        1.0-3.0 SEC
        etc.
        """
        beats = []

        # Find all timestamp sections
        beat_pattern = (
            r"(\d+\.?\d*)[:\s]*[-–—]\s*(\d+\.?\d*)\s*(?:SEC|SECONDS?|S)\b\s*[:\-—–]?\s*"
            r"([^\n]+(?:\n(?!\d+\.?\d*\s*[-–—]\s*\d+)[^\n]*)*)"
        )

        matches = re.finditer(beat_pattern, text, re.IGNORECASE | re.MULTILINE)

        beat_id = 1
        for match in matches:
            start_time = float(match.group(1))
            end_time = float(match.group(2))
            description = match.group(3).strip()

            if end_time <= start_time:
                self.warnings.append(f"Invalid time range: {start_time}-{end_time}, skipping beat")
                continue

            beat = self._create_beat_from_description(
                beat_id=f"beat_{beat_id:02d}",
                start_time=start_time,
                end_time=end_time,
                description=description,
            )

            beats.append(beat)
            beat_id += 1

        if not beats:
            self.warnings.append("No explicit timeline beats found, using fallback parsing")
            beats = self._fallback_beat_parsing(text, duration)

        return beats

    def _extract_attempt_marker(self, description: str) -> tuple[bool, str]:
        """Extract an explicit ``[ATTEMPT: VERB]`` marker from a beat description.

        Returns (is_attempt, primary_verb). primary_verb is normalized
        upper-case with surrounding whitespace stripped. Beats without an
        explicit marker are never guessed into being an attempt — isAttempt
        defaults to False, consistent with the parser's existing
        "flag ambiguity, don't invent data" convention.
        """
        match = re.search(r"\[ATTEMPT:\s*([A-Za-z][A-Za-z\s]*)\]", description)
        if not match:
            return False, ""
        verb = match.group(1).strip().upper()
        return True, verb

    # Physical action verbs that, when they are the first word of a beat's
    # action text, indicate a problem-solving attempt even with no explicit
    # [ATTEMPT: VERB] marker. Deliberately short and conservative -- this is
    # a confidence-improving inference, not a replacement for the marker;
    # ambiguous or non-physical leading words are left unmarked (isAttempt
    # stays False) rather than guessed.
    _INFERABLE_ATTEMPT_VERBS = frozenset(
        {
            "CATCHES",
            "CATCH",
            "BLOCKS",
            "BLOCK",
            "GRABS",
            "GRAB",
            "PULLS",
            "PULL",
            "PUSHES",
            "PUSH",
            "LIFTS",
            "LIFT",
            "HOLDS",
            "HOLD",
            "STEPS",
            "STEP",
            "TURNS",
            "TURN",
            "PLACES",
            "PLACE",
            "ROTATES",
            "ROTATE",
        }
    )

    # Articles/determiners that can lead a noun phrase using a word that is
    # ALSO in _INFERABLE_ATTEMPT_VERBS (e.g. "the push", "a turn") without
    # that word being used as a verb at all. A leading word followed
    # immediately by one of these is never treated as a subject-skip
    # candidate -- "The push toward the door failed" must not infer an
    # attempt just because word 2 ("push") is whitelisted; "push" there is
    # a noun, not a character performing an action.
    _NON_SUBJECT_LEADING_WORDS = frozenset({"THE", "A", "AN", "NO", "THIS", "THAT", "THESE", "THOSE"})

    def _infer_attempt_from_leading_verb(self, description: str) -> tuple[bool, str]:
        """Infer isAttempt/primaryVerb from an unmarked beat's leading word,
        when that word is a known physical action verb. Returns
        (False, "") when the leading word is not in the conservative
        _INFERABLE_ATTEMPT_VERBS set -- never guessed from anything else.

        Beat text conventionally leads with a character name, optionally
        followed by a dash separator, before the action verb (e.g.
        "Mimi catches the cup" or "Mimi — catches the cup"). To find the
        verb to check against the whitelist, this looks at the first word;
        if that word is not itself in the whitelist, it also checks the
        word immediately after a leading subject token -- but ONLY when
        that first word plausibly IS a subject (capitalized, and not an
        article/determiner in _NON_SUBJECT_LEADING_WORDS). This prevents a
        noun-phrase sentence like "The push toward the door failed" or "A
        turn of events surprises everyone" from being misread as an
        attempt just because word 2 happens to be whitelisted -- there,
        word 1 ("The"/"A") is a determiner, not a character's name, so the
        second-word check never fires. A bare name like "Mimi" is itself
        never in _INFERABLE_ATTEMPT_VERBS, so allowing the second-word
        check for genuine capitalized-subject cases does not loosen the
        conservative matching; it only locates the verb correctly when a
        real subject precedes it.
        """
        stripped = description.strip()
        first_word_match = re.match(r"[A-Za-z]+", stripped)
        if not first_word_match:
            return False, ""
        first_word = first_word_match.group(0).upper()
        if first_word in self._INFERABLE_ATTEMPT_VERBS:
            return True, first_word

        # Not a verb on its own -- only treat it as a skippable subject
        # token when it's capitalized in the original text (a plausible
        # proper noun/character name) and not a determiner/article that
        # would make the following word a noun, not a verb.
        first_word_raw = stripped[: first_word_match.end()]
        is_plausible_subject = (
            first_word_raw[:1].isupper() and first_word not in self._NON_SUBJECT_LEADING_WORDS
        )
        if not is_plausible_subject:
            return False, ""

        after_first_word = stripped[first_word_match.end() :]
        second_word_match = re.match(r"\s*(?:[-—–]\s*)?([A-Za-z]+)", after_first_word)
        if second_word_match:
            second_word = second_word_match.group(1).upper()
            if second_word in self._INFERABLE_ATTEMPT_VERBS:
                return True, second_word
        return False, ""

    def _extract_detached_marker(self, description: str) -> bool:
        """Extract an explicit ``[DETACHED]`` marker from a beat description.

        Returns True (relatesToCoreProblem) unless the beat is explicitly
        marked as detached from the core problem/mechanic. This default
        (True, i.e. "assumed on-topic") is the documented backward-compatible
        default for pre-1.2 IRs that have never seen this field — see
        VIDEO_PLAN_IR_SCHEMA.md's Backward Compatibility section.
        """
        return "[DETACHED]" not in description.upper()

    def _create_beat_from_description(
        self, beat_id: str, start_time: float, end_time: float, description: str
    ) -> dict[str, Any]:
        """Create a beat dict from timestamp and description"""
        duration = end_time - start_time

        # Extract action (first sentence or phrase)
        action = self._extract_action_from_description(description)

        # Extract visual state
        visual_state = self._extract_visual_state(description, action)
        visual_state_id = self._normalize_visual_state_id(visual_state)

        # Extract consequence
        consequence = self._extract_consequence(description)

        # Determine action type
        action_type = self._determine_action_type(action, description)

        # Estimate intensity
        intensity = self._estimate_intensity(description)

        # Estimate motion amount
        motion_amount = self._estimate_motion_amount(description)

        # Extract dialogue if present
        dialogue = self._extract_dialogue(description)

        # Check readability
        is_readable = duration >= 0.6

        is_attempt, primary_verb = self._extract_attempt_marker(description)
        if not is_attempt:
            is_attempt, primary_verb = self._infer_attempt_from_leading_verb(description)
            if is_attempt:
                self.assumptions.append(
                    f"Beat '{description[:40]}...' inferred as an attempt ({primary_verb}) "
                    "from its leading verb; no explicit [ATTEMPT: VERB] marker was present."
                )
        relates_to_core_problem = self._extract_detached_marker(description)

        return {
            "id": beat_id,
            "startTime": start_time,
            "endTime": end_time,
            "duration": duration,
            "action": action,
            "actionType": action_type,
            "visualState": visual_state,
            "visualStateId": visual_state_id,
            "consequence": consequence,
            "consequenceType": "new",  # Will be enriched later
            "intensity": intensity,
            "motionAmount": motion_amount,
            "dialogue": dialogue,
            "readabilityDuration": duration,
            "isReadable": is_readable,
            "isNewConsequence": True,  # Will be enriched later
            "similarToBeats": [],  # Will be enriched later
            "cycleGroup": None,  # Will be enriched later
            "isAttempt": is_attempt,
            "primaryVerb": primary_verb,
            "relatesToCoreProblem": relates_to_core_problem,
        }

    def _extract_action_from_description(self, description: str) -> str:
        """Extract main action from beat description"""
        # Take first sentence or up to 60 chars
        first_line = description.split("\n")[0]
        if len(first_line) > 80:
            first_line = first_line[:80] + "..."
        return first_line.strip()

    def _extract_visual_state(self, description: str, action: str) -> str:
        """Infer visual state from description"""
        # Simplified: use action as visual state
        return f"character {action.lower()}"

    def _normalize_visual_state_id(self, visual_state: str) -> str:
        """Convert visual state to normalized ID"""
        # Convert to lowercase, replace spaces with underscores
        normalized = re.sub(r"\s+", "_", visual_state.lower())
        normalized = re.sub(r"[^a-z0-9_]", "", normalized)
        return normalized[:50]  # Limit length

    def _extract_consequence(self, description: str) -> str:
        """Extract physical consequence from description"""
        # Look for result descriptions (simplified)
        return description[:150]  # First 150 chars as consequence

    def _determine_action_type(self, action: str, description: str) -> str:
        """Classify action type"""
        action_lower = action.lower()
        desc_lower = description.lower()

        if any(word in action_lower for word in ["move", "walk", "run", "slide", "jump"]):
            return "motion"
        elif any(word in action_lower for word in ["grab", "pull", "push", "hold", "touch"]):
            return "interaction"
        elif any(word in desc_lower for word in ["react", "surprise", "notice", "realize"]):
            return "reaction"
        elif any(word in action_lower for word in ["reach", "step", "approach"]):
            return "transition"
        else:
            return "interaction"

    def _estimate_intensity(self, description: str) -> int:
        """Estimate intensity 1-10 based on keywords"""
        desc_lower = description.lower()

        # High intensity keywords
        # ``ParserConfig.__post_init__`` always populates these lists when the
        # constructor leaves them unset, so the ``or []`` fallback is
        # unreachable in practice; it only satisfies the type checker.
        high_keywords = self.config.intensity_keywords_high or []
        high_score = sum(1 for kw in high_keywords if kw in desc_lower)

        # Low intensity keywords
        low_keywords = self.config.intensity_keywords_low or []
        low_score = sum(1 for kw in low_keywords if kw in desc_lower)

        # Base intensity
        base = 5

        # Adjust
        intensity = base + (high_score * 2) - (low_score * 2)

        # Clamp to 1-10
        return max(1, min(10, intensity))

    def _estimate_motion_amount(self, description: str) -> str:
        """Estimate motion amount"""
        desc_lower = description.lower()

        if any(word in desc_lower for word in ["sudden", "quick", "fast", "immediately", "rapidly"]):
            return "high"
        elif any(word in desc_lower for word in ["gentle", "slow", "careful", "tiny", "small"]):
            return "minimal"
        elif "no" in desc_lower or "static" in desc_lower or "still" in desc_lower:
            return "none"
        else:
            return "moderate"

    def _extract_dialogue(self, description: str) -> dict[str, Any] | None:
        """Extract dialogue from description"""
        # Look for quoted text or explicit dialogue markers
        dialogue_match = re.search(r'["""\'](.*?)["""\']', description)
        if dialogue_match:
            text = dialogue_match.group(1)
            # Infer speaker from context (simplified)
            return {
                "speaker": "Character",
                "text": text,
                "isLearningWord": text.isupper(),  # Assume uppercase = learning word
            }
        return None

    def _fallback_beat_parsing(self, text: str, duration: float) -> list[dict[str, Any]]:
        """Fallback if no explicit timestamps found"""
        self.warnings.append("Using fallback beat parsing - confidence low")
        # Create generic beats
        return []

    def _identify_hook(self, text: str, beats: list[dict[str, Any]]) -> dict[str, Any]:
        """Identify hook characteristics.

        visualStrength and soundOffClear are only ever populated from
        explicit evidence in the prompt text. A prompt with no HOOK section
        and no visual-strength/sound-off language leaves both as None
        (evidence missing) rather than defaulting to values that would pass
        HOOK_002's un-reverified threshold checks.
        """
        starts_mid_action = "start" in text.lower() and ("mid" in text.lower() or "action" in text.lower())

        first_beat = beats[0] if beats else None

        visual_strength = self._extract_hook_visual_strength(text)
        sound_off_clear = self._extract_hook_sound_off_clear(text)

        if visual_strength is None:
            self.warnings.append("hook.visualStrength not explicitly stated in prompt; evidence missing")
        if sound_off_clear is None:
            self.warnings.append("hook.soundOffClear not explicitly stated in prompt; evidence missing")

        return {
            "anomaly": first_beat["action"] if first_beat else "Unknown",
            "startsAt": 0.0,
            "startsMidAction": starts_mid_action,
            "visualStrength": visual_strength,
            "soundOffClear": sound_off_clear,
        }

    def _extract_hook_visual_strength(self, text: str) -> int | None:
        """Extract an explicit visual-strength rating (1-5) from a HOOK
        section, e.g. "Visual strength: 5". Returns None when absent."""
        match = re.search(r"visual\s*strength[:\s]+(\d)", text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 5:
                return value
        return None

    def _extract_hook_sound_off_clear(self, text: str) -> bool | None:
        """Extract an explicit sound-off-clear claim from a HOOK section,
        e.g. "Sound off clear: true". Returns None when absent."""
        match = re.search(r"sound\s*off\s*clear[:\s]+(true|false|yes|no)", text, re.IGNORECASE)
        if match:
            return match.group(1).lower() in ("true", "yes")
        return None

    def _identify_final_payoff(
        self, text: str, beats: list[dict[str, Any]], duration: float
    ) -> dict[str, Any]:
        """Identify final payoff characteristics"""
        loops_to_opening = "loop" in text.lower() and "no loop" not in text.lower()
        loop_quality = "strong" if "strong loop" in text.lower() else "weak" if loops_to_opening else "none"

        if not beats:
            return {
                "type": "escalation",
                "startsAt": duration - 3.0,
                "endsAt": duration,
                "isPeakIntensity": True,
                "isHardCut": True,
                "isRepeatOfOpening": False,
                "loopsToOpening": loops_to_opening,
                "loopQuality": loop_quality,
            }

        last_beat = beats[-1]
        first_beat = beats[0]

        # Check if final repeats opening
        is_repeat = self._check_similarity(first_beat["action"], last_beat["action"]) > 0.7

        return {
            "type": "escalation",
            "startsAt": last_beat["startTime"],
            "endsAt": last_beat["endTime"],
            "isPeakIntensity": last_beat["intensity"] >= max(b["intensity"] for b in beats),
            "isHardCut": "hard cut" in text.lower() or "mid" in text.lower(),
            "isRepeatOfOpening": is_repeat,
            "loopsToOpening": loops_to_opening,
            "loopQuality": loop_quality,
        }

    def _assess_producibility(self, text: str, beats: list[dict[str, Any]]) -> dict[str, Any]:
        """Assess AI producibility"""
        text_lower = text.lower()

        # Count risk factors
        risk_factors = []
        if "hand" in text_lower and "object" in text_lower:
            risk_factors.append("hand-object precision")
        if "morph" in text_lower or "transform" in text_lower:
            risk_factors.append("morphing")
        if "liquid" in text_lower or "water" in text_lower:
            risk_factors.append("liquid physics")

        # Estimate complexity
        if len(risk_factors) >= 3:
            complexity = "very_high"
        elif len(risk_factors) == 2:
            complexity = "high"
        elif len(risk_factors) == 1:
            complexity = "medium"
        else:
            complexity = "low"

        return {
            "overallComplexity": complexity,
            "riskFactors": risk_factors,
            "estimatedRenderQuality": 4 if complexity == "low" else 3 if complexity == "medium" else 2,
        }

    def _enrich_beats(self, beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich beats with:
        - isNewConsequence flags
        - similarToBeats lists
        - consequenceType classification
        - cycleGroup detection
        """
        if not beats:
            return beats

        # Mark first beat as new
        beats[0]["isNewConsequence"] = True
        beats[0]["consequenceType"] = "new"

        # Compare each beat to previous beats
        for i in range(1, len(beats)):
            current = beats[i]
            is_new = True
            similar_beats = []

            for j in range(i):
                previous = beats[j]
                similarity = self._check_similarity(current["action"], previous["action"])

                if similarity > 0.7:
                    similar_beats.append(previous["id"])
                    is_new = False

            current["isNewConsequence"] = is_new
            current["similarToBeats"] = similar_beats

            if similar_beats:
                current["consequenceType"] = "repeat"
            elif i > 0 and current["visualStateId"] == beats[i - 1]["visualStateId"]:
                current["consequenceType"] = "continuation"
            else:
                current["consequenceType"] = "new"

        return beats

    def _check_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity check (could be enhanced with embeddings)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_confidence(self) -> float:
        """Calculate overall parser confidence"""
        confidence = 1.0

        # Reduce confidence for each issue
        confidence -= len(self.warnings) * 0.1
        confidence -= len(self.ambiguities) * 0.05
        confidence -= len(self.assumptions) * 0.03

        return max(0.0, min(1.0, confidence))


# Convenience function
def parse_prompt(prompt_text: str, config: ParserConfig | None = None) -> ParseResult:
    """Parse a prompt into the canonical :class:`ParseResult`.

    Callers consume ``result.video_plan_ir`` and ``result.metadata`` rather
    than the historical ``{"videoPlanIR": ..., "parserMetadata": ...}`` dict.
    """
    parser = PromptParser(config)
    raw = parser.parse(prompt_text)
    pm = raw["parserMetadata"]
    return ParseResult(
        video_plan_ir=raw["videoPlanIR"],
        metadata=ParserMetadata(
            confidence=float(pm.get("confidence", 0.0)),
            ambiguities=tuple(pm.get("ambiguities", [])),
            assumptions=tuple(pm.get("assumptions", [])),
            warnings=tuple(pm.get("warnings", [])),
        ),
    )
