"""Observations only: never supplies score, eligibility or selection inputs."""

from collections import Counter
from statistics import mean, median

from . import creative_shape as shape


def audit(raw, record):
    c, v = record["candidate"], record["validation"]
    sfe = v["shortFormEngine"]
    natural = c["premiseNaturalness"]

    def item(status, supplied, interpreted):
        return dict(status=status, rawEvidence=supplied, validatorEvidence=interpreted)

    def recognized(yes):
        return "recognized" if yes else "not recognized"

    return {
        "everydayGoal": item(
            recognized(sfe["goalScore"] >= 60),
            raw.get("everydayGoal"),
            dict(goalScore=sfe["goalScore"], normalizedGoal=v["normalizedConcept"].get("protagonistGoal")),
        ),
        # The SFE reads combined Beat 1. Naturalness reads the raw opening. Keep both visible.
        "frameZeroAnomaly": item(
            "recognized" if natural["instantCausalLegibility"] >= 60 else "ambiguous",
            raw.get("frameZeroDescription"),
            dict(
                rawOpeningLegibility=natural["instantCausalLegibility"],
                flags=natural["flags"],
                combinedBeatOneLegibility=sfe["instantPremiseLegibility"],
            ),
        ),
        "coreRule": item(
            recognized(bool(sfe["rules"])),
            raw.get("impossibleRule"),
            dict(
                sfeRules=sfe["rules"],
                adapterEngine=c["engineFamily"],
                naturalResponse=natural["responseType"],
            ),
        ),
        "trigger": item(
            "ambiguous"
            if c["composition"]["trigger"] in ("UNKNOWN", "UNSPECIFIED", "UNSUPPORTED", "UNSUPPORTED_TRIGGER")
            else "recognized",
            raw.get("visibleTrigger"),
            c["composition"]["trigger"],
        ),
        "beatCount": item(
            recognized(sfe["majorCausalBeatCount"] == len(raw.get("beats", []))),
            len(raw.get("beats", [])),
            dict(described=sfe["describedBlockCount"], majorCausal=sfe["majorCausalBeatCount"]),
        ),
        "causalProgression": item(
            recognized(sfe["progressDensityScore"] >= 60 and sfe["escalationScore"] >= 60),
            raw.get("beats"),
            dict(
                progressDensityScore=sfe["progressDensityScore"],
                escalationScore=sfe["escalationScore"],
                beats=sfe["beats"],
                beatGrammar=c["beatGrammar"],
            ),
        ),
        "payoff": item(
            recognized(sfe["payoffScore"] >= 60),
            raw.get("finalPayoff"),
            dict(
                payoffScore=sfe["payoffScore"],
                shape=c["storyShapeFingerprint"]["payoffFamily"],
                finalRelationship=c["storyShapeFingerprint"]["finalRelationship"],
            ),
        ),
        "loop": item(
            "ambiguous",
            raw.get("loopPotential"),
            dict(
                sfeRewatchScore=sfe["rewatchScore"],
                shapeLoop=c["storyShapeFingerprint"]["dimensions"].get("loopMechanism"),
                limitation="Rewatch score alone does not verify the provider loop.",
            ),
        ),
    }


def diagnose(raw, record, extraction):
    v = record["validation"]
    if v["shortFormScore"] >= 60:
        return None
    mapping = dict(
        instantCausalLegibility="frameZeroAnomaly",
        visualContradiction="frameZeroAnomaly",
        goalClarity="everydayGoal",
        oneRuleStrength="coreRule",
        progressDensity="causalProgression",
        escalationQuality="causalProgression",
        payoffStrength="payoff",
        rewatchPotential="loop",
    )
    failures = []
    for dimension in v["rankingDimensions"]:
        if dimension["score"] >= 60:
            continue
        evidence = extraction[mapping[dimension["dimension"]]]
        # A supplied field is not proof of a good idea. Missing recognition is a possible mismatch.
        label = "UNKNOWN"
        reason = "Text diagnostics cannot establish creative quality or causal validity."
        if not evidence["rawEvidence"]:
            label = "STRUCTURE_FAILURE"
            reason = "Required source evidence is absent."
        elif dimension["dimension"] == "oneRuleStrength" and not v["shortFormEngine"]["rules"]:
            label = "EVIDENCE_EXTRACTION_FAILURE"
            reason = (
                "A rule was supplied, but SFE extracted no recognized rule family. This is a "
                "coverage observation, not proof the rule is coherent."
            )
        elif (
            dimension["dimension"] in ("progressDensity", "escalationQuality")
            and len({b.get("visibleConsequence") for b in raw.get("beats", [])}) == 1
        ):
            label = "CONTENT_FAILURE"
            reason = "Every raw beat repeats the exact same visible consequence."
        elif evidence["status"] == "not recognized":
            reason = (
                "Source evidence is present but unrecognized; content weakness and extraction "
                "coverage cannot be separated automatically."
            )
        failures.append(dict(**dimension, classification=label, diagnosticReason=reason, extraction=evidence))
    return dict(
        code="LOW_SCORE_DIAGNOSIS",
        shortFormScore=v["shortFormScore"],
        failedDimensions=failures,
        canonicalReasons=v["eligibilityReasons"],
        canonicalWarnings=v["weaknesses"],
        penalties=v["penalties"],
        classificationAuthority="OBSERVATIONAL_ONLY",
        scoreOverride=False,
    )


