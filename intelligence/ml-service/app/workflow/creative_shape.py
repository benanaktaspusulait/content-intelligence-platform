"""Object/engine-independent story-shape review. Planned metadata, never semantic vision."""

import json
from collections import Counter
from copy import deepcopy
from itertools import combinations
from pathlib import Path

from . import beat_grammar as bg
from . import premise_naturalness as natural
from .concept_fingerprint import digest

VERSION = "creative-shape-v1"
UNKNOWN = "UNKNOWN"
PAYOFF_FAMILIES = (
    "RESET",
    "OPENING_RECREATED",
    "FALSE_SUCCESS_COLLAPSE",
    "ROLE_REVERSAL",
    "CONTROL_REVERSAL",
    "GOAL_INVERSION",
    "OBJECT_FUNCTION_REVERSAL",
    "PROPERTY_TRANSFER",
    "ENVIRONMENTAL_TAKEOVER",
    "CHARACTER_TRANSFORMATION",
    "OBJECT_TRANSFORMATION",
    "HIDDEN_CAUSE_REVEAL",
    "SELF_CAUSED_PROBLEM",
    "CHAIN_REACTION",
    "LOGICAL_EXTREME",
    "SCALE_EXTREME",
    "POSITION_EXTREME",
    "ABSURD_SUCCESS",
    "PARTIAL_SUCCESS_NEW_PROBLEM",
    "CONTACT_ENTANGLEMENT",
    UNKNOWN,
)
WEIGHTS = dict(
    goalStateSequence=0.16,
    controlStateSequence=0.16,
    strategyRoleSequence=0.12,
    bodyStateSequence=0.08,
    environmentUsageSequence=0.06,
    payoffMechanism=0.14,
    finalCharacterObjectRelation=0.12,
    falseSuccessPosition=0.06,
    loopMechanism=0.04,
    temporalShape=0.06,
)
STRATEGY_ROLES = {
    "DIRECT_USE": "ESTABLISH",
    "FIRST_NORMAL_USE": "TEST_NORMAL_USE",
    "SWITCH_CONTACT_POINT": "ADAPT_CONTACT",
    "CHANGE_ANGLE": "ADAPT_APPROACH",
    "APPROACH_FROM_SIDE": "ADAPT_APPROACH",
    "MOVE_UNDER_OBJECT": "ADAPT_APPROACH",
    "BRACE_BODY": "FORCE",
    "TWO_HAND_FORCE": "FORCE",
    "INCREASE_FORCE": "FORCE",
    "WHOLE_BODY_BRACE": "FORCE",
    "REDUCE_FORCE": "MODULATE_INPUT",
    "ANCHOR_TO_ENVIRONMENT": "CONSTRAIN",
    "BLOCK_PATH": "CONSTRAIN",
    "TRAP_OBJECT": "CONSTRAIN",
    "USE_ENVIRONMENT_SURFACE": "GUIDE_WITH_ENVIRONMENT",
    "USE_BODY_WEIGHT": "FORCE",
    "TEMPORARILY_STOP_TRIGGER": "PAUSE_TRIGGER",
    "MOVE_SELF_NOT_OBJECT": "MOVE_SELF",
    "FREE_ONE_BODY_PART": "RELEASE_CONTACT",
    "WAIT_AND_TIME": "TIME_INTERACTION",
}
CONTROL = {
    "CHARACTER_ATTEMPTS_CONTROL": "OBJECT_RESISTS",
    "ENVIRONMENT_LIMITS_CONTROL": "CONTESTED",
    "CHARACTER_MODULATES_INPUT": "CONTESTED",
    "BODY_ACCEPTS_CONSEQUENCE": "OBJECT_RESISTS",
    "OBJECT_DISPLACES_BODY": "OBJECT_DOMINATES",
    "APPARENT_CONTROL_WITHOUT_TRIGGER": "FALSE_CONTROL",
    "BODY_MOVES_IN_OBJECT_SPACE": "CHARACTER_REGAINS_CONTROL",
    "ENVIRONMENT_BECOMES_OBSTACLE": "OBJECT_DOMINATES",
    "OPENING_PROBLEM_RETURNS": "OBJECT_RESISTS",
    "OBJECT_CONTROLS_CHARACTER": "ROLE_REVERSED",
}


