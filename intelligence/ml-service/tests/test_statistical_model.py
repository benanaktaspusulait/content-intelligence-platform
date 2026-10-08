from datetime import datetime, timedelta, timezone
import math
from types import SimpleNamespace
import pytest

from app.config import settings
from app.contracts import PredictionRequest
from app.statistical_model import fit, infer, load


def rows():
    result=[]
    for n in range(40):
        published=datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(days=n*5)
        x=(n%7)/6
        result.append({"parentVideoId":f"parent-{n}","observationId":f"observation-{n}","horizon":"72H","verified":True,"paid":False,"metricSemantics":"CUMULATIVE", "publishedAt":published.isoformat(), "measuredAt":(published+timedelta(hours=72)).isoformat(),"featureCutoff":(published-timedelta(hours=1)).isoformat(),"views":math.expm1(2+3*x),"features":{"overallMotionIntensity":{"value":x}}})
    return result


def request(data=None):
    return SimpleNamespace(rows=data or rows(),platform="instagram",dataset_version="fixture-verified-v1")


def test_artifact_temporal_groups_reload_prediction_parity_and_challenger_inactive(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,"data_root",tmp_path)
    model=fit(request())
    assert model["artifactCreated"] and model["status"]=="CHALLENGER_CREATED"
    assert model["metrics"]["promotionEligible"]
    assert not set(model["trainGroups"]) & set(model["testGroups"])
    ref={k:model[k] for k in ("modelVersion","artifactPath","artifactSha256")}
    reloaded=load(ref,"instagram")
    prediction=PredictionRequest(contractVersion="v1",platform="instagram",fingerprint={"overallMotionIntensity":{"value":.5}},knowledgeCutoff=datetime.now(timezone.utc),modelReference=ref)
    output=infer(prediction)
    expected=math.expm1(reloaded["intercept"]+reloaded["slope"]*.5)
    assert output["payload"]["targets"][0]["expectedValue"]==pytest.approx(expected)
    from app.prediction import prepublish
    assert prepublish(prediction.model_copy(update={"model_reference":None})).model_version=="cold-start-baseline-v1"
    assert prepublish(prediction).model_version==model["modelVersion"]
    (tmp_path/model["artifactPath"]).write_text('{}')
    with pytest.raises(ValueError,match="hash mismatch"): infer(prediction)


@pytest.mark.parametrize("mutation",[
    {"horizon":"LIFETIME"}, {"paid":True}, {"verified":False}, {"featureCutoff":"2026-10-08T00:00:00Z"},
    {"measuredAt":"2099-01-01T00:00:00Z"}, {"views":None}, {"features":{"views":{"value":1000}}},
])
def test_leakage_and_unverified_labels_are_rejected_without_artifact(tmp_path,monkeypatch,mutation):
    monkeypatch.setattr(settings,"data_root",tmp_path)
    data=rows();data[0].update(mutation)
    with pytest.raises(ValueError):fit(request(data))
    assert not (tmp_path/'models').exists()


def test_sibling_videos_cannot_inflate_independent_sample_size(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,"data_root",tmp_path)
    data=rows()
    for n,item in enumerate(data):item["parentVideoId"]=f"parent-{n%10}"
    with pytest.raises(ValueError,match="independent parent"):fit(request(data))


def test_model_from_future_cannot_predict_historical_cutoff(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,"data_root",tmp_path)
    model=fit(request())
    with pytest.raises(ValueError,match="newer than prediction"):load(model,"instagram",datetime(2025,1,1,tzinfo=timezone.utc))


def test_registry_model_version_must_match_immutable_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_root", tmp_path)
    model = fit(request())
    with pytest.raises(ValueError, match="model version mismatch"):
        load({**model, "modelVersion": "forged-version"}, "instagram")


def test_artifact_http_verification_preserves_registry_identity_and_rejects_forgery(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(settings, "data_root", tmp_path)
    model = fit(request())
    reference = {key: model[key] for key in ("modelVersion", "artifactPath", "artifactSha256")}
    with TestClient(app) as client:
        response = client.post("/v1/training/verify-artifact", json={**reference, "platform": "instagram"})
        assert response.status_code == 200
        assert response.json()["modelVersion"] == model["modelVersion"]
        assert response.json()["datasetVersion"] == "fixture-verified-v1"
        assert response.json()["verified"]
        assert client.post("/v1/training/verify-artifact", json={**reference, "platform":"instagram", "modelVersion":"forged"}).status_code == 409
        del reference["modelVersion"]
        assert client.post("/v1/training/verify-artifact", json={**reference,"platform":"instagram"}).status_code == 409
