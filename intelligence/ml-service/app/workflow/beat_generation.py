"""Versioned opt-in Beat Grammar orchestration; accepted V1/V2 code is untouched."""

from collections import Counter
from itertools import product
from typing import Literal
from pydantic import model_validator
from . import beat_grammar as bg
from . import short_concept_generation_v2 as old
from .short_concept_generation import resolve_cast, ranking_input
from .concept_fingerprint import digest, fingerprint, token
from . import concept_ranking as ranking
from .creative_distance import distributions, creative_distance, descriptors, pairwise_summary
from .concept_production_selection import tie_signals, materially_distinct


class GenerationRequest(old.GenerationRequest):
    beatGrammarVersion: Literal["v2", "beat-grammar-v2"] | None = None

    @model_validator(mode="after")
    def only_v2(self):
        if self.beatGrammarVersion and self.generatorVersion not in ("v2", old.VERSION):
            raise ValueError("Beat Grammar V2 requires generator V2 explicitly")
        return self


def generate_and_rank(config):
    config = GenerationRequest.model_validate(config)
    if not config.beatGrammarVersion:
        return old.generate_and_rank(config.model_dump(exclude={"beatGrammarVersion"}))
    return generate_with_beats(config)


def make_candidate(composition, shape, cast, config, grammar, data):
    plan = bg.build_plan(composition, shape, grammar, data)
    evidence = bg.assess(plan, composition, data)
    if evidence["beatGrammarQuality"] == "BROKEN":
        raise ValueError("Broken beat plan")
    actor = cast[int(digest([config.seed, composition, shape])[:12], 16) % len(cast)]
    texts = bg.render_plan(plan, composition, actor, grammar, data)
    obj = next(o for o in grammar["objects"] if o["id"] == composition["objectId"])
    goal = next(g for g in grammar["goals"] if g["id"] == composition["goalId"])
    final = plan[-1]["payoffStateChange"]
    structural = {
        "interactionType": goal["interaction"],
        "trigger": composition["trigger"],
        "transformationDirection": composition["stateTransition"],
        "escalationTopology": shape,
        "resolutionTopology": final,
        "finalSilhouetteTopology": plan[-1]["bodyStateAfter"],
        "loopTopology": "TRIGGER_RECREATES_PROBLEM" if final == "OPENING_PROBLEM_RETURNS" else "NONE",
    }
    candidate = {
        "candidateId": "bg2-" + digest([composition, shape])[:16],
        "title": f"{obj['name'].title()} / {composition['engineFamily'].replace('_', ' ').title()} / {shape.replace('_', ' ').title()}",
        "protagonist": actor["name"],
        "protagonistCharacterId": actor["id"],
        "everydayGoal": goal["visibleAction"],
        "primaryObject": obj["name"],
        "engineFamily": composition["engineFamily"],
        "impossibleRule": plan[0]["impossibleRule"],
        "goalRuleRelationship": f"The {composition['stateTransition'].lower().replace('_', ' ')} response to {goal['interaction']} blocks the working state needed to {goal['visibleAction']}.",
        "frameZeroDescription": texts[0],
        "beats": [
            {
                "startSeconds": round(i * config.duration / 5, 2),
                "endSeconds": config.duration if i == 4 else round((i + 1) * config.duration / 5, 2),
                "description": text,
            }
            for i, text in enumerate(texts)
        ],
        "finalPayoff": texts[-1],
        "escalationCurve": [
            {
                "beatIndex": p["beatNumber"],
                "sourceRule": p["impossibleRule"],
                "stateTransition": composition["stateTransition"],
                "transitionApplication": p["objectStateAfter"]["applicationCount"],
            }
            for p in plan
        ],
        "loopPotential": {"type": structural["loopTopology"], "status": "UNVERIFIED_CREATIVE_HYPOTHESIS"},
        "dialogueRequirement": "NONE",
        "environment": composition["environment"],
        "intendedDurationSeconds": config.duration,
        "productionNotes": [
            "One protagonist, one primary object; fixed boundary is declared in the planned environment.",
            "Broad contact only; verify body displacement and persistent object identity in later production.",
        ],
        "composition": composition,
        "structuralPlan": structural,
        "progressionShape": shape,
        "structuredBeatPlan": plan,
        "beatGrammar": evidence,
        "visualFingerprint": {
            "characterPoseFamily": plan[-1]["bodyStateAfter"],
            "objectRelativePosition": obj["position"],
            "dominantDirection": composition["stateTransition"],
            "objectScaleRelation": "INCREASING"
            if composition["stateTransition"] == "SCALE_UP"
            else "DECREASING"
            if composition["stateTransition"] == "SCALE_DOWN"
            else "STABLE",
            "characterObjectContact": plan[-1]["contactPattern"],
            "finalFrameComposition": final,
            "movementAxis": obj["axis"],
            "environmentInteraction": "BOUNDARY_CONTACT"
            if any(p["contactPattern"] == "FIXED_SURFACE_CONTACT" for p in plan)
            else "LOCAL_WORK_AREA",
        },
        "provenance": {
            "generatorVersion": old.VERSION,
            "beatGrammarVersion": bg.VERSION,
            "grammarSha256": digest(grammar),
            "beatGrammarSha256": digest(data),
            "seed": config.seed,
            "structuredBeforeProse": True,
            "characterAssignedAfterEngine": True,
        },
    }
    candidate["structuralFingerprint"] = fingerprint(candidate)
    return candidate


