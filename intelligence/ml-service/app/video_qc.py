"""Asset-bound post-render QC. Technical inspection never invokes a provider.

Viewer experience is primary; source-plan fidelity is a separate diagnostic.
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

VERSION = "story-video-qc-v2"
EVALUATION_POLICY = "audience-first-simple-v1"
STATUSES = {"PASS", "FAIL", "UNCERTAIN", "NOT_EVALUATED"}

CREATIVE_DIMENSIONS = {
    "hook": "Would the first 1-2 seconds stop scrolling? Consider surprise, curiosity, appeal, action and comprehension.",
    "engagement": "Does interest hold through development and escalation? Consider reactions, suspense, pacing, rhythm and dead time, not constant motion.",
    "payoff": "Does the ending reward watching through surprise, humor, satisfaction, curiosity or a compelling unresolved moment? Comedy and a happy ending are optional.",
    "rewatch": "Is there a plausible reason to intentionally rewatch or share, for adults and parent-to-child viewing? Distinguish enjoyment/curiosity from confusion; a seamless loop is optional.",
}


def _creative_result(payload: dict[str, Any], frames: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    """One four-question owner review; no numerical creative or audience score."""
    unavailable = dict(status="CREATIVE_REVIEW_NOT_EVALUATED", recommendation="NOT_EVALUATED",
        reason="No grounded creative review is available", basis="QUALITATIVE_VIEWER_EXPERIENCE",
        audienceOutcomes="NOT_MEASURED", dimensions=[dict(id=id, rating="UNKNOWN") for id in CREATIVE_DIMENSIONS],
        observations=[], biggestWeakness="UNKNOWN", actionableRecommendation="Authorize one visual review or make an explicit owner decision")
    if not isinstance(payload, dict) or payload.get("recommendation") == "NOT_EVALUATED":
        return unavailable
    if payload.get("recommendation") not in {"PUBLISH", "REVIEW", "REJECT"}:
        return unavailable
    dimensions = payload.get("dimensions", [])
    if (not isinstance(dimensions, list) or len(dimensions) != 4 or
        any(not isinstance(d, dict) or d.get("id") not in CREATIVE_DIMENSIONS or
            d.get("rating") not in {"STRONG", "MODERATE", "WEAK", "UNKNOWN"} for d in dimensions) or
        len({d["id"] for d in dimensions}) != 4):
        return unavailable
    observations = payload.get("observations", [])
    if not isinstance(observations, list) or not 1 <= len(observations) <= 3:
        return unavailable
    known = {f["timestampSeconds"] for f in frames}
    cited = set()
    for o in observations:
        if not isinstance(o, dict) or not isinstance(o.get("description"), str) or not o["description"].strip():
            return unavailable
        times = o.get("timestampsSeconds", [])
        if not isinstance(times, list) or not times or not all(not isinstance(t, bool) and isinstance(t, (int,float))
                and t in known and 0 <= t <= duration + .05 for t in times):
            return unavailable
        cited.update(times)
    # A full-video recommendation needs opening, middle and ending evidence.
    if (len(cited) < 3 or not any(t <= min(2, duration / 3) for t in cited)
        or not any(duration / 3 <= t <= duration * 2 / 3 for t in cited)
        or not any(t >= duration - min(2, duration / 3) - .05 for t in cited)):
        return unavailable
    if any(not isinstance(payload.get(k), str) or not payload[k].strip()
           for k in ["reason", "biggestWeakness", "actionableRecommendation"]):
        return unavailable
    if all(d["rating"] == "UNKNOWN" for d in dimensions):
        return unavailable
    recommendation = payload["recommendation"]
    if recommendation == "PUBLISH" and any(d["rating"] == "UNKNOWN" for d in dimensions):
        recommendation = "REVIEW"
    return dict(status="CREATIVE_REVIEW_EVALUATED", recommendation=recommendation, reason=payload["reason"],
        dimensions=[dict(id=d["id"], rating=d["rating"]) for d in dimensions],
        observations=[dict(description=o["description"], timestampsSeconds=o["timestampsSeconds"]) for o in observations],
        biggestWeakness=payload["biggestWeakness"], actionableRecommendation=payload["actionableRecommendation"],
        basis="QUALITATIVE_VIEWER_EXPERIENCE", audienceOutcomes="NOT_MEASURED")


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


def normalize_contract(source: dict[str, Any] | None) -> dict[str, Any] | None:
    """Reuse the immutable production intent when no explicit visual contract was authored."""
    if not isinstance(source, dict) or source.get("version") == "visual-acceptance-v1":
        return source
    intent = source.get("intent", source)
    if not isinstance(intent, dict):
        return source
    explicit = intent.get("visualAcceptanceContract")
    if isinstance(explicit, dict):
        return explicit
    beats = intent.get("timingIntent", intent.get("beats", []))
    if not isinstance(beats, list) or not beats:
        return source  # No invented timeline or story binding.
    requirements = []
    for i, beat in enumerate(beats):
        start = beat.get("startTime", beat.get("startSeconds"))
        end = beat.get("endTime", beat.get("endSeconds"))
        action = beat.get("action", beat.get("description"))
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not action:
            return source
        requirements.append(dict(id=f"beat-{i + 1}", category="beat-order", startSeconds=start,
                                 endSeconds=end, description="Required timed action and consequence: " + json.dumps(beat)))
    end = max(r["endSeconds"] for r in requirements)
    opening_end = min(end, requirements[0]["endSeconds"])
    dimensions = {
        "first-frame": (0, 0, intent.get("openingIntent", intent.get("hook", {}))),
        "opening": (0, opening_end, intent.get("openingIntent", intent.get("hook", {}))),
        "causality": (0, end, "Each required action must visibly cause its required consequence; do not infer missing events."),
        "physical-rule": (0, end, intent.get("mechanicIntent", intent.get("coreMechanic", {}))),
        "character-identity": (0, end, intent.get("characterIntent", intent.get("characters", {}))),
        "object-continuity": (0, end, "Objects and attachment states must remain continuous across the required beats."),
        "payoff": (requirements[-1]["startSeconds"], end, intent.get("payoffIntent", intent.get("finalPayoff", {}))),
        "temporal-pacing": (0, end, "Required events must remain readable in their authored windows without unexplained stalls."),
    }
    loop = intent.get("loopIntent", intent.get("loop", {}))
    loop_intended = isinstance(loop, dict) and loop.get("loopsToOpening") is True
    if loop_intended:
        dimensions["loop-compatibility"] = (0, end, loop)
    for category, (start, stop, expected) in dimensions.items():
        requirements.append(dict(id=category, category=category, startSeconds=start, endSeconds=stop,
                                 requiresMotion=stop > start,
                                 description="Compare actual temporal pixels against source intent: " + json.dumps(expected)))
    digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    return dict(version="visual-acceptance-v1", scope="FULL_VIDEO", storyId="source-plan:" + digest,
                storyRevision=str(source.get("promptVersion", source.get("videoPlanVersion", digest))),
                loopIntended=loop_intended, requirements=requirements)


def semantic_frames(contract: VisualAcceptanceContract | None, frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bound one existing vision call while retaining before/during/after per timed window.

    Full contiguous evidence stays on disk. Sent pixels cover the entire clip at
    roughly 4Hz, with denser authored opening/event anchors, capped at 100 images.
    """
    selected = {}
    budget = 100 - (len(contract.canonicalReferences) if contract else 0)
    def add(t):
        frame = min(frames, key=lambda f: abs(f["timestampSeconds"] - t))
        if len(selected) < budget or frame["index"] in selected:
            selected[frame["index"]] = frame
    end = frames[-1]["timestampSeconds"]
    for t in [0, .25, .5, .75, 1]:
        add(min(t, end))
    for t in np.linspace(0, end, min(65, max(3, math.ceil(end * 4) + 1))):
        add(t)
    for r in contract.requirements if contract else []:
        for t in np.linspace(r.startSeconds, r.endSeconds, 3 if r.requiresMotion else 1):
            add(t)
    for t in (contract.sampleTimesSeconds if contract else [0, .25, .5, .75, 1]):
        add(min(t, end))
    return sorted(selected.values(), key=lambda f: f["timestampSeconds"])


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
        "version": VERSION, "evaluationPolicy": EVALUATION_POLICY, "assetHash": asset_hash, "relativePath": relative_path,
        "contractHash": contract_hash, "contract": contract or {},
        "capturedAt": datetime.now(timezone.utc).isoformat(), "checks": checks,
        "frames": [], "motionWindows": [], "providerCalls": 0,
        "creativeAssessment": _creative_result({}, [], 0), "evaluationScope": "FULL_VIDEO",
    }
    authored = None
    try:
        authored = VisualAcceptanceContract.model_validate(normalize_contract(contract))
        result["evaluatedContract"] = authored.model_dump()
        result["storyBinding"] = {"storyId": authored.storyId, "storyRevision": authored.storyRevision,
                                  "contractHash": contract_hash, "scope": authored.scope}
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
        # Viewer evaluation covers the actual duration even when the source plan ends earlier.
        if not windows:
            windows = [("viewer-experience", 0, pts[-1])]
        elif authored:
            windows.append(("viewer-experience", 0, pts[-1]))
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
    story_checks = [c for c in checks if c["id"] not in {"stream_decode", "timestamped_pixels", "pixel_inspection", "asset_unchanged"}]
    result["storyStatus"] = decision(story_checks).replace("VIDEO_QC_", "STORY_QC_")
    result["storyChecks"] = story_checks
    result["promptFidelityStatus"] = result["storyStatus"].replace("STORY_QC_", "PROMPT_FIDELITY_")
    result["creativeStatus"] = result["creativeAssessment"]["status"]
    technical = [c for c in checks if c["id"] in {"stream_decode", "timestamped_pixels", "pixel_inspection", "asset_unchanged"}]
    result["technicalStatus"] = decision(technical).replace("VIDEO_QC_", "TECHNICAL_QC_")
    result["creativeRecommendation"] = result["creativeAssessment"]["recommendation"]
    result["status"] = decision(technical)
    result["approvalBlocked"] = result["technicalStatus"] == "TECHNICAL_QC_FAIL"
    result["automaticPublishingAllowed"] = False
    result["ownerDecisionRequired"] = True
    if authored and authored.scope == "OPENING_PROOF":
        result["scopeNote"] = "Source plan describes an opening proof; creative advice reviews the actual supplied clip"
    result["evidencePath"] = str(output / "result.json")
    Path(result["evidencePath"]).write_text(json.dumps(result, indent=2))
    return result


