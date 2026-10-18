"""QC orchestration tests; mock semantics here are NOT visual regression conclusions."""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest

from app import video_qc


@pytest.fixture
def clip(tmp_path, monkeypatch):
    monkeypatch.setattr(video_qc.settings, "data_root", tmp_path)
    monkeypatch.delenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", raising=False)
    path = tmp_path / "fixture.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (96, 160))
    for i in range(36):
        frame = np.full((160, 96, 3), 150, dtype=np.uint8)
        cv2.circle(frame, (20 + i, 60), 10, (10, 50, 180), -1)
        writer.write(frame)
    writer.release()
    return path


def contract():
    return {"version": "visual-acceptance-v1", "storyId": "unit-transport-only", "storyRevision": "1", "scope": "OPENING_PROOF",
            "sampleTimesSeconds": [0, .15, .3, .5, .75, 1],
            "requirements": [{"id": "event", "description": "Observe an authored causal visual event",
                              "category": "causality", "startSeconds": 0, "endSeconds": .5}]}


def test_local_decode_does_not_authorize_semantics_or_approval(clip):
    with patch("app.llm.get_provider", side_effect=AssertionError("No provider may be constructed")):
        result = video_qc.inspect_video(clip.name, contract())
    assert result["status"] == "VIDEO_QC_NOT_EVALUATED"
    assert result["approvalBlocked"] is True
    assert result["providerCalls"] == 0
    assert result["technicalObservations"]["decodedFrames"] == 36
    assert result["motionWindows"][0]["contiguous"] is True
    assert result["motionWindows"][0]["frameIndices"] == list(range(13))
    times = [f["timestampSeconds"] for f in result["frames"]]
    for t in [0, .15, .3, .5, .75, 1]:
        assert min(abs(x - t) for x in times) <= 1 / 24
    assert Path(result["contactSheetPath"]).is_file()
    assert json.loads(Path(result["evidencePath"]).read_text())["assetHash"] == video_qc._digest(clip)


def test_missing_story_contract_cannot_pass(clip):
    result = video_qc.inspect_video(clip.name)
    assert result["status"] == "VIDEO_QC_NOT_EVALUATED"
    assert result["checks"][0]["id"] == "visual_contract"
    assert result["frames"]


def test_short_render_contradicts_required_story_timing(clip):
    c = contract()
    c["requirements"][0]["endSeconds"] = 15
    result = video_qc.inspect_video(clip.name, c)
    assert result["status"] == "VIDEO_QC_FAIL"
    assert "exceeds" in result["checks"][-1]["reason"]


def test_unreadable_pixels_are_not_a_valid_format_pass(clip):
    clip.write_bytes(b"not a video")
    result = video_qc.inspect_video(clip.name, contract())
    assert result["status"] == "VIDEO_QC_FAIL"
    assert result["approvalBlocked"]


@pytest.mark.parametrize("bad", ["../outside.mp4", "/etc/passwd"])
def test_inspection_cannot_escape_media_root(clip, bad):
    with pytest.raises(ValueError):
        video_qc.inspect_video(bad, contract())


@pytest.mark.parametrize("status", ["PASS", "FAIL", "UNCERTAIN"])
def test_authorized_adapter_status_is_bound_to_actual_frame_evidence(clip, monkeypatch, status):
    monkeypatch.setenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", "true")
    provider = Mock()
    provider.complete_images.return_value = (json.dumps({"checks": [{"id": "event", "status": status,
        "reason": "Mock adapter response, not a real visual conclusion", "timestampsSeconds": [0, .25, .5]}]}), {})
    with patch("app.llm.get_provider", return_value=provider):
        result = video_qc.inspect_video(clip.name, contract())
    assert result["status"] == f"VIDEO_QC_{status}"
    assert result["providerCalls"] == 1
    provider.complete_images.assert_called_once()


def test_fabricated_or_insufficient_motion_timestamps_cannot_pass(clip, monkeypatch):
    monkeypatch.setenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", "true")
    provider = Mock()
    provider.complete_images.return_value = (json.dumps({"checks": [{"id": "event", "status": "PASS",
        "reason": "Unsubstantiated claim", "timestampsSeconds": [0, .12345, .5]}]}), {})
    with patch("app.llm.get_provider", return_value=provider):
        result = video_qc.inspect_video(clip.name, contract())
    assert result["status"] == "VIDEO_QC_NOT_EVALUATED"


def test_mimi_contract_is_data_not_a_special_case_in_engine():
    c = video_qc.VisualAcceptanceContract.model_validate_json(
        (Path(__file__).parent / "fixtures/video-qc/mimi-sticky-notes.json").read_text())
    assert c.sampleTimesSeconds == [0, .15, .3, .5, .75, 1]
    assert any(r.id == "not-paper-separation" for r in c.requirements)


def test_duplicate_requirement_ids_are_rejected():
    c = contract()
    c["requirements"] *= 2
    with pytest.raises(ValueError):
        video_qc.VisualAcceptanceContract.model_validate(c)
