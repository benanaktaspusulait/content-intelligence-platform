#!/usr/bin/env python3
"""Plan/validate offline by default; at most one corrected minimal-E live probe."""
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
    p.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-native-schema-integrity-probe-1-run-001')
    args=p.parse_args(argv)
    from app.workflow import semantic_schema_integrity_probe_v1 as probe
    e=json.loads((ROOT/'intelligence/docs/semantic-provider-contract-decomposition-v1-run-001/probe-e/request.json').read_text())
    if not args.execute_live:
        print(json.dumps(probe.plan(e),indent=2));return 0
    if not args.verification or not args.authorization:p.error('Completed integrity/tests and explicit authorization required')
    tests=json.loads(args.verification.read_text())
    for file,sha in tests['sourceHashes'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=sha:p.error('Source changed after tests')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow.creative_provider_profiles import profile
    result=probe.execute(args.output,profile('openai-escalation'),e,
        authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),tests=tests)
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
