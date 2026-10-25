"""Opt-in naturalness prefilter and production selection. Legacy generators are unchanged."""

from collections import Counter
from itertools import product
from typing import Literal

from pydantic import Field, model_validator

from . import beat_generation as legacy
from . import beat_grammar as beats
from . import concept_ranking as ranking
from . import premise_naturalness as gate
from .concept_fingerprint import digest, token
from .concept_production_selection import tie_signals
from .creative_distance import creative_distance, descriptors, distributions, pairwise_summary
from .short_concept_generation import ranking_input, resolve_cast


class GenerationRequest(legacy.GenerationRequest):
    premiseNaturalnessGateVersion: Literal["v1", "premise-naturalness-v1"] | None = None
    premisePoolSize: int = Field(480, ge=20, le=1200, strict=True)

    @model_validator(mode="after")
    def explicit_stack(self):
        if self.premiseNaturalnessGateVersion and (
            self.generatorVersion not in ("v2", legacy.old.VERSION) or not self.beatGrammarVersion
        ):
            raise ValueError("Premise gate requires generator V2 and Beat Grammar V2 explicitly")
        return self


def generate_and_rank(config):
    config = GenerationRequest.model_validate(config)
    if not config.premiseNaturalnessGateVersion:
        return legacy.generate_and_rank(
            config.model_dump(exclude={"premiseNaturalnessGateVersion", "premisePoolSize"})
        )
    return generate_with_gate(config)


