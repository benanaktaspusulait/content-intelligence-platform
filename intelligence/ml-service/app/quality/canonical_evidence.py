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
    canonical_confidence: float | None

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
    """Normalize the concrete mechanical action into a conservative family.

    ``targetObject``, ``intendedEffect`` and result prose are evidence about what
    the action is trying to achieve, not strategy names. The primary verb wins;
    action text is only a fallback when a structured verb is unavailable.
    """

    primary_words = _words(primary_verb)
    action_words = _words(action)
    source_words = primary_words or action_words
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
    if source_words.intersection({"GRAB", "GRABS", "GRABBED"}):
        return "GRAB_HOLD"
    for family, candidates in direct:
        if source_words.intersection(candidates):
            return family
    verb = str(primary_verb or "").strip().upper()
    return UNSPECIFIED_VERB if is_unspecified_verb(verb) else f"OTHER:{verb}"


def strategy_semantics_for_beat(beat: dict[str, Any]) -> dict[str, str]:
    """Separate the physical first action from the intended attempt strategy."""
    action_family = normalize_strategy_family(beat.get("primaryVerb"), beat.get("action"))
    result_text = " ".join(
        str(beat.get(key, "")) for key in ("action", "consequence", "result", "goal", "targetObject", "intendedEffect")
    )
    result_words = _words(result_text)
    derived_family = action_family
    strategy_intent = "DIRECT"
    strategy_role = "INTENDED"
    if result_words.intersection({"SPOT", "SITTING", "SIT", "SQUAT", "COMMIT"}) and (result_words.intersection({"CAT", "TARGET", "EMPTY"}) or action_family.startswith("OTHER:")):
        derived_family = "COMMIT_TO_TARGET"
        strategy_intent = "CLAIM_TARGET"
    elif "CAT" in result_words and "OUT" in result_words:
        derived_family = "DISPLACE"
        strategy_intent = "REMOVE_OBSTRUCTION"
    elif "BOX" in result_words and (action_family == "LIFT" or result_words.intersection({"MOVE", "MOVES", "MOVING"})):
        derived_family = "RELOCATE"
        strategy_intent = "CHANGE_TARGET_LOCATION"
    elif "BOX" in result_words and result_words.intersection({"WATCH", "WATCHES", "GUARD", "GUARDS", "STAYS", "CAREFULLY"}):
        derived_family = "GUARD"
        strategy_intent = "PREVENT_RECLAIM"
    if action_family == "CATCH" and result_words.intersection(
        {"SQUEEZE", "SQUEEZES", "SQUEEZED", "TEST", "TESTS", "CHECK", "CHECKS", "NORMAL", "NORMALLY"}
    ):
        derived_family = "SQUEEZE" if result_words.intersection({"SQUEEZE", "SQUEEZES", "SQUEEZED"}) else "TEST"
        strategy_intent = "TEST_OBJECT_BEHAVIOR"
        strategy_role = "REACTIVE_SETUP"
    declared_family = str(beat.get("intendedStrategyFamily") or beat.get("strategyFamily") or "").strip().upper()
    known_families = {
        "UNSPECIFIED", "PULL", "PUSH", "SHAKE", "POUR", "ADD", "STIR", "SQUEEZE",
        "THROW_TOSS", "CATCH", "LIFT", "HOLD", "GRAB_HOLD", "TEST",
    }
    intended_family = (
        declared_family
        if declared_family in {action_family, derived_family} or (action_family == UNSPECIFIED_VERB and declared_family in known_families)
        else derived_family
    )
    return {
        "reactiveActionFamily": action_family,
        "intendedStrategyFamily": intended_family,
        "strategyIntent": strategy_intent,
        "strategyRole": strategy_role,
    }


def strategy_family_for_beat(beat: dict[str, Any]) -> str:
    return strategy_semantics_for_beat(beat)["intendedStrategyFamily"]


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
    semantics = strategy_semantics_for_beat(beat)
    family = semantics["intendedStrategyFamily"]
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
        "reactiveActionFamily": semantics["reactiveActionFamily"],
        "intendedStrategyFamily": family,
        "strategyRole": semantics["strategyRole"],
        "strategyIntent": semantics["strategyIntent"],
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
    confidences = [
        float(record["confidence"])
        for record in records
        if isinstance(record.get("confidence"), (int, float))
    ]
    return AttemptEvidence(
        count=len(records),
        beat_ids=tuple(str(record["beatId"]) for record in records),
        verbs=tuple(str(beat.get("primaryVerb", "")).strip().upper() for beat in attempts),
        strategy_families=families,
        active_seconds=active_seconds,
        active_ratio=active_seconds / duration if duration > 0 else 0.0,
        sources=dict(sources),
        attempts=tuple(records),
        canonical_confidence=min(confidences) if confidences else None,
    )


