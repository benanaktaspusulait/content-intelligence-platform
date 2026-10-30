"""Single compact.2 probe; reuse the frozen compact.1 bounded LOW SDK transport."""
from copy import deepcopy
from datetime import UTC, datetime
import os
from pathlib import Path
import time

from . import semantic_compact_1_probe_v1 as prior
from .semantic_concept_prompt_v2_compact_2 import Compact2PromptRequest, construct_native_request, inspect_response
from .semantic_live_experiment import write_new
from .semantic_schema_integrity_probe_v1 import timing_record

EXPERIMENT_ID = 'semantic-compact-2-low-probe-1-run-001'
worker = prior.worker
bounded = prior.bounded


def plan(profile, prior_high, accepted_low, accepted_compact1):
    old, selected = prior.plan(profile, prior_high, accepted_low)
    if old['arguments'] != accepted_compact1['arguments']:
        raise ValueError('Frozen successful compact.1 request required')
    if old['timeout'] != accepted_compact1['timeout'] or accepted_compact1['maxRetries'] != 0:
        raise ValueError('Accepted timeout/retry envelope changed')
    config = Compact2PromptRequest.model_validate({**old['configuration'], 'semanticConceptPromptVersion': 'v2-compact.2'})
    spec = construct_native_request(config, old['cast'], 1, selected)
    for key in ('timeout','maxOutputTokens','streamingMode','cast'):
        spec[key] = deepcopy(old[key])
    spec['configuration'] = config.model_dump()
    without_messages = lambda body: {k:v for k,v in body.items() if k!='messages'}
    if without_messages(spec['arguments']) != without_messages(old['arguments']):
        raise ValueError('Only prompt/version may change')
    spec.update(maximumLiveRequests=1, SDKMaxRetries=0, promptVersion='v2-compact.2',
                requestDiff=prior.low.differences(old['arguments'],spec['arguments']))
    return spec, selected


def execute(path, profile, prior_high, accepted_low, accepted_compact1, *, authorization, tests, runner=None):
    if not authorization or not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):
        raise ValueError('Authorization and completed offline regression required')
    spec, selected = plan(profile, prior_high, accepted_low, accepted_compact1)
    if not os.getenv('OPENAI_API_KEY'): raise ValueError('Credential unavailable; no call')
    path = Path(path);path.mkdir(parents=True,exist_ok=False)
    write_new(path/'plan.json',dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',reasoningEffort='low',
        promptVersion='v2-compact.2',candidateCount=1,maxOutputTokens=8192,timeout=spec['timeout'],
        structuredOutputMode='json_schema',streamingMode='NON_STREAMING',maximumLiveRequests=1,
        SDKMaxRetries=0,retries=0,fallbacks=0,DeepSeekCalls=0,renders=0,authorization=authorization,tests=tests,
        transport='Unmodified compact.1 bounded worker and CreativeCapabilityProvider SDK path'))
    for name,value in [('prompt.json',spec['prompt']),('configuration.json',spec['configuration']),
                       ('request-diff.json',spec['requestDiff']),('offline-schema-validation.json',spec['FINAL_PROVIDER_SCHEMA_VALIDATION'])]:
        write_new(path/name,value)
    write_new(path/'request-before-sdk.json',dict(provider='openai',baseUrl=selected['baseUrl'],arguments=spec['arguments'],timeout=spec['timeout'],maxRetries=0))
    start_ns=time.monotonic_ns();start_utc=datetime.now(UTC)
    write_new(path/'request-started.json',dict(logicalRequestCount=1,maximumLiveRequests=1,startUTC=start_utc.isoformat()))
    try:result=(runner or bounded)(path,selected,spec)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,usage=None,safeMessage='No retry or replacement')
    end_utc=datetime.now(UTC);end_ns=time.monotonic_ns()
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    raw=(path/'response.txt').read_text();inspection=None
    if result['status']=='COMPLETED' and raw:
        try:pre=prior.low.previous.pre_pipeline_contract(prior.low.previous.parse_exact(raw))
        except (ValueError,TypeError):pre=dict(parseFailed=True)
        write_new(path/'pre-pipeline-creative-contract.json',pre)
        try:inspection=inspect_response(raw,spec)
        except Exception as error:inspection=dict(executionClassification='UNRESOLVED',pipelineError=type(error).__name__,pipelineRan=False)
        write_new(path/'inspection.json',inspection)
        if inspection.get('pipeline'):write_new(path/'pipeline.json',inspection['pipeline'])
    result.update(executionClassification=inspection['executionClassification'].replace('COMPACT_FULL_CONTRACT','COMPACT_2_FULL_CONTRACT') if inspection else 'COMPACT_2_NO_CANDIDATE',
        timing=timing_record(start_utc,end_utc,start_ns,end_ns),responseBytes=len(raw.encode()),logicalRequestCount=1,maximumLiveRequests=1,
        retries=0,fallbacks=0,DeepSeekCalls=0,renders=0,selectedReasoningEffort='low',promptHash=spec['prompt']['sha256'],
        schemaHash=spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256'],pipelineRan=bool(inspection and inspection.get('pipelineRan')))
    write_new(path/'result.json',result)
    return result