def search(config, cast):
    grammar = old.load_grammar()
    data = bg.load_data()
    for k in ("goals", "objects", "engines"):
        grammar[k].sort(key=lambda r: r["id"])
    options = []
    rejected = []
    for goal in grammar["goals"]:
        for obj in grammar["objects"]:
            if (
                goal["id"] not in obj["goalIds"]
                or obj["name"].casefold() in config.excludeObjects
                or obj["category"].casefold() in config.excludeObjectCategories
            ):
                continue
            for engine in grammar["engines"]:
                if engine["id"] in {token(s) for s in config.excludeEngineFamilies}:
                    continue
                for esc, pay, env in product(
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
                        escalationTopology=esc,
                        payoffTopology=pay,
                        environment=env,
                        stateTransition=engine["stateTransition"],
                    )
                    invalid = old.sanity_errors(composition, grammar)
                    if invalid:
                        rejected.append({"composition": composition, "reasons": invalid})
                        continue
                    for shape, profile in sorted(data["shapes"].items()):
                        errors = sorted(
                            {e for s in profile["strategies"] for e in bg.compatible(s, composition, data)}
                        )
                        if composition["stateTransition"] not in profile.get(
                            "validTransitions", [composition["stateTransition"]]
                        ):
                            errors.append("PROGRESSION_SHAPE_ENGINE_MISMATCH")
                        if errors:
                            rejected.append({"composition": composition, "shape": shape, "reasons": errors})
                        else:
                            options.append((composition, shape))
    options.sort(key=lambda p: digest([config.seed, p]))
    pool = [make_candidate(p, s, cast, config, grammar, data) for p, s in options[: config.internalPoolSize]]
    unique = []
    suppressed = []
    seen = set()
    for c in pool:
        # Distinct choreography can share an engine, but noun-swaps cannot create new choreography.
        core = digest(
            [
                c["engineFamily"],
                c["composition"]["trigger"],
                c["progressionShape"],
                c["beatGrammar"]["strategyFamilySequence"],
                c["beatGrammar"]["consequenceSequence"],
                c["beatGrammar"]["payoffStateChange"],
            ]
        )
        if core in seen:
            suppressed.append({"candidate": c, "reasons": ["ENGINE_AND_ATTEMPT_SEQUENCE_DUPLICATE"]})
            continue
        seen.add(core)
        unique.append(c)
    selected = []
    remaining = unique[:]
    while remaining and len(selected) < min(config.count, 30):
        eligible = [
            c for c in remaining if all(creative_distance(c, s)["creativeDistance"] >= 0.28 for s in selected)
        ]
        if not eligible:
            break

        def priority(c):
            d = descriptors(c)
            axes = ("engineFamily", "goalFamily", "objectCategory", "environment", "character")
            concentration = sum(sum(descriptors(s)[a] == d[a] for s in selected) for a in axes)
            choreography = sum(s["progressionShape"] == c["progressionShape"] for s in selected)
            return (
                concentration + 2 * choreography,
                -min((creative_distance(c, s)["creativeDistance"] for s in selected), default=1),
                digest([config.seed, c["candidateId"]]),
            )

        chosen = min(eligible, key=priority)
        selected.append(chosen)
        remaining.remove(chosen)
    suppressed.extend(
        {"candidate": c, "reasons": ["BATCH_DISTANCE_OR_CHOREOGRAPHY_CONCENTRATION"]} for c in remaining
    )
    return (
        selected,
        {
            "generatorVersion": old.VERSION,
            "beatGrammarVersion": bg.VERSION,
            "seed": config.seed,
            "requestedCount": config.count,
            "internalPoolSize": len(pool),
            "validCompositionCount": len(options),
            "finalCandidateCount": len(selected),
            "capacityStatus": "REQUEST_SATISFIED"
            if len(selected) == config.count
            else "RANKING_CAPACITY_REACHED"
            if len(selected) == 30
            else "DIVERSITY_CAPACITY_REACHED",
            "scope": "BOUNDED_LOCAL_SEARCH",
        },
        rejected,
        suppressed,
    )


