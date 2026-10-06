"""Canonical pre-render evidence accessors.

The parser writes beat evidence once. Rule evaluators, family scoring, assessment and
UI projections read it here; none of them re-derive attempts from raw action text.
This module contains normalization/accessor logic only. It does not contain thresholds
or performance data.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .contracts import RuleEvaluation, RuleOutcome

CANONICAL_EVIDENCE_VERSION = "canonical-attempt-evidence-v2"
UNSPECIFIED_VERB = "UNSPECIFIED"
EVIDENCE_INCOMPLETE_FAILURE = "EVIDENCE_INCOMPLETE"


@dataclass(frozen=True)
class AttemptEvidence:
    """Canonical active-attempt and strategy evidence for one plan."""

    count: int
    beat_ids: tuple[str, ...]
    verbs: tuple[str, ...]
    strategy_families: tuple[str, ...]
    active_seconds: float
    active_ratio: float
    sources: dict[str, int]
    attempts: tuple[dict[str, Any], ...]

    @property
    def active_attempt_count(self) -> int:
        return self.count

    @property
    def distinct_strategy_count(self) -> int:
        return len(set(self.strategy_families))


def is_unspecified_verb(verb: object) -> bool:
    text = str(verb or "").strip().upper()
    return text in {"", UNSPECIFIED_VERB}


def _words(text: object) -> set[str]:
    return {word.upper() for word in re.findall(r"[A-Za-z]+", str(text or ""))}


def normalize_strategy_family(primary_verb: object, action: object = "", consequence: object = "") -> str:
    """Normalize a concrete action into a conservative mechanical strategy family.

    Synonyms and force/angle variants share a family; materially different mechanics do
    not. Unknown verbs remain explicit ``OTHER:<verb>`` rather than being silently
    merged with a neighboring strategy.
    """

    text = f"{primary_verb or ''} {action or ''} {consequence or ''}".upper()
    primary_words = _words(primary_verb)
    words = _words(text)
    direct = (
        ("PULL", {"PULL", "PULLS", "PULLED", "YANK", "YANKS", "YANKED", "TUG", "TUGS", "TUGGED", "DRAG", "DRAGS", "DRAGGED", "HAUL", "HAULS"}),
        ("PUSH", {"PUSH", "PUSHES", "PUSHED", "SHOVE", "SHOVES", "SHOVED"}),
        ("SHAKE", {"SHAKE", "SHAKES", "SHAKING", "SHAKEN", "JIGGLE", "JIGGLES", "JIGGLED"}),
        ("POUR", {"POUR", "POURS", "POURED", "POURING"}),
        ("ADD", {"ADD", "ADDS", "ADDED", "INSERT", "INSERTS", "INSERTED", "PLACE", "PLACES", "PLACED"}),
        ("STIR", {"STIR", "STIRS", "STIRRED", "STIRRING"}),
        ("SQUEEZE", {"SQUEEZE", "SQUEEZES", "SQUEEZED", "SQUEEZING"}),
        ("THROW_TOSS", {"THROW", "THROWS", "THREW", "TOSS", "TOSSES", "TOSSED", "FLING", "FLINGS"}),
        ("CATCH", {"CATCH", "CATCHES", "CAUGHT"}),
        ("LIFT", {"LIFT", "LIFTS", "LIFTED", "RAISE", "RAISES", "RAISED"}),
        ("HOLD", {"HOLD", "HOLDS", "HELD", "GRIP", "GRIPS", "GRIPPED"}),
    )
    if primary_words.intersection({"GRAB", "GRABS", "GRABBED"}):
        return "PULL" if words.intersection({"PULL", "PULLS", "BACKWARD", "TOWARD", "AWAY", "LEAN", "LEANS"}) else "GRAB_HOLD"
    for family, candidates in direct:
        if primary_words.intersection(candidates):
            return family
    verb = str(primary_verb or "").strip().upper()
    return UNSPECIFIED_VERB if is_unspecified_verb(verb) else f"OTHER:{verb}"


def strategy_family_for_beat(beat: dict[str, Any]) -> str:
    return str(
        beat.get("strategyFamily")
        or normalize_strategy_family(beat.get("primaryVerb"), beat.get("action"), beat.get("consequence"))
    )


def _target_tokens(beat: dict[str, Any]) -> set[str]:
    text = " ".join(
        str(beat.get(key, ""))
        for key in ("targetObject", "action", "consequence", "result", "intendedEffect")
    )
    return _words(text).difference(
        {
            "THE", "A", "AN", "AND", "WITH", "FROM", "TO", "IT", "HE", "SHE", "THIS", "THAT",
            "BALL", "WALL", "ROPE", "BOX", "CUP", "DOOR", "BOOK", "MAT", "CHEEK", "OBJECT",
        }
    )


def _canonical_attempt(beat: dict[str, Any], video_plan_ir: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    characters = video_plan_ir.get("characters") or {}
    core = video_plan_ir.get("coreMechanic") or {}
    actor = beat.get("actor") or characters.get("primary")
    target = beat.get("targetObject") or core.get("primaryObject")
    if not target:
        props = (video_plan_ir.get("setting") or {}).get("mainProps") or []
        target = props[0] if props else None
    family = strategy_family_for_beat(beat)
    previous_family = previous.get("strategyFamily") if previous else None
    distinct = previous is None or family != previous_family
    source = str(beat.get("attemptSource") or "UNKNOWN")
    confidence = beat.get("attemptConfidence")
    if confidence is None:
        confidence = {"EXPLICIT_ATTEMPT_LABEL": 1.0, "STRUCTURED_PLAN_ROLE": 0.95, "SEMANTIC_INFERENCE": 0.9}.get(source)
    goal_evidence = video_plan_ir.get("goalEvidence") or {}
    return {
        "beatId": str(beat.get("id", "")),
        "actor": actor,
        "goal": beat.get("goal") or goal_evidence.get("description"),
        "strategyFamily": family,
        "primaryAction": beat.get("primaryAction") or beat.get("action", ""),
        "targetObject": target,
        "intendedEffect": beat.get("intendedEffect") or goal_evidence.get("intendedEffect"),
        "result": beat.get("result") or beat.get("consequence", ""),
        "source": source,
        "confidence": confidence,
        "distinctFromPreviousAttempt": distinct,
        "reason": beat.get("attemptReason") or "The beat has canonical goal-directed attempt evidence.",
    }


def attempt_beats(video_plan_ir: dict[str, Any]) -> list[dict[str, Any]]:
    return [beat for beat in video_plan_ir.get("beats", []) if beat.get("isAttempt", False)]


def attempt_evidence(video_plan_ir: dict[str, Any]) -> AttemptEvidence:
    attempts = attempt_beats(video_plan_ir)
    duration = float(video_plan_ir.get("metadata", {}).get("duration", 15.0) or 0.0)
    active_seconds = float(sum(float(beat.get("duration", 0.0) or 0.0) for beat in attempts))
    records: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for beat in attempts:
        record = _canonical_attempt(beat, video_plan_ir, previous)
        records.append(record)
        previous = record
    families = tuple(str(record["strategyFamily"]) for record in records)
    sources = Counter(str(record["source"]) for record in records)
    return AttemptEvidence(
        count=len(records),
        beat_ids=tuple(str(record["beatId"]) for record in records),
        verbs=tuple(str(beat.get("primaryVerb", "")).strip().upper() for beat in attempts),
        strategy_families=families,
        active_seconds=active_seconds,
        active_ratio=active_seconds / duration if duration > 0 else 0.0,
        sources=dict(sources),
        attempts=tuple(records),
    )


def _beat_objects(beat: dict[str, Any]) -> set[str]:
    explicit = str(beat.get("targetObject") or "").strip().upper()
    if explicit:
        return {explicit}
    words = _words(" ".join(str(beat.get(key, "")) for key in ("action", "consequence", "result")))
    return words.intersection({"BALL", "WALL", "ROPE", "BOX", "CUP", "DOOR", "BOOK", "MAT", "CHEEK", "FLOOR", "HAND"})


def escalation_evidence(video_plan_ir: dict[str, Any]) -> dict[str, Any]:
    beats = video_plan_ir.get("beats", [])
    attempts = attempt_beats(video_plan_ir)
    if not attempts:
        return {"status": "UNKNOWN", "reason": "No canonical goal-directed attempt window exists.", "new_target": False, "intensity_rise": False, "consequence_expansion": False}
    baseline_objects = set().union(*(_beat_objects(beat) for beat in attempts[:1])) if attempts else set()
    escalation_beats = [beat for beat in beats if beat.get("beatRole") == "ESCALATION" or beat.get("consequenceType") == "escalation"]
    later_beats = [beat for beat in beats if float(beat.get("startTime", 0.0)) >= float(attempts[0].get("startTime", 0.0))]
    candidate_beats = escalation_beats or later_beats
    candidate_objects = set().union(*(_beat_objects(beat) for beat in candidate_beats)) if candidate_beats else set()
    new_target = bool(candidate_objects - baseline_objects)
    intensities = [float(beat.get("intensity", 0) or 0) for beat in attempts + escalation_beats]
    intensity_rise = len(intensities) >= 2 and max(intensities[1:]) > intensities[0]
    expansion_words = {"FLEX", "FLEXES", "STRETCH", "STRETCHES", "WHOLE", "WALL", "LARGER", "BIGGER", "ENTIRE", "ITSELF"}
    consequence_expansion = bool(expansion_words.intersection(_words(" ".join(str(beat.get("consequence", "")) for beat in candidate_beats))))
    new_target = bool(candidate_objects - baseline_objects) or consequence_expansion
    available = len(attempts) >= 2 or bool(escalation_beats)
    status = "AVAILABLE" if available else "UNKNOWN"
    reason = (
        "Escalation changes intensity, affected target or consequence scale."
        if (new_target or intensity_rise or consequence_expansion)
        else "No increasing intensity, target, stakes or consequence scale was evidenced."
    )
    return {
        "status": status,
        "reason": reason,
        "new_target": new_target,
        "newTarget": new_target,
        "intensity_rise": intensity_rise,
        "intensityRise": intensity_rise,
        "consequence_expansion": consequence_expansion,
        "consequenceExpansion": consequence_expansion,
        "candidateBeatIds": [str(beat.get("id", "")) for beat in candidate_beats],
    }


def beat_audit(video_plan_ir: dict[str, Any]) -> list[dict[str, Any]]:
    """Human-readable audit of every beat's role versus strategy evidence."""
    attempts = {record["beatId"]: record for record in attempt_evidence(video_plan_ir).attempts}
    audit: list[dict[str, Any]] = []
    for beat in video_plan_ir.get("beats", []):
        record = attempts.get(str(beat.get("id", "")))
        audit.append(
            {
                "beatId": beat.get("id"),
                "beatRole": beat.get("beatRole", ""),
                "action": beat.get("action", ""),
                "goal": (record or {}).get("goal") or beat.get("goal"),
                "strategyFamily": beat.get("strategyFamily") or strategy_family_for_beat(beat),
                "isAttempt": bool(beat.get("isAttempt", False)),
                "attemptSource": beat.get("attemptSource", "NONE"),
                "distinctFromPreviousAttempt": (record or {}).get("distinctFromPreviousAttempt"),
                "reason": (record or {}).get("reason") or (beat.get("attemptCandidate") or {}).get("reason") or "Narrative beat has no canonical goal-directed attempt evidence.",
            }
        )
    return audit


def is_evidence_gap(evaluation: RuleEvaluation) -> bool:
    if evaluation.outcome in (RuleOutcome.UNKNOWN, RuleOutcome.SERVICE_ERROR):
        return True
    return evaluation.outcome is RuleOutcome.FAIL and evaluation.details.get("failureBasis") == EVIDENCE_INCOMPLETE_FAILURE


def evidence_gap_kind(evaluation: RuleEvaluation) -> str:
    if evaluation.outcome is RuleOutcome.UNKNOWN:
        return "UNKNOWN"
    if evaluation.outcome is RuleOutcome.SERVICE_ERROR:
        return "SERVICE_ERROR"
    return "EVIDENCE_INCOMPLETE_FAIL"


def unscored_families(evaluations: Iterable[RuleEvaluation]) -> tuple[str, ...]:
    scoring = {RuleOutcome.PASS, RuleOutcome.FAIL, RuleOutcome.SERVICE_ERROR}
    families: dict[str, bool] = {}
    for evaluation in evaluations:
        families[evaluation.family] = families.get(evaluation.family, False) or evaluation.outcome in scoring
    return tuple(family for family, has_signal in families.items() if not has_signal)
