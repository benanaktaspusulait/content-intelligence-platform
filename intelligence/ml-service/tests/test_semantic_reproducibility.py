from pathlib import Path

from app.semantic_reproducibility import (
    canonicalize_beats,
    request_fingerprint,
    validate_consistency,
)


def _selection(path: str) -> dict:
    return {
        "assetHash": "asset-a",
        "version": "semantic-frame-selection-v2",
        "temporalEvents": [{"eventId": "event-1", "startSeconds": 1.0}],
        "selectedFrames": [{
            "timestampSeconds": 0.0,
            "selectionReason": "OPENING_ANCHOR",
            "framePath": path,
            "frameAvailable": True,
        }],
    }


def test_fingerprint_is_stable_for_identical_effective_input(tmp_path: Path) -> None:
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"frame-v1")
    first, inputs = request_fingerprint(_selection(str(frame)), "openai", "gpt-test", "policy-v1", ["Child"])
    second, _ = request_fingerprint(_selection(str(frame)), "openai", "gpt-test", "policy-v1", ["Child"])

    assert first == second
    assert inputs["orderedFrames"][0]["frameHash"]


def test_fingerprint_changes_when_frame_order_or_bytes_change(tmp_path: Path) -> None:
    first_frame = tmp_path / "first.jpg"
    second_frame = tmp_path / "second.jpg"
    first_frame.write_bytes(b"first")
    second_frame.write_bytes(b"second")
    selection = _selection(str(first_frame))
    selection["selectedFrames"].append({
        "timestampSeconds": 1.0,
        "selectionReason": "V5_EVENT_DURING",
        "framePath": str(second_frame),
        "frameAvailable": True,
    })
    original, _ = request_fingerprint(selection, "openai", "gpt-test", "policy-v1", ["Child"])
    selection["selectedFrames"].reverse()
    reordered, _ = request_fingerprint(selection, "openai", "gpt-test", "policy-v1", ["Child"])
    assert original != reordered

    second_frame.write_bytes(b"second-changed")
    changed, _ = request_fingerprint(selection, "openai", "gpt-test", "policy-v1", ["Child"])
    assert reordered != changed


def test_fingerprint_includes_prompt_and_schema_versions(tmp_path: Path) -> None:
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"frame")
    selection = _selection(str(frame))
    baseline, _ = request_fingerprint(selection, "openai", "gpt-test", "policy-v1", ["Child"])
    prompt_changed, _ = request_fingerprint(selection, "openai", "gpt-test", "policy-v1", ["Child"], prompt_version="prompt-v-next")
    schema_changed, _ = request_fingerprint(selection, "openai", "gpt-test", "policy-v1", ["Child"], schema_version="schema-v-next")
    assert baseline != prompt_changed
    assert baseline != schema_changed


def test_canonicalizer_merges_only_adjacent_same_family_beats() -> None:
    base = {
        "primaryCharacter": "Child",
        "targetObject": "Box",
        "primaryAction": "push",
        "objectStateBefore": "still",
        "objectStateAfter": "moving",
        "consequence": "slides",
        "confidence": 0.9,
    }
    merged = canonicalize_beats([
        {**base, "startSeconds": 0, "endSeconds": 1, "supportingFrames": [0]},
        {**base, "startSeconds": 1, "endSeconds": 2, "confidence": 0.7, "supportingFrames": [1]},
        {**base, "startSeconds": 2, "endSeconds": 3, "primaryAction": "catch", "supportingFrames": [2]},
    ])
    assert len(merged) == 2
    assert merged[0]["endSeconds"] == 2
    assert merged[0]["confidence"] == 0.7
    assert merged[0]["supportingFrames"] == [0, 1]


def test_consistency_validator_preserves_unknown_and_flags_contradictions() -> None:
    questionable = validate_consistency({"opening": {}, "payoff": {"status": "UNKNOWN"}, "loop": {"status": "UNKNOWN"}})
    assert questionable["status"] == "QUESTIONABLE"
    invalid = validate_consistency({
        "opening": {"semanticHookReadability": "NOT_READABLE", "problemOrAnomalyReadable": True},
        "payoff": {"status": "COMPLETED", "payoffDetected": False, "stateChangeDetected": False},
        "loop": {"status": "CONSISTENT", "samePrimaryCharacter": False, "samePrimaryObject": False, "restartPlausibility": False},
    })
    assert invalid["status"] == "INVALID"
    assert len(invalid["contradictions"]) == 3
