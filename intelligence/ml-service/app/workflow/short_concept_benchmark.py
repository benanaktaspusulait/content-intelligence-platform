"""Local V1/V2 comparison with explicit annotation coverage and denominator evidence."""

from copy import deepcopy
import json
from pathlib import Path
from .short_concept_generation_v2 import generate_and_rank, load_grammar
from .creative_distance import distributions, pairwise_summary


CATEGORY_MAP = {
    "seating": "furniture",
    "eating_tool": "utensil",
    "grooming_tool": "grooming",
    "washing": "hygiene",
    "drinkware": "utensil",
    "clothing": "clothing",
    "cleaning": "fabric",
    "textile": "fabric",
    "play_equipment": "toy",
}
PAYOFF_MAP = {
    "FAKE_SUCCESS_BROKEN": "FAKE_RESOLUTION",
    "GOAL_REVERSAL": "GOAL_INVERSION",
    "TRANSFER_PROBLEM": "ROLE_REVERSAL",
    "REINTERPRETATION": "VISUAL_REVEAL",
    "ATTEMPT_BECOMES_PROBLEM": "SELF_CREATED_LOOP",
    "LOGICAL_EXTREME": "LOGICAL_EXTREME",
}
ESCALATION_MAP = {
    "MAGNITUDE_RATCHET": "LINEAR_MAGNITUDE",
    "CAPABILITY_LOSS": "CONTROL_LOSS",
    "CONSTRAINT_LADDER": "SPACE_COMPRESSION",
    "COUNTER_FORCE": "STRATEGY_RESPONSE",
    "DISTANCE_RESET": "FALSE_PROGRESS",
    "CONTACT_SPREAD": "ACCUMULATION",
    "DEFORMATION_TRANSFER": "CONTROL_LOSS",
    "PROPERTY_HANDOFF": "STATE_CHAIN",
    "UNDOING_PROGRESS": "FALSE_PROGRESS",
    "LEVER_REVERSAL": "STRATEGY_RESPONSE",
    "LIFT_RATCHET": "LINEAR_MAGNITUDE",
    "CYCLIC_PROPAGATION": "STATE_CHAIN",
    "DISTANCE_EXTENSION": "SPACE_COMPRESSION",
    "OBSTACLE_TRANSFER": "STATE_CHAIN",
    "SUPPORT_LOSS": "CONTROL_LOSS",
    "OPPOSITE_EDGE_UNDO": "FALSE_PROGRESS",
    "ASYMPTOTIC_DISTANCE": "SPACE_COMPRESSION",
    "SURFACE_INVERSION": "STATE_CHAIN",
    "MISALIGNED_DELAY": "FALSE_PROGRESS",
    "QUANTITY_RATCHET": "ACCUMULATION",
    "ACTION_ECHO": "ACCUMULATION",
    "DELAYED_ECHO": "STATE_CHAIN",
    "POSITION_LEAP": "STATE_CHAIN",
    "TOPOLOGY_FOLD": "STATE_CHAIN",
    "BALANCE_RATCHET": "CONTROL_LOSS",
}


def annotate_v1(run):
    """New derived benchmark copies; original V1 run and evidence stay unchanged."""
    recipes = {
        r["id"]: r
        for r in json.loads(Path(__file__).with_name("short_concept_catalog.json").read_text())["recipes"]
    }
    grammar = load_grammar()
    objects = {r["name"]: r for r in grammar["objects"]}
    result = []
    for record in run["candidates"]:
        c = deepcopy(record["candidate"])
        r = recipes[c["provenance"]["recipeId"]]
        obj = objects.get(c["primaryObject"])
        goal = c["everydayGoal"].lower()
        family = (
            "BODY_SELF_CARE"
            if any(v in goal for v in ["brush", "wash", "wipe"])
            else "FOOD"
            if any(v in goal for v in ["eat", "drink", "pour"])
            else "DRESSING"
            if any(v in goal for v in ["shoe", "wear", "fold"])
            else "HOUSEHOLD"
        )
        c["composition"] = {
            "goalFamily": family,
            "objectCategory": CATEGORY_MAP.get(r["objectCategory"], r["objectCategory"]),
            "engineFamily": c["structuralFingerprint"]["dimensions"]["engineFamily"],
            "trigger": r["trigger"],
            "escalationTopology": ESCALATION_MAP.get(r["escalationTopology"], r["escalationTopology"]),
            "payoffTopology": PAYOFF_MAP[r["resolutionTopology"]],
        }
        # Only supported shared staging dimensions are annotated. No inferred pixels or unseen final pose.
        c["visualFingerprint"] = (
            {
                "characterPoseFamily": obj["pose"],
                "objectRelativePosition": obj["position"],
                "characterObjectContact": obj["contact"],
                "movementAxis": obj["axis"],
            }
            if obj
            else {}
        )
        c["benchmarkAnnotationProvenance"] = (
            "DERIVED_FROM_V1_CATALOG_AND_SHARED_OBJECT_AFFORDANCES_NOT_FROZEN_EVIDENCE"
        )
        result.append(c)
    return result


def _metrics(run, candidates, slate):
    ds = distributions(candidates)
    n = len(candidates)
    concentration = lambda counts: round(max(counts.values(), default=0) / n, 6) if n else None
    return {
        "outputCount": n,
        "eligibleCount": run["generationSummary"]["eligibleCount"],
        "eligibilityYield": run["generatorMetrics"]["eligibilityYield"],
        "outputStructuralDuplicateRate": round(
            sum(r["disposition"] == "STRUCTURAL_DUPLICATE" for r in run["candidates"]) / n, 6
        )
        if n
        else None,
        "internalPoolDuplicateRate": run["generatorMetrics"]["duplicateRate"]
        if run["generatorVersion"].endswith("v2")
        else None,
        "objectConcentration": concentration(ds["objectCategoryDistribution"]),
        "engineConcentration": concentration(ds["engineDistribution"]),
        "payoffConcentration": concentration(ds["payoffDistribution"]),
        **pairwise_summary(candidates),
        "top3Diversity": pairwise_summary(slate),
        "averageShortFormScore": run["generatorMetrics"]["averageShortFormScore"],
        "productionRiskRate": run["generatorMetrics"]["productionRiskRate"],
        "distributionEvidence": ds,
        "visualAxesCoverage": {c["candidateId"]: len(c.get("visualFingerprint", {})) for c in candidates},
    }


def benchmark(seed=42, count=20):
    old = generate_and_rank({"generatorVersion": "v1", "seed": seed, "count": count})
    new = generate_and_rank({"generatorVersion": "v2", "seed": seed, "count": count})
    a = annotate_v1(old)
    b = [r["candidate"] for r in new["candidates"]]
    by_id = {c["candidateId"]: c for c in a}
    old_slate = [by_id[s["candidateId"]] for s in old["top3ProductionCandidates"]]
    new_slate = [s["candidate"] for s in new["top3ProductionCandidates"]]
    return {
        "seed": seed,
        "requestedCount": count,
        "v1": _metrics(old, a, old_slate),
        "v2": _metrics(new, b, new_slate),
        "limitations": [
            "Same accepted quality assessors and scores; no scorer or generator tuning from benchmark results.",
            "V1 staging annotations cover at most four shared affordance axes; V2 provides eight planned axes. Distances normalize supported weights; comparison is approximate, not a visual study.",
            "V1 one generic environment versus V2 goal-linked environment labels is a schema/content difference, not measured audience novelty.",
            "V2 internal duplicate rate and output duplicate rate have different denominators, separately exposed.",
            "V1 has a broader authored engine bank; V2 need not improve every metric. No external providers or measured performance.",
        ],
    }
