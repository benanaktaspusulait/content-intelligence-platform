"""Compatible causal primitives, deterministic search, unchanged accepted validators."""

from collections import Counter
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
from typing import Literal

from pydantic import Field
from . import concept_ranking as ranking
from .short_concept_generation import GenerationRequest as V1Request, resolve_cast, ranking_input
from .concept_fingerprint import digest, fingerprint, compare, token
from .creative_distance import (
    creative_distance,
    silhouette_similarity,
    novelty,
    distributions,
    pairwise_summary,
    descriptors,
)
from .concept_production_selection import select_production

VERSION = "short-concept-generator-v2"


class GenerationRequest(V1Request):
    generatorVersion: Literal["short-concept-generator-v1", "short-concept-generator-v2", "v1", "v2"] = (
        "short-concept-generator-v1"
    )
    internalPoolSize: int = Field(240, ge=20, le=600, strict=True)


def generate_and_rank(config):
    config = GenerationRequest.model_validate(config)
    if config.generatorVersion in ("v1", "short-concept-generator-v1"):
        from .short_concept_generation import generate_and_rank as v1

        return v1(
            {
                **config.model_dump(exclude={"internalPoolSize"}),
                "generatorVersion": "short-concept-generator-v1",
            }
        )
    return generate_v2(config)


def load_grammar():
    return json.loads(Path(__file__).with_name("short_concept_grammar_v2.json").read_text())


def sanity_errors(plan, grammar):
    """Compatibility is checked on typed primitives, never claimed as semantic proof."""
    goals = {r["id"]: r for r in grammar["goals"]}
    objects = {r["id"]: r for r in grammar["objects"]}
    engines = {r["id"]: r for r in grammar["engines"]}
    goal, obj, eng = (
        goals.get(plan.get("goalId")),
        objects.get(plan.get("objectId")),
        engines.get(plan.get("engineFamily")),
    )
    errors = []
    if not all((goal, obj, eng)):
        return ["UNKNOWN_PRIMITIVE"]
    if goal["id"] not in obj["goalIds"]:
        errors.append("GOAL_OBJECT_MISMATCH")
    if goal["interaction"] not in obj["affordances"]:
        errors.append("OBJECT_AFFORDANCE_MISMATCH")
    if goal["interaction"] not in eng["validInteractionTypes"]:
        errors.append("ENGINE_INTERACTION_MISMATCH")
    trigger = plan.get("trigger")
    data = grammar["triggers"].get(trigger, {})
    if trigger != goal["trigger"] or trigger not in eng["validTriggerTypes"]:
        errors.append("TRIGGER_INTERACTION_MISMATCH")
    if not data.get("visible"):
        errors.append("TRIGGER_NOT_VISIBLE")
    if plan.get("escalationTopology") not in eng["allowedEscalations"]:
        errors.append("ENGINE_ESCALATION_MISMATCH")
    payoff = plan.get("payoffTopology")
    if payoff not in eng["compatiblePayoffFamilies"]:
        errors.append("UNEXPLAINED_PAYOFF_RULE")
    if grammar["payoffs"].get(payoff, {}).get("newObjects", True):
        errors.append("UNINTRODUCED_OBJECT_REQUIRED")
    if plan.get("stateTransition") != eng["stateTransition"]:
        errors.append("FINAL_STATE_VIOLATES_ENGINE")
    if plan.get("environment") not in goal["environments"]:
        errors.append("ENVIRONMENT_GOAL_MISMATCH")
    return errors


