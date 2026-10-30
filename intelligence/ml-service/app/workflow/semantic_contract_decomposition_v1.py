"""Two diagnostic cross-cases only. Never run creative judges on their content."""
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
import json
import multiprocessing
import os
from pathlib import Path
import re
import time
import traceback
import httpx
from jsonschema import Draft202012Validator
from referencing.exceptions import Unresolvable

from .concept_fingerprint import digest
from .semantic_transport_isolation_v1 import request_metrics, TIMEOUT
from .semantic_live_experiment import write_new

EXPERIMENT_ID='semantic-provider-contract-decomposition-v1-run-001'
OUTPUT_LIMITS={'D':4096,'E':8192}
SMALL_FIELDS=['title','everydayGoal','primaryObject','impossibleRule','frameZeroDescription','finalPayoff']


def structural_metrics(system,schema):
    lines=system.splitlines()
    headings=[dict(line=i+1,text=line) for i,line in enumerate(lines) if line and line.upper()==line and re.search('[A-Z]',line) and not line.startswith('Return ')]
    keywords={name:len(re.findall(pattern,system,re.I)) for name,pattern in dict(must=r'\bmust\b',doNot=r'\bdo not\b',never=r'\bnever\b',avoid=r'\bavoid\b',exactly=r'\bexactly\b',discard=r'\bdiscard\b').items()}
    themes=dict(ruleConsistency=r'\brule\b|\btrigger\b',frameZero=r'frame.zero|paused|opening still|STILL',payoff=r'payoff|ending',nonScoring=r'\bscore|winner|eligibility',privateChecks=r'check|discard|redesign')
    clusters={key:[dict(line=i+1,text=line) for i,line in enumerate(lines) if re.search(pattern,line,re.I)] for key,pattern in themes.items()}
    sentences=[re.sub(r'\s+',' ',s).strip().casefold() for s in re.split(r'(?<=[.!?])\s+',system) if len(s.strip())>=35]
    enums=[];descriptions=[];constraints=Counter();refs=[]
    def visit(value,path=''):
        if isinstance(value,dict):
            if 'enum' in value:enums.append(dict(path=path,values=value['enum']))
            if isinstance(value.get('description'),str):descriptions.append(value['description'])
            if '$ref' in value:refs.append(dict(path=path,reference=value['$ref']))
            for key,item in value.items():
                if key in ('minLength','maxLength','minItems','maxItems','pattern','additionalProperties'):constraints[key]+=1
                visit(item,path+'/'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value):visit(item,path+'/'+str(i))
    visit(schema)
    fmt={'model':'gpt-6.1-sol','messages':[],'response_format':{'type':'json_schema','json_schema':{'schema':schema}}}
    metrics=request_metrics(fmt)
    unresolved=[]
    for ref in refs:
        if ref['reference'].startswith('#/'):
            current=schema
            for part in ref['reference'][2:].split('/'):
                part=part.replace('~1','/').replace('~0','~')
                if not isinstance(current,dict) or part not in current:
                    unresolved.append(dict(**ref,missingRootPointerSegment=part));break
                current=current[part]
    return dict(prompt=dict(characters=len(system),lines=len(lines),sectionCount=len(headings),sections=headings,keywordCounts=keywords,
        explicitMustDoNotOccurrences=keywords['must']+keywords['doNot'],localTokenEstimate=None,
        exactDuplicateSentences=[dict(text=text,count=count) for text,count in Counter(sentences).items() if count>1],
        repeatedInstructionThemes=clusters,limitation='Keyword/theme overlap is a deterministic heuristic,not proof of redundant or unnecessary instructions. No prompt edits.'),
        schema=dict(characters=metrics['schemaCharacters'],topLevelProperties=len(schema.get('properties',{})),
            nestedDeclaredProperties=metrics['declaredProperties']-len(schema.get('properties',{})),requiredByPath=metrics['requiredByPath'],
            requiredFieldOccurrences=sum(len(v['fields']) for v in metrics['requiredByPath']),arrays=metrics['arraySchemas'],
            maximumSchemaJSONNestingDepth=metrics['schemaJSONNestingDepth'],enumCount=len(enums),enumValues=enums,
            descriptionTextCharacters=sum(map(len,descriptions)),referenceSites=refs,unresolvedLocalReferences=unresolved,constraintCounts=dict(constraints),
            potentialProcessingStructures='ideas array→candidate object→beats array(4–5 objects),$defs/$ref,required scalar fields and bounded strings. These are structural observations,not proven latency causes.'))


