"""Bounded two-shard transport recovery; all accepted creative judges unchanged."""
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import time

from .concept_fingerprint import digest
from .semantic_concept_prompt_v2 import prompt_v2
from .semantic_prompt_v2_experiment import configuration_for, analyze, all_ideas_text, review_cards
from .semantic_live_experiment import response_format, request_arguments, write_new
from .short_concept_generation import resolve_cast
from . import creative_shape

EXPERIMENT_ID='semantic-live-v2-count-40-run-001-recovery-001'
PARENT_EXPERIMENT_ID='semantic-live-v2-count-40-run-001'
OUTPUT_TOKENS=32768
TIMEOUT=dict(readSeconds=120,connectSeconds=15,writeSeconds=60,poolSeconds=15,wallSeconds=300)


def shard_prompt(config,cast,shard):
    if shard not in ('A','B'):raise ValueError('Only two planned shards')
    p=prompt_v2(config,cast,20);payload=json.loads(p['prompt'])
    payload['limits']['timeoutSeconds']=TIMEOUT['readSeconds']
    payload['shardMetadata']=dict(experimentId=EXPERIMENT_ID,shardId=shard,requestedCandidateCount=20,
        ideaIdPrefix='v2-'+shard.lower()+'-',ordinalRange=[1,20])
    p['prompt']=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    p['sha256']=digest([p['system'],payload])
    return p


def _worker(path,profile,config,prompt):
    """A child gets one SDK call, no retry. Parent enforces a real wall deadline."""
    from .creative_provider_profiles import CreativeCapabilityProvider
    import httpx
    path=Path(path);provider=None;raw='';result=dict(status='REQUEST_FAILED',usage=None,providerRequestId=None,
        providerResponseMetadata=None,providerCostUsd=None,sdkMaxRetries=0,observableTransportRetries=0)
    try:
        provider=CreativeCapabilityProvider(profile,OUTPUT_TOKENS,TIMEOUT['readSeconds'])
        if provider.client.max_retries!=0:raise ValueError('SDK retries must be disabled before request')
        provider.client.timeout=httpx.Timeout(TIMEOUT['readSeconds'],connect=TIMEOUT['connectSeconds'],
            write=TIMEOUT['writeSeconds'],pool=TIMEOUT['poolSeconds'])
        provider.response_format=response_format()
        provider.response_format['json_schema']['schema']['properties']['ideas'].update(minItems=20,maxItems=20)
        write_new(path/'sdk-call-started.json',dict(status='REQUEST_STARTED',sdkMaxRetries=provider.client.max_retries))
        raw=provider.complete(prompt['prompt'],system=prompt['system'],temperature=config['semanticProvider']['temperature'])
        result['status']='REQUEST_COMPLETED'
    except Exception as error:
        result.update(errorType=type(error).__name__,httpStatus=getattr(error,'status_code',None),
            safeError='Shard request failed; no retry or replacement.')
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        result['usage']=getattr(provider,'last_usage',None)
        result['providerResponseMetadata']=getattr(provider,'last_response_metadata',None)
        result['providerRequestId']=(result['providerResponseMetadata'] or {}).get('requestId')
        usage=result['usage'] or {}
        result['providerCostUsd']=usage.get('actual_cost_usd') if isinstance(usage,dict) else None
        write_new(path/'response.txt',raw,raw=True)
        write_new(path/'worker-result.json',result)


def bounded_request(path,profile,config,prompt):
    ctx=multiprocessing.get_context('spawn')
    process=ctx.Process(target=_worker,args=(str(path),profile,config,prompt))
    process.start();process.join(TIMEOUT['wallSeconds'])
    timed_out=process.is_alive()
    if timed_out:
        process.terminate();process.join(5)
        if process.is_alive():process.kill();process.join(5)
    result_path=Path(path)/'worker-result.json'
    if not timed_out and result_path.exists():return json.loads(result_path.read_text())
    return dict(status='REQUEST_FAILED',errorType='ExperimentWallTimeout' if timed_out else 'WorkerExited',
        safeError='Bounded shard worker stopped; no retry or replacement.',usage=None,providerCostUsd=None,
        providerRequestId=None,sdkMaxRetries=0,observableTransportRetries=0,workerTerminated=timed_out)


