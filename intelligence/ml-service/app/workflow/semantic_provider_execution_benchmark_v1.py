"""One5-item capability probe with body-byte observation, never SSE generation."""
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import time
import httpx

from .semantic_prompt_v2_experiment import configuration_for, analyze, all_ideas_text, review_cards
from .semantic_concept_prompt_v2 import prompt_v2
from .semantic_live_experiment import request_arguments, response_format, write_new
from .short_concept_generation import resolve_cast
from .concept_fingerprint import digest

ATTEMPT_ID='semantic-provider-execution-benchmark-v1-deepseek-5-run-001'
OUTPUT_TOKENS=16384
TIMEOUT=dict(connectSeconds=15,readSeconds=90,writeSeconds=60,poolSeconds=15,wallSeconds=180)


class BodyObserver:
    """Observe raw HTTP body chunks without asking the API/SDK for streaming."""
    def __init__(self,path,clock=time.monotonic):
        self.path=Path(path);self.clock=clock;self.start=clock()
        self.data=dict(firstByteMs=None,firstNonWhitespaceByteMs=None,responseHeadersMs=None,
            httpBodyBytesObserved=0,httpRequestsObserved=0,httpStatus=None,
            firstByteDefinition='First nonempty HTTP body chunk, possibly JSON/whitespace; NOT first model token.')
        self.save()
    def save(self):
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(self.data,indent=2)+'\n');temporary.replace(self.path)
    def on_request(self,request):
        self.data['httpRequestsObserved']+=1;self.save()
    def on_response(self,response):
        if self.data['responseHeadersMs'] is None:self.data['responseHeadersMs']=(self.clock()-self.start)*1000
        self.data['httpStatus']=response.status_code
        response.stream=ObservedStream(response.stream,self);self.save()
    def received(self,chunk):
        if not chunk:return
        now=(self.clock()-self.start)*1000
        if self.data['firstByteMs'] is None:self.data['firstByteMs']=now
        if chunk.strip() and self.data['firstNonWhitespaceByteMs'] is None:self.data['firstNonWhitespaceByteMs']=now
        self.data['httpBodyBytesObserved']+=len(chunk);self.save()


class ObservedStream(httpx.SyncByteStream):
    def __init__(self,stream,observer):self.stream=stream;self.observer=observer
    def __iter__(self):
        for chunk in self.stream:self.observer.received(chunk);yield chunk
    def close(self):self.stream.close()


def request_for(profile):
    cfg=configuration_for(profile);cfg.semanticRawCount=5;cfg.semanticProvider.maxOutputTokens=OUTPUT_TOKENS
    cast,_=resolve_cast(cfg);p=prompt_v2(cfg,cast,5);payload=json.loads(p['prompt']);payload['limits']['timeoutSeconds']=TIMEOUT['readSeconds']
    p['prompt']=json.dumps(payload,ensure_ascii=False,sort_keys=True);p['sha256']=digest([p['system'],payload])
    fmt=response_format();fmt['json_schema']['schema']['properties']['ideas'].update(minItems=5,maxItems=5)
    args=request_arguments(profile,cfg,p)
    if profile['responseMode']=='json_object':args['messages'][0]['content']=p['system']+'\nReturn JSON matching this schema; use catalog IDs exactly:\n'+json.dumps(fmt['json_schema']['schema'],separators=(',',':'))
    else:args['response_format']=fmt
    return cfg,p,args


def worker(path,profile,config,prompt):
    from .creative_provider_profiles import CreativeCapabilityProvider
    path=Path(path);observer=BodyObserver(path/'http-observation.json');provider=None;raw=''
    result=dict(status='FAILED',usage=None,providerCostUsd=None,providerRequestId=None,sdkMaxRetries=0)
    try:
        provider=CreativeCapabilityProvider(profile,OUTPUT_TOKENS,TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must be disabled')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        hooks=provider.client._client.event_hooks
        hooks['request'].append(observer.on_request);hooks['response'].append(observer.on_response)
        provider.response_format=response_format();provider.response_format['json_schema']['schema']['properties']['ideas'].update(minItems=5,maxItems=5)
        write_new(path/'sdk-call-started.json',dict(sdkMaxRetries=0,streamingMode='NON_STREAMING',requestOrdinal=1))
        raw=provider.complete(prompt['prompt'],system=prompt['system'],temperature=config['semanticProvider']['temperature'])
        result['status']='COMPLETED'
    except Exception as error:
        result.update(errorClass=type(error).__name__,errorCauseClass=type(error.__cause__).__name__ if error.__cause__ else None,
            httpStatus=getattr(error,'status_code',None),safeError='Bounded capability probe failed; no retry or fallback.')
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        result.update(usage=getattr(provider,'last_usage',None),providerResponseMetadata=getattr(provider,'last_response_metadata',None))
        result['providerRequestId']=(result['providerResponseMetadata'] or {}).get('requestId')
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
        safeError='Probe worker stopped; no retry or fallback.',usage=None,providerCostUsd=None,providerRequestId=None,sdkMaxRetries=0)