def plan(stored_c):
    full=stored_c['arguments']['response_format'];messages=stored_c['arguments']['messages']
    system=next(m['content'] for m in messages if m['role']=='system');user=next(m['content'] for m in messages if m['role']=='user')
    small=dict(type='json_schema',json_schema=dict(name='contract_decomposition_small',strict=False,schema=dict(type='object',
        properties={k:dict(type='string') for k in SMALL_FIELDS},required=SMALL_FIELDS,additionalProperties=False)))
    specs={}
    for level in ['D','E']:
        args=deepcopy(stored_c['arguments']);args['max_completion_tokens']=OUTPUT_LIMITS[level]
        args['messages']=deepcopy(messages) if level=='D' else [dict(role='system',content='Return JSON only.'),dict(role='user',content='Generate one fictional short-video concept matching the supplied response schema. Keep every field concise.')]
        args['response_format']=small if level=='D' else deepcopy(full)
        metrics=request_metrics(args);metrics['requiredFieldOccurrences']=sum(len(r['fields']) for r in metrics['requiredByPath'])
        schema=args['response_format']['json_schema']['schema']
        specs[level]=dict(level=level,arguments=args,metrics=metrics,timeout=deepcopy(stored_c['timeout']),
            system=args['messages'][0]['content'],prompt=args['messages'][1]['content'],format=args['response_format'],
            promptTextHash=digest(args['messages']),systemTextHash=digest(args['messages'][0]['content']),
            schemaHash=digest(schema),formatHash=digest(args['response_format']),
            purpose='Full exact C prompt with6-field flat native diagnostic schema; deliberately conflicting contracts.' if level=='D' else 'Minimal diagnostic prompt with full exact C native response schema.',
            constraint='D preserves embedded candidateSchema and declared output8192 prompt metadata exactly; actual SDK output bound4096 is recorded separately.' if level=='D' else 'No Prompt V2 creative instructions included.')
    return specs,structural_metrics(system,full['json_schema']['schema'])


