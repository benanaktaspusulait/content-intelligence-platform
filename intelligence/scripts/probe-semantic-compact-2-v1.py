#!/usr/bin/env python3
"""Offline audit by default; one authorized LOW probe after completed regression."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
DOCS=ROOT/'intelligence/docs';OUT=DOCS/'semantic-prompt-v2-compact-2-v1';RUN=DOCS/'semantic-compact-2-low-probe-1-run-001'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-live',action='store_true');a=p.parse_args()
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    if not a.execute_live:
        def offline_guard(event,args):
            if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
                raise RuntimeError('Offline audit forbids external calls and subprocesses')
        sys.addaudithook(offline_guard)
    from app.workflow import semantic_compact_2_probe_v1 as probe
    from app.workflow.creative_provider_profiles import profile
    from app.workflow.semantic_concept_prompt_v2_compact_2 import Compact2PromptRequest
    from app.workflow.semantic_concept_prompt_v2_compact import size_metrics
    from app.workflow.semantic_prompt_v2_experiment import analyze
    cfg=profile('openai-escalation')
    high=json.loads((DOCS/'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    low=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    compact1=json.loads((DOCS/'semantic-compact-1-low-probe-1-run-001/request-before-sdk.json').read_text())
    spec,selected=probe.plan(cfg,high,low,compact1)
    if not a.execute_live:
        OUT.mkdir(parents=True,exist_ok=True)
        old=probe.prior.plan(cfg,high,low)[0]['prompt'];new=spec['prompt']
        sizes={}
        for label,pr in [('v2-compact.1',old),('v2-compact.2',new)]:
            sizes[label]={part:size_metrics(text) for part,text in dict(system=pr['system'],user=pr['prompt'],totalText=pr['system']+'\n'+pr['prompt']).items()}
        sizes['deltaPercent']={part:100*(sizes['v2-compact.2'][part]['characters']/sizes['v2-compact.1'][part]['characters']-1) for part in ('system','user','totalText')}
        assert all(value<=10 for value in sizes['deltaPercent'].values())
        fixture=ROOT/'intelligence/ml-service/tests/fixtures'
        policy=json.loads((fixture/'semantic_prompt_v2_compact_2_policy.json').read_text())
        cases=json.loads((fixture/'semantic_prompt_v2_compact_2_mocks.json').read_text())
        config=Compact2PromptRequest.model_validate(spec['configuration']);results=[]
        for case in cases['cases']:
            replay=analyze(json.dumps({'ideas':[case['raw']]}),config,new)
            r=replay['allRawIdeas'][0]['record']
            results.append(dict(case=case['case'],purpose=case['purpose'],editorialPromptIntent=case['editorialIntent'],scope=case['scope'],
                openingScore=r['observation']['openingScore'],ruleConsistency=r['observation']['ruleConsistency'],admission=r['admission']['status'],
                payoffRuleLinked=r['observation']['payoffRuleLinked'],providerCallsDuringAnalysis=replay['providerCallsDuringAnalysis'],
                qualification='Editorial intent is not a new runtime judge. Existing judge replay tests source constraints; it does not test a model following this prompt.'))
        artifacts={'offline-native-request.json':spec,'prompt.json':new,'sizes.json':sizes,'policy-equivalence.json':policy,
                   'adversarial-results.json':dict(cases=results,providerCalls=0,renders=0,networkBlocked=True),
                   'request-diff.json':spec['requestDiff']}
        for name,value in artifacts.items():(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False))
        (OUT/'prompt-exact.txt').write_text(new['system'])
        print(json.dumps(dict(providerCalls=0,renders=0,systemCharacters=sizes['v2-compact.2']['system']['characters'],deltaPercent=sizes['deltaPercent'],policyGroups=len(policy['requirements']),mockCases=len(results))))
        return
    if RUN.exists():p.error('Experiment already claimed; no second call, retry or replacement')
    evidence=json.loads((OUT/'pre-live-verification.json').read_text())
    if not evidence.get('noNewFailures') or not evidence.get('schemaIntegrityPassed'):p.error('Offline regression/schema proof required')
    for group in ('sourceHashes','protectedHashes'):
        for path,sha in evidence[group].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:p.error('Changed since tests: '+path)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    auth=OUT/'authorization.txt'
    result=probe.execute(RUN,cfg,high,low,compact1,authorization=dict(file=str(auth),sha256=hashlib.sha256(auth.read_bytes()).hexdigest()),
                         tests={k:v for k,v in evidence.items() if k!='protectedHashes'})
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