def human_review(record):
    return (
        record["validation"]["eligibility"] == "ELIGIBLE"
        or record["validation"]["shortFormScore"] >= 75
        or (
            record["candidate"]["premiseNaturalness"]["premiseNaturalness"] == "STRONG"
            and bool(
                record.get("selectionBlockReasons")
                or record.get("failureReasons")
                or record.get("suppressionReasons")
                or record["validation"].get("eligibilityReasons")
            )
        )
    )


def pool_records(run):
    if "attempts" in run:
        return run["attempts"]
    records = {r["candidate"]["candidateId"]: r for r in run["candidates"]}
    records.update({r["candidate"]["candidateId"]: r for r in run["suppressedCandidates"]})
    return [records[k] for k in sorted(records)]


def statistics(records, raw_count, production_count):
    scores = [r["validation"]["shortFormScore"] for r in records]
    candidates = shape.review_batch([r["candidate"] for r in records]) if records else []
    # Semantic adapter overlays are authoritative; use existing annotations for semantic runs.
    if records and records[0]["candidate"].get("generationSource") == "SEMANTIC_V1":
        candidates = [r["candidate"] for r in records]
    return dict(
        rawCandidateCount=raw_count,
        normalizedCount=len(records),
        validNormalizationRate=len(records) / raw_count if raw_count else None,
        eligibilityCount=sum(r["validation"]["eligibility"] == "ELIGIBLE" for r in records),
        eligibilityRate=sum(r["validation"]["eligibility"] == "ELIGIBLE" for r in records) / len(records)
        if records
        else None,
        meanShortFormScore=mean(scores) if scores else None,
        medianShortFormScore=median(scores) if scores else None,
        scoreDistribution=dict(
            Counter(
                "<60" if s < 60 else "60-74" if s < 75 else "75-89" if s < 90 else "90-100" for s in scores
            )
        ),
        meanStoryShapeDistance=shape.batch_metrics(candidates).get("meanStoryShapeDistance"),
        payoffFamilyDistribution=dict(
            Counter(c["storyShapeFingerprint"]["payoffFamily"] for c in candidates)
        ),
        templateShapeHighRate=sum(c["templateShapeRisk"]["risk"] == "HIGH" for c in candidates)
        / len(candidates)
        if candidates
        else None,
        historicalCollisionRate=sum(
            c["historicalCreativeTerritory"]["historicalCreativeTerritoryRisk"] == "HIGH" for c in candidates
        )
        / len(candidates)
        if candidates
        else None,
        productionCandidateCount=production_count,
        humanReviewCount=sum(human_review(r) for r in records),
        denominator="ALL_NORMALIZED_POOL; eligibility is canonical before selection suppression",
    )


