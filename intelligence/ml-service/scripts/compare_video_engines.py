#!/usr/bin/env python3
"""Run the immutable v3 and selectable v4 analyzers side by side for local diagnostics."""

import argparse
import json
from pathlib import Path

from app.video import analyse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Paths relative to POMPOM_DATA_ROOT")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    rows = []
    for path in args.paths:
        v3 = analyse(path, "sampled-visual-motion-v3")
        v4 = analyse(path, "sampled-visual-motion-v4")
        profile = v4.evidence["temporalProfile"]
        novelty = v4.evidence["visualNovelty"]
        repetition = v4.evidence["repetitiveMotion"]
        rows.append({
            "video": path,
            "durationSeconds": v4.metadata.duration_ms / 1000,
            "v3MotionScore": v3.motion_heuristic_score,
            "v3OverallMotion": v3.motion.get("overallMotionIntensity"),
            "v3Density": v3.motion.get("motionIntervalDensity"),
            "v4MotionIntensity": profile.get("overallMotion"),
            "v4TemporalConsistency": profile.get("variation"),
            "largestTroughDuration": max((item.get("durationSeconds", 0) for item in profile.get("troughs", [])), default=0),
            "averageVisualNovelty": novelty.get("averageNovelty"),
            "repetitiveRegionCandidate": repetition.get("repeatedPatternCandidate"),
            "statePersistence": 1 - novelty.get("averageNovelty", 0),
            "plannedActionDiversity": "NOT_EVALUATED",
            "fidelity": "NOT_EVALUATED",
        })
    output = json.dumps(rows, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
