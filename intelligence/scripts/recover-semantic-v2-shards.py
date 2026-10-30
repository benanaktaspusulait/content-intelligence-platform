#!/usr/bin/env python3
"""Plan only by default; explicit tested two-shard recovery or network-free replay."""
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
    p.add_argument('--replay',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-live-v2-count-40-run-001-recovery-001')
    args=p.parse_args(argv)
    from app.workflow import semantic_v2_sharded_recovery as recovery
    if args.replay and args.execute_live:p.error('Replay cannot authorize requests')
    if not args.replay:
        from dotenv import load_dotenv
        load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
        os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
        from app.workflow.creative_provider_profiles import profile
        prof=profile('deepseek-primary')
        if not args.execute_live:
            print(json.dumps(dict(experimentId=recovery.EXPERIMENT_ID,provider=prof['provider'],model=prof['model'],
                shards=['A','B'],rawPerShard=20,maximumRequests=2,maxOutputTokens=recovery.OUTPUT_TOKENS,timeout=recovery.TIMEOUT,sdkMaxRetries=0),indent=2));return 0
        if not args.verification or not args.authorization:p.error('Completed test proof and explicit authorization required')
        verified=json.loads(args.verification.read_text())
        for file,sha in verified['sourceHashes'].items():
            if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=sha:p.error('Source changed since tests')
        recovery.execute_two(args.output,prof,authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),test_evidence=verified)
    # All source reads/replays and combined judgments below have no transport.
    def guard(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('Offline analysis only')
    sys.addaudithook(guard)
    directory=args.replay or args.output
    result=recovery.analyze_combined(directory)
    print(json.dumps(result.get('metrics',result),indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
