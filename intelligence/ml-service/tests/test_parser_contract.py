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


def test_core_mechanic_defaults_mechaniccount_to_1() -> None:
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["mechanicCount"] == 1


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
