from app.parser.prompt_parser import PromptParser


def test_mimi_timeline_preserves_two_digit_ranges_and_exact_quotes():
    prompt = """TITLE / FORMAT: Mimi's Sticky Note Mystery / ANIMATION (15s, 9:16)
TIMED SHOT PLAN
0-3s: Mimi stands in front of a cabinet.
3-6s: The note flips and sticks to her face.
6-10s: She peels it off.
10-13s: Notes multiply.
13-15s: Notes cover Mimi completely.
AUDIO: playful music
NEGATIVE CONSTRAINTS: no other characters
FINAL CUT: hard cut.
"""
    result = PromptParser().parse(prompt)
    beats = result["videoPlanIR"]["beats"]

    assert [(beat["startTime"], beat["endTime"]) for beat in beats] == [
        (0.0, 3.0),
        (3.0, 6.0),
        (6.0, 10.0),
        (10.0, 13.0),
        (13.0, 15.0),
    ]
    assert beats[-1]["sourceQuote"] == "13-15s: Notes cover Mimi completely."
    assert beats[-1]["evidenceStatus"] == "SOURCE_VERIFIED"
    assert all(0 <= beat["startTime"] < beat["endTime"] <= 15 for beat in beats)
    assert all("AUDIO:" not in beat["sourceQuote"] for beat in beats)


def test_overlapping_timeline_is_not_promoted_to_verified_evidence():
    result = PromptParser().parse("""ANIMATION (15s)
TIMED SHOT PLAN
0-3s: Opening.
2-5s: Overlapping continuation.
5-15s: Ending.
""")
    beats = result["videoPlanIR"]["beats"]
    assert [(beat["startTime"], beat["endTime"]) for beat in beats] == [
        (0.0, 3.0),
        (5.0, 15.0),
    ]
    assert any("Overlapping time range" in warning for warning in result["parserMetadata"]["warnings"])
