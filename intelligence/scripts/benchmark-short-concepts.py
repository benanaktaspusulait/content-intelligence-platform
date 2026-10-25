#!/usr/bin/env python3
"""Compare deterministic local V1/V2 generation without providers or renders."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml-service"))
from app.workflow.short_concept_benchmark import benchmark


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    try:
        print(json.dumps(benchmark(args.seed, args.count), indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError) as error:
        print(f"Benchmark input error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