# One-step state transitions are reusable across objects. No goal or finished beat sequence lives here.
TRANSITIONS = {
    "SCALE_UP": (
        "grows one size step whenever {trigger}",
        [
            "grows past the contact point",
            "grows larger than the available gap",
            "grows even larger than before and blocks the body",
            "grows until the enormous {obj} fills the frame",
        ],
    ),
    "SCALE_DOWN": (
        "shrinks one size step whenever {trigger}",
        [
            "shrinks below the usable contact size",
            "shrinks to half the usable size",
            "shrinks beneath the fingertips",
            "shrinks until the character has to bring the body to the tiny {obj}",
        ],
    ),
    "CONTACT_RETAINS": (
        "sticks to every body part touching it whenever {trigger}",
        [
            "sticks to the first contact point",
            "sticks to the second contact point as well",
            "sticks across both contact points and traps the hands",
            "sticks to the cheek when the character brings the face close",
        ],
    ),
    "RETURN_ORIGIN": (
        "slides back to its starting position whenever {trigger}",
        [
            "slides back into the starting position",
            "slides back from the halfway position",
            "slides back from the goal boundary",
            "slides back into its starting position again",
        ],
    ),
    "INVERT_ORIENTATION": (
        "flips its usable surface away from the character whenever {trigger}",
        [
            "flips upside down at contact",
            "flips upside down while both hands follow the moving surface",
            "flips upside down as the braced body is forced sideways",
            "flips upside down with the character still holding it",
        ],
    ),
    "EXTEND_CONTACT": (
        "stretches one body length from the contact point whenever {trigger}",
        [
            "stretches beyond the first reach",
            "stretches further past both hands",
            "stretches around the braced body",
            "stretches until the enormous {obj} fills the frame",
        ],
    ),
    "MOVE_AWAY": (
        "slides back one object width away from the goal whenever {trigger}",
        [
            "slides back beyond the first reach",
            "slides back beyond the wider reach",
            "slides back across the last usable gap",
            "slides back away from the goal again",
        ],
    ),
    "FLOAT_AWAY": (
        "floats one body height higher whenever {trigger}",
        [
            "floats above the intended contact point",
            "floats above the shoulders",
            "floats overhead and lifts the gripping arms",
            "floats above the body with the character still holding it",
        ],
    ),
}


