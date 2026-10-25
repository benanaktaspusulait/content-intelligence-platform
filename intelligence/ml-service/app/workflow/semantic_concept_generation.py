"""Semantic/hybrid orchestration: mock possibilities, authoritative deterministic judgement."""

from collections import Counter
from copy import deepcopy
from typing import Literal

from pydantic import Field, model_validator

from . import concept_ranking as ranking
from . import creative_shape as shape
from . import shape_generation as deterministic
from .concept_fingerprint import digest
from .creative_distance import distributions
from .semantic_concept_provider import SemanticConceptGeneratorV1, SemanticProviderConfig
from .short_concept_generation import ranking_input, resolve_cast

MODE_FIELDS = {
    "generatorMode",
    "semanticProvider",
    "semanticRawCount",
    "semanticConceptPromptVersion",
    "allowExternalGeneration",
}


class GenerationRequest(deterministic.GenerationRequest):
    generatorMode: Literal["deterministic", "semantic", "hybrid"] | None = None
    semanticProvider: SemanticProviderConfig | None = None
    semanticRawCount: int | None = Field(None, ge=1, le=60, strict=True)
    semanticConceptPromptVersion: Literal["v1", "semantic-concept-prompt-v1"] = "v1"
    allowExternalGeneration: bool = False

    @model_validator(mode="before")
    @classmethod
    def explicit_mode_defaults(cls, value):
        if isinstance(value, dict) and value.get("generatorMode") is not None:
            value = dict(value)
            value.setdefault("generatorVersion", "v2")
            if value.get("generatorVersion") in ("v2", "short-concept-generator-v2"):
                for key, v in [
                    ("beatGrammarVersion", "v2"),
                    ("premiseNaturalnessGateVersion", "v1"),
                    ("creativeShapeVersion", "v1"),
                ]:
                    value.setdefault(key, v)
        return value

    @model_validator(mode="after")
    def semantic_stack(self):
        if self.generatorMode in ("semantic", "hybrid") and (
            not self.creativeShapeVersion or self.generatorVersion not in ("v2", "short-concept-generator-v2")
        ):
            raise ValueError(
                "Semantic/hybrid modes require the complete existing V2 deterministic validation stack"
            )
        if self.generatorMode is None and self.semanticProvider is not None:
            raise ValueError("Semantic provider requires an explicit generatorMode")
        return self

    def run_id(self):
        return "concept-run-" + digest(self.model_dump(exclude={"allowExternalGeneration"}))[:20]


def review_pool(pool):
    """Reuse accepted shape review; retain explicit new adapter coverage and recalculate peers."""
    overrides = {
        c["candidateId"]: c.get("storyShapeFingerprint")
        for c in pool
        if c.get("storyShapeFingerprint", {}).get("adapterVersion")
    }
    result = shape.review_batch(pool)
    for c in result:
        if c["candidateId"] in overrides:
            c["baselineStoryShapeFingerprint"] = c["storyShapeFingerprint"]
            c["storyShapeFingerprint"] = deepcopy(overrides[c["candidateId"]])
    for c in result:
        others = [p for p in result if p["candidateId"] != c["candidateId"]]
        closest = (
            min(others, key=lambda p: (shape.distance(c, p)["distance"], p["candidateId"]))
            if others
            else None
        )
        c["closestBatchShape"] = (
            {"candidateId": closest["candidateId"], **shape.distance(c, closest)} if closest else None
        )
        f = c["storyShapeFingerprint"]
        e = {}
        for label, path in [
            ("repeatedStrategySequence", "strategySequenceFingerprint"),
            ("repeatedPayoffFamily", "payoffFamily"),
            ("repeatedFinalRelationship", "finalRelationship"),
        ]:
            e[label] = sum(p["storyShapeFingerprint"][path] == f[path] for p in others)
        for label, path in [
            ("repeatedFalseSuccessPosition", "falseSuccessPosition"),
            ("repeatedTemporalShape", "temporalShape"),
        ]:
            e[label] = (
                sum(p["storyShapeFingerprint"]["dimensions"][path] == f["dimensions"][path] for p in others)
                if f["dimensions"][path]
                else 0
            )
        repeated = sum(v > 0 for v in e.values())
        c["templateShapeRisk"] = dict(
            code="TEMPLATE_SHAPE_RISK" if repeated else None,
            risk="HIGH"
            if repeated >= 3 or closest and shape.distance(c, closest)["distance"] < 0.2
            else "MEDIUM"
            if repeated
            else "LOW",
            evidence=e,
            peerDenominator=len(others),
        )
        c["historicalCreativeTerritory"] = shape.territory(c)
    return result