def annotate(candidate, *, canonical_creative_evidence=None):
    if canonical_creative_evidence is not None and canonical_creative_evidence.is_structured:
        canonical = canonical_creative_evidence
        canonical.assert_candidate(candidate)
        source = deepcopy(candidate)
        source["structuredBeatPlan"] = canonical.beat_plan(candidate["structuredBeatPlan"], bg.load_data())
        result = annotate(source)
        result["canonicalCreativeEvidence"] = canonical.receipt()
        result["annotationProvenance"] = "CANONICAL_CREATIVE_EVIDENCE_V1"
        result["classificationLimit"] = "Explicit payoff presence does not classify its mechanism; unstated physical states remain UNKNOWN."
        return result
    """Return a fingerprint without modifying source or trusting advertised progression labels."""
    c = candidate if candidate.get("structuredBeatPlan") else bg.annotate_legacy(candidate)
    plan = c["structuredBeatPlan"]
    goals, controls, roles, bodies, environments = [], [], [], [], []
    false_positions = []
    for i, b in enumerate(plan):
        relation = b.get("relationshipAfter", UNKNOWN)
        false = b.get("bodyStateAfter") == "FALSE_SUCCESS" or relation == "APPARENT_CONTROL_WITHOUT_TRIGGER"
        if false:
            false_positions.append(i + 1)
        goal = (
            "APPARENT_SUCCESS"
            if false
            else {
                "CLOSER": "PARTIAL_PROGRESS",
                "FARTHER": "FARTHER",
                "UNCHANGED": "BLOCKED",
                "AT_GOAL": "NEAR_SUCCESS",
            }.get(b.get("goalProgress"), b.get("goalProgress", UNKNOWN))
        )
        if i == 0 and goal == "FARTHER":
            goal = "BLOCKED"
        if relation == "OPENING_PROBLEM_RETURNS":
            goal = "RESET"
        if b.get("consequenceType") == "ENVIRONMENT_BECOMES_BLOCKED":
            goal = "NEW_PROBLEM"
        goals.append(goal)
        controls.append(CONTROL.get(relation, UNKNOWN))
        roles.append(STRATEGY_ROLES.get(b.get("characterStrategy"), UNKNOWN))
        bodies.append(b.get("bodyStateAfter", UNKNOWN))
        spatial = b.get("spatialChange", {})
        environments.append(
            "OBSTACLE"
            if b.get("consequenceType") == "ENVIRONMENT_BECOMES_BLOCKED"
            else "CONSTRAINT"
            if spatial.get("environmentUse") == "BOUNDARY_CONTACT"
            else "LOCAL"
        )
    last = plan[-1]
    relation = last.get("relationshipAfter", UNKNOWN)
    trapped = last.get("bodyStateAfter") == "TRAPPED"
    recurrence = relation == "OPENING_PROBLEM_RETURNS"
    # Concrete contact state overrides generic 'object controls'/'opening returns' labels.
    if trapped:
        payoff, final, loop = "CONTACT_ENTANGLEMENT", "CHARACTER_ATTACHED_TO_OBJECT", "RETRIGGER_NEW_CONTACT"
    elif recurrence:
        payoff = "FALSE_SUCCESS_COLLAPSE" if false_positions else "OPENING_RECREATED"
        final, loop = "OPENING_STATE_RECREATED", "NORMAL_USE_RETRIGGERS_PROBLEM"
    elif relation == "OBJECT_CONTROLS_CHARACTER":
        payoff, final, loop = "CONTROL_REVERSAL", "OBJECT_CONTROLS_CHARACTER", "NONE"
    elif relation == "ENVIRONMENT_BECOMES_OBSTACLE":
        payoff, final, loop = "ENVIRONMENTAL_TAKEOVER", "ENVIRONMENT_BECOMES_PROBLEM", "NONE"
    else:
        payoff, final, loop = UNKNOWN, UNKNOWN, UNKNOWN
    temporal = []
    for i in range(len(plan)):
        events = []
        if i == 0:
            events.append("PROBLEM")
        if i and roles[i] != roles[i - 1]:
            events.append("TACTIC_CHANGE")
        if i and controls[i] != controls[i - 1]:
            events.append("CONTROL_SHIFT")
        if i + 1 in false_positions:
            events.append("FALSE_SUCCESS")
        if i == len(plan) - 1:
            events.append("PAYOFF")
        # Relative thirds, independent of duration and exact timestamps.
        phase = (
            "EARLY" if i / (len(plan) - 1) < 1 / 3 else "MIDDLE" if i / (len(plan) - 1) < 2 / 3 else "LATE"
        )
        temporal.extend(phase + ":" + e for e in events)
    dimensions = dict(
        openingState=goals[0],
        goalStateSequence=goals,
        controlStateSequence=controls,
        strategyRoleSequence=roles,
        successDistanceSequence=goals[:],
        bodyStateSequence=bodies,
        environmentUsageSequence=environments,
        falseSuccessPosition=false_positions,
        payoffMechanism=payoff,
        finalCharacterObjectRelation=final,
        loopMechanism=loop,
        temporalShape=temporal,
    )
    macro = {
        k: dimensions[k]
        for k in [
            "goalStateSequence",
            "controlStateSequence",
            "strategyRoleSequence",
            "falseSuccessPosition",
            "payoffMechanism",
            "finalCharacterObjectRelation",
            "loopMechanism",
        ]
    }
    return {
        "version": VERSION,
        "dimensions": dimensions,
        "shapeHash": digest(dimensions),
        "macroShapeHash": digest(macro),
        "strategySequenceFingerprint": digest(roles),
        "payoffFamily": payoff,
        "finalRelationship": final,
        "falseSuccessBeat4": 4 in false_positions,
        "temporaryStopTrigger": any(b.get("characterStrategy") == "TEMPORARILY_STOP_TRIGGER" for b in plan),
        "annotationProvenance": "STRUCTURED_PLAN"
        if candidate.get("structuredBeatPlan")
        else "RETROSPECTIVE_LEGACY_TEXT_APPROXIMATION",
        "scope": "NON_CANONICAL_PLANNED_SEQUENCE_NOT_SEMANTIC_EQUIVALENCE",
    }