def search(config, cast):
    grammar = legacy.old.load_grammar()
    data = beats.load_data()
    model = gate.load_model()
    for key in ("goals", "objects", "engines"):
        grammar[key].sort(key=lambda v: v["id"])
    options = []
    rejections = []
    gate_cache = {}
    for goal in grammar["goals"]:
        for obj in grammar["objects"]:
            if (
                goal["id"] not in obj["goalIds"]
                or obj["name"].casefold() in config.excludeObjects
                or obj["category"].casefold() in config.excludeObjectCategories
            ):
                continue
            for engine in grammar["engines"]:
                if engine["id"] in {token(v) for v in config.excludeEngineFamilies}:
                    continue
                for escalation, payoff, environment in product(
                    sorted(engine["allowedEscalations"]),
                    sorted(engine["compatiblePayoffFamilies"]),
                    sorted(goal["environments"]),
                ):
                    composition = dict(
                        goalId=goal["id"],
                        goalFamily=goal["family"],
                        objectId=obj["id"],
                        objectCategory=obj["category"],
                        engineFamily=engine["id"],
                        trigger=goal["trigger"],
                        escalationTopology=escalation,
                        payoffTopology=payoff,
                        environment=environment,
                        stateTransition=engine["stateTransition"],
                    )
                    errors = legacy.old.sanity_errors(composition, grammar)
                    if errors:
                        rejections.append(
                            {
                                "composition": composition,
                                "stage": "AFFORDANCE_COMPATIBILITY",
                                "failureReasons": errors,
                            }
                        )
                        continue
                    cache_key = (
                        obj["name"],
                        goal["visibleAction"],
                        engine["stateTransition"],
                        goal["trigger"],
                    )
                    if cache_key not in gate_cache:
                        rule = (
                            "The "
                            + obj["name"]
                            + " "
                            + legacy.old.TRANSITIONS[engine["stateTransition"]][0].format(
                                trigger=grammar["triggers"][goal["trigger"]]["rule"]
                            )
                            + "."
                        )
                        gate_cache[cache_key] = gate.assess(
                            {
                                "primaryObject": obj["name"],
                                "everydayGoal": goal["visibleAction"],
                                "impossibleRule": rule,
                                "composition": composition,
                            },
                            model,
                        )
                    premise = gate_cache[cache_key]
                    if not premise["admitted"]:
                        rejections.append(
                            {
                                "composition": composition,
                                "stage": "PREMISE_NATURALNESS",
                                "premiseNaturalness": premise,
                                "failureReasons": [f["code"] for f in premise["flags"]]
                                or ["INSUFFICIENT_DIRECT_FUNCTIONAL_CONTRADICTION"],
                            }
                        )
                        continue
                    for shape, profile in sorted(data["shapes"].items()):
                        errors = sorted(
                            {e for s in profile["strategies"] for e in beats.compatible(s, composition, data)}
                        )
                        if engine["stateTransition"] not in profile.get(
                            "validTransitions", [engine["stateTransition"]]
                        ):
                            errors.append("PROGRESSION_SHAPE_ENGINE_MISMATCH")
                        if errors:
                            rejections.append(
                                {
                                    "composition": composition,
                                    "shape": shape,
                                    "stage": "BEAT_COMPATIBILITY",
                                    "failureReasons": errors,
                                }
                            )
                        else:
                            options.append((composition, shape))
    options.sort(key=lambda value: digest([config.seed, value]))
    pool = []
    for composition, shape in options[: config.premisePoolSize]:
        candidate = legacy.make_candidate(composition, shape, cast, config, grammar, data)
        candidate["premiseNaturalness"] = gate.assess(candidate, model)
        candidate["provenance"].update(
            premiseNaturalnessGateVersion=gate.VERSION,
            expectationModelSha256=digest(model),
            premiseScreenedBeforeBeatPlan=True,
        )
        pool.append(candidate)
    unique = []
    seen = set()
    suppressed = []
    for candidate in pool:
        if not candidate["premiseNaturalness"]["admitted"]:
            rejections.append(
                {
                    "candidate": candidate,
                    "stage": "FRAME_AND_PREMISE_RECHECK",
                    "failureReasons": candidate["premiseNaturalness"]["flags"],
                }
            )
            continue
        core = digest(
            [
                candidate["engineFamily"],
                candidate["composition"]["trigger"],
                candidate["progressionShape"],
                candidate["beatGrammar"]["strategyFamilySequence"],
                candidate["beatGrammar"]["consequenceSequence"],
                candidate["beatGrammar"]["payoffStateChange"],
            ]
        )
        if core in seen:
            suppressed.append({"candidate": candidate, "reason": "ENGINE_AND_ATTEMPT_SEQUENCE_DUPLICATE"})
            continue
        seen.add(core)
        unique.append(candidate)
    selected = []
    remaining = unique[:]
    while remaining and len(selected) < min(config.count, 30):
        available = [
            c for c in remaining if all(creative_distance(c, p)["creativeDistance"] >= 0.28 for p in selected)
        ]
        if not available:
            break

        def key(c):
            p = c["premiseNaturalness"]
            d = descriptors(c)
            concentration = sum(
                sum(descriptors(s)[axis] == d[axis] for s in selected)
                for axis in ("engineFamily", "goalFamily", "objectCategory", "environment", "character")
            ) + 2 * sum(s["progressionShape"] == c["progressionShape"] for s in selected)
            # Explicit preference within bounded naturalness tiers, never a ranking-score feedback loop.
            return (
                0 if p["premiseNaturalness"] == "STRONG" else 1,
                concentration,
                -p["objectSpecificityScore"],
                -p["physicalPayoffPotential"],
                digest([config.seed, c["candidateId"]]),
            )

        chosen = min(available, key=key)
        selected.append(chosen)
        remaining.remove(chosen)
    suppressed.extend(
        {"candidate": c, "reason": "BATCH_DISTANCE_OR_CONCENTRATION_SELECTION"} for c in remaining
    )
    return (
        selected,
        {
            "generatorVersion": legacy.old.VERSION,
            "beatGrammarVersion": beats.VERSION,
            "premiseNaturalnessGateVersion": gate.VERSION,
            "seed": config.seed,
            "requestedCount": config.count,
            "configuredPoolSize": config.premisePoolSize,
            "internalPoolSize": len(pool),
            "validCompositionCount": len(options),
            "screenedUniquePremiseCount": len(gate_cache),
            "rejectedPremiseCount": sum(not p["admitted"] for p in gate_cache.values()),
            "finalCandidateCount": len(selected),
            "capacityStatus": "REQUEST_SATISFIED"
            if len(selected) == config.count
            else "RANKING_CAPACITY_REACHED"
            if len(selected) == 30
            else "DIVERSITY_CAPACITY_REACHED",
            "scope": "BOUNDED_LOCAL_SEARCH_CURATED_EXPECTATION_COVERAGE",
        },
        rejections,
        suppressed,
    )


