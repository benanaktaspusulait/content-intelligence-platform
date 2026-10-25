"""Source-bound creative evidence, independent of vendors and scoring.

Presence is a fact about supplied fields, never a claim of visible/causal quality.
The accepted text-only validator input is preserved byte-for-byte. No vocabulary
is injected to make a taxonomy-unknown rule look like a known rule.
"""

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import creative_shape as shape
from . import premise_naturalness as natural
from .concept_fingerprint import digest
from .short_concept_generation import ranking_input

VERSION = "semantic-evidence-adapter-v1"
FIELD_MAP = {
    "visibleGoalEvidence": "everydayGoal",
    "primaryObjectEvidence": "primaryObject",
    "expectedAffordanceEvidence": "normalExpectation",
    "coreRuleEvidence": "impossibleRule",
    "triggerEvidence": "visibleTrigger",
    "openingProblemEvidence": "frameZeroDescription",
    "payoffEvidence": "finalPayoff",
    "loopEvidence": "loopPotential",
    "affordanceRelationshipEvidence": "whyThisObject",
    "goalRuleRelationshipEvidence": "goalRuleRelationship",
}
FieldName = Literal[
    "visibleGoalEvidence",
    "primaryObjectEvidence",
    "expectedAffordanceEvidence",
    "coreRuleEvidence",
    "triggerEvidence",
    "openingProblemEvidence",
    "payoffEvidence",
    "loopEvidence",
    "affordanceRelationshipEvidence",
    "goalRuleRelationshipEvidence",
]


class StrictEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class SourceEvidence(StrictEvidence):
    sourceType: Literal["SEMANTIC_NORMALIZED_FIELD"] = "SEMANTIC_NORMALIZED_FIELD"
    sourceField: str
    sourceText: str
    projectionRule: str
    confidence: Literal["EXPLICIT", "STRUCTURED_INFERENCE", "AMBIGUOUS"] = "EXPLICIT"


class EvidenceField(StrictEvidence):
    presence: Literal["PRESENT", "MISSING", "AMBIGUOUS"]
    classification: str = "UNCLASSIFIED"
    classificationBasis: Literal["NOT_CLASSIFIED", "EXISTING_NORMALIZER", "EXISTING_CREATIVE_SHAPE"] = (
        "NOT_CLASSIFIED"
    )
    evidence: list[SourceEvidence]


class BeatEvidence(StrictEvidence):
    beatNumber: int = Field(ge=1, le=30)
    beatStrategyEvidence: EvidenceField
    consequenceEvidence: EvidenceField
    progressionEvidence: EvidenceField
    hasStrategy: bool
    hasVisibleConsequence: bool
    hasNewInformation: bool


class CanonicalEvidence(StrictEvidence):
    version: Literal["semantic-evidence-adapter-v1"] = VERSION
    sourceSha256: str
    normalizedFieldsSha256: str
    candidateId: str
    fields: dict[FieldName, EvidenceField]
    beats: list[BeatEvidence]
    describedBeatCount: int
    enginePresence: Literal["PRESENT", "MISSING", "AMBIGUOUS"]
    engineClassification: str
    payoffPresence: Literal["PRESENT", "MISSING", "AMBIGUOUS"]
    payoffClassification: str
    payoffStatus: Literal[
        "PAYOFF_MISSING", "PAYOFF_PRESENT_CLASSIFIED", "PAYOFF_PRESENT_UNCLASSIFIED", "PAYOFF_AMBIGUOUS"
    ]
    providerDeclaredLoop: EvidenceField
    structurePresence: Literal["PRESENT", "MISSING"]
    structureClassification: str
    # This is explicitly not a verified causal-development count.
    fullySpecifiedBeatCount: int


def text(value):
    return value.strip() if isinstance(value, str) else ""


def normalize_fields(raw):
    """Lossless allowed-field selection, not creative generation or repair.

    Provider rationale, suggestions, model scores and eligibility labels cannot
    enter the evidence domain. Missing/malformed values stay empty/missing.
    """
    result = {field: text(raw.get(field)) for field in FIELD_MAP.values()}
    result["beats"] = (
        [
            {key: text(b.get(key)) for key in ("strategy", "visibleConsequence", "newInformation")}
            for b in raw.get("beats", [])
            if isinstance(b, dict)
        ]
        if isinstance(raw.get("beats"), list)
        else []
    )
    return result


def source(field, value, rule, confidence="EXPLICIT"):
    return SourceEvidence(
        sourceField=field, sourceText=value, projectionRule=f"{VERSION}:{rule}", confidence=confidence
    )


def field_evidence(field, value, classification="UNCLASSIFIED", basis="NOT_CLASSIFIED"):
    return EvidenceField(
        presence="PRESENT" if value else "MISSING",
        classification=classification,
        classificationBasis=basis,
        evidence=[source(field, value, "explicit-field-presence")] if value else [],
    )


