"""Opt-in shape-aware curation of the unchanged deterministic grammar's candidate pool."""

from collections import Counter
from copy import deepcopy
from typing import Literal

from pydantic import Field, model_validator

from . import concept_ranking as ranking
from . import creative_shape as shape
from . import premise_generation as prior
from .concept_fingerprint import digest
from .creative_distance import VISUAL_AXES, distributions, pairwise_summary, silhouette_similarity
from .short_concept_generation import ranking_input, resolve_cast


class GenerationRequest(prior.GenerationRequest):
    creativeShapeVersion: Literal["v1", "creative-shape-v1"] | None = None
    minimumStoryShapeDistance: float = Field(0.22, ge=0.1, le=0.8)
    minimumShapeShortFormScore: float = Field(85, ge=80, le=100)
    minimumShapeRankingScore: float = Field(75, ge=70, le=100)
    allowHighHistoricalTerritoryRisk: bool = False

    @model_validator(mode="after")
    def shape_stack(self):
        if self.creativeShapeVersion and (not self.premiseNaturalnessGateVersion or not self.rank):
            raise ValueError(
                "Creative shape V1 requires explicit Naturalness V1, Beat Grammar "
                "V2, generator V2 and rank=true"
            )
        return self


NEW_FIELDS = {
    "creativeShapeVersion",
    "minimumStoryShapeDistance",
    "minimumShapeShortFormScore",
    "minimumShapeRankingScore",
    "allowHighHistoricalTerritoryRisk",
}


def generate_and_rank(config):
    config = GenerationRequest.model_validate(config)
    if not config.creativeShapeVersion:
        return prior.generate_and_rank(config.model_dump(exclude=NEW_FIELDS, exclude_unset=True))
    # Normalize numeric defaults exactly as explicitly supplied API/CLI values.
    config = GenerationRequest.model_validate(config.model_dump())
    return generate_with_shape(config)


def quality_reasons(c, row, config):
    reasons = []
    if row["eligibility"] != "ELIGIBLE":
        reasons.append("ACCEPTED_VALIDATOR_INELIGIBLE")
    if (row.get("shortFormScore") or 0) < config.minimumShapeShortFormScore:
        reasons.append("SHORT_FORM_QUALITY_FLOOR")
    if (row.get("rankingScore") or 0) < config.minimumShapeRankingScore:
        reasons.append("RANKING_QUALITY_FLOOR")
    if c["beatGrammar"]["beatGrammarQuality"] not in ("STRONG", "ACCEPTABLE"):
        reasons.append("BEAT_GRAMMAR_QUALITY_FLOOR")
    if not c["premiseNaturalness"]["admitted"]:
        reasons.append("PREMISE_NOT_ADMITTED")
    if (
        not config.allowHighHistoricalTerritoryRisk
        and c["historicalCreativeTerritory"]["historicalCreativeTerritoryRisk"] == "HIGH"
    ):
        reasons.append("HIGH_HISTORICAL_CREATIVE_TERRITORY")
    return reasons


def novelty(c, selected):
    return min((shape.distance(c, s)["distance"] for s in selected), default=1.0)


