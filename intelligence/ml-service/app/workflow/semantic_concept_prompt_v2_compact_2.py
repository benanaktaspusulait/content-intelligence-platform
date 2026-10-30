"""Additive frame-zero-first opt-in. Existing rules, schema and judges stay frozen."""
from copy import deepcopy
import json
from pathlib import Path
from typing import Literal

from .concept_fingerprint import digest
from .semantic_concept_prompt_v2_compact_1 import Compact1PromptRequest, construct_native_request as prior_request

PROMPT_VERSION = 'semantic-concept-prompt-v2-compact.2'


class Compact2PromptRequest(Compact1PromptRequest):
    semanticConceptPromptVersion: Literal['v2-compact.2'] = 'v2-compact.2'


def construct_native_request(config, cast, raw_count, profile):
    if config.semanticConceptPromptVersion != 'v2-compact.2':
        raise ValueError('Explicit v2-compact.2 opt-in required')
    bridge = Compact1PromptRequest.model_validate({**config.model_dump(), 'semanticConceptPromptVersion': 'v2-compact.1'})
    result = prior_request(bridge, cast, raw_count, profile)
    payload = json.loads(result['prompt']['prompt'])
    payload.update(promptVersion=PROMPT_VERSION, semanticConceptPromptVersion='v2-compact.2')
    system = Path(__file__).with_suffix('.txt').read_text().strip()
    result['prompt'] = {**result['prompt'], 'system': system,
        'prompt': json.dumps(payload, ensure_ascii=False, sort_keys=True), 'version': PROMPT_VERSION,
        'semanticConceptPromptVersion': 'v2-compact.2', 'sha256': digest([system,payload])}
    result['arguments']['messages'] = [dict(role='system',content=system), dict(role='user',content=result['prompt']['prompt'])]
    return result


def inspect_response(raw, spec):
    # Only bridge the accepted helper's frozen preliminary config shape check.
    # The unchanged full pipeline receives the actual compact.2 config/provenance.
    from .semantic_compact_capability_probe_v1 import inspect_response as accepted_inspect
    from .semantic_prompt_v2_experiment import analyze
    config = Compact2PromptRequest.model_validate(spec['configuration'])
    bridge = deepcopy(spec)
    bridge['configuration']['semanticConceptPromptVersion'] = 'v2-compact'
    return accepted_inspect(raw, bridge, analysis=lambda text, _legacy, prompt: analyze(text, config, prompt))
