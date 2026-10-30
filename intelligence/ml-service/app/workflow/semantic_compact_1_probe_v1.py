"""One frozen LOW request for compact.1; same SDK adapter, guards and timeouts."""
from copy import deepcopy
from datetime import UTC, datetime
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback

import httpx
from .concept_fingerprint import digest
from . import semantic_low_reasoning_probe_v1 as low
from .semantic_concept_prompt_v2_compact_1 import Compact1PromptRequest, construct_native_request, inspect_response
from .semantic_native_schema_integrity_v1 import LastMileSchemaGuard
from .semantic_schema_integrity_probe_v1 import timing_record, OUTPUT_TOKENS
from .semantic_transport_isolation_v1 import TIMEOUT
from .semantic_live_experiment import write_new

EXPERIMENT_ID = 'semantic-compact-1-low-probe-1-run-001'


def plan(profile, prior_high, accepted_low):
    accepted = low.plan(profile, prior_high)
    if accepted['newRequest'] != accepted_low or accepted['selectedReasoningEffort'] != 'low':
        raise ValueError('Exact accepted LOW request required')
    original = accepted['spec']
    config = Compact1PromptRequest.model_validate({**original['configuration'], 'semanticConceptPromptVersion': 'v2-compact.1'})
    spec = construct_native_request(config, original['cast'], 1, accepted['profile'])
    for key in ('timeout', 'maxOutputTokens', 'streamingMode', 'cast'):
        spec[key] = deepcopy(original[key])
    spec['configuration'] = config.model_dump()
    old_body = deepcopy(accepted_low['arguments']); new_body = deepcopy(spec['arguments'])
    old_body.pop('messages'); new_body.pop('messages')
    if old_body != new_body: raise ValueError('Only prompt text/version may differ')
    old_payload = json.loads(accepted_low['arguments']['messages'][1]['content'])
    new_payload = json.loads(spec['arguments']['messages'][1]['content'])
    for payload in (old_payload, new_payload):
        payload.pop('promptVersion'); payload.pop('semanticConceptPromptVersion')
    if old_payload != new_payload: raise ValueError('Cast/history/count/schema metadata changed')
    spec.update(maximumLiveRequests=1, SDKMaxRetries=0, promptVersion='v2-compact.1',
                requestDiff=low.differences(accepted_low['arguments'], spec['arguments']))
    return spec, accepted['profile']


