from app.workflow.concept_ranking import normalize
from app.workflow.short_form_engine import _timeline


def test_markdown_story_timing_table_is_acquired_as_source_bound_timed_beats():
    source = """# Story and Timing

| Time | Beat |
|---|---|
| 00–03s | Kiko waves once beside the puddle. |
| 03–06s | The reflection stays still. |
| 06–09s | The reflection copies Kiko after she lowers her hand. |
| 09–12s | She repeats the wave test. |
| 12–15s | The reflection completes the delayed wave. |

## Visual and Motion Direction
Keep the character and puddle in frame.
"""

    beats = _timeline(source)

    assert [(beat["start"], beat["end"]) for beat in beats] == [
        (0.0, 3.0),
        (3.0, 6.0),
        (6.0, 9.0),
        (9.0, 12.0),
        (12.0, 15.0),
    ]
    assert [beat["quote"] for beat in beats] == [
        "Kiko waves once beside the puddle.",
        "The reflection stays still.",
        "The reflection copies Kiko after she lowers her hand.",
        "She repeats the wave test.",
        "The reflection completes the delayed wave.",
    ]
    assert all(source[start:end] == quote for (start, end), quote in (
        (beat["sourceSpan"], beat["quote"]) for beat in beats
    ))


def test_markdown_production_fields_map_but_absent_goal_object_and_rule_stay_missing():
    source = """**Title:** Kiko’s Reflection Is Late
**Character:** Kiko
**Duration:** 15 seconds

| Time | Beat |
|---|---|
| 00–03s | Kiko notices her reflection and lifts one hand. |
| 03–06s | Kiko gives one slow wave. |
| 06–09s | The reflection waits, then copies Kiko. |
| 09–12s | Kiko repeats the test. |
| 12–15s | They settle beside the puddle. |

## Clean Start State
Kiko kneels beside a small puddle with her reflection matching her neutral pose.

## Completed End State
Kiko and the delayed reflection finish their second wave and settle.
"""

    candidate = normalize(source)

    assert candidate["title"] == "Kiko’s Reflection Is Late"
    assert candidate["protagonist"] == "Kiko"
    assert candidate["frameZeroDescription"] == (
        "Kiko kneels beside a small puddle with her reflection matching her neutral pose."
    )
    assert candidate["finalPayoff"] == (
        "Kiko and the delayed reflection finish their second wave and settle."
    )
    assert candidate["intendedDurationSeconds"] == 15.0
    assert candidate["protagonistGoal"] is None
    assert candidate["objectOrPrimaryInteraction"] is None
    assert candidate["impossibleRuleOrCoreContradiction"] is None
    assert [(beat["start"], beat["end"]) for beat in _timeline(candidate["evaluationText"])] == [
        (0.0, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 12.0), (12.0, 15.0)
    ]
