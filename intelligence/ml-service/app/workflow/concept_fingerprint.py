"""Noun-independent structural descriptors, not creative quality scores."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

VERSION = "short-concept-fingerprint-v1"
UNKNOWN = "UNSPECIFIED"
CORE = (
    "interactionType",
    "engineFamily",
    "transformationDirection",
    "trigger",
    "escalationTopology",
    "resolutionTopology",
    "finalSilhouetteTopology",
)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def token(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_") or UNKNOWN


def fingerprint(candidate: dict[str, Any]) -> dict[str, Any]:
    rule = str(candidate.get("impossibleRule", candidate.get("impossibleRuleOrCoreContradiction", "")))
    goal = str(candidate.get("everydayGoal", candidate.get("protagonistGoal", "")))
    ending = str(candidate.get("finalPayoff", ""))
    text = rule.lower()
    plan = candidate.get("structuralPlan") or {}
    family = token(str(candidate.get("engineFamily") or ""))
    if re.search(r"smaller|shrink", text) or family in {"SHRINKING", "UNEXPECTED_SHRINKING"}:
        family = "PROGRESSIVE_SHRINKING"
    elif re.search(r"(?:grow|larger|bigger|doubles? in size)", text) or family in {
        "GROWTH",
        "UNEXPECTED_GROWTH",
    }:
        family = "PROGRESSIVE_GROWTH"
    trigger = next(
        (
            value
            for pattern, value in [
                (r"changes? (?:gripping )?strategy|changes? strateg|different strateg", "STRATEGY_CHANGE"),
                (r"lift(?:ed|ing|s)?", "OBJECT_LIFT"),
                (r"releas", "RELEASE_PRESSURE"),
                (r"touch|contact", "CONTACT"),
                (r"pull", "PULL_CONTACT"),
            ]
            if re.search(pattern, text)
        ),
        UNKNOWN,
    )
    direction = (
        "INCREASE"
        if family == "PROGRESSIVE_GROWTH"
        else "DECREASE"
        if family == "PROGRESSIVE_SHRINKING"
        else UNKNOWN
    )
    topology = (
        "MAGNITUDE_RATCHET"
        if direction == "INCREASE"
        else "CAPABILITY_LOSS"
        if direction == "DECREASE"
        else UNKNOWN
    )
    resolution = (
        "GOAL_REVERSAL" if re.search(r"revers(?:es|ing)|instead of|rather than", ending.lower()) else UNKNOWN
    )
    goal_type = next(
        (
            value
            for pattern, value in [
                (r"eat|bite", "EAT"),
                (r"brush|hair", "GROOM"),
                (r"sit", "SIT"),
                (r"wash", "WASH"),
                (r"open", "OPEN"),
                (r"close", "CLOSE"),
                (r"put.*away|pack", "STORE"),
                (r"wear|shoe", "DRESS"),
                (r"carry", "CARRY"),
                (r"retrieve|pick", "RETRIEVE"),
                (r"wipe|clean", "CLEAN"),
                (r"fold", "FOLD"),
                (r"hang", "HANG"),
            ]
            if re.search(pattern, goal.lower())
        ),
        UNKNOWN,
    )
    inferred = {
        "goalType": goal_type,
        "interactionType": trigger,
        "engineFamily": family,
        "transformationDirection": direction,
        "trigger": trigger,
        "escalationTopology": topology,
        "resolutionTopology": resolution,
        "finalSilhouetteTopology": UNKNOWN,
        "loopTopology": "NONE",
    }
    dimensions = {key: token(str(plan.get(key, value))) for key, value in inferred.items()}
    # The physical growth/shrinkage direction cannot be disguised by metadata.
    if direction != UNKNOWN:
        dimensions.update(engineFamily=family, transformationDirection=direction)
    core = {key: dimensions[key] for key in CORE}
    return {
        "version": VERSION,
        "dimensions": dimensions,
        "fullHash": digest(dimensions),
        "coreHash": digest(core),
        "supportedCoreDimensions": sum(v != UNKNOWN for v in core.values()),
        "evidenceKind": "LOCAL_AUTHORED_STRUCTURAL_PLAN" if plan else "RULE_TEXT_PATTERN_SCREEN",
        "limitation": "Structural descriptors are not semantic verification. Goal nouns and optional loop wording cannot create a new causal engine.",
    }


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    a, b = left["dimensions"], right["dimensions"]
    matches = [key for key in CORE if a[key] == b[key] and a[key] != UNKNOWN]
    differences = [key for key in CORE if a[key] != b[key]]
    return {
        "nearDuplicate": not differences and len(matches) >= 4,
        "matchingDimensions": matches,
        "materialDifferences": differences,
        "goalDifferenceIsCosmeticForEngine": a["goalType"] != b["goalType"],
    }