def deterministic_pool(config, cast):
    selected, evidence, rejected, suppressed = deterministic.prior.search(config, cast)
    values = {c["candidateId"]: c for c in selected}
    values.update({r["candidate"]["candidateId"]: r["candidate"] for r in suppressed})
    pool = [values[k] for k in sorted(values)]
    for c in pool:
        c.update(generationSource="DETERMINISTIC_V2", generationRunId=config.run_id())
        c["provenance"].update(generationSource="DETERMINISTIC_V2", generationRunId=config.run_id())
    return pool, evidence, rejected


def generate_and_rank(config, generator=None):
    config = GenerationRequest.model_validate(config)
    if config.generatorMode is None:
        return deterministic.generate_and_rank(config.model_dump(exclude=MODE_FIELDS, exclude_unset=True))
    config = GenerationRequest.model_validate(config.model_dump())
    if config.generatorMode == "deterministic" and config.generatorVersion in (
        "v1",
        "short-concept-generator-v1",
    ):
        result = deterministic.generate_and_rank(config.model_dump(exclude=MODE_FIELDS))
        for record in result["candidates"]:
            record["candidate"]["generationSource"] = "DETERMINISTIC_V1"
            record["candidate"]["generationRunId"] = config.run_id()
        result.update(generatorMode="deterministic", generationRunId=config.run_id())
        return result
    cast, source = resolve_cast(config)
    pool = []
    rejected = []
    det_evidence = None
    semantic_evidence = None
    if config.generatorMode in ("deterministic", "hybrid"):
        pool, det_evidence, rejected = deterministic_pool(config, cast)
    if config.generatorMode in ("semantic", "hybrid"):
        generator = generator or SemanticConceptGeneratorV1()
        if not isinstance(generator, SemanticConceptGeneratorV1):
            raise ValueError("Explicit semantic generator boundary required")
        pool.extend(generator.generate(config, cast))
        rejected.extend(generator.schema_rejections)
        semantic_evidence = generator.evidence
    pool = review_pool(pool)
    rows = {c["candidateId"]: ranking.validate_concept(ranking_input(c)) for c in pool}
    # A legibility floor applies identically to all sources; it never changes accepted scores.
    ready = []
    suppressed = []
    for c in pool:
        if c["premiseNaturalness"]["instantCausalLegibility"] < 60:
            suppressed.append(
                dict(
                    candidate=c,
                    validation=rows[c["candidateId"]],
                    suppressionReasons=[
                        "OPENING_EVIDENCE_INSUFFICIENT",
                        *deterministic.quality_reasons(c, rows[c["candidateId"]], config),
                    ],
                )
            )
        else:
            ready.append(c)
    selected, other_suppressed, decisions = deterministic.curate(ready, rows, config)
    suppressed.extend(other_suppressed)
    selected = review_pool(selected)
    raw = ranking.rank_concepts([ranking_input(c) for c in selected]) if selected else None
    finalrows = (
        {r["candidateId"]: r for r in raw["rankedEligibleCandidates"] + raw["revisionCandidates"]}
        if raw
        else {}
    )
    selection = (
        deterministic.production_selection(
            raw["rankedEligibleCandidates"],
            selected,
            config.minimumStoryShapeDistance,
            config.minimumShapeShortFormScore,
            config.minimumShapeRankingScore,
        )
        if raw
        else dict(productionSlate=[], firstRenderCandidate=None)
    )

    def record(c, row, final=False):
        chosen = next((s for s in selection["productionSlate"] if s["candidateId"] == c["candidateId"]), None)
        blocks = next(
            (
                s["suppressionReasons"]
                for s in suppressed
                if s["candidate"]["candidateId"] == c["candidateId"]
            ),
            [],
        )
        return dict(
            candidateId=c["candidateId"],
            candidate=c,
            generationSource=c["generationSource"],
            validation=row,
            disposition="ELIGIBLE"
            if row["eligibility"] == "ELIGIBLE" and not blocks
            else "REVISION_REQUIRED",
            deterministicEligibility=row["eligibility"],
            failureReasons=row["eligibilityReasons"],
            selectionBlockReasons=blocks,
            rawRank=row.get("rank"),
            productionSlateRank=chosen["productionSlateRank"] if chosen else None,
            premiseNaturalness=c["premiseNaturalness"],
            beatGrammar=c["beatGrammar"],
            creativeShape=c["storyShapeFingerprint"],
            structuredBeatPlan=c["structuredBeatPlan"],
            templateShapeRisk=c["templateShapeRisk"],
            closestBatchShape=c["closestBatchShape"],
            historicalCreativeTerritory=c["historicalCreativeTerritory"],
        )

    records = [record(c, finalrows[c["candidateId"]], True) for c in selected]
    attempts = [record(c, rows[c["candidateId"]]) for c in pool]
    metrics = shape.batch_metrics(selected)
    scores = [r["validation"]["shortFormScore"] for r in records]
    result = dict(
        workflow="GENERATE_AND_RANK_SHORT_CONCEPTS",
        generatorVersion="short-concept-generator-v2",
        generatorMode=config.generatorMode,
        generationRunId=config.run_id(),
        beatGrammarVersion="beat-grammar-v2",
        premiseNaturalnessGateVersion="premise-naturalness-v1",
        creativeShapeVersion="creative-shape-v1",
        semanticConceptPromptVersion="semantic-concept-prompt-v1",
        seed=config.seed,
        generationConfig=config.model_dump(exclude={"canonicalCast"}),
        castEvidence={"source": source, "sha256": digest(cast)},
        generationSummary=dict(
            requestedCount=config.count,
            rawCandidateCount=len(pool),
            finalCandidateCount=len(selected),
            eligibleCount=sum(r["disposition"] == "ELIGIBLE" for r in records),
            revisionCount=0,
            rejectedCount=0,
        ),
        generationEvidence=dict(
            capacityStatus="REQUEST_SATISFIED"
            if len(selected) == config.count
            else "DIVERSITY_CAPACITY_REACHED",
            deterministic=det_evidence,
            semantic=semantic_evidence,
            selectionDecisions=decisions,
            sourceDistribution=dict(Counter(c["generationSource"] for c in pool)),
        ),
        candidates=records,
        attempts=attempts,
        generationRejections=rejected,
        suppressedCandidates=suppressed,
        rankingResult=raw,
        rankedCandidates=raw["rankedEligibleCandidates"] if raw else [],
        productionSelection=selection,
        top3ProductionCandidates=selection["productionSlate"],
        firstRenderCandidate=selection["firstRenderCandidate"],
        generatorMetrics={**metrics, "averageShortFormScore": sum(scores) / len(scores) if scores else None},
        creativeShapeMetrics=metrics,
        providerCalls=0,
        externalProviderCalls=0,
        paidEvaluations=0,
        renderAuthorized=False,
        selfOptimizationEnabled=False,
        humanReviewRequired=True,
        **distributions(selected),
    )
    result["diversityScore"] = round(100 * result["engineDiversity"], 2)
    result["dominantEngineWarning"] = None
    result["humanReadableConcepts"] = [deterministic.human_report(r) for r in records]
    result["humanReadableTop3"] = [
        deterministic.human_report(next(r for r in records if r["candidateId"] == s["candidateId"]))
        for s in selection["productionSlate"]
    ]
    result["limitations"] = [
        "Mock fixtures verify architecture only and cannot demonstrate semantic superiority.",
        (
            "Novel mechanics may exceed accepted English-pattern coverage; "
            "their canonical revision outcomes are retained."
        ),
        "Provider rationale, suggested payoff and claimed novelty have no scoring or selection authority.",
        (
            "Human inspection and approval precede prompt generation and "
            "rendering. External semantic execution is disabled in V1."
        ),
    ]
    result["reportLines"] = [
        "Semantic concept boundary V1 — MOCK ONLY.",
        *result["humanReadableConcepts"],
        *result["limitations"],
    ]
    return result