def behaviorally_distinct(a, b):
    return materially_distinct(a, b) and (
        a["progressionShape"] != b["progressionShape"]
        or a["beatGrammar"]["payoffStateChange"] != b["beatGrammar"]["payoffStateChange"]
    )


def select_production(ranked, candidates):
    by_id = {c["candidateId"]: c for c in candidates}
    pending = sorted(ranked, key=lambda r: (-r["rankingScore"], r["candidateId"]))
    ordered = []

    def key(row):
        c = by_id[row["candidateId"]]
        s = tie_signals(row, c, candidates)
        b = c["beatGrammar"]
        return (
            -s["payoff"],
            -s["progress"],
            -s["frameZero"],
            s["duplicateRisk"],
            -b["strategyDiversityScore"],
            -b["consequenceDiversityScore"],
            -b["payoffDistance"],
            -b["bodyStateProgressionScore"],
            -s["batchNovelty"],
            -s["visualNovelty"],
            s["productionRisk"],
            -s["rewatch"],
            row["candidateId"],
        )

    while pending:
        anchor = pending[0]["rankingScore"]
        band = [r for r in pending if anchor - r["rankingScore"] <= 3]
        band.sort(key=key)
        ordered.extend(band)
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
            and all(behaviorally_distinct(by_id[r["candidateId"]], s["candidate"]) for s in slate)
        ]
        if not available:
            break
        row = available[0]
        c = by_id[row["candidateId"]]
        slate.append(
            {
                **row,
                "candidate": c,
                "rawRank": row["rank"],
                "productionSlateRank": len(slate) + 1,
                "productionRank": len(slate) + 1,
                "beatGrammar": c["beatGrammar"],
                "diversityAdjustmentReason": "BEAT_GRAMMAR_BEFORE_COSMETIC_NOVELTY_WITHIN_3_POINT_BAND_AND_5_POINT_DIVERSITY_MARGIN",
            }
        )
        if row is not baseline:
            adjustments.append(
                {
                    "code": "DIVERSITY_PROMOTION",
                    "candidateId": row["candidateId"],
                    "aheadOf": baseline["candidateId"],
                }
            )
        remaining.remove(row)
    return {
        "productionSlate": slate,
        "firstRenderCandidate": slate[0]["candidateId"] if slate else None,
        "diversityAdjustments": adjustments,
        "productionOrder": [r["candidateId"] for r in ordered],
        "policy": {
            "canonicalScoreMutation": False,
            "beatTieOrder": [
                "strategyDiversityScore",
                "consequenceDiversityScore",
                "payoffDistance",
                "bodyStateProgressionScore",
            ],
            "position": "AFTER_CANONICAL_PAYOFF_PROGRESS_HOOK_DUPLICATE_BEFORE_COSMETIC_NOVELTY_ID",
        },
        "top3PairwiseCreativeDistance": pairwise_summary([s["candidate"] for s in slate]),
    }