def compose(plan, grammar, cast, seed, duration):
    errors = sanity_errors(plan, grammar)
    if errors:
        raise ValueError(",".join(errors))
    obj = next(r for r in grammar["objects"] if r["id"] == plan["objectId"])
    goal = next(r for r in grammar["goals"] if r["id"] == plan["goalId"])
    engine = next(r for r in grammar["engines"] if r["id"] == plan["engineFamily"])
    # Identity follows the complete mechanics, never determines them.
    actor = cast[int(digest([seed, plan])[:12], 16) % len(cast)]
    name = actor["name"]
    noun = obj["name"]
    trigger = grammar["triggers"][plan["trigger"]]["rule"]
    rule, effects = TRANSITIONS[plan["stateTransition"]]
    rule = f"The {noun} " + rule.format(trigger=trigger) + "."
    effect = lambda i: f"The {noun} " + effects[i].format(obj=noun) + "."
    strategies = grammar["escalations"][plan["escalationTopology"]]["strategies"]
    action = obj["action"]
    responses = grammar["triggers"][plan["trigger"]]["responseStrategies"]
    beats = [
        f"{name} tries to {goal['visibleAction']} and {action}. {effect(0)} {name}'s eyes widen at the blocked goal.",
        f"{name} {strategies[0]}, {responses[0]}, and {action}. {effect(1)}",
        f"{name} {strategies[1]}, {responses[1]}, and {action}. {effect(2)}",
        f"{name} {strategies[2]} and moves underneath the stationary {noun} without repeating the trigger. This angle exposes the unchanged physical state at the goal boundary; the original task remains unfinished.",
    ]
    payoff = plan["payoffTopology"]
    if payoff == "FAKE_RESOLUTION":
        ending = f"{name} finally holds the {noun} at the goal position without repeating the trigger; the task appears complete. {name} relaxes into the normal use and {action}. {effect(3)} The apparent success becomes the same physical problem again."
    elif payoff == "OPENING_RECREATED":
        ending = f"{name} finally holds the {noun} at the goal position, moves back into the opening body pose, then {action}. {effect(3)} The original reaching pose and blocked goal are recreated at the starting position."
    elif payoff == "SELF_CREATED_LOOP":
        ending = f"{name} finally stops triggering the {noun} at the goal boundary and relaxes. As an absentminded part of the original task, {name} {action}. {effect(3)} {name} immediately starts the opening reach again, creating the next cycle."
    elif payoff == "ROLE_REVERSAL":
        ending = f"{name} tries to use the body to guide the {noun} and {action}. {effect(3)} The body's final pose now follows the {noun} rather than guiding it."
    elif payoff == "GOAL_INVERSION":
        ending = f"{name} makes one last attempt and {action}. {effect(3)} Instead of bringing the {noun} to the goal, {name} must bring the body to the {noun}; the original task remains undone."
    else:
        ending = f"{name} makes one last broad attempt and {action}. {effect(3)} The final scale leaves the original task visibly impossible."
    beats.append(ending)
    ident = "v2-" + digest(plan)[:16]
    structural = {
        "interactionType": goal["interaction"],
        "trigger": plan["trigger"],
        "transformationDirection": plan["stateTransition"],
        "escalationTopology": plan["escalationTopology"],
        "resolutionTopology": payoff,
        "finalSilhouetteTopology": plan["stateTransition"] + "_" + payoff,
        "loopTopology": "TRIGGER_RECREATES_PROBLEM"
        if payoff in ("SELF_CREATED_LOOP", "OPENING_RECREATED")
        else "NONE",
    }
    final_composition = {
        "SCALE_UP": "OBJECT_FILLS_FRAME",
        "SCALE_DOWN": "BODY_APPROACHES_TINY_OBJECT",
        "CONTACT_RETAINS": "FACE_ATTACHMENT",
        "RETURN_ORIGIN": "START_MARK_RETURN",
        "INVERT_ORIENTATION": "INVERTED_CONTACT",
        "EXTEND_CONTACT": "EXTENDED_TETHER",
        "MOVE_AWAY": "GOAL_GAP",
        "FLOAT_AWAY": "OVERHEAD_TETHER",
    }[plan["stateTransition"]]
    visual = dict(
        zip(
            (
                "characterPoseFamily",
                "objectRelativePosition",
                "dominantDirection",
                "objectScaleRelation",
                "characterObjectContact",
                "finalFrameComposition",
                "movementAxis",
                "environmentInteraction",
            ),
            (
                obj["pose"],
                obj["position"],
                plan["stateTransition"],
                "INCREASING"
                if plan["stateTransition"] == "SCALE_UP"
                else "DECREASING"
                if plan["stateTransition"] == "SCALE_DOWN"
                else "STABLE",
                obj["contact"],
                final_composition,
                obj["axis"],
                "SPACE_LOSS" if plan["escalationTopology"] == "SPACE_COMPRESSION" else "LOCAL_WORK_AREA",
            ),
        )
    )
    candidate = {
        "candidateId": ident,
        "title": f"{noun.title()} / {plan['engineFamily'].replace('_', ' ').title()} / {payoff.replace('_', ' ').title()}",
        "protagonist": name,
        "protagonistCharacterId": actor["id"],
        "everydayGoal": goal["visibleAction"],
        "primaryObject": noun,
        "engineFamily": plan["engineFamily"],
        "goalRuleRelationship": f"The {plan['stateTransition'].lower().replace('_', ' ')} response to {goal['interaction']} prevents the {noun} from reaching or holding the usable state needed to {goal['visibleAction']}.",
        "impossibleRule": rule,
        "frameZeroDescription": beats[0],
        "beats": [
            dict(
                startSeconds=round(duration * i / 5, 2),
                endSeconds=duration if i == 4 else round(duration * (i + 1) / 5, 2),
                description=b,
            )
            for i, b in enumerate(beats)
        ],
        "finalPayoff": beats[-1],
        "escalationCurve": [
            dict(
                beatIndex=i + 1,
                sourceRule=rule,
                stateTransition=plan["stateTransition"],
                transitionApplication=i + 1 if i < 3 else 3 if i == 3 else 4,
            )
            for i in range(5)
        ],
        "loopPotential": {"type": structural["loopTopology"], "status": "UNVERIFIED_CREATIVE_HYPOTHESIS"},
        "dialogueRequirement": "NONE",
        "environment": plan["environment"],
        "intendedDurationSeconds": duration,
        "productionNotes": ["One character and one primary object; fixed camera and continuous identity."]
        + engine["productionRiskHints"],
        "composition": deepcopy(plan),
        "structuralPlan": structural,
        "visualFingerprint": visual,
        "provenance": {
            "generatorVersion": VERSION,
            "grammarVersion": grammar["version"],
            "grammarSha256": digest(grammar),
            "seed": seed,
            "characterAssignedAfterEngine": True,
            "evidenceKind": "COMPOSED_PLANNED_SCENE_NOT_OBSERVED_VIDEO",
        },
    }
    candidate["structuralFingerprint"] = fingerprint(candidate)
    return candidate


