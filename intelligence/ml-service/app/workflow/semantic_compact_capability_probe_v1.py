"""One compact/full-schema capability request; additive experiment, never a judge."""
from copy import deepcopy
from datetime import UTC, datetime
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback

import httpx
from jsonschema import Draft202012Validator
from .concept_fingerprint import digest
from .semantic_concept_prompt_v2_compact import CompactPromptRequest, construct_native_request, size_metrics
from .semantic_native_schema_integrity_v1 import LastMileSchemaGuard
from .semantic_schema_integrity_probe_v1 import timing_record, OUTPUT_TOKENS
from .semantic_transport_isolation_v1 import TIMEOUT, request_metrics
from .semantic_concept_provider import parse_response
from .semantic_concept_adapter import normalize_idea
from .short_concept_generation import resolve_cast
from .evidence_supported_admission_v2 import coherence_findings
from .semantic_prompt_v2_experiment import analyze, all_ideas_text
from .semantic_live_experiment import write_new

EXPERIMENT_ID='semantic-compact-full-contract-probe-1-run-001'
PROMPT_HASH='94f61976840e76e44ec6e2f15c51c360592e4adf9cc0c10d31507f1a4694eecb'
SCHEMA_HASH='91b6a9023b8d7a952ad380b494a4fa91d6f94f58c03a9fe0a979f894f7470ce3'


def plan(profile):
    if (profile['provider'],profile['model'],profile['responseMode'],profile['tokenParameter'],profile.get('reasoningEffort'),profile.get('temperatureSupported'))!=('openai','gpt-6.1-sol','json_schema','max_completion_tokens','high',False):
        raise ValueError('Exact accepted OpenAI profile required; no fallback or parameter change')
    if profile['maxOutputTokens']<OUTPUT_TOKENS:raise ValueError('Insufficient configured output capacity')
    cfg=CompactPromptRequest(generatorMode='semantic',seed=42,count=20,semanticRawCount=1,
        semanticProvider=dict(provider='openai',model='gpt-6.1-sol',maxCandidates=60,maxOutputTokens=OUTPUT_TOKENS,timeoutSeconds=90),allowExternalGeneration=False)
    cast,_=resolve_cast(cfg);request=construct_native_request(cfg,cast,1,profile)
    if request['prompt']['sha256']!=PROMPT_HASH:raise ValueError('Accepted compact prompt identity changed')
    if request['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']!=SCHEMA_HASH:raise ValueError('Accepted corrected schema identity changed')
    return dict(**request,configuration=cfg.model_dump(),cast=cast,timeout=deepcopy(TIMEOUT),maxOutputTokens=OUTPUT_TOKENS,
        streamingMode='NON_STREAMING',maximumLiveRequests=1,SDKMaxRetries=0,retries=0,fallbacks=0,DeepSeekCalls=0,renders=0,
        metrics=request_metrics(request['arguments']),systemSize=size_metrics(request['prompt']['system']))


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
            write_new(path/'sdk-request-forwarded.json',dict(SDKRequests=1,SDKMaxRetries=0,requestSha256=digest(kwargs),promptHash=PROMPT_HASH,schemaHash=SCHEMA_HASH))
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


def parse_exact(raw):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('Duplicate JSON key')
            value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def pre_pipeline_contract(data):
    """Read-only source/shape observations, not new scoring or admission gates."""
    item=data.get('ideas',[None])[0] if isinstance(data,dict) and isinstance(data.get('ideas'),list) and data['ideas'] else None
    if not isinstance(item,dict):return dict(stage='BEFORE_FULL_PIPELINE',sourceCandidatePresent=False,structuralContractPassed=False)
    beats=item.get('beats',[]);beats=beats if isinstance(beats,list) else []
    findings=coherence_findings(item) if isinstance(item.get('impossibleRule'),str) and all(isinstance(b,dict) and all(isinstance(b.get(k),str) for k in ('strategy','visibleConsequence','newInformation')) for b in beats) else []
    duration=item.get('durationSeconds',15)
    duration_ok=type(duration) in (int,float) and 10<=duration<=20
    text=lambda k:isinstance(item.get(k),str) and bool(item[k].strip())
    return dict(stage='BEFORE_FULL_PIPELINE',sourceCandidatePresent=True,
        declaredProtagonistFields=1 if text('protagonistSuggestion') else 0,declaredPrimaryObjectFields=1 if text('primaryObject') else 0,
        depictedProtagonistCount=None,depictedPrimaryObjectCount=None,countLimitation='Scalar fields do not prove depicted actor/object counts; normalization checks canonical named actors, not every implied entity.',
        everydayGoalPresent=text('everydayGoal'),frameZeroDescriptionPresent=text('frameZeroDescription'),impossibleRulePresent=text('impossibleRule'),visibleTriggerPresent=text('visibleTrigger'),
        payoffPresent=text('finalPayoff'),beatCount=len(beats),beatCountPassed=len(beats) in (4,5),
        eachBeat=[dict(number=i+1,strategyPresent=isinstance(b,dict) and bool(b.get('strategy')),visibleConsequencePresent=isinstance(b,dict) and bool(b.get('visibleConsequence')),newInformationPresent=isinstance(b,dict) and bool(b.get('newInformation')),
            source=b,ruleConsistency='RULE_INCONSISTENT' if any(f.get('beatNumber')==i+1 for f in findings) else 'AMBIGUOUS',
            findings=[f for f in findings if f.get('beatNumber')==i+1]) for i,b in enumerate(beats)],
        ruleConsistency='RULE_INCONSISTENT' if findings else 'AMBIGUOUS',ruleFindings=findings,
        ruleConsistencyLimitation='Existing source-constraint comparison can find explicit violations; no finding is not full semantic proof. Final source-supported status is reported with pipeline evidence.',
        duration=dict(supplied='durationSeconds' in item,declared=item.get('durationSeconds'),effectiveLocalDefault=duration,rangePassed=duration_ok,target=15,maximum=20,renderMeasured=False),
        finalPayoffEqualsLastConsequence=bool(beats and isinstance(beats[-1],dict) and item.get('finalPayoff')==beats[-1].get('visibleConsequence')),
        structuralContractPassed=len(beats) in (4,5) and duration_ok and all(text(k) for k in ('everydayGoal','frameZeroDescription','impossibleRule','visibleTrigger','finalPayoff')))


