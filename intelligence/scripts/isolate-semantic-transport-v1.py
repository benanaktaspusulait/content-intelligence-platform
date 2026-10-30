#!/usr/bin/env python3
"""Plan diagnostics by default; execute A/B/C until first failure only."""
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
    p.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-provider-transport-isolation-v1-run-001')
    args=p.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow.creative_provider_profiles import profile
    from app.workflow import semantic_transport_isolation_v1 as isolation
    configuration=profile('openai-escalation');specs=isolation.plan(configuration)
    previous=json.loads((ROOT/'intelligence/docs/semantic-provider-openai-gpt-6-1-sol-probe-5-run-001/request.json').read_text())
    static=dict(planned={k:s['metrics'] for k,s in specs.items()},previousFailed5=dict(
        metrics=isolation.request_metrics(previous['arguments']),candidateCount=5,timeout=previous['timeout']))
    if not args.execute_live:
        print(json.dumps(static,indent=2));return 0
    if not args.verification or not args.authorization:p.error('Completed tests and explicit authorization required')
    verified=json.loads(args.verification.read_text())
    for file,sha in verified['sourceHashes'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=sha:p.error('Source changed after tests')
    # All static metrics are materialized in memory before the first request; exact snapshots are written by execute().
    result=isolation.execute(args.output,configuration,authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),tests=verified)
    from app.workflow.semantic_live_experiment import write_new
    write_new(args.output/'static-comparison.json',static)
    def guard(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('Offline diagnosis only; no repair/fallback')
    sys.addaudithook(guard)
    try:secondary=isolation.validate_c_offline(args.output)
    except Exception as error:secondary=dict(status='FAILED_SECONDARY_ANALYSIS',errorClass=type(error).__name__)
    write_new(args.output/'secondary-analysis.json',secondary)
    print(json.dumps(dict(summary=result,secondary=secondary),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
