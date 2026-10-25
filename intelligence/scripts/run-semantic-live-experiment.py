#!/usr/bin/env python3
"""Explicit experiment CLI. Default is a network-free plan; replay is also offline."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--allow-external-generation", action="store_true")
    parser.add_argument("--replay", type=Path)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/semantic-live-v1-seed-42-count-40"
    )
    args = parser.parse_args(argv)
    from app.workflow.semantic_concept_generation import GenerationRequest
    from app.workflow.semantic_live_experiment import execute, plan, replay, write_new

    baseline = json.loads(
        (ROOT / "docs/creative-shape-v1/experiment-seed-42-count-20.json").read_text()
    )
    if args.replay:
        if args.execute_live or args.allow_external_generation:
            parser.error("Replay cannot authorize live generation")
        stored = args.replay
        cfg = json.loads((stored / "configuration.json").read_text())
        result = replay(
            (stored / "response.txt").read_text(),
            GenerationRequest.model_validate(cfg["generation"]),
            json.loads((stored / "prompt.json").read_text()),
            baseline,
        )
        args.output.mkdir(parents=True, exist_ok=True)
        write_new(args.output / "replay-analysis.json", result)
        print(json.dumps({"status": "REPLAYED", "providerCalls": 0}))
        return 0
    # Existing .env mechanism is only loaded by explicit CLI invocation, never import/tests.
    from dotenv import load_dotenv

    load_dotenv(ROOT / "ml-service/.env", override=False)
    os.environ.setdefault("POMPOM_DATA_ROOT", str(ROOT / "data"))
    from app.workflow.creative_provider_profiles import profile

    configuration = profile("deepseek-primary")
    if not args.execute_live:
        print(json.dumps(plan(configuration), indent=2))
        return 0
    if not args.allow_external_generation:
        parser.error("--execute-live also requires --allow-external-generation")
    metadata = execute(
        args.output, configuration, baseline, allow_external_generation=True
    )
    print(json.dumps(metadata, indent=2))
    return 0 if metadata["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
