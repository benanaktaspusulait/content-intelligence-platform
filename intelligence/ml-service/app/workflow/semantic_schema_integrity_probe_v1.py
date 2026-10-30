"""Single minimal-prompt probe,only after final native schema integrity passes."""
from datetime import UTC, datetime
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback
import httpx
from jsonschema import Draft202012Validator

from .semantic_transport_isolation_v1 import TIMEOUT
from .semantic_live_experiment import write_new
from .semantic_native_schema_integrity_v1 import native_response_format,final_provider_schema_validation,semantic_equivalence_proof,native_compatibility_audit,LastMileSchemaGuard

EXPERIMENT_ID='semantic-native-schema-integrity-probe-1-run-001'
OUTPUT_TOKENS=8192


def timing_record(start_utc,end_utc,start_ns,end_ns,tolerance=1.0):
    elapsed=(end_ns-start_ns)/1_000_000_000
    wall=(end_utc-start_utc).total_seconds()
    return dict(wallClockStartUTC=start_utc.isoformat(),wallClockEndUTC=end_utc.isoformat(),
        monotonicElapsedSeconds=elapsed,wallClockSpanSeconds=wall,wallMinusMonotonicSeconds=wall-elapsed,
        recordingToleranceSeconds=tolerance,timingConsistent=abs(wall-elapsed)<=tolerance,
        timeoutClock='time.monotonic; UTC never controls deadlines. Inconsistent records are flagged,not rewritten.')


def plan(stored_e):
    if stored_e['timeout']!=TIMEOUT:raise ValueError('Comparable timeout envelope required')
    args=json.loads(json.dumps(stored_e['arguments']))
    if args['model']!='gpt-6.1-sol' or args['max_completion_tokens']!=OUTPUT_TOKENS:raise ValueError('Exact previous one-candidate envelope required')
    fmt=native_response_format(1);args['response_format']=fmt
    return dict(arguments=args,format=fmt,timeout=TIMEOUT,
        integrity=final_provider_schema_validation(fmt['json_schema']['schema']),
        equivalence=semantic_equivalence_proof(fmt['json_schema']['schema']),
        nativeCompatibility=native_compatibility_audit(fmt))


def worker(path,profile,spec):
    from .creative_provider_profiles import CreativeCapabilityProvider
    path=Path(path);provider=None;raw='';guard=None
    result=dict(status='FAILED',usage=None,providerRequestId=None,timeToHeadersMs=None,firstTokenMs=None,firstUsableContentMs=None)
    try:
        provider=CreativeCapabilityProvider(profile,OUTPUT_TOKENS,TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must remain disabled')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        provider.response_format=spec['format']
        def record_actual(kwargs,receipt):
            write_new(path/'last-mile-sdk-request.json',kwargs)
            write_new(path/'final-provider-schema-validation.json',receipt)
            write_new(path/'sdk-request-forwarded.json',dict(requestCount=1,SDKMaxRetries=0))
        guard=LastMileSchemaGuard(provider.client.chat.completions.create,spec['format'],record_actual)
        provider.client.chat.completions.create=guard
        write_new(path/'sdk-call-started.json',dict(provider='openai',model='gpt-6.1-sol',requestCount=1,SDKMaxRetries=0))
        start=time.monotonic();args=spec['arguments']
        system=next(m['content'] for m in args['messages'] if m['role']=='system');user=next(m['content'] for m in args['messages'] if m['role']=='user')
        raw=provider.complete(user,system=system,temperature=.7)
        result.update(status='COMPLETED',firstUsableContentMs=(time.monotonic()-start)*1000 if raw else None)
    except Exception as error:
        current=error;seen=set();chain=[]
        while current is not None and id(current) not in seen and len(chain)<8:
            seen.add(id(current));chain.append(dict(exceptionClass=type(current).__name__,httpStatus=getattr(current,'status_code',None),providerCode=getattr(current,'code',None)))
            current=current.__cause__ or current.__context__
        result.update(errorClass=type(error).__name__,exceptionChain=chain,safeMessage='Corrected schema probe failed; no retry or fallback.',
            safeTrace=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)])
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        metadata=getattr(provider,'last_response_metadata',None);usage=getattr(provider,'last_usage',None)
        result.update(usage=usage,providerMetadata=metadata,providerRequestId=(metadata or {}).get('requestId'),finishReason=(metadata or {}).get('finishReason'),
            requestIdMeaning='Existing adapter exposes completion response.id,not the HTTP x-request-id.',providerReportedCostUsd=(usage or {}).get('actual_cost_usd'),
            SDKRequestsForwarded=guard.forwarded if guard else 0)
        write_new(path/'response.txt',raw,raw=True);write_new(path/'worker-result.json',result)


