"""Three preplanned diagnostic levels; stop at first failure, never repair/retry."""
from datetime import UTC, datetime
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback
import httpx

from .semantic_provider_openai_probe_v1 import TIMEOUT
from .semantic_prompt_v2_experiment import configuration_for, analyze, all_ideas_text
from .semantic_concept_prompt_v2 import prompt_v2
from .semantic_live_experiment import response_format, write_new
from .semantic_concept_provider import parse_response
from .short_concept_generation import resolve_cast

EXPERIMENT_ID='semantic-provider-transport-isolation-v1-run-001'
OUTPUT_LIMITS={'A':512,'B':1024,'C':8192}


def schema_metrics(schema):
    properties=0;arrays=0;required=[]
    def visit(value,path='',depth=0):
        nonlocal properties,arrays
        maximum=depth
        if isinstance(value,dict):
            properties+=len(value.get('properties',{}));arrays+=value.get('type')=='array'
            if 'required' in value:required.append(dict(path=path or '/',fields=value['required']))
            for key,item in value.items():maximum=max(maximum,visit(item,path+'/'+key,depth+1))
        elif isinstance(value,list):
            for i,item in enumerate(value):maximum=max(maximum,visit(item,path+'/'+str(i),depth+1))
        return maximum
    depth=visit(schema) if schema else 0
    return dict(declaredProperties=properties,arraySchemas=arrays,schemaJSONNestingDepth=depth,requiredByPath=required,
        depthDefinition='JSON schema-document nesting,not resolved data depth; $defs counted once,not expanded per reference.')


def request_metrics(args):
    system=sum(len(m['content']) for m in args['messages'] if m['role']=='system')
    user=sum(len(m['content']) for m in args['messages'] if m['role']=='user')
    fmt=args.get('response_format',{});schema=fmt.get('json_schema',{}).get('schema')
    compact=lambda value:json.dumps(value,ensure_ascii=False,separators=(',',':'))
    return dict(systemCharacters=system,userCharacters=user,totalRequestTextCharacters=system+user,
        schemaCharacters=len(compact(schema)) if schema else 0,serializedRequestCharacters=len(compact(args)),
        serializedRequestUTF8Bytes=len(compact(args).encode()),maxOutputTokens=args.get('max_completion_tokens'),
        mode=fmt.get('type'),strict=fmt.get('json_schema',{}).get('strict'),
        localTokenEstimate=None,tokenEstimateReason='No installed tokenizer/local token-count utility; no external counting call or download.',
        **schema_metrics(schema))


def plan(profile):
    cfg=configuration_for(profile);cfg.semanticRawCount=1;cfg.semanticProvider.maxOutputTokens=OUTPUT_LIMITS['C']
    cast,_=resolve_cast(cfg);full=prompt_v2(cfg,cast,1);fmt=response_format()
    fmt['json_schema']['schema']['properties']['ideas'].update(minItems=1,maxItems=1)
    tiny=dict(type='json_schema',json_schema=dict(name='transport_isolation_small',strict=False,
        schema=dict(type='object',properties={k:dict(type='string') for k in ['title','goal','object']},required=['title','goal','object'],additionalProperties=False)))
    specs={
        'A':dict(system='Return JSON only.',prompt='Return exactly this JSON object and nothing else: {"status":"ok"}',format={'type':'text'}),
        'B':dict(system='Return one JSON object matching the supplied schema.',prompt='Give one short fictional everyday example using title, goal and object.',format=tiny),
        'C':dict(system=full['system'],prompt=full['prompt'],format=fmt)}
    result={}
    for level,spec in specs.items():
        args=dict(model=profile['model'],messages=[dict(role='system',content=spec['system']),dict(role='user',content=spec['prompt'])],
            response_format=spec['format'],**{profile['tokenParameter']:OUTPUT_LIMITS[level]})
        if profile.get('reasoningEffort'):args['reasoning_effort']=profile['reasoningEffort']
        if profile.get('temperatureSupported'):args['temperature']=cfg.semanticProvider.temperature
        result[level]=dict(level=level,system=spec['system'],prompt=spec['prompt'],format=spec['format'],arguments=args,
            configuration=cfg.model_dump(),fullV2Prompt=full if level=='C' else None,metrics=request_metrics(args),
            executionMode='NATIVE_STRUCTURED_OUTPUT' if level!='A' else 'TEXT_JSON',timeout=TIMEOUT)
    return result


