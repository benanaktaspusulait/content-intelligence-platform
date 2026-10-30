#!/usr/bin/env python3
"""One controlled low-effort request; offline comparison by default."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
RUN=ROOT/'intelligence/docs/semantic-low-reasoning-full-contract-probe-1-run-001'
PRIOR=ROOT/'intelligence/docs/semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-live',action='store_true');p.add_argument('--verification',type=Path);p.add_argument('--authorization',type=Path)
    a=p.parse_args(argv);os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow import semantic_low_reasoning_probe_v1 as probe
    from app.workflow.creative_provider_profiles import profile
    prior=json.loads(PRIOR.read_text());configuration=profile('openai-escalation');planned=probe.plan(configuration,prior)
    if planned['status']=='REASONING_EFFORT_NOT_CONTROLLABLE':print(json.dumps(planned,indent=2));return 0
    if not a.execute_live:
        print(json.dumps({k:planned[k] for k in ('status','previousReasoningEffort','selectedReasoningEffort','discovery','requestDiff','onlyReasoningChanged')},indent=2));return 0
    if RUN.exists():p.error('Experiment already claimed; no retry or second effort level')
    if not a.verification or not a.authorization:p.error('Completed verification and explicit authorization required')
    tests=json.loads(a.verification.read_text())
    if not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):p.error('Completed regression/schema evidence required')
    for group in ('sourceHashes','protectedHashes'):
        for path,sha in tests[group].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:p.error('Source or accepted evidence changed after tests')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    result=probe.execute(RUN,configuration,prior,authorization=dict(file=str(a.authorization.resolve()),sha256=hashlib.sha256(a.authorization.read_bytes()).hexdigest()),tests={k:v for k,v in tests.items() if k!='protectedHashes'})
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