def bounded(path,profile,spec):
    process=multiprocessing.get_context('spawn').Process(target=worker,args=(str(path),profile,spec))
    process.start();process.join(TIMEOUT['wallSeconds']);timeout=process.is_alive()
    if timeout:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
    p=Path(path)/'worker-result.json'
    if not timeout and p.exists():return json.loads(p.read_text())
    return dict(status='FAILED',errorClass='ExperimentWallTimeout' if timeout else 'WorkerExited',usage=None,
        safeMessage='Corrected probe worker stopped; no second request.')


def execute(path,profile,stored_e,*,authorization=None,tests=None,runner=None):
    if not authorization or not tests or not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):
        raise ValueError('Explicit authorization,completed tests and schema integrity proof required')
    if (profile['provider'],profile['model'],profile['responseMode'])!=('openai','gpt-6.1-sol','json_schema'):raise ValueError('Exact existing native OpenAI profile required')
    if profile.get('reasoningEffort')!=stored_e['arguments'].get('reasoning_effort') or profile.get('temperatureSupported'):
        raise ValueError('Do not change model parameters')
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('Credential unavailable')
    if profile['maxOutputTokens']<OUTPUT_TOKENS:raise ValueError('Configured output capacity insufficient')
    spec=plan(stored_e);path=Path(path);path.mkdir(parents=True,exist_ok=False)
    write_new(path/'plan.json',dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',candidateCount=1,
        promptMode='PREVIOUS_E_MINIMAL_DIAGNOSTIC_UNCHANGED',maximumLiveRequests=1,SDKRetries=0,timeout=TIMEOUT,
        maxOutputTokens=OUTPUT_TOKENS,streaming=False,authorization=authorization,tests=tests))
    write_new(path/'request-before-sdk.json',dict(provider='openai',baseUrl=profile['baseUrl'],arguments=spec['arguments'],timeout=TIMEOUT,maxRetries=0))
    write_new(path/'offline-schema-validation.json',dict(integrity=spec['integrity'],equivalence=spec['equivalence'],nativeCompatibility=spec['nativeCompatibility']))
    start_ns=time.monotonic_ns();start_utc=datetime.now(UTC)
    write_new(path/'request-started.json',dict(logicalRequestCount=1,wallClockStartUTC=start_utc.isoformat()))
    try:result=(runner or bounded)(path,profile,spec)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,safeMessage='Probe runner failed; no replacement.',usage=None)
    end_utc=datetime.now(UTC);end_ns=time.monotonic_ns()
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    raw=(path/'response.txt').read_text();valid=False;check=dict(status='NO_USABLE_COMPLETED_RESPONSE')
    if result['status']=='COMPLETED' and raw:
        try:
            def unique(pairs):
                data={}
                for key,value in pairs:
                    if key in data:raise ValueError('Duplicate JSON key')
                    data[key]=value
                return data
            data=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            errors=list(Draft202012Validator(spec['format']['json_schema']['schema']).iter_errors(data))
            valid=not errors;check=dict(status='VALID_CORRECTED_FULL_SCHEMA' if valid else 'INVALID_CORRECTED_FULL_SCHEMA',
                errors=[dict(path=list(e.path),validator=e.validator) for e in errors])
        except (ValueError,TypeError):check=dict(status='MALFORMED_RESPONSE')
    result.update(primaryClassification='FULL_SCHEMA_EXECUTION_CONFIRMED_AFTER_SCHEMA_REPAIR' if valid else 'FULL_SCHEMA_EXECUTION_STILL_UNRESOLVED',
        timing=timing_record(start_utc,end_utc,start_ns,end_ns),responseBytes=len(raw.encode()),schemaCheck=check,
        requestCount=1,maximumLiveRequests=1,retries=0,DeepSeekCalls=0,fallbacks=0,creativePipelineCalls=0,renders=0,
        timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS,
        causalityLimit='This result tests the corrected schema in isolation. It cannot prove the broken reference caused all prior failures.')
    write_new(path/'result.json',result);return result
