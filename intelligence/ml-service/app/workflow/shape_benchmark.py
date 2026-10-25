"""Four saved-stage comparison; new annotations never replace historical scores."""

from . import creative_shape as shape
from .creative_distance import pairwise_summary


def compare_runs(runs):
    result = {}
    for name, run in runs.items():
        candidates = [r["candidate"] for r in run["candidates"]]
        slate = [r["candidate"] for r in run["top3ProductionCandidates"]]
        scores = [
            r["validation"]["shortFormScore"]
            for r in run["candidates"]
            if r.get("validation") and r["validation"].get("shortFormScore") is not None
        ]
        result[name] = {
            **shape.batch_metrics(candidates),
            **pairwise_summary(candidates),
            "eligibilityYield": sum(r["disposition"] == "ELIGIBLE" for r in run["candidates"])
            / len(candidates)
            if candidates
            else None,
            "averageShortFormScore": sum(scores) / len(scores) if scores else None,
            "finalCandidateCount": len(candidates),
            "productionSlateDiversity": {
                "size": len(slate),
                **shape.batch_metrics(slate),
                **pairwise_summary(slate),
            },
            "annotationProvenance": "NEW_NON_CANONICAL_RUN"
            if name.startswith("D")
            else "RETROSPECTIVE_NON_CANONICAL_ANNOTATION_ON_FROZEN_RUN",
        }
    return dict(
        stages=result,
        limitations=[
            (
                "Generator-controlled diagnostic improvements are expected after "
                "filtering and are not independent evidence of creative quality."
            ),
            (
                "A/B/C story-shape and territory metrics are new annotations of "
                "saved evidence, not historical canonical results; A uses "
                "conservative legacy text approximation."
            ),
            (
                "D preselects candidates using existing quality validators, while "
                "A/B/C retain low-quality outputs. Eligibility yield and mean "
                "score are selection-biased, not a controlled causal quality "
                "experiment."
            ),
            (
                "D can return fewer than requested; batch concentration "
                "denominators and null pairwise values are explicit."
            ),
            (
                "No new grammar stories, providers, audience tests, paid "
                "evaluations or media renders. Manual inspection remains required."
            ),
        ],
    )
