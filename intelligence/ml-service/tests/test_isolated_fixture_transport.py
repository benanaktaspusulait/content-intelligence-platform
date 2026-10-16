import json

from app.workflow.creative_roles import run_paid_role


def test_isolated_fixture_transport_uses_contract_without_provider(monkeypatch, tmp_path):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_TOKEN', 'x' * 32)
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_DIR', str(tmp_path))
    (tmp_path / 'story.json').write_text(json.dumps({'alternatives': [
        {'candidateId': 'candidate-1', 'title': 'Fixture A', 'text': 'Mimi sees a note and it sticks.'},
        {'candidateId': 'candidate-2', 'title': 'Fixture B', 'text': 'Mimi reaches for a note and it multiplies.'},
    ]}), encoding='utf-8')
    result = run_paid_role('STORY', 'Mimi note', {
        'requestedAlternativeCount': 2,
        'inputMode': 'DETAILED_STORY',
        'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
        'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
    }, 0.20)
    assert result['provider'] == 'ISOLATED_FIXTURE'
    assert result['providerDispatched'] is False
    assert result['calls'] == 0
    assert len(result['result']['alternatives']) == 2


def test_isolated_fixture_missing_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_TOKEN', 'x' * 32)
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_DIR', str(tmp_path))
    try:
        run_paid_role('STORY', 'Mimi note', {'requestedAlternativeCount': 2}, 0.20)
    except ValueError as error:
        assert 'Missing or invalid isolated fixture' in str(error)
    else:
        raise AssertionError('missing fixture must fail closed')


def test_round_fixture_preserves_actual_retained_context(monkeypatch, tmp_path):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_TOKEN', 'x' * 32)
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_DIR', str(tmp_path))
    response = {'alternatives': [{'candidateId': 'next', 'title': 'Fixture continuation',
                                 'text': 'The retained rabbit story now makes the existing contact gap visible.'}]}
    (tmp_path / 'story.json').write_text(json.dumps({'rounds': {'2': response}}))
    retained = {'text': 'Previously retained story', 'sourceFingerprint': 'source-sha'}
    assessment = {'reviewId': 'actual-previous-review', 'reviewStatus': 'COMPLETED'}
    result = run_paid_role('STORY', 'Original source', {'roundNumber': 2, 'bestCandidate': retained,
        'previousAssessment': assessment, 'previousRevision': 'retained-draft-id', 'requestedAlternativeCount': 1}, .02)
    request = json.loads((tmp_path / 'provider-trace.jsonl').read_text())['request']
    assert request['context']['bestCandidate'] == retained
    assert request['context']['previousAssessment'] == assessment
    assert request['context']['previousRevision'] == 'retained-draft-id'
    assert result['result']['alternatives'][0]['candidateId'] == 'next'
    assert result['calls'] == 0


def test_fixture_review_does_not_fabricate_a_recommendation(monkeypatch, tmp_path):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE', 'true')
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_TOKEN', 'x' * 32)
    monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_DIR', str(tmp_path))
    review = dict(reviewId='fixture-review', sourceRequestId=None, sourceFingerprint=None,
        reviewModel='fixture', reviewModelVersion='fixture-v1', reviewPolicyVersion='story-evolution-v1',
        reviewTimestamp='TEST_ONLY', reviewStatus='COMPLETED', diversityAssessment={}, comparativeFindings=[],
        candidateReviews=[{'candidateId': 'candidate-1', 'concerns': ['No justified improvement']}],
        recommendedCandidateId=None, recommendationReason='Keep original', overallConcerns=[], usageAndCost={},
        evidenceLimitations=['Fixture only'], revisionComparison={'resolved': [], 'remaining': [], 'newFindings': []})
    (tmp_path / 'story_review.json').write_text(json.dumps(review))
    result = run_paid_role('STORY_REVIEW', 'original', {'sourceRequestId': 'live-run-id',
        'sourceFingerprint': 'live-source-sha', 'candidates': [{'candidateId': 'candidate-1', 'text': 'proposal'}]}, .02)
    assert result['result']['recommendedCandidateId'] is None
    assert result['result']['candidateReviews'][0]['concerns'] == ['No justified improvement']
    assert result['result']['sourceRequestId'] == 'live-run-id'
