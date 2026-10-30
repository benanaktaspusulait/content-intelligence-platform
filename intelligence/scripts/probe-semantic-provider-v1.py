#!/usr/bin/env python3
"""Discover/plan by default; one explicitly authorized DeepSeek5 probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-live',action='store_true')
    parser.add_argument('--verification',type=Path);parser.add_argument('--authorization',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-provider-execution-benchmark-v1/probe-deepseek-5-run-001')
    args=parser.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow.creative_provider_profiles import profile,profiles
    from app.workflow import semantic_provider_execution_benchmark_v1 as b
    discovery=b.discovery(profiles())
    if not args.execute_live:
        print(json.dumps(discovery,indent=2));return 0
    if not args.verification or not args.authorization:parser.error('Completed tests and explicit authorization required')
    tests=json.loads(args.verification.read_text())
    for path,sha in tests['sourceHashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:parser.error('Source changed after tests')
    record=b.execute(args.output,profile('deepseek-primary'),authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),tests=tests)
    from app.workflow.semantic_live_experiment import write_new
    write_new(args.output/'provider-discovery.json',discovery)
    def guard(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('Offline analysis only; no fallback')
    sys.addaudithook(guard)
    try:analysis=b.analyze_probe(args.output)
    except Exception as error:analysis=dict(status='FAILED_OFFLINE_VALIDATION',errorClass=type(error).__name__,safeError=str(error),creativeQualityConclusion=None)
    write_new(args.output/'analysis-status.json',analysis)
    print(json.dumps(dict(benchmark=record,offline=analysis),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
