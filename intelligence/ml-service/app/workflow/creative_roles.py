"""Explicit text roles over existing adapters; generation never approves its own output."""
from __future__ import annotations
import json
import math
import os
from typing import Any

from app.llm.provider import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from .deepseek import DeepSeekTextProvider
from .story_quality import analyse_story_candidates

ROLES = {'STORY': 'deepseek', 'BUILD_PROMPT': 'openai', 'MINIMAL_REPAIR': 'openai'}


def role_readiness() -> dict[str, Any]:
    enabled = os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() == 'true'
    return {'enabled': enabled, 'liveVerified': False, 'roles': [
        {'role': role, 'provider': provider, 'model': os.getenv(f'WORKFLOW_{role}_MODEL', ''),
         'configured': bool(os.getenv(f'{provider.upper()}_API_KEY') and os.getenv(f'WORKFLOW_{role}_MODEL')),
         'modality': 'TEXT_ONLY', 'automaticFallback': False}
        for role, provider in ROLES.items()]}


def perform_role(role: str, text: str, context: dict[str, Any], provider: LLMProvider, model: str) -> dict[str, Any]:
    if role not in ROLES or not text.strip() or len(text.encode('utf-8')) > 16000:
        raise ValueError('Supported role and bounded text required')
    if any(context.get(key) for key in ('image', 'images', 'video')):
        raise ValueError('Creative roles are text-only; visual evidence was not supplied')
    system = {
        'STORY': 'Return JSON alternatives: one to three story candidates. Respect the requested generation mode and locked requirements. For EXPLORE_DIFFERENT_STORIES vary meaningful narrative structure; for IMPROVE_EXISTING_STORY preserve locked events and ending while offering refinements. Preserve the supplied characters and intent. No production authorization.',
        'BUILD_PROMPT': 'Return JSON prompt: a production prompt string. Use only supplied story, references and constraints. Do not invent character appearance or evidence. No production authorization.',
        'MINIMAL_REPAIR': 'Return JSON patches: at most three minimal edits with integer Unicode code point start/end, exact sourceQuote and replacement. Preserve protected intent and ESSENTIAL source quotes. Never return approval or rewrite the entire prompt.',
    }[role]
    safe_context = {key: context[key] for key in ('protectedIntent', 'intentRequirements', 'findings', 'retrievedLessons', 'constraints', 'storyGenerationMode', 'lockedRequirements', 'permittedVariation', 'mainCharacter', 'preferences', 'profile') if key in context}
    value = json.loads(provider.complete(json.dumps({'text': text, 'context': safe_context}, ensure_ascii=False), system=system, temperature=0))
    if not isinstance(value, dict):
        raise ValueError('Role result must be an object')
    if role == 'STORY':
        alternatives = value.get('alternatives')
        if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 3:
            raise ValueError('One to three bounded story alternatives required')
        for candidate in alternatives:
            if isinstance(candidate, str):
                if not candidate.strip() or len(candidate) > 12000: raise ValueError('Bounded story alternative text required')
            elif not isinstance(candidate, dict) or not isinstance(candidate.get('text') or candidate.get('description'), str) or len((candidate.get('text') or candidate.get('description')))>12000:
                raise ValueError('Story alternatives must contain bounded text')
        value['storyQuality'] = analyse_story_candidates(alternatives, context)
    elif role == 'BUILD_PROMPT':
        if not isinstance(value.get('prompt'), str) or not value['prompt'].strip() or len(value['prompt']) > 16000:
            raise ValueError('Bounded production prompt required')
    else:
        patches = value.get('patches')
        if not isinstance(patches, list) or len(patches) > 3:
            raise ValueError('At most three minimal patches required')
        for patch in patches:
            if not isinstance(patch, dict) or any(type(patch.get(k)) is not int for k in ('start', 'end')) or not 0 <= patch['start'] < patch['end'] <= len(text) or patch.get('sourceQuote') != text[patch['start']:patch['end']] or not isinstance(patch.get('replacement'), str):
                raise ValueError('Patch must bind to the exact source span')
    return {'role': role, 'provider': ROLES[role], 'model': model, 'result': value,
            'calls': 1, 'visualInspected': False, 'validationStatus': 'NOT_VALIDATED', 'usage': getattr(provider, 'last_usage', None)}


def run_paid_role(role: str, text: str, context: dict[str, Any], max_cost_usd: float) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError('Unknown creative role')
    if os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() != 'true':
        raise ValueError('Paid creative roles are disabled; explicit scope and budget required')
    model = os.getenv(f'WORKFLOW_{role}_MODEL', '')
    if not model:
        raise ValueError('Explicit server model configuration required; no fallback')
    input_rate = float(os.getenv(f'WORKFLOW_{role}_INPUT_USD_PER_MILLION', 'nan'))
    output_rate = float(os.getenv(f'WORKFLOW_{role}_OUTPUT_USD_PER_MILLION', 'nan'))
    if not all(math.isfinite(v) and v > 0 for v in (input_rate, output_rate, max_cost_usd)):
        raise ValueError('Verified server price configuration and explicit positive budget required')
    payload_bytes = len(json.dumps({'text': text, 'context': context}, ensure_ascii=False).encode('utf-8'))
    upper_bound = ((payload_bytes + 2000) * input_rate + 2000 * output_rate) / 1_000_000
    if payload_bytes > 24000 or upper_bound > max_cost_usd:
        raise ValueError('Request exceeds approved cost ceiling')
    provider = DeepSeekTextProvider(model) if role == 'STORY' else OpenAIProvider(model=model)
    provider.max_output_tokens = 2000
    provider.json_output = True
    result = perform_role(role, text, context, provider, model)
    result['costUpperBoundUsd'] = upper_bound
    result['approvedCostCeilingUsd'] = max_cost_usd
    return result
