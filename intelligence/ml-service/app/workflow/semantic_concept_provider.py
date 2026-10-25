"""Versioned, provider-neutral semantic ideation contract. V1 execution is mock-only."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.llm.provider import LLMProvider

from .concept_fingerprint import digest

VERSION = "semantic-concept-generator-v1"
PROMPT_VERSION = "semantic-concept-prompt-v1"
MAX_RESPONSE_BYTES = 2_000_000


class BoundedData(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)

    @model_validator(mode="after")
    def safe_text(self):
        def strings(value):
            if isinstance(value, str):
                return [value]
            if isinstance(value, dict):
                return [s for v in value.values() for s in strings(v)]
            if isinstance(value, list):
                return [s for v in value for s in strings(v)]
            return []

        text = " ".join(strings(self.model_dump()))
        if any(unicodedata.category(c) in ("Cc", "Cf") and c not in "\n\r\t" for c in text):
            raise ValueError("Unsupported control or formatting character")
        if re.search(r"\b(gun|knife|blood|chok\w*|strangl\w*|suicide|sexual|nude)\b", text, re.I):
            raise ValueError("Unsafe physical/sexual content for child-character ideation")
        return self


class SemanticBeat(BoundedData):
    strategy: str = Field(min_length=3, max_length=300)
    visibleConsequence: str = Field(min_length=8, max_length=1200)
    newInformation: str = Field(min_length=5, max_length=600)


class SemanticIdea(BoundedData):
    ideaId: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")
    title: str = Field(min_length=3, max_length=160)
    protagonistSuggestion: str = Field(min_length=1, max_length=100)
    everydayGoal: str = Field(min_length=3, max_length=300)
    primaryObject: str = Field(min_length=2, max_length=100)
    normalExpectation: str = Field(min_length=8, max_length=600)
    impossibleRule: str = Field(min_length=12, max_length=1200)
    visibleTrigger: str = Field(min_length=3, max_length=300)
    whyThisObject: str = Field(min_length=8, max_length=600)
    goalRuleRelationship: str = Field(min_length=8, max_length=600)
    frameZeroDescription: str = Field(min_length=15, max_length=1800)
    beats: list[SemanticBeat] = Field(min_length=4, max_length=5)
    finalPayoff: str = Field(min_length=8, max_length=1200)
    suggestedPayoffFamily: str = Field(min_length=2, max_length=100)
    loopPotential: str = Field(min_length=2, max_length=400)
    environment: str = Field(min_length=3, max_length=300)
    dialogueNeed: Literal["NONE", "OPTIONAL", "REQUIRED"] = "NONE"
    providerRationale: str = Field(min_length=1, max_length=1000)
    durationSeconds: float = Field(15, ge=10, le=20)

    @model_validator(mode="after")
    def consistent_final(self):
        if self.finalPayoff != self.beats[-1].visibleConsequence:
            raise ValueError("Final payoff must match the last visible consequence; no unplanned extra event")
        if len({b.model_dump_json() for b in self.beats}) != len(self.beats):
            raise ValueError("Repeated identical beat")
        return self


class SemanticProviderConfig(BoundedData):
    provider: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=2, max_length=120)
    temperature: float = Field(0.7, ge=0, le=2)
    maxCandidates: int = Field(60, ge=1, le=60, strict=True)
    maxOutputTokens: int = Field(16000, ge=1000, le=64000, strict=True)
    timeoutSeconds: float = Field(30, gt=0, le=90)
    mockCorpus: Literal["review-v1"] = "review-v1"


def build_prompt(config, cast, raw_count):
    refs = json.loads(Path(__file__).with_name("creative_territories_v1.json").read_text())
    system = """
