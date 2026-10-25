"""Explicit single-request experiment. Import/replay never constructs a provider.

The accepted V1 path remains mock-only. This separate path stores a response first,
then injects a network-free replay generator into the unchanged judges.
"""

import hashlib
import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from .concept_fingerprint import digest
from .semantic_concept_adapter import normalize_idea
from .semantic_concept_generation import GenerationRequest, generate_and_rank
from .semantic_concept_provider import SemanticConceptGeneratorV1, SemanticIdea, build_prompt, parse_response
from .semantic_live_diagnostics import markdown, report
from .short_concept_generation import resolve_cast

PROMPT_VERSION = "semantic-concept-prompt-v1.1"
EXPERIMENT_ID = "semantic-live-v1-seed-42-count-40"


def write_new(path, value, raw=False):
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(value if raw else json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def live_prompt(config, cast):
    base = build_prompt(config, cast, 40)
    payload = json.loads(base["prompt"])
    payload["promptVersion"] = PROMPT_VERSION
    payload["historicalCautionZones"].append(
        dict(
            referenceId="reset-to-start-shoe-territory",
            signature=(
                "Footwear returns character to the starting position after apparent forward "
                "progress; repeated attempts and reset ending. Avoid recasting this mechanism. "
                "Source: deterministic Creative Shape seed-42 pool."
            ),
        )
    )
    payload["liveSearchDirections"] = {
        "mechanisms": (
            "Do not let grows/shrinks/sticks/resets/flips dominate. Explore function "
            "reversal, property transfer, delayed consequence, action duplication, state "
            "transfer, environmental consequence, accumulation, impossible containment, "
            "cause/result inversion, literal task interpretation, role reversal, spatial rule"
            " changes, physical dependency, conservation, self-created obstacles and causal "
            "chains. Inspiration only; no fixed taxonomy."
        ),
        "variation": (
            "Avoid excessive reuse of object category, trigger, impossible rule, five-beat "
            "progression, fake success, reset ending and final silhouette. Why this object "
            "must follow its function, affordance, material or expected motion."
        ),
        "boundedOutput": (
            "Return exactly 40 raw ideas, not winners; concise concrete sentences for each "
            "field and 4-5 beats. No model scores, rankings or self-selection. Use canonical "
            "character names. Preserve exact finalPayoff equality with last "
            "visibleConsequence."
        ),
    }
    prompt = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return dict(
        system=base["system"],
        prompt=prompt,
        version=PROMPT_VERSION,
        sha256=digest([base["system"], payload]),
        basePromptVersion=base["version"],
        basePromptSha256=base["sha256"],
    )


class StoredResponseGenerator(SemanticConceptGeneratorV1):
    """Trusted local replay adapter; accepts stored text, has no transport."""

    def __init__(self, raw, prompt):
        super().__init__()
        self.raw = raw
        self.prompt = deepcopy(prompt)

    def generate(self, config, cast):
        ideas, self.schema_rejections = parse_response(self.raw, config.semanticProvider.maxCandidates)
        normalized = []
        for idea in sorted(ideas, key=lambda i: i.ideaId):
            try:
                normalized.append(normalize_idea(idea, config, cast, self.prompt))
            except ValueError as error:
                self.schema_rejections.append(
                    dict(ideaId=idea.ideaId, stage="NORMALIZATION", errors=[dict(message=str(error))])
                )
        self.evidence = dict(
            providerName=config.semanticProvider.provider,
            providerModel=config.semanticProvider.model,
            providerPromptVersion=self.prompt["version"],
            responseSha256=digest(self.raw),
            receivedRawCount=len(json.loads(self.raw)["ideas"]),
            schemaValidCount=len(ideas),
            normalizedCount=len(normalized),
            schemaRejectedCount=sum(r["stage"] == "SCHEMA" for r in self.schema_rejections),
            normalizationRejectedCount=sum(r["stage"] == "NORMALIZATION" for r in self.schema_rejections),
            externalProviderCalls=0,
            execution="STORED_RESPONSE_REPLAY_NO_TRANSPORT",
            automaticRetries=0,
        )
        return normalized


def replay(raw, config, prompt, baseline):
    """No provider factory, credential reads or network calls."""
    run = generate_and_rank(config, StoredResponseGenerator(raw, prompt))
    diagnostics = report(json.loads(raw)["ideas"], run, baseline)
    return dict(
        storedResponseValidation=run,
        diagnostics=diagnostics,
        replayMetadata=dict(
            actualPromptVersion=prompt["version"],
            providerCallsDuringReplay=0,
            acceptedOrchestratorLabels=(
                "Inherited V1 MOCK ONLY labels/counters describe accepted orchestration, not this"
                " separately recorded live transport."
            ),
            responseSha256=digest(raw),
        ),
    )


def plan(configuration):
    return dict(
        experimentId=EXPERIMENT_ID,
        provider=configuration["provider"],
        model=configuration["model"],
        maxRequestCount=1,
        requestedRawCount=40,
        requestedFinalCount=20,
        seed=42,
        maxOutputTokens=64000,
        timeoutSeconds=90,
        automaticRetries=0,
        fallback=False,
        maxCostUsd=2,
        liveGenerationByteDeterministic=False,
        allowExternalGeneration=False,
    )


def configuration_for(configuration):
    return GenerationRequest(
        generatorMode="semantic",
        seed=42,
        count=20,
        semanticRawCount=40,
        semanticProvider=dict(
            provider=configuration["provider"],
            model=configuration["model"],
            maxCandidates=60,
            maxOutputTokens=64000,
            timeoutSeconds=90,
        ),
        allowExternalGeneration=True,
    )


def response_format():
    return dict(
        type="json_schema",
        json_schema=dict(
            name="semantic_raw_ideas_v1",
            strict=False,
            schema=dict(
                type="object",
                additionalProperties=False,
                properties=dict(
                    ideas=dict(type="array", minItems=40, maxItems=40, items=SemanticIdea.model_json_schema())
                ),
                required=["ideas"],
            ),
        ),
    )


def request_arguments(configuration, config, prompt):
    fmt = response_format()
    system = prompt["system"]
    if configuration["responseMode"] == "json_object":
        system += "\nReturn JSON matching this schema; use catalog IDs exactly:\n" + json.dumps(
            fmt["json_schema"]["schema"], separators=(",", ":")
        )
        fmt = {"type": "json_object"}
    args = dict(
        model=configuration["model"],
        messages=[dict(role="system", content=system), dict(role="user", content=prompt["prompt"])],
        response_format=fmt,
    )
    args[configuration["tokenParameter"]] = config.semanticProvider.maxOutputTokens
    if configuration.get("reasoningEffort"):
        args["reasoning_effort"] = configuration["reasoningEffort"]
    if configuration.get("temperatureSupported"):
        args["temperature"] = config.semanticProvider.temperature
    return args


def execute(directory, configuration, baseline, *, allow_external_generation=False, provider_factory=None):
    if not allow_external_generation:
        raise ValueError("EXTERNAL_GENERATION_DISABLED")
    bounded = plan(configuration)
    if configuration["maxOutputTokens"] < bounded["maxOutputTokens"]:
        raise ValueError("Configured model output capacity insufficient; no request attempted")
    key = configuration["provider"].upper() + "_API_KEY"
    if not os.getenv(key):
        raise ValueError("Configured provider credential unavailable; no request attempted")
    config = configuration_for(configuration)
    cast, _ = resolve_cast(config)
    prompt = live_prompt(config, cast)
    # Conservative configuration-derived upper estimate; not an actual bill.
    args = request_arguments(configuration, config, prompt)
    upper_input = len(json.dumps(args).encode("utf-8"))
    estimate = (
        upper_input * configuration["inputUsdPerMillion"] + 64000 * configuration["outputUsdPerMillion"]
    ) / 1e6
    if upper_input + 64000 > configuration["contextTokens"] or estimate > bounded["maxCostUsd"]:
        raise ValueError("Experiment context/cost ceiling exceeded; no request attempted")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Atomic directory claim precedes SDK construction and survives every failure.
    attempt = directory / "live-attempt"
    attempt.mkdir(exist_ok=False)
    bounded.update(
        allowExternalGeneration=True,
        configurationPriceUpperEstimateUsd=estimate,
        upperInputTokenEstimate=upper_input,
        estimateBasis="UTF8_BYTES_UPPER_ESTIMATE_PLUS_MAX_OUTPUT; CONFIGURED_PRICES_NOT_BILL",
    )
    write_new(attempt / "plan.json", bounded)
    write_new(
        attempt / "configuration.json", dict(profile=configuration, generation=config.model_dump(), cast=cast)
    )
    write_new(attempt / "prompt.json", prompt)
    write_new(
        attempt / "request.json",
        dict(
            baseUrl=configuration["baseUrl"],
            method="chat.completions.create",
            arguments=args,
            maxRetries=0,
            timeoutSeconds=90,
        ),
    )
    print(json.dumps(bounded), flush=True)
    if provider_factory is None:
        from .creative_provider_profiles import CreativeCapabilityProvider

        provider_factory = CreativeCapabilityProvider
    metadata = dict(
        startedAt=datetime.now(UTC).isoformat(),
        provider=configuration["provider"],
        model=configuration["model"],
        requestCount=0,
        status="PREPARING",
        usage=None,
        actualCostUsd=None,
    )
    provider = None
    raw = ""
    try:
        provider = provider_factory(configuration, 64000, 90)
        provider.response_format = response_format()
        metadata.update(requestCount=1, status="REQUEST_STARTED")
        write_new(attempt / "request-started.json", metadata)
        raw = provider.complete(
            prompt["prompt"], system=prompt["system"], temperature=config.semanticProvider.temperature
        )
        metadata["status"] = "COMPLETED"
    except Exception as error:
        # Exception messages may contain request headers/credentials. Keep safe type/status only.
        metadata.update(
            status="FAILED",
            errorType=type(error).__name__,
            httpStatus=getattr(error, "status_code", None),
            error="Provider request failed; no retry or fallback.",
        )
        raw = getattr(provider, "last_raw_response", "") if provider else ""
    finally:
        metadata.update(
            finishedAt=datetime.now(UTC).isoformat(),
            usage=getattr(provider, "last_usage", None),
            providerResponseMetadata=getattr(provider, "last_response_metadata", None),
        )
        write_new(attempt / "response.txt", raw, raw=True)
        write_new(attempt / "provider-metadata.json", metadata)
    if metadata["status"] != "COMPLETED":
        write_new(
            attempt / "manifest.json",
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(attempt.iterdir())
                if p.is_file()
            },
        )
        return metadata
    try:
        analysis = replay(raw, config, prompt, baseline)
        write_new(attempt / "analysis.json", analysis)
        write_new(attempt / "all-concepts-review.md", markdown(analysis["diagnostics"]), raw=True)
        write_new(
            attempt / "analysis-status.json",
            dict(
                status="COMPLETED",
                normalizedCount=len(analysis["storedResponseValidation"]["attempts"]),
                rawCount=len(analysis["diagnostics"]["allRawConcepts"]),
            ),
        )
    except Exception as error:
        write_new(
            attempt / "analysis-status.json",
            dict(status="FAILED", errorType=type(error).__name__, error=str(error)),
        )
    manifest = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(attempt.iterdir()) if p.is_file()
    }
    write_new(attempt / "manifest.json", manifest)
    return metadata
