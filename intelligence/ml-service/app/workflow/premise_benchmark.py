"""Read-only A/B/C comparison; retrospective annotations never replace frozen scores."""

from copy import deepcopy

from . import beat_grammar as beats
from . import premise_naturalness as gate
from .premise_generation import premise_metrics


def compare_runs(original, beat_run, gated):
    result = {}
    for name, run in (
        ("A_originalV2", original),
        ("B_beatGrammarV2", beat_run),
        ("C_premiseNaturalnessV1", gated),
    ):
        candidates = [deepcopy(r["candidate"]) for r in run["candidates"]]
        for c in candidates:
            c["premiseNaturalness"] = gate.assess(c)
        beat_candidates = (
            [beats.annotate_legacy(c) for c in candidates] if name.startswith("A_") else candidates
        )
        bm = beats.batch_evidence(beat_candidates)
        scores = [
            r["validation"]["shortFormScore"]
            for r in run["candidates"]
            if r.get("validation") and r["validation"].get("shortFormScore") is not None
        ]
        result[name] = {
            "eligibilityYield": sum(r["disposition"] == "ELIGIBLE" for r in run["candidates"])
            / len(candidates),
            "averageShortFormScore": sum(scores) / len(scores),
            **{k: v for k, v in bm.items() if "Diversity" in k},
            **premise_metrics(candidates),
            "top3ProductionSlateSize": len(run["top3ProductionCandidates"]),
            "annotationProvenance": "RETROSPECTIVE_NON_CANONICAL_ON_COPIES"
            if not name.startswith("C_")
            else "NEW_RUN_NON_CANONICAL",
        }
    return {
        "seed": gated["seed"],
        "requestedCount": gated["generationConfig"]["count"],
        "runs": result,
        "limitations": [
            (
                "A/B naturalness annotations and A beat annotations are newly "
                "computed on stored copies; historical scores and selections remain unchanged."
            ),
            (
                "Curated coverage and filtering mechanically increase "
                "admitted-premise metrics; this is not independent creative-quality validation."
            ),
            (
                "Object specificity tests functional-family dependence over 13 "
                "configured comparison archetypes, not unique-object originality."
            ),
            "No audience, retention, rendering or overall creative-superiority inference is supported.",
        ],
    }