def curate(pool, rows, config):
    remaining = []
    suppressed = []
    selected = []
    decisions = []
    for c in pool:
        reasons = quality_reasons(c, rows[c["candidateId"]], config)
        if reasons:
            suppressed.append(
                dict(candidate=c, suppressionReasons=reasons, validation=rows[c["candidateId"]])
            )
        else:
            remaining.append(c)
    while remaining and len(selected) < min(config.count, 30):
        available = [c for c in remaining if novelty(c, selected) >= config.minimumStoryShapeDistance]
        if not available:
            break

        # Quality is a prerequisite, then novelty across a quality-controlled pool. No rewriting.
        def key(c):
            p = c["premiseNaturalness"]
            r = rows[c["candidateId"]]
            f = c["storyShapeFingerprint"]
            concentration = sum(
                s["storyShapeFingerprint"]["payoffFamily"] == f["payoffFamily"] for s in selected
            )
            return (
                -novelty(c, selected),
                concentration,
                c["historicalCreativeTerritory"]["closestHistoricalCreativeTerritory"]["similarity"],
                -r["shortFormScore"],
                -r["rankingScore"],
                -p["physicalPayoffPotential"],
                digest([config.seed, c["candidateId"]]),
            )

        chosen = min(available, key=key)
        decisions.append(
            dict(
                candidateId=chosen["candidateId"],
                minimumDistanceToPreviouslySelected=novelty(chosen, selected),
                acceptedShortFormScore=rows[chosen["candidateId"]]["shortFormScore"],
                acceptedRankingScore=rows[chosen["candidateId"]]["rankingScore"],
            )
        )
        selected.append(chosen)
        remaining.remove(chosen)
    for c in remaining:
        nearest = (
            min(selected, key=lambda s: (shape.distance(c, s)["distance"], s["candidateId"]))
            if selected
            else None
        )
        suppressed.append(
            dict(
                candidate=c,
                suppressionReasons=[
                    "STORY_SHAPE_DISTANCE_CAPACITY"
                    if novelty(c, selected) < config.minimumStoryShapeDistance
                    else "REQUESTED_COUNT_REACHED"
                ],
                closestSelectedShape=dict(candidateId=nearest["candidateId"], **shape.distance(c, nearest))
                if nearest
                else None,
                validation=rows[c["candidateId"]],
            )
        )
    return selected, suppressed, decisions


def production_selection(ranked, candidates, minimum_distance=0.22, minimum_short=85, minimum_rank=75):
    byid = {c["candidateId"]: c for c in candidates}
    remaining = sorted(
        [
            deepcopy(r)
            for r in ranked
            if r.get("eligibility") == "ELIGIBLE"
            and (r.get("shortFormScore") or 0) >= minimum_short
            and (r.get("rankingScore") or 0) >= minimum_rank
        ],
        key=lambda r: (-r["rankingScore"], r["candidateId"]),
    )
    slate = []
    decisions = []
    while remaining and len(slate) < 3:
        anchor = max(r["rankingScore"] for r in remaining)
        close = [r for r in remaining if anchor - r["rankingScore"] <= 3]
        eligible = [
            r
            for r in close
            if novelty(byid[r["candidateId"]], [s["candidate"] for s in slate]) >= minimum_distance
        ]
        if not eligible:
            # Five-point margin permits a diversity promotion, never an unlimited quality sacrifice.
            eligible = [
                r
                for r in remaining
                if anchor - r["rankingScore"] <= 5
                and novelty(byid[r["candidateId"]], [s["candidate"] for s in slate]) >= minimum_distance
            ]
        if not eligible:
            break

        def signals(r):
            c = byid[r["candidateId"]]
            p = c["premiseNaturalness"]
            f = c["storyShapeFingerprint"]
            b = c["beatGrammar"]
            return dict(
                instantCausalLegibility=p["instantCausalLegibility"],
                payoffStrength=(r.get("shortFormEngine") or {}).get("payoffScore", 0),
                premiseNaturalness={"STRONG": 2, "ACCEPTABLE": 1}.get(p["premiseNaturalness"], 0),
                storyShapeNovelty=novelty(c, [s["candidate"] for s in slate]),
                historicalTerritoryDistance=1
                - c["historicalCreativeTerritory"]["closestHistoricalCreativeTerritory"]["similarity"],
                finalRelationshipNovelty=int(
                    not any(
                        s["candidate"]["storyShapeFingerprint"]["finalRelationship"] == f["finalRelationship"]
                        for s in slate
                    )
                ),
                payoffFamilyNovelty=int(
                    not any(
                        s["candidate"]["storyShapeFingerprint"]["payoffFamily"] == f["payoffFamily"]
                        for s in slate
                    )
                ),
                productionFeasibility=min(
                    b["productionFeasibility"]["score"], r.get("productionEfficiency", {}).get("score", 100)
                ),
                visualSilhouetteNovelty=min(
                    (
                        1 - silhouette_similarity(c, s["candidate"])["similarity"]
                        if silhouette_similarity(c, s["candidate"])["supportedAxes"] == len(VISUAL_AXES)
                        else 0
                        for s in slate
                    ),
                    default=1.0,
                ),
                objectGoalExperienceNovelty=int(
                    not any(
                        all(
                            shape.scene_signature(c)[axis] == shape.scene_signature(s["candidate"])[axis]
                            for axis in ("objectCategory", "goal")
                        )
                        for s in slate
                    )
                ),
            )

        chosen = min(eligible, key=lambda r: tuple(-v for v in signals(r).values()) + (r["candidateId"],))
        values = signals(chosen)
        decisions.append(
            dict(
                candidateId=chosen["candidateId"],
                qualityAnchor=anchor,
                qualityGap=round(anchor - chosen["rankingScore"], 4),
                signals=values,
                alternatives=[
                    dict(candidateId=r["candidateId"], signals=signals(r))
                    for r in eligible
                    if r is not chosen
                ],
            )
        )
        c = byid[chosen["candidateId"]]
        slate.append(
            {
                **chosen,
                "candidate": c,
                "title": c["title"],
                "rawRank": chosen["rank"],
                "productionSlateRank": len(slate) + 1,
                "productionRank": len(slate) + 1,
                "diversityAdjustmentReason": (
                    "SHAPE_AWARE_SELECTION_WITHIN_QUALITY_BANDS_WITHOUT_ENGINE_LABEL_EXCLUSION"
                ),
            }
        )
        remaining.remove(chosen)
    return dict(
        productionSlate=slate,
        firstRenderCandidate=slate[0]["candidateId"] if slate else None,
        tieDecisions=decisions,
        policy=dict(
            qualityBand=3,
            diversityMargin=5,
            minimumStoryShapeDistance=minimum_distance,
            canonicalScoreMutation=False,
            stableIdFinalFallback=True,
        ),
        storyShapeDiversity=shape.batch_metrics([s["candidate"] for s in slate]),
        creativeDistance=pairwise_summary([s["candidate"] for s in slate]),
    )


