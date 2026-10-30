"""Additive opt-in prompt repair. No default routing, schema or judge changes."""
from copy import deepcopy
import json
from pathlib import Path
from typing import Literal

from .concept_fingerprint import digest
from .semantic_concept_prompt_v2_compact import CompactPromptRequest, compact_prompt
from .semantic_native_schema_integrity_v1 import (
    final_provider_schema_validation, native_response_format, semantic_equivalence_proof,
)

PROMPT_VERSION = 'semantic-concept-prompt-v2-compact.1'


class Compact1PromptRequest(CompactPromptRequest):
    semanticConceptPromptVersion: Literal['v2-compact.1'] = 'v2-compact.1'


def compact1_prompt(config, cast, raw_count):
    if config.semanticConceptPromptVersion != 'v2-compact.1':
        raise ValueError('Explicit v2-compact.1 opt-in required')
    prior_config = CompactPromptRequest.model_validate({**config.model_dump(), 'semanticConceptPromptVersion': 'v2-compact'})
    prior = compact_prompt(prior_config, cast, raw_count)
    payload = json.loads(prior['prompt'])
    payload.update(promptVersion=PROMPT_VERSION, semanticConceptPromptVersion='v2-compact.1')
    system = Path(__file__).with_suffix('.txt').read_text().strip()
    return dict(system=system, prompt=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                version=PROMPT_VERSION, semanticConceptPromptVersion='v2-compact.1',
                sha256=digest([system, payload]), nativeSchemaSha256=prior['nativeSchemaSha256'],
                candidateSchemaDuplicatedInPrompt=False, providerCalls=0)


def construct_native_request(config, cast, raw_count, profile):
    if profile.get('responseMode') != 'json_schema':
        raise ValueError('Corrected native schema required; no fallback')
    prompt = compact1_prompt(config, cast, raw_count)
    fmt = native_response_format(raw_count)
    args = dict(model=profile['model'], messages=[dict(role='system', content=prompt['system']),
                dict(role='user', content=prompt['prompt'])], response_format=fmt,
                **{profile['tokenParameter']: config.semanticProvider.maxOutputTokens})
    if profile.get('reasoningEffort'): args['reasoning_effort'] = profile['reasoningEffort']
    if profile.get('temperatureSupported'): args['temperature'] = config.semanticProvider.temperature
    return dict(prompt=prompt, arguments=args,
                FINAL_PROVIDER_SCHEMA_VALIDATION=final_provider_schema_validation(fmt['json_schema']['schema']),
                semanticEquivalence=semantic_equivalence_proof(fmt['json_schema']['schema']), providerCalls=0,
                execution='OFFLINE_REQUEST_CONSTRUCTION_ONLY_NO_TRANSPORT')


def inspect_response(raw, spec):
    # The accepted inspection helper validates its configuration through a frozen
    # v2-compact-only model. Bridge that preliminary shape check; actual scoring
    # receives the explicit new configuration and prompt without changing judges.
    from .semantic_compact_capability_probe_v1 import inspect_response as accepted_inspect
    from .semantic_prompt_v2_experiment import analyze
    config = Compact1PromptRequest.model_validate(spec['configuration'])
    bridge = deepcopy(spec)
    bridge['configuration']['semanticConceptPromptVersion'] = 'v2-compact'
    return accepted_inspect(raw, bridge, analysis=lambda text, _legacy, prompt: analyze(text, config, prompt))