def worker(path,profile,spec):
    from .creative_provider_profiles import CreativeCapabilityProvider
    path=Path(path);provider=None;raw='';result=dict(status='FAILED',usage=None,providerRequestId=None,
        timeToHeadersMs=None,firstTokenMs=None,firstUsableContentMs=None)
    try:
        provider=CreativeCapabilityProvider(profile,OUTPUT_LIMITS[spec['level']],TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must remain disabled')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        provider.response_format=spec['format']
        write_new(path/'sdk-call-started.json',dict(level=spec['level'],SDKMaxRetries=0,provider='openai',model='gpt-6.1-sol'))
        start=time.monotonic();raw=provider.complete(spec['prompt'],system=spec['system'],temperature=spec['configuration']['semanticProvider']['temperature'])
        result.update(status='COMPLETED',firstUsableContentMs=(time.monotonic()-start)*1000 if raw else None)
    except Exception as error:
        chain=[];current=error;seen=set()
        while current is not None and id(current) not in seen and len(chain)<8:
            seen.add(id(current));chain.append(dict(exceptionClass=type(current).__name__,httpStatus=getattr(current,'status_code',None),
                providerCode=getattr(current,'code',None),providerParam=getattr(current,'param',None)))
            current=current.__cause__ or current.__context__
        response=getattr(error,'response',None);headers=getattr(response,'headers',{})
        result.update(errorClass=type(error).__name__,exceptionChain=chain,
            safeMessage='Diagnostic request failed in existing SDK path; no retry or fallback.',httpStatus=getattr(error,'status_code',None),
            safeHeaders={k:headers[k] for k in ['x-request-id','retry-after','content-type'] if k in headers},
            safeTrace=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)])
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        metadata=getattr(provider,'last_response_metadata',None);usage=getattr(provider,'last_usage',None)
        result.update(usage=usage,providerMetadata=metadata,providerRequestId=(metadata or {}).get('requestId'),
            requestIdMeaning='Existing adapter exposes completion response.id; HTTP x-request-id only if captured on error.',
            finishReason=(metadata or {}).get('finishReason'),providerReportedCostUsd=(usage or {}).get('actual_cost_usd'))
        write_new(path/'response.txt',raw,raw=True);write_new(path/'worker-result.json',result)


def bounded(path,profile,spec):
    process=multiprocessing.get_context('spawn').Process(target=worker,args=(str(path),profile,spec))
    process.start();process.join(TIMEOUT['wallSeconds']);timeout=process.is_alive()
    if timeout:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
    output=Path(path)/'worker-result.json'
    if not timeout and output.exists():return json.loads(output.read_text())
    return dict(status='FAILED',errorClass='ExperimentWallTimeout' if timeout else 'WorkerExited',usage=None,
        exceptionChain=[dict(exceptionClass='ExperimentWallTimeout' if timeout else 'WorkerExited')],safeMessage='Bounded worker stopped; no replacement.')


def validate(level,raw):
    try:
        if level=='C':
            ideas,rejected=parse_response(raw,60)
            return dict(passed=len(ideas)==1 and not rejected,reason='FULL_V2_SCHEMA_CHECK',schemaValidCount=len(ideas),schemaRejectedCount=len(rejected))
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('Duplicate key')
                result[key]=value
            return result
        value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        ok=value=={'status':'ok'} if level=='A' else isinstance(value,dict) and set(value)=={'title','goal','object'} and all(isinstance(v,str) for v in value.values())
        return dict(passed=ok,reason='EXPECTED_TINY_OBJECT' if ok else 'UNEXPECTED_DIAGNOSTIC_OBJECT')
    except (ValueError,TypeError):return dict(passed=False,reason='EMPTY_OR_MALFORMED_JSON')


def classification(results):
    for level,label in [('A','FAILURE_BELOW_MODEL_RESPONSE'),('B','STRUCTURED_OUTPUT_PATH_FAILURE'),('C','FULL_V2_CONTRACT_FAILURE')]:
        if level not in results:return 'UNRESOLVED'
        if not results[level]['passed']:return label
    return 'BATCH_SIZE_OR_OUTPUT_SCALE_FAILURE'


