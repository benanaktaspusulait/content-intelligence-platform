"""Asset-bound post-render QC. Technical inspection never invokes a provider.

Visual requirements are authored with the story, not inferred from a prompt score.
No semantic evaluator is authorized by default; missing evidence blocks approval.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import settings

VERSION = "story-video-qc-v1"
STATUSES = {"PASS", "FAIL", "UNCERTAIN", "NOT_EVALUATED"}


class VisualRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=10, max_length=4000)
    category: str = Field(min_length=1, max_length=100)
    startSeconds: float = Field(ge=0, le=120, allow_inf_nan=False)
    endSeconds: float = Field(ge=0, le=120, allow_inf_nan=False)
    mandatory: bool = True
    requiresMotion: bool = True
    referenceRequired: bool = False

    @model_validator(mode="after")
    def ordered(self):
        if self.endSeconds < self.startSeconds or (self.requiresMotion and self.endSeconds == self.startSeconds):
            raise ValueError("Motion requirements need a nonempty ordered time window")
        return self


class VisualAcceptanceContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["visual-acceptance-v1"]
    storyId: str = Field(min_length=1, max_length=200)
    storyRevision: str = Field(min_length=1, max_length=200)
    scope: Literal["OPENING_PROOF", "FULL_VIDEO"] = "FULL_VIDEO"
    loopIntended: bool = False
    requirements: list[VisualRequirement] = Field(min_length=1, max_length=40)
    sampleTimesSeconds: list[float] = Field(default_factory=list, max_length=120)
    canonicalReferences: list[dict[str, str]] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def complete(self):
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Requirement IDs must be unique")
        if not any(r.mandatory and r.requiresMotion for r in self.requirements):
            raise ValueError("At least one mandatory motion requirement is required")
        if any(not math.isfinite(t) or t < 0 or t > 120 for t in self.sampleTimesSeconds):
            raise ValueError("Invalid sample time")
        if self.scope == "FULL_VIDEO":
            expected = {"first-frame", "opening", "beat-order", "causality", "character-identity",
                        "object-continuity", "physical-rule", "payoff", "temporal-pacing"}
            if self.loopIntended:
                expected.add("loop-compatibility")
            missing = expected - {r.category for r in self.requirements if r.mandatory}
            if missing:
                raise ValueError("Full-video contract missing mandatory dimensions: " + ", ".join(sorted(missing)))
        return self


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def decision(checks: list[dict[str, Any]]) -> str:
    required = [c["status"] for c in checks if c.get("mandatory", True)]
    if "FAIL" in required:
        return "VIDEO_QC_FAIL"
    if not required or "NOT_EVALUATED" in required:
        return "VIDEO_QC_NOT_EVALUATED"
    if "UNCERTAIN" in required:
        return "VIDEO_QC_UNCERTAIN"
    return "VIDEO_QC_PASS"


def _check(id: str, status: str, reason: str, **evidence) -> dict[str, Any]:
    return {"id": id, "status": status, "mandatory": True, "reason": reason, **evidence}


def inspect_video(relative_path: str, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    # Reuse the established root confinement, metadata and streaming checksum implementation.
    from .video import probe, safe_video_path

    path = safe_video_path(relative_path)
    asset_hash = _digest(path)
    output = settings.data_root.resolve() / "video-qc" / asset_hash / str(uuid.uuid4())
    output.mkdir(parents=True)
    contract_hash = hashlib.sha256(json.dumps(contract or {}, sort_keys=True).encode()).hexdigest()
    checks: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "version": VERSION, "assetHash": asset_hash, "relativePath": relative_path,
        "contractHash": contract_hash, "contract": contract or {},
        "capturedAt": datetime.now(timezone.utc).isoformat(), "checks": checks,
        "frames": [], "motionWindows": [], "providerCalls": 0,
    }
    authored = None
    try:
        authored = VisualAcceptanceContract.model_validate(contract)
    except (ValueError, TypeError) as error:
        checks.append(_check("visual_contract", "NOT_EVALUATED", "Missing or invalid story visual acceptance contract: " + str(error)[:600]))
    try:
        metadata = probe(path)
        result["metadata"] = metadata.model_dump(by_alias=True)
        duration = metadata.duration_ms / 1000
        if not (0 < duration <= 120 and 0 < metadata.fps <= 120 and metadata.width * metadata.height <= 8294400):
            raise ValueError("Video exceeds bounded QC inspection limits (120s, 120fps, 8.3MP)")
        # Decode the whole stream, including unsampled portions, and reject decoder errors.
        decode = subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
            capture_output=True, timeout=60,
        )
        if decode.returncode:
            checks.append(_check("stream_decode", "FAIL", "FFmpeg could not decode the complete video stream"))
        else:
            checks.append(_check("stream_decode", "PASS", "Complete video stream decoded without errors"))
        # ffprobe PTS, not frame-number / nominal-FPS guesses, align all saved frames.
        pts_run = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames", "-show_entries",
             "frame=best_effort_timestamp_time", "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=45,
        )
        pts = [float(f["best_effort_timestamp_time"]) for f in json.loads(pts_run.stdout)["frames"]]
        if not pts or any(not math.isfinite(t) for t in pts) or any(b <= a for a, b in zip(pts, pts[1:])):
            raise ValueError("Missing or nonmonotonic decoded frame timestamps")
        origin = pts[0]
        pts = [t - origin for t in pts]
        targets = {0.0, *np.arange(0, duration, 1.0).tolist(), pts[-1]}
        windows = []
        if authored:
            targets.update(authored.sampleTimesSeconds)
            for r in authored.requirements:
                targets.update([r.startSeconds, r.endSeconds])
                if r.requiresMotion:
                    windows.append((r.id, r.startSeconds, r.endSeconds))
        # Generic imports still retain a contiguous opening for later story-bound evaluation.
        if not windows:
            windows = [("opening", 0, min(1, pts[-1]))]
        selected = {min(range(len(pts)), key=lambda i: abs(pts[i] - t)) for t in targets if t <= duration}
        for _, start, end in windows:
            selected.update(i for i, t in enumerate(pts) if start <= t <= end)
        cap = cv2.VideoCapture(str(path))
        frames = []
        dark, frozen, previous, count = [], [], None, 0
        try:
            for index, timestamp in enumerate(pts):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Frame decode ended early at index {index}")
                count += 1
                small = cv2.resize(frame, (96, 96))
                if float(small.mean()) < 4:
                    dark.append(timestamp)
                if previous is not None and np.array_equal(small, previous):
                    frozen.append(timestamp)
                previous = small
                if index not in selected:
                    continue
                scale = min(1, 480 / frame.shape[1])
                prepared = cv2.resize(frame, (round(frame.shape[1] * scale), round(frame.shape[0] * scale)))
                filename = output / f"frame-{index:05d}.jpg"
                if not cv2.imwrite(str(filename), prepared, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                    raise ValueError("Could not save frame evidence")
                frames.append({"index": index, "timestampSeconds": timestamp,
                               "framePath": str(filename), "frameHash": _digest(filename)})
        finally:
            cap.release()
        result["frames"] = frames
        result["technicalObservations"] = {"decodedFrames": count, "darkFrameTimes": dark, "identicalFrameTimes": frozen,
                                           "interpretation": "Darkness and holds are review signals, not semantic failures."}
        for id, start, end in windows:
            members = [f for f in frames if start <= f["timestampSeconds"] <= end]
            result["motionWindows"].append({"requirementId": id, "startSeconds": start, "endSeconds": end,
                                            "frameIndices": [f["index"] for f in members], "contiguous": True})
        anchors = [min(frames, key=lambda f: abs(f["timestampSeconds"] - t)) for t in sorted(targets) if t <= duration]
        tiles = []
        for f in anchors[:60]:
            im = cv2.imread(f["framePath"])
            im = cv2.resize(im, (240, round(im.shape[0] * 240 / im.shape[1])))
            tile = cv2.copyMakeBorder(im, 28, 0, 0, 0, cv2.BORDER_CONSTANT)
            cv2.putText(tile, f'{f["timestampSeconds"]:.3f}s', (8, 20), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            tiles.append(tile)
        columns = min(6, len(tiles))
        sheet = np.zeros((tiles[0].shape[0] * math.ceil(len(tiles) / columns), 240 * columns, 3), dtype=np.uint8)
        for i, tile in enumerate(tiles):
            y, x = (i // columns) * tile.shape[0], (i % columns) * 240
            sheet[y:y + tile.shape[0], x:x + 240] = tile
        sheet_path = output / "contact-sheet.jpg"
        cv2.imwrite(str(sheet_path), sheet)
        result["contactSheetPath"] = str(sheet_path)
        checks.append(_check("timestamped_pixels", "PASS", "PTS-aligned frames and contiguous motion windows saved"))
        if authored:
            if authored.scope == "FULL_VIDEO" and max(r.endSeconds for r in authored.requirements if r.mandatory) < duration - .15:
                checks.append(_check("full_video_coverage", "NOT_EVALUATED", "Mandatory story requirements do not cover the ending of the actual video"))
            checks.extend(_semantics(authored, result, duration))
    except subprocess.CalledProcessError:
        checks.append(_check("stream_decode", "FAIL", "Actual media could not be parsed/decoded by local video tools"))
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, StopIteration) as error:
        checks.append(_check("pixel_inspection", "NOT_EVALUATED", f"Inspection unavailable: {type(error).__name__}: {str(error)[:300]}"))
    if _digest(path) != asset_hash:
        checks.append(_check("asset_unchanged", "FAIL", "Video bytes changed during inspection"))
    result["status"] = decision(checks)
    result["approvalBlocked"] = result["status"] != "VIDEO_QC_PASS" or authored is None or authored.scope != "FULL_VIDEO"
    if authored and authored.scope == "OPENING_PROOF":
        result["approvalBlockReason"] = "Opening proofs do not evaluate the complete story and cannot authorize production"
    result["evidencePath"] = str(output / "result.json")
    Path(result["evidencePath"]).write_text(json.dumps(result, indent=2))
    return result


def _semantics(contract: VisualAcceptanceContract, result: dict[str, Any], duration: float) -> list[dict[str, Any]]:
    checks = [_check(r.id, "NOT_EVALUATED", "Story-aware visual evaluator is not authorized/configured",
                     mandatory=r.mandatory, window=[r.startSeconds, r.endSeconds]) for r in contract.requirements]
    for r, check in zip(contract.requirements, checks):
        if r.endSeconds > duration + .05:
            check.update(status="FAIL", reason="Required story event window exceeds actual rendered duration")
    # Server/operator opt-in, independent from possession of API credentials or caller input.
    if os.getenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", "false").lower() != "true":
        return checks
    frames = result["frames"]
    if len(frames) > 100:
        for c in checks:
            if c["status"] != "FAIL":
                c["reason"] = "Contiguous motion evidence exceeds single-call visual evaluator capacity (100 frames)"
        return checks
    try:
        from .llm import get_provider
        from .semantic_routing import SemanticModelRoutingPolicy

        selection = SemanticModelRoutingPolicy.from_environment().primary
        provider = get_provider(selection.provider, selection.model)
        references = []
        for ref in contract.canonicalReferences:
            root = settings.data_root.resolve()
            image = (root / ref["relativePath"]).resolve()
            if root not in image.parents or not image.is_file() or _digest(image) != ref["sha256"]:
                raise ValueError("Canonical image reference is unavailable or changed")
            references.append(str(image))
        prompt = (
            "Inspect these actual rendered frames IN TIMESTAMP ORDER against the authored visual contract. "
            "Use the contiguous frames to judge events and causality, not just counts. "
            "Do not infer success from instructions. If ambiguous use UNCERTAIN; if not observable use NOT_EVALUATED. "
            "Return JSON {checks:[{id,status:PASS|FAIL|UNCERTAIN|NOT_EVALUATED,reason,timestampsSeconds:[number,...]}]}. "
            "For each mandatory event establish its before, transition and after states inside its deadline. "
            "Preserve source-object identity, attachment, temporal order, prohibited alternatives and visibility. "
            "No story-specific requirement may be assumed. Canonical reference images follow all timed video frames. "
            + json.dumps({"contract": contract.model_dump(), "assetHash": result["assetHash"],
                          "frames": [{"timestampSeconds": f["timestampSeconds"], "frameHash": f["frameHash"]} for f in frames]})
        )
        result["providerCalls"] = 1
        raw, usage = provider.complete_images(prompt, [f["framePath"] for f in frames] + references,
                                              system="Return only JSON observations grounded in supplied pixels.", temperature=0)
        result["semanticProvenance"] = {"provider": selection.provider, "model": selection.model, "usage": usage}
        payload = json.loads(raw)
        observations = payload["checks"]
        if len({o["id"] for o in observations}) != len(observations):
            raise ValueError("Duplicate semantic requirement IDs")
        known = {f["timestampSeconds"] for f in frames}
        for r, c in zip(contract.requirements, checks):
            if c["status"] == "FAIL":
                continue
            if r.referenceRequired and not references:
                c["reason"] = "Required canonical reference pixels are unavailable"
                continue
            o = next((o for o in observations if o.get("id") == r.id), None)
            if not o or o.get("status") not in STATUSES or not str(o.get("reason", "")).strip():
                continue
            timestamps = o.get("timestampsSeconds", [])
            valid = (isinstance(timestamps, list) and bool(timestamps)
                     and all(isinstance(t, (int, float)) and t in known and r.startSeconds - .05 <= t <= r.endSeconds + .05 for t in timestamps))
            if o["status"] in {"PASS", "FAIL"} and (not valid or (r.requiresMotion and len(set(timestamps)) < 3)):
                c["reason"] = "Evaluator did not supply enough valid time-aligned motion evidence"
                continue
            c.update(status=o["status"], reason=o["reason"], timestampsSeconds=timestamps)
    except Exception as error:
        result["semanticError"] = type(error).__name__  # Never persist provider exception text/credentials.
    return checks