def inspect_response(raw,spec,*,analysis=analyze):
    out=dict(executionClassification='COMPACT_FULL_CONTRACT_PARSE_FAILURE',nativeSchemaValid=False,normalization=False,creativeContractClassification='CREATIVE_CONTRACT_FAILURE',pipelineRan=False)
    try:data=parse_exact(raw)
    except (ValueError,TypeError):return out
    out['parsed']=True;out['prePipelineContract']=pre_pipeline_contract(data)
    errors=list(Draft202012Validator(spec['arguments']['response_format']['json_schema']['schema']).iter_errors(data))
    out['nativeSchemaValid']=not errors;out['nativeSchemaErrors']=[dict(path=list(e.path),validator=e.validator) for e in errors]
    if errors:
        out['executionClassification']='COMPACT_FULL_CONTRACT_SCHEMA_FAILURE';return out
    ideas,rejected=parse_response(raw,60);out['domainRejections']=rejected
    if len(ideas)!=1:
        out['executionClassification']='COMPACT_FULL_CONTRACT_SCHEMA_FAILURE';return out
    cfg=CompactPromptRequest.model_validate(spec['configuration'])
    try:normalize_idea(ideas[0],cfg,spec['cast'],spec['prompt'])
    except ValueError as error:
        out.update(executionClassification='UNRESOLVED',normalizationError=str(error));return out
    out.update(executionClassification='COMPACT_FULL_CONTRACT_EXECUTION_PASS',normalization=True)
    # The complete preflight receipt is persisted by execute before this full analysis.
    result=analysis(raw,cfg,spec['prompt']);out['pipeline']=result;out['pipelineRan']=True
    record=result['allRawIdeas'][0]['record']
    if record is None:
        out.update(executionClassification='UNRESOLVED',pipelineError='No normalized pipeline record');return out
    o=record['observation'];pre=out['prePipelineContract'];findings=pre['ruleFindings']
    rule='RULE_INCONSISTENT' if findings else 'RULE_CONSISTENT' if o['sameRuleEscalation'] else 'AMBIGUOUS'
    sfe=record['validation']['shortFormEngine']
    silent=dict(score=sfe['silentLegibilityScore'],parts=sfe['silentLegibility'],dialogue=sfe['dialogue'],evidenceLimitations=sfe['evidenceLimitations'])
    per_beat=deepcopy(pre['eachBeat'])
    for b,canonical in zip(per_beat,o['beatCausalEvidence']):
        b['canonicalEvidence']=canonical
        if b['ruleConsistency']!='RULE_INCONSISTENT' and rule=='RULE_CONSISTENT' and canonical.get('stateChangeSupported'):
            b['ruleConsistency']='RULE_CONSISTENT'
    if any(b['ruleConsistency']=='AMBIGUOUS' for b in per_beat) and rule=='RULE_CONSISTENT':rule='AMBIGUOUS'
    out['creativeEvidence']=dict(ruleConsistency=rule,ruleConsistencyBasis='Existing declared source constraints and canonical causal support, not observed video or proof of every physical implication.',
        perBeat=per_beat,statedRule=ideas[0].impossibleRule,offendingFindings=findings,
        stableTrigger=rule,frameZeroProblemSupported=o['frameZeroSupported'],goalVisible=o['goalVisible'],
        payoffRuleLinked=o['payoffRuleLinked'],payoffEvidence=o['payoffEvidence'],silentViewEvidence=silent,
        silentViewSource='Existing shortFormEngine.silentLegibilityScore/silentLegibility/dialogue; source-text screen only',duration=pre['duration'],
        providerRationaleUsedAsAuthority=False,sourceOnly=True)
    creative_ok=bool(pre['structuralContractPassed'] and pre['finalPayoffEqualsLastConsequence'] and o['frameZeroSupported'] and o['goalVisible'] and rule=='RULE_CONSISTENT' and o['payoffRuleLinked'] and record['candidate']['beatGrammar']['beatGrammarQuality'] not in ('BROKEN','MECHANICAL') and record['admission']['admitted'] and not sfe['dialogue']['audioDependent'] and ideas[0].dialogueNeed!='REQUIRED')
    out['creativeContractClassification']='CREATIVE_CONTRACT_PASS' if creative_ok else 'CREATIVE_CONTRACT_FAILURE'
    out['creativeContractScope']='Read-only summary of existing structural/source evidence; not a new downstream gate, quality certification or model comparison. Production blockers remain authoritative and separate.'
    return out


