#!/usr/bin/env python3
"""Replay the immutable run-oT9HS7 provider responses without network access."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


def digest(value):
    raw=value if isinstance(value,bytes) else value.encode()
    return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--offline-real-response-replay',action='store_true',required=True)
    parser.add_argument('--evidence-dir',type=Path)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[2]
    venv_python=repo/'intelligence/ml-service/.venv/bin/python'
    if venv_python.is_file() and not os.environ.get('POMPOM_OFFLINE_REPLAY_BOOTSTRAPPED'):
        os.environ['POMPOM_OFFLINE_REPLAY_BOOTSTRAPPED']='1'
        os.execv(str(venv_python),[str(venv_python),str(Path(__file__).resolve()),*sys.argv[1:]])
    evidence=args.evidence_dir or repo/'intelligence/backend/target/disposable-owner-http/run-oT9HS7/real-execution-runtime'
    required=['run-a-final.json','run-b-final.json','deepseek-raw-structured-decision.json','openai-raw-structured-decision.json','experiment-summary.json']
    missing=[name for name in required if not (evidence/name).is_file()]
    if missing:raise SystemExit('Missing authoritative evidence: '+', '.join(missing))
    os.environ.setdefault('POMPOM_DATA_ROOT',str(repo/'intelligence/data'))
    sys.path.insert(0,str(repo/'intelligence/ml-service'))
    os.chdir(repo/'intelligence/ml-service')
    from app.workflow.creative_reconstruction import perform_reconstruction, request_payload
    from app.workflow.optimization_loop import generation_context, evaluate, fingerprint

    run_a=json.loads((evidence/'run-a-final.json').read_text())
    run_b=json.loads((evidence/'run-b-final.json').read_text())
    raws={
        'deepseek':(evidence/'deepseek-raw-structured-decision.json').read_text(),
        'openai':(evidence/'openai-raw-structured-decision.json').read_text(),
    }
    # Pretty-printed evidence is compared semantically and against the exact raw
    # response stored in the durable request envelope.
    for label,run in [('deepseek',run_a),('openai',run_b)]:
        exact=run['requests'][0]['response']['rawResponse']
        if json.loads(raws[label])!=json.loads(exact):raise SystemExit(label+' evidence differs from durable raw response')
        raws[label]=exact
    scope=run_a['scope'];source=scope['baselinePrompt']
    if fingerprint(source)!='1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5':
        raise SystemExit('Baseline fingerprint mismatch')
    baseline=(run_a['progress'].get('baselineEvaluation') or run_a['progress']['bestEvaluation'])['canonical']
    context=generation_context(scope,source,baseline,{})

    class ReplayProvider:
        external_dispatches=0
        def __init__(self,raw):self.raw=raw;self.calls=0
        def complete(self,*args,**kwargs):self.calls+=1;return self.raw

    results={}
    for label in ('deepseek','openai'):
        provider=ReplayProvider(raws[label])
        try:
            value=perform_reconstruction(source,context,provider,'saved-real-'+label+'-offline-replay')
            results[label]={'status':'ACCEPTED' if value['result']['candidates'] else 'REJECTED','pipeline':value['result']}
        except Exception as error:
            results[label]={'status':'BLOCKED','exception':type(error).__name__+': '+str(error)}
        results[label]['offlineResponseReads']=provider.calls
        results[label]['externalProviderDispatches']=provider.external_dispatches
        results[label]['rawResponseSha256']=digest(raws[label])

    accepted=results['openai'].get('pipeline',{}).get('candidates',[])
    if accepted:
        candidate=accepted[0]
        provenance={'origin':'REAL_AI_PROVIDER','provider':'openai','model':'gpt-6.1-sol',
            'requestFingerprint':run_b['requests'][0]['requestId'],
            'responseFingerprint':results['openai']['rawResponseSha256'],
            'reviewerOrigin':'UNKNOWN_ORIGIN','reviewerIndependent':False,
            'evaluatorVersion':'creative-validity-v1'}
        with patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('offline replay forbids provider construction')):
            assessment=evaluate({'scope':scope,'prompt':candidate['prompt'],'provenance':provenance})
        results['openai'].update(candidatePrompt=candidate['prompt'],candidateSha256=digest(candidate['prompt']),
            profileValidation=candidate['profileValidation'],productionProvenance=candidate.get('productionProvenance'),
            canonical=assessment['canonical'],creativeValidity=assessment['creativeValidity'],
            integrity=assessment['integrity'])
        (evidence/'openai-offline-accepted-research-candidate.txt').write_text(candidate['prompt']+'\n')
    payload=request_payload(source,context)
    output={'version':'offline-real-response-replay-v1','authoritativeEvidenceDirectory':str(evidence),
        'baselinePromptSha256':digest(source),'baselineCanonical':{'rulesetVersion':'1.11','score':baseline['score'],'grade':baseline['grade']},
        'rawResponseFingerprints':{key:results[key]['rawResponseSha256'] for key in results},
        'results':results,'opportunityInventory':payload['creativeDiagnosis']['creativePriorityAudit'],
        'rankedActionableOpportunities':payload['creativeDiagnosis']['opportunities'],
        'externalProviderDispatches':0,'newProviderSpendUsd':0,'sourceStoryChanged':False,
        'baselinePromptChanged':False,'rulesetChanged':False,'renderAuthorized':False,'promptApprovalAllowed':False}
    target=evidence/'offline-real-response-replay.json';target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(target),'deepseek':results['deepseek']['status'],'openai':results['openai']['status'],
        'openaiScore':results['openai'].get('canonical',{}).get('score'),'openaiGrade':results['openai'].get('canonical',{}).get('grade'),
        'externalProviderDispatches':0,'newProviderSpendUsd':0},ensure_ascii=False))
    return 0 if results['openai']['status']=='ACCEPTED' and results['deepseek']['status']=='REJECTED' else 2


if __name__=='__main__':raise SystemExit(main())