def execute(path,profile,*,authorization=None,tests=None,runner=None):
    if not authorization or not tests or not tests.get('noNewFailures'):raise ValueError('Authorization and completed tests required')
    if profile['provider']!='deepseek' or profile['model']!='deepseek-v4-pro':raise ValueError('Exact configured probe model required')
    if not os.getenv('DEEPSEEK_API_KEY'):raise ValueError('Credential unavailable')
    if profile['maxOutputTokens']<OUTPUT_TOKENS:raise ValueError('Insufficient configured output capacity')
    cfg,p,args=request_for(profile);path=Path(path);path.mkdir(parents=True,exist_ok=False)
    write_new(path/'plan.json',dict(attemptId=ATTEMPT_ID,provider='deepseek',model='deepseek-v4-pro',candidateCount=5,maxLiveRequests=1,
        timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS,streamingMode='NON_STREAMING',sdkMaxRetries=0,authorization=authorization,tests=tests))
    write_new(path/'configuration.json',dict(profile=profile,generation=cfg.model_dump()))
    write_new(path/'prompt.json',p);write_new(path/'request.json',dict(baseUrl=profile['baseUrl'],arguments=args,maxRetries=0,timeout=TIMEOUT))
    stamp=datetime.now(UTC).isoformat();start=time.monotonic()
    write_new(path/'request-started.json',dict(attemptId=ATTEMPT_ID,requestCount=1,startedAt=stamp))
    try:result=(runner or bounded)(path,profile,cfg.model_dump(),p)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,safeError='Probe runner failed; no replacement.',usage=None)
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    observed=json.loads((path/'http-observation.json').read_text()) if (path/'http-observation.json').exists() else {}
    result.update(attemptId=ATTEMPT_ID,provider=profile['provider'],model=profile['model'],promptVersion='v2',candidateCount=5,
        timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS,streamingMode='NON_STREAMING',start=stamp,end=datetime.now(UTC).isoformat(),
        durationSeconds=time.monotonic()-start,firstByteMs=observed.get('firstByteMs'),responseHeadersMs=observed.get('responseHeadersMs'),
        httpBodyBytesObserved=observed.get('httpBodyBytesObserved'),responseBytes=len((path/'response.txt').read_bytes()),
        requestCount=1,automaticRetries=0,fallbackCalls=0,renders=0)
    result['capabilityClassification']='RESPONSE_RETURNED_OFFLINE_VALIDATION_PENDING' if result['status']=='COMPLETED' and result['responseBytes'] else 'UNSUITABLE_FOR_CURRENT_SEMANTIC_V2_EXECUTION_ENVELOPE'
    write_new(path/'benchmark-record.json',result);return result


def analyze_probe(path):
    path=Path(path);record=json.loads((path/'benchmark-record.json').read_text())
    if record['status']!='COMPLETED' or not record['responseBytes']:return dict(status='NOT_RUN_NO_USABLE_RESPONSE',creativeQualityConclusion=None)
    from .semantic_concept_prompt_v2 import PromptV2Request
    cfg=PromptV2Request.model_validate(json.loads((path/'configuration.json').read_text())['generation'])
    result=analyze((path/'response.txt').read_text(),cfg,json.loads((path/'prompt.json').read_text()))
    out=path/'offline-analysis';out.mkdir(exist_ok=False)
    write_new(out/'results.json',result);write_new(out/'all-returned-stories.txt',all_ideas_text(result),raw=True)
    write_new(out/'review-cards.json',review_cards(result))
    return dict(status='COMPLETED_CAPABILITY_EVIDENCE_ONLY',rawCount=result['rawCount'],schemaValidCount=result['metrics']['schemaValidCount'],
        normalizedCount=result['metrics']['normalizedCount'],metrics=result['metrics'],comparisonTo40ConceptExperiments=False)


def discovery(profiles):
    from app.llm.provider import get_provider_identity
    def installed(name):
        try:return importlib.util.find_spec(name) is not None
        except (ImportError,ModuleNotFoundError,ValueError):return False
    configured=[]
    for identity,p in profiles['profiles'].items():
        configured.append(dict(identity=identity,provider=p['provider'],model=p['model'],
            structuredOutput=p['responseMode'],streaming='STREAMING_NOT_SUPPORTED',
            timeout='Caller-supplied SDK transport timeout; existing semantic experiment90s; no adapter total deadline.',
            credentialsPresent=bool(os.getenv(p['provider'].upper()+'_API_KEY')),SDKInstalled=installed('openai'),
            semanticIntegration='Existing CreativeCapabilityProvider supports the same schema envelope; external availability untested.',
            configuredOutputCeiling=p['maxOutputTokens'],alternative=p['provider']!='deepseek'))
    legacy=[]
    for name,key,sdk in [('openai','OPENAI_API_KEY','openai'),('claude','ANTHROPIC_API_KEY','anthropic'),('gemini','GOOGLE_API_KEY','google.generativeai'),('ollama',None,'requests')]:
        provider,model=get_provider_identity(name)
        legacy.append(dict(provider=provider,model=model,credentialsPresent=bool(os.getenv(key)) if key else None,
            SDKInstalled=installed(sdk),streaming='STREAMING_NOT_SUPPORTED',
            semanticIntegration='Generic text/image completion adapter; not a configured semantic schema profile.',
            structuredOutput='No semantic schema contract in this generic adapter',
            timeout=f"OPENAI_REQUEST_TIMEOUT_SECONDS={os.getenv('OPENAI_REQUEST_TIMEOUT_SECONDS','20')}" if name=='openai' else 'No explicit timeout in adapter; SDK default not overridden' if name in ('claude','gemini') else 'requests.post without explicit timeout; server availability unknown'))
    return dict(configuredSemanticProfiles=configured,genericFactoryAdapters=legacy,
        alternativeCalls=0,modelAvailabilityVerified=False,SDKsAdded=False,
        limitation='Presence of configuration/credentials/SDK is readiness evidence only, not a successful capability probe or model availability guarantee.')