def execute_two(directory,profile,*,authorization=None,test_evidence=None,runner=None):
    if not authorization or not test_evidence or not test_evidence.get('noNewFailures'):
        raise ValueError('Explicit authorization and completed tests required')
    if profile.get('provider')!='deepseek' or profile.get('model')!='deepseek-v4-pro':
        raise ValueError('Same configured DeepSeek/deepseek-v4-pro required')
    if profile['maxOutputTokens']<OUTPUT_TOKENS:raise ValueError('Insufficient configured output capacity')
    if not os.getenv('DEEPSEEK_API_KEY'):raise ValueError('Configured credential unavailable')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    cfg=configuration_for(profile);cfg.semanticProvider.maxOutputTokens=OUTPUT_TOKENS
    cast,_=resolve_cast(cfg)
    # Both immutable requests are planned before either result exists. B never receives A.
    prompts={s:shard_prompt(cfg,cast,s) for s in ('A','B')}
    write_new(directory/'plan.json',dict(experimentId=EXPERIMENT_ID,parentExperimentId=PARENT_EXPERIMENT_ID,
        plannedShards=['A','B'],requestedCounts=[20,20],maxLiveRequests=2,maxOutputTokensPerShard=OUTPUT_TOKENS,
        timeout=TIMEOUT,sdkMaxRetries=0,replacementRequests=0,authorization=authorization,testEvidence=test_evidence,
        originalFailedAttemptPreserved=True,renders=0))
    write_new(directory/'configuration.json',dict(profile=profile,generation=cfg.model_dump(),cast=cast,
        transportTimeout=TIMEOUT,legacyGenerationTimeoutNotUsedForTransport=True))
    for s in ('A','B'):
        path=directory/('shard-'+s.lower());path.mkdir()
        write_new(path/'prompt.json',prompts[s]);fmt=response_format()
        fmt['json_schema']['schema']['properties']['ideas'].update(minItems=20,maxItems=20)
        args=request_arguments(profile,cfg,prompts[s])
        # Existing JSON-mode request helper embeds a40-item envelope; replace only that request-level count.
        if profile['responseMode']=='json_object':
            args['messages'][0]['content']=prompts[s]['system']+'\nReturn JSON matching this schema; use catalog IDs exactly:\n'+json.dumps(fmt['json_schema']['schema'],separators=(',',':'))
        else:args['response_format']=fmt
        write_new(path/'request.json',dict(baseUrl=profile['baseUrl'],arguments=args,maxRetries=0,timeout=TIMEOUT))
    results=[];runner=runner or bounded_request
    for s in ('A','B'):
        path=directory/('shard-'+s.lower());started=time.monotonic();stamp=datetime.now(UTC).isoformat()
        write_new(path/'request-started.json',dict(status='REQUEST_STARTED',shardId=s,startedAt=stamp,
            logicalRequestOrdinal=len(results)+1,maximumRequests=2))
        try:result=runner(path,profile,cfg.model_dump(),prompts[s])
        except Exception as error:
            result=dict(status='REQUEST_FAILED',errorType=type(error).__name__,safeError='Shard runner failed; next planned shard remains independent.',usage=None,providerCostUsd=None)
        result.update(shardId=s,provider=profile['provider'],model=profile['model'],promptVersion='v2',
            startedAt=stamp,finishedAt=datetime.now(UTC).isoformat(),latencySeconds=time.monotonic()-started,
            timeout=TIMEOUT,maxOutputTokens=OUTPUT_TOKENS,logicalRequestCount=1)
        if not (path/'response.txt').exists():write_new(path/'response.txt','',raw=True)
        write_new(path/'provider-metadata.json',result);results.append(result)
        print(json.dumps({k:result[k] for k in ('shardId','status','latencySeconds')}),flush=True)
    write_new(directory/'transport-summary.json',dict(logicalRequestCount=len(results),maxLiveRequests=2,
        sdkMaxRetries=0,shards=results,usage=aggregate_usage(results),renders=0))
    return results


def aggregate_usage(results):
    fields=dict(inputTokens='prompt_tokens',outputTokens='completion_tokens',totalTokens='total_tokens')
    totals={k:sum((r.get('usage') or {}).get(v,0) for r in results) if all(isinstance((r.get('usage') or {}).get(v),int) for r in results) else None for k,v in fields.items()}
    totals['providerCostUsd']=sum(r['providerCostUsd'] for r in results) if all(isinstance(r.get('providerCostUsd'),(int,float)) for r in results) else None
    totals['reportedSubsetTotals']={k:sum((r.get('usage') or {}).get(v,0) for r in results) for k,v in fields.items()}
    totals['completeUsageReported']=all(r.get('usage') is not None for r in results)
    return totals


