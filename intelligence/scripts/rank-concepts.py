#!/usr/bin/env python3
"""Offline supplied-concept ranking CLI. No model calls or production writes."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml-service"))
from app.workflow.concept_ranking import rank_concepts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, help="JSON candidate/object/array/batch, or one labeled text concept"
    )
    parser.add_argument(
        "--text-report", action="store_true", help="Print the report projection rather than JSON"
    )
    args = parser.parse_args()
    try:
        text = args.input.read_text()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = text
        if isinstance(value, dict) and "candidates" in value:
            if set(value) != {"candidates"}:
                raise ValueError("Batch accepts only candidates")
            candidates = value["candidates"]
        else:
            candidates = value if isinstance(value, list) else [value]
        if not isinstance(candidates, list):
            raise ValueError("candidates must be an array")
        result = rank_concepts(candidates)
        print(
            "\n".join(result["reportLines"])
            if args.text_report
            else json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        )
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(f"Concept input error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