def search(config, cast, grammar=None):
    grammar = deepcopy(grammar or load_grammar())
    for collection in ("goals", "objects", "engines"):
        grammar[collection].sort(key=lambda row: row["id"])
    plans = []
    rejected = []
    excluded_families = {token(v) for v in config.excludeEngineFamilies}
    for goal in sorted(grammar["goals"], key=lambda r: r["id"]):
        for obj in sorted(grammar["objects"], key=lambda r: r["id"]):
            if (
                goal["id"] not in obj["goalIds"]
                or obj["name"].casefold() in config.excludeObjects
                or obj["category"].casefold() in config.excludeObjectCategories
            ):
                continue
            for eng in sorted(grammar["engines"], key=lambda r: r["id"]):
                if eng["id"] in excluded_families:
                    continue
                for esc, pay, env in product(
                    sorted(eng["allowedEscalations"]),
                    sorted(eng["compatiblePayoffFamilies"]),
                    sorted(goal["environments"]),
                ):
                    plan = dict(
                        goalId=goal["id"],
                        goalFamily=goal["family"],
                        objectId=obj["id"],
                        objectCategory=obj["category"],
                        engineFamily=eng["id"],
                        trigger=goal["trigger"],
                        escalationTopology=esc,
                        payoffTopology=pay,
                        environment=env,
                        stateTransition=eng["stateTransition"],
                    )
                    errors = sanity_errors(plan, grammar)
                    if errors:
                        rejected.append({"composition": plan, "failureReasons": errors})
                    else:
                        plans.append(plan)
    plans.sort(key=lambda p: (digest([config.seed, p]), digest(p)))
    pool = [compose(p, grammar, cast, config.seed, config.duration) for p in plans[: config.internalPoolSize]]
    unique = []
    dedup = []
    silhouettes = []
    for c in pool:
        previous = next(
            (
                p
                for p in unique
                if compare(c["structuralFingerprint"], p["structuralFingerprint"])["nearDuplicate"]
            ),
            None,
        )
        if previous:
            dedup.append(
                {
                    "candidate": c,
                    "duplicateOf": previous["candidateId"],
                    "failureReasons": ["STRUCTURAL_ENGINE_DUPLICATE"],
                }
            )
            continue
        previous = next((p for p in unique if silhouette_similarity(c, p)["similarity"] >= 0.875), None)
        if previous:
            silhouettes.append(
                {
                    "candidate": c,
                    "duplicateOf": previous["candidateId"],
                    "failureReasons": ["PLANNED_SILHOUETTE_NEAR_DUPLICATE"],
                }
            )
            continue
        unique.append(c)
    selected = []
    available = unique[:]
    distance_cache = {}

    def distance(a, b):
        key = tuple(sorted((a["candidateId"], b["candidateId"])))
        if key not in distance_cache:
            distance_cache[key] = creative_distance(a, b)["creativeDistance"]
        return distance_cache[key]

    while available and len(selected) < min(config.count, 30):
        eligible = [c for c in available if all(distance(c, s) >= 0.28 for s in selected)]
        if not eligible:
            break

        def priority(c):
            d = descriptors(c)
            dims = (
                "engineFamily",
                "goalFamily",
                "objectCategory",
                "escalationTopology",
                "payoffTopology",
                "environment",
                "character",
            )
            concentration = sum(
                sum(descriptors(s)[axis] == d[axis] for s in selected) / max(1, len(selected))
                for axis in dims
            )
            return (
                concentration,
                -min((distance(c, s) for s in selected), default=1),
                digest([config.seed, c["candidateId"]]),
            )

        chosen = min(eligible, key=priority)
        selected.append(chosen)
        available.remove(chosen)
    suppressed = [
        {"candidate": c, "failureReasons": ["CREATIVE_DISTANCE_OR_CONCENTRATION_SELECTION"]}
        for c in available
    ]
    return {
        "selected": selected,
        "pool": pool,
        "sanityRejections": rejected,
        "structuralSuppressions": dedup,
        "silhouetteSuppressions": silhouettes,
        "diversitySuppressions": suppressed,
        "evidence": {
            "generatorVersion": VERSION,
            "seed": config.seed,
            "requestedCount": config.count,
            "internalPoolSize": len(pool),
            "configuredPoolSize": config.internalPoolSize,
            "capacityScope": "BOUNDED_SEARCH_POOL_NOT_EXHAUSTIVE_CREATIVE_SPACE",
            "validCompositionCount": len(plans),
            "sanityRejectionCount": len(rejected),
            "dedupeCount": len(dedup),
            "silhouetteSuppressionCount": len(silhouettes),
            "diversitySuppressionCount": len(suppressed),
            "finalCandidateCount": len(selected),
            "capacityStatus": "REQUEST_SATISFIED"
            if len(selected) == config.count
            else "RANKING_CAPACITY_REACHED"
            if len(selected) == 30
            else "DIVERSITY_CAPACITY_REACHED",
        },
    }