def _difference(a, b):
    if isinstance(a, list) and isinstance(b, list):
        length = max(len(a), len(b))
        return (
            sum((a[i] if i < len(a) else None) != (b[i] if i < len(b) else None) for i in range(length))
            / length
            if length
            else 0
        )
    return float(a != b)


def distance(a, b):
    x = a.get("storyShapeFingerprint") or annotate(a)
    y = b.get("storyShapeFingerprint") or annotate(b)
    diffs = {k: _difference(x["dimensions"][k], y["dimensions"][k]) for k in WEIGHTS}
    return {
        "distance": round(sum(WEIGHTS[k] * v for k, v in diffs.items()), 6),
        "dimensionDifferences": diffs,
        "scope": "DETERMINISTIC_CREATIVE_SHAPE_DISTANCE_NOT_SEMANTIC_EQUIVALENCE",
    }


def batch_metrics(candidates):
    fps = [c.get("storyShapeFingerprint") or annotate(c) for c in candidates]
    n = len(fps)

    def concentration(values):
        return max(Counter(values).values(), default=0) / n if n else None

    payoffs = Counter(f["payoffFamily"] for f in fps)
    seq = Counter(f["strategySequenceFingerprint"] for f in fps)
    values = [distance(a, b)["distance"] for a, b in combinations(candidates, 2)]
    dominant = sorted(payoffs, key=lambda k: (-payoffs[k], k))[0] if n else None
    return dict(
        candidateDenominator=n,
        meanStoryShapeDistance=round(sum(values) / len(values), 6) if values else None,
        minimumStoryShapeDistance=min(values) if values else None,
        payoffFamilyDistribution=dict(sorted(payoffs.items())),
        payoffConcentrationRate=concentration([f["payoffFamily"] for f in fps]),
        dominantPayoffWarning={
            "code": "PAYOFF_FAMILY_CONCENTRATION",
            "family": dominant,
            "share": payoffs[dominant] / n,
        }
        if n and payoffs[dominant] / n > 0.5
        else None,
        strategySequenceDistribution=dict(sorted(seq.items())),
        strategySequenceConcentration=max(seq.values(), default=0) / n if n else None,
        strategySequenceWarning="STRATEGY_SEQUENCE_CONCENTRATION"
        if n and max(seq.values()) / n > 0.35
        else None,
        falseSuccessBeat4Rate=sum(f["falseSuccessBeat4"] for f in fps) / n if n else None,
        temporaryStopTriggerRate=sum(f["temporaryStopTrigger"] for f in fps) / n if n else None,
        resetPayoffRate=sum(
            f["payoffFamily"] in ("RESET", "OPENING_RECREATED", "FALSE_SUCCESS_COLLAPSE") for f in fps
        )
        / n
        if n
        else None,
        finalRelationshipDistribution=dict(sorted(Counter(f["finalRelationship"] for f in fps).items())),
        historicalCreativeTerritoryCollisionRate=sum(
            territory(c)["historicalCreativeTerritoryRisk"] == "HIGH" for c in candidates
        )
        / n
        if n
        else None,
        scope="NON_CANONICAL_GENERATOR_CONTROLLED_DIAGNOSTICS_NOT_INDEPENDENT_CREATIVE_QUALITY",
    )


