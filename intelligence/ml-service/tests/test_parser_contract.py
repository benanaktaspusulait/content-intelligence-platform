"""Canonical parser contract (Slice A Task 5).

``parse_prompt`` must return a typed :class:`ParseResult` exposing
``video_plan_ir`` and ``metadata`` (a :class:`ParserMetadata`), never a raw
dict with ``videoPlanIR``/``parserMetadata`` keys.
"""

from app.parser.prompt_parser import ParserConfig, parse_prompt
from app.quality.contracts import ParseResult, ParserMetadata

SAMPLE_PROMPT = """
Title: Kiko's Discovery

15-second video

## Characters
- Kiko: Curious, energetic

## Timeline
0.0-3.0 SEC: Kiko — spots a shiny box
3.0-6.0 SEC: Kiko — opens the box with excitement
6.0-9.0 SEC: Kiko — finds colorful ribbons inside
9.0-12.0 SEC: Kiko — pulls ribbons creating patterns
12.0-15.0 SEC: Kiko — ribbons form a rainbow arch
"""


def test_parse_prompt_returns_parse_result() -> None:
    result = parse_prompt(SAMPLE_PROMPT)
    assert isinstance(result, ParseResult)
    assert isinstance(result.metadata, ParserMetadata)


def test_parse_result_exposes_video_plan_ir_with_beats() -> None:
    result = parse_prompt(SAMPLE_PROMPT)
    ir = result.video_plan_ir
    assert isinstance(ir, dict)
    # The canonical IR key is ``beats`` (not ``timeline``).
    assert "beats" in ir
    assert len(ir["beats"]) == 5
    assert ir["metadata"]["title"] == "Kiko's Discovery"
    assert ir["metadata"]["duration"] == 15.0


def test_parser_metadata_fields_are_tuples() -> None:
    result = parse_prompt(SAMPLE_PROMPT)
    meta = result.metadata
    assert isinstance(meta.confidence, float)
    assert isinstance(meta.ambiguities, tuple)
    assert isinstance(meta.assumptions, tuple)
    assert isinstance(meta.warnings, tuple)


def test_parse_prompt_accepts_optional_config() -> None:
    config = ParserConfig(default_duration=20.0)
    result = parse_prompt(SAMPLE_PROMPT, config=config)
    assert isinstance(result, ParseResult)


def test_parse_result_is_immutable() -> None:
    result = parse_prompt(SAMPLE_PROMPT)
    try:
        result.video_plan_ir = {}  # type: ignore[misc]
    except Exception as exc:  # frozen dataclass -> FrozenInstanceError
        assert "cannot assign" in str(exc) or "FrozenInstance" in type(exc).__name__
    else:  # pragma: no cover - frozen dataclass must reject assignment
        raise AssertionError("ParseResult must be immutable")


def test_beats_default_isattempt_false_and_primaryverb_empty() -> None:
    """Beats with no explicit attempt marker default isAttempt False."""
    prompt = """
Title: Plain Beat

15-second video

## Characters
- Hero: Brave

## Timeline
0.0-5.0 SEC: Hero — stands still
5.0-15.0 SEC: Hero — walks away
"""
    ir = parse_prompt(prompt).video_plan_ir
    for beat in ir["beats"]:
        assert beat["isAttempt"] is False
        assert beat["primaryVerb"] == ""


def test_beats_explicit_attempt_marker_sets_isattempt_and_verb() -> None:
    """`[ATTEMPT: VERB]` in a beat description sets isAttempt/primaryVerb."""
    prompt = """
Title: Mimi vs Rug

15-second video

## Characters
- Mimi: Curious

## Timeline
0.0-2.0 SEC: Mimi — catches the sliding cup [ATTEMPT: CATCH]
2.0-5.0 SEC: Mimi — blocks it with a book [ATTEMPT: BLOCK]
5.0-15.0 SEC: Mimi — watches the rug slide away
"""
    ir = parse_prompt(prompt).video_plan_ir
    beats = ir["beats"]
    assert beats[0]["isAttempt"] is True
    assert beats[0]["primaryVerb"] == "CATCH"
    assert beats[1]["isAttempt"] is True
    assert beats[1]["primaryVerb"] == "BLOCK"
    assert beats[2]["isAttempt"] is False
    assert beats[2]["primaryVerb"] == ""


def test_beats_default_relatestocoreproblem_true() -> None:
    """Beats with no explicit detachment marker default relatesToCoreProblem True."""
    prompt = """
Title: Plain Beat

15-second video

## Characters
- Hero: Brave

## Timeline
0.0-5.0 SEC: Hero — stands still
5.0-15.0 SEC: Hero — walks away
"""
    ir = parse_prompt(prompt).video_plan_ir
    for beat in ir["beats"]:
        assert beat["relatesToCoreProblem"] is True


def test_beats_explicit_detached_marker_sets_relatestocoreproblem_false() -> None:
    """`[DETACHED]` in a beat description sets relatesToCoreProblem to False."""
    prompt = """
Title: Mimi vs Rug

15-second video

## Characters
- Mimi: Curious

## Timeline
0.0-2.0 SEC: Mimi — catches the sliding cup [ATTEMPT: CATCH]
2.0-3.0 SEC: Camera cuts to unrelated scenery [DETACHED]
3.0-15.0 SEC: Mimi — blocks it with a book [ATTEMPT: BLOCK]
"""
    ir = parse_prompt(prompt).video_plan_ir
    beats = ir["beats"]
    assert beats[0]["relatesToCoreProblem"] is True
    assert beats[1]["relatesToCoreProblem"] is False
    assert beats[2]["relatesToCoreProblem"] is True