def historical_vector(candidate, validation):
    """Reuse accepted evidence; unrepresented axes and unverified winners stay unknown."""
    h = validation.get("historicalComparison", {}) if validation else {}
    risk = validation.get("duplicateRisk") if validation else None
    # Accepted corpus has engine/action/ending signatures, no V2 staging taxonomy or verified outcome labels.
    engine = 1.0 if risk == "HIGH" else 0.5 if h.get("similarities") else 0.0 if validation else None
    vec = {
        "engineNovelty": None if engine is None else 1 - engine,
        "goalNovelty": None,
        "objectNovelty": None,
        "escalationNovelty": None,
        "payoffNovelty": None,
        "visualSilhouetteNovelty": None,
    }
    return {
        "historicalConcepts": {
            "noveltyVector": vec,
            "engineSimilarity": engine,
            "visualSilhouetteSimilarity": None,
            "acceptedComparison": h,
            "classification": "ENGINE_SILHOUETTE_DUPLICATE"
            if risk == "HIGH"
            else "PROVEN_ENGINE_WITH_NEW_EXECUTION"
            if h.get("similarities")
            else "NOVELTY_UNVERIFIED",
        },
        "historicalWinners": {
            "noveltyVector": dict.fromkeys(vec),
            "status": "NO_VERIFIED_WINNER_OUTCOMES_IN_ACCEPTED_CORPUS",
        },
        "limitation": "Two accepted historical production references; no V2 staging annotations or verified winner performance. Unknown axes are null, not originality claims.",
    }


