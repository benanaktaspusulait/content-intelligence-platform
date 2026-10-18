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


def test_existing_production_intent_is_bound_without_inventing_a_timeline():
    source = {"promptVersion": "7", "intent": {"timingIntent": [
        {"id": "a", "startTime": 0, "endTime": .5, "action": "Attempt transfer", "consequence": "Object duplicates"},
        {"id": "b", "startTime": .5, "endTime": 1.5, "action": "Stop and react", "consequence": "Both objects remain"}],
        "mechanicIntent": {"rule": "transfer duplicates"}, "payoffIntent": {"action": "stop"}}}
    normalized = video_qc.VisualAcceptanceContract.model_validate(video_qc.normalize_contract(source))
    assert normalized.scope == "FULL_VIDEO"
    assert normalized.storyRevision == "7"
    assert normalized.requirements[0].endSeconds == .5
    assert "Object duplicates" in normalized.requirements[0].description
    assert video_qc.normalize_contract({"intent": {}}) == {"intent": {}}


def test_full_duration_evidence_fits_existing_single_call_budget(clip, monkeypatch):
    # Transport regression, not a claim about the visual contents of the fixture.
    frames = [{"index": i, "timestampSeconds": i / 24, "framePath": str(clip), "frameHash": "test"} for i in range(361)]
    c = contract()
    c["requirements"][0]["endSeconds"] = 15
    selected = video_qc.semantic_frames(video_qc.VisualAcceptanceContract.model_validate(c), frames)
    assert 3 <= len(selected) <= 100
    assert selected[0]["timestampSeconds"] == 0
    assert selected[-1]["timestampSeconds"] == 15
    assert max(b["timestampSeconds"] - a["timestampSeconds"] for a, b in zip(selected, selected[1:])) <= .251


def test_unavailable_story_is_prominent_and_never_motion_pass(clip):
    result = video_qc.inspect_video(clip.name, contract())
    assert result["storyStatus"] == "STORY_QC_NOT_EVALUATED"
    assert result["storyChecks"][0]["id"] == "event"
    assert result["storyBinding"]["storyId"] == "unit-transport-only"
    assert result["approvalBlocked"]


def test_ambiguous_or_contradictory_temporal_pixels_propagate_story_verdict(clip, monkeypatch):
    monkeypatch.setenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", "true")
    for status in ("FAIL", "UNCERTAIN"):
        provider = Mock()
        provider.complete_images.return_value = (json.dumps({"checks": [{"id": "event", "status": status,
            "reason": "Adapter transport test, not a real visual finding", "timestampsSeconds": [0, .25, .5]}]}), {})
        with patch("app.llm.get_provider", return_value=provider):
            result = video_qc.inspect_video(clip.name, contract())
        assert result["storyStatus"] == f"STORY_QC_{status}"
        assert result["approvalBlocked"]
        assert result["semanticFrames"]
        assert result["semanticMotionWindows"][0]["sampling"] == "TIMESTAMPED_WINDOW_SEQUENCE"


def test_actual_mimi_import_http_retains_all_story_windows_without_paid_calls(tmp_path, monkeypatch):
    """Real pixels; no mocked or hardcoded semantic verdict about those pixels."""
    import shutil
    from fastapi.testclient import TestClient
    from app.main import app
    root = Path(__file__).resolve().parents[3]
    source = root / "intelligence/docs/mimi-single-take-15s/mimi-openart-original-15s.mp4"
    if not source.exists():
        pytest.skip("Owner's real Mimi regression asset is not installed")
    c = json.loads((Path(__file__).parent / "fixtures/video-qc/mimi-full-story.json").read_text())
    for ref in c["canonicalReferences"]:
        shutil.copyfile(root / ref["relativePath"], tmp_path / "approved.png")
        ref["relativePath"] = "approved.png"
    shutil.copyfile(source, tmp_path / "mimi.mp4")
    monkeypatch.setattr(video_qc.settings, "data_root", tmp_path)
    monkeypatch.setenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", "false")
    with patch("app.llm.get_provider", side_effect=AssertionError("No paid evaluator is authorized")):
        response = TestClient(app).post("/v1/analysis/video-qc", json={"relativePath": "mimi.mp4", "visualAcceptanceContract": c})
    assert response.status_code == 200
    result = response.json()
    assert result["assetHash"] == video_qc._digest(source)
    assert result["technicalObservations"]["decodedFrames"] == 361
    assert result["storyStatus"] == "STORY_QC_NOT_EVALUATED"
    assert result["approvalBlocked"] and result["providerCalls"] == 0
    assert len(result["motionWindows"]) == 11
    assert {c["id"] for c in result["storyChecks"]} == {r["id"] for r in c["requirements"]}
    assert len(video_qc.semantic_frames(video_qc.VisualAcceptanceContract.model_validate(c), result["frames"])) + len(c["canonicalReferences"]) <= 100
