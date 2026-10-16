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
