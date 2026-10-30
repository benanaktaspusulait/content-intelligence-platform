"""Additive V2 prompt; no change to V1 schema, prompt, adapters or judges."""
import json
from pathlib import Path
from typing import Literal

from .concept_fingerprint import digest
from .semantic_concept_generation import GenerationRequest
from .semantic_concept_provider import build_prompt

PROMPT_VERSION = 'semantic-concept-prompt-v2'


class PromptV2Request(GenerationRequest):
    semanticConceptPromptVersion: Literal['v2'] = 'v2'


def prompt_v2(config, cast, raw_count=40):
    if config.semanticConceptPromptVersion != 'v2':
        raise ValueError('Explicit semanticConceptPromptVersion=v2 required')
    base = build_prompt(config, cast, raw_count)
    payload = json.loads(base['prompt'])
    payload.update(promptVersion=PROMPT_VERSION, semanticConceptPromptVersion='v2')
    payload['historicalCautionZones'].append(dict(
        referenceId='reset-to-start-shoe-territory',
        signature='Footwear returns protagonist to the starting position; repeated attempts and reset ending.'))
    payload['batchInstructions'] = dict(
        count=f'Return exactly {raw_count} raw ideas, not winners. No ranking, scores or production readiness claims.',
        length='About 15 seconds; exactly4 or5 major beats; concise physical sentences.',
        schema='Existing SemanticIdea schema unchanged; finalPayoff equals last visibleConsequence exactly.',
        authority='All self-checks are private editorial checks, never validator evidence or scores.')
    system = Path(__file__).with_suffix('.txt').read_text().strip()
    return dict(system=system, prompt=json.dumps(payload,sort_keys=True,ensure_ascii=False),
                version=PROMPT_VERSION, semanticConceptPromptVersion='v2',
                sha256=digest([system,payload]), basePromptVersion=base['version'],
                basePromptSha256=base['sha256'], responseSchemaChanged=False)