def production_signals(row, candidate, peers):
    p = candidate["premiseNaturalness"]
    b = candidate["beatGrammar"]
    prior = tie_signals(row, candidate, peers)
    return {
        "directGoalInterference": int(p["goalInterferenceType"] == "DIRECT"),
        "instantCausalLegibility": p["instantCausalLegibility"],
        "objectSpecificity": p["objectSpecificityScore"],
        "functionalIrony": {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}[p["functionalIrony"]],
        "physicalPayoffPotential": p["physicalPayoffPotential"],
        "beatGrammarQuality": {"STRONG": 3, "ACCEPTABLE": 2, "MECHANICAL": 1, "BROKEN": 0}[
            b["beatGrammarQuality"]
        ],
        "productionFeasibility": min(
            b["productionFeasibility"]["score"], row.get("productionEfficiency", {}).get("score", 100)
        ),
        "existingCreativeSignals": prior,
    }


def select_production(ranked, candidates):
    by_id = {c["candidateId"]: c for c in candidates}
    pending = sorted(ranked, key=lambda r: (-r["rankingScore"], r["candidateId"]))
    ordered = []
    bands = []
    decisions = []
    axes = (
        "directGoalInterference",
        "instantCausalLegibility",
        "objectSpecificity",
        "functionalIrony",
        "physicalPayoffPotential",
        "beatGrammarQuality",
        "productionFeasibility",
    )

    def key(row):
        signals = production_signals(row, by_id[row["candidateId"]], candidates)
        return tuple(-signals[a] for a in axes) + (row["candidateId"],)

    while pending:
        anchor = pending[0]["rankingScore"]
        band = [r for r in pending if anchor - r["rankingScore"] <= 3]
        band.sort(key=key)
        for a, b in zip(band, band[1:], strict=False):
            x = production_signals(a, by_id[a["candidateId"]], candidates)
            y = production_signals(b, by_id[b["candidateId"]], candidates)
            first = next((axis for axis in axes if x[axis] != y[axis]), "candidateId")
            decisions.append(
                {
                    "candidateId": a["candidateId"],
                    "comparedWith": b["candidateId"],
                    "firstDifferentiatingSignal": first,
                    "values": [x[first], y[first]]
                    if first != "candidateId"
                    else [a["candidateId"], b["candidateId"]],
                }
            )
        ordered.extend(band)
        bands.append({"anchor": anchor, "candidateIds": [r["candidateId"] for r in band]})
        ids = {r["candidateId"] for r in band}
        pending = [r for r in pending if r["candidateId"] not in ids]
    slate = []
    remaining = ordered[:]
    adjustments = []
    while remaining and len(slate) < 3:
        baseline = remaining[0]
        available = [
            r
            for r in remaining
            if baseline["rankingScore"] - r["rankingScore"] <= 5
            and all(legacy.behaviorally_distinct(by_id[r["candidateId"]], s["candidate"]) for s in slate)
        ]
        if not available:
            break
        chosen = available[0]
        candidate = by_id[chosen["candidateId"]]
        slate.append(
            {
                **chosen,
                "candidate": candidate,
                "rawRank": chosen["rank"],
                "productionRank": len(slate) + 1,
                "productionSlateRank": len(slate) + 1,
                "premiseNaturalness": candidate["premiseNaturalness"],
                "productionTieSignals": production_signals(chosen, candidate, candidates),
                "diversityAdjustmentReason": (
                    "FUNCTIONAL_PREMISE_PREFERENCE_WITHIN_UNCHANGED_3_POINT_BAND_AND_5_POINT_DIVERSITY_MARGIN"
                ),
            }
        )
        if chosen is not baseline:
            adjustments.append(
                {
                    "code": "DIVERSITY_PROMOTION",
                    "candidateId": chosen["candidateId"],
                    "aheadOf": baseline["candidateId"],
                }
            )
        remaining.remove(chosen)
    return {
        "productionSlate": slate,
        "firstRenderCandidate": slate[0]["candidateId"] if slate else None,
        "productionOrder": [r["candidateId"] for r in ordered],
        "tieBands": bands,
        "tieDecisions": decisions,
        "diversityAdjustments": adjustments,
        "policy": {
            "canonicalScoreMutation": False,
            "priority": list(axes) + ["candidateId"],
            "qualityBand": 3,
            "diversityMargin": 5,
        },
        "top3PairwiseCreativeDistance": pairwise_summary([s["candidate"] for s in slate]),
    }