# Same bounded SDK/HTTP observer as the accepted compact worker. Only identity
# receipts below derive hashes from this explicit spec instead of legacy constants.
def worker(path,profile,spec,provider_factory=None):
    """Existing adapter and timeout envelope; instance-only observation and cap."""
    if provider_factory is None:
        from .creative_provider_profiles import CreativeCapabilityProvider
        provider_factory=CreativeCapabilityProvider
    path=Path(path);provider=None;raw='';guard=None;http_attempts=0;started=time.monotonic_ns()
    result=dict(status='FAILED',usage=None,httpStatus=None,timeToHeadersMs=None,firstTokenMs=None,
        firstUsableContentMs=None,providerRequestId=None,httpRequestId=None)
    try:
        provider=provider_factory(profile,OUTPUT_TOKENS,TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must remain disabled')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        provider.response_format=spec['arguments']['response_format']
        def before_http(request):
            nonlocal http_attempts
            if http_attempts:raise ValueError('HTTP request cap1; redirect/retry/fallback forbidden')
            body=json.loads(request.content)
            if digest(body)!=digest(spec['arguments']):raise ValueError('HTTP body differs from exact validated SDK request')
            http_attempts=1
            write_new(path/'http-request-started.json',dict(HTTPRequests=1,SDKMaxRetries=0,bodySha256=digest(body),method=request.method))
        def headers(response):
            result.update(httpStatus=response.status_code,timeToHeadersMs=(time.monotonic_ns()-started)/1e6,
                httpRequestId=response.headers.get('x-request-id'))
            write_new(path/'http-headers.json',dict(httpStatus=result['httpStatus'],timeToHeadersMs=result['timeToHeadersMs'],
                safeHeaders={k:response.headers[k] for k in ('x-request-id','content-type','retry-after') if k in response.headers}))
        provider.client._client.event_hooks['request'].append(before_http)
        provider.client._client.event_hooks['response'].append(headers)
        def record_actual(kwargs,receipt):
            write_new(path/'last-mile-sdk-request.json',kwargs)
            write_new(path/'final-provider-schema-validation.json',receipt)
            write_new(path/'sdk-request-forwarded.json',dict(SDKRequests=1,SDKMaxRetries=0,requestSha256=digest(kwargs),promptHash=spec['prompt']['sha256'],schemaHash=spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']))
        native_guard=LastMileSchemaGuard(provider.client.chat.completions.create,spec['arguments']['response_format'],record_actual)
        def exact_guard(**kwargs):
            if digest(kwargs)!=digest(spec['arguments']):raise ValueError('Last-mile SDK request differs from accepted exact request')
            return native_guard(**kwargs)
        guard=native_guard;provider.client.chat.completions.create=exact_guard
        write_new(path/'sdk-call-started.json',dict(provider='openai',model='gpt-6.1-sol',maximumLiveRequests=1,SDKMaxRetries=0))
        started=time.monotonic_ns()
        raw=provider.complete(spec['prompt']['prompt'],system=spec['prompt']['system'],temperature=.7)
        result.update(status='COMPLETED',firstUsableContentMs=(time.monotonic_ns()-started)/1e6 if raw else None)
    except Exception as error:
        chain=[];current=error;seen=set()
        while current is not None and id(current) not in seen and len(chain)<8:
            seen.add(id(current));chain.append(dict(exceptionClass=type(current).__name__,httpStatus=getattr(current,'status_code',None),providerCode=getattr(current,'code',None)))
            current=current.__cause__ or current.__context__
        result.update(errorClass=type(error).__name__,exceptionChain=chain,safeMessage='Single compact probe failed; no retry, fallback or replacement.',
            safeTrace=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)])
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        meta=getattr(provider,'last_response_metadata',None);usage=getattr(provider,'last_usage',None)
        result.update(usage=usage,providerMetadata=meta,providerRequestId=(meta or {}).get('requestId'),finishReason=(meta or {}).get('finishReason'),
            providerRequestIdMeaning='Completion response.id; HTTP x-request-id recorded separately if observable.',
            providerReportedCostUsd=(usage or {}).get('actual_cost_usd'),SDKRequestsForwarded=guard.forwarded if guard else 0,HTTPRequestsObserved=http_attempts)
        write_new(path/'response.txt',raw,raw=True);write_new(path/'worker-result.json',result)
        if provider:provider.client.close()


def bounded(path,profile,spec):
    process=multiprocessing.get_context('spawn').Process(target=worker,args=(str(path),profile,spec))
    process.start();process.join(TIMEOUT['wallSeconds']);expired=process.is_alive()
    if expired:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
    p=Path(path)/'worker-result.json'
    if not expired and p.exists():return json.loads(p.read_text())
    headers=Path(path)/'http-headers.json';h=json.loads(headers.read_text()) if headers.exists() else {}
    return dict(status='FAILED',errorClass='ExperimentWallTimeout' if expired else 'WorkerExited',usage=None,
        exceptionChain=[dict(exceptionClass='ExperimentWallTimeout' if expired else 'WorkerExited')],
        SDKRequestsForwarded=int((Path(path)/'sdk-request-forwarded.json').exists()),HTTPRequestsObserved=int((Path(path)/'http-request-started.json').exists()),
        httpStatus=h.get('httpStatus'),timeToHeadersMs=h.get('timeToHeadersMs'),firstUsableContentMs=None,
        safeMessage='Bounded worker stopped; no replacement request.')


def execute(path, profile, prior_high, accepted_low, *, authorization, tests, runner=None):
    if not authorization or not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):
        raise ValueError('Authorization and completed regression/schema proof required')
    spec, selected = plan(profile, prior_high, accepted_low)
    if not os.getenv('OPENAI_API_KEY'): raise ValueError('Credential unavailable; no call')
    path = Path(path); path.mkdir(parents=True, exist_ok=False)
    write_new(path/'plan.json', dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',
        reasoningEffort='low',candidateCount=1,promptVersion='v2-compact.1',maximumLiveRequests=1,
        SDKMaxRetries=0,retries=0,fallbacks=0,DeepSeekCalls=0,renders=0,timeout=spec['timeout'],
        maxOutputTokens=OUTPUT_TOKENS,streamingMode='NON_STREAMING',structuredOutputMode='json_schema',
        authorization=authorization,tests=tests))
    write_new(path/'prompt.json',spec['prompt']);write_new(path/'configuration.json',spec['configuration'])
    write_new(path/'request-before-sdk.json',dict(provider='openai',baseUrl=selected['baseUrl'],arguments=spec['arguments'],timeout=spec['timeout'],maxRetries=0))
    write_new(path/'request-diff.json',spec['requestDiff'])
    write_new(path/'offline-schema-validation.json',spec['FINAL_PROVIDER_SCHEMA_VALIDATION'])
    start_ns=time.monotonic_ns();start_utc=datetime.now(UTC)
    write_new(path/'request-started.json',dict(logicalRequestCount=1,maximumLiveRequests=1,startUTC=start_utc.isoformat()))
    try:result=(runner or bounded)(path,selected,spec)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,usage=None,safeMessage='No retry or replacement')
    end_utc=datetime.now(UTC);end_ns=time.monotonic_ns()
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    raw=(path/'response.txt').read_text();inspection=None
    if result['status']=='COMPLETED' and raw:
        try:pre=low.previous.pre_pipeline_contract(low.previous.parse_exact(raw))
        except (ValueError,TypeError):pre=dict(parseFailed=True)
        write_new(path/'pre-pipeline-creative-contract.json',pre)
        inspection=inspect_response(raw,spec)
        write_new(path/'inspection.json',inspection)
        if inspection.get('pipeline'):write_new(path/'pipeline.json',inspection['pipeline'])
    result.update(executionClassification=inspection['executionClassification'].replace('COMPACT_FULL_CONTRACT','COMPACT_1_FULL_CONTRACT') if inspection else 'COMPACT_1_NO_CANDIDATE',
        timing=timing_record(start_utc,end_utc,start_ns,end_ns),responseBytes=len(raw.encode()),logicalRequestCount=1,
        maximumLiveRequests=1,retries=0,fallbacks=0,DeepSeekCalls=0,renders=0,
        selectedReasoningEffort='low',promptHash=spec['prompt']['sha256'],schemaHash=spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256'],
        pipelineRan=bool(inspection and inspection.get('pipelineRan')))
    write_new(path/'result.json',result)
    return result
