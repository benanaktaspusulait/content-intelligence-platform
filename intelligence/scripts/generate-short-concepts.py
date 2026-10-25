#!/usr/bin/env python3
"""Generate local causal concepts; optionally apply accepted validation/ranking."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml-service"))
from app.workflow.semantic_concept_generation import generate_and_rank


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["deterministic", "semantic", "hybrid"], default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--allow-external-generation", action="store_true")
    parser.add_argument("--raw-count", type=int, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=16000)
    parser.add_argument("--creative-shape-version", choices=["v1"], default=None)
    parser.add_argument("--minimum-story-shape-distance", type=float, default=.22)
    parser.add_argument("--generator-version", choices=["v1", "v2"], default=None)
    parser.add_argument("--premise-naturalness-gate-version", choices=["v1"], default=None)
    parser.add_argument("--premise-pool-size", type=int, default=480)
    parser.add_argument("--beat-grammar-version", choices=["v2"], default=None)
    parser.add_argument("--internal-pool-size", type=int, default=240)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--duration", type=float, default=15)
    parser.add_argument("--rank", action="store_true")
    parser.add_argument("--character-id", action="append", default=[])
    parser.add_argument("--exclude-engine-family", action="append", default=[])
    parser.add_argument("--exclude-object", action="append", default=[])
    parser.add_argument("--exclude-object-category", action="append", default=[])
    parser.add_argument(
        "--cast-file", type=Path, help="Canonical id/name registry snapshot JSON array"
    )
    parser.add_argument("--text-report", action="store_true")
    args = parser.parse_args()
    try:
        config = {
            "count": args.count,
            "creativeShapeVersion": args.creative_shape_version,
            "minimumStoryShapeDistance": args.minimum_story_shape_distance,
            "premiseNaturalnessGateVersion": args.premise_naturalness_gate_version,
            "premisePoolSize": args.premise_pool_size,
            "beatGrammarVersion": args.beat_grammar_version,
            "generatorVersion": args.generator_version or ("v2" if args.mode else "v1"),
            "internalPoolSize": args.internal_pool_size,
            "seed": args.seed,
            "duration": args.duration,
            "rank": args.rank,
            "characterIds": args.character_id,
            "excludeEngineFamilies": args.exclude_engine_family,
            "excludeObjects": args.exclude_object,
            "excludeObjectCategories": args.exclude_object_category,
        }
        if args.mode:
            config.update(generatorMode=args.mode, allowExternalGeneration=args.allow_external_generation,
                          semanticRawCount=args.raw_count)
            for key, value in [("beatGrammarVersion", "v2"), ("premiseNaturalnessGateVersion", "v1"), ("creativeShapeVersion", "v1")]:
                if config["generatorVersion"] == "v2" and config[key] is None: config[key] = value
        if args.mock or args.provider or args.model:
            config["semanticProvider"] = {"provider": "mock" if args.mock else args.provider or "unconfigured",
                                          "model": args.model or "fixture-v1", "maxOutputTokens": args.max_output_tokens}
        if args.cast_file:
            config["canonicalCast"] = json.loads(args.cast_file.read_text())
        result = generate_and_rank(config)
        print(
            "\n".join(result["reportLines"])
            if args.text_report
            else json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        )
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Generation input error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
