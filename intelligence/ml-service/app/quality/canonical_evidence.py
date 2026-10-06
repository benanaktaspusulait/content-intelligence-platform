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


@dataclass(frozen=True)
class EngineProfileEvidence:
    profile: str
    source: str
    confidence: str
    active: bool
    candidate_only: bool
    signals: dict[str, bool]
    recurrence_count: int
    intervention_count: int
    state_memory_cost: str
    reason: str


def _engine_profile_payload(video_plan_ir: dict[str, Any]) -> dict[str, Any]:
    root = video_plan_ir.get("engineProfile")
    core = (video_plan_ir.get("coreMechanic") or {}).get("engineProfile")
    return root if isinstance(root, dict) else core if isinstance(core, dict) else {}


def engine_profile_evidence(video_plan_ir: dict[str, Any]) -> EngineProfileEvidence:
    """Resolve Spoon-class evidence; MEDIUM/LOW never activates exceptions."""
    beats = list(video_plan_ir.get("beats") or [])
    payload = _engine_profile_payload(video_plan_ir)
    explicit = payload.get("engineProfile") == "STUBBORN_RETURN_LOOP" and payload.get("engineProfileSource") == "EXPLICIT"
    all_text = " ".join(str(beat.get(key, "")) for beat in beats for key in ("action", "consequence")).lower()
    words = _words(all_text)
    core = video_plan_ir.get("coreMechanic") or {}
    object_signal = bool(core.get("primaryObject") or payload.get("dominantObject"))
    boundary_signal = bool((payload.get("boundary") or {}).get("type")) or bool(
        words.intersection({"EDGE", "HOLE", "LINE", "SHELF", "DOORWAY", "ZONE", "MARKED"})
    )
    safe_signal = bool((payload.get("boundary") or {}).get("safeState")) or any(
        phrase in all_text for phrase in ("safe", "inward", "away from", "pulls in", "pulled in")
    )
    return_signal = bool(payload.get("autonomousReturn") is True) or any(
        phrase in all_text for phrase in ("by itself", "itself", "returns", "slides back", "goes back", "back to")
    )
    recurrence_count = int(payload.get("recurrenceCount") or 0)
    if recurrence_count < 2:
        recurrence_count = max(0, sum(all_text.count(phrase) for phrase in ("by itself", "returns", "slides back", "goes back")))
    recurrence_signal = recurrence_count >= 2
    intervention_count = sum(1 for beat in beats if beat.get("isAttempt") or any(
        word in _words(str(beat.get("action", ""))) for word in ("PULL", "PULLS", "GRAB", "GRABS", "HOLD", "HOLDS", "PIN", "PINS")
    ))
    intervention_signal = intervention_count >= 2
    intensities = [float(beat.get("intensity", 0) or 0) for beat in beats]
    escalation_signal = bool(payload.get("resistanceEscalation") or payload.get("emotionalEscalation")) or (
        len(intensities) >= 2 and max(intensities[-2:]) > intensities[0]
    )
    no_dead_reset = not any(word in all_text for word in ("reset", "waits", "stands still", "long stare", "nothing changes"))
    signals = {
        "SINGLE_DOMINANT_OBJECT": object_signal,
        "FIXED_VISIBLE_BOUNDARY": boundary_signal,
        "SAFE_STATE": safe_signal,
        "AUTONOMOUS_RETURN": return_signal,
        "RECURRENCE": recurrence_signal,
        "CHARACTER_INTERVENTION": intervention_signal,
        "ESCALATION": escalation_signal,
        "NO_DEAD_RESET": no_dead_reset,
    }
    state_memory_cost = "HIGH" if sum(1 for phrase in ("inside", "outside", "reinsert", "catch", "transfer") if phrase in all_text) >= 3 else "LOW"
    if explicit:
        valid = all(signals.values())
        return EngineProfileEvidence("STUBBORN_RETURN_LOOP", "EXPLICIT", "HIGH" if valid else "LOW", valid, False, signals, recurrence_count, intervention_count, state_memory_cost, "Explicit profile is active only when every mandatory signal is valid.")
    score = sum(signals.values())
    confidence = "HIGH" if score == len(signals) else "MEDIUM" if score >= 5 else "LOW"
    active = confidence == "HIGH"
    return EngineProfileEvidence("STUBBORN_RETURN_LOOP" if score >= 4 else "DEFAULT", "INFERRED" if score else "NONE", confidence, active, bool(score and not active), signals, recurrence_count, intervention_count, state_memory_cost, "All mandatory deterministic return-loop signals are present." if active else "Return-loop candidate lacks one or more mandatory signals.")


