#!/usr/bin/env python3
"""Frozen micro-batch. Live execution requires completed preflight; no resumption."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
DOCS=ROOT/'intelligence/docs'
EVIDENCE=DOCS/'semantic-compact-micro-batch-v1'
RUN=DOCS/'semantic-compact-micro-batch-v1-run-001'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-live',action='store_true')
    a=p.parse_args()
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow import semantic_compact_micro_batch_v1 as batch
    from app.workflow.creative_provider_profiles import profile
    configuration=profile('openai-escalation')
    prior=json.loads((DOCS/'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    accepted=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    if not a.execute_live:
        print(json.dumps(batch.plan(configuration,prior,accepted),indent=2));return
    if RUN.exists():p.error('Batch already claimed; no retry/resume/fourth request')
    tests=json.loads((EVIDENCE/'pre-live-verification.json').read_text())
    if not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):p.error('Offline verification required')
    for group in ('sourceHashes','protectedHashes'):
        for path,sha in tests[group].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:p.error('Source/evidence changed since verification: '+path)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    if not os.getenv('OPENAI_API_KEY'):p.error('Credential unavailable; no requests')
    auth=EVIDENCE/'authorization.txt'
    result=batch.execute(RUN,configuration,prior,accepted,
        DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/inspection.json',
        authorization=dict(file=str(auth),sha256=hashlib.sha256(auth.read_bytes()).hexdigest()),
        tests={k:v for k,v in tests.items() if k!='protectedHashes'})
    print(json.dumps({k:v for k,v in result.items() if k!='candidates'},indent=2))


if __name__=='__main__':main()
