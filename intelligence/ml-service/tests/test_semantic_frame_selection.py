from app.semantic_evidence import unavailable_semantic_evidence
from app.semantic_frame_selector import _deduplicate


def test_frame_selection_keeps_opening_event_and_ending_provenance() -> None:
    selected = _deduplicate(
        [
            {"timestampSeconds": 0.0, "selectionReason": "OPENING_ANCHOR"},
            {"timestampSeconds": 0.5, "selectionReason": "OPENING_ANCHOR"},
            {"timestampSeconds": 4.0, "selectionReason": "V5_EVENT_DURING", "relatedEventId": "event-1"},
            {"timestampSeconds": 9.5, "selectionReason": "ENDING_ANCHOR"},
        ],
        max_frames=14,
        duration=10.0,
    )

    assert [item["timestampSeconds"] for item in selected] == [0.0, 0.5, 4.0, 9.5]
    assert selected[2]["relatedEventId"] == "event-1"


def test_unavailable_semantic_evidence_is_explicit() -> None:
    evidence = unavailable_semantic_evidence(
        video_id="video-1",
        asset_hash="hash-1",
        frame_selection={"version": "semantic-frame-selection-v1", "selectedFrames": []},
    )

    assert evidence["status"] == "NOT_EVALUATED"
    assert evidence["semanticCoverage"] == "NONE"
    assert evidence["opening"]["status"] == "UNKNOWN"
    assert evidence["provenance"]["selectedFrameTimestamps"] == []
