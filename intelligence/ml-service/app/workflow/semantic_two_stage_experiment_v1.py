"""Durable three-seed/one-expansion experiment. No retry, replacement or fallback."""
from datetime import UTC, datetime
import os
from pathlib import Path
import time

from . import semantic_two_stage_v1 as stage
from .semantic_compact_1_probe_v1 import bounded
from .semantic_transport_isolation_v1 import TIMEOUT
from .semantic_schema_integrity_probe_v1 import timing_record
from .semantic_live_experiment import write_new

EXPERIMENT_ID='semantic-two-stage-v1-run-001'
REQUEST_IDS=('opening-a','opening-b','opening-c')


class RequestBudget:
    def __init__(self):self.used=[]
    def claim(self,phase,identity):
        if phase not in ('A','B') or identity in [id for _,id in self.used]:raise ValueError('NO_RETRY_OR_REPLACEMENT')
        if len(self.used)>=4 or sum(p==phase for p,_ in self.used)>=(3 if phase=='A' else 1):raise ValueError('LIVE_REQUEST_CAP')
        self.used.append((phase,identity))


def call(path,profile,spec,*,budget,identity,runner=None):
    budget.claim(spec['phase'],identity)
    path=Path(path);path.mkdir(exist_ok=False)
    write_new(path/'plan.json',dict(requestId=identity,phase=spec['phase'],provider='openai',model='gpt-6.1-sol',reasoningEffort='low',
        maximumTotalRequests=4,maximumPhaseA=3,maximumPhaseB=1,SDKRetries=0,timeout=TIMEOUT,maxOutputTokens=8192,streaming='NON_STREAMING'))
    write_new(path/'prompt.json',spec['prompt'])
    write_new(path/'request-before-sdk.json',dict(provider='openai',baseUrl=profile['baseUrl'],arguments=spec['arguments'],timeout=TIMEOUT,maxRetries=0))
    write_new(path/'offline-schema-validation.json',spec['FINAL_PROVIDER_SCHEMA_VALIDATION'])
    start_ns=time.monotonic_ns();start=datetime.now(UTC)
    try:result=(runner or bounded)(path,profile,spec)
    except Exception as error:result=dict(status='FAILED',errorClass=type(error).__name__,usage=None)
    end=datetime.now(UTC);end_ns=time.monotonic_ns()
    if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
    result.update(timing=timing_record(start,end,start_ns,end_ns),responseBytes=len((path/'response.txt').read_bytes()),
                  retries=0,fallbacks=0,DeepSeekCalls=0,renders=0,requestId=identity,phase=spec['phase'])
    write_new(path/'result.json',result)
    return result,(path/'response.txt').read_text()


def execute(directory,config,cast,profile,*,authorization,tests,runner=None):
    if not authorization or not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):
        raise ValueError('Offline verification and explicit authorization required')
    if not os.getenv('OPENAI_API_KEY'):raise ValueError('Credential unavailable; no calls')
    spec=stage.request_spec(config,cast,profile,'A')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    write_new(directory/'experiment-plan.json',dict(experimentId=EXPERIMENT_ID,generationArchitecture=stage.ARCHITECTURE,
        PhaseARequests=list(REQUEST_IDS),maximumPhaseARequests=3,maximumPhaseBRequests=1,maximumTotalRequests=4,
        openingFloor=stage.OPENING_FLOOR,SDKRetries=0,retries=0,replacements=0,fallbacks=0,DeepSeekCalls=0,renders=0,
        authorization=authorization,tests=tests))
    budget=RequestBudget();records=[]
    for identity in REQUEST_IDS:
        path=directory/identity
        result,raw=call(path,profile,spec,budget=budget,identity=identity,runner=runner)
        row=dict(requestId=identity,execution=result,seed=None,gate=None)
        if result['status']=='COMPLETED' and raw:
            try:
                seed=stage.parse_seed(raw);unique=f'{EXPERIMENT_ID}/{identity}/{seed.seedId}'
                gate=stage.gate_seed(seed,cast,unique)
                row.update(seed=seed.model_dump(),gate=gate)
                write_new(path/'seed.json',row['seed']);write_new(path/'gate.json',gate)
            except Exception as error:row.update(rejection=dict(code='SEED_PARSE_OR_GATE_FAILURE',errorClass=type(error).__name__,message=str(error)[:2000]))
        records.append(row);write_new(directory/f'{identity}-record.json',row)
    selected=stage.select_seed(records);expansion=None
    if selected:
        provenance=stage.SeedProvenance(openingSeedId=selected['gate']['openingSeedId'],openingSeedRunId=f'{EXPERIMENT_ID}/{selected["requestId"]}',storyExpansionRunId=f'{EXPERIMENT_ID}/expansion-1')
        frozen=stage.freeze_seed(selected['seed'],selected['gate'],provenance)
        write_new(directory/'frozen-opening-seed.json',frozen)
        bspec=stage.request_spec(config,cast,profile,'B',frozen)
        result,raw=call(directory/'expansion-1',profile,bspec,budget=budget,identity='expansion-1',runner=runner)
        expansion=dict(execution=result,analysis=None)
        if result['status']=='COMPLETED' and raw:
            try:expansion['analysis']=stage.analyze_expansion(raw,frozen,config,bspec['prompt'])
            except Exception as error:expansion['analysis']=dict(status='EXPANSION_REJECTED',errorClass=type(error).__name__,message=str(error)[:2000],pipelineRan=False)
        write_new(directory/'expansion-result.json',expansion)
    below=[r['gate']['openingScore'] for r in records if r.get('gate')]
    status='EXPANSION_ATTEMPTED' if selected else 'OPENING_SEED_GENERATION_STILL_WEAK' if len(below)==3 and all(v<stage.OPENING_FLOOR for v in below) else 'NO_ACCEPTED_OPENING_SEED'
    report=dict(status=status,PhaseA=records,selectedOpeningSeedId=selected['gate']['openingSeedId'] if selected else None,PhaseB=expansion,
        metrics=dict(openingSeedsGenerated=sum(r['seed'] is not None for r in records),openingSeedsPassingGate=sum(bool(r.get('gate') and r['gate']['acceptedForExpansion']) for r in records),
        seedsExpanded=int(expansion is not None),PhaseAProviderCalls=sum(p=='A' for p,_ in budget.used),PhaseBProviderCalls=sum(p=='B' for p,_ in budget.used),
        totalProviderRequests=len(budget.used),SDKRequestsForwarded=sum(r['execution'].get('SDKRequestsForwarded',0) for r in records)+(expansion['execution'].get('SDKRequestsForwarded',0) if expansion else 0),
        HTTPRequestsObserved=sum(r['execution'].get('HTTPRequestsObserved',0) for r in records)+(expansion['execution'].get('HTTPRequestsObserved',0) if expansion else 0),
        retries=0,replacements=0,fallbacks=0,DeepSeekCalls=0,renders=0),
        baselineOpeningScores=[35]*5,providerScoresUsed=False,stoppedAfterControlledExperiment=True)
    write_new(directory/'experiment-result.json',report)
    return report
