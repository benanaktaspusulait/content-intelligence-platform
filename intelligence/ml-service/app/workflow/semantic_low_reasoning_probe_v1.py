"""One-variable low-effort experiment reusing the exact accepted SDK/HTTP worker."""
from copy import deepcopy
from datetime import UTC, datetime
import inspect
import json
import os
from pathlib import Path
import time
from typing import get_args

from openai.resources.chat.completions.completions import Completions
from openai.types.shared.reasoning_effort import ReasoningEffort
from . import semantic_compact_capability_probe_v1 as previous
from .creative_provider_profiles import MODEL_REASONING_EFFORTS,CreativeCapabilityProvider,validate_reasoning_effort
from .concept_fingerprint import digest
from .semantic_live_experiment import write_new
from .semantic_schema_integrity_probe_v1 import timing_record
from .semantic_prompt_v2_experiment import all_ideas_text

EXPERIMENT_ID='semantic-low-reasoning-full-contract-probe-1-run-001'
ORDER=('none','minimal','low','medium','high','xhigh','max')


def discover_reasoning(*,model_contract=None,sdk_type=ReasoningEffort,sdk_parameter=None,adapter_parameter=None):
    """Intersect SDK literal support with accepted exact-model integration policy."""
    def literals(value):
        return [value] if isinstance(value,str) else [s for child in get_args(value) for s in literals(child)]
    model_contract=MODEL_REASONING_EFFORTS if model_contract is None else model_contract
    sdk_values=literals(sdk_type)
    sdk_parameter='reasoning_effort' in inspect.signature(Completions.create).parameters if sdk_parameter is None else sdk_parameter
    adapter_parameter="args['reasoning_effort']=p['reasoningEffort']" in inspect.getsource(CreativeCapabilityProvider.complete) if adapter_parameter is None else adapter_parameter
    model_values=list(model_contract.get(('openai','gpt-6.1-sol'),()))
    supported=[v for v in ORDER if v in sdk_values and v in model_values] if sdk_parameter and adapter_parameter else []
    return dict(status='CONTROLLABLE' if supported else 'REASONING_EFFORT_NOT_CONTROLLABLE',
        sdkValues=sdk_values,exactModelIntegrationValues=model_values,supportedSettings=supported,
        SDKChatCompletionsParameterPresent=sdk_parameter,adapterForwardsParameter=adapter_parameter,
        selectedLowest=supported[0] if supported else None,
        evidence=['creative_provider_profiles.MODEL_REASONING_EFFORTS','CreativeCapabilityProvider.complete','openai.types.shared.reasoning_effort.ReasoningEffort','openai.resources.chat.completions.completions.Completions.create'],
        selection='Lowest supported exact-model/SDK intersection; generic SDK none/minimal are not accepted for this model.')


def differences(a,b,path=''):
    if type(a) is not type(b):return [dict(path=path,previous=a,new=b)]
    if isinstance(a,dict):
        out=[]
        for key in sorted(set(a)|set(b)):
            at=path+'/'+key
            out.extend(differences(a[key],b[key],at) if key in a and key in b else [dict(path=at,previous=a.get(key),new=b.get(key))])
        return out
    if isinstance(a,list):
        if len(a)!=len(b):return [dict(path=path,previous=a,new=b)]
        return [d for i,(x,y) in enumerate(zip(a,b)) for d in differences(x,y,path+'/'+str(i))]
    return [] if a==b else [dict(path=path,previous=a,new=b)]


def plan(profile,previous_request,*,discovery=None):
    discovery=discover_reasoning() if discovery is None else discovery
    prior_effort=previous_request['arguments'].get('reasoning_effort','NOT_EXPLICITLY_CONFIGURED')
    if discovery['status']!='CONTROLLABLE' or discovery['selectedLowest']==prior_effort:
        return dict(status='REASONING_EFFORT_NOT_CONTROLLABLE',discovery=discovery,previousReasoningEffort=prior_effort,providerCalls=0,
            reason='No supported lower effort exposed by current exact-model/SDK/adapter integration')
    # Rebuild the previous accepted request unchanged first, then alter only the one parameter.
    spec=previous.plan(profile)
    if spec['arguments']!=previous_request['arguments']:raise ValueError('Accepted construction no longer matches exact previous failed SDK request')
    if spec['timeout']!=previous_request['timeout'] or previous_request['maxRetries']!=0 or previous_request['provider']!='openai' or previous_request['baseUrl']!=profile['baseUrl']:
        raise ValueError('Accepted execution envelope changed')
    selected=discovery['selectedLowest'];low_profile=deepcopy(profile);low_profile['reasoningEffort']=selected
    validate_reasoning_effort(low_profile)
    spec['arguments']['reasoning_effort']=selected
    new_request=deepcopy(previous_request);new_request['arguments']=deepcopy(spec['arguments'])
    delta=differences(previous_request,new_request)
    expected=[dict(path='/arguments/reasoning_effort',previous=prior_effort,new=selected)]
    if delta!=expected:raise ValueError('More than one request variable changed')
    return dict(status='READY',spec=spec,profile=low_profile,previousReasoningEffort=prior_effort,selectedReasoningEffort=selected,discovery=discovery,
        previousRequest=previous_request,newRequest=new_request,requestDiff=delta,onlyReasoningChanged=True,
        unchangedArgumentsSha256=digest({k:v for k,v in spec['arguments'].items() if k!='reasoning_effort'}),
        unavoidableSDKDifferences='No semantic body difference permitted. Per-call auth/transport headers, SDK retry-attempt UUID and request timestamps can differ; raw credential headers are never persisted.',providerCalls=0)