def premise_metrics(candidates):
    values = [c["premiseNaturalness"] for c in candidates]
    n = len(values)

    def rate(predicate):
        return round(sum(predicate(v) for v in values) / n, 6) if n else None

    return {
        "arbitraryMagicRate": rate(
            lambda p: any(f["code"] == "ARBITRARY_MAGIC_RELATIONSHIP" for f in p["flags"])
        ),
        "genericEngineApplicationRate": rate(
            lambda p: p["objectSwapTest"]["classification"] == "GENERIC_ENGINE_APPLICATION"
        ),
        "highObjectSpecificityRate": rate(lambda p: p["objectSpecificity"] == "HIGH"),
        "highFunctionalIronyRate": rate(lambda p: p["functionalIrony"] == "HIGH"),
        "meanPhysicalPayoffPotential": round(sum(v["physicalPayoffPotential"] for v in values) / n, 4)
        if n
        else None,
        "premiseReviewDistribution": dict(Counter(v["premiseReviewStatus"] for v in values)),
        "candidateDenominator": n,
        "scoreUse": "NON_CANONICAL_PRE_RENDER_HEURISTICS",
    }


def human_report(record):
    c = record["candidate"]
    p = c["premiseNaturalness"]
    row = record["validation"]
    lines = [
        c["title"],
        "PROTAGONIST: " + c["protagonist"],
        "GOAL: " + c["everydayGoal"],
        "OBJECT: " + c["primaryObject"],
        "EXPECTED OBJECT BEHAVIOR: " + "; ".join(p["primaryExpectedBehaviors"]),
        "IMPOSSIBLE RULE: " + c["impossibleRule"],
        "CONTRADICTION TYPE: " + str(p["contradictionType"]),
        "WHY THIS OBJECT?: " + p["whyThisObject"],
        "FRAME ZERO: " + c["frameZeroDescription"],
    ]
    lines.extend(
        f"BEAT {i + 1}{' / PAYOFF' if i == 4 else ''}: {b['description']}" for i, b in enumerate(c["beats"])
    )
    lines.extend(
        f"{key}: {p[key]}"
        for key in (
            "premiseNaturalness",
            "goalInterferenceType",
            "triggerNaturalness",
            "objectSpecificity",
            "objectSpecificityScore",
            "functionalIrony",
            "physicalPayoffPotential",
            "staticFrameLegibility",
        )
    )
    lines += [
        "BeatGrammarQuality: " + c["beatGrammar"]["beatGrammarQuality"],
        f"shortFormScore: {row['shortFormScore'] if row else None}",
        f"rankingScore: {row['rankingScore'] if row else None}",
        "eligibility: " + record["disposition"],
        f"productionSlateRank: {record['productionSlateRank']}",
    ]
    return "\n".join(lines)


