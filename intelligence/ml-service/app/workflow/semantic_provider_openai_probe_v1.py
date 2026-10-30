"""One authorized OpenAI probe through the unchanged CreativeCapabilityProvider.

No response/body hooks or new streaming path. Timings unavailable from the stable
adapter stay unknown. Capability PASS is independent of creative scores.
"""
from datetime import UTC, datetime
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback
import httpx

from .semantic_provider_execution_benchmark_v1 import request_for, TIMEOUT, OUTPUT_TOKENS
from .semantic_prompt_v2_experiment import analyze, all_ideas_text, review_cards
from .semantic_live_experiment import response_format, write_new
from .semantic_concept_provider import parse_response

ATTEMPT_ID='semantic-provider-openai-gpt-6-1-sol-probe-5-run-001'


def worker(path,profile,config,prompt):
    from .creative_provider_profiles import CreativeCapabilityProvider
    path=Path(path);provider=None;raw=''
    result=dict(status='FAILED',usage=None,providerCostUsd=None,providerRequestId=None,
        responseHeadersMs=None,firstTokenMs=None,firstUsableContentMs=None,sdkMaxRetries=0,
        timingScope='First usable content measured from existing complete() call start; no header/body/SSE instrumentation.')
    try:
        provider=CreativeCapabilityProvider(profile,OUTPUT_TOKENS,TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must be disabled')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        provider.response_format=response_format();provider.response_format['json_schema']['schema']['properties']['ideas'].update(minItems=5,maxItems=5)
        write_new(path/'sdk-call-started.json',dict(provider='openai',model='gpt-6.1-sol',requestCount=1,sdkMaxRetries=0,streamingMode='NON_STREAMING',responseMode='json_schema',strict=False))
        started=time.monotonic()
        raw=provider.complete(prompt['prompt'],system=prompt['system'],temperature=config['semanticProvider']['temperature'])
        result.update(status='COMPLETED',firstUsableContentMs=(time.monotonic()-started)*1000 if raw else None)
    except Exception as error:
        result.update(errorClass=type(error).__name__,errorCauseClass=type(error.__cause__).__name__ if error.__cause__ else None,
            httpStatus=getattr(error,'status_code',None),safeError='Existing OpenAI provider path failed; no retry, repair or fallback.',
            providerErrorCode=getattr(error,'code',None),providerErrorParam=getattr(error,'param',None),providerErrorType=getattr(error,'type',None),
            safeTrace=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)])
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        metadata=getattr(provider,'last_response_metadata',None)
        result.update(usage=getattr(provider,'last_usage',None),providerResponseMetadata=metadata,
            providerRequestId=(metadata or {}).get('requestId'),finishReason=(metadata or {}).get('finishReason'),
            providerRequestIdMeaning='Existing adapter stores response.id (completion ID); HTTP x-request-id is not exposed.',
            HTTPStatusExact=None,HTTPOutcome='SDK_COMPLETED' if result['status']=='COMPLETED' else 'FAILED')
        result['providerCostUsd']=(result['usage'] or {}).get('actual_cost_usd')
        write_new(path/'response.txt',raw,raw=True);write_new(path/'worker-result.json',result)


def bounded(path,profile,config,prompt):
    process=multiprocessing.get_context('spawn').Process(target=worker,args=(str(path),profile,config,prompt))
    process.start();process.join(TIMEOUT['wallSeconds']);timeout=process.is_alive()
    if timeout:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
    result=Path(path)/'worker-result.json'
    if not timeout and result.exists():return json.loads(result.read_text())
    return dict(status='FAILED',errorClass='ExperimentWallTimeout' if timeout else 'WorkerExited',
        safeError='OpenAI probe worker stopped; no second request.',usage=None,providerRequestId=None,
        providerCostUsd=None,responseHeadersMs=None,firstTokenMs=None,firstUsableContentMs=None)


