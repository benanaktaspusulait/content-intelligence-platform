"""Offline-only versioned compact policy and native request construction.

No provider execution API. V1/V2 defaults and all judges remain unchanged.
"""
import json
import math
from pathlib import Path
from typing import Literal

from .concept_fingerprint import digest
from .semantic_concept_generation import GenerationRequest
from .semantic_concept_provider import build_prompt
from .semantic_native_schema_integrity_v1 import native_response_format,final_provider_schema_validation,semantic_equivalence_proof,VERSION as SCHEMA_VERSION

PROMPT_VERSION='semantic-concept-prompt-v2-compact'


class CompactPromptRequest(GenerationRequest):
    semanticConceptPromptVersion: Literal['v2-compact']='v2-compact'


def size_metrics(text):
    import re
    lines=text.splitlines()
    return dict(characters=len(text),UTF8Bytes=len(text.encode()),lines=len(lines),
        sections=[dict(line=i+1,title=line) for i,line in enumerate(lines) if line and line==line.upper() and re.search('[A-Z]',line)],
        instructionMarkerOccurrences={k:len(re.findall(p,text,re.I)) for k,p in dict(must=r'\bmust\b',doNot=r'\bdo not\b',never=r'\bnever\b',avoid=r'\bavoid\b',exactly=r'\bexactly\s*\d*',check=r'\bcheck\b').items()},
        estimatedTokens=math.ceil(len(text)/4),estimateMethod='Local character proxy:4 characters/token assumption; not model tokenization or billing.',
        exactTokenizerTokens=None,exactTokenizerStatus='No installed tokenizer/local model-token counting utility; no download or provider call.')


def compact_prompt(config,cast,raw_count):
    if config.semanticConceptPromptVersion!='v2-compact':raise ValueError('Explicit v2-compact version required')
    fmt=native_response_format(raw_count)
    # Reuse accepted cast/history metadata; remove the schema duplicated in V1/V2 user text.
    base=json.loads(build_prompt(config,cast,raw_count)['prompt'])
    cautions=base['historicalCautionZones']+[dict(referenceId='reset-to-start-shoe-territory',signature='Footwear returns protagonist to the starting position; repeated attempts and reset ending.')]
    payload=dict(promptVersion=PROMPT_VERSION,semanticConceptPromptVersion='v2-compact',seed=config.seed,
        requestedRawCount=raw_count,canonicalCast=cast,historicalCautionZones=cautions,
        suppliedNativeSchema=dict(version=SCHEMA_VERSION,sha256=digest(fmt['json_schema']['schema'])))
    system=Path(__file__).with_suffix('.txt').read_text().strip()
    return dict(system=system,prompt=json.dumps(payload,ensure_ascii=False,sort_keys=True),version=PROMPT_VERSION,
        semanticConceptPromptVersion='v2-compact',sha256=digest([system,payload]),nativeSchemaSha256=digest(fmt['json_schema']['schema']),
        candidateSchemaDuplicatedInPrompt=False,providerCalls=0)


def construct_native_request(config,cast,raw_count,profile):
    if profile.get('responseMode')!='json_schema':raise ValueError('Compact path requires an explicitly supplied native schema; no text-schema fallback')
    prompt=compact_prompt(config,cast,raw_count);fmt=native_response_format(raw_count)
    args=dict(model=profile['model'],messages=[dict(role='system',content=prompt['system']),dict(role='user',content=prompt['prompt'])],
        response_format=fmt,**{profile['tokenParameter']:config.semanticProvider.maxOutputTokens})
    if profile.get('reasoningEffort'):args['reasoning_effort']=profile['reasoningEffort']
    if profile.get('temperatureSupported'):args['temperature']=config.semanticProvider.temperature
    return dict(prompt=prompt,arguments=args,FINAL_PROVIDER_SCHEMA_VALIDATION=final_provider_schema_validation(fmt['json_schema']['schema']),
        semanticEquivalence=semantic_equivalence_proof(fmt['json_schema']['schema']),providerCalls=0,
        execution='OFFLINE_REQUEST_CONSTRUCTION_ONLY_NO_TRANSPORT')