def report(raw_items, run, baseline):
    records = run["attempts"]
    by_id = {r["candidate"]["providerData"]["ideaId"]: r for r in records}
    selected = {r["candidateId"]: r for r in run["candidates"]}
    slate = {r["candidateId"] for r in run["top3ProductionCandidates"]}
    det = pool_records(baseline)
    result = []
    for index, raw in enumerate(raw_items):
        raw = raw if isinstance(raw, dict) else {"invalidRawValue": raw}
        record = by_id.get(raw.get("ideaId"))
        rejections = [
            e
            for e in run["generationRejections"]
            if e.get("index") == index
            or e.get("stage") == "NORMALIZATION"
            and e.get("ideaId") == raw.get("ideaId")
        ]
        if record is None:
            result.append(
                dict(
                    rawIndex=index,
                    ideaId=raw.get("ideaId"),
                    title=raw.get("title"),
                    providerRawIdea=raw,
                    normalizationStatus="MALFORMED",
                    finalDisposition="MALFORMED",
                    failureReasons=rejections or ["ENVELOPE_OR_COUNT_REJECTED"],
                    normalizedInterpretation=None,
                )
            )
            continue
        extraction = audit(raw, record)
        closest = (
            min(
                det,
                key=lambda r: (
                    shape.distance(record["candidate"], r["candidate"])["distance"],
                    r["candidate"]["candidateId"],
                ),
            )
            if det
            else None
        )
        distance = shape.distance(record["candidate"], closest["candidate"]) if closest else None
        dimensions = record["creativeShape"]["dimensions"]
        differences = {
            k: dict(
                semantic=v, deterministic=closest["candidate"]["storyShapeFingerprint"]["dimensions"].get(k)
            )
            for k, v in dimensions.items()
            if closest and v != closest["candidate"]["storyShapeFingerprint"]["dimensions"].get(k)
        }
        unknown = record["candidate"]["engineFamily"] in (
            "UNCLASSIFIED_SEMANTIC_ENGINE",
            "UNSUPPORTED_RESPONSE",
        )
        cid = record["candidateId"]
        review = human_review(record)
        status = record["validation"]["shortFormEngine"]["status"]
        bucket = (
            "PRODUCTION_CANDIDATE"
            if cid in slate
            else "HUMAN_REVIEW"
            if review
            else "REJECTED"
            if status == "REJECT"
            else "REVISION_REQUIRED"
        )
        # Distinct structured shapes with unknown dimensions remain discovery hypotheses.
        discovery = dict(
            closestDeterministicCandidateId=closest["candidate"]["candidateId"] if closest else None,
            closestDeterministicTitle=closest["candidate"]["title"] if closest else None,
            structuredDistance=distance,
            differences=differences,
            exactShapeRepresented=not differences,
            discoveryStatus="DISTINCT_STRUCTURED_REPRESENTATION_REQUIRES_HUMAN_REVIEW"
            if differences
            else "REPRESENTED",
            noveltyVerified=False,
            limitation=(
                "Unknown/default adapter dimensions can inflate apparent distance; wording is not"
                " used as novelty evidence."
            ),
        )
        result.append(
            dict(
                rawIndex=index,
                ideaId=raw.get("ideaId"),
                title=raw.get("title"),
                candidateId=cid,
                providerRawIdea=raw,
                normalizationStatus="NORMALIZED",
                normalizedInterpretation=record,
                finalSelectedRecord=selected.get(cid),
                eligibility=record["validation"]["eligibility"],
                shortFormScore=record["validation"]["shortFormScore"],
                rankingScore=record["validation"]["rankingScore"],
                naturalness=record["premiseNaturalness"],
                beatGrammar=record["beatGrammar"],
                creativeShape=record["creativeShape"],
                historicalTerritoryRisk=record["historicalCreativeTerritory"],
                finalDisposition=bucket,
                canonicalStatus=status,
                failureReasons=record["failureReasons"],
                selectionBlockReasons=record["selectionBlockReasons"],
                humanReview=review,
                extractionAudit=extraction,
                lowScoreDiagnosis=diagnose(raw, record, extraction),
                engineDiscovery="UNCLASSIFIED_CAUSAL_ENGINE" if unknown else None,
                shapeDiscovery=discovery,
            )
        )
    return dict(
        allRawConcepts=result,
        HUMAN_REVIEW_SET=[r["candidateId"] for r in result if r.get("humanReview")],
        topProductionSlate=run["top3ProductionCandidates"],
        bucketCounts=dict(Counter(r["finalDisposition"] for r in result)),
        eligibilityCounts=dict(Counter(r.get("eligibility", "MALFORMED") for r in result)),
        comparison=dict(
            semantic=statistics(records, len(raw_items), len(slate)),
            deterministic=statistics(det, len(det), len(baseline["top3ProductionCandidates"])),
        ),
        limitations=[
            "One live run does not establish semantic superiority.",
            "Extraction diagnostics are observations/hypotheses, not manual score corrections.",
            (
                "No genuinely novel shape is certified automatically; inspect raw stories "
                "alongside structured differences."
            ),
        ],
    )


def markdown(evidence):
    lines = [
        "# Controlled semantic live experiment",
        "",
        (
            "All scores and canonical outcomes are unchanged. Raw ideas are provider "
            "evidence; diagnostic interpretations are explicitly provisional."
        ),
        "",
    ]
    lines += [
        "## Summary",
        "",
        "```json",
        __import__("json").dumps(
            {k: v for k, v in evidence.items() if k != "allRawConcepts"}, indent=2, ensure_ascii=False
        ),
        "```",
        "",
    ]
    for r in evidence["allRawConcepts"]:
        lines += [
            f"## {r['rawIndex'] + 1}. {r.get('title')} — {r.get('ideaId')}",
            "",
            (
                f"Disposition: {r['finalDisposition']}; eligibility: {r.get('eligibility')}; "
                f"SFE: {r.get('shortFormScore')}; ranking: {r.get('rankingScore')}"
            ),
            "",
            "### A. Provider raw idea",
            "",
        ]
        raw = r["providerRawIdea"]
        for key, value in raw.items():
            if key == "beats" and isinstance(value, list):
                for i, b in enumerate(value, 1):
                    lines.append(
                        f"**Beat {i}:** "
                        + (" ".join(f"{k}: {v}" for k, v in b.items()) if isinstance(b, dict) else str(b))
                    )
                    lines.append("")
            else:
                lines += [f"**{key}:** {value}", ""]
        lines += [
            "### B. Normalized / deterministic interpretation",
            "",
            "```json",
            __import__("json").dumps(
                {k: v for k, v in r.items() if k not in ("providerRawIdea", "finalSelectedRecord")},
                indent=2,
                ensure_ascii=False,
            ),
            "```",
            "",
        ]
    return "\n".join(lines)