@dataclass(frozen=True)
class StoryDensityEvidence:
    major_beat_count: int
    micro_beat_count: int
    state_transition_count: int
    strategy_change_count: int
    critical_beat_durations: tuple[float, ...]
    generation_mode: str
    temporal_load: str
    split_recommendation: str | None
    goal_status: str
    obstruction_status: str
    realization_status: str
    payoff_status: str
    continuation_status: str
    continuation_mismatches: tuple[str, ...]


_MAJOR_ROLES = frozenset({
    "HOOK", "DISCOVERY", "ATTEMPT", "ESCALATION", "REALIZATION", "DECISION",
    "SOLUTION", "PAYOFF", "TWIST", "FAKE_RESOLUTION", "FAILURE",
})
_MICRO_ROLES = frozenset({"REACTION", "TRANSITION", "MICRO_ACTION", "IDLE"})
_CONTINUATION_FIELDS = (
    "character", "characterPoseIntent", "heldObjects", "objectStates", "objectState", "camera", "environment", "unresolvedAction"
)


def _is_major_beat(beat: dict[str, Any]) -> bool:
    if isinstance(beat.get("majorBeat"), bool):
        return bool(beat["majorBeat"])
    role = str(beat.get("beatRole") or "").upper()
    if role in _MICRO_ROLES:
        return False
    if role in _MAJOR_ROLES:
        return True
    return beat.get("consequenceType") in {"new", "escalation", "fake_win"}


def _continuation_mismatches(ir: dict[str, Any]) -> tuple[str, ...]:
    split = ir.get("splitPlan") or {}
    part1 = (split.get("part1") or {}).get("endState") or {}
    part2 = (split.get("part2") or {}).get("startState") or {}
    if not part1 or not part2:
        return ()
    return tuple(field for field in _CONTINUATION_FIELDS if part1.get(field) != part2.get(field))


def story_density_evidence(video_plan_ir: dict[str, Any]) -> StoryDensityEvidence:
    beats = list(video_plan_ir.get("beats") or [])
    major = [beat for beat in beats if _is_major_beat(beat)]
    micro = [beat for beat in beats if not _is_major_beat(beat)]
    transitions = video_plan_ir.get("storyEvidence", {}).get("stateTransitionCount")
    if not isinstance(transitions, int):
        transitions = 0
        for index, beat in enumerate(beats):
            if index == 0 or beat.get("visualStateId") != beats[index - 1].get("visualStateId"):
                transitions += 1
            if beat.get("consequenceType") in {"new", "escalation", "fake_win"} and index > 0:
                transitions += 1
    attempts = attempt_evidence(video_plan_ir)
    strategy_changes = sum(
        1 for before, after in zip(attempts.strategy_families, attempts.strategy_families[1:]) if before != after
    )
    critical_durations = tuple(
        float(beat.get("duration", 0.0) or 0.0) for beat in major if float(beat.get("duration", 0.0) or 0.0) > 0
    )
    mode = str((video_plan_ir.get("metadata") or {}).get("generationMode") or "SINGLE_15S")
    overloaded = (
        len(major) > 6
        or transitions > 6
        or strategy_changes > 4
        or (len(critical_durations) >= 4 and min(critical_durations) < 1.5)
    )
    goal = video_plan_ir.get("goalEvidence") or {}
    goal_status = str(goal.get("goalExplicitness") or "UNKNOWN")
    obstruction_status = "AVAILABLE" if goal.get("obstruction") else "UNKNOWN"
    realization_status = "AVAILABLE" if any(
        str(beat.get("beatRole", "")).upper() in {"REALIZATION", "DECISION"}
        or any(word in str(beat.get("action", "")).lower() for word in ("realize", "understand", "decide", "notices"))
        for beat in beats
    ) else "UNKNOWN"
    payoff = video_plan_ir.get("finalPayoff") or {}
    payoff_status = "AVAILABLE" if payoff.get("startsAt") is not None or any(
        str(beat.get("beatRole", "")).upper() in {"PAYOFF", "SOLUTION", "TWIST"} for beat in beats
    ) else "UNKNOWN"
    mismatches = _continuation_mismatches(video_plan_ir)
    continuation_status = (
        "NOT_APPLICABLE" if mode != "SPLIT_2X15S"
        else "UNKNOWN" if not (video_plan_ir.get("splitPlan") or {})
        else "FAIL" if mismatches else "PASS"
    )
    return StoryDensityEvidence(
        major_beat_count=len(major),
        micro_beat_count=len(micro),
        state_transition_count=transitions,
        strategy_change_count=strategy_changes,
        critical_beat_durations=critical_durations,
        generation_mode=mode,
        temporal_load="HIGH" if overloaded else "MANAGEABLE",
        split_recommendation="RECOMMEND_SPLIT_2X15" if overloaded else None,
        goal_status=goal_status,
        obstruction_status=obstruction_status,
        realization_status=realization_status,
        payoff_status=payoff_status,
        continuation_status=continuation_status,
        continuation_mismatches=mismatches,
    )


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