def combine(directory):
    directory=Path(directory);ideas=[];provenance=[];envelopes=[]
    for s in ('A','B'):
        path=directory/('shard-'+s.lower());raw=(path/'response.txt').read_text();meta=json.loads((path/'provider-metadata.json').read_text())
        try:
            def unique(pairs):
                value={}
                for key,item in pairs:
                    if key in value:raise ValueError('Duplicate JSON key')
                    value[key]=item
                return value
            payload=json.loads(raw,object_pairs_hook=unique,
                parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            if not isinstance(payload,dict) or set(payload)!={'ideas'} or not isinstance(payload['ideas'],list):raise ValueError('Invalid envelope')
            items=payload['ideas'];status='JSON_ENVELOPE_AVAILABLE'
        except (ValueError,TypeError):items=[];status='NO_USABLE_JSON_ENVELOPE'
        envelopes.append(dict(shardId=s,status=status,returnedRawCount=len(items),transportStatus=meta['status']))
        for ordinal,item in enumerate(items,1):
            id=f'v2-{s.lower()}-{ordinal:03d}'
            source=dict(ideaId=id,shardId=s,candidateOrdinalWithinShard=ordinal,
                providerOriginalIdeaId=item.get('ideaId') if isinstance(item,dict) else None,
                provider=meta['provider'],model=meta['model'],promptVersion='v2',generationSource='SEMANTIC_V2',
                experimentId=EXPERIMENT_ID,parentExperimentId=PARENT_EXPERIMENT_ID,
                providerRequestId=meta.get('providerRequestId'),responseSha256=hashlib.sha256(raw.encode()).hexdigest(),
                providerPromptSha256=json.loads((path/'prompt.json').read_text())['sha256'])
            normalized=deepcopy(item)
            if isinstance(normalized,dict):normalized['ideaId']=id
            ideas.append(normalized);provenance.append(source)
    return dict(ideas=ideas),provenance,envelopes


def analyze_combined(directory):
    directory=Path(directory);out=directory/'combined-analysis';out.mkdir(exist_ok=False)
    corpus,provenance,envelopes=combine(directory)
    write_new(out/'combined-corpus.json',corpus);write_new(out/'source-provenance.json',provenance);write_new(out/'shard-envelopes.json',envelopes)
    if not corpus['ideas']:
        status=dict(status='NO_USABLE_SHARD_RESPONSE',rawCount=0,creativeMetrics=None,HUMAN_REVIEW_SET=None,renders=0,providerCallsDuringAnalysis=0)
        write_new(out/'analysis-status.json',status);return status
    cfgdata=json.loads((directory/'configuration.json').read_text())
    from .semantic_concept_prompt_v2 import PromptV2Request
    cfg=PromptV2Request.model_validate(cfgdata['generation']);p=prompt_v2(cfg,cfgdata['cast'],40)
    result=analyze(json.dumps(corpus),cfg,p);byid={s['ideaId']:s for s in provenance}
    for row in result['allRawIdeas']:
        row['sourceProvenance']=byid.get(row['ideaId'],provenance[row['rawIndex']])
        r=row['record']
        if not r:continue
        source=row['sourceProvenance'];c=r['candidate'];r['sourceProvenance']=source
        c['adapterGenerationSource']=c['generationSource'];c['generationSource']='SEMANTIC_V2'
        c['provenance'].update(source);c['providerPromptVersion']='v2';c.update({k:source[k] for k in ('experimentId','shardId','providerRequestId','candidateOrdinalWithinShard')})
        o=r['observation'];status=o['ruleConsistency']['status']
        o['ruleConsistencyResult']={'CONTRADICTION_DETECTED':'RULE_INCONSISTENT','SUPPORTED_BY_EXISTING_EVIDENCE':'RULE_CONSISTENT','UNRESOLVED':'AMBIGUOUS'}[status]
        opening=c['premiseNaturalness']['openingEvidence']
        o['openingAudit']=opening
        payoff=o['payoffEvidence'];o['payoffAudit']=dict(present=payoff['presence']!='MISSING',ruleLinked=o['payoffRuleLinked'],stateChanging=payoff['stateChanging'],
            introducesNewRule=True if o['payoffRuleConsistencyFindings'] else None,
            limitation='No finding means unestablished, not proof that no new rule exists.')
    # No source rewrite reaches judges. Original accepted source snapshots/receipts remain attached.
    duplicates=[];records=[r['record'] for r in result['allRawIdeas'] if r['record']]
    for i,a in enumerate(records):
        for b in records[i+1:]:
            if a['sourceProvenance']['shardId']==b['sourceProvenance']['shardId']:continue
            x,y=a['candidate'],b['candidate'];d=creative_shape.distance(x,y)
            duplicates.append(dict(candidateIds=[x['candidateId'],y['candidateId']],
                exactStructuralFingerprint=x['structuralFingerprint']==y['structuralFingerprint'],
                exactShapeHash=x['storyShapeFingerprint']['shapeHash']==y['storyShapeFingerprint']['shapeHash'],
                shapeDistance=d,rankingDuplicateRisks=[a['validation']['duplicateRisk'],b['validation']['duplicateRisk']],
                limitation='Existing fingerprint equivalence/distance, not certified semantic identity; no new dedup gate.'))
    result['crossShardComparisons']=duplicates;result['shardEnvelopes']=envelopes
    write_new(out/'results.json',result);write_new(out/'all-candidate-stories.txt',all_ideas_text(result),raw=True)
    write_new(out/'human-review-cards.json',review_cards(result));write_new(out/'cross-shard-duplicates.json',duplicates)
    write_new(out/'analysis-status.json',dict(status='COMPLETED',metrics=result['metrics'],providerCallsDuringAnalysis=0,renders=0))
    return result