def worker(path,profile,spec):
    from .creative_provider_profiles import CreativeCapabilityProvider
    path=Path(path);provider=None;raw='';result=dict(status='FAILED',usage=None,providerRequestId=None,timeToHeadersMs=None,firstTokenMs=None,firstUsableContentMs=None)
    try:
        provider=CreativeCapabilityProvider(profile,OUTPUT_LIMITS[spec['level']],TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must remain disabled')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        provider.response_format=spec['format']
        write_new(path/'sdk-call-started.json',dict(level=spec['level'],SDKMaxRetries=0,provider='openai',model='gpt-6.1-sol'))
        start=time.monotonic();raw=provider.complete(spec['prompt'],system=spec['system'],temperature=.7)
        result.update(status='COMPLETED',firstUsableContentMs=(time.monotonic()-start)*1000 if raw else None)
    except Exception as error:
        chain=[];current=error;seen=set()
        while current is not None and id(current) not in seen and len(chain)<8:
            seen.add(id(current));chain.append(dict(exceptionClass=type(current).__name__,httpStatus=getattr(current,'status_code',None),providerCode=getattr(current,'code',None),providerParam=getattr(current,'param',None)))
            current=current.__cause__ or current.__context__
        response=getattr(error,'response',None);headers=getattr(response,'headers',{})
        result.update(errorClass=type(error).__name__,exceptionChain=chain,safeMessage='Diagnostic cross-case failed; no retry or fallback.',
            httpStatus=getattr(error,'status_code',None),safeHeaders={k:headers[k] for k in ['x-request-id','retry-after','content-type'] if k in headers},
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
        exceptionChain=[dict(exceptionClass='ExperimentWallTimeout' if timeout else 'WorkerExited')],safeMessage='Bounded worker stopped; next planned cross-case is independent.')


def check(raw,schema):
    try:
        def unique(pairs):
            value={}
            for key,item in pairs:
                if key in value:raise ValueError('Duplicate JSON key')
                value[key]=item
            return value
        value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        try:errors=list(Draft202012Validator(schema).iter_errors(value))
        except Unresolvable as error:
            return dict(passed=None,parseable=True,validationStage='JSON_SCHEMA_ONLY_NO_CREATIVE_ASSESSORS',
                reason='UNCHANGED_SCHEMA_REFERENCE_UNRESOLVABLE',errorClass=type(error).__name__,
                causeClass=type(error.__cause__).__name__ if error.__cause__ else None,
                limitation='Raw response execution can succeed while formal schema validity remains unestablished. Schema is not repaired.')
        return dict(passed=not errors,parseable=True,validationStage='JSON_SCHEMA_ONLY_NO_CREATIVE_ASSESSORS',
            schemaErrors=[dict(path=list(e.path),validator=e.validator) for e in errors])
    except (ValueError,TypeError):return dict(passed=False,parseable=False,reason='EMPTY_OR_MALFORMED_JSON')


def classification(d,e):
    if type(d) is not bool or type(e) is not bool:return 'UNRESOLVED_CONTRACT_FAILURE'
    return {(False,True):'PROMPT_COMPLEXITY_FAILURE',(True,False):'SCHEMA_COMPLEXITY_FAILURE',
        (False,False):'PROMPT_AND_SCHEMA_COMPLEXITY_FAILURE',(True,True):'PROMPT_SCHEMA_INTERACTION_FAILURE'}[(d,e)]


def execute(path,profile,stored_c,*,authorization=None,tests=None,runner=None):
    if not authorization or not tests or not tests.get('noNewFailures'):raise ValueError('Authorization and completed tests required')
    if (profile['provider'],profile['model'],profile['responseMode'])!=('openai','gpt-6.1-sol','json_schema'):raise ValueError('Exact existing OpenAI profile required')
    if profile.get('reasoningEffort')!=stored_c['arguments'].get('reasoning_effort') or profile.get('temperatureSupported'):
        raise ValueError('Do not change the stored C model parameters')
    if stored_c['timeout']!=TIMEOUT:raise ValueError('Do not change stored C timeout strategy')
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('Credential unavailable')
    if profile['maxOutputTokens']<max(OUTPUT_LIMITS.values()):raise ValueError('Configured capacity insufficient')
    specs,structure=plan(stored_c);path=Path(path);path.mkdir(parents=True,exist_ok=False)
    write_new(path/'stored-c-request.json',stored_c);write_new(path/'structural-metrics.json',structure)
    write_new(path/'plan.json',dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',maximumRequests=2,
        levels=['D','E'],executeBothEvenIfDFails=True,SDKRetries=0,authorization=authorization,tests=tests,
        timeout=TIMEOUT,outputLimits=OUTPUT_LIMITS,confound='Exact full D user payload includes full candidateSchema; only native response schema is reduced. D is also a deliberate instruction/schema mismatch.'))
    write_new(path/'profile.json',profile)
    for level,spec in specs.items():
        directory=path/('probe-'+level.lower());directory.mkdir()
        write_new(directory/'request.json',dict(provider='openai',baseUrl=profile['baseUrl'],arguments=spec['arguments'],timeout=TIMEOUT,maxRetries=0))
        write_new(directory/'specification.json',spec)
    results={};runner=runner or bounded
    for level in ['D','E']:
        directory=path/('probe-'+level.lower());spec=specs[level];start=time.monotonic();stamp=datetime.now(UTC).isoformat()
        write_new(directory/'request-started.json',dict(level=level,requestOrdinal=len(results)+1,maximumRequests=2,start=stamp))
        try:r=runner(directory,profile,spec)
        except Exception as error:r=dict(status='FAILED',errorClass=type(error).__name__,safeMessage='Cross-case runner failed; no replacement.',usage=None)
        if not (directory/'response.txt').exists():write_new(directory/'response.txt','',raw=True)
        raw=(directory/'response.txt').read_text();validation=check(raw,spec['format']['json_schema']['schema']) if r['status']=='COMPLETED' else dict(passed=False,reason=r.get('errorClass','SDK_FAILURE'))
        r.update(level=level,start=stamp,end=datetime.now(UTC).isoformat(),durationSeconds=time.monotonic()-start,responseBytes=len(raw.encode()),
            passed=validation['passed'],executionPassed=r['status']=='COMPLETED' and bool(raw) and validation.get('parseable') is True,
            contractCheck=validation,timeout=TIMEOUT,maxOutputTokens=OUTPUT_LIMITS[level])
        write_new(directory/'result.json',r);results[level]=r;print(json.dumps(dict(level=level,passed=r['passed'],durationSeconds=r['durationSeconds'])),flush=True)
    summary=dict(primaryClassification=classification(results['D']['passed'],results['E']['passed']),results=results,
        requestCount=2,maximumRequests=2,SDKRetries=0,DeepSeekCalls=0,fallbacks=0,creativePipelineCalls=0,HUMAN_REVIEW_SET_CREATED=False,renders=0,
        caveats=['D retains full schema text in the user prompt; it reduces native structured schema only.','D deliberate prompt/schema mismatch and smaller output bound are confounds.','One observation per cross-case does not identify a unique root cause.'])
    write_new(path/'summary.json',summary);return summary