def human_report(candidate, record=None):
    c = candidate
    lines = [
        c["title"],
        "FRAME ZERO: " + c["frameZeroDescription"],
        "GOAL: " + c["everydayGoal"],
        "OBJECT: " + c["primaryObject"],
        "ENGINE: " + c["engineFamily"],
        "RULE: " + c["impossibleRule"],
    ]
    for b, text in zip(c["structuredBeatPlan"], c["beats"]):
        lines += [
            f"BEAT {b['beatNumber']}{' / PAYOFF' if b['beatNumber'] == 5 else ''}: {text['description']}",
            "Strategy: " + b["characterStrategy"],
            "Consequence: " + b["characterConsequence"],
            "New information: " + ", ".join(b["newInformation"]),
        ]
    e = c["beatGrammar"]
    lines += [
        "PAYOFF STATE CHANGE: " + str(e["payoffStateChange"]),
        f"strategyDiversityScore={e['strategyDiversityScore']}; consequenceDiversityScore={e['consequenceDiversityScore']}; bodyStateProgressionScore={e['bodyStateProgressionScore']}; spatialProgressionScore={e['spatialProgressionScore']}; payoffDistance={e['payoffDistance']}; beatGrammarQuality={e['beatGrammarQuality']}",
    ]
    if record:
        row = record["validation"]
        lines += [
            f"shortFormScore={row['shortFormScore'] if row else None}; rankingScore={row['rankingScore'] if row else None}; eligibility={record['disposition']}; productionSlateRank={record['productionSlateRank']}",
            "Accepted failures: " + ", ".join(f["code"] for f in record["failureReasons"]),
        ]
    return "\n".join(lines)


def generate_with_beats(config):
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
        slate = next((s for s in selection["productionSlate"] if s["candidateId"] == c["candidateId"]), None)
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
                "beatGrammar": c["beatGrammar"],
                "structuredBeatPlan": c["structuredBeatPlan"],
                "disposition": disposition,
                "failureReasons": row["eligibilityReasons"] if row else [],
                "validation": row,
                "rawRank": row.get("rank") if row else None,
                "productionSlateRank": slate["productionSlateRank"] if slate else None,
                "existingProgressFindingSupport": {
                    "acceptedCodes": [
                        f["code"]
                        for f in (row.get("shortFormEngine") or {}).get("findings", [])
                        if f["code"] in ("HIGH_ACTIVITY_LOW_PROGRESS", "IDENTICAL_ATTEMPTS")
                    ]
                    if row
                    else [],
                    "structuredFlags": c["beatGrammar"]["flags"],
                    "acceptedFindingsModified": False,
                },
            }
        )
    counts = Counter(r["disposition"] for r in records)
    ds = distributions(candidates)
    metrics = bg.batch_evidence(candidates)
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
        "generatorVersion": old.VERSION,
        "beatGrammarVersion": bg.VERSION,
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
        "providerCalls": 0,
        "renderAuthorized": False,
        "selfOptimizationEnabled": False,
        "limitations": [
            "Non-canonical structured plan diagnostics; no measured retention, semantic or rendered adherence claim.",
            "Accepted validators and ranking are unchanged; English pattern coverage still limits eligibility.",
            "New body reactions and environment constraints are planned causal hypotheses for human review.",
        ],
    }
    result["humanReadableConcepts"] = [human_report(r["candidate"], r) for r in records]
    result["humanReadableTop3"] = [
        human_report(s["candidate"], next(r for r in records if r["candidateId"] == s["candidateId"]))
        for s in selection["productionSlate"]
    ]
    result["reportLines"] = [
        "Beat Grammar V2 local pre-render experiment.",
        *result["humanReadableConcepts"],
        *result["limitations"],
    ]
    return result