def review_batch(candidates):
    """Annotate copies; small batches retain explicit denominators and concentration warnings."""
    result = deepcopy(candidates)
    for c in result:
        c["storyShapeFingerprint"] = annotate(c)
        c["historicalCreativeTerritory"] = territory(c)
    for c in result:
        others = [p for p in result if p["candidateId"] != c["candidateId"]]
        closest = (
            min(others, key=lambda p: (distance(c, p)["distance"], p["candidateId"])) if others else None
        )
        c["closestBatchShape"] = (
            {"candidateId": closest["candidateId"], **distance(c, closest)} if closest else None
        )
        f = c["storyShapeFingerprint"]
        support = {
            "repeatedStrategySequence": sum(
                p["storyShapeFingerprint"]["strategySequenceFingerprint"] == f["strategySequenceFingerprint"]
                for p in others
            ),
            "repeatedFalseSuccessPosition": sum(
                p["storyShapeFingerprint"]["dimensions"]["falseSuccessPosition"]
                == f["dimensions"]["falseSuccessPosition"]
                for p in others
            )
            if f["dimensions"]["falseSuccessPosition"]
            else 0,
            "repeatedPayoffFamily": sum(
                p["storyShapeFingerprint"]["payoffFamily"] == f["payoffFamily"] for p in others
            ),
            "repeatedFinalRelationship": sum(
                p["storyShapeFingerprint"]["finalRelationship"] == f["finalRelationship"] for p in others
            ),
            "repeatedTemporalShape": sum(
                p["storyShapeFingerprint"]["dimensions"]["temporalShape"] == f["dimensions"]["temporalShape"]
                for p in others
            ),
        }
        flags = [k for k, v in support.items() if v > 0]
        risk = (
            "HIGH"
            if len(flags) >= 3 or closest and distance(c, closest)["distance"] < 0.2
            else "MEDIUM"
            if flags
            else "LOW"
        )
        c["templateShapeRisk"] = {
            "code": "TEMPLATE_SHAPE_RISK" if flags else None,
            "risk": risk,
            "evidence": support,
            "peerDenominator": len(others),
        }
    return result


def scene_signature(candidate):
    name = str(candidate.get("primaryObject", "")).casefold()
    model = natural.load_model()
    role = model["objects"].get(name, {}).get("archetype", UNKNOWN)
    category = {"SEATING": "SEATING"}.get(role, role)
    goal = str(candidate.get("everydayGoal", "")).lower()
    goal_role = (
        "SIT"
        if "sit" in goal
        else "CLOSE"
        if "close" in goal
        else "WEAR"
        if "put" in goal
        else "WASH"
        if "wash" in goal
        else "GROOM"
        if "hair" in goal
        else "OPEN"
        if "open" in goal
        else UNKNOWN
    )
    transform = natural.infer_response(candidate)
    shape = candidate.get("storyShapeFingerprint") or annotate(candidate)
    final = shape["finalRelationship"]
    silhouette = (
        "INVERTED_SEAT_BODY"
        if role == "SEATING" and transform == "INVERT_ORIENTATION"
        else "BODY_ATTACHED_OBJECT"
        if final == "CHARACTER_ATTACHED_TO_OBJECT"
        else candidate.get("visualFingerprint", {}).get("characterPoseFamily", UNKNOWN)
    )
    return dict(
        objectCategory=category,
        goal=goal_role,
        openingRelation="USE_BLOCKED" if candidate.get("frameZeroDescription") else UNKNOWN,
        dominantTransformation=transform,
        finalRelation=final,
        silhouetteTopology=silhouette,
    )


def territory(candidate):
    data = json.loads(Path(__file__).with_name("creative_territories_v1.json").read_text())
    signature = scene_signature(candidate)
    weights = dict(
        objectCategory=0.2,
        goal=0.2,
        openingRelation=0.1,
        dominantTransformation=0.25,
        finalRelation=0.1,
        silhouetteTopology=0.15,
    )
    comparisons = []
    for ref in data["references"]:
        matches = [k for k in weights if signature[k] != UNKNOWN and signature[k] == ref["signature"][k]]
        score = round(sum(weights[k] for k in matches), 6)
        comparisons.append(
            dict(
                referenceId=ref["referenceId"],
                similarity=score,
                matchingAxes=matches,
                sourcePath=ref["sourcePath"],
                sourceSha256=ref["sourceSha256"],
            )
        )
    closest = sorted(comparisons, key=lambda p: (-p["similarity"], p["referenceId"]))[0]
    risk = "HIGH" if closest["similarity"] >= 0.75 else "MEDIUM" if closest["similarity"] >= 0.45 else "LOW"
    return dict(
        historicalCreativeTerritoryRisk=risk,
        closestHistoricalCreativeTerritory=closest,
        plannedSceneSignature=signature,
        comparisons=comparisons,
        evidenceKind="NEW_STRUCTURAL_ANNOTATION_OF_TWO_FROZEN_PROMPTS_NOT_PIXELS_OR_WINNER_PERFORMANCE",
        canonicalHistoricalMetricsChanged=False,
    )
