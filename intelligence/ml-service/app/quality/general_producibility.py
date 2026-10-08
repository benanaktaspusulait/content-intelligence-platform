"""Family 10: pure, generator-agnostic production feasibility projection.

Consumes explicit video-plan dependencies, never historical performance, legacy
keyword complexity scores, or a particular provider's execution behavior. Missing
risk evidence remains UNKNOWN. This projection has no rule/scoring/admission side
effects: the frozen authorization policy continues to consume its existing rules.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from .canonical_evidence import temporal_generation_load_evidence

GENERAL_PRODUCIBILITY_VERSION = "general-producibility-v1"
GENERAL_PRODUCIBILITY_STATUSES = (
    "PRODUCIBLE",
    "RISKY",
    "NOT_PRODUCIBLE",
    "UNKNOWN",
    "NOT_APPLICABLE",
)
GENERAL_PRODUCIBILITY_DIMENSIONS = (
    "ENTITY_LOAD",
    "OBJECT_IDENTITY_CONTINUITY",
    "CHARACTER_IDENTITY_CONTINUITY",
    "FINE_MOTOR_PRECISION",
    "CONTACT_PHYSICS_COMPLEXITY",
    "OCCLUSION_HIDDEN_STATE",
    "EXACT_COUNT_DEPENDENCY",
    "MULTI_ENTITY_CONCURRENCY",
    "TRANSFORMATION_COMPLEXITY",
    "LIQUID_CLOTH_PARTICLE",
    "SPATIAL_RELATIONSHIP_COMPLEXITY",
    "CAMERA_ACTION_COUPLING",
    "MULTI_SCENE_CONTINUITY",
    "TEXT_LIP_SYNC_SYMBOL",
    "SEGMENT_CONTINUITY",
)
_RANK = {"UNKNOWN": -1, "NOT_APPLICABLE": -1, "LOW": 0, "MODERATE": 1, "HIGH": 2}
_DEPENDENCIES = {
    "OBJECT_IDENTITY_CONTINUITY": ("objectContinuity",),
    "CHARACTER_IDENTITY_CONTINUITY": ("characterContinuity",),
    "FINE_MOTOR_PRECISION": ("fineMotorRequirement",),
    "CONTACT_PHYSICS_COMPLEXITY": ("contactPhysicsRequirement",),
    "OCCLUSION_HIDDEN_STATE": ("occlusionRequirement",),
    "EXACT_COUNT_DEPENDENCY": ("exactCountDependency",),
    "TRANSFORMATION_COMPLEXITY": ("transformationRequirement",),
    "LIQUID_CLOTH_PARTICLE": ("simulationRequirement",),
    "SPATIAL_RELATIONSHIP_COMPLEXITY": ("spatialRequirement",),
    "MULTI_SCENE_CONTINUITY": ("sceneContinuityRequirement",),
    "TEXT_LIP_SYNC_SYMBOL": ("textRequirement", "dialogueRequirement", "symbolRequirement"),
    "SEGMENT_CONTINUITY": ("segmentContinuityRequirement",),
}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _names(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value} if value.strip() else set()
    if isinstance(value, (list, tuple)):
        return {item for item in value if isinstance(item, str) and item.strip()}
    return set()


def _row(
    level: str, reason: str, references: list[str], *, material: bool = False, redesign: bool = False
) -> dict[str, Any]:
    return {
        "level": level,
        "reason": reason,
        "evidenceReferences": list(dict.fromkeys(references)),
        "material": material,
        "requiresRedesign": redesign,
    }


def _raise(
    rows: dict[str, dict[str, Any]],
    key: str,
    level: str,
    reason: str,
    references: list[str],
    *,
    material: bool = True,
    redesign: bool = False,
) -> None:
    previous = rows[key]
    if _RANK[level] >= _RANK[previous["level"]]:
        rows[key] = _row(
            level,
            reason,
            previous["evidenceReferences"] + references,
            material=material or previous["material"],
            redesign=redesign or previous["requiresRedesign"],
        )


def _precision(requirement: dict[str, Any]) -> str:
    precision = str(requirement.get("precision") or requirement.get("complexity") or "").upper()
    if precision in {"HIGH", "EXACT", "TINY_PINCHING_THREADING", "INTRICATE"}:
        return "HIGH"
    if precision in {"LOW", "BROAD", "SIMPLE"}:
        return "LOW"
    return "MODERATE"


def _dependency(
    rows: dict[str, dict[str, Any]], key: str, requirement: dict[str, Any], reference: str
) -> None:
    if requirement.get("applicable") is False:
        rows[key] = _row("NOT_APPLICABLE", "This dependency is explicitly not applicable.", [reference])
        return
    if requirement.get("required") is not True:
        return
    level = _precision(requirement)
    if key in {"OBJECT_IDENTITY_CONTINUITY", "CHARACTER_IDENTITY_CONTINUITY"}:
        burden = any(
            requirement.get(item) is True
            for item in (
                "throughOcclusion",
                "throughTransformation",
                "acrossScenes",
                "acrossSegments",
                "largePoseChanges",
                "exactIdentityRequired",
            )
        )
        if not burden and level != "HIGH":
            level = "LOW"  # ordinary visible continuity is not an inherent risk
    if key == "TEXT_LIP_SYNC_SYMBOL":
        level = (
            "HIGH"
            if any(
                requirement.get(item)
                for item in (
                    "exactText",
                    "lettersMustMatch",
                    "exactSymbols",
                    "lipSyncRequired",
                )
            )
            else level
        )
    if key == "TRANSFORMATION_COMPLEXITY" and any(
        requirement.get(item) is True
        for item in (
            "reversible",
            "topologyChange",
            "exactIntermediateStates",
        )
    ):
        level = "HIGH"
    if key == "EXACT_COUNT_DEPENDENCY":
        level = "HIGH" if requirement.get("acrossStages") is True else "MODERATE"
    essential = requirement.get("essential") is True
    _raise(
        rows,
        key,
        level,
        str(requirement.get("reason") or f"Required {key.lower().replace('_', ' ')} dependency ({level})."),
        [reference, *sorted(_names(requirement.get("evidenceReferences")))],
        material=level != "LOW" and requirement.get("material") is not False,
        redesign=level == "HIGH" and essential and requirement.get("requiresRedesign") is True,
    )


def _duration(metadata: dict[str, Any], beats: list[dict[str, Any]]) -> tuple[float | None, str]:
    declared = _number(metadata.get("duration"))
    if declared is not None and declared > 0:
        return declared, "metadata.duration"
    ends = [_number(beat.get("endTime")) for beat in beats]
    if ends and all(value is not None and value > 0 for value in ends):
        return max(value for value in ends if value is not None), "beats.endTime"
    return None, "UNAVAILABLE"


def _structured_plan(beats: list[dict[str, Any]]) -> bool:
    return bool(beats) and all(
        bool(beat.get("action") or beat.get("primaryAction"))
        and bool(_names(beat.get("actors")) or _names(beat.get("actor")))
        and (
            isinstance(beat.get("objects"), list)
            or isinstance(beat.get("heldObjects"), list)
            or bool(_names(beat.get("targetObject")))
        )
        for beat in beats
    )


def _duration_load(beats: list[dict[str, Any]], duration: float | None, complete: bool) -> dict[str, Any]:
    changes = [
        beat
        for beat in beats
        if beat.get("stateChangeRequired") is True and beat.get("dependsOnPreviousState") is True
    ]
    if duration is None or not complete:
        return {
            **_row("UNKNOWN", "Timed, independently tracked action evidence is incomplete.", []),
            "dependentStateChanges": len(changes),
            "changesPerSecond": None,
        }
    density = len(changes) / duration
    level = "HIGH" if density > 1 else "MODERATE" if density > 0.5 else "LOW"
    return {
        **_row(
            level,
            "Dependent state changes relative to the actual plan duration; "
            "simple sequential beats have no fixed-count limit.",
            [str(beat.get("id") or "beat") for beat in changes],
            material=level != "LOW",
        ),
        "dependentStateChanges": len(changes),
        "changesPerSecond": round(density, 6),
    }


def _beat_risks(rows: dict[str, dict[str, Any]], beats: list[dict[str, Any]]) -> None:
    occluded: dict[tuple[str, str], list[str]] = {}
    returned: dict[tuple[str, str], list[str]] = {}
    exact_counts: list[str] = []
    for index, beat in enumerate(beats):
        reference = f"beats[{index}]:{beat.get('id') or index}"
        for key, fields in _DEPENDENCIES.items():
            for field in fields:
                _dependency(rows, key, _mapping(beat.get(field)), f"{reference}.{field}")
        moving = _names(beat.get("movingEntities"))
        if beat.get("simultaneous") is True and beat.get("independentMotion") is True and len(moving) > 1:
            level = "HIGH" if len(moving) >= 4 else "MODERATE"
            _raise(
                rows,
                "MULTI_ENTITY_CONCURRENCY",
                level,
                f"{len(moving)} independently moving entities must act simultaneously.",
                [reference],
            )
            _raise(
                rows,
                "ENTITY_LOAD",
                "HIGH" if len(moving) >= 6 else "MODERATE",
                f"{len(moving)} important entities require simultaneous tracking.",
                [reference],
            )
        visibility = _mapping(beat.get("visibility"))
        if visibility.get("state") in {"FULLY_OCCLUDED", "OUT_OF_FRAME", "HIDDEN"}:
            for kind in ("object", "character"):
                name = visibility.get(kind)
                if isinstance(name, str) and name:
                    occluded.setdefault((kind, name), []).append(reference)
        reappearance = _mapping(beat.get("requiredReappearance"))
        if reappearance.get("mustReturnVisible") is True:
            for kind in ("object", "character"):
                name = reappearance.get(kind)
                if isinstance(name, str) and name:
                    returned.setdefault((kind, name), []).append(reference)
        if _mapping(beat.get("quantityAtStage")).get("exact") is True:
            exact_counts.append(reference)
        camera = _mapping(beat.get("camera"))
        interaction = _mapping(beat.get("objectInteraction"))
        if (
            _precision(camera) == "HIGH"
            and _precision(interaction) == "HIGH"
            and (
                camera.get("coupledToInteraction") is True
                or interaction.get("requiresSynchronizedCamera") is True
            )
        ):
            _raise(
                rows,
                "CAMERA_ACTION_COUPLING",
                "HIGH",
                "Complex camera movement is synchronized with complex object interaction.",
                [reference],
            )
    for identity in sorted(occluded.keys() & returned.keys()):
        references = occluded[identity] + returned[identity]
        _raise(
            rows,
            "OCCLUSION_HIDDEN_STATE",
            "HIGH",
            "The same important entity must survive full occlusion and required reappearance.",
            references,
        )
        key = "CHARACTER_IDENTITY_CONTINUITY" if identity[0] == "character" else "OBJECT_IDENTITY_CONTINUITY"
        _raise(
            rows,
            key,
            "MODERATE",
            "The same identity must survive disappearance and reappearance.",
            references,
        )
    if exact_counts:
        _raise(
            rows,
            "EXACT_COUNT_DEPENDENCY",
            "HIGH" if len(exact_counts) > 1 else "MODERATE",
            "Visual correctness requires exact quantities at declared stages.",
            exact_counts,
        )


def general_producibility_evidence(
    video_plan_ir: dict[str, Any] | None,
    *,
    duration_is_declared: bool = True,
) -> dict[str, Any]:
    """Return a lossless Family 10 read model without modifying any input/policy.

    HIGH material dependencies warn; only explicit essential HIGH requirements
    marked as needing structural redesign block. Material moderate dependencies may combine;
    non-material risks do not
    override core feasibility. No average, creative grade, or winner label is used.
    """
    ir = video_plan_ir or {}
    metadata = _mapping(ir.get("metadata"))
    raw_beats = ir.get("beats")
    beats = [item for item in raw_beats if isinstance(item, dict)] if isinstance(raw_beats, list) else []
    duration, duration_source = _duration(metadata, beats)
    if not duration_is_declared:
        duration, duration_source = None, "PARSER_DURATION_ASSUMPTION"
    complete = _structured_plan(beats)
    not_applicable = metadata.get("requiresGenerativeVideo") is False
    base_level = "NOT_APPLICABLE" if not_applicable else "LOW" if complete else "UNKNOWN"
    base_reason = {
        "LOW": "No material dependency detected in the supplied tracked action plan.",
        "UNKNOWN": "Independent entity/action evidence is missing; feasibility is not established.",
        "NOT_APPLICABLE": "The artifact explicitly requires no generative video production.",
    }[base_level]
    rows = {
        key: _row(
            base_level,
            base_reason,
            ["metadata.requiresGenerativeVideo"] if not_applicable else ["beats"] if complete else [],
        )
        for key in GENERAL_PRODUCIBILITY_DIMENSIONS
    }
    load = _duration_load(beats, duration, complete)
    if not_applicable:
        load = {
            **_row("NOT_APPLICABLE", base_reason, ["metadata.requiresGenerativeVideo"]),
            "dependentStateChanges": None,
            "changesPerSecond": None,
        }
    else:
        for key, fields in _DEPENDENCIES.items():
            for field in fields:
                _dependency(rows, key, _mapping(ir.get(field)), field)
        _beat_risks(rows, beats)
        split = _mapping(ir.get("splitPlan"))
        if split.get("required") is True:
            continuity = _mapping(ir.get("segmentContinuityRequirement"))
            end_state = _mapping(_mapping(split.get("part1")).get("endState"))
            start_state = _mapping(_mapping(split.get("part2")).get("startState"))
            if continuity.get("required") is True or (end_state and start_state):
                _raise(
                    rows,
                    "SEGMENT_CONTINUITY",
                    "MODERATE",
                    "Independently generated segments require an explicit state handoff.",
                    ["splitPlan"],
                )
            elif split.get("continuityRequired") is False:
                rows["SEGMENT_CONTINUITY"] = _row(
                    "NOT_APPLICABLE",
                    "Independent segments explicitly require no state transfer.",
                    ["splitPlan.continuityRequired"],
                )
            elif rows["SEGMENT_CONTINUITY"]["level"] == "LOW":
                rows["SEGMENT_CONTINUITY"] = _row(
                    "UNKNOWN",
                    "Independent segments are declared but their continuity requirement is unspecified.",
                    ["splitPlan"],
                )
        camera = _mapping(ir.get("camera"))
        interaction = _mapping(ir.get("objectInteraction"))
        if (
            _precision(camera) == "HIGH"
            and _precision(interaction) == "HIGH"
            and camera.get("coupledToInteraction") is True
        ):
            _raise(
                rows,
                "CAMERA_ACTION_COUPLING",
                "HIGH",
                "Complex camera and action are explicitly coupled.",
                ["camera", "objectInteraction"],
            )
        if complete:
            entities: set[str] = set()
            for beat in beats:
                for field in ("actors", "actor", "objects", "heldObjects", "movingEntities"):
                    entities.update(_names(beat.get(field)))
            if len(entities) >= 6:
                _raise(
                    rows,
                    "ENTITY_LOAD",
                    "MODERATE",
                    f"{len(entities)} independently important entities occur in the action plan.",
                    ["beats"],
                    material=False,
                )
    # Consume only the Family 6 concurrency evidence with a production consequence.
    # A HIGH Family 6 result by itself is deliberately not a Family 10 failure.
    temporal = temporal_generation_load_evidence(video_plan_ir).to_dict()
    if not not_applicable:
        for axis in temporal.get("axes", []):
            if axis.get("axis") == "action_concurrency" and axis.get("level") == "SEVERE":
                _raise(
                    rows,
                    "MULTI_ENTITY_CONCURRENCY",
                    "HIGH",
                    "Family 6 records simultaneous coupled actor/object actions.",
                    ["family6.action_concurrency", *axis.get("evidenceReferences", [])],
                )
    material = [key for key, row in rows.items() if row["material"] and row["level"] in {"MODERATE", "HIGH"}]
    unknown = [key for key, row in rows.items() if row["level"] == "UNKNOWN"]
    if not_applicable:
        status = "NOT_APPLICABLE"
    elif any(row["requiresRedesign"] for row in rows.values()):
        status = "NOT_PRODUCIBLE"
    elif material or load["level"] in {"MODERATE", "HIGH"}:
        status = "RISKY"
    elif unknown or duration is None:
        status = "UNKNOWN"
    else:
        status = "PRODUCIBLE"
    reasons = [rows[key]["reason"] for key in material]
    if load["material"]:
        reasons.append(load["reason"])
    if unknown or duration is None:
        reasons.append("Some required structured production evidence is unavailable.")
    if not reasons:
        reasons = [base_reason]
    # Family 6 evidence is consumed verbatim, never reclassified or fed back into scoring.
    return {
        "status": status,
        "dimensions": rows,
        "reasons": reasons,
        "materialRisks": material,
        "unknownDimensions": unknown,
        "durationSeconds": duration,
        "durationSource": duration_source,
        "durationLoad": load,
        "provenance": {
            "evaluatorVersion": GENERAL_PRODUCIBILITY_VERSION,
            "source": "STRUCTURED_VIDEO_PLAN_IR",
            "sourceEvidence": deepcopy(_mapping(metadata.get("generalProducibilityEvidence"))),
            "family6TemporalLoad": temporal,
            "authorizationPolicy": "EXISTING_POLICY_UNCHANGED",
        },
    }


def general_producibility_from_parse(ir: dict[str, Any], parser_metadata: Any) -> dict[str, Any]:
    """Do not mistake a frozen parser duration fallback for declared evidence."""
    assumptions = getattr(parser_metadata, "assumptions", ())
    declared = not any("Duration not explicit" in str(item) for item in assumptions)
    return general_producibility_evidence(ir, duration_is_declared=declared)
