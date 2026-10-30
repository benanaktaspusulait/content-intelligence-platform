#!/usr/bin/env python3
"""Offline-first two-stage audit; fixed initial live experiment only after verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
DOCS=ROOT/'intelligence/docs';OUT=DOCS/'semantic-two-stage-v1';RUN=DOCS/'semantic-two-stage-v1-run-001'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-live',action='store_true');args=parser.parse_args()
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    if not args.execute_live:
        def guard(event,args):
            if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('Offline audit forbids network/subprocess execution')
        sys.addaudithook(guard)
    from app.workflow import semantic_two_stage_v1 as stage
    from app.workflow import semantic_two_stage_experiment_v1 as experiment
    from app.workflow import semantic_low_reasoning_probe_v1 as low
    from app.workflow.creative_provider_profiles import profile
    from app.workflow.short_concept_generation import resolve_cast
    prior=json.loads((DOCS/'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    accepted=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    inherited=low.plan(profile('openai-escalation'),prior)
    if inherited['newRequest']!=accepted:parser.error('Accepted LOW profile changed')
    selected=inherited['profile']
    config=stage.TwoStageRequest.model_validate({**inherited['spec']['configuration'],'semanticConceptPromptVersion':'two-stage-v1'})
    cast,_=resolve_cast(config)
    if not args.execute_live:
        OUT.mkdir(exist_ok=True,parents=True)
        spec=stage.request_spec(config,cast,selected,'A')
        fixture=json.loads((ROOT/'intelligence/ml-service/tests/fixtures/semantic_two_stage_v1_mocks.json').read_text())
        results=[]
        for case in fixture['seeds']:
            gate=stage.gate_seed(case['seed'],cast,'offline/'+case['case'])
            assert gate['acceptedForExpansion']==case['expectAccepted']
            results.append(dict(**case,gate=gate))
        seed=results[0];provenance=stage.SeedProvenance(openingSeedId='offline/A',openingSeedRunId='offline/A',storyExpansionRunId='offline/B')
        frozen=stage.freeze_seed(seed['seed'],seed['gate'],provenance);bspec=stage.request_spec(config,cast,selected,'B',frozen)
        expansions=[]
        from copy import deepcopy
        for case in ('consistent','mutate-opening','mutate-rule','mutate-trigger','reset','payoff-magic','correct-payoff'):
            raw=deepcopy(fixture['consistentExpansion'])
            if case=='mutate-opening':raw['frameZeroDescription']='Kiko holds a normal hammer beside the wall.'
            if case=='mutate-rule':raw['impossibleRule']='Every hammer strike now straightens the nail into the wall.'
            if case=='mutate-trigger':raw['visibleTrigger']='Kiko whistles at the nail.'
            if case=='reset':raw['beats'][0]['strategy']='Kiko resets the nail to normal straight form before starting again.'
            if case=='payoff-magic':raw['beats'][-1]['visibleConsequence']='The hammer becomes a mirror and shows the picture frame.';raw['finalPayoff']=raw['beats'][-1]['visibleConsequence']
            analysis=stage.analyze_expansion(json.dumps({'ideas':[raw]}),frozen,config,bspec['prompt'])
            expansions.append(dict(case=case,status=analysis['status'],drift=analysis['drift'],pipelineRan=analysis['pipelineRan'],findings=analysis.get('findings',[])))
        artifacts={'opening-seed-schema.json':stage.seed_response_format(),'phase-a-request.json':spec,'phase-b-mock-request.json':bspec,
                   'mock-phase-a-results.json':results,'mock-phase-b-results.json':expansions,'provenance-model.json':stage.SeedProvenance.model_json_schema(),
                   'offline-summary.json':dict(providerCalls=0,renders=0,networkAndSubprocessBlocked=True,seedMocks=len(results),expansionMocks=len(expansions),gateFloor=60)}
        for name,value in artifacts.items():(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False))
        (OUT/'phase-a-prompt-exact.txt').write_text(spec['prompt']['system']);(OUT/'phase-b-prompt-exact.txt').write_text(bspec['prompt']['system'])
        print(json.dumps(artifacts['offline-summary.json']));return
    if RUN.exists():parser.error('Experiment already claimed; no retries/resume/replacement/additional seeds')
    proof=json.loads((OUT/'pre-live-verification.json').read_text())
    if not proof.get('noNewFailures') or not proof.get('schemaIntegrityPassed'):parser.error('Offline regression/schema verification required')
    for group in ('protectedHashes','sourceHashes'):
        for path,sha in proof[group].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:parser.error('Changed since verification: '+path)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    auth=OUT/'authorization.txt'
    result=experiment.execute(RUN,config,cast,selected,authorization=dict(file=str(auth),sha256=hashlib.sha256(auth.read_bytes()).hexdigest()),tests={k:v for k,v in proof.items() if k!='protectedHashes'})
    print(json.dumps(dict(status=result['status'],selectedOpeningSeedId=result['selectedOpeningSeedId'],metrics=result['metrics']),indent=2))


if __name__=='__main__':main()