def _beat_objects(beat: dict[str, Any]) -> set[str]:
    explicit = str(beat.get("targetObject") or "").strip().upper()
    if explicit:
        return {explicit}
    words = _words(" ".join(str(beat.get(key, "")) for key in ("action", "consequence", "result")))
    return words.intersection({"BALL", "WALL", "ROPE", "BOX", "CUP", "DOOR", "BOOK", "MAT", "CHEEK", "FLOOR", "HAND"})


@dataclass(frozen=True)
class CanonicalEscalationEvidence:
    """Typed escalation evidence independent of active-attempt classification."""

    status: str
    reason: str
    candidate_beat_ids: tuple[str, ...]
    new_target: bool
    intensity_rise: bool
    consequence_expansion: bool
    resistance: bool
    wall_flex: bool
    force_rise: bool
    deformation: bool
    scope_expansion: bool
    difficulty_rise: bool
    stakes_rise: bool
    persistence: bool
    quantity_growth: bool
    applicability: str
    strength: str
    source: str
    confidence: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "candidateBeatIds": list(self.candidate_beat_ids),
            "candidate_beat_ids": list(self.candidate_beat_ids),
            "newTarget": self.new_target,
            "new_target": self.new_target,
            "intensityRise": self.intensity_rise,
            "intensity_rise": self.intensity_rise,
            "consequenceExpansion": self.consequence_expansion,
            "consequence_expansion": self.consequence_expansion,
            "resistance": self.resistance,
            "wallFlex": self.wall_flex,
            "wall_flex": self.wall_flex,
            "forceRise": self.force_rise,
            "deformation": self.deformation,
            "scopeExpansion": self.scope_expansion,
            "difficultyRise": self.difficulty_rise,
            "stakesRise": self.stakes_rise,
            "persistence": self.persistence,
            "quantityGrowth": self.quantity_growth,
            "applicability": self.applicability,
            "strength": self.strength,
            "source": self.source,
            "confidence": self.confidence,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