def generate_v2(config):
    cast, cast_source = resolve_cast(config)
    found = search(config, cast)
    candidates = found["selected"]
    ranked = (
        ranking.rank_concepts([ranking_input(c) for c in candidates]) if candidates and config.rank else None
    )
    rows = (
        {r["candidateId"]: r for r in ranked["rankedEligibleCandidates"] + ranked["revisionCandidates"]}
        if ranked
        else {}
    )
    records = []
    for c in candidates:
        row = rows.get(c["candidateId"])
        peers = [p for p in candidates if p is not c]
        ds = [creative_distance(c, p) for p in peers]
        record = {
            "candidateId": c["candidateId"],
            "candidate": c,
            "structuralFingerprint": c["structuralFingerprint"],
            "visualFingerprint": c["visualFingerprint"],
            "validation": row,
            "rawRank": row.get("rank") if row else None,
            "disposition": "NOT_EVALUATED"
            if not row
            else "ELIGIBLE"
            if row["eligibility"] == "ELIGIBLE"
            else "REJECTED"
            if (row.get("shortFormEngine") or {}).get("status") == "REJECT"
            or row.get("duplicateRisk") == "HIGH"
            else "REVISION_REQUIRED",
            "failureReasons": row["eligibilityReasons"] if row else [],
            "noveltyVector": {"currentBatch": novelty(c, candidates), **historical_vector(c, row)},
            "creativeDistanceSummary": {
                "minimum": min((d["creativeDistance"] for d in ds), default=None),
                "mean": round(sum(d["creativeDistance"] for d in ds) / len(ds), 6) if ds else None,
                "engineSimilarity": max((d["engineSimilarity"] for d in ds), default=None),
                "visualSilhouetteSimilarity": max(
                    (d["visualSilhouetteSimilarity"] for d in ds), default=None
                ),
            },
        }
        records.append(record)
    selection = (
        select_production(ranked["rankedEligibleCandidates"], candidates)
        if ranked
        else {
            "productionSlate": [],
            "firstRenderCandidate": None,
            "diversityAdjustments": [],
            "top3PairwiseCreativeDistance": pairwise_summary([]),
        }
    )
    slate = selection["productionSlate"]
    for record in records:
        chosen = next((s for s in slate if s["candidateId"] == record["candidateId"]), None)
        record.update(
            productionSlateRank=chosen["productionSlateRank"] if chosen else None,
            productionResult="SELECTED_FOR_SLATE" if chosen else record["disposition"],
            diversityAdjustmentReason=chosen["diversityAdjustmentReason"] if chosen else None,
        )
    distribution = distributions(candidates)
    counts = Counter(r["disposition"] for r in records)
    scores = [row["shortFormScore"] for row in rows.values() if row.get("shortFormScore") is not None]
    metrics = {
        **distribution,
        **pairwise_summary(candidates),
        "top3PairwiseCreativeDistance": selection["top3PairwiseCreativeDistance"],
        "eligibilityYield": round(counts["ELIGIBLE"] / len(candidates), 6) if candidates and ranked else None,
        "duplicateRate": round(len(found["structuralSuppressions"]) / len(found["pool"]), 6)
        if found["pool"]
        else None,
        "averageShortFormScore": round(sum(scores) / len(scores), 2) if scores else None,
        "productionRiskRate": round(
            sum(bool(row["productionRisk"]["flags"]) for row in rows.values()) / len(rows), 6
        )
        if rows
        else None,
        "historicalEngineSimilarityRate": round(
            sum(bool(row["historicalComparison"]["similarities"]) for row in rows.values()) / len(rows), 6
        )
        if rows
        else None,
        "historicalSilhouetteSimilarityRate": None,
        "historicalSilhouetteCoverage": "NO_COMPARABLE_V2_STAGING_METADATA",
        "evaluatedDenominator": len(rows),
        "scoreUse": "BATCH_DIAGNOSTICS_ONLY_NOT_CANONICAL_VIDEO_SCORES",
    }
    result = {
        "workflow": "GENERATE_AND_RANK_SHORT_CONCEPTS",
        "generatorVersion": VERSION,
        "seed": config.seed,
        "generationConfig": {**config.model_dump(exclude={"canonicalCast"}), "canonicalCast": cast},
        "castEvidence": {"source": cast_source, "sha256": digest(cast)},
        "generationEvidence": found["evidence"],
        "generationSummary": {
            "requestedCount": config.count,
            "rawCandidateCount": len(candidates),
            "structuralDuplicateCount": 0,
            "eligibleCount": counts["ELIGIBLE"],
            "revisionCount": counts["REVISION_REQUIRED"],
            "rejectedCount": counts["REJECTED"],
            "finalCandidateCount": len(candidates),
            "capacityStatus": found["evidence"]["capacityStatus"],
        },
        **distribution,
        "diversityScore": round(100 * distribution["engineDiversity"], 2),
        "dominantEngineWarning": None,
        "candidates": records,
        "generationRejections": found["sanityRejections"],
        "suppressedCandidates": found["structuralSuppressions"]
        + found["silhouetteSuppressions"]
        + found["diversitySuppressions"],
        "rankingResult": ranked,
        "rankedCandidates": ranked["rankedEligibleCandidates"] if ranked else [],
        "productionSelection": selection,
        "top3ProductionCandidates": slate,
        "firstRenderCandidate": selection["firstRenderCandidate"],
        "WHY_THIS_ONE_FIRST": {
            "candidateId": selection["firstRenderCandidate"],
            "policy": selection.get("policy"),
            "signals": slate[0]["productionTieSignals"] if slate else None,
            "rawRank": slate[0]["rawRank"] if slate else None,
            "tieDecision": next(
                (
                    d
                    for d in selection.get("creativeTieDecisions", [])
                    if d["candidateId"] == selection["firstRenderCandidate"]
                ),
                None,
            ),
            "reason": slate[0]["selectionReason"]
            if slate
            else "No eligible sufficiently distinct slate candidate.",
        },
        "generatorMetrics": metrics,
        "providerCalls": 0,
        "renderAuthorized": False,
        "selfOptimizationEnabled": False,
        "limitations": [
            "Planned scenes and scores are hypotheses, not measured retention or observed video.",
            "Finite compatible grammar and bounded search; no unlimited uniqueness claim.",
            "Accepted English pattern screens, historical coverage and raw ranking are unchanged.",
            "Production selection is additive; raw ranking and canonical scores are preserved.",
        ],
    }
    result["humanReadableTop3"] = [
        idea_summary(s, next(r for r in records if r["candidateId"] == s["candidateId"])) for s in slate
    ]
    result["reportLines"] = [
        "What should we make today? V2 composed pre-render hypotheses.",
        json.dumps(result["generationEvidence"], sort_keys=True),
        *result["humanReadableTop3"],
        *result["limitations"],
    ]
    return result