def execute(path,profile,*,authorization=None,tests=None,runner=None):
    if not authorization or not tests or not tests.get('noNewFailures'):raise ValueError('Authorization and completed tests required')
    if (profile['provider'],profile['model'],profile['responseMode'])!=('openai','gpt-6.1-sol','json_schema'):raise ValueError('Exact existing OpenAI profile required')
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('Credential unavailable')
    if profile['maxOutputTokens']<max(OUTPUT_LIMITS.values()):raise ValueError('Configured capacity insufficient')
    specs=plan(profile);path=Path(path);path.mkdir(parents=True,exist_ok=False)
    write_new(path/'plan.json',dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',maximumRequests=3,SDKRetries=0,
        levels=['A','B','C'],stopAtFirstFailure=True,authorization=authorization,tests=tests,timeout=TIMEOUT,outputLimits=OUTPUT_LIMITS))
    write_new(path/'profile.json',profile)
    for level,spec in specs.items():
        directory=path/('probe-'+level.lower());directory.mkdir()
        write_new(directory/'request.json',dict(provider='openai',baseUrl=profile['baseUrl'],arguments=spec['arguments'],timeout=TIMEOUT,maxRetries=0))
        write_new(directory/'metrics-before-execution.json',spec['metrics']);write_new(directory/'specification.json',spec)
    results={};runner=runner or bounded
    for level in ['A','B','C']:
        directory=path/('probe-'+level.lower());spec=specs[level];start=time.monotonic();stamp=datetime.now(UTC).isoformat()
        write_new(directory/'request-started.json',dict(level=level,requestOrdinal=len(results)+1,maxRequests=3,start=stamp))
        try:r=runner(directory,profile,spec)
        except Exception as error:r=dict(status='FAILED',errorClass=type(error).__name__,safeMessage='Diagnostic runner failed; stop ladder.',usage=None)
        if not (directory/'response.txt').exists():write_new(directory/'response.txt','',raw=True)
        raw=(directory/'response.txt').read_text();check=validate(level,raw) if r['status']=='COMPLETED' else dict(passed=False,reason=r.get('errorClass','SDK_FAILURE'))
        r.update(level=level,start=stamp,end=datetime.now(UTC).isoformat(),durationSeconds=time.monotonic()-start,
            responseBytes=len(raw.encode()),parsedResult=check,passed=bool(check['passed']),timeout=TIMEOUT,maxOutputTokens=OUTPUT_LIMITS[level])
        write_new(directory/'result.json',r);results[level]=r;print(json.dumps(dict(level=level,passed=r['passed'],durationSeconds=r['durationSeconds'])),flush=True)
        if not r['passed']:break
    for level in ['A','B','C']:
        if level not in results:write_new(path/('probe-'+level.lower())/'not-executed.json',dict(status='NOT_EXECUTED',reason='Stopped at earlier failed diagnostic',liveRequests=0))
    summary=dict(primaryClassification=classification(results),requestCount=len(results),maximumRequests=3,
        results=results,DeepSeekCalls=0,retries=0,fallbacks=0,renders=0,productionPrompts=0,
        limitation='First failing level is isolated,not its unique root cause. All-pass scale label is a hypothesis from stored5 failure,not proof of causality.')
    write_new(path/'summary.json',summary);return summary


def validate_c_offline(path):
    path=Path(path);summary=json.loads((path/'summary.json').read_text())
    if not summary['results'].get('C',{}).get('passed'):return dict(status='NOT_RUN_C_NOT_PASSED',providerCalls=0)
    spec=json.loads((path/'probe-c/specification.json').read_text())
    from .semantic_concept_prompt_v2 import PromptV2Request
    cfg=PromptV2Request.model_validate(spec['configuration'])
    result=analyze((path/'probe-c/response.txt').read_text(),cfg,spec['fullV2Prompt'])
    out=path/'probe-c/offline-analysis';out.mkdir(exist_ok=False)
    write_new(out/'results.json',result);write_new(out/'one-candidate.txt',all_ideas_text(result),raw=True)
    return dict(status='COMPLETED_SECONDARY_DIAGNOSTIC',metrics=result['metrics'],creativeConclusion=None,providerCalls=0)