def interpretation(classification):
    if classification=='LOW_REASONING_FULL_CONTRACT_EXECUTION_PASS':return 'REASONING_LATENCY_CONFIRMED_AS_MAJOR_FACTOR'
    if classification=='LOW_REASONING_FULL_CONTRACT_TIMEOUT':return 'REASONING_REDUCTION_INSUFFICIENT'
    return 'UNRESOLVED'


def execute(path,profile,previous_request,*,authorization=None,tests=None,runner=None,discovery=None):
    planned=plan(profile,previous_request,discovery=discovery)
    if planned['status']=='REASONING_EFFORT_NOT_CONTROLLABLE':return planned
    if not authorization or not tests or not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):
        raise ValueError('Explicit authorization and completed regression/schema proof required')
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('Credential unavailable; no request')
    path=Path(path);path.mkdir(parents=True,exist_ok=False)
    spec=planned['spec'];low_profile=planned['profile']
    write_new(path/'plan.json',dict(experimentId=EXPERIMENT_ID,provider='openai',model='gpt-6.1-sol',candidateCount=1,previousReasoningEffort=planned['previousReasoningEffort'],
        selectedReasoningEffort=planned['selectedReasoningEffort'],promptHash=previous.PROMPT_HASH,schemaHash=previous.SCHEMA_HASH,
        timeout=spec['timeout'],maxOutputTokens=spec['maxOutputTokens'],streamingMode=spec['streamingMode'],structuredOutputMode='json_schema',temperature=None,
        maximumLiveRequests=1,SDKMaxRetries=0,authorization=authorization,tests=tests,
        requestConstruction='Reuses frozen compact construct_native_request + previous bounded worker + same CreativeCapabilityProvider.complete + same SDK/API method; only reasoning_effort changed.'))
    write_new(path/'discovery.json',planned['discovery']);write_new(path/'pre-request-diff.json',{k:planned[k] for k in ('previousReasoningEffort','selectedReasoningEffort','previousRequest','newRequest','requestDiff','onlyReasoningChanged','unchangedArgumentsSha256','unavoidableSDKDifferences')})
    write_new(path/'request-before-sdk.json',planned['newRequest']);write_new(path/'prompt.json',spec['prompt']);write_new(path/'configuration.json',spec['configuration'])
    write_new(path/'offline-schema-validation.json',dict(integrity=spec['FINAL_PROVIDER_SCHEMA_VALIDATION'],equivalence=spec['semanticEquivalence'],metrics=spec['metrics']))
    start_ns=time.monotonic_ns();start_utc=datetime.now(UTC)
    write_new(path/'request-started.json',dict(logicalRequestCount=1,maximumLiveRequests=1,startUTC=start_utc.isoformat()))
    try:result=(runner or previous.bounded)(path,low_profile,spec)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,exceptionChain=[dict(exceptionClass=type(error).__name__)],safeMessage='Runner failed; no replacement request.',usage=None)
    end_utc=datetime.now(UTC);end_ns=time.monotonic_ns()
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    raw=(path/'response.txt').read_text();inspection=None
    if result['status']=='COMPLETED' and raw:
        try:pre=previous.pre_pipeline_contract(previous.parse_exact(raw))
        except (ValueError,TypeError):pre=dict(parseFailed=True)
        write_new(path/'pre-pipeline-creative-contract.json',pre)
        try:inspection=previous.inspect_response(raw,spec)
        except Exception as error:inspection=dict(executionClassification='UNRESOLVED',creativeContractClassification='CREATIVE_CONTRACT_FAILURE',pipelineError=type(error).__name__)
        write_new(path/'inspection.json',inspection)
        if inspection.get('pipeline'):
            write_new(path/'pipeline.json',inspection['pipeline']);write_new(path/'complete-candidate-and-pipeline.txt',all_ideas_text(inspection['pipeline']),raw=True)
        classification=inspection['executionClassification'].replace('COMPACT_FULL_CONTRACT_','LOW_REASONING_FULL_CONTRACT_')
    else:
        chain=[c.get('exceptionClass','') for c in result.get('exceptionChain',[])]+[result.get('errorClass','')]
        classification='LOW_REASONING_FULL_CONTRACT_TIMEOUT' if any('timeout' in c.casefold() for c in chain) else 'LOW_REASONING_FULL_CONTRACT_PROVIDER_FAILURE'
    result.update(executionClassification=classification,interpretation=interpretation(classification),creativeContractClassification=inspection['creativeContractClassification'] if inspection else None,
        timing=timing_record(start_utc,end_utc,start_ns,end_ns),responseBytes=len(raw.encode()),logicalRequestCount=1,maximumLiveRequests=1,retries=0,DeepSeekCalls=0,fallbacks=0,renders=0,
        pipelineRan=bool(inspection and inspection.get('pipelineRan')),previousReasoningEffort=planned['previousReasoningEffort'],selectedReasoningEffort=planned['selectedReasoningEffort'],
        promptHash=previous.PROMPT_HASH,schemaHash=previous.SCHEMA_HASH,timeout=spec['timeout'],maxOutputTokens=spec['maxOutputTokens'])
    write_new(path/'result.json',result);return result
