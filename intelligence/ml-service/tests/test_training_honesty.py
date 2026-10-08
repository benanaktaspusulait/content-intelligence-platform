from fastapi.testclient import TestClient
from app.main import app


def test_training_does_not_claim_an_artifact_for_placeholder_rows():
    response = TestClient(app).post('/v1/training/train', json={
        'contractVersion': 'v1', 'platform': 'instagram',
        'datasetVersion': 'synthetic', 'rows': [{} for _ in range(30)]})
    assert response.status_code == 409
    assert response.json()['detail']['artifactCreated'] is False
    assert response.json()['detail']['status'] == 'TRAINING_DATA_INELIGIBLE'


def test_small_dataset_is_not_eligible():
    response = TestClient(app).post('/v1/training/train', json={
        'contractVersion': 'v1', 'platform': 'instagram',
        'datasetVersion': 'synthetic', 'rows': []})
    assert response.status_code == 409


def test_actual_clip_review_without_plan_never_claims_fidelity():
    from app.workflow.feedback import review_render
    result = review_render({'bindingHash': 'actual', 'lineageStatus': 'UNAVAILABLE'}, {
        'bindingHash': 'actual', 'assetHash': 'a' * 64, 'duration': 10,
        'coverage': [0, 10], 'experience': {},
    })
    assert result['planFidelity'] == 'NOT_EVALUATED'
    assert result['viewerFacingUsability'] == 'UNKNOWN'


def test_grounded_actual_experience_can_be_usable_without_original_plan():
    from app.workflow.feedback import review_render
    values = {'coreEventReadability': 'ADEQUATE', 'identity': 'RECOGNIZABLE', 'safety': 'APPROPRIATE', 'coherence': 'ADEQUATE', 'progression': 'DEVELOPING', 'opening': 'READABLE_PROMISE', 'ending': 'DELIVERS_PROMISE'}
    experience = {key: {'value': value, 'start': 0, 'end': 10, 'evidenceBasis': 'HUMAN_REVIEWED_CLIP', 'reference': 'clip', 'observed': 'Human inspected whole clip', 'confidence': 'HIGH'} for key, value in values.items()}
    result = review_render({'bindingHash': 'actual', 'lineageStatus': 'UNAVAILABLE'}, {
        'bindingHash': 'actual', 'assetHash': 'a' * 64, 'duration': 10, 'coverage': [0, 10], 'experience': experience,
    })
    assert result['planFidelity'] == 'NOT_EVALUATED'
    assert result['viewerFacingUsability'] == 'USABLE'
    assert result['editorialRecommendation'] == 'TEST_CANDIDATE'


def test_actual_only_transport_accepts_explicit_null_plan_dimensions():
    from fastapi.testclient import TestClient
    from app.main import app
    response = TestClient(app).post('/api/v1/workflow/feedback', json={'kind': 'ACTUAL_RENDER_QA', 'payload': {
        'plan': {'bindingHash': 'actual', 'lineageStatus': 'UNAVAILABLE', 'events': [], 'planQuality': None, 'executionRisk': None},
        'observation': {'bindingHash': 'actual', 'assetHash': 'a'*64, 'duration': 12, 'coverage': [0,12]},
    }})
    assert response.status_code == 200
    value = response.json()
    assert value['planFidelity'] == 'NOT_EVALUATED'
    assert value['reviewDimensions']['promptPlanQuality']['status'] == 'UNKNOWN'
    assert value['reviewDimensions']['generatorExecutionRisk']['status'] == 'UNKNOWN'
    assert value['viewerFacingUsability'] != 'USABLE'
