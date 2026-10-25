"""Planned creative distance, never semantic vision or canonical video quality."""

from collections import Counter
from itertools import combinations
import math
from .concept_fingerprint import fingerprint, token

VISUAL_AXES = (
    "characterPoseFamily",
    "objectRelativePosition",
    "dominantDirection",
    "objectScaleRelation",
    "characterObjectContact",
    "finalFrameComposition",
    "movementAxis",
    "environmentInteraction",
)
WEIGHTS = {
    "engineFamily": 0.20,
    "trigger": 0.08,
    "goalFamily": 0.10,
    "objectCategory": 0.10,
    "escalationTopology": 0.14,
    "payoffTopology": 0.14,
    "visualSilhouette": 0.24,
}


def canonical_engine(value):
    value = token(value)
    return {
        "GROWTH": "PROGRESSIVE_GROWTH",
        "UNEXPECTED_GROWTH": "PROGRESSIVE_GROWTH",
        "PROGRESSIVE_SHRINKING": "PROGRESSIVE_SHRINK",
        "SHRINKING": "PROGRESSIVE_SHRINK",
    }.get(value, value)


def canonical_payoff(value):
    value = token(value)
    return "RECURRENCE" if value in ("OPENING_RECREATED", "SELF_CREATED_LOOP") else value


def descriptors(candidate):
    fp = candidate.get("structuralFingerprint") or fingerprint(candidate)
    dims = fp["dimensions"]
    plan = candidate.get("composition", {})
    return {
        **{
            k: (
                canonical_engine(plan.get(k, dims.get(k, candidate.get(k, "UNSPECIFIED"))))
                if k == "engineFamily"
                else canonical_payoff(plan.get(k, candidate.get(k, dims.get(k, "UNSPECIFIED"))))
                if k == "payoffTopology"
                else token(str(plan.get(k, candidate.get(k, dims.get(k, "UNSPECIFIED")))))
            )
            for k in WEIGHTS
            if k != "visualSilhouette"
        },
        "environment": candidate.get("environment", "UNSPECIFIED"),
        "character": candidate.get("protagonistCharacterId", candidate.get("protagonist", "UNSPECIFIED")),
        "visualSilhouette": candidate.get("visualFingerprint", {}),
    }


def silhouette_similarity(a, b):
    """Unknown axes contribute no similarity, never evidence of difference."""
    left, right = a.get("visualFingerprint", {}), b.get("visualFingerprint", {})
    known = [k for k in VISUAL_AXES if left.get(k) and right.get(k)]
    return {
        "similarity": round(sum(left[k] == right[k] for k in known) / len(VISUAL_AXES), 6),
        "supportedAxes": len(known),
        "evidenceKind": "PLANNED_STAGING_METADATA_NOT_PIXELS",
    }


def creative_distance(a, b):
    x, y = descriptors(a), descriptors(b)
    visual = silhouette_similarity(a, b)
    differences = {
        k: (None if "UNSPECIFIED" in (x[k], y[k]) else float(x[k] != y[k]))
        for k in WEIGHTS
        if k != "visualSilhouette"
    }
    support = visual["supportedAxes"]
    differences["visualSilhouette"] = (
        (1 - visual["similarity"] * len(VISUAL_AXES) / support) if support else None
    )
    denominator = sum(WEIGHTS[k] for k, v in differences.items() if v is not None)
    value = (
        sum(WEIGHTS[k] * v for k, v in differences.items() if v is not None) / denominator
        if denominator
        else None
    )
    engine_axes = ("engineFamily", "trigger", "escalationTopology")
    known = [k for k in engine_axes if x[k] != "UNSPECIFIED" and y[k] != "UNSPECIFIED"]
    return {
        "creativeDistance": round(value, 6) if value is not None else None,
        "supportedWeight": round(denominator, 6),
        "engineSimilarity": round(sum(x[k] == y[k] for k in known) / 3, 6),
        "visualSilhouetteSimilarity": visual["similarity"],
        "visualSupportedAxes": visual["supportedAxes"],
        "dimensionDifferences": differences,
        "limitation": "Structured creative distance, not semantic similarity or measured visual quality.",
    }


def pairwise_summary(candidates):
    values = [creative_distance(a, b)["creativeDistance"] for a, b in combinations(candidates, 2)]
    return {
        "meanPairwiseCreativeDistance": round(sum(values) / len(values), 6) if values else None,
        "minimumPairwiseCreativeDistance": min(values) if values else None,
        "pairCount": len(values),
    }


def distributions(candidates):
    axes = {
        "goalFamilyDistribution": "goalFamily",
        "objectCategoryDistribution": "objectCategory",
        "engineDistribution": "engineFamily",
        "escalationDistribution": "escalationTopology",
        "payoffDistribution": "payoffTopology",
        "environmentDistribution": "environment",
        "characterDistribution": "character",
    }
    rows = [descriptors(c) for c in candidates]
    result = {label: dict(sorted(Counter(r[axis] for r in rows).items())) for label, axis in axes.items()}
    warnings = []
    for label, counts in result.items():
        for category, count in counts.items():
            if candidates and count / len(candidates) > 0.35:
                warnings.append(
                    {
                        "code": {
                            "goalFamily": "GOAL_FAMILY",
                            "objectCategory": "OBJECT_CATEGORY",
                            "engineFamily": "ENGINE_FAMILY",
                        }.get(axes[label], axes[label].upper())
                        + "_CONCENTRATION",
                        "dimension": axes[label],
                        "value": category,
                        "count": count,
                        "share": round(count / len(candidates), 6),
                        "reason": f"{category} appears in {100 * count / len(candidates):.1f}% of candidates.",
                    }
                )
    counts = result["engineDistribution"]
    n = len(candidates)
    entropy = -sum(v / n * math.log(v / n) for v in counts.values()) if n else 0
    result.update(
        concentrationWarnings=warnings,
        engineEntropy=round(entropy, 6),
        engineDiversity=round(entropy / math.log(len(counts)), 6) if len(counts) > 1 else 0,
    )
    return result


def novelty(candidate, peers):
    """Separate novelty axes against nearest supported match; unknown remains null."""
    others = [p for p in peers if p["candidateId"] != candidate["candidateId"]]
    if not others:
        return dict.fromkeys(
            [
                "engineNovelty",
                "goalNovelty",
                "objectNovelty",
                "escalationNovelty",
                "payoffNovelty",
                "visualSilhouetteNovelty",
            ]
        )
    d = descriptors(candidate)
    pd = [descriptors(p) for p in others]
    result = {}
    for label, axis in [
        ("goalNovelty", "goalFamily"),
        ("objectNovelty", "objectCategory"),
        ("escalationNovelty", "escalationTopology"),
        ("payoffNovelty", "payoffTopology"),
    ]:
        result[label] = (
            None
            if d[axis] == "UNSPECIFIED" or not any(p[axis] != "UNSPECIFIED" for p in pd)
            else int(not any(d[axis] == p[axis] for p in pd))
        )
    result["engineNovelty"] = round(
        1 - max(creative_distance(candidate, p)["engineSimilarity"] for p in others), 6
    )
    result["visualSilhouetteNovelty"] = round(
        1 - max(silhouette_similarity(candidate, p)["similarity"] for p in others), 6
    )
    return result