def _semantics(contract: VisualAcceptanceContract | None, result: dict[str, Any], duration: float) -> list[dict[str, Any]]:
    checks = [_check(r.id, "NOT_EVALUATED", "Story-aware visual evaluator is not authorized/configured",
                     mandatory=r.mandatory, window=[r.startSeconds, r.endSeconds],
                     viewerImpact="UNCERTAIN", departureKind="UNCERTAIN") for r in contract.requirements] if contract else []
    for r, check in zip(contract.requirements if contract else [], checks):
        if r.endSeconds > duration + .05:
            check.update(status="FAIL", timingDeviation=True, reason="Source-plan event window exceeds actual rendered duration; viewer impact is evaluated separately")
    # Server/operator opt-in, independent from possession of API credentials or caller input.
    if os.getenv("POMPOM_VIDEO_QC_SEMANTIC_AUTHORIZED", "false").lower() != "true":
        result["creativeAssessment"]["reason"] = "Semantic viewer-experience evaluation is not authorized/configured; no creative verdict inferred from motion or fidelity"
        return checks
    for check in checks:
        if check["status"] != "FAIL":
            check["reason"] = "Evaluator did not return usable timestamped evidence for this requirement"
    try:
        frames = semantic_frames(contract, result["frames"])
        result["semanticFrames"] = frames
        result["semanticMotionWindows"] = [{**w, "frameIndices": [f["index"] for f in frames
            if w["startSeconds"] <= f["timestampSeconds"] <= w["endSeconds"]], "contiguous": False,
            "sampling": "TIMESTAMPED_WINDOW_SEQUENCE"} for w in result["motionWindows"]]
        from .llm import get_provider
        from .semantic_routing import SemanticModelRoutingPolicy

        selection = SemanticModelRoutingPolicy.from_environment().primary
        provider = get_provider(selection.provider, selection.model)
        references = []
        for ref in contract.canonicalReferences if contract else []:
            root = settings.data_root.resolve()
            image = (root / ref.get("relativePath", "")).resolve()
            if root not in image.parents or not image.is_file() or _digest(image) != ref.get("sha256"):
                result.setdefault("referenceLimitations", []).append("Source-plan reference unavailable; canonical fidelity cannot be verified")
                continue
            references.append(str(image))
        prompt = (
            "Evaluate the actual video as a standalone viewer experience FIRST. The audience never sees its prompt. "
            "Assess scroll-stop impact, immediate comprehension, curiosity, meaningful escalation, reactions, pacing/dead time, "
            "surprise/satisfaction, intentional replay potential, animation and parent-to-child shareability. "
            "These are qualitative creative hypotheses, NOT measured engagement, retention, completion, rewatches or shares. "
            "Do not invent audience data, numeric creative scores or success probabilities. "
            "Do not require comedy, a traditional resolution or a seamless loop. "
            "An engaging departure can be better than boring compliance. Judge the overall experience holistically; "
            "one weak or inapplicable dimension does not automatically fail it. "
            "SECOND, compare source-plan requirements diagnostically. Counts, timing, ordering and changed endings are not creative failures by themselves. "
            "For each deviation describe its viewer impact as IMPROVES, HARMS, NEUTRAL or UNCERTAIN and "
            "its kind as CREATIVE_DEPARTURE, GENERATION_DEFECT or UNCERTAIN. Do not infer author intention from pixels alone. "
            "Use timestamped sequences within each window, not isolated counts. Samples are not every consecutive frame; "
            "use UNCERTAIN for hidden transitions. References follow timed video frames. "
            "Return JSON {creativeAssessment:{recommendation:PUBLISH|REVIEW|REJECT|NOT_EVALUATED,reason,biggestWeakness,actionableRecommendation,"
            "observations:[{description,timestampsSeconds:[number,...]}],dimensions:[{id,rating:STRONG|MODERATE|WEAK|UNKNOWN}]},"
            "checks:[{id,status:PASS|FAIL|UNCERTAIN|NOT_EVALUATED,reason,timestampsSeconds:[number,...],"
            "viewerImpact:IMPROVES|HARMS|NEUTRAL|UNCERTAIN,departureKind:CREATIVE_DEPARTURE|GENERATION_DEFECT|UNCERTAIN}]}. "
            "Answer only FOUR core creative questions. Give at most THREE concrete observations with supplied timestamps covering opening, development/escalation and ending, "
            "the biggest creative weakness and ONE actionable recommendation. Hook concerns 0-2 seconds. "
            "A recommendation is decision support, never publishing authorization. Use NOT_EVALUATED when scene understanding is unavailable. "
            "Source-plan checks are optional diagnostics; incomplete diagnostics must not prevent useful creative feedback. "
            + json.dumps({"creativeDimensions": CREATIVE_DIMENSIONS,
                          "sourcePlanForDiagnosticsOnly": contract.model_dump() if contract else None,
                          "assetHash": result["assetHash"], "motionWindows": result["semanticMotionWindows"],
                          "frames": [{"timestampSeconds": f["timestampSeconds"], "frameHash": f["frameHash"]} for f in frames]})
        )
        result["providerCalls"] = 1
        raw, usage = provider.complete_images(prompt, [f["framePath"] for f in frames] + references,
                                              system="Return only JSON observations grounded in supplied pixels.", temperature=0)
        result["semanticProvenance"] = {"provider": selection.provider, "model": selection.model, "usage": usage,
                                         "framesSent": len(frames), "contractHash": result["contractHash"]}
        payload = json.loads(raw)
        result["creativeAssessment"] = _creative_result(payload.get("creativeAssessment", {}), frames, duration)
        observations = payload.get("checks", [])
        if len({o["id"] for o in observations}) != len(observations):
            raise ValueError("Duplicate semantic requirement IDs")
        known = {f["timestampSeconds"] for f in frames}
        for r, c in zip(contract.requirements if contract else [], checks):
            if r.referenceRequired and not references:
                c["reason"] = "Required canonical reference pixels are unavailable"
                continue
            o = next((o for o in observations if o.get("id") == r.id), None)
            if not o or o.get("status") not in STATUSES or not str(o.get("reason", "")).strip():
                continue
            timestamps = o.get("timestampsSeconds", [])
            valid = (isinstance(timestamps, list) and bool(timestamps)
                     and all(not isinstance(t, bool) and isinstance(t, (int, float)) and t in known and 0 <= t <= duration + .05 for t in timestamps))
            if o["status"] in {"PASS", "FAIL", "UNCERTAIN"} and (not valid or (r.requiresMotion and len(set(timestamps)) < 3)):
                c["reason"] = "Evaluator did not supply enough valid time-aligned motion evidence"
                continue
            c.update(status="FAIL" if c.get("timingDeviation") else o["status"], reason=o["reason"], timestampsSeconds=timestamps,
                     viewerImpact=o.get("viewerImpact") if o.get("viewerImpact") in {"IMPROVES", "HARMS", "NEUTRAL"} else "UNCERTAIN",
                     departureKind=o.get("departureKind") if o.get("departureKind") in {"CREATIVE_DEPARTURE", "GENERATION_DEFECT"} else "UNCERTAIN")
    except Exception as error:
        result["semanticError"] = type(error).__name__  # Never persist provider exception text/credentials.
        if result["creativeAssessment"]["status"] == "CREATIVE_REVIEW_NOT_EVALUATED":
            result["creativeAssessment"]["reason"] = "Creative evaluator unavailable: " + type(error).__name__
        for check in checks:
            if check["status"] == "NOT_EVALUATED":
                check["reason"] = "Story-aware visual evaluator unavailable: " + type(error).__name__
    return checks
