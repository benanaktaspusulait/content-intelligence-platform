"""Local engine-first concept generation; accepted ranking remains the only ranker."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import re
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import concept_ranking as ranking
from .concept_fingerprint import compare, digest, fingerprint, token

VERSION = "short-concept-generator-v1"


class CastMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=150)
    name: str = Field(min_length=1, max_length=80)


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    generatorVersion: Literal["short-concept-generator-v1"] = VERSION
    count: int = Field(20, ge=10, le=100, strict=True)
    seed: int = Field(42, ge=0, le=2147483647, strict=True)
    duration: float = Field(15, ge=10, le=20)
    characterIds: list[str] = Field(default_factory=list, max_length=100)
    excludeEngineFamilies: list[str] = Field(default_factory=list, max_length=100)
    excludeObjects: list[str] = Field(default_factory=list, max_length=100)
    excludeObjectCategories: list[str] = Field(default_factory=list, max_length=100)
    canonicalCast: list[CastMember] | None = Field(None, max_length=100)
    rank: bool = True

    @field_validator("characterIds", "excludeEngineFamilies", "excludeObjects", "excludeObjectCategories")
    @classmethod
    def ordered_constraints(cls, value):
        if any(not isinstance(v, str) or not v.strip() or len(v) > 150 for v in value):
            raise ValueError("Constraints require nonempty identifiers of at most 150 characters")
        return sorted({v.strip().casefold() for v in value})


class GeneratedConcept(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_min_length=1, str_strip_whitespace=True
    )
    candidateId: str
    title: str
    protagonist: str
    protagonistCharacterId: str
    everydayGoal: str
    primaryObject: str
    engineFamily: str
    impossibleRule: str
    goalRuleRelationship: str
    frameZeroDescription: str
    beats: list[ranking.ConceptBeat] = Field(min_length=4, max_length=5)
    escalationCurve: list[dict[str, Any]]
    finalPayoff: str
    loopPotential: dict[str, str]
    dialogueRequirement: Literal["NONE", "OPTIONAL", "STRUCTURALLY_REQUIRED"]
    environment: str
    intendedDurationSeconds: float = Field(ge=10, le=20)
    productionNotes: list[str]
    structuralPlan: dict[str, str]
    provenance: dict[str, Any]
    structuralFingerprint: dict[str, Any] | None = None

    @field_validator("beats")
    @classmethod
    def distinct_beats(cls, value):
        if len({beat.description.strip().casefold() for beat in value}) != len(value):
            raise ValueError("Identical repeated attempts are not a generated causal progression")
        return value


def resolve_cast(config: GenerationRequest) -> tuple[list[dict[str, str]], str]:
    if config.canonicalCast is not None:
        cast = [member.model_dump() for member in config.canonicalCast]
        source = "SUPPLIED_CANONICAL_REGISTRY_SNAPSHOT_NOT_INDEPENDENTLY_VERIFIED"
    else:
        # Read the repository's canonical seed data. Never copy descriptions or
        # hard-code the cast into generation logic; deployed backend supplies DB registry.
        seed_file = (
            Path(__file__).resolve().parents[3]
            / "backend/src/main/resources/db/migration/V4__seed_canonical_characters.sql"
        )
        if not seed_file.is_file():
            raise ValueError("Canonical cast unavailable; supply a registry snapshot via canonicalCast")
        cast = [
            {"id": row[0], "name": row[1]}
            for row in re.findall(r"\('([^']+)','([^']+)','[^']*','[^']*',true\)", seed_file.read_text())
        ]
        source = "REPOSITORY_CANONICAL_SEED_SNAPSHOT_NOT_LIVE_REGISTRY"
    cast.sort(key=lambda member: member["id"])
    if len({row["id"] for row in cast}) != len(cast) or len({row["name"].casefold() for row in cast}) != len(
        cast
    ):
        raise ValueError("Canonical cast IDs and names must be unique")
    selected = set(config.characterIds)
    if selected - {row["id"].casefold() for row in cast}:
        raise ValueError("Character constraints contain an unregistered character ID")
    if selected:
        cast = [row for row in cast if row["id"].casefold() in selected]
    if not cast:
        raise ValueError("No configured canonical characters remain")
    return cast, source


class ConceptCandidateGenerator(Protocol):
    version: str

    def generate(self, config: GenerationRequest, cast: list[dict[str, str]]) -> list[dict[str, Any]]: ...


class DeterministicConceptGenerator:
    version = VERSION

    def __init__(self, catalog: dict[str, Any] | None = None):
        self.catalog = (
            deepcopy(catalog)
            if catalog is not None
            else json.loads(Path(__file__).with_name("short_concept_catalog.json").read_text())
        )
        self.catalog["recipes"].sort(key=lambda recipe: recipe["id"])
        self.catalog_hash = digest(self.catalog)
        ids = [recipe["id"] for recipe in self.catalog["recipes"]]
        if len(set(ids)) != len(ids):
            raise ValueError("Engine recipe IDs must be unique")
        for recipe in self.catalog["recipes"]:
            if not 4 <= len(recipe["beats"]) <= 5 or len(set(recipe["beats"])) != len(recipe["beats"]):
                raise ValueError("Recipes require 4–5 distinct authored causal beats")
            if any(re.search(r"\{(?!character\})", beat) for beat in recipe["beats"]):
                raise ValueError("Only character assignment may be substituted into authored engines")

    def generate(self, config: GenerationRequest, cast: list[dict[str, str]]) -> list[dict[str, Any]]:
        families = {token(v) for v in config.excludeEngineFamilies}
        objects, categories = set(config.excludeObjects), set(config.excludeObjectCategories)
        recipes = [
            recipe
            for recipe in self.catalog["recipes"]
            if token(recipe["engineFamily"]) not in families
            and recipe["primaryObject"].casefold() not in objects
            and recipe["objectCategory"].casefold() not in categories
        ]
        if not recipes:
            raise ValueError("No engine recipes remain after exclusions")
        result, remaining, usage = [], [], Counter()
        recipe_usage = Counter()
        cap = max(2, math.ceil(config.count * 0.25))
        for index in range(config.count):
            if not remaining:
                cycle = index // len(recipes)
                remaining = sorted(
                    recipes, key=lambda recipe: (digest([config.seed, cycle, recipe["id"]]), recipe["id"])
                )
            alternatives = [recipe for recipe in remaining if usage[recipe["engineFamily"]] < cap]
            if not alternatives:
                alternatives = sorted(
                    [recipe for recipe in recipes if usage[recipe["engineFamily"]] < cap],
                    key=lambda recipe: (digest([config.seed, index, recipe["id"]]), recipe["id"]),
                )
            if not alternatives:
                minimum = min(usage[recipe["engineFamily"]] for recipe in remaining)
                alternatives = [recipe for recipe in remaining if usage[recipe["engineFamily"]] == minimum]
            recipe = alternatives[0]
            if recipe in remaining:
                remaining.remove(recipe)
            usage[recipe["engineFamily"]] += 1
            reuse_index = recipe_usage[recipe["id"]]
            recipe_usage[recipe["id"]] += 1
            # Goal/object/rule and causal path are fixed before character assignment.
            cast_index = int(digest([config.seed, recipe["id"], index])[:16], 16) % len(cast)
            actor = cast[cast_index]
            descriptions = [beat.format(character=actor["name"]) for beat in recipe["beats"]]
            beats = [
                {
                    "startSeconds": round(config.duration * i / len(descriptions), 2),
                    "endSeconds": config.duration
                    if i == len(descriptions) - 1
                    else round(config.duration * (i + 1) / len(descriptions), 2),
                    "description": value,
                }
                for i, value in enumerate(descriptions)
            ]
            structural = {
                key: recipe[key]
                for key in (
                    "interactionType",
                    "trigger",
                    "transformationDirection",
                    "escalationTopology",
                    "resolutionTopology",
                    "finalSilhouetteTopology",
                    "loopTopology",
                )
            }
            result.append(
                {
                    "candidateId": f"local-{recipe['id']}-{index + 1:03d}",
                    "title": recipe["title"],
                    "protagonist": actor["name"],
                    "protagonistCharacterId": actor["id"],
                    "everydayGoal": recipe["everydayGoal"],
                    "primaryObject": recipe["primaryObject"],
                    "engineFamily": recipe["engineFamily"],
                    "impossibleRule": recipe["impossibleRule"],
                    "goalRuleRelationship": recipe["goalRuleRelationship"],
                    "frameZeroDescription": descriptions[0],
                    "beats": beats,
                    "escalationCurve": [
                        {
                            "beatIndex": i + 1,
                            "plannedStateChange": value,
                            "sourceRule": recipe["impossibleRule"],
                        }
                        for i, value in enumerate(descriptions)
                    ],
                    "finalPayoff": descriptions[-1],
                    "loopPotential": {
                        "type": recipe["loopTopology"],
                        "status": "UNVERIFIED_CREATIVE_HYPOTHESIS",
                    },
                    "dialogueRequirement": "NONE",
                    "environment": recipe["environment"],
                    "intendedDurationSeconds": config.duration,
                    "productionNotes": deepcopy(recipe["productionNotes"]),
                    "structuralPlan": structural,
                    "provenance": {
                        "generatorVersion": self.version,
                        "seed": config.seed,
                        "recipeId": recipe["id"],
                        "catalogVersion": self.catalog["version"],
                        "catalogSha256": self.catalog_hash,
                        "characterAssignedAfterEngine": True,
                        "catalogCycle": index // len(recipes),
                        "recipeReuseIndex": reuse_index,
                    },
                }
            )
        return result


def ranking_input(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate["candidateId"],
        "title": candidate["title"],
        "protagonist": candidate["protagonist"],
        "protagonistGoal": candidate["everydayGoal"],
        "objectOrPrimaryInteraction": candidate["primaryObject"],
        "impossibleRuleOrCoreContradiction": candidate["impossibleRule"],
        "frameZeroDescription": candidate["frameZeroDescription"],
        "escalationPlan": candidate["beats"],
        "finalPayoff": candidate["finalPayoff"],
        "intendedDurationSeconds": candidate["intendedDurationSeconds"],
    }


def _distribution(candidates):
    counts = Counter(candidate.get("engineFamily", "UNSPECIFIED") for candidate in candidates)
    total = sum(counts.values())
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values()) if total else 0
    diversity = entropy / math.log(len(counts)) if len(counts) > 1 else 0
    dominant = max(counts.items(), key=lambda pair: (pair[1], pair[0])) if counts else (None, 0)
    return {
        "engineDistribution": dict(sorted(counts.items())),
        "diversityScore": round(100 * diversity, 2),
        "engineDiversity": round(diversity, 6),
        "dominantEngineWarning": {
            "engineFamily": dominant[0],
            "count": dominant[1],
            "total": total,
            "reason": "Engine family exceeds 35% of raw attempts; constraints or catalog exhaustion may limit diversity.",
        }
        if total and dominant[1] / total > 0.35
        else None,
    }


def generate_and_rank(
    config: GenerationRequest | dict[str, Any], generator: ConceptCandidateGenerator | None = None
) -> dict[str, Any]:
    config = GenerationRequest.model_validate(config)
    cast, cast_source = resolve_cast(config)
    generator = generator or DeterministicConceptGenerator()
    if generator.version != config.generatorVersion:
        raise ValueError("Generator version and explicit configuration differ")
    raw = deepcopy(generator.generate(config, cast))
    if len(raw) != config.count:
        raise ValueError("Generator must return the requested raw attempt count")
    raw.sort(key=lambda candidate: (str(candidate.get("candidateId", "")), digest(candidate)))
    records, admitted, seen = [], [], []
    for index, value in enumerate(raw):
        record = {
            "candidateId": str(value.get("candidateId") or f"incomplete-{index + 1:03d}"),
            "candidate": value,
            "disposition": "NOT_EVALUATED",
            "failureReasons": [],
            "validation": None,
        }
        records.append(record)
        try:
            candidate = GeneratedConcept.model_validate(value).model_dump()
            structure = fingerprint(candidate)
            record["structuralFingerprint"] = structure
            record["candidate"] = {**value, "structuralFingerprint": structure}
            if any(item["candidateId"] == record["candidateId"] for item in seen):
                raise ValueError("Duplicate candidate ID; every attempt must be addressable independently")
            previous = next(
                (item for item in seen if compare(structure, item["structuralFingerprint"])["nearDuplicate"]),
                None,
            )
            if previous:
                record.update(
                    disposition="STRUCTURAL_DUPLICATE",
                    duplicateOf=previous["candidateId"],
                    failureReasons=[
                        {
                            "code": "GENERATION_ENGINE_DUPLICATE",
                            "reason": "Same causal core; changing character, object, goal nouns or optional loop wording is not new execution.",
                        }
                    ],
                )
                continue
            seen.append(record)
            adapted = ranking_input(candidate)
            record["normalizedConcept"] = ranking.normalize(adapted)
            if len(admitted) >= 30:
                record.update(
                    disposition="DEFERRED_RANKING_CAPACITY",
                    failureReasons=[
                        {
                            "code": "EXISTING_RANKING_CAPACITY",
                            "reason": "Accepted ranking is limited to 30 structural admissions; no partial result is claimed to rank all candidates.",
                        }
                    ],
                )
                continue
            admitted.append(adapted)
        except (ValueError, TypeError, KeyError) as error:
            record.update(
                disposition="REVISION_REQUIRED",
                failureReasons=[{"code": "GENERATED_SCHEMA_INCOMPLETE", "reason": str(error)}],
            )
    ranked = ranking.rank_concepts(admitted) if admitted and config.rank else None
    if ranked:
        rows = {
            row["candidateId"]: row
            for row in ranked["rankedEligibleCandidates"] + ranked["revisionCandidates"]
        }
        for record in records:
            if record["disposition"] != "NOT_EVALUATED":
                continue
            validation = rows[record["candidateId"]]
            record["validation"] = validation
            record["historicalNoveltyGuard"] = {
                **validation["historicalComparison"],
                "classification": "ENGINE_SILHOUETTE_DUPLICATE"
                if validation["duplicateRisk"] == "HIGH"
                else "PROVEN_ENGINE_WITH_NEW_EXECUTION"
                if validation["historicalComparison"]["similarities"]
                else "NOVELTY_UNVERIFIED",
            }
            record["failureReasons"] = validation["eligibilityReasons"]
            record["disposition"] = (
                "ELIGIBLE"
                if validation["eligibility"] == "ELIGIBLE"
                else (
                    "REJECTED"
                    if validation["duplicateRisk"] == "HIGH"
                    or (validation["shortFormEngine"] or {}).get("status") == "REJECT"
                    else "REVISION_REQUIRED"
                )
            )
    counts = Counter(record["disposition"] for record in records)
    evaluated = [record["validation"] for record in records if record["validation"]]
    scores = [row["shortFormScore"] for row in evaluated if row["shortFormScore"] is not None]

    def rate(code):
        return (
            round(
                sum(
                    any(f["code"] == code for f in (row["shortFormEngine"] or {}).get("findings", []))
                    for row in evaluated
                )
                / len(evaluated),
                6,
            )
            if evaluated
            else None
        )

    distribution = _distribution(raw)
    candidates_by_id = {
        record["candidateId"]: record["candidate"] for record in records if record["validation"]
    }
    first = ranked["firstRenderCandidate"] if ranked else None
    slate = (
        [
            {**entry, "candidate": candidates_by_id[entry["candidateId"]]}
            for entry in ranked["productionSlate"]
        ]
        if ranked
        else []
    )
    first_row = (
        next((row for row in ranked["rankedEligibleCandidates"] if row["candidateId"] == first), None)
        if ranked
        else None
    )
    why = {
        "candidateId": first,
        "reason": first_row["whyRankedHere"]
        if first_row
        else "No eligible production candidate; revise the preserved failures.",
        "concreteDimensions": first_row["rankingDimensions"] if first_row else [],
        "comparisons": ranked["whyThisBeatsTheOthers"] if ranked else [],
        "historicalComparison": first_row["historicalComparison"] if first_row else None,
        "productionRisk": first_row["productionRisk"] if first_row else None,
    }
    result = {
        "workflow": "GENERATE_AND_RANK_SHORT_CONCEPTS",
        "generatorVersion": generator.version,
        "seed": config.seed,
        "generationConfig": {**config.model_dump(exclude={"canonicalCast"}), "canonicalCast": cast},
        "castEvidence": {"source": cast_source, "sha256": digest(cast), "visualIdentityVerified": False},
        "generationSummary": {
            "requestedCount": config.count,
            "rawCandidateCount": len(raw),
            "structuralDuplicateCount": counts["STRUCTURAL_DUPLICATE"],
            "eligibleCount": counts["ELIGIBLE"],
            "revisionCount": counts["REVISION_REQUIRED"],
            "rejectedCount": counts["REJECTED"] + counts["STRUCTURAL_DUPLICATE"],
            "deferredCount": counts["DEFERRED_RANKING_CAPACITY"],
            "notEvaluatedCount": counts["NOT_EVALUATED"],
            "rankingAdmissionCount": len(admitted),
            "catalogExhausted": any(v.get("provenance", {}).get("recipeReuseIndex", 0) > 0 for v in raw),
        },
        **distribution,
        "candidates": records,
        "rankedCandidates": ranked["rankedEligibleCandidates"] if ranked else [],
        "top3ProductionCandidates": slate,
        "firstRenderCandidate": first,
        "WHY_THIS_ONE_FIRST": why,
        "rankingResult": ranked,
        "rankingScope": "ALL_STRUCTURAL_ADMISSIONS"
        if not counts["DEFERRED_RANKING_CAPACITY"]
        else "FIRST_30_CANONICAL_ID_ADMISSIONS_ONLY",
        "generatorMetrics": {
            "eligibilityYield": round(counts["ELIGIBLE"] / len(raw), 6) if config.rank else None,
            "duplicateRate": round(counts["STRUCTURAL_DUPLICATE"] / len(raw), 6),
            "engineDiversity": distribution["engineDiversity"],
            "averageShortFormScore": round(sum(scores) / len(scores), 2) if scores else None,
            "topCandidateScore": first_row["rankingScore"] if first_row else None,
            "highActivityLowProgressRate": rate("HIGH_ACTIVITY_LOW_PROGRESS"),
            "weakPayoffRate": rate("WEAK_VISUAL_PAYOFF"),
            "lateHookRate": rate("OPENING_NOT_IN_TROUBLE"),
            "productionRiskRate": round(
                sum(bool(row["productionRisk"]["flags"]) for row in evaluated) / len(evaluated), 6
            )
            if evaluated
            else None,
            "evaluatedDenominator": len(evaluated),
            "scoreUse": "GENERATOR_DIAGNOSTICS_ONLY_NOT_CANONICAL_CREATIVE_SCORES",
        },
        "providerCalls": 0,
        "renderAuthorized": False,
        "selfOptimizationEnabled": False,
        "limitations": [
            "Highest-ranked production candidate is a pre-render hypothesis, not measured retention or a guaranteed outcome.",
            "Finite authored catalog; large batches retain exhausted-catalog repeats as rejected structural duplicates.",
            "Fingerprint metadata and accepted English pattern checks do not prove semantic novelty or rendered adherence.",
            "Historical coverage and existing hard gates/ranking/diversity policy are unchanged.",
        ],
    }
    for key in (
        "rawCandidateCount",
        "structuralDuplicateCount",
        "eligibleCount",
        "revisionCount",
        "rejectedCount",
    ):
        result[key] = result["generationSummary"][key]
    result["reportLines"] = project_generation_report(result)
    return result


def project_generation_report(result: dict[str, Any]) -> list[str]:
    lines = [
        "What should we make today? Deterministic pre-render hypotheses.",
        "Batch: " + json.dumps(result["generationSummary"], sort_keys=True),
        "Engine distribution: " + json.dumps(result["engineDistribution"], sort_keys=True),
        f"First production candidate: {result['firstRenderCandidate'] or 'none; revise preserved candidates'}",
    ]
    for entry in result["top3ProductionCandidates"]:
        row = next(row for row in result["rankedCandidates"] if row["candidateId"] == entry["candidateId"])
        lines.append(
            f"{entry['productionRank']}. {row['title']} ({row['candidateId']}): ranking {row['rankingScore']}; short form {row['shortFormScore']}; closest historical engine {row['historicalComparison']['closestHistoricalEngine']}; duplicate {row['duplicateRisk']}; production {row['productionRisk']}"
        )
        lines.append(row["whyRankedHere"]["text"])
    lines.append(
        "Failures retained: "
        + "; ".join(
            f"{row['candidateId']}: {row['disposition']}"
            for row in result["candidates"]
            if row["disposition"] not in {"ELIGIBLE", "NOT_EVALUATED"}
        )
    )
    lines.extend(result["limitations"])
    return lines
