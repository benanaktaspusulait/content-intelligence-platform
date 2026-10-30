#!/usr/bin/env python3
"""Offline plan by default; explicit authorized single compact capability probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
RUN=ROOT/'intelligence/docs/semantic-compact-full-contract-probe-1-run-001'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live',action='store_true');parser.add_argument('--verification',type=Path);parser.add_argument('--authorization',type=Path)
    args=parser.parse_args(argv)
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow import semantic_compact_capability_probe_v1 as probe
    from app.workflow.creative_provider_profiles import profile
    p=profile('openai-escalation');spec=probe.plan(p)
    if not args.execute_live:
        print(json.dumps(dict(execution='OFFLINE_PLAN_ONLY',promptHash=probe.PROMPT_HASH,schemaHash=probe.SCHEMA_HASH,metrics=spec['metrics'],timeout=spec['timeout'],maximumRequests=1,providerCalls=0),indent=2));return 0
    if RUN.exists():parser.error('Durable experiment claim already exists; never execute a replacement or retry')
    if not args.verification or not args.authorization:parser.error('Completed tests and explicit authorization required')
    tests=json.loads(args.verification.read_text())
    if not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed'):parser.error('Regression/schema preflight must pass first')
    for path,sha in tests['sourceHashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:parser.error('Source changed after tests')
    for path,sha in tests['protectedHashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:parser.error('Accepted source or evidence changed after tests')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    result=probe.execute(RUN,p,authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),tests={k:v for k,v in tests.items() if k!='protectedHashes'})
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
