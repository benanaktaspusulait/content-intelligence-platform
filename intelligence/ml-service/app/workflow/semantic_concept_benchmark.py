"""Mock-only architecture comparison; no semantic quality or vendor capability inference."""

from collections import Counter

from . import creative_shape as shape


def compare_runs(runs):
    stages = {}
    for label, run in runs.items():
        ideas = [r["candidate"] for r in run["candidates"]]
        attempts = run.get("attempts", run["candidates"])
        semantic = run.get("generationEvidence", {}).get("semantic") or {}
        scores = [r["validation"]["shortFormScore"] for r in run["candidates"]]
        received = semantic.get("receivedRawCount", 0)
        stages[label] = dict(
            rawNormalizedCount=len(attempts),
            schemaValidYield=semantic.get("schemaValidCount", 0) / received if received else None,
            validCandidateYield=sum(
                not [
                    code
                    for code in r.get("selectionBlockReasons", [])
                    if code not in ("STORY_SHAPE_DISTANCE_CAPACITY", "REQUESTED_COUNT_REACHED")
                ]
                for r in attempts
            )
            / len(attempts)
            if attempts
            else None,
            finalCandidateCount=len(ideas),
            meanShortFormScore=sum(scores) / len(scores) if scores else None,
            **shape.batch_metrics(ideas),
            templateShapeRiskDistribution=dict(Counter(c["templateShapeRisk"]["risk"] for c in ideas)),
            productionSlateSize=len(run["top3ProductionCandidates"]),
            sourceDistribution=run["generationEvidence"]["sourceDistribution"],
        )
    return dict(
        stages=stages,
        externalProviderCalls=0,
        paidEvaluations=0,
        limitations=[
            (
                "Authored mock fixtures validate architecture, not semantic "
                "superiority, model performance or retention."
            ),
            (
                "Final score/yield are conditional on unchanged deterministic "
                "quality floors. Source pools and sizes differ."
            ),
            (
                "Novel transfer ideas can pass naturalness/shape analysis while "
                "remaining canonical revisions because accepted language coverage "
                "is limited."
            ),
            "Human inspection/approval is required before prompt generation or rendering.",
        ],
    )
