"""Family 10 lossless Golden comparator, additive to the frozen Family 9 gate."""

from __future__ import annotations

from typing import Any


def compare_general_producibility(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Compare whole canonical projections, including nulls, reasons and provenance."""
    mismatches: list[dict[str, Any]] = []
    expected = snapshot.get("generalProducibility")
    sources = {
        "canonicalEvidence.generalProducibility": (snapshot.get("canonicalEvidence") or {}).get(
            "generalProducibility"
        ),
        "assessment.general_producibility": (snapshot.get("assessment") or {}).get("general_producibility"),
        "apiReport.pre_render_assessment.general_producibility": (
            (snapshot.get("apiReport") or {}).get("pre_render_assessment") or {}
        ).get("general_producibility"),
    }
    if not isinstance(expected, dict):
        mismatches.append({"path": "generalProducibility", "reason": "Canonical Family 10 evidence missing"})
    elif snapshot.get("status") == "OK":
        for path, actual in sources.items():
            if expected != actual:
                mismatches.append({"path": path, "expected": expected, "actual": actual})
    elif expected.get("status") != "UNKNOWN":
        mismatches.append(
            {"path": "generalProducibility.status", "reason": "Unavailable plan must remain UNKNOWN"}
        )
    return {"assetId": snapshot.get("goldenId"), "consistent": not mismatches, "mismatches": mismatches}