def capability(raw):
    """Existing JSON/schema boundary; schema rejection still reaches validation."""
    if not raw:return dict(status='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_FAILED',reason='EMPTY_CONTENT',parsed=False,candidatesReachedSchema=0)
    try:
        ideas,rejected=parse_response(raw,60)
        count=len(ideas)+len(rejected)
        return dict(status='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_PASS' if count else 'OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_FAILED',
            reason='NONEMPTY_PARSEABLE_RESPONSE_REACHED_SCHEMA' if count else 'EMPTY_IDEAS_ARRAY',parsed=True,
            candidatesReachedSchema=count,schemaValidCount=len(ideas),schemaRejectedCount=len(rejected))
    except (ValueError,TypeError):return dict(status='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_FAILED',reason='MALFORMED_RESPONSE',parsed=False,candidatesReachedSchema=0)


def execute(path,profile,*,authorization=None,tests=None,runner=None):
    if not authorization or not tests or not tests.get('noNewFailures'):raise ValueError('Authorization and completed tests required')
    if (profile['provider'],profile['model'],profile['responseMode'])!=('openai','gpt-6.1-sol','json_schema'):
        raise ValueError('Only exact configured OpenAI/gpt-6.1-sol native schema path is authorized')
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('OpenAI credential unavailable')
    if profile['maxOutputTokens']<OUTPUT_TOKENS:raise ValueError('Insufficient configured output capacity')
    cfg,p,args=request_for(profile);path=Path(path);path.mkdir(parents=True,exist_ok=False)
    write_new(path/'plan.json',dict(attemptId=ATTEMPT_ID,provider='openai',model='gpt-6.1-sol',promptVersion='v2',candidateCount=5,
        maxLiveRequests=1,sdkMaxRetries=0,fallback=False,timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS,
        streamingMode='NON_STREAMING',structuredOutputMode='json_schema',strict=False,authorization=authorization,tests=tests,
        adapter='Existing CreativeCapabilityProvider.complete; no body or response hook instrumentation'))
    write_new(path/'configuration.json',dict(profile=profile,generation=cfg.model_dump()))
    write_new(path/'prompt.json',p);write_new(path/'request.json',dict(baseUrl=profile['baseUrl'],arguments=args,maxRetries=0,timeout=TIMEOUT))
    start=time.monotonic();stamp=datetime.now(UTC).isoformat();write_new(path/'request-started.json',dict(provider='openai',requestCount=1,start=stamp))
    try:result=(runner or bounded)(path,profile,cfg.model_dump(),p)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,safeError='Probe runner failed; no replacement.',usage=None)
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    raw=(path/'response.txt').read_text()
    result.update(attemptId=ATTEMPT_ID,provider=profile['provider'],model=profile['model'],promptVersion='v2',candidateCount=5,
        start=stamp,end=datetime.now(UTC).isoformat(),durationSeconds=time.monotonic()-start,
        timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS,structuredOutputMode='json_schema',strict=False,
        streamingMode='NON_STREAMING',responseBytes=len(raw.encode()),requestCount=1,automaticRetries=0,DeepSeekCalls=0,
        fallbackCalls=0,renders=0)
    result['capability']=capability(raw) if raw else dict(status='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_FAILED',reason=result.get('errorClass','EMPTY_CONTENT'))
    write_new(path/'benchmark-record.json',result);return result


def analyze_stored(path):
    path=Path(path);record=json.loads((path/'benchmark-record.json').read_text())
    if record['capability']['status']!='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_PASS':
        return dict(status='NOT_RUN_NO_USABLE_PARSED_CORPUS',schemaValidCount=None,normalizedCount=None)
    from .semantic_concept_prompt_v2 import PromptV2Request
    cfg=PromptV2Request.model_validate(json.loads((path/'configuration.json').read_text())['generation'])
    result=analyze((path/'response.txt').read_text(),cfg,json.loads((path/'prompt.json').read_text()))
    out=path/'offline-analysis';out.mkdir(exist_ok=False)
    write_new(out/'results.json',result);write_new(out/'all-returned-concepts.txt',all_ideas_text(result),raw=True)
    write_new(out/'review-cards.json',review_cards(result))
    return dict(status='COMPLETED_CAPABILITY_EVIDENCE_ONLY',schemaValidCount=result['metrics']['schemaValidCount'],
        normalizedCount=result['metrics']['normalizedCount'],metrics=result['metrics'],statisticalComparison=False)
