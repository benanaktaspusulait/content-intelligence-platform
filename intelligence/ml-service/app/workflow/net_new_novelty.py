"""Bounded, source-backed Phase A territory exclusions; no quality score."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .concept_fingerprint import digest

VERSION = "net-new-opening-exclusions-v1"
EXCLUSION_ID = "mimi-rolling-pin-dough-wall"
SOURCE = Path(__file__).resolve().parents[3] / "docs/semantic-two-stage-v1-phase-b-run-001/source-seed.json"
SUPPORTING_SOURCES = (
    Path(__file__).resolve().parents[3] / "docs/semantic-two-stage-v1-run-001/opening-a/seed.json",
    Path(__file__).resolve().parents[3] / "docs/semantic-two-stage-v1-run-001/opening-c/seed.json",
)


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def load_exclusions():
    source_bytes = SOURCE.read_bytes()
    seed = json.loads(source_bytes)
    # Mechanic aliases describe only the source-backed causal relationship. They are
    # not a general object ban or weighted similarity model.
    supporting = []
    for path in SUPPORTING_SOURCES:
        raw = path.read_bytes()
        row = json.loads(raw)
        supporting.append({"conceptId": row["seedId"], "sourceRecord": str(path),
                           "sourceSha256": hashlib.sha256(raw).hexdigest(),
                           "protagonistSuggestion": row["protagonistSuggestion"],
                           "everydayGoal": row["everydayGoal"], "primaryObject": row["primaryObject"],
                           "impossibleRule": row["impossibleRule"], "frameZeroDescription": row["frameZeroDescription"]})
    return [{
        "conceptId": EXCLUSION_ID,
        "sourceRecord": str(SOURCE),
        "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "mechanic": "Mimi uses a rolling pin to flatten dough; pressure at the barrel contact makes that dough strip rise into a tall vertical ridge or wall, lifting/supporting the barrel above the surrounding flat sheet.",
        "reason": "Historical Phase A seed was expanded as Flat-Pack Dough; this repeated causal opening territory is not acceptable as net-new production.",
        "sourceFields": {k: seed[k] for k in (
            "protagonistSuggestion", "everydayGoal", "primaryObject", "impossibleRule",
            "visibleTrigger", "frameZeroDescription")},
        "supportingHistoricalSeeds": supporting,
        "aliases": {
            "goal": ["flatten dough", "roll dough flat", "make dough thinner", "spread dough", "dough flat", "dough thinner"],
            "object": ["rolling pin", "dough roller"],
            "response": ["dough rises", "dough grows upward", "dough thickens upward", "dough forms a ridge", "dough forms a wall", "vertical dough wall", "upright ridge", "pastry rises", "standing rib", "touched pastry rises"],
            "trigger": ["presses against dough", "presses down on dough", "barrel contacts dough", "rolling pin pressure", "bears down", "downward force along"],
            "opening": ["barrel rests on ridge", "barrel rests across ridge", "barrel supported by wall", "barrel above flat dough", "wall beneath barrel", "ridge beneath barrel", "wall occupies the exact strip beneath its barrel", "narrow crest carries the tool above the sheet"]
        }
    }]


def context_record():
    exclusions = load_exclusions()
    body = {"version": VERSION, "exclusions": exclusions}
    return {**body, "contextSha256": digest(body)}


def request_message(record):
    rows = []
    for item in record["exclusions"]:
        rows.append({"conceptId": item["conceptId"], "mechanicToAvoid": item["mechanic"],
                     "instruction": "Create a genuinely different causal mechanism and opening silhouette. Do not reuse this mechanism, including semantic paraphrases. The character Mimi or a rolling pin alone is not prohibited; either may appear only if the causal rule and visual progression are materially different."})
    return {"role": "user", "content": json.dumps({"contextVersion": VERSION,
            "contextSha256": record["contextSha256"], "historicalExclusions": rows}, ensure_ascii=False, sort_keys=True)}


def _has_any(text, aliases):
    normalized = f" {_norm(text)} "
    return any(f" {_norm(alias)} " in normalized for alias in aliases)


def compare_opening(seed, exclusions=None):
    exclusions = load_exclusions() if exclusions is None else exclusions
    results = []
    for item in exclusions:
        sf = item["sourceFields"]
        # Canonical protagonist/goal/object fields and source-backed semantic
        # paraphrase witnesses for rule, trigger-response and frame-zero relation.
        same_character = _norm(seed.get("protagonistSuggestion")) == _norm(sf["protagonistSuggestion"])
        goal = _has_any(seed.get("everydayGoal", ""), item["aliases"]["goal"])
        obj = _has_any(seed.get("primaryObject", ""), item["aliases"]["object"])
        rule = _has_any(seed.get("impossibleRule", ""), item["aliases"]["response"])
        trigger = _has_any(seed.get("impossibleRule", "") + " " + seed.get("visibleTrigger", ""), item["aliases"]["trigger"])
        opening = _has_any(seed.get("frameZeroDescription", ""), item["aliases"]["opening"])
        # A categorical duplicate requires the same character, task family,
        # object, contact-triggered response and opening silhouette.
        axes = {"protagonist": same_character, "goal": goal, "object": obj,
                "coreRuleResponse": rule, "triggerResponse": trigger, "firstFrameRelation": opening}
        status = "DUPLICATE_CREATIVE_TERRITORY" if all(axes.values()) else (
            "HIGH_SIMILARITY_REVIEW" if sum(axes.values()) >= 4 else
            # A different causal response and opening relation are material
            # differences even when ordinary character/task/object overlap.
            "NO_KNOWN_EQUIVALENT" if sum(axes.values()) <= 1 or (not rule and not opening) else
            "UNKNOWN_SIMILARITY")
        results.append({"conceptId": item["conceptId"], "sourceRecord": item["sourceRecord"],
                        "sourceSha256": item["sourceSha256"], "status": status,
                        "matchingAxes": [k for k,v in axes.items() if v],
                        "axisEvidence": axes,
                        "scope": "SOURCE_BACKED_CATEGORICAL_OPENING_EXCLUSION_NOT_GENERAL_SIMILARITY_SCORE"})
    return {"version": VERSION, "results": results,
            "disposition": "DUPLICATE_CREATIVE_TERRITORY" if any(r["status"] == "DUPLICATE_CREATIVE_TERRITORY" for r in results) else
            "HIGH_SIMILARITY_REVIEW" if any(r["status"] == "HIGH_SIMILARITY_REVIEW" for r in results) else
            "UNKNOWN_SIMILARITY" if any(r["status"] == "UNKNOWN_SIMILARITY" for r in results) else "NO_KNOWN_EQUIVALENT",
            "unknownIsPass": False}
