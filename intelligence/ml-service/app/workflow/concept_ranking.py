"""Rank supplied short concepts by orchestrating accepted validators, never generate.

No canonical grading, calibration, provider construction, persistence or render
authorization. Versioned orchestration policy is separate from validator scores.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import short_form_engine as short
from .creative_prompt_quality import assess as assess_cpq

VERSION = "concept-ranking-v1"
TIE_MARGIN = 3
DIVERSITY_MARGIN = 5
DIMENSIONS = (
    ("instantCausalLegibility", "instantPremiseLegibility.score", 22),
    ("visualContradiction", "hookScore", 8),
    ("goalClarity", "goalScore", 10),
    ("oneRuleStrength", "ruleClarityScore", 8),
    ("progressDensity", "progressDensityScore", 18),
    ("escalationQuality", "escalationScore", 10),
    ("payoffStrength", "payoffScore", 18),
    ("rewatchPotential", "rewatchScore", 6),
)
PENALTY_POLICY = {
    "PASSIVE_PREMISE": {"points": 8, "findings": ["EVERYDAY_GOAL_UNCLEAR", "TOO_FEW_CAUSAL_BEATS"]},
    "HIGH_ACTIVITY_LOW_PROGRESS": {"points": 12, "findings": ["HIGH_ACTIVITY_LOW_PROGRESS"]},
    "DIALOGUE_DEPENDENT": {"points": 20, "findings": ["AUDIO_DEPENDENT_CAUSALITY"]},
    "TEMPORAL_OVERLOAD": {"points": 6, "findings": ["TEMPORAL_OVERLOAD"]},
    "WEAK_PAYOFF": {"points": 15, "findings": ["WEAK_VISUAL_PAYOFF"]},
    "LATE_HOOK": {"points": 15, "findings": ["OPENING_NOT_IN_TROUBLE"]},
    "RANDOM_ESCALATION": {"points": 20, "findings": ["MULTIPLE_UNRELATED_RULES", "CORE_RULE_UNSUPPORTED"]},
}
REQUIRED = (
    "title",
    "protagonist",
    "protagonistGoal",
    "objectOrPrimaryInteraction",
    "impossibleRuleOrCoreContradiction",
    "frameZeroDescription",
    "escalationPlan",
    "finalPayoff",
    "intendedDurationSeconds",
)


class ConceptBeat(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    startSeconds: float = Field(ge=0, le=600)
    endSeconds: float = Field(gt=0, le=600)
    description: str = Field(min_length=1, max_length=5000)


class ConceptInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str | None = Field(None, min_length=1, max_length=150)
    title: str | None = Field(None, max_length=1000)
    protagonist: str | None = Field(None, max_length=1000)
    protagonistGoal: str | None = Field(None, max_length=3000)
    objectOrPrimaryInteraction: str | None = Field(None, max_length=2000)
    impossibleRuleOrCoreContradiction: str | None = Field(None, max_length=3000)
    frameZeroDescription: str | None = Field(None, max_length=5000)
    escalationPlan: str | list[ConceptBeat] | None = Field(None, max_length=50000)
    finalPayoff: str | None = Field(None, max_length=5000)
    optionalDialogue: str | None = Field(None, max_length=3000)
    intendedDurationSeconds: float | None = Field(None, gt=0, le=600)
    text: str | None = Field(None, max_length=50000)

    @field_validator("escalationPlan")
    @classmethod
    def bounded_plan(cls, value):
        if isinstance(value, list) and len(value) > 30:
            raise ValueError("At most 30 supplied beats per concept")
        return value


class ConceptBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[ConceptInput | str] = Field(min_length=1, max_length=30)


_LABELS = {
    "id": "id",
    "candidateid": "id",
    "title": "title",
    "protagonist": "protagonist",
    "maincharacter": "protagonist",
    "protagonistgoal": "protagonistGoal",
    "goal": "protagonistGoal",
    "objectorprimaryinteraction": "objectOrPrimaryInteraction",
    "object": "objectOrPrimaryInteraction",
    "impossibleruleorcorecontradiction": "impossibleRuleOrCoreContradiction",
    "rule": "impossibleRuleOrCoreContradiction",
    "framezerodescription": "frameZeroDescription",
    "framezero": "frameZeroDescription",
    "escalationplan": "escalationPlan",
    "finalpayoff": "finalPayoff",
    "payoff": "finalPayoff",
    "optionaldialogue": "optionalDialogue",
    "dialogue": "optionalDialogue",
    "intendeddurationseconds": "intendedDurationSeconds",
    "duration": "intendedDurationSeconds",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _same(a: str, b: str) -> bool:
    return re.sub(r"\W+", "", a).casefold() == re.sub(r"\W+", "", b).casefold()


def _labels(text: str) -> dict[str, Any]:
    """Extract labeled multiline values without inventing missing concepts."""
    found: dict[str, str] = {}
    active = None
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z _-]{0,55}):\s*(.*)$", line)
        key = _LABELS.get(re.sub(r"[^a-z]", "", match[1].lower())) if match else None
        if key:
            active = key
            found[key] = match[2].strip()
        elif active:
            found[active] += "\n" + line
    return {key: value.strip() for key, value in found.items()}


def _assemble(plan: Any, frame: str, payoff: str, duration: Any) -> str:
    if isinstance(plan, str):
        return plan
    if not isinstance(plan, list) or not plan:
        return ""
    beats = [b.model_dump() if isinstance(b, ConceptBeat) else b for b in plan]
    # Missing opening/ending windows use supplied middle-beat boundaries only;
    # no action, time quota or premise is generated.
    if beats[0]["startSeconds"] > 0 and frame:
        beats.insert(0, {"startSeconds": 0, "endSeconds": beats[0]["startSeconds"], "description": frame})
    if isinstance(duration, (int, float)) and beats[-1]["endSeconds"] < duration and payoff:
        beats.append({"startSeconds": beats[-1]["endSeconds"], "endSeconds": duration, "description": payoff})
    return "\n".join(f"{b['startSeconds']:g}-{b['endSeconds']:g}s: {b['description']}" for b in beats)


def normalize(candidate: ConceptInput | dict[str, Any] | str) -> dict[str, Any]:
    """Source-preserving normalization. Unresolved fields stay missing."""
    if isinstance(candidate, str):
        if not candidate.strip() or len(candidate) > 50000:
            raise ValueError("Plain-text concepts must contain 1–50000 characters")
        supplied = {"text": candidate}
    else:
        supplied = ConceptInput.model_validate(candidate).model_dump(exclude_none=True)
    labeled = _labels(supplied.get("text", ""))
    values = {**labeled, **supplied}
    provenance = {key: "EXPLICIT_FIELD" if key in supplied else "LABELED_SOURCE_TEXT" for key in values}
    duration = values.get("intendedDurationSeconds")
    if isinstance(duration, str):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)?\s*", duration)
        duration = float(match[1]) if match else None
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration)
    ):
        raise ValueError("intendedDurationSeconds must be a finite number")
    values["intendedDurationSeconds"] = duration
    text = supplied.get("text") or _assemble(
        values.get("escalationPlan"),
        values.get("frameZeroDescription", ""),
        values.get("finalPayoff", ""),
        duration,
    )
    # For labeled concepts the timeline can be the escalationPlan field, while
    # the complete original text remains available as normalization evidence.
    if supplied.get("text") and labeled.get("escalationPlan"):
        text = labeled["escalationPlan"]
    if len(text) > 50000:
        raise ValueError("Assembled concept exceeds 50000 characters")
    timed = short._timeline(text) if text else []
    timed = [beat for beat in timed if beat["start"] is not None]
    if timed:
        first, last = timed[0]["quote"], timed[-1]["quote"]
        auto = {"frameZeroDescription": first, "finalPayoff": last, "escalationPlan": text}
        if duration is None:
            auto["intendedDurationSeconds"] = max(beat["end"] for beat in timed)
        visual = short._visual(first)
        goal = re.search(short._GOAL, visual, re.I)
        actor = re.search(r"\b([A-Z][a-z]+) (?:tries|runs|has|is|wants|must|pulls|attempts|needs)\b", visual)
        obj = re.search(
            r"\b(?:chair|stool|spoon|brush|ball|lid|drawer|shoe|garden|plant|snack|hands|hair)\b",
            visual,
            re.I,
        )
        if goal:
            auto["protagonistGoal"] = goal[0]
        if actor:
            auto["protagonist"] = actor[1]
        if obj:
            auto["objectOrPrimaryInteraction"] = obj[0]
        if short._features(first)["rules"]:
            auto["impossibleRuleOrCoreContradiction"] = first
        for key, value in auto.items():
            if not values.get(key):
                values[key] = value
                provenance[key] = (
                    "EXACT_SOURCE_EXCERPT" if key != "intendedDurationSeconds" else "TIMELINE_END"
                )
    normalized = {key: values.get(key) for key in REQUIRED}
    normalized["optionalDialogue"] = values.get("optionalDialogue")
    candidate_id = (
        str(values.get("id") or "").strip()
        or "concept-" + _sha(_canonical({"text": text, **normalized}))[:16]
    )
    return {
        "id": candidate_id,
        **normalized,
        "evaluationText": text,
        "originalInput": supplied,
        "normalizationEvidence": provenance,
        "sourceSha256": _sha(text),
        "normalizationWarnings": [
            "Only explicit fields, labeled text and supported source excerpts are normalized; unknown fields remain missing.",
            "Timed middle beats can bound supplied opening/payoff windows; no actions are generated.",
        ],
    }


def _axes(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    # Same three axes and equality test as accepted duplicate-engine detection.
    return [key for key in ("opening", "progression", "ending") if left[key] and left[key] == right[key]]


def _historical(signature: dict[str, Any]) -> dict[str, Any]:
    refs = json.loads(Path(short.__file__).with_name("short_form_references.json").read_text())
    scored = sorted(((-len(_axes(signature, ref["signature"])), ref["referenceId"], ref) for ref in refs))
    count, _, ref = scored[0]
    if count == 0:
        return {
            "closestHistoricalEngine": None,
            "similarities": [],
            "differences": [],
            "duplicateRisk": "NO_MATCH_IN_LIMITED_CORPUS",
            "limitation": "No supported structural match in the two-reference corpus; originality remains unverified.",
        }
    axes = _axes(signature, ref["signature"])
    return {
        "closestHistoricalEngine": ref["referenceId"],
        "sourceSha256": ref["sourceSha256"],
        "similarities": axes,
        "differences": [
            {"axis": key, "candidate": signature[key], "historical": ref["signature"][key]}
            for key in signature
            if key not in axes
        ],
        "duplicateRisk": "HIGH" if len(axes) == 3 else ("MODERATE" if len(axes) == 2 else "LOW"),
        "limitation": "Familiar structure alone is not rejection; exact three-axis reuse needs meaningful novelty. No new performance evidence.",
    }


def validate_concept(candidate: ConceptInput | dict[str, Any] | str) -> dict[str, Any]:
    normalized = normalize(candidate)
    text = normalized["evaluationText"]
    report = (
        short.assess(
            text, {"shortFormEvaluation": True, "desiredDuration": normalized["intendedDurationSeconds"]}
        )
        if text.strip()
        else None
    )
    missing = [key for key in REQUIRED if not normalized.get(key)]
    reasons = [
        {"code": "MISSING_FIELD", "field": key, "source": "NORMALIZATION", "reason": f"Missing {key}."}
        for key in missing
    ]
    if report:
        for finding in report["findings"]:
            if finding["severity"] == "REVISION_REQUIRED":
                reasons.append(
                    {
                        "code": finding["code"],
                        "source": "SHORT_FORM_ENGINE",
                        "reason": finding["message"],
                        "beatIds": finding["beatIds"],
                    }
                )
        if report["status"] not in {"PASS", "PASS_WITH_WARNINGS"} and not reasons:
            reasons.append(
                {
                    "code": "SHORT_FORM_NOT_ELIGIBLE",
                    "source": "SHORT_FORM_ENGINE",
                    "reason": report["humanReadableReport"],
                }
            )
        # Declared fields cannot substitute for a different opening or ending.
        for field, quote in (
            ("frameZeroDescription", report["beats"][0]["quote"]),
            ("finalPayoff", report["beats"][-1]["quote"]),
        ):
            if normalized.get(field) and not _same(str(normalized[field]), quote):
                reasons.append(
                    {
                        "code": "PLAN_FIELD_CONFLICT",
                        "field": field,
                        "source": "NORMALIZATION",
                        "reason": f"{field} differs from the actual timed plan.",
                    }
                )
        if (
            normalized.get("protagonistGoal")
            and not short._features(str(normalized["protagonistGoal"]))["goal"]
        ):
            reasons.append(
                {
                    "code": "DECLARED_GOAL_UNSUPPORTED",
                    "field": "protagonistGoal",
                    "source": "SHORT_FORM_ENGINE_GOAL_PATTERN",
                    "reason": "The declared goal is not a supported visible everyday goal.",
                }
            )
        declared_goal = re.search(short._GOAL, str(normalized.get("protagonistGoal") or ""), re.I)
        opening_goal = re.search(short._GOAL, report["beats"][0]["visual"], re.I)
        if declared_goal and opening_goal:

            def goal_words(value):
                words = re.findall(r"\w+", value.lower())
                return [word for word in words if word not in {"the", "a", "an", "his", "her"}]

            if goal_words(declared_goal[0]) != goal_words(opening_goal[0]):
                reasons.append(
                    {
                        "code": "DECLARED_GOAL_CONFLICT",
                        "field": "protagonistGoal",
                        "source": "NORMALIZATION",
                        "reason": "The declared goal differs from the supported opening goal; clarify the source rather than assuming equivalence.",
                    }
                )
        protagonist = str(normalized.get("protagonist") or "").split()
        opening_actor = re.search(
            r"\b([A-Z][a-z]+) (?:tries|runs|has|is|wants|must|pulls|attempts|needs)\b",
            report["beats"][0]["visual"],
        )
        named_actor = opening_actor and opening_actor[1] not in {"He", "She", "They", "The", "This"}
        if (
            protagonist
            and named_actor
            and not re.search(r"\b" + re.escape(protagonist[0]) + r"\b", report["beats"][0]["visual"], re.I)
        ):
            reasons.append(
                {
                    "code": "DECLARED_PROTAGONIST_CONFLICT",
                    "field": "protagonist",
                    "source": "NORMALIZATION",
                    "reason": "The declared protagonist conflicts with the named actor in the supplied opening.",
                }
            )
        declared_rules = short._features(str(normalized.get("impossibleRuleOrCoreContradiction") or ""))[
            "rules"
        ]
        if declared_rules and not set(declared_rules).issubset(report["rules"]):
            reasons.append(
                {
                    "code": "DECLARED_RULE_CONFLICT",
                    "field": "impossibleRuleOrCoreContradiction",
                    "source": "SHORT_FORM_ENGINE_RULE_PATTERNS",
                    "reason": "The declared rule differs from the rule supported by the timed plan.",
                }
            )
        dialogue = normalized.get("optionalDialogue")
        if dialogue and str(dialogue).strip('“”" ') not in text:
            reasons.append(
                {
                    "code": "UNTIMED_DIALOGUE",
                    "field": "optionalDialogue",
                    "source": "NORMALIZATION",
                    "reason": "Place the supplied dialogue in the timed plan; speech timing is not invented.",
                }
            )
    signature = (
        short._signature(report["beats"]) if report else {"opening": [], "progression": [], "ending": []}
    )
    historical = _historical(signature)
    # The accepted validator exempts a reference from comparing with itself.
    # A production shortlist must still identify resubmission of that winner.
    duplicate = report["duplicateEngineRisk"]["status"] if report else "NOT_EVALUATED"
    if historical["duplicateRisk"] == "HIGH":
        duplicate = "HIGH"
        if not any(r["code"] == "ENGINE_DUPLICATE_RISK" for r in reasons):
            reasons.append(
                {
                    "code": "ENGINE_DUPLICATE_RISK",
                    "source": "HISTORICAL_SIGNATURE_COMPARISON",
                    "reason": "Opening, progression and final physical function reuse a historical engine without supported novelty.",
                }
            )
    penalties = []
    codes = {finding["code"] for finding in report["findings"]} if report else set()
    for code, policy in PENALTY_POLICY.items():
        triggers = sorted(codes.intersection(policy["findings"]))
        if triggers:
            penalties.append(
                {"code": code, "points": policy["points"], "scope": "RANKING_SCORE", "evidence": triggers}
            )
    if duplicate in {"MODERATE", "HIGH"}:
        penalties.append(
            {
                "code": "DUPLICATE_ENGINE",
                "points": 25 if duplicate == "HIGH" else 8,
                "scope": "RANKING_SCORE",
                "evidence": [historical["closestHistoricalEngine"]],
            }
        )
    feasibility = report["productionFeasibilityScore"] if report else None
    if feasibility is not None and feasibility < 100:
        penalties.append(
            {
                "code": "PRODUCTION_COMPLEXITY",
                "points": 0,
                "secondaryPoints": 100 - feasibility,
                "scope": "CLOSE_SCORE_TIE_BREAK_ONLY",
                "evidence": report["productionRisks"],
            }
        )
    dimensions = []
    if report:
        for name, source, weight in DIMENSIONS:
            value = report
            for part in source.split("."):
                value = value[part]
            dimensions.append(
                {
                    "dimension": name,
                    "score": value,
                    "weightPercent": weight,
                    "source": f"SHORT_FORM_ENGINE.{source}",
                }
            )
    base_units = sum(d["score"] * d["weightPercent"] for d in dimensions)
    penalty_points = sum(p["points"] for p in penalties)
    eligible = not reasons and report is not None
    cpq = (
        assess_cpq(
            {
                "originalPrompt": text,
                "candidatePrompt": text,
                "durationSeconds": normalized["intendedDurationSeconds"],
            }
        )
        if text.strip()
        else None
    )
    return {
        "candidateId": normalized["id"],
        "title": normalized.get("title"),
        "normalizedConcept": normalized,
        "eligibility": "ELIGIBLE" if eligible else "INELIGIBLE",
        "missingFields": missing,
        "eligibilityReasons": reasons,
        "shortFormScore": report["shortFormScore"] if report else None,
        "rankingScore": max(0, base_units - penalty_points * 100) / 100 if eligible else None,
        "baseCompositeScore": base_units / 100 if eligible else None,
        "rankingDimensions": dimensions,
        "penalties": penalties,
        "rankingPenaltyPoints": penalty_points,
        "duplicateRisk": duplicate,
        "productionRisk": {
            "score": feasibility,
            "flags": report["productionRisks"] if report else [],
            "evidenceStatus": "TEXT_RISK_SCREEN_ONLY",
        },
        "productionEfficiency": {
            "score": feasibility,
            "source": "SHORT_FORM_ENGINE.productionFeasibilityScore",
            "use": "Secondary only within a 3-point anchored quality band; no verified monetary cost estimate.",
        },
        "strengths": [d for d in dimensions if d["score"] >= 85],
        "weaknesses": report["findings"] if report else [],
        "shortFormEngine": report,
        "cpqPreview": cpq,
        "historicalComparison": historical,
        "engineSignature": signature,
        "renderAuthorized": False,
    }


def _comparison(row: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    a = {d["dimension"]: d["score"] for d in row["rankingDimensions"]}
    b = {d["dimension"]: d["score"] for d in other["rankingDimensions"]}
    values = [
        {"dimension": name, "candidateScore": a[name], "otherScore": b[name], "difference": a[name] - b[name]}
        for name in a
    ]
    return {
        "candidateId": row["candidateId"],
        "otherCandidateId": other["candidateId"],
        "dimensions": values,
        "rankingScore": [row["rankingScore"], other["rankingScore"]],
        "duplicateRisk": [row["duplicateRisk"], other["duplicateRisk"]],
        "rankingPenaltyPoints": [row["rankingPenaltyPoints"], other["rankingPenaltyPoints"]],
        "productionEfficiency": [
            row["productionEfficiency"]["score"],
            other["productionEfficiency"]["score"],
        ],
    }


def rank_concepts(candidates: list[ConceptInput | dict[str, Any] | str]) -> dict[str, Any]:
    if not 1 <= len(candidates) <= 30:
        raise ValueError("Provide 1–30 supplied concepts")
    rows = [validate_concept(candidate) for candidate in candidates]
    ids = [row["candidateId"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(
            "Duplicate candidate IDs: " + ", ".join(sorted({key for key in ids if ids.count(key) > 1}))
        )
    rows.sort(key=lambda row: row["candidateId"])
    raw = sorted(
        (row for row in rows if row["eligibility"] == "ELIGIBLE"),
        key=lambda row: (-row["rankingScore"], row["candidateId"]),
    )
    for index, row in enumerate(raw):
        row["rawRank"] = index + 1
    # Anchored bands avoid a non-transitive pairwise "within N points" comparator.
    remaining, ranked, bands = raw[:], [], []
    while remaining:
        anchor = remaining[0]["rankingScore"]
        group = [row for row in remaining if anchor - row["rankingScore"] <= TIE_MARGIN]
        remaining = [row for row in remaining if anchor - row["rankingScore"] > TIE_MARGIN]
        group.sort(
            key=lambda row: (-row["productionEfficiency"]["score"], -row["rankingScore"], row["candidateId"])
        )
        for row in group:
            row["tieBand"] = len(bands) + 1
        bands.append(
            {
                "anchorRankingScore": anchor,
                "candidateIds": [row["candidateId"] for row in group],
                "margin": TIE_MARGIN,
            }
        )
        ranked.extend(group)
    for index, row in enumerate(ranked):
        row["rank"] = index + 1
        other = ranked[index - 1] if index else (ranked[1] if len(ranked) > 1 else None)
        if other:
            comparison = _comparison(row, other)
            close = row["tieBand"] == other["tieBand"]
            basis = (
                "PRODUCTION_EFFICIENCY_TIE_BREAK"
                if close and row["productionEfficiency"]["score"] != other["productionEfficiency"]["score"]
                else "QUALITY_SCORE"
            )
            if (
                row["rankingScore"] == other["rankingScore"]
                and row["productionEfficiency"]["score"] == other["productionEfficiency"]["score"]
            ):
                basis = "STABLE_ID_TIE_BREAK"
            concrete = "; ".join(
                f"{d['dimension']} {d['candidateScore']} vs {d['otherScore']}"
                for d in comparison["dimensions"]
                if d["difference"]
            )
            row["whyRankedHere"] = {
                "basis": basis,
                "comparison": comparison,
                "text": f"Rank {index + 1} vs {other['candidateId']}: composite {row['rankingScore']:g} vs {other['rankingScore']:g}; {concrete or 'all creative dimensions equal'}; ranking penalties {row['rankingPenaltyPoints']} vs {other['rankingPenaltyPoints']}; duplicate risk {row['duplicateRisk']} vs {other['duplicateRisk']}; production efficiency {row['productionEfficiency']['score']} vs {other['productionEfficiency']['score']}; {basis}.",
            }
        else:
            row["whyRankedHere"] = {
                "basis": "ONLY_ELIGIBLE_CANDIDATE",
                "text": f"Only eligible concept: hook {row['shortFormEngine']['hookScore']}, progress {row['shortFormEngine']['progressDensityScore']}, payoff {row['shortFormEngine']['payoffScore']}.",
            }
    slate, adjustments, pending = [], [], ranked[:]
    while pending and len(slate) < 3:
        available = [
            row
            for row in pending
            if not any(
                len(_axes(row["engineSignature"], selected["engineSignature"])) >= 2 for selected in slate
            )
        ]
        if not available:
            adjustments.append(
                {
                    "code": "SLATE_UNDERFILLED_DUPLICATE_ENGINES",
                    "deferredCandidateIds": [row["candidateId"] for row in pending],
                }
            )
            break
        chosen, baseline = available[0], pending[0]
        if baseline["rankingScore"] - chosen["rankingScore"] > DIVERSITY_MARGIN:
            adjustments.append(
                {
                    "code": "SLATE_UNDERFILLED_QUALITY_GAP",
                    "candidateId": chosen["candidateId"],
                    "gap": round(baseline["rankingScore"] - chosen["rankingScore"], 2),
                }
            )
            break
        if chosen is not baseline:
            adjustments.append(
                {
                    "code": "DIVERSITY_PROMOTION",
                    "candidateId": chosen["candidateId"],
                    "aheadOfCandidateIds": [r["candidateId"] for r in pending[: pending.index(chosen)]],
                    "qualityGap": round(max(0, baseline["rankingScore"] - chosen["rankingScore"]), 2),
                }
            )
        slate.append(chosen)
        pending.remove(chosen)
    rejected = [row for row in rows if row["eligibility"] == "INELIGIBLE"]
    output = {
        "workflow": "CONCEPT_CANDIDATE_RANKING",
        "version": VERSION,
        "policy": {
            "dimensions": [
                {"dimension": name, "source": source, "weightPercent": weight}
                for name, source, weight in DIMENSIONS
            ],
            "tieMargin": TIE_MARGIN,
            "diversityMargin": DIVERSITY_MARGIN,
            "penalties": PENALTY_POLICY,
            "duplicatePenalty": {"HIGH": 25, "MODERATE": 8},
            "productionComplexity": "0 quality points; feasibility deficit applies only in close-score ordering",
            "rationale": "Hook/instant clarity carry 30%, progression/escalation 28%, payoff 18%; no moral/dialogue/decorative score. Novelty is an explicit risk penalty, costs secondary. CPQ previews remain uncalibrated and unscored.",
        },
        "rankedEligibleCandidates": ranked,
        "revisionCandidates": rejected,
        "productionSlate": [
            {
                "productionRank": index + 1,
                "candidateId": row["candidateId"],
                "rank": row["rank"],
                "rankingScore": row["rankingScore"],
            }
            for index, row in enumerate(slate)
        ],
        "firstRenderCandidate": slate[0]["candidateId"] if slate else None,
        "whyThisBeatsTheOthers": [
            _comparison(slate[0], row) for row in ranked if slate and row is not slate[0]
        ],
        "tieBands": bands,
        "diversityAdjustments": adjustments,
        "inputFingerprint": _sha(_canonical([row["normalizedConcept"] for row in rows])),
        "renderAuthorized": False,
        "providerCalls": 0,
        "conceptsGenerated": 0,
        "limitations": [
            "Editorial recommendations require later prompt/canonical/render admission checks.",
            "Accepted English text validators and two-reference historical corpus retain their limitations.",
            "No calibrated CPQ grade, actual-frame verification, audience prediction or monetary cost estimate is invented.",
        ],
    }
    output["reportLines"] = project_report(output)
    return output


def project_report(result: dict[str, Any]) -> list[str]:
    lines = ["Concept production ranking (editorial; render admission remains separate)"]
    first = result.get("firstRenderCandidate")
    lines.append(f"Produce first: {first}" if first else "Produce first: none; revise the excluded concepts.")
    for row in result.get("rankedEligibleCandidates", []):
        lines.append(
            f"{row['rank']}. {row['candidateId']} — {row['title']}: ranking {row['rankingScore']:g}; short form {row['shortFormScore']}; hook {row['shortFormEngine']['hookScore']}; progress {row['shortFormEngine']['progressDensityScore']}; payoff {row['shortFormEngine']['payoffScore']}; duplicate {row['duplicateRisk']}; production efficiency {row['productionEfficiency']['score']}."
        )
        lines.append(row["whyRankedHere"]["text"])
        for penalty in row["penalties"]:
            lines.append(
                f"Penalty {penalty['code']}: {penalty['points']} quality points; scope {penalty['scope']}."
            )
    for row in result.get("revisionCandidates", []):
        lines.append(
            f"INELIGIBLE {row['candidateId']}: "
            + "; ".join(reason["reason"] for reason in row["eligibilityReasons"])
        )
    for adjustment in result.get("diversityAdjustments", []):
        lines.append("Diversity: " + _canonical(adjustment))
    return lines
