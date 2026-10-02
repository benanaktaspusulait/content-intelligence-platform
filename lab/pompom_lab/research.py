from __future__ import annotations

import json
import statistics
from datetime import date
from pathlib import Path
from typing import Any

from .database import Database


def update_findings(database: Database, output: Path, minimum_sample: int = 8) -> dict[str, Any]:
    proposed = 0
    with database.connect() as connection:
        for platform in ("instagram", "facebook", "tiktok"):
            rows = [dict(row) for row in connection.execute(
                """SELECT t.views,f.features_json FROM performance_trajectories t JOIN creative_fingerprints f ON f.video_id=t.video_id
                WHERE t.platform=? AND t.checkpoint_minutes=1440 AND t.views IS NOT NULL""", (platform,)
            )]
            if len(rows) < minimum_sample:
                continue
            high = [float(row["views"]) for row in rows if (json.loads(row["features_json"]).get("physical_action") or 0) >= .8]
            rest = [float(row["views"]) for row in rows if (json.loads(row["features_json"]).get("physical_action") or 0) < .8]
            if len(high) < 4 or len(rest) < 4:
                continue
            high_median, rest_median = statistics.median(high), statistics.median(rest)
            effect = high_median - rest_median
            statement = f"In the observed {platform} sample, videos with physical_action >= 0.8 had a {effect:+.0f} median 24h-view difference versus the remaining sample."
            evidence = {"high_n": len(high), "other_n": len(rest), "high_median": high_median, "other_median": rest_median, "effect": effect}
            duplicate = connection.execute("SELECT 1 FROM research_findings WHERE platform=? AND statement=?", (platform, statement)).fetchone()
            if not duplicate:
                connection.execute(
                    "INSERT INTO research_findings(scope,platform,statement,evidence_json,sample_size,confidence) VALUES('CREATIVE_FEATURE',?,?,?,?,?)",
                    (platform, statement, json.dumps(evidence), len(rows), "MEDIUM" if len(rows) >= 20 else "LOW"),
                )
                proposed += 1
        findings = [dict(row) for row in connection.execute("SELECT * FROM research_findings ORDER BY created_at,id")]
    lines = ["# Research Findings", "", "Observational findings only. These notes do not establish causality.", ""]
    if not findings:
        lines.extend(["No finding has met the configured evidence threshold yet.", ""])
    for finding in findings:
        evidence = json.loads(finding["evidence_json"])
        lines.extend([
            f"## {finding['created_at'][:10]} - {finding['platform'] or 'cross-platform'}",
            "",
            finding["statement"],
            "",
            f"- Sample: n={finding['sample_size']}",
            f"- Confidence: {finding['confidence']}",
            f"- Effect/evidence: `{json.dumps(evidence, sort_keys=True)}`",
            "- Limitation: observational platform data with possible series, timing, character, and channel-momentum confounding.",
            "",
        ])
    output.write_text("\n".join(lines), encoding="utf-8")
    return {"new_findings": proposed, "total_findings": len(findings), "output": str(output)}
