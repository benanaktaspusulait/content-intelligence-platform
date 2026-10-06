"""Human-readable pre-render assessment projection.

This module is deliberately a read model: it consumes the canonical parser IR and
existing rule results. It does not invent a second rule engine or rewrite prompts.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..quality.canonical_evidence import (
    attempt_beats,
    attempt_evidence,
    beat_audit,
    engine_profile_evidence,
    evidence_gap_kind,
    is_evidence_gap,
    is_unspecified_verb,
    story_density_evidence,
    unscored_families,
)


def build_pre_render_assessment(ir: dict[str, Any], parser: Any, report: Any, ruleset_version: str) -> dict[str, Any]:
    evaluations = tuple(report.evaluations)
    applicable = tuple(e for e in evaluations if e.outcome.value not in {"NOT_APPLICABLE"})
    evaluated = tuple(e for e in applicable if not is_evidence_gap(e))
    coverage = round(len(evaluated) * 100 / max(len(applicable), 1))

    story = story_density_evidence(ir)
    engine_profile = engine_profile_evidence(ir)
    dimensions = [
        _concept(ir),
        _opening(ir, evaluations),
        _goal(ir, evaluations),
        _mechanic(ir),
        _attempts(ir, evaluations),
        _progression(ir, evaluations),
        _escalation(ir, evaluations),
        _payoff(ir, evaluations),
        _loop(ir, evaluations),
        _character_intent(ir, evaluations),
        _sound_off(ir),
        _producibility(ir, evaluations),
        _timing(ir),
        _family_fit(ir),
    ]
    strengths = [f"{item['title']}: {item['summary']}" for item in dimensions if item["status"] in {"STRONG", "MODERATE"}][:4]
    concerns = [f"{item['title']}: {item['observed']}" for item in dimensions if item["status"] in {"NEEDS_ATTENTION", "UNKNOWN"}][:5]
    recommendations = [item["recommendation"] for item in dimensions if item["status"] == "NEEDS_ATTENTION"][:5]

    grade = _grade(report, coverage, parser)
    creative_grade = _creative_grade(evaluations)
    evidence_completeness = _evidence_completeness(report, ir, evaluations, coverage, dimensions)
    first_frame = _first_frame_assessment(ir)
    render_authorization = _render_authorization(
        report, creative_grade, evidence_completeness, first_frame
    )
    prompt_stage = _prompt_stage(creative_grade, first_frame, render_authorization)
    readiness = {
        "A": "READY_TO_RENDER", "B": "READY_TO_RENDER", "C": "EDIT_PLAN",
        "D": "EDIT_PLAN", "F": "BLOCKED", "INCOMPLETE": "INCOMPLETE",
    }[grade]
    if grade == "B":
        verdict = "The plan satisfies the current major gates; minor creative improvements are recommended before spending render credits."
    elif grade == "A":
        verdict = "The plan satisfies the current pre-render creative policy with strong evidence coverage."
    elif grade == "INCOMPLETE":
        verdict = "A final creative readiness decision is not reliable because applicable evidence is missing or a provider failed."
    elif grade == "F":
        verdict = "A critical concept or render-safety gate failed; do not spend render credits on this version."
    else:
        verdict = "The plan is understandable but meaningful creative changes are recommended before rendering."

    return {
        "name": "PRE_RENDER_CREATIVE_READINESS",
        "engine_profile": {
            "profile": engine_profile.profile,
            "source": engine_profile.source,
            "confidence": engine_profile.confidence,
            "active": engine_profile.active,
            "candidate_only": engine_profile.candidate_only,
            "signals": engine_profile.signals,
            "recurrence_count": engine_profile.recurrence_count,
            "intervention_count": engine_profile.intervention_count,
            "state_memory_cost": engine_profile.state_memory_cost,
            "reason": engine_profile.reason,
        },
        "story_structure": {
            "goal": story.goal_status,
            "obstacle": story.obstruction_status,
            "attempts": attempt_evidence(ir).active_attempt_count,
            "distinct_strategies": attempt_evidence(ir).distinct_strategy_count,
            "realization": story.realization_status,
            "payoff": story.payoff_status,
            "fake_resolution": "OPTIONAL",
            "recurrence": "OPTIONAL",
        },
        "temporal_complexity": {
            "status": "BLOCK_SINGLE_GENERATION" if story.temporal_load == "HIGH" and story.generation_mode == "SINGLE_15S" else "PASS_WITH_SPLIT" if story.temporal_load == "HIGH" else "MANAGEABLE",
            "major_beats": story.major_beat_count,
            "micro_beats": story.micro_beat_count,
            "state_transitions": story.state_transition_count,
            "strategy_changes": story.strategy_change_count,
            "generation_mode": story.generation_mode,
            "recommendation": story.split_recommendation,
        },
        "grade": grade,
        "creative_grade": creative_grade,
        "creative_score": round(float(report.overall_score), 2),
        "readiness": readiness,
        "prompt_stage": prompt_stage,
        "assessment_coverage_percent": coverage,
        "evidence_completeness": evidence_completeness,
        "first_frame": first_frame,
        "render_authorization": render_authorization,
        "verdict": verdict,
        "strengths": strengths or ["No dimension has enough evidence to be called a strength."],
        "concerns": concerns or ["No unresolved dimension concern was recorded."],
        "recommended_changes": recommendations or ["No mandatory change was generated by the current rule evidence."],
        "dimensions": dimensions,
        "stable_intent": _stable_intent(ir),
        "provenance": {
            "rulesetVersion": ruleset_version,
            "parserVersion": "prompt-parser-v2",
            "canonicalEvidenceVersion": "canonical-attempt-evidence-v2",
            "assessmentVersion": "pre-render-assessment-v2",
            "scoringVersion": "quality-scorer-v2",
            "semanticProvider": "deterministic-pre-render-evidence",
            "evaluationStage": "PRE_RENDER",
        },
    }


def _dimension(key: str, title: str, status: str, summary: str, observed: str, recommendation: str, evidence: str = "AVAILABLE") -> dict[str, str]:
    return {"key": key, "title": title, "status": status, "summary": summary, "observed": observed, "recommendation": recommendation, "evidence_status": evidence}


def _rule(evaluations: Iterable[Any], *ids: str) -> Any | None:
    wanted = set(ids)
    return next((item for item in evaluations if item.rule_id in wanted), None)


def _rule_status(evaluations: Iterable[Any], *ids: str) -> str | None:
    item = _rule(evaluations, *ids)
    return None if item is None else item.outcome.value


def _concept(ir: dict[str, Any]) -> dict[str, str]:
    characters = ir.get("characters") or {}
    primary = characters.get("primary")
    mechanic = ir.get("coreMechanic") or {}
    props = (ir.get("setting") or {}).get("mainProps") or []
    beats = ir.get("beats") or []
    if primary and primary != "Unknown" and mechanic.get("physicalRule") not in {None, "Inferred from beat actions"} and props and beats:
        return _dimension("CONCEPT_CLARITY", "Concept clarity", "STRONG", "One primary character, a concrete object and a central rule are present.", f"{primary} · {props[0]} · {mechanic.get('physicalRule')}", "Preserve the character-object-rule relationship while revising weaker beats.")
    return _dimension("CONCEPT_CLARITY", "Concept clarity", "NEEDS_ATTENTION", "The core concept cannot yet be summarized confidently from the plan.", "Character, object, mechanic or beats are missing or inferred.", "State one primary character, one interactive object and one impossible rule explicitly.", "PARTIAL")


def _opening(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    hook = ir.get("hook") or {}
    rule = _rule(evaluations, "INSTANT_CAUSAL_LEGIBILITY", "INSTANT_VISUAL_ABSURDITY_GATE", "HOOK_001", "HOOK_002")
    status = None if rule is None else rule.outcome.value
    if rule is not None and is_evidence_gap(rule):
        return _dimension(
            "OPENING_HOOK",
            "Opening / hook",
            "UNKNOWN",
            "Textual opening evidence exists, but visual hook verification is pending.",
            rule.message,
            "Supply first-frame visual evidence; do not rewrite the prompt solely for this gap.",
            "PARTIAL",
        )
    if status == "FAIL":
        return _dimension(
            "OPENING_HOOK",
            "Opening / hook",
            "NEEDS_ATTENTION",
            "The opening rule evidence reports a delayed or unclear anomaly.",
            hook.get("description", "The central problem is not established early enough."),
            "Start at the first visible consequence of the impossible rule.",
        )
    if hook.get("startTime", 0) <= 0.8 or hook.get("visualStrength") is True:
        return _dimension(
            "OPENING_HOOK",
            "Opening / hook",
            "STRONG",
            "The plan declares an immediate opening beat.",
            "The hook begins at the opening window; face, text and direct gaze are not mandatory.",
            "Keep the anomaly readable without adding an unnecessary establishing shot.",
        )
    return _dimension(
        "OPENING_HOOK",
        "Opening / hook",
        "UNKNOWN",
        "The opening cannot be confirmed from explicit plan evidence.",
        "Hook timing or visual consequence is not explicit.",
        "Specify what the viewer sees in the first 0–0.8 seconds.",
        "PARTIAL",
    )


def _goal(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    status = _rule_status(evaluations, "GOAL_001", "OPENING_GOAL_OBSTRUCTION")
    if status == "FAIL":
        return _dimension("CHARACTER_GOAL", "Character goal", "NEEDS_ATTENTION", "The character reacts, but the rule evidence does not establish a visible objective.", "Goal/obstruction evidence failed.", "Write a simple visible goal and a specific obstruction.")
    if status == "PASS":
        return _dimension("CHARACTER_GOAL", "Character goal", "STRONG", "The plan gives the character a visible objective and obstruction.", "Existing goal rule passed.", "Preserve the goal while varying the attempts.")
    return _dimension("CHARACTER_GOAL", "Character goal", "UNKNOWN", "The character goal is not explicit enough for a reliable diagnosis.", "No explicit goal field is available in the current IR.", "Add a one-sentence visible goal before the timeline.", "PARTIAL")


def _mechanic(ir: dict[str, Any]) -> dict[str, str]:
    mechanic = ir.get("coreMechanic") or {}
    rule = mechanic.get("physicalRule")
    if rule and rule != "Inferred from beat actions":
        return _dimension("CENTRAL_MECHANIC", "Central mechanic", "STRONG", "A single physical rule is named and can anchor the sequence.", str(rule), "Keep later consequences inside the same mechanic.")
    return _dimension("CENTRAL_MECHANIC", "Central mechanic", "NEEDS_ATTENTION", "The central rule is inferred rather than explicitly planned.", "No explicit physical rule was parsed.", "Name the one impossible behavior that drives every beat.", "PARTIAL")


def _attempts(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    # Attempt facts come from the canonical accessor; "distinct" comes from the rule
    # that judged it (ATTEMPT_002) so this dimension can never disagree with the rule list.
    evidence = attempt_evidence(ir)
    verbs = [family for family in evidence.strategy_families if family != "UNSPECIFIED"]
    rule = _rule(evaluations, "ATTEMPT_002", "ATTEMPT_STRATEGY_DIVERSITY", "ATTEMPT_003")
    judged = (
        rule is not None
        and rule.outcome.value in {"PASS", "FAIL"}
        and isinstance(rule.actual_value, (int, float))
    )
    distinct = int(rule.actual_value) if judged and rule is not None else len(set(verbs))
    summary = f"{evidence.count} attempt(s), {distinct} distinct action strategies"
    observed = f"{summary}: {', '.join(verbs) or 'unspecified'}."
    key, title = "ATTEMPT_DIVERSITY", "Attempt diversity"
    if (rule is not None and rule.outcome.value == "FAIL") or (evidence.count >= 2 and distinct <= 1):
        return _dimension(
            key,
            title,
            "NEEDS_ATTENTION",
            "The planned attempts rely on one underlying strategy.",
            observed,
            "Replace later stronger/repeated versions with materially different actions.",
        )
    if evidence.count >= 2 and distinct >= 2:
        if rule is not None and not judged:
            return _dimension(
                key,
                title,
                "MODERATE",
                "The attempts use different action verbs; their semantic distinctness was not verified.",
                observed,
                "Re-run validation once the semantic check is available.",
                "PARTIAL",
            )
        return _dimension(
            key,
            title,
            "STRONG",
            "The attempts use materially different action strategies.",
            observed,
            "Preserve the strategy change and keep each consequence visible.",
        )
    return _dimension(
        key,
        title,
        "UNKNOWN",
        "Fewer than two explicit attempts were parsed.",
        "Attempt sequence is missing or under-specified.",
        "Mark each attempt with its action, target and expected consequence.",
        "PARTIAL",
    )


def _progression(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    beats = ir.get("beats", [])
    states = [beat.get("visualStateId") for beat in beats if beat.get("visualStateId")]
    consequences = [beat.get("consequenceType") for beat in beats if beat.get("consequenceType")]
    status = _rule_status(evaluations, "ACTIVITY_IS_NOT_PROGRESSION", "MEANINGFUL_PROGRESSION", "CONTINUOUS_ACTION_MOMENTUM")
    if status == "FAIL" or len(set(states)) <= 1 and len(beats) >= 3:
        return _dimension("PROGRESSION", "Progression", "NEEDS_ATTENTION", "The timeline contains activity without enough state change.", f"{len(beats)} beat(s) collapse into {len(set(states)) or 1} visual state(s).", "Make every important beat change the object, character, problem or consequence.")
    if len(set(states)) >= 2 or len(set(consequences)) >= 2:
        return _dimension("PROGRESSION", "Progression", "MODERATE", "The plan includes observable state or consequence changes.", f"{len(set(states))} visual state(s), {len(set(consequences))} consequence type(s).", "Make the final state visibly stronger than the opening state.")
    return _dimension("PROGRESSION", "Progression", "UNKNOWN", "Progression cannot be confirmed from the parsed state evidence.", "State transitions are not explicit.", "Add before-state, action and after-state for each meaningful beat.", "PARTIAL")


def _escalation(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    evidence = attempt_evidence(ir)
    key, title = "ESCALATION", "Escalation"
    if evidence.count < 2:
        summary = (
            "Escalation cannot be evaluated without explicit attempts."
            if evidence.count == 0
            else "Escalation needs at least two attempts to compare."
        )
        observed = "No attempt sequence was parsed." if evidence.count == 0 else "Only one attempt was parsed."
        return _dimension(
            key,
            title,
            "UNKNOWN",
            summary,
            observed,
            "Define at least two attempts and their changing consequences.",
            "PARTIAL",
        )
    attempts = attempt_beats(ir)
    intensities = [float(beat.get("intensity", 0)) for beat in attempts]
    observed = (
        f"Attempt intensity moves from {intensities[0]:.0f} to {intensities[-1]:.0f} "
        f"across {evidence.count} attempts."
    )
    # Prefer the rule's judgment (ESCALATION_005) over re-comparing intensities here.
    status = _rule_status(evaluations, "ESCALATION_005")
    rises = intensities[-1] > intensities[0] if status is None else status == "PASS"
    if rises:
        return _dimension(
            key,
            title,
            "MODERATE",
            "Later attempts are planned with greater commitment or consequence.",
            observed,
            "Make the increase change the problem, not only the movement size.",
        )
    return _dimension(
        key,
        title,
        "NEEDS_ATTENTION",
        "The attempt sequence does not show a clear structural increase.",
        observed,
        "Increase difficulty, surprise or consequence while keeping the same mechanic.",
    )


def _payoff(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    payoff = ir.get("finalPayoff") or {}
    status = _rule_status(evaluations, "PAYOFF_001", "PAYOFF_002", "PAYOFF_003", "FINAL_PAYOFF")
    if status == "FAIL" or not payoff:
        return _dimension("PAYOFF", "Payoff", "NEEDS_ATTENTION", "The final beat is missing or does not clearly resolve the central mechanic.", "No reliable payoff event was parsed.", "Define the final consequence, final state change and how it is visually emphasized.")
    emphasis = payoff.get("visualEmphasis") or payoff.get("emphasisStrategy")
    summary = "The final consequence is explicit and tied to the plan." if emphasis else "The final consequence exists, but its visual emphasis is not explicit."
    return _dimension("PAYOFF", "Payoff", "STRONG" if emphasis else "MODERATE", summary, str(payoff.get("description") or payoff.get("event") or "Payoff parsed"), "Preserve the same mechanic and specify a short hold, reaction, object action or motion spike." if not emphasis else "Keep the payoff visually distinct without adding a random mechanic.")


def _loop(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    payoff = ir.get("finalPayoff") or {}
    if payoff.get("loopsToOpening") and payoff.get("loopQuality") in {"strong", "moderate"}:
        return _dimension("LOOP_INTENT", "Loop intent", "STRONG", "The ending intentionally returns toward the opening relationship.", "The parsed payoff declares a loop to the opening.", "Preserve the visual relationship; render-time evidence must verify it later.")
    if payoff.get("loopsToOpening") is False or payoff.get("loopQuality") == "none":
        return _dimension("LOOP_INTENT", "Loop intent", "MODERATE", "The plan declares an ordinary ending rather than a loop.", "No loop is claimed; this is valid but has no loop intent.", "Add a loop only if it naturally follows the same mechanic.")
    return _dimension("LOOP_INTENT", "Loop intent", "UNKNOWN", "Loop intent is not explicit in the parsed plan.", "The ending does not state its relationship to the opening.", "State whether the final state naturally restarts the opening action.", "PARTIAL")


def _character_intent(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    characters = ir.get("characters") or {}
    primary = characters.get("primary")
    secondary = characters.get("secondary") or []
    if primary and primary != "Unknown":
        return _dimension("CHARACTER_PERFORMANCE_INTENT", "Character performance intent", "STRONG" if not secondary else "MODERATE", "The primary character is identified as the causal performer of the mechanic.", f"Primary: {primary}; secondary: {', '.join(secondary) or 'none'}.", "Keep the primary character carrying the mechanic; secondary characters should not obscure the causal action.")
    return _dimension("CHARACTER_PERFORMANCE_INTENT", "Character performance intent", "UNKNOWN", "The causal character is not explicit.", "Primary character could not be parsed confidently.", "Name one primary character and define what they attempt to do.", "PARTIAL")


def _sound_off(ir: dict[str, Any]) -> dict[str, str]:
    value = (ir.get("hook") or {}).get("soundOffClear")
    if value is True:
        return _dimension("SOUND_OFF_READABILITY", "Sound-off readability", "STRONG", "The prompt explicitly plans visual readability without dialogue or sound.", "Hook sound-off evidence is explicit.", "Preserve the visible cause and consequence even when muted.")
    if value is False:
        return _dimension("SOUND_OFF_READABILITY", "Sound-off readability", "NEEDS_ATTENTION", "The hook depends on audio or dialogue for comprehension.", "Sound-off clarity is explicitly weak.", "Make the central action and consequence visible without requiring dialogue.")
    return _dimension("SOUND_OFF_READABILITY", "Sound-off readability", "UNKNOWN", "Sound-off readability is not explicit in the plan.", "No clear sound-off claim was parsed.", "Describe what a viewer understands with audio muted.", "PARTIAL")


def _producibility(ir: dict[str, Any], evaluations: Iterable[Any]) -> dict[str, str]:
    value = ir.get("producibility") or {}
    status = _rule_status(evaluations, "PRODUCIBILITY_001", "GENERATION_EXECUTABLE_ATTEMPTS")
    if status == "FAIL":
        return _dimension("PRODUCIBILITY", "Producibility", "NEEDS_ATTENTION", "The current plan contains a generation-risk concern.", "Existing producibility evidence failed.", "Reduce simultaneous moving parts and keep the mechanic focused on one object.")
    if value and value.get("score") is not None:
        return _dimension("PRODUCIBILITY", "Producibility", "MODERATE", "The parser produced a producibility assessment with explicit evidence.", str(value), "Resolve any unknown character, prop or transition before rendering.")
    return _dimension("PRODUCIBILITY", "Producibility", "UNKNOWN", "Producibility evidence is incomplete.", "No reliable generation-risk assessment was parsed.", "Specify character count, object continuity and the exact physical action for each beat.", "PARTIAL")


def _timing(ir: dict[str, Any]) -> dict[str, str]:
    beats = ir.get("beats") or []
    duration = float((ir.get("metadata") or {}).get("duration") or 0)
    if beats and duration > 0:
        covered = max(float(beat.get("endTime", 0)) for beat in beats)
        return _dimension("TIMING_PACING", "Timing / pacing plan", "STRONG" if covered >= duration * 0.9 else "MODERATE", "The prompt contains timestamped beats that cover the intended runtime.", f"{len(beats)} beat(s) through {covered:.1f}s of {duration:.1f}s.", "Keep idle time intentional and reserve the final beat for the payoff.")
    return _dimension("TIMING_PACING", "Timing / pacing plan", "UNKNOWN", "The pacing plan is not sufficiently timestamped.", "Beat timing is missing or incomplete.", "Add explicit start/end windows for hook, attempts and payoff.", "PARTIAL")


def _family_fit(ir: dict[str, Any]) -> dict[str, str]:
    family = (ir.get("metadata") or {}).get("seriesType") or "unknown"
    return _dimension("CONTENT_FAMILY_FIT", "Content-family fit", "MODERATE" if family != "unknown" else "UNKNOWN", "The plan is scoped to a recognized content family." if family != "unknown" else "Content-family scope is not explicit.", str(family), "Keep family-specific restrictions scoped; do not apply Pompom-only rules globally.")


def _stable_intent(ir: dict[str, Any]) -> list[str]:
    characters = ir.get("characters") or {}
    mechanic = ir.get("coreMechanic") or {}
    return [value for value in [f"primary_character:{characters.get('primary')}" if characters.get("primary") else None, f"central_mechanic:{mechanic.get('physicalRule')}" if mechanic.get("physicalRule") else None, f"content_family:{(ir.get('metadata') or {}).get('seriesType')}" if (ir.get('metadata') or {}).get('seriesType') else None] if value]


def _textual_first_frame_intent(ir: dict[str, Any]) -> dict[str, Any]:
    hook = ir.get("hook") or {}
    beats = ir.get("beats") or []
    first = beats[0] if beats else {}
    text = " ".join(
        str(first.get(key, "")) for key in ("action", "consequence", "visualState")
    )
    text += " " + str((ir.get("coreMechanic") or {}).get("physicalRule", ""))
    lower = text.lower()
    timing = hook.get("startsAt") is not None and float(hook.get("startsAt") or 0) <= 0.8
    anomaly_terms = ("stick", "stuck", "sticky", "impossible", "instead of", "wrong", "already", "won't", "will not", "cannot")
    has_anomaly = any(term in lower for term in anomaly_terms)
    has_actor = bool((ir.get("characters") or {}).get("primary")) and bool(first.get("action"))
    if not beats or hook.get("startsAt") is None:
        return {"status": "UNKNOWN", "reason": "Opening beat or timestamp evidence is missing.", "evidence": {}}
    if timing and has_anomaly and has_actor:
        return {
            "status": "PASS",
            "reason": "The prompt describes an actor, object and immediate abnormal relationship in the opening window.",
            "evidence": {"startsAt": hook.get("startsAt"), "hasActor": has_actor, "hasAnomaly": has_anomaly},
        }
    return {
        "status": "FAIL",
        "reason": "The opening text does not explicitly establish an immediate, history-free visual anomaly with the character engaged.",
        "evidence": {"startsAt": hook.get("startsAt"), "hasActor": has_actor, "hasAnomaly": has_anomaly},
    }


def _visual_verification_status(ir: dict[str, Any], key: str) -> dict[str, Any]:
    evidence = (ir.get("visualEvidence") or {}).get(key) or (ir.get("creativeFingerprint") or {}).get(key)
    if isinstance(evidence, dict) and evidence.get("status"):
        return dict(evidence)
    return {"status": "PENDING", "reason": "No verified image evidence has been supplied yet."}


def _first_frame_assessment(ir: dict[str, Any]) -> dict[str, Any]:
    fingerprint = ir.get("creativeFingerprint") or {}
    silhouette = fingerprint.get("silhouetteVerification") or (ir.get("visualEvidence") or {}).get("silhouette")
    if not silhouette:
        silhouette_result = {"status": "PENDING", "reason": "First-frame/silhouette comparison has not been run."}
    elif isinstance(silhouette, dict):
        silhouette_result = dict(silhouette)
    else:
        silhouette_result = {"status": "AVAILABLE", "value": silhouette}
    return {
        "textual_intent": _textual_first_frame_intent(ir),
        "visual_verification": _visual_verification_status(ir, "firstFrame"),
        "silhouette_verification": silhouette_result,
    }


def _prompt_stage(
    creative_grade: str, first_frame: dict[str, Any], render_authorization: dict[str, Any]
) -> str:
    if render_authorization.get("status") in {"BLOCKED_CREATIVE_FAILURE", "BLOCKED_TECHNICAL_FAILURE"}:
        return render_authorization["status"]
    if first_frame["textual_intent"]["status"] != "PASS":
        return "BLOCKED_CREATIVE_FAILURE"
    return "READY_FOR_FIRST_FRAME"


def _render_authorization(
    report: Any, creative_grade: str, completeness: dict[str, Any], first_frame: dict[str, Any]
) -> dict[str, Any]:
    evidence_gate_ids = {"INSTANT_VISUAL_ABSURDITY_GATE", "ENGINE_SILHOUETTE_DUPLICATE"}
    pending = [
        gap["rule_id"] for gap in completeness["gaps"] if gap["rule_id"] in evidence_gate_ids
    ]
    creative_failures = [
        evaluation.rule_id
        for evaluation in report.evaluations
        if evaluation.outcome.value == "FAIL" and not is_evidence_gap(evaluation)
    ]
    technical = [
        evaluation.rule_id
        for evaluation in report.evaluations
        if evaluation.outcome.value == "SERVICE_ERROR"
    ]
    pending_items = list(pending)
    if first_frame["visual_verification"]["status"] == "PENDING" and "first-frame visual verification" not in pending_items:
        pending_items.append("first-frame visual verification")
    if first_frame["silhouette_verification"]["status"] == "PENDING" and "silhouette duplicate comparison" not in pending_items:
        pending_items.append("silhouette duplicate comparison")
    if not bool(getattr(report, "independent_revalidated", False)):
        pending_items.append("independent validation revalidation")
    final_policy_ready = (
        str(getattr(report.status, "value", report.status)) == "RENDER_READY"
        and report.blocker_count == 0
        and report.critical_count == 0
    )
    if technical:
        status = "BLOCKED_TECHNICAL_FAILURE"
    elif creative_failures:
        status = "BLOCKED_CREATIVE_FAILURE"
    elif not final_policy_ready or pending_items:
        status = "BLOCKED_PENDING_EVIDENCE"
    else:
        status = "AUTHORIZED"
    return {
        "status": status,
        "final_video_render": status,
        "creative_failures": creative_failures,
        "pending_evidence_blockers": pending_items,
        "technical_failures": technical,
        "human_review": status == "HUMAN_REVIEW",
        "reason": {
            "BLOCKED_PENDING_EVIDENCE": "Final video authorization remains fail-closed until required visual evidence is supplied.",
            "BLOCKED_CREATIVE_FAILURE": "One or more evaluated creative policies failed.",
            "BLOCKED_TECHNICAL_FAILURE": "A required provider or technical evaluation failed.",
            "AUTHORIZED": "All applicable creative and authorization evidence is available.",
        }.get(status, "Human review is required."),
    }


_UNSCORED_FAMILY_REASON = (
    "No rule in this family produced an evaluable result; its canonical score is null, not a creative zero."
)

def _creative_grade(evaluations: Iterable[Any]) -> str:
    """Grade from creative judgments only.

    Outcomes that merely reflect missing evidence (UNKNOWN, SERVICE_ERROR and gates that
    fail closed on absent evidence) are reported under evidence completeness instead, so
    "we could not tell" never reads as "the plan is weak".
    """
    creative = [item for item in evaluations if not is_evidence_gap(item) and item.outcome.value != "NOT_APPLICABLE"]
    if not creative:
        return "INCOMPLETE"
    failed = [item for item in creative if item.outcome.value == "FAIL"]
    if any(item.configured_severity.value == "BLOCKER" for item in failed):
        return "F"
    if any(item.configured_severity.value == "CRITICAL" for item in failed):
        return "D"
    if failed:
        return "C"
    if any(item.configured_severity.value == "WARNING" for item in creative):
        return "B"
    return "A"


def _evidence_completeness(
    report: Any, ir: dict[str, Any], evaluations: tuple[Any, ...], coverage: int, dimensions: list[dict[str, str]]
) -> dict[str, Any]:
    """How much of the plan could actually be judged, independent of how good it is."""
    gaps = [
        {"rule_id": item.rule_id, "family": item.family, "kind": evidence_gap_kind(item), "message": item.message}
        for item in evaluations
        if is_evidence_gap(item)
    ]
    if report.service_error_count or coverage < 80:
        status = "INCOMPLETE"
    elif gaps:
        status = "PARTIAL"
    else:
        status = "COMPLETE"
    attempts = attempt_evidence(ir)
    beats = ir.get("beats") or []
    return {
        "status": status,
        "coverage_percent": coverage,
        "gaps": gaps,
        "unscored_families": [
            {"family": family, "reason": _UNSCORED_FAMILY_REASON} for family in unscored_families(evaluations)
        ],
        "partial_dimensions": [item["key"] for item in dimensions if item["evidence_status"] != "AVAILABLE"],
        "canonical_evidence": {
            "beat_count": len(beats),
            "labelled_beats": sum(1 for beat in beats if beat.get("beatRole")),
            "beatAudit": beat_audit(ir),
            "attempts": {
                "count": attempts.count,
                "activeAttemptCount": attempts.active_attempt_count,
                "distinctStrategyCount": attempts.distinct_strategy_count,
                "beat_ids": list(attempts.beat_ids),
                "verbs": list(attempts.verbs),
                "strategy_families": list(attempts.strategy_families),
                "attempts": list(attempts.attempts),
                "active_seconds": round(attempts.active_seconds, 3),
                "active_ratio": round(attempts.active_ratio, 4),
                "sources": attempts.sources,
            },
        },
    }


def _grade(report: Any, coverage: int, parser: Any) -> str:
    if report.service_error_count or coverage < 80:
        return "INCOMPLETE"
    if report.blocker_count:
        return "F"
    if report.critical_count:
        return "D"
    if report.failed_rules:
        return "C"
    if report.warning_count or getattr(parser, "warnings", ()):
        return "B"
    return "A"
