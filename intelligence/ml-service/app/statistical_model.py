"""Small, versioned 72-hour model with grouped temporal holdout and JSON artifacts."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import statistics

from .config import settings

VERSION = "grouped-ridge-72h-v1"
FEATURE = "prerender-motion-intensity-v1"


def time(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp timezone required")
    return result


def feature(values):
    item = values.get("motionIntensity")
    if not isinstance(item, dict) or not isinstance(item.get("value"), (int, float)) or isinstance(item["value"], bool):
        raise ValueError("Versioned pre-publish motionIntensity feature required")
    value = float(item["value"])
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Finite normalized feature required")
    return value


def fit(request):
    now = datetime.now(timezone.utc)
    eligible = []
    identities = set()
    for row in request.rows:
        if row.get("horizon") != "72H" or row.get("verified") is not True or row.get("paid") is not False or row.get("metricSemantics") not in {"CUMULATIVE", "SNAPSHOT"}:
            raise ValueError("Verified organic 72H observations required; lifetime and approximate labels are ineligible")
        published, measured, cutoff = (time(row[k]) for k in ("publishedAt", "measuredAt", "featureCutoff"))
        if not cutoff < published or not timedelta(hours=72) <= measured - published <= timedelta(hours=73) or measured > now:
            raise ValueError("Pre-publish features and mature, nonfuture 72H outcomes required")
        if not row.get("parentVideoId") or not row.get("observationId") or row["observationId"] in identities:
            raise ValueError("Unique observation and sibling group identity required")
        identities.add(row["observationId"])
        y = row.get("views")
        if not isinstance(y, (int, float)) or isinstance(y, bool) or not math.isfinite(y) or y < 0:
            raise ValueError("Finite nonnegative views required; blank is not zero")
        eligible.append({**row, "x": feature(row["features"]), "y": math.log1p(y), "published": published, "measured": measured})
    groups = {}
    for row in eligible:
        groups.setdefault(row["parentVideoId"], []).append(row)
    if len(groups) < 30:
        raise ValueError("At least 30 independent parent videos required")
    ordered = sorted(groups, key=lambda group: min(r["published"] for r in groups[group]))
    test_groups = ordered[max(20, int(len(ordered) * .7)):]
    boundary = min(r["published"] for group in test_groups for r in groups[group])
    train_rows = [r for group in ordered if group not in test_groups for r in groups[group] if r["measured"] < boundary]
    test_rows = [r for group in test_groups for r in groups[group]]
    if len(train_rows) < 20 or len(test_rows) < 5:
        raise ValueError("Temporal outcome cutoff leaves insufficient training/holdout rows")
    xmean = statistics.mean(r["x"] for r in train_rows)
    ymean = statistics.mean(r["y"] for r in train_rows)
    slope = sum((r["x"]-xmean)*(r["y"]-ymean) for r in train_rows)/(1 + sum((r["x"]-xmean)**2 for r in train_rows))
    intercept = ymean - slope*xmean
    errors = [abs(intercept+slope*r["x"]-r["y"]) for r in test_rows]
    mae = statistics.mean(errors)
    baseline = statistics.mean(abs(ymean-r["y"]) for r in test_rows)
    dataset = [{k:v for k,v in row.items() if k not in {"x","y","published","measured"}} for row in eligible]
    dataset_hash = hashlib.sha256(json.dumps(dataset, sort_keys=True).encode()).hexdigest()
    artifact = {"pipelineVersion": VERSION, "featureVersion": FEATURE, "platform": request.platform, "datasetVersion": request.dataset_version,
        "datasetSha256": dataset_hash, "featureKeys": ["motionIntensity.value"], "horizonMinutes":4320,
        "trainingCutoff": max(r["measured"] for r in train_rows).isoformat(), "knowledgeCutoff": max(r["measured"] for r in eligible).isoformat(), "trainedAt": now.isoformat(),
        "intercept": intercept, "slope": slope, "sampleSize":len(train_rows), "holdoutSize":len(test_rows),
        "metrics": {"logMAE":mae, "baselineLogMAE":baseline, "promotionEligible":mae < baseline},
        "trainObservationIds":[r["observationId"] for r in train_rows],"testObservationIds":[r["observationId"] for r in test_rows],
        "trainGroups": [g for g in ordered if g not in test_groups],"testGroups":test_groups,
        "intervalLog80": sorted(errors)[min(len(errors)-1,math.ceil(len(errors)*.8)-1)], "intervalLog50": statistics.median(errors)}
    raw = json.dumps(artifact,sort_keys=True,allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    root = settings.data_root / "models/statistical"
    root.mkdir(parents=True,exist_ok=True)
    dataset_file=root / (dataset_hash+".dataset.json")
    if not dataset_file.exists():
        with dataset_file.open("x") as stream: json.dump(dataset,stream,sort_keys=True,allow_nan=False)
    path=root / (digest+".json")
    if not path.exists():
        with path.open("xb") as stream: stream.write(raw)
    return {**artifact, "modelVersion":VERSION+"-"+digest[:12], "artifactPath":str(path.relative_to(settings.data_root)), "artifactSha256":digest, "artifactCreated":True, "status":"CHALLENGER_CREATED"}


def load(reference, platform, cutoff=None):
    if not isinstance(reference,dict) or not reference.get("artifactSha256"):
        raise ValueError("Verified registry artifact required")
    root=(settings.data_root / "models/statistical").resolve()
    path=(settings.data_root / str(reference.get("artifactPath",""))).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError("Invalid artifact location")
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=reference["artifactSha256"]: raise ValueError("Artifact hash mismatch")
    artifact=json.loads(raw)
    if artifact["pipelineVersion"]!=VERSION or artifact["featureVersion"]!=FEATURE or artifact["platform"]!=platform: raise ValueError("Artifact schema/platform mismatch")
    if cutoff is not None and time(artifact["knowledgeCutoff"])>cutoff: raise ValueError("Model knowledge is newer than prediction cutoff")
    return artifact


def infer(request):
    model=load(request.model_reference,request.platform,request.knowledge_cutoff)
    x=feature(request.fingerprint)
    prediction=max(0,model["intercept"]+model["slope"]*x)
    target={"horizonMinutes":4320,"metric":"views","expectedValue":math.expm1(min(700,prediction)),
        **{f"interval{level}":[math.expm1(max(0,prediction-model[f"intervalLog{level}"])),math.expm1(min(700,prediction+model[f"intervalLog{level}"]))] for level in (50,80)}}
    return {"modelVersion":request.model_reference["modelVersion"],"datasetVersion":model["datasetVersion"],"featureVersion":FEATURE,"confidence":"LOW","comparableSampleSize":model["sampleSize"],
        "payload":{"platform":request.platform,"targets":[target],"artifactSha256":request.model_reference["artifactSha256"],"notice":"Historical 72H estimate from a small statistical model; no platform causal or winner claim", "uncertaintyReasons":["Single feature baseline; interval calibration is limited by holdout size"]}}