def idea_summary(slate, record):
    c = slate["candidate"]
    row = record["validation"]
    h = row["historicalComparison"]
    lines = [
        c["title"],
        "FRAME ZERO: " + c["frameZeroDescription"],
        "GOAL: " + c["everydayGoal"],
        "IMPOSSIBLE RULE: " + c["impossibleRule"],
    ]
    lines.extend(
        f"BEAT {i + 1}{' / PAYOFF' if i == 4 else ''}: {b['description']}" for i, b in enumerate(c["beats"])
    )
    lines += [
        "WHY IT MAY WORK: "
        + f"Existing hook {row['shortFormEngine']['hookScore']}, progress {row['shortFormEngine']['progressDensityScore']}, payoff {row['shortFormEngine']['payoffScore']}. Explicit visible trigger; five planned causal states. These are text-screen hypotheses.",
        "MAIN RISK: "
        + (
            "; ".join(c["productionNotes"][1:] + row["productionRisk"]["flags"])
            or "Rendered causal legibility remains unverified."
        ),
        "CLOSEST HISTORICAL ENGINE: "
        + str(h["closestHistoricalEngine"] or "No supported match in limited corpus"),
        f"RAW RANK: {slate['rawRank']} / PRODUCTION SLATE RANK: {slate['productionSlateRank']}",
    ]
    return "\n".join(lines)
