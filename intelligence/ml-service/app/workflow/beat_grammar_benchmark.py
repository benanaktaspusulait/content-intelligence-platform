"""Compare stored runs. Legacy beat annotations are explicitly approximate, not frozen scores."""

from copy import deepcopy
from . import beat_grammar as bg


def compare_runs(old_run, new_run):
    legacy = [bg.annotate_legacy(r["candidate"]) for r in old_run["candidates"]]
    old_metrics = bg.batch_evidence(legacy)
    old_metrics.update(
        eligibilityYield=old_run["generatorMetrics"]["eligibilityYield"],
        averageShortFormScore=old_run["generatorMetrics"]["averageShortFormScore"],
        acceptedProductionRiskRate=old_run["generatorMetrics"]["productionRiskRate"],
        top3CreativeDistance=old_run["generatorMetrics"]["top3PairwiseCreativeDistance"],
    )
    return {
        "seed": new_run["seed"],
        "requestedCount": new_run["generationConfig"]["count"],
        "oldV2": old_metrics,
        "newV2WithBeatGrammar": deepcopy(new_run["beatGrammarMetrics"]),
        "top3BeatGrammar": bg.batch_evidence([s["candidate"] for s in new_run["top3ProductionCandidates"]]),
        "limitations": [
            "Old V2 beat metrics are new conservative annotations of stored text, not historical canonical scores. Coverage differs from structured-first plans.",
            "High structured diversity can coexist with poor prose, low accepted eligibility or repeated choreography. These metrics do not establish creative success.",
            "Scores and selections from old V2 are read only. No tuning, provider calls or renders.",
        ],
    }