def frontier(pool, rows, selected, config):
    points = []
    for c in pool:
        r = rows[c["candidateId"]]
        if quality_reasons(c, r, config):
            continue
        refs = [s for s in selected if s["candidateId"] != c["candidateId"]]
        points.append(
            dict(
                candidateId=c["candidateId"],
                quality=r["rankingScore"],
                distanceToSelectedSet=novelty(c, refs),
            )
        )
    nondominated = [
        p
        for p in points
        if not any(
            q["quality"] >= p["quality"]
            and q["distanceToSelectedSet"] >= p["distanceToSelectedSet"]
            and (q["quality"] > p["quality"] or q["distanceToSelectedSet"] > p["distanceToSelectedSet"])
            for q in points
        )
    ]
    return dict(
        referenceSet=[s["candidateId"] for s in selected],
        selfExcluded=True,
        points=points,
        nondominatedCandidateIds=sorted(p["candidateId"] for p in nondominated),
        scope="PARETO_LIKE_ACCEPTED_RANKING_VS_DISTANCE_TO_FINAL_SET_NOT_GLOBAL_OPTIMUM",
    )


def human_report(record):
    c = record["candidate"]
    f = c["storyShapeFingerprint"]
    d = f["dimensions"]
    r = record["validation"]
    lines = [
        "TITLE: " + c["title"],
        "CANDIDATE: " + c["candidateId"],
        "PROTAGONIST: " + c["protagonist"],
        "GOAL: " + c["everydayGoal"],
        "OBJECT: " + c["primaryObject"],
        "ONE-LINE PREMISE: "
        + c["protagonist"]
        + " tries to "
        + c["everydayGoal"]
        + ". "
        + c["impossibleRule"],
        "IMPOSSIBLE RULE: " + c["impossibleRule"],
        "FRAME ZERO: " + c["frameZeroDescription"],
    ]
    lines.extend(
        f"BEAT {i + 1}{' / PAYOFF' if i == 4 else ''}: {b['description']}" for i, b in enumerate(c["beats"])
    )
    lines += [
        "STORY SHAPE: " + " → ".join(d["strategyRoleSequence"]),
        "GOAL-STATE ARC: " + " → ".join(d["goalStateSequence"]),
        "CONTROL-STATE ARC: " + " → ".join(d["controlStateSequence"]),
        "STORY SHAPE FINGERPRINT: " + f["shapeHash"],
        "PAYOFF FAMILY: " + f["payoffFamily"],
        "FINAL RELATIONSHIP: " + f["finalRelationship"],
        "CLOSEST BATCH SHAPE: " + str(c["closestBatchShape"]),
        "CLOSEST HISTORICAL CREATIVE TERRITORY: "
        + str(c["historicalCreativeTerritory"]["closestHistoricalCreativeTerritory"]),
        "HISTORICAL TERRITORY RISK: " + c["historicalCreativeTerritory"]["historicalCreativeTerritoryRisk"],
        "TEMPLATE SHAPE RISK: " + str(c["templateShapeRisk"]),
        "premiseNaturalness: " + c["premiseNaturalness"]["premiseNaturalness"],
        "BeatGrammarQuality: " + c["beatGrammar"]["beatGrammarQuality"],
        f"shortFormScore: {r['shortFormScore']}",
        f"rankingScore: {r['rankingScore']}",
        "eligibility: " + record["disposition"],
        f"rawRank: {record['rawRank']}",
        f"productionSlateRank: {record['productionSlateRank']}",
    ]
    return "\n".join(lines)