def execute(path,profile,*,authorization=None,tests=None,runner=None):
    if not authorization or not tests or not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):
        raise ValueError('Explicit authorization, completed regression and schema integrity proof required')
    spec=plan(profile)
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('Credential unavailable; no request')
    path=Path(path);path.mkdir(parents=True,exist_ok=False) # Durable claim; failure still consumes this experiment.
    write_new(path/'plan.json',dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',promptVersion='v2-compact',promptHash=PROMPT_HASH,schemaHash=SCHEMA_HASH,
        candidateCount=1,structuredOutputMode='json_schema',strict=False,streamingMode='NON_STREAMING',reasoningEffort='high',temperature=None,maxOutputTokens=OUTPUT_TOKENS,
        timeout=TIMEOUT,SDKTimeout=dict(connect=15,read=90,write=60,pool=15),maximumLiveRequests=1,SDKRetries=0,retries=0,fallbacks=0,authorization=authorization,tests=tests))
    write_new(path/'prompt.json',spec['prompt']);write_new(path/'configuration.json',spec['configuration'])
    write_new(path/'request-before-sdk.json',dict(provider='openai',baseUrl=profile['baseUrl'],arguments=spec['arguments'],timeout=TIMEOUT,maxRetries=0))
    write_new(path/'offline-schema-validation.json',dict(integrity=spec['FINAL_PROVIDER_SCHEMA_VALIDATION'],equivalence=spec['semanticEquivalence'],metrics=spec['metrics']))
    start_ns=time.monotonic_ns();start_utc=datetime.now(UTC)
    write_new(path/'request-started.json',dict(logicalRequestCount=1,maximumLiveRequests=1,startUTC=start_utc.isoformat()))
    try:result=(runner or bounded)(path,profile,spec)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,exceptionChain=[dict(exceptionClass=type(error).__name__)],safeMessage='Runner failed; no replacement request.',usage=None)
    end_utc=datetime.now(UTC);end_ns=time.monotonic_ns()
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    raw=(path/'response.txt').read_text();inspection=None
    if result['status']=='COMPLETED' and raw:
        # Persist creative/shape observations before invoking the accepted full pipeline.
        try:pre=pre_pipeline_contract(parse_exact(raw))
        except (ValueError,TypeError):pre=dict(parseFailed=True)
        write_new(path/'pre-pipeline-creative-contract.json',pre)
        try:inspection=inspect_response(raw,spec)
        except Exception as error:inspection=dict(executionClassification='UNRESOLVED',creativeContractClassification='CREATIVE_CONTRACT_FAILURE',pipelineError=type(error).__name__)
        write_new(path/'inspection.json',inspection)
        if inspection.get('pipeline'):
            write_new(path/'pipeline.json',inspection['pipeline'])
            write_new(path/'complete-candidate-and-pipeline.txt',all_ideas_text(inspection['pipeline']),raw=True)
        classification=inspection['executionClassification']
    else:
        chain=[c.get('exceptionClass','') for c in result.get('exceptionChain',[])]+[result.get('errorClass','')]
        classification='COMPACT_FULL_CONTRACT_TIMEOUT' if any('timeout' in c.casefold() for c in chain) else 'COMPACT_FULL_CONTRACT_PROVIDER_FAILURE'
    result.update(executionClassification=classification,creativeContractClassification=inspection['creativeContractClassification'] if inspection else None,
        timing=timing_record(start_utc,end_utc,start_ns,end_ns),responseBytes=len(raw.encode()),
        logicalRequestCount=1,maximumLiveRequests=1,retries=0,DeepSeekCalls=0,fallbacks=0,renders=0,pipelineRan=bool(inspection and inspection.get('pipelineRan')),
        promptHash=PROMPT_HASH,schemaHash=SCHEMA_HASH,timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS)
    write_new(path/'result.json',result)
    return result