def escalation_evidence(video_plan_ir: dict[str, Any]) -> CanonicalEscalationEvidence:
    beats = list(video_plan_ir.get("beats") or [])
    attempts = attempt_beats(video_plan_ir)
    escalation_beats = [
        beat
        for beat in beats
        if str(beat.get("beatRole") or "").upper() == "ESCALATION"
        or beat.get("consequenceType") == "escalation"
    ]
    all_text = " ".join(
        str(beat.get(key, "")) for beat in beats for key in ("action", "consequence", "result")
    ).upper()
    goal = video_plan_ir.get("goalEvidence") or {}
    core = video_plan_ir.get("coreMechanic") or {}
    mechanic_signal = bool(
        _words(all_text).intersection(
            {
                "STICK", "STUCK", "RETURNS", "RESISTS", "FLEX", "FLEXES", "MULTIPLY",
                "MULTIPLYING", "MORE", "SWITCH", "WATCHED", "FLIP", "CLAIMS", "CHANGES",
                "NORMAL", "GROW", "SHRINK", "FLOAT", "SPITS", "BOUNCE", "WRONG", "APPEARS",
                "FLIPS", "LID", "CRACKER", "CAT", "CHAIR", "LAMP", "BOX", "BALLOON", "SHOES",
            }
        )
    )
    no_mechanic = (
        not attempts
        and not escalation_beats
        and str(goal.get("goalExplicitness") or "").upper() in {"", "UNKNOWN", "UNSUPPORTED"}
        and str(core.get("physicalRule") or "").strip().lower() in {"", "inferred from beat actions"}
        and not mechanic_signal
    )
    not_applicable = no_mechanic and len(beats) >= 3
    if not_applicable:
        return CanonicalEscalationEvidence(
            status="NOT_APPLICABLE", reason="No single established local mechanic exists for escalation measurement.",
            candidate_beat_ids=(), new_target=False, intensity_rise=False, consequence_expansion=False,
            resistance=False, wall_flex=False, force_rise=False, deformation=False, scope_expansion=False,
            difficulty_rise=False, stakes_rise=False, persistence=False, quantity_growth=False,
            applicability="NOT_APPLICABLE", strength="NOT_APPLICABLE", source="NONE", confidence=None,
        )
    if no_mechanic:
        return CanonicalEscalationEvidence(
            status="UNKNOWN", reason="Escalation evidence is insufficient because no established local mechanic was found.",
            candidate_beat_ids=(), new_target=False, intensity_rise=False, consequence_expansion=False,
            resistance=False, wall_flex=False, force_rise=False, deformation=False, scope_expansion=False,
            difficulty_rise=False, stakes_rise=False, persistence=False, quantity_growth=False,
            applicability="APPLICABLE", strength="UNKNOWN", source="NONE", confidence=None,
        )
    later_beats = [
        beat for beat in beats
        if attempts and float(beat.get("startTime", 0.0) or 0.0) >= float(attempts[0].get("startTime", 0.0) or 0.0)
    ]
    if escalation_beats:
        first_escalation_index = min(beats.index(beat) for beat in escalation_beats)
        candidate_beats = beats[first_escalation_index:]
    else:
        candidate_beats = later_beats or beats[1:]
    if not candidate_beats:
        return CanonicalEscalationEvidence(
            status="UNKNOWN", reason="No comparable attempts or explicit escalation beat exists.",
            candidate_beat_ids=(), new_target=False, intensity_rise=False, consequence_expansion=False,
            resistance=False, wall_flex=False, force_rise=False, deformation=False, scope_expansion=False,
            difficulty_rise=False, stakes_rise=False, persistence=False, quantity_growth=False,
            applicability="APPLICABLE", strength="UNKNOWN", source="NONE", confidence=None,
        )
    baseline_objects = _beat_objects(attempts[0]) if attempts else set()
    candidate_objects = set().union(*(_beat_objects(beat) for beat in candidate_beats)) if candidate_beats else set()
    new_target = bool(baseline_objects and candidate_objects - baseline_objects)
    candidate_text = " ".join(
        str(beat.get(key, "")) for beat in candidate_beats for key in ("action", "consequence", "result")
    ).upper()
    candidate_words = _words(candidate_text)
    resistance = bool(candidate_words.intersection({"STUCK", "STAYS", "REMAINS", "RESISTS", "WILL", "WONT", "WON"}))
    wall_flex = "WALL" in candidate_words and bool(candidate_words.intersection({"FLEX", "FLEXES", "BEND", "BENDS", "STRETCH", "STRETCHES"}))
    force_rise = bool(candidate_words.intersection({"HARDER", "FASTER", "STRONGER", "BURST", "BURSTS"})) or (
        "LEAN" in candidate_words and bool(candidate_words.intersection({"BACKWARD", "TOWARD"}))
    )
    deformation = bool(candidate_words.intersection({"STRETCH", "STRETCHES", "FLEX", "FLEXES", "BEND", "BENDS", "GROW", "GROWS", "SHRINK", "SHRINKS", "INFLATE", "INFLATES", "PUFF", "PUFFS", "EXPAND", "EXPANDS"}))
    scope_expansion = bool(candidate_words.intersection({"WALL", "WHOLE", "ENTIRE", "FOUNTAIN", "SURROUNDED", "SHOULDERS", "SHOULDER"})) or (
        "SECOND" in candidate_words and "LIGHT" in candidate_words
    ) or ("ANOTHER" in candidate_words and "LIGHT" in candidate_words)
    difficulty_rise = bool(candidate_words.intersection({"HARDER", "MISSES", "MISSED", "ALMOST", "CANNOT", "RESISTS", "TIGHTER"}))
    stakes_rise = bool(candidate_words.intersection({"CHEEK", "UPSIDE", "SURROUNDED", "SHOULDERS", "SHOULDER", "HAT", "MOUTH"}))
    persistence = bool(candidate_words.intersection({"AGAIN", "RETURNS", "BACK", "CLAIMS", "REMAINS", "STILL", "REPEAT", "REPEATS", "ITSELF"}))
    quantity_words = candidate_words.intersection({"ONE", "TWO", "THREE", "SIX", "DOZENS"})
    quantity_growth = len(quantity_words) >= 2 or bool(candidate_words.intersection({"MORE", "MULTIPLY", "MULTIPLYING", "FOUNTAIN", "MANY"}))
    consequence_expansion = bool({"WHOLE", "WALL", "LARGER", "BIGGER", "ENTIRE", "ITSELF", "FLEX", "FLEXES", "STRETCH", "STRETCHES"}.intersection(candidate_words)) or wall_flex or quantity_growth
    comparable = [beat for beat in beats if beat in attempts or beat in escalation_beats]
    intensities = [float(beat.get("intensity", 0) or 0) for beat in comparable]
    intensity_rise = len(intensities) >= 2 and max(intensities[1:]) > intensities[0]
    available = bool(escalation_beats) or len(attempts) >= 2 or (not attempts and len(candidate_beats) > 0)
    source = "STRUCTURED_ESCALATION_ROLE" if escalation_beats else "CANONICAL_BEAT_SEQUENCE" if not attempts else "LATER_ATTEMPT_COMPARISON"
    confidence = 0.95 if escalation_beats else 0.8
    result_variation = bool(candidate_words.intersection({"WRONG", "DIFFERENT", "CHANGING"}))
    strong = quantity_growth or (deformation and (scope_expansion or persistence or stakes_rise)) or (force_rise and (difficulty_rise or stakes_rise)) or (scope_expansion and stakes_rise)
    moderate = force_rise or deformation or scope_expansion or difficulty_rise or result_variation or stakes_rise or intensity_rise or (persistence and len(attempts) >= 2)
    strength = "STRONG" if strong else "MODERATE" if moderate else "WEAK" if persistence or new_target or intensity_rise or (len(attempts) >= 2 and len(candidate_beats) > 0) else "UNKNOWN"
    positive = strength in {"STRONG", "MODERATE", "WEAK"}
    reason = "Escalation is evidenced by consequence magnitude, force, deformation, scope, difficulty, stakes or mechanic persistence." if positive else "A candidate escalation window exists, but no measurable escalation axis was evidenced."
    return CanonicalEscalationEvidence(
        status="AVAILABLE" if available else "UNKNOWN", reason=reason,
        candidate_beat_ids=tuple(str(beat.get("id", "")) for beat in candidate_beats),
        new_target=new_target, intensity_rise=intensity_rise, consequence_expansion=consequence_expansion,
        resistance=resistance, wall_flex=wall_flex, force_rise=force_rise, deformation=deformation,
        scope_expansion=scope_expansion, difficulty_rise=difficulty_rise, stakes_rise=stakes_rise,
        persistence=persistence, quantity_growth=quantity_growth, applicability="APPLICABLE",
        strength=strength, source=source, confidence=confidence,
    )


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
    raw_beat_count: int
    load_beat_count: int
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
    attempts = attempt_evidence(video_plan_ir)
    strategy_changes = sum(
        1 for before, after in zip(attempts.strategy_families, attempts.strategy_families[1:]) if before != after
    )
    load_beats = major if major else beats
    transitions = (video_plan_ir.get("storyEvidence") or {}).get("stateTransitionCount")
    if not isinstance(transitions, int):
        transitions = 0
        previous_state: object = object()
        for beat in load_beats:
            state = beat.get("visualStateId") or beat.get("visualState") or beat.get("id")
            if state != previous_state:
                transitions += 1
                previous_state = state
    critical_durations = tuple(
        float(beat.get("duration", 0.0) or 0.0) for beat in load_beats if float(beat.get("duration", 0.0) or 0.0) > 0
    )
    mode = str((video_plan_ir.get("metadata") or {}).get("generationMode") or "SINGLE_15S")
    overloaded = (
        len(load_beats) > 6
        or transitions > 6
        or strategy_changes > 4
    )
    goal = video_plan_ir.get("goalEvidence") or {}
    goal_status = str(goal.get("goalExplicitness") or "UNKNOWN")
    obstruction_status = "AVAILABLE" if goal.get("obstruction") else "UNKNOWN"
    resolution_text = " ".join(
        str(beat.get(key, "")) for beat in beats for key in ("action", "consequence", "result")
    ).lower()
    explicit_realization = any(
        str(beat.get("beatRole", "")).upper() in {"REALIZATION", "DECISION"}
        or any(word in str(beat.get("action", "")).lower() for word in ("realize", "understand", "decide", "notice"))
        for beat in beats
    )
    resolution_words = _words(resolution_text)
    normal_state = bool(resolution_words.intersection({"NORMAL", "NORMALLY", "WORKS", "RESTORED"})) or "BACK TO NORMAL" in resolution_text
    positive_reaction = any(term in resolution_text for term in ("smile", "smiles", "relax", "relaxes", "relieved"))
    fake_resolution = any(
        str(beat.get("beatRole", "")).upper() == "FAKE_RESOLUTION" or beat.get("consequenceType") == "fake_win"
        for beat in beats
    )
    realization_status = "AVAILABLE" if explicit_realization or (normal_state and (positive_reaction or fake_resolution)) else "UNKNOWN"
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
        raw_beat_count=len(beats),
        load_beat_count=len(load_beats),
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