def generate_with_shape(config):
    cast, source = resolve_cast(config)
    chosen, evidence, rejected, suppressed = prior.search(config, cast)
    # Recover the full realized pool, including candidates suppressed by the prior batch selector.
    pool = {c["candidateId"]: c for c in chosen}
    pool.update({x["candidate"]["candidateId"]: x["candidate"] for x in suppressed})
    pool = shape.review_batch([pool[k] for k in sorted(pool)])
    rows = {c["candidateId"]: ranking.validate_concept(ranking_input(c)) for c in pool}
    selected, suppressed, decisions = curate(pool, rows, config)
    selected = shape.review_batch(selected)
    raw = ranking.rank_concepts([ranking_input(c) for c in selected]) if selected else None
    finalrows = (
        {r["candidateId"]: r for r in raw["rankedEligibleCandidates"] + raw["revisionCandidates"]}
        if raw
        else {}
    )
    selection = (
        production_selection(
            raw["rankedEligibleCandidates"],
            selected,
            config.minimumStoryShapeDistance,
            config.minimumShapeShortFormScore,
            config.minimumShapeRankingScore,
        )
        if raw
        else dict(productionSlate=[], firstRenderCandidate=None)
    )
    records = []
    for c in selected:
        row = finalrows[c["candidateId"]]
        slate = next((s for s in selection["productionSlate"] if s["candidateId"] == c["candidateId"]), None)
        records.append(
            dict(
                candidateId=c["candidateId"],
                candidate=c,
                validation=row,
                disposition="ELIGIBLE" if row["eligibility"] == "ELIGIBLE" else "REVISION_REQUIRED",
                failureReasons=row["eligibilityReasons"],
                rawRank=row.get("rank"),
                productionSlateRank=slate["productionSlateRank"] if slate else None,
                premiseNaturalness=c["premiseNaturalness"],
                beatGrammar=c["beatGrammar"],
                structuredBeatPlan=c["structuredBeatPlan"],
                storyShapeFingerprint=c["storyShapeFingerprint"],
                creativeShape=c["storyShapeFingerprint"],
                historicalCreativeTerritory=c["historicalCreativeTerritory"],
                closestBatchShape=c["closestBatchShape"],
                templateShapeRisk=c["templateShapeRisk"],
            )
        )
    summary = Counter(r["disposition"] for r in records)
    evidence = {
        **evidence,
        "creativeShapeVersion": shape.VERSION,
        "internalPoolSize": len(pool),
        "finalCandidateCount": len(records),
        "capacityStatus": "REQUEST_SATISFIED"
        if len(records) == config.count
        else "DIVERSITY_CAPACITY_REACHED",
        "qualityScreenedPoolSize": sum(not quality_reasons(c, rows[c["candidateId"]], config) for c in pool),
        "selectionConfiguration": {k: config.model_dump()[k] for k in sorted(NEW_FIELDS)},
        "selectionDecisions": decisions,
        "noProseRewrites": True,
    }
    result = dict(
        workflow="GENERATE_AND_RANK_SHORT_CONCEPTS",
        generatorVersion=prior.legacy.old.VERSION,
        beatGrammarVersion=prior.beats.VERSION,
        premiseNaturalnessGateVersion=prior.gate.VERSION,
        creativeShapeVersion=shape.VERSION,
        seed=config.seed,
        generationConfig={**config.model_dump(exclude={"canonicalCast"}), "canonicalCast": cast},
        castEvidence=dict(source=source, sha256=digest(cast)),
        generationEvidence=evidence,
        generationSummary=dict(
            requestedCount=config.count,
            rawCandidateCount=len(pool),
            finalCandidateCount=len(records),
            eligibleCount=summary["ELIGIBLE"],
            revisionCount=summary["REVISION_REQUIRED"],
            rejectedCount=0,
        ),
        candidates=records,
        generationRejections=rejected,
        suppressedCandidates=suppressed,
        rankingResult=raw,
        rankedCandidates=raw["rankedEligibleCandidates"] if raw else [],
        productionSelection=selection,
        top3ProductionCandidates=selection["productionSlate"],
        firstRenderCandidate=selection["firstRenderCandidate"],
        generatorMetrics=shape.batch_metrics(selected),
        creativeShapeMetrics=shape.batch_metrics(selected),
        beatGrammarMetrics=prior.beats.batch_evidence(selected),
        premiseNaturalnessMetrics=prior.premise_metrics(selected),
        qualityDiversityFrontier=frontier(pool, rows, selected, config),
        poolValidationEvidence=dict(
            candidateCount=len(rows), canonicalValidatorsReused=True, finalRankingScoresUsedForRewrites=False
        ),
        providerCalls=0,
        renderAuthorized=False,
        selfOptimizationEnabled=False,
        **distributions(selected),
    )
    result["diversityScore"] = round(100 * result["engineDiversity"], 2)
    result["dominantEngineWarning"] = None
    result["humanReadableConcepts"] = [human_report(r) for r in records]
    result["humanReadableTop3"] = [
        human_report(next(r for r in records if r["candidateId"] == s["candidateId"]))
        for s in selection["productionSlate"]
    ]
    result["limitations"] = [
        (
            "Generator-controlled diagnostic improvements after filtering are "
            "expected and are not independent evidence of creative quality."
        ),
        (
            "No new story templates or prose rewrites were added; this "
            "experiment exposes the existing deterministic grammar ceiling."
        ),
        (
            "Historical territory uses new planned-scene annotations of two "
            "frozen prompts, not observed pixels or verified winner outcomes."
        ),
        (
            "Batch search is bounded and greedy; output can be below "
            "requested count. Human review is required before claiming "
            "creative success."
        ),
    ]
    result["reportLines"] = [
        "Creative Shape V1: deterministic curation, not creative-quality certification.",
        *result["humanReadableConcepts"],
        *result["limitations"],
    ]
    return result
