"""Additive production selection. Accepted raw ranking and scores remain untouched."""

from .creative_distance import creative_distance, novelty, pairwise_summary, descriptors

TIE_MARGIN = 3
DIVERSITY_MARGIN = 5


def _number(row, key):
    return (row.get("shortFormEngine") or {}).get(key, 0) or 0


def tie_signals(row, candidate, peers):
    vector = novelty(candidate, peers)
    known = [v for k, v in vector.items() if k != "visualSilhouetteNovelty" and v is not None]
    return {
        "payoff": _number(row, "payoffScore"),
        "progress": _number(row, "progressDensityScore"),
        "frameZero": (row.get("shortFormEngine") or {}).get("instantPremiseLegibility", {}).get("score", 0),
        "duplicateRisk": {"HIGH": 2, "MODERATE": 1}.get(row.get("duplicateRisk"), 0),
        "batchNovelty": round(sum(known) / len(known), 6) if known else 0,
        "visualNovelty": vector["visualSilhouetteNovelty"] or 0,
        "productionRisk": len(row.get("productionRisk", {}).get("flags", [])),
        "rewatch": _number(row, "rewatchScore"),
        "noveltyVector": vector,
    }


def _key(row, candidate, peers):
    s = tie_signals(row, candidate, peers)
    return (
        -s["payoff"],
        -s["progress"],
        -s["frameZero"],
        s["duplicateRisk"],
        -s["batchNovelty"],
        -s["visualNovelty"],
        s["productionRisk"],
        -s["rewatch"],
        row["candidateId"],
    )


def materially_distinct(a, b):
    x, y = descriptors(a), descriptors(b)
    d = creative_distance(a, b)
    return (
        (x["engineFamily"] != y["engineFamily"] or x["trigger"] != y["trigger"])
        and (x["payoffTopology"] != y["payoffTopology"] or x["escalationTopology"] != y["escalationTopology"])
        and d["creativeDistance"] >= 0.32
        and not (x["objectCategory"] == y["objectCategory"] and d["visualSilhouetteSimilarity"] >= 0.625)
    )


def select_production(ranked, candidates):
    """Anchored quality bands prevent comparator cycles and chains of weak promotions."""
    by_id = {c["candidateId"]: c for c in candidates}
    pending = sorted(ranked, key=lambda r: (-r["rankingScore"], r["candidateId"]))
    ordered = []
    bands = []
    decisions = []
    while pending:
        anchor = pending[0]["rankingScore"]
        band = [r for r in pending if anchor - r["rankingScore"] <= TIE_MARGIN]
        band.sort(key=lambda r: _key(r, by_id[r["candidateId"]], candidates))
        for first, second in zip(band, band[1:]):
            left = tie_signals(first, by_id[first["candidateId"]], candidates)
            right = tie_signals(second, by_id[second["candidateId"]], candidates)
            key = next(
                (
                    k
                    for k in (
                        "payoff",
                        "progress",
                        "frameZero",
                        "duplicateRisk",
                        "batchNovelty",
                        "visualNovelty",
                        "productionRisk",
                        "rewatch",
                    )
                    if left[k] != right[k]
                ),
                "candidateId",
            )
            decisions.append(
                {
                    "candidateId": first["candidateId"],
                    "comparedWith": second["candidateId"],
                    "firstDifferentiatingSignal": key,
                    "values": [first["candidateId"], second["candidateId"]]
                    if key == "candidateId"
                    else [left[key], right[key]],
                }
            )
        ordered.extend(band)
        bands.append({"anchorScore": anchor, "candidateIds": [r["candidateId"] for r in band]})
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
            if baseline["rankingScore"] - r["rankingScore"] <= DIVERSITY_MARGIN
            and all(materially_distinct(by_id[r["candidateId"]], by_id[s["candidateId"]]) for s in slate)
        ]
        if not available:
            adjustments.append(
                {
                    "code": "SLATE_UNDERFILLED_DIVERSITY_OR_QUALITY_GAP",
                    "remainingCandidateIds": [r["candidateId"] for r in remaining],
                }
            )
            break
        chosen = available[0]
        rank = len(slate) + 1
        signals = tie_signals(chosen, by_id[chosen["candidateId"]], candidates)
        slate.append(
            {
                **chosen,
                "rawRank": chosen["rank"],
                "productionSlateRank": rank,
                "productionRank": rank,
                "candidate": by_id[chosen["candidateId"]],
                "productionTieSignals": signals,
                "diversityAdjustmentReason": "MATERIAL_ENGINE_TRIGGER_AND_PAYOFF_ESCALATION_DISTANCE"
                if chosen is not baseline
                else "CREATIVE_TIE_ORDER_WITHIN_ANCHORED_3_POINT_BAND",
                "selectionReason": "Payoff, progress, frame-zero, duplicate risk, batch novelty, visual novelty, production flags, rewatch, then ID; no score mutation.",
            }
        )
        if chosen is not baseline:
            adjustments.append(
                {
                    "code": "CREATIVE_DIVERSITY_PROMOTION",
                    "candidateId": chosen["candidateId"],
                    "aheadOf": baseline["candidateId"],
                    "qualityGap": round(baseline["rankingScore"] - chosen["rankingScore"], 6),
                }
            )
        remaining.remove(chosen)
    return {
        "productionSlate": slate,
        "firstRenderCandidate": slate[0]["candidateId"] if slate else None,
        "tieBands": bands,
        "creativeTieDecisions": decisions,
        "productionOrder": [r["candidateId"] for r in ordered],
        "diversityAdjustments": adjustments,
        "top3PairwiseCreativeDistance": pairwise_summary([s["candidate"] for s in slate]),
        "policy": {
            "scoreMutation": False,
            "qualityTieMargin": TIE_MARGIN,
            "diversityMargin": DIVERSITY_MARGIN,
            "tieOrder": [
                "payoff",
                "progress",
                "frameZero",
                "duplicateRisk",
                "batchNovelty",
                "visualNovelty",
                "productionRisk",
                "rewatch",
                "candidateId",
            ],
            "noveltyAggregation": "Arithmetic mean of separately exposed known non-visual batch axes; visual axis follows separately.",
        },
    }
