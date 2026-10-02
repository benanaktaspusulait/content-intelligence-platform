"""Duration extraction robustness (Slice A Task 5 review fix).

Guards the divide-by-zero regression: the parser must read a plural
"15 seconds" declaration and must never latch onto a fractional timeline
token such as the "0" in "11.0 SEC" (which previously produced duration 0.0
and a downstream divide-by-zero in the static-state analyzer).
"""

from app.parser.prompt_parser import parse_prompt

_PROMPT_WITH_PLURAL_SECONDS = """[TITLE] Kiko's Mat Mystery
[DURATION] 15 seconds
[FORMAT] Instagram Reel

[CHARACTERS]
- Kiko

[HOOK] 0.0-2.0 SEC
Kiko walks toward the mat.

[BEAT 1] 2.0-8.5 SEC
Kiko sits. Mat turns blue.

[BEAT 2] 8.5-11.0 SEC
Kiko waits.

[PAYOFF] 11.0-15.0 SEC
Kiko smiles.
"""


def test_plural_seconds_duration_is_parsed_positive() -> None:
    result = parse_prompt(_PROMPT_WITH_PLURAL_SECONDS)
    duration = result.video_plan_ir["metadata"]["duration"]
    assert duration == 15.0


def test_duration_never_latches_fractional_timeline_token() -> None:
    # Even with multiple "N.N SEC" timeline tokens present, the duration must
    # not collapse to 0 (which caused the analyzer divide-by-zero).
    result = parse_prompt(_PROMPT_WITH_PLURAL_SECONDS)
    assert result.video_plan_ir["metadata"]["duration"] > 0