def generate_with_gate(config):
    cast, source = resolve_cast(config)
    candidates, evidence, rejected, suppressed = search(config, cast)
    raw = (
        ranking.rank_concepts([ranking_input(c) for c in candidates]) if config.rank and candidates else None
    )
    rows = (
        {r["candidateId"]: r for r in raw["rankedEligibleCandidates"] + raw["revisionCandidates"]}
        if raw
        else {}
    )
    selection = (
        select_production(raw["rankedEligibleCandidates"], candidates)
        if raw
        else {"productionSlate": [], "firstRenderCandidate": None}
    )
    records = []
    for c in candidates:
        row = rows.get(c["candidateId"])
        selected = next(
            (s for s in selection["productionSlate"] if s["candidateId"] == c["candidateId"]), None
        )
        disposition = (
            "NOT_EVALUATED"
            if not row
            else "ELIGIBLE"
            if row["eligibility"] == "ELIGIBLE"
            else "REJECTED"
            if (row["shortFormEngine"] or {}).get("status") == "REJECT" or row["duplicateRisk"] == "HIGH"
            else "REVISION_REQUIRED"
        )
        records.append(
            {
                "candidateId": c["candidateId"],
                "candidate": c,
                "premiseNaturalness": c["premiseNaturalness"],
                "beatGrammar": c["beatGrammar"],
                "structuredBeatPlan": c["structuredBeatPlan"],
                "validation": row,
                "disposition": disposition,
                "failureReasons": row["eligibilityReasons"] if row else [],
                "rawRank": row.get("rank") if row else None,
                "productionSlateRank": selected["productionSlateRank"] if selected else None,
            }
        )
    counts = Counter(r["disposition"] for r in records)
    ds = distributions(candidates)
    metrics = beats.batch_evidence(candidates)
    scores = [r["shortFormScore"] for r in rows.values() if r["shortFormScore"] is not None]
    metrics.update(
        eligibilityYield=counts["ELIGIBLE"] / len(candidates) if raw and candidates else None,
        averageShortFormScore=sum(scores) / len(scores) if scores else None,
        acceptedProductionRiskRate=sum(bool(r["productionRisk"]["flags"]) for r in rows.values()) / len(rows)
        if rows
        else None,
        top3CreativeDistance=pairwise_summary([s["candidate"] for s in selection["productionSlate"]]),
    )
    result = {
        "workflow": "GENERATE_AND_RANK_SHORT_CONCEPTS",
        "generatorVersion": legacy.old.VERSION,
        "beatGrammarVersion": beats.VERSION,
        "premiseNaturalnessGateVersion": gate.VERSION,
        "seed": config.seed,
        "generationConfig": {**config.model_dump(exclude={"canonicalCast"}), "canonicalCast": cast},
        "castEvidence": {"source": source, "sha256": digest(cast)},
        "generationEvidence": evidence,
        "generationSummary": {
            "requestedCount": config.count,
            "rawCandidateCount": len(candidates),
            "finalCandidateCount": len(candidates),
            "eligibleCount": counts["ELIGIBLE"],
            "revisionCount": counts["REVISION_REQUIRED"],
            "rejectedCount": counts["REJECTED"],
        },
        **ds,
        "diversityScore": round(100 * ds["engineDiversity"], 2),
        "dominantEngineWarning": None,
        "candidates": records,
        "generationRejections": rejected,
        "suppressedCandidates": suppressed,
        "rankingResult": raw,
        "rankedCandidates": raw["rankedEligibleCandidates"] if raw else [],
        "productionSelection": selection,
        "top3ProductionCandidates": selection["productionSlate"],
        "firstRenderCandidate": selection["firstRenderCandidate"],
        "beatGrammarMetrics": metrics,
        "generatorMetrics": metrics,
        "premiseNaturalnessMetrics": premise_metrics(candidates),
        "providerCalls": 0,
        "renderAuthorized": False,
        "selfOptimizationEnabled": False,
        "limitations": [
            (
                "Curated premise expectations are pre-render hypotheses, not "
                "human judgement or retention measurements."
            ),
            "Filtering uses no final ranking scores, rewrites or adaptive tuning.",
            (
                "Accepted ranker and Beat Grammar remain unchanged; admissible "
                "surreal premises can still fail accepted validation."
            ),
        ],
    }
    result["humanReadableConcepts"] = [human_report(r) for r in records]
    result["humanReadableTop3"] = [
        human_report(next(r for r in records if r["candidateId"] == s["candidateId"]))
        for s in selection["productionSlate"]
    ]
    result["reportLines"] = [
        "Premise Naturalness Gate V1: deterministic pre-render experiment.",
        *result["humanReadableConcepts"],
        *result["limitations"],
    ]
    return result