def project(raw, candidate):
    """Project declared source facts; never score, infer success or choose winners."""
    fields = normalize_fields(raw)
    projected = {name: field_evidence(path, fields[path]) for name, path in FIELD_MAP.items()}
    beats = []
    for i, beat in enumerate(fields["beats"]):
        values = {key: field_evidence(f"beats[{i}].{key}", value) for key, value in beat.items()}
        beats.append(
            BeatEvidence(
                beatNumber=i + 1,
                beatStrategyEvidence=values["strategy"],
                consequenceEvidence=values["visibleConsequence"],
                progressionEvidence=values["newInformation"],
                hasStrategy=bool(beat["strategy"]),
                hasVisibleConsequence=bool(beat["visibleConsequence"]),
                hasNewInformation=bool(beat["newInformation"]),
            )
        )
    rule = fields["impossibleRule"]
    response = natural.infer_response({"impossibleRule": rule}) if rule else "UNSUPPORTED_RESPONSE"
    engine = (
        response
        if response not in ("UNSUPPORTED_RESPONSE", "ORDINARY_RESPONSE")
        else "UNCLASSIFIED_CAUSAL_ENGINE"
    )
    projected["coreRuleEvidence"] = field_evidence("impossibleRule", rule, engine, "EXISTING_NORMALIZER")
    trigger = (
        natural._trigger({"impossibleRule": fields["visibleTrigger"]})
        if fields["visibleTrigger"]
        else "UNSPECIFIED"
    )
    projected["triggerEvidence"] = field_evidence(
        "visibleTrigger",
        fields["visibleTrigger"],
        trigger if trigger != "UNSPECIFIED" else "UNCLASSIFIED_TRIGGER",
        "EXISTING_NORMALIZER",
    )
    # Reuse the accepted classifier only. Provider-suggested labels are not evidence.
    known = candidate.get("storyShapeFingerprint", {}).get("payoffFamily", "UNKNOWN")
    if known not in shape.PAYOFF_FAMILIES:
        known = "UNKNOWN"
    payoff = fields["finalPayoff"]
    last = fields["beats"][-1] if fields["beats"] else {}
    last_payoff = last.get("visibleConsequence", "")
    if not payoff:
        payoff_status, presence = "PAYOFF_MISSING", "MISSING"
    elif not last_payoff or payoff != last_payoff:
        payoff_status, presence = "PAYOFF_AMBIGUOUS", "AMBIGUOUS"
    else:
        payoff_status, presence = (
            ("PAYOFF_PRESENT_UNCLASSIFIED" if known == "UNKNOWN" else "PAYOFF_PRESENT_CLASSIFIED"),
            "PRESENT",
        )
    classification = "UNCLASSIFIED_PAYOFF_PATTERN" if known == "UNKNOWN" else known
    evidence = [source("finalPayoff", payoff, "explicit-terminal-field")] if payoff else []
    if last_payoff:
        evidence.append(
            source(
                f"beats[{len(fields['beats']) - 1}].visibleConsequence",
                last_payoff,
                "terminal-consequence-consistency",
            )
        )
    if last.get("newInformation"):
        evidence.append(
            source(
                f"beats[{len(fields['beats']) - 1}].newInformation",
                last["newInformation"],
                "terminal-information-preserved",
            )
        )
    projected["payoffEvidence"] = EvidenceField(
        presence=presence,
        classification=classification,
        classificationBasis="EXISTING_CREATIVE_SHAPE",
        evidence=evidence,
    )
    result = CanonicalEvidence(
        sourceSha256=digest(raw),
        normalizedFieldsSha256=digest(fields),
        candidateId=candidate["candidateId"],
        fields=projected,
        beats=beats,
        describedBeatCount=len(beats),
        enginePresence=projected["coreRuleEvidence"].presence,
        engineClassification=engine,
        payoffPresence=presence,
        payoffClassification=classification,
        payoffStatus=payoff_status,
        providerDeclaredLoop=projected["loopEvidence"],
        structurePresence="PRESENT" if beats else "MISSING",
        structureClassification="PRESENT_UNCLASSIFIED_EVIDENCE" if known == "UNKNOWN" else known,
        fullySpecifiedBeatCount=sum(
            b.hasStrategy and b.hasVisibleConsequence and b.hasNewInformation for b in beats
        ),
    )
    return fields, result


def validator_input(candidate, evidence):
    """Current validators have a text-only contract: supply the unchanged plan.

    Typed evidence is carried separately. Passing it in a context dict would be
    silently ignored by SFE; injecting labels/synonyms into story text would be
    unsupported evidence. Neither is represented as improved score recognition.
    """
    if evidence.candidateId != candidate["candidateId"]:
        raise ValueError("Projection candidate identity mismatch")
    canonical = deepcopy(ranking_input(candidate))
    for target, name in [
        ("protagonistGoal", "visibleGoalEvidence"),
        ("objectOrPrimaryInteraction", "primaryObjectEvidence"),
        ("impossibleRuleOrCoreContradiction", "coreRuleEvidence"),
    ]:
        field = evidence.fields[name]
        canonical[target] = field.evidence[0].sourceText if field.presence == "PRESENT" else None
    return canonical


def project_candidate(raw, candidate):
    normalized, evidence = project(raw, candidate)
    result = deepcopy(candidate)
    canonical = validator_input(candidate, evidence)
    # Feed only accepted canonical input fields to the accepted orchestration.
    for target, key in [
        ("everydayGoal", "protagonistGoal"),
        ("primaryObject", "objectOrPrimaryInteraction"),
        ("impossibleRule", "impossibleRuleOrCoreContradiction"),
        ("frameZeroDescription", "frameZeroDescription"),
        ("beats", "escalationPlan"),
        ("finalPayoff", "finalPayoff"),
    ]:
        result[target] = deepcopy(canonical[key])
    result["semanticEvidenceAdapterVersion"] = VERSION
    result["canonicalCreativeEvidence"] = evidence.model_dump()
    result["normalizedSemanticFields"] = normalized
    return result
