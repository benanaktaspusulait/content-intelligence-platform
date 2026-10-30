#!/usr/bin/env python3
"""Plan missing cross-cases D/E; explicit maximum2 requests,no creative pipeline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-live',action='store_true')
    p.add_argument('--verification',type=Path);p.add_argument('--authorization',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-provider-contract-decomposition-v1-run-001')
    args=p.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow.creative_provider_profiles import profile
    from app.workflow import semantic_contract_decomposition_v1 as d
    stored_c=json.loads((ROOT/'intelligence/docs/semantic-provider-transport-isolation-v1-run-001/probe-c/request.json').read_text())
    specs,structure=d.plan(stored_c)
    if not args.execute_live:
        print(json.dumps(dict(CMetrics=d.request_metrics(stored_c['arguments']),DMetrics=specs['D']['metrics'],EMetrics=specs['E']['metrics'],structure=structure),indent=2));return 0
    if not args.verification or not args.authorization:p.error('Completed tests and explicit authorization required')
    tests=json.loads(args.verification.read_text())
    for file,sha in tests['sourceHashes'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=sha:p.error('Source changed after tests')
    result=d.execute(args.output,profile('openai-escalation'),stored_c,authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),tests=tests)
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