def test_core_mechanic_does_not_invent_mechanic_count() -> None:
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["mechanicCount"] is None


def test_final_payoff_defaults_loop_fields() -> None:
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["finalPayoff"]["loopsToOpening"] is False
    assert ir["finalPayoff"]["loopQuality"] == "none"


def test_hook_fields_are_none_when_no_explicit_evidence() -> None:
    """A prompt with no HOOK: section and no visual-strength/sound-off
    language must not fabricate a passing visualStrength=4/soundOffClear=True
    — those become None (evidence missing), not an invented pass."""
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    result = parse_prompt(prompt)
    ir = result.video_plan_ir
    assert ir["hook"]["visualStrength"] is None
    assert ir["hook"]["soundOffClear"] is None
    assert "hook.visualStrength" in " ".join(result.metadata.warnings) or any(
        "visualStrength" in w for w in result.metadata.warnings
    )


def test_hook_fields_are_populated_when_explicit_evidence_present() -> None:
    """An explicit HOOK: section with a stated visual strength and sound-off
    claim is parsed, not discarded."""
    prompt = """
Title: Loud Hook

15-second video

## Hook
Visual strength: 5
Sound off clear: true

## Timeline
0.0-15.0 SEC: Hero — explodes into view
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["hook"]["visualStrength"] == 5
    assert ir["hook"]["soundOffClear"] is True


def test_core_mechanic_consistency_is_none_when_not_stated() -> None:
    """No explicit consistency statement in the prompt must not default to
    the passing value "consistent" — it becomes None (evidence missing)."""
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["consistency"] is None


def test_core_mechanic_consistency_is_parsed_when_explicitly_stated() -> None:
    prompt = """
Title: Breaking Rule

15-second video

## Core Rule
The rule breaks halfway through on purpose for the twist.

## Timeline
0.0-15.0 SEC: Hero — walks normally
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["consistency"] == "breaking"


def test_core_mechanic_consistency_unrelated_breaks_in_same_sentence_is_not_misread() -> None:
    """A prop event ("pencil tip breaks off") sharing a sentence with an
    unrelated mention of "rule" must not be misread as a rule-consistency
    claim just because both words appear in the same sentence -- this is
    the exact false-positive pattern that caused a regression against the
    FAIL_003_ARDA_REPETITIVE_SHARPEN_DRAW.md fixture during this task."""
    prompt = """
Title: Pencil Mishap

15-second video

## Core Rule
The core rule is simple and clean, but the pencil tip breaks off here.

## Timeline
0.0-15.0 SEC: Hero — sharpens the pencil
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["consistency"] is None


def test_unmarked_beat_with_clear_action_verb_is_inferred_as_attempt() -> None:
    """A beat description starting with a recognizable physical action verb,
    even with no [ATTEMPT: VERB] marker, is inferred as an attempt at lower
    confidence rather than being invisible to ATTEMPT_001/ATTEMPT_002."""
    prompt = """
Title: Mimi vs Rug

15-second video

## Characters
- Mimi: Curious

## Timeline
0.0-3.0 SEC: Mimi catches the sliding cup with both hands
3.0-6.0 SEC: Mimi blocks it with a book
6.0-15.0 SEC: Mimi watches the rug slide away
"""
    result = parse_prompt(prompt)
    ir = result.video_plan_ir
    beats = ir["beats"]
    assert beats[0]["isAttempt"] is True
    assert beats[0]["primaryVerb"] == "CATCHES"
    assert beats[1]["isAttempt"] is True
    assert beats[1]["primaryVerb"] == "BLOCKS"
    assert beats[2]["isAttempt"] is False
    assert any("inferred" in a.lower() for a in result.metadata.assumptions)


def test_explicit_marker_still_takes_precedence_over_inference() -> None:
    """When both an explicit [ATTEMPT: VERB] marker and an inferrable leading
    verb are present, the explicit marker's verb wins."""
    prompt = """
Title: Mimi vs Rug

15-second video

## Timeline
0.0-3.0 SEC: Mimi catches the sliding cup [ATTEMPT: GRAB]
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["beats"][0]["primaryVerb"] == "GRAB"


def test_noun_phrase_with_whitelisted_second_word_is_not_misread_as_attempt() -> None:
    """A sentence led by an article/determiner ("The push...", "A turn...")
    using a whitelisted verb word as a NOUN, not an actor performing an
    action, must not be inferred as an attempt just because word 2 happens
    to be in the whitelist -- the leading-subject-skip logic only applies
    when word 1 is a plausible capitalized subject (e.g. a character name),
    never an article/determiner."""
    prompt = """
Title: Narrated Events

15-second video

## Timeline
0.0-7.0 SEC: The push toward the door failed completely
7.0-15.0 SEC: A turn of events surprises everyone watching
"""
    ir = parse_prompt(prompt).video_plan_ir
    beats = ir["beats"]
    assert beats[0]["isAttempt"] is False
    assert beats[0]["primaryVerb"] == ""
    assert beats[1]["isAttempt"] is False
    assert beats[1]["primaryVerb"] == ""


def test_fallback_parsing_with_no_timeline_marks_evidence_missing() -> None:
    """A prompt with no parseable timeline at all must surface
    evidenceMissing=("beats",), not silently return an empty, valid-looking
    plan that callers mistake for a genuinely zero-beat video."""
    prompt = "Title: No Timeline Here\n\nJust some prose, no SEC markers at all.\n"
    result = parse_prompt(prompt)
    assert result.video_plan_ir["beats"] == []
    assert "beats" in result.metadata.evidence_missing


def test_normal_parse_with_beats_has_empty_evidence_missing() -> None:
    result = parse_prompt(SAMPLE_PROMPT)
    assert result.metadata.evidence_missing == ()
