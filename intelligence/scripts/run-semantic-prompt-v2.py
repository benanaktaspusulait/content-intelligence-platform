#!/usr/bin/env python3
"""V2 plan by default, explicit single live request, or stored offline analysis."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-live',action='store_true')
    p.add_argument('--allow-external-generation',action='store_true')
    p.add_argument('--test-verification',type=Path)
    p.add_argument('--authorization-file',type=Path)
    p.add_argument('--replay',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'intelligence/docs/semantic-live-v2-count-40-run-001')
    args=p.parse_args(argv)
    from app.workflow.semantic_prompt_v2_experiment import execute,plan,analyze,all_ideas_text,review_cards
    from app.workflow.semantic_concept_prompt_v2 import PromptV2Request
    from app.workflow.semantic_live_experiment import write_new
    if args.replay:
        if args.execute_live or args.allow_external_generation:p.error('Replay cannot authorize live requests')
        attempt=args.replay
        cfg=PromptV2Request.model_validate(json.loads((attempt/'configuration.json').read_text())['generation'])
    else:
        from dotenv import load_dotenv
        load_dotenv(ROOT/'intelligence/ml-service/.env',override=False)
        os.environ.setdefault('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
        from app.workflow.creative_provider_profiles import profile
        profile_data=profile('deepseek-primary')
        if not args.execute_live:
            print(json.dumps(plan(profile_data),indent=2));return 0
        if not args.allow_external_generation or not args.test_verification or not args.authorization_file:
            p.error('Live execution requires explicit authorization and completed test evidence')
        verification=json.loads(args.test_verification.read_text())
        for file,sha in verification['sourceHashes'].items():
            if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=sha:
                p.error('Source changed since completed tests; no request attempted')
        evidence={**verification,'verificationSha256':hashlib.sha256(args.test_verification.read_bytes()).hexdigest()}
        metadata=execute(args.output,profile_data,allow_external_generation=True,
            authorization=dict(file=str(args.authorization_file.resolve()),sha256=hashlib.sha256(args.authorization_file.read_bytes()).hexdigest()),
            test_evidence=evidence)
        print(json.dumps(metadata,indent=2),flush=True)
        attempt=args.output/'live-attempt'
        if metadata['status']!='COMPLETED':return 1
        cfg=PromptV2Request.model_validate(json.loads((attempt/'configuration.json').read_text())['generation'])
    # Analysis cannot construct a provider. Deny all subsequent network and subprocess use.
    def guard(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
            raise RuntimeError('Offline V2 analysis forbids network/subprocesses')
    sys.addaudithook(guard)
    out=args.output if args.replay else args.output/'offline-analysis'
    out.mkdir(parents=True,exist_ok=False)
    raw=(attempt/'response.txt').read_text();prompt=json.loads((attempt/'prompt.json').read_text())
    try:
        result=analyze(raw,cfg,prompt)
        write_new(out/'results.json',result)
        write_new(out/'all-raw-ideas.txt',all_ideas_text(result),raw=True)
        write_new(out/'human-review-cards.json',review_cards(result))
        write_new(out/'analysis-status.json',dict(status='COMPLETED',providerCalls=0,renders=0,metrics=result['metrics']))
    except Exception as error:
        write_new(out/'analysis-status.json',dict(status='FAILED',errorType=type(error).__name__,error=str(error),providerCalls=0,renders=0))
        raise
    write_new(out/'manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps(result['metrics'],indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