You invent candidate possibilities; the deterministic application judges them. Return JSON only.
Invent visually understandable impossible situations where this exact everyday object behaves in
the worst possible way for what the character is trying to do. Aim for: I understand the problem
immediately, but I did not expect that. Strange but intuitive; avoid random magic.
One canonical main character, one everyday goal, one primary object/interaction, one dominant
impossible rule, immediate visible trouble, 4–5 major beats, and a causal payoff in about 15
seconds. Start with a frame-zero STILL showing who, goal and physical contradiction without
sound or text. Do not defer understanding.
Explain normal expectation, visible trigger, why this exact object and direct goal interference
before describing action. Every beat must identify character strategy, visible consequence and
genuinely new information/state change. The finalPayoff must equal the last beat's
visibleConsequence.
Invent outside fixed engine taxonomies. Vary progression, object category, impossible rule,
final silhouette and payoff across the raw pool. Inspiration families, not recipes: loss of
control, transfer, chain reaction, environmental takeover, delayed consequence, false assumption
reveal, goal reached wrongly, solution creates a new problem.
Avoid the default sequence: contact change → harder force/bracing → pause trigger → apparent
success → normal use resets the problem. Do not end every concept by recreating the opening.
Explore role reversal, property transfer, absurd success, visual reveal, logical extreme or
unexpected causal success; derive every ending from the original rule.
Do not select winners, assign scores/confidence, assert eligibility, change validators, or claim
novelty. Suggested payoff labels and rationale are informational only. No finished-story
examples are provided. Child-safe physical comedy only; no injury, weapons, dangerous restraint
or sexual content.
""".strip()
    payload = dict(
        promptVersion=PROMPT_VERSION,
        seed=config.seed,
        requestedFinalCount=config.count,
        requestedRawCount=raw_count,
        canonicalCast=cast,
        historicalCautionZones=[
            dict(referenceId=r["referenceId"], signature=r["signature"]) for r in refs["references"]
        ],
        outputEnvelope={"ideas": "array of candidate objects"},
        candidateSchema=SemanticIdea.model_json_schema(),
        limits=dict(
            maxOutputTokens=config.semanticProvider.maxOutputTokens,
            timeoutSeconds=config.semanticProvider.timeoutSeconds,
        ),
    )
    prompt = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return dict(system=system, prompt=prompt, version=PROMPT_VERSION, sha256=digest([system, payload]))


def parse_response(raw, max_candidates):
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("Semantic response exceeds bounded JSON size")

    def unique_pairs(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("Duplicate JSON object key")
            d[k] = v
        return d

    try:
        payload = json.loads(
            raw,
            object_pairs_hook=unique_pairs,
            parse_constant=lambda v: (_ for _ in ()).throw(ValueError("Non-finite JSON")),
        )
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError("Malformed semantic JSON response") from e
    if not isinstance(payload, dict) or set(payload) != {"ideas"} or not isinstance(payload["ideas"], list):
        raise ValueError("Semantic response requires only the ideas array envelope")
    if len(payload["ideas"]) > max_candidates:
        raise ValueError("Semantic response candidate limit exceeded")
    ids = [v.get("ideaId") for v in payload["ideas"] if isinstance(v, dict)]
    duplicates = {v for v in ids if isinstance(v, str) and ids.count(v) > 1}
    ideas = []
    rejected = []
    for i, item in enumerate(payload["ideas"]):
        try:
            idea = SemanticIdea.model_validate(item)
            if idea.ideaId in duplicates:
                raise ValueError("Duplicate ideaId; all occurrences rejected")
            ideas.append(idea)
        except (ValidationError, ValueError) as e:
            errors = (
                e.errors(include_input=False, include_url=False)
                if isinstance(e, ValidationError)
                else [{"msg": str(e)}]
            )
            # No exception objects or original untrusted data in serializable error evidence.
            rejected.append(
                dict(
                    index=i,
                    ideaId=item.get("ideaId") if isinstance(item, dict) else None,
                    stage="SCHEMA",
                    errors=[dict(loc=list(v.get("loc", [])), message=v["msg"]) for v in errors],
                )
            )
    return ideas, rejected


class MockSemanticProvider(LLMProvider):
    """No SDK/factory, networking, retries, environment credentials or fallback."""

    is_mock = True

    def __init__(self, corpus="review-v1", response=None):
        self.calls = []
        self.response = (
            response
            if response is not None
            else Path(__file__).with_name("semantic_concept_mock_v1.json").read_text()
        )

    def complete(self, prompt, system="", temperature=0.7, image=None):
        if image is not None:
            raise ValueError("Text ideation only")
        self.calls.append(dict(promptSha256=digest([system, prompt]), temperature=temperature))
        return self.response


class SemanticConceptGeneratorV1:
    """Conforms structurally to existing ConceptCandidateGenerator.generate(config, cast)."""

    version = VERSION

    def __init__(self, provider=None):
        self.provider = provider
        self.evidence = {}
        self.schema_rejections = []

    def generate(self, config, cast):
        p = config.semanticProvider
        if p is None:
            raise ValueError("SEMANTIC_PROVIDER_NOT_CONFIGURED: configure an explicit mock provider/model")
        if p.provider != "mock":
            if not config.allowExternalGeneration:
                raise ValueError("EXTERNAL_GENERATION_DISABLED: explicit permission is required")
            raise ValueError("LIVE_SEMANTIC_TRANSPORT_NOT_ENABLED: V1 implementation supports mocks only")
        if self.provider is not None and type(self.provider) is not MockSemanticProvider:
            raise ValueError("Only the controlled mock transport is executable in V1")
        raw_count = min(config.semanticRawCount or max(2 * config.count, 40), p.maxCandidates)
        prompt = build_prompt(config, cast, raw_count)
        provider = self.provider or MockSemanticProvider(p.mockCorpus)
        raw = provider.complete(prompt["prompt"], system=prompt["system"], temperature=p.temperature)
        ideas, self.schema_rejections = parse_response(raw, p.maxCandidates)
        accepted = sorted(ideas, key=lambda idea: idea.ideaId)[:raw_count]
        self.evidence = dict(
            prompt=prompt,
            providerName=p.provider,
            providerModel=p.model,
            providerPromptVersion=PROMPT_VERSION,
            requestedRawCount=raw_count,
            receivedRawCount=len(json.loads(raw)["ideas"]),
            schemaValidCount=len(ideas),
            normalizedCount=len(accepted),
            schemaRejectedCount=len(self.schema_rejections),
            maxOutputTokens=p.maxOutputTokens,
            timeoutSeconds=p.timeoutSeconds,
            estimatedRequestCount=1,
            recordedMockRequestCount=1,
            externalProviderCalls=0,
            automaticRetries=0,
            mockCorpusExhausted=len(ideas) < raw_count,
            responseSha256=digest(raw),
        )
        from .semantic_concept_adapter import normalize_idea

        normalized = []
        for idea in accepted:
            try:
                normalized.append(normalize_idea(idea, config, cast, prompt))
            except ValueError as error:
                self.schema_rejections.append(
                    dict(ideaId=idea.ideaId, stage="NORMALIZATION", errors=[dict(message=str(error))])
                )
        self.evidence.update(
            normalizedCount=len(normalized),
            normalizationRejectedCount=sum(r["stage"] == "NORMALIZATION" for r in self.schema_rejections),
            ignoredSchemaValidCount=len(ideas) - len(accepted),
        )
        return normalized
