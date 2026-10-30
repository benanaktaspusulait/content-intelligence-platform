#!/usr/bin/env python3
"""One explicit OpenAI5 capability probe; never fallback to DeepSeek."""
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
    p.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-provider-openai-gpt-6-1-sol-probe-5-run-001')
    args=p.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
    os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    from app.workflow.creative_provider_profiles import profile
    from app.workflow import semantic_provider_openai_probe_v1 as probe
    configuration=profile('openai-escalation')
    if not args.execute_live:
        print(json.dumps(dict(attemptId=probe.ATTEMPT_ID,provider=configuration['provider'],model=configuration['model'],count=5,
            responseMode=configuration['responseMode'],maxRequests=1,timeout=probe.TIMEOUT,maxOutputTokens=probe.OUTPUT_TOKENS,streaming=False),indent=2));return 0
    if not args.verification or not args.authorization:p.error('Completed tests and explicit authorization required')
    tests=json.loads(args.verification.read_text())
    for file,sha in tests['sourceHashes'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=sha:p.error('Source changed after tests')
    result=probe.execute(args.output,configuration,authorization=dict(file=str(args.authorization.resolve()),sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()),tests=tests)
    def guard(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('Offline only; no repair or fallback')
    sys.addaudithook(guard)
    try:analysis=probe.analyze_stored(args.output)
    except Exception as error:analysis=dict(status='FAILED_OFFLINE_ANALYSIS',errorClass=type(error).__name__,safeError=str(error))
    from app.workflow.semantic_live_experiment import write_new
    write_new(args.output/'analysis-status.json',analysis)
    print(json.dumps(dict(benchmark=result,analysis=analysis),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
