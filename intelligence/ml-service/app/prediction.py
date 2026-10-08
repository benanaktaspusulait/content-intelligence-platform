from typing import Any

from .contracts import LivePredictionRequest, PredictionRequest, PredictionResponse

HORIZONS = (30, 60, 120, 180, 360, 720, 1440, 2880, 10080)
BANDS = ("LOW", "PARTIAL", "MEANINGFUL_EXPANSION", "STRONG", "PERSISTENT", "BREAKOUT")
TRAJECTORIES = (
    "EARLY_STALL",
    "SLOW_GROWTH",
    "FAST_START_STALL",
    "SECOND_WAVE",
    "MULTI_WAVE",
    "PERSISTENT_GROWTH",
    "LATE_BREAKOUT",
)


def prepublish(request: PredictionRequest) -> PredictionResponse:
    if request.model_reference is not None:
        from .statistical_model import infer
        return PredictionResponse(**infer(request))
    targets: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        targets.append(
            {
                "horizonMinutes": horizon,
                "metric": "views",
                "expectedValue": None,
                "interval50": [None, None],
                "interval80": [None, None],
                "bandProbabilities": {band: round(1 / len(BANDS), 6) for band in BANDS},
                "trajectoryProbabilities": {label: round(1 / len(TRAJECTORIES), 6) for label in TRAJECTORIES},
            }
        )
    quality_values: list[float] = [
        float(item["value"])
        for item in request.fingerprint.values()
        if isinstance(item, dict) and isinstance(item.get("value"), int | float)
    ]
    return PredictionResponse(
        modelVersion="cold-start-baseline-v1",
        datasetVersion=f"{request.platform}-no-observed-training-data",
        featureVersion="creative-fingerprint-v1",
        confidence="LOW",
        comparableSampleSize=0,
        payload={
            "platform": request.platform,
            "targets": targets,
            "creativeQualityEvidence": sum(quality_values) / len(quality_values) if quality_values else None,
            "positiveFactors": [],
            "negativeFactors": [],
            "uncertaintyReasons": [
                "No comparable platform observations have been supplied",
                "Uniform probabilities are an explicit cold-start prior",
            ],
            "notice": "Historical estimate only; not a guarantee and not a claim about platform algorithms.",
        },
    )


def live(request: LivePredictionRequest) -> PredictionResponse:
    response = prepublish(request.model_copy(update={"model_reference":None}))
    payload = dict(response.payload)
    payload["liveSignals"] = request.live_features
    payload["reachFurtherUsed"] = bool(request.live_features.get("reachFurtherObserved"))
    payload["uncertaintyReasons"] = [
        *payload["uncertaintyReasons"],
        "Reach Further is observational evidence, not a causal or winner label",
    ]
    return response.model_copy(
        update={
            "model_version": "cold-start-live-baseline-v1",
            "feature_version": "creative-fingerprint-plus-live-signals-v1",
            "payload": payload,
        }
    )
